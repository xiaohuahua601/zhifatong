"""
智法通 - 合同服务模块

提供合同文件解析、Agent审查、报告管理等核心业务逻辑。
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import UploadFile, HTTPException, status
from typing import Optional
import os
import time
import json
import logging

from app.models.contract import Contract, ReviewReport, RiskClause, ContractStatus, RiskLevel
from app.utils.file_parser import FileParser
from app.agent.workflow import ContractReviewWorkflow
# 复用Agent节点的LLM调用与JSON提取工具（模块级函数，供优化服务使用）
from app.agent.nodes import _call_ollama, _extract_json, OllamaCallError
from app.config import settings

logger = logging.getLogger(__name__)


class ContractService:
    """合同审查服务类

    封装合同上传、解析、审查和报告管理的业务逻辑。
    """

    def __init__(self, db: AsyncSession):
        """初始化合同服务

        Args:
            db: 异步数据库会话
        """
        self.db = db
        self.review_workflow = ContractReviewWorkflow()

    async def upload_contract(
        self,
        user_id: int,
        file: UploadFile,
    ) -> dict:
        """上传合同文件

        保存文件到磁盘，创建合同记录，并启动异步解析。
        上传前会对文件进行严格的安全校验：扩展名白名单、文件大小、MIME类型、
        文件名路径遍历防护，任一校验失败均抛出 ValueError 阻止上传。

        Args:
            user_id: 用户ID
            file: 上传的文件对象

        Returns:
            包含合同ID、标题、文件名和状态的字典

        Raises:
            ValueError: 文件未提供 / 扩展名不允许 / 文件过大 / MIME类型不匹配
        """
        # ==================== 安全校验（P0修复）====================
        # 1. 文件名存在性校验
        if not file.filename:
            raise ValueError("文件名不能为空")

        # 2. 文件名安全处理：使用 basename 防止路径遍历攻击
        #    攻击者可能传入 "../../etc/passwd" 等文件名覆盖系统文件
        safe_filename = os.path.basename(file.filename)
        if not safe_filename:
            # basename 后可能为空（如纯路径分隔符的输入）
            raise ValueError("文件名不合法")

        # 3. 扩展名白名单校验：仅允许 .pdf/.docx/.doc/.txt
        allowed_extensions = (".pdf", ".docx", ".doc", ".txt")
        # 统一小写比较，避免 .PDF 等大小写绕过
        file_ext = os.path.splitext(safe_filename)[1].lower()
        if file_ext not in allowed_extensions:
            raise ValueError(
                f"不支持的文件类型：{file_ext or '无扩展名'}，"
                f"仅允许 {', '.join(allowed_extensions)} 格式"
            )

        # 4. 文件大小限制：最大10MB
        #    先读取内容到内存以统一校验大小和后续解析
        content = await file.read()
        max_size = 10 * 1024 * 1024  # 10MB
        if len(content) > max_size:
            raise ValueError(
                f"文件大小超过限制：{len(content)} 字节，最大允许 {max_size} 字节（10MB）"
            )
        if len(content) == 0:
            raise ValueError("文件内容为空，无法上传")

        # 5. MIME类型校验：检查 content_type 是否与扩展名匹配
        #    注意：content_type 由客户端提供，仍需校验以防简单伪造
        allowed_mime_map = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".doc": "application/msword",
            ".txt": "text/plain",
        }
        expected_mime = allowed_mime_map[file_ext]
        # 客户端可能附加 charset 等参数（如 "text/plain; charset=utf-8"），取分号前部分比较
        actual_mime = (file.content_type or "").split(";")[0].strip().lower()
        if actual_mime != expected_mime:
            raise ValueError(
                f"文件MIME类型不匹配：实际 {actual_mime or '未知'}，"
                f"扩展名 {file_ext} 期望 {expected_mime}"
            )

        # ==================== 文件保存与解析 ====================
        # 确保上传目录存在
        upload_dir = os.path.abspath(settings.UPLOAD_DIR)
        os.makedirs(upload_dir, exist_ok=True)

        # 生成唯一文件名，避免冲突（使用安全处理后的扩展名）
        timestamp = int(time.time() * 1000)
        saved_filename = f"contract_{user_id}_{timestamp}{file_ext}"
        file_path = os.path.join(upload_dir, saved_filename)

        # 保存文件到磁盘（content 已在上一步读取）
        with open(file_path, "wb") as f:
            f.write(content)

        # 创建合同记录（使用安全处理后的文件名）
        contract = Contract(
            user_id=user_id,
            title=os.path.splitext(safe_filename)[0],  # 使用文件名作为标题
            file_name=safe_filename,
            file_path=file_path,
            file_size=len(content),
            file_type=file_ext.lstrip("."),
            status=ContractStatus.UPLOADED,
        )
        self.db.add(contract)
        await self.db.flush()

        # 异步解析合同内容
        try:
            contract.status = ContractStatus.PARSING
            await self.db.flush()

            # 解析文件内容
            parsed_content = await FileParser.parse(file_path, file_ext.lstrip("."))
            contract.content = parsed_content
            contract.status = ContractStatus.PARSED
            await self.db.flush()
        except Exception as e:
            contract.status = ContractStatus.FAILED
            await self.db.flush()
            raise ValueError(f"合同解析失败：{str(e)}")

        return {
            "id": contract.id,
            "title": contract.title,
            "file_name": contract.file_name,
            "status": contract.status,
        }

    async def review_contract(
        self,
        user_id: int,
        contract_id: int,
        contract_type: Optional[str] = None,
    ) -> dict:
        """启动合同审查

        使用LangGraph Agent工作流对合同进行多维度审查。

        Args:
            user_id: 用户ID
            contract_id: 合同ID
            contract_type: 合同类型

        Returns:
            包含审查结果的字典
        """
        # 获取合同
        contract = await self.db.get(Contract, contract_id)
        if not contract or contract.user_id != user_id:
            raise ValueError("合同不存在或无权访问")

        # ==================== 并发防抖（P0修复）====================
        # 若合同已在审查中，拒绝重复发起，避免多请求并发审查同一合同
        # （此前用户在审查进行中点击"重试"会触发MySQL行锁等待超时1205）
        if contract.status == ContractStatus.REVIEWING:
            raise ValueError("该合同正在审查中，请等待当前审查完成后再试")

        if not contract.content:
            # 容错：历史合同可能解析结果未持久化（content为空），
            # 若源文件仍存在则现场重新解析，避免用户被迫重新上传
            reparse_ok = False
            if contract.file_path and os.path.exists(contract.file_path):
                try:
                    parsed = await FileParser.parse(
                        contract.file_path, contract.file_type or "txt"
                    )
                    if parsed and parsed.strip():
                        contract.content = parsed
                        if contract.status != ContractStatus.REVIEWED:
                            contract.status = ContractStatus.PARSED
                        await self.db.flush()
                        reparse_ok = True
                except Exception as parse_err:
                    # 重新解析失败则落入下方统一报错
                    logger.warning(f"合同重新解析失败（id={contract_id}）：{parse_err}")
            if not reparse_ok:
                raise ValueError("合同内容为空，请先完成解析")

        # 更新合同状态
        contract.status = ContractStatus.REVIEWING
        if contract_type:
            contract.contract_type = contract_type
        # ==================== 事务边界修复（P0）====================
        # 立即提交而非仅flush：将REVIEWING状态落库并释放该行锁。
        # 此前仅flush未提交，长耗时的LLM审查期间（数十秒）一直持有
        # contracts行锁，导致并发/重试请求的UPDATE因锁等待超时(1205)失败。
        # expire_on_commit=False（database.py已配置），commit后ORM对象属性仍可读写。
        await self.db.commit()

        # 调用Agent工作流进行审查（纯LLM计算，不持有任何数据库事务）
        start_time = time.time()
        try:
            review_result = await self.review_workflow.run(
                contract_content=contract.content,
                contract_type=contract_type or contract.contract_type or "通用合同",
            )
            review_duration_ms = int((time.time() - start_time) * 1000)

            # 保存审查报告
            report = ReviewReport(
                contract_id=contract.id,
                overall_score=review_result.get("overall_score"),
                risk_level=review_result.get("risk_level"),
                risk_clause_count=len(review_result.get("risk_clauses", [])),
                summary=review_result.get("summary"),
                suggestions=json.dumps(review_result.get("suggestions", []), ensure_ascii=False),
                # ==================== V6.0.4修复：维度分存数值 ====================
                # 此前三字段存的是json.dumps(dict)（如{"completeness_ratio":0.57,...}），
                # 前端parseInt解析JSON字符串恒得NaN→显示0%，造成"综合评分非0但三维度全0"缺陷。
                # 现改存数值分数字符串（state顶层已由各检查节点产出0-100的评分），
                # 各维度详情数据仍通过报告的issues/缺失条款等字段完整呈现。
                completeness=str(round(float(review_result.get("completeness_score", 0) or 0), 1)),
                compliance=str(round(float(review_result.get("compliance_score", 0) or 0), 1)),
                consistency=str(round(float(review_result.get("consistency_score", 0) or 0), 1)),
                review_duration_ms=review_duration_ms,
                # V4.0新增：多Agent对抗式审查结果持久化（参考文档4.3节）
                primary_risks=json.dumps(review_result.get("primary_risks", []), ensure_ascii=False),
                review_check=json.dumps(review_result.get("review_check", {}), ensure_ascii=False),
                adverse_opinions=json.dumps(review_result.get("adverse_opinions", []), ensure_ascii=False),
                debate_log=json.dumps(review_result.get("debate_log", []), ensure_ascii=False),
                unresolved_issues=json.dumps(review_result.get("unresolved_issues", []), ensure_ascii=False),
                adverse_opinion_count=review_result.get("adverse_opinion_count", len(review_result.get("adverse_opinions", []))),
                unresolved_count=review_result.get("unresolved_count", len(review_result.get("unresolved_issues", []))),
            )
            self.db.add(report)
            await self.db.flush()

            # 保存风险条款
            for idx, clause_data in enumerate(review_result.get("risk_clauses", [])):
                risk_clause = RiskClause(
                    report_id=report.id,
                    clause_index=idx + 1,
                    original_text=clause_data.get("original_text", ""),
                    risk_type=clause_data.get("risk_type"),
                    risk_level=clause_data.get("risk_level"),
                    risk_score=clause_data.get("risk_score"),
                    risk_description=clause_data.get("risk_description"),
                    suggestion=clause_data.get("suggestion"),
                    legal_basis=clause_data.get("legal_basis"),
                )
                self.db.add(risk_clause)

            # 更新合同状态
            contract.status = ContractStatus.REVIEWED
            # 审查结果原子提交：报告+风险条款+REVIEWED状态在同一事务落库
            await self.db.commit()

            return {
                "report_id": report.id,
                "overall_score": report.overall_score,
                "risk_level": report.risk_level,
                "risk_clause_count": report.risk_clause_count,
                "review_duration_ms": review_duration_ms,
            }

        except Exception as e:
            # ==================== 失败路径独立事务（P0修复）====================
            # 审查异常时：先回滚当前会话（清空可能残留的半成品报告写入），
            # 再以新事务将合同状态回写为FAILED，确保状态可靠落库；
            # 此前直接flush，若会话已处于异常/回滚状态会二次抛错，掩盖真实失败原因
            try:
                await self.db.rollback()
                contract.status = ContractStatus.FAILED
                await self.db.commit()
            except Exception as mark_err:
                logger.error(f"回写FAILED状态失败（contract_id={contract_id}）：{mark_err}")
            raise ValueError(f"合同审查失败：{str(e)}")

    async def get_review_report(
        self,
        user_id: int,
        contract_id: int,
    ) -> dict:
        """获取合同审查报告

        Args:
            user_id: 用户ID
            contract_id: 合同ID

        Returns:
            审查报告详情字典
        """
        # 验证合同归属
        contract = await self.db.get(Contract, contract_id)
        if not contract or contract.user_id != user_id:
            raise ValueError("合同不存在或无权访问")

        # 查询最新的审查报告
        # V6.0.4修复：重新审查会使同一合同存在多份历史报告，
        # 此前scalar_one_or_none在多行时抛"Multiple rows"导致接口500，
        # 改为按创建时间倒序取最新一份
        result = await self.db.execute(
            select(ReviewReport)
            .where(ReviewReport.contract_id == contract_id)
            .order_by(ReviewReport.created_at.desc(), ReviewReport.id.desc())
        )
        report = result.scalars().first()

        if not report:
            return {
                "id": 0,
                "contract_id": contract_id,
                "overall_score": None,
                "risk_level": None,
                "risk_clause_count": 0,
                "summary": None,
                "suggestions": None,
                "completeness": None,
                "compliance": None,
                "consistency": None,
                "review_duration_ms": None,
                "risk_clauses": [],
                # V4.0新增：对抗式审查字段默认值
                "primary_risks": "[]",
                "review_check": "{}",
                "adverse_opinions": "[]",
                "debate_log": "[]",
                "unresolved_issues": "[]",
                "adverse_opinion_count": 0,
                "unresolved_count": 0,
            }

        # 查询风险条款
        clauses_result = await self.db.execute(
            select(RiskClause).where(RiskClause.report_id == report.id)
        )
        risk_clauses = clauses_result.scalars().all()

        return {
            "id": report.id,
            "contract_id": contract_id,
            "overall_score": report.overall_score,
            "risk_level": report.risk_level,
            "risk_clause_count": report.risk_clause_count,
            "summary": report.summary,
            "suggestions": report.suggestions,
            "completeness": report.completeness,
            "compliance": report.compliance,
            "consistency": report.consistency,
            "review_duration_ms": report.review_duration_ms,
            # V4.0新增：返回多Agent对抗式审查结果（JSON字符串，由前端解析）
            "primary_risks": report.primary_risks or "[]",
            "review_check": report.review_check or "{}",
            "adverse_opinions": report.adverse_opinions or "[]",
            "debate_log": report.debate_log or "[]",
            "unresolved_issues": report.unresolved_issues or "[]",
            "adverse_opinion_count": report.adverse_opinion_count or 0,
            "unresolved_count": report.unresolved_count or 0,
            "risk_clauses": [
                {
                    "id": rc.id,
                    "clause_index": rc.clause_index,
                    "original_text": rc.original_text,
                    "risk_type": rc.risk_type,
                    "risk_level": rc.risk_level,
                    "risk_score": rc.risk_score,
                    "risk_description": rc.risk_description,
                    "suggestion": rc.suggestion,
                    "legal_basis": rc.legal_basis,
                }
                for rc in risk_clauses
            ],
        }

    async def get_contract_history(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        status_filter: Optional[str] = None,
    ) -> dict:
        """获取合同历史记录

        Args:
            user_id: 用户ID
            page: 页码
            page_size: 每页数量
            status_filter: 状态筛选

        Returns:
            包含合同列表和分页信息的字典
        """
        # 构建查询条件
        conditions = [Contract.user_id == user_id]
        if status_filter:
            conditions.append(Contract.status == status_filter)

        # 查询总数
        count_result = await self.db.execute(
            select(func.count(Contract.id)).where(*conditions)
        )
        total = count_result.scalar() or 0

        # 查询合同列表
        result = await self.db.execute(
            select(Contract)
            .where(*conditions)
            .order_by(Contract.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        contracts = result.scalars().all()

        # 批量获取每个合同的最新报告评分（修复N+1查询：原实现每条合同单独查一次DB）
        # 改为一次查询取出当前页所有合同的最新报告，再在内存中按 contract_id 映射
        contract_ids = [c.id for c in contracts]
        latest_reports: dict = {}
        if contract_ids:
            # 子查询：每个 contract_id 下 created_at 最大的那条报告
            latest_subq = (
                select(
                    ReviewReport.contract_id,
                    func.max(ReviewReport.created_at).label("max_created"),
                )
                .where(ReviewReport.contract_id.in_(contract_ids))
                .group_by(ReviewReport.contract_id)
                .subquery()
            )
            # 关联回主表取完整报告字段（overall_score / risk_level）
            report_result = await self.db.execute(
                select(ReviewReport)
                .join(
                    latest_subq,
                    (ReviewReport.contract_id == latest_subq.c.contract_id)
                    & (ReviewReport.created_at == latest_subq.c.max_created),
                )
            )
            for rpt in report_result.scalars().all():
                latest_reports[rpt.contract_id] = rpt

        # 组装返回结果（O(1) 内存查表，无额外DB往返）
        items = []
        for c in contracts:
            report = latest_reports.get(c.id)
            items.append({
                "id": c.id,
                "title": c.title,
                "file_name": c.file_name,
                "contract_type": c.contract_type,
                "status": c.status,
                "overall_score": report.overall_score if report else None,
                "risk_level": report.risk_level if report else None,
                "created_at": c.created_at.isoformat() if c.created_at else "",
            })

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_contract_detail(
        self,
        user_id: int,
        contract_id: int,
    ) -> dict:
        """获取合同详细信息

        Args:
            user_id: 用户ID
            contract_id: 合同ID

        Returns:
            合同详情字典
        """
        contract = await self.db.get(Contract, contract_id)
        if not contract or contract.user_id != user_id:
            raise ValueError("合同不存在或无权访问")

        return {
            "id": contract.id,
            "title": contract.title,
            "file_name": contract.file_name,
            "file_size": contract.file_size,
            "file_type": contract.file_type,
            "content": contract.content,
            "status": contract.status,
            "contract_type": contract.contract_type,
            "party_a": contract.party_a,
            "party_b": contract.party_b,
            "amount": contract.amount,
            "created_at": contract.created_at.isoformat() if contract.created_at else "",
            "updated_at": contract.updated_at.isoformat() if contract.updated_at else "",
        }

    async def delete_contract(
        self,
        user_id: int,
        contract_id: int,
    ) -> None:
        """删除合同

        同时删除文件存储和数据库记录。

        Args:
            user_id: 用户ID
            contract_id: 合同ID
        """
        contract = await self.db.get(Contract, contract_id)
        if not contract or contract.user_id != user_id:
            raise ValueError("合同不存在或无权访问")

        # 删除文件
        if contract.file_path and os.path.exists(contract.file_path):
            os.remove(contract.file_path)

        # 删除数据库记录（级联删除报告和风险条款）
        await self.db.delete(contract)
        await self.db.flush()

    async def update_contract_type(
        self,
        user_id: int,
        contract_id: int,
        contract_type: Optional[str],
    ) -> dict:
        """更新合同分类（支持「未分类」合同归档管理）

        仅允许合同所有者修改本人合同的分类，防止越权修改他人数据。

        Args:
            user_id: 当前登录用户ID（用于数据隔离校验）
            contract_id: 合同ID
            contract_type: 合同类型（如：劳动合同、租赁合同、采购合同等）

        Returns:
            包含更新后合同信息的字典

        Raises:
            ValueError: 合同不存在或非本人合同
        """
        contract = await self.db.get(Contract, contract_id)
        if not contract or contract.user_id != user_id:
            raise ValueError("合同不存在或无权访问")

        # 更新合同分类字段（允许设置为空以清除分类）
        contract.contract_type = contract_type.strip() if contract_type else None
        await self.db.flush()

        return {
            "id": contract.id,
            "title": contract.title,
            "contract_type": contract.contract_type,
            "status": contract.status,
            "message": "合同分类已更新",
        }

    # ==================== 合同优化下载（V6.0.6新增）====================

    async def optimize_contract(self, user_id: int, contract_id: int) -> dict:
        """基于审查报告修改建议优化原合同，生成Markdown格式优化版合同

        处理流程：
        1. 校验合同归属与审查状态，加载最新审查报告的建议清单
        2. LLM批量改写风险条款（一次调用输出JSON数组，逐条对应建议）
        3. LLM改写失败或输出无效时，规则兜底（保留原文+修订提示标注）
        4. 在原合同全文中定位并替换被优化条款
        5. 组装精美专业的Markdown文档（封面、当事人、正文、修订对照附录）

        Args:
            user_id: 当前登录用户ID（用于数据隔离校验）
            contract_id: 合同ID

        Returns:
            {"markdown": 优化后合同全文(Markdown), "file_name": "原合同名_优化后.md"}

        Raises:
            ValueError: 合同不存在/无权访问/尚未审查/内容为空/暂无修改建议
        """
        # ---------- 1. 校验与数据加载 ----------
        contract = await self.db.get(Contract, contract_id)
        if not contract or contract.user_id != user_id:
            raise ValueError("合同不存在或无权访问")
        if contract.status != ContractStatus.REVIEWED:
            raise ValueError("请先完成合同审查，再进行优化下载")
        if not contract.content or not contract.content.strip():
            raise ValueError("合同内容为空，无法优化")

        # 取最新审查报告（同一合同重新审查会产生多份历史报告，取最新）
        report_result = await self.db.execute(
            select(ReviewReport)
            .where(ReviewReport.contract_id == contract_id)
            .order_by(ReviewReport.created_at.desc(), ReviewReport.id.desc())
        )
        report = report_result.scalars().first()
        if not report:
            raise ValueError("未找到审查报告，请先完成合同审查")

        # 解析建议清单（V6.0.5起为JSON数组，含clause_index/original_text/suggestion/legal_basis）
        try:
            suggestions = json.loads(report.suggestions) if report.suggestions else []
            if not isinstance(suggestions, list):
                suggestions = []
        except (json.JSONDecodeError, TypeError):
            suggestions = []
        if not suggestions:
            raise ValueError("该合同审查报告暂无修改建议，无需优化")

        contract_title = contract.title
        contract_type = contract.contract_type or "通用合同"
        original_text = contract.content

        # ---------- 2. LLM批量改写风险条款 ----------
        # 将建议清单送入LLM，要求逐条输出改写后的完整条款文本
        revisions: dict[int, dict] = {}  # clause_index -> {"revised": 新条款文本, "source": "llm"/"fallback"}
        suggestion_lines = []
        for i, s in enumerate(suggestions):
            if not isinstance(s, dict):
                continue
            suggestion_lines.append(
                f"[{i + 1}] 原条款：{str(s.get('original_text', ''))[:200]}\n"
                f"    修改建议：{str(s.get('suggestion', ''))[:300]}\n"
                f"    法律依据：{str(s.get('legal_basis', '') or '无')}"
            )

        prompt = f"""你是资深法律文书专家。请根据以下修改建议，逐条改写该{contract_type}的风险条款。
改写要求：
1. 每条改写为一段完整、可直接替换原条款的合同条款文本
2. 消除所述风险，符合给出的法律依据，保持合同条款的正式法律语言风格
3. 仅输出JSON数组，格式：[{{"index": 1, "revised_text": "改写后的完整条款"}}]

修改建议清单：
{chr(10).join(suggestion_lines)[:3000]}"""

        llm_ok = False
        try:
            result = await _call_ollama(prompt, temperature=0.3, max_tokens=2500)
            llm_revisions = _extract_json(result, is_array=True) or []
            for item in llm_revisions:
                if isinstance(item, dict) and item.get("revised_text"):
                    idx = int(item.get("index", 0))
                    # 有效改写需与建议序号对应且非空、非原文复述
                    rt = str(item["revised_text"]).strip()
                    orig = str(suggestions[idx - 1].get("original_text", "")).strip() if 0 < idx <= len(suggestions) else ""
                    if len(rt) >= 10 and rt != orig:
                        revisions[idx] = {"revised": rt, "source": "llm"}
            llm_ok = len(revisions) > 0
            if not llm_ok:
                logger.warning(f"[optimize_contract] LLM改写无效（合同{contract_id}），启用规则兜底")
        except OllamaCallError as e:
            logger.warning(f"[optimize_contract] LLM改写失败（合同{contract_id}）：{e}，启用规则兜底")

        # ---------- 3. 规则兜底：LLM未覆盖的建议条目 ----------
        # 兜底方式：保留原条款文本，其后追加修订说明块（不破坏合同结构，保证法务可读性）
        # 注意：原条款文本无效（LLM复述prompt占位符"原文"/"缺失条款"等）时，
        # 仅输出修订说明，避免占位符文本残留在最终文档中
        def _orig_usable(o: str) -> bool:
            """兜底场景的原文可用性判断（占位符/过短文本不可用）"""
            if not o or len(o) < 8:
                return False
            cleaned = o.replace(" ", "")
            # 纯占位符（"原文"/"缺失条款"/"[N] 原文"）不可用
            if cleaned in ("原文", "缺失条款") or cleaned.rstrip("原文") in ("", "[1]", "[2]", "[3]", "[4]", "[5]", "[6]", "[7]", "[8]", "[9]", "[10]", "[11]", "[12]"):
                return False
            # "[N] 真实长文本"可用（截去编号前缀后仍有实质内容）
            return True

        for i, s in enumerate(suggestions):
            if not isinstance(s, dict):
                continue
            idx = i + 1
            if idx not in revisions:
                orig = str(s.get("original_text", "")).strip()
                advice = str(s.get("suggestion", "")).strip()
                law = str(s.get("legal_basis", "") or "").strip()
                # 组装修订说明（法律依据后置括注）
                note = f"> ⚖️ **【修订说明】** {advice}"
                if law:
                    note += f"（依据：{law}）"
                # 原文可用时保留原文+说明；不可用时仅输出说明
                fallback_block = f"{orig}\n\n{note}" if _orig_usable(orig) else note
                revisions[idx] = {"revised": fallback_block or advice, "source": "fallback"}

        # ---------- 4. 全文条款定位与替换 ----------
        # 定位策略（三级回退，应对小模型建议中原文不可靠的情况）：
        #   a) 建议的original_text有效 → 全文精确子串定位
        #   b) original_text无效（LLM复述了prompt占位符"原文"/"缺失条款"等）
        #      → 按与审查工作流相同的正则重新拆分全文条款，按clause_index取条款
        #   c) 均失败 → 正文不动，修订收入附录B完整呈现（用户可手动应用）
        import re as _re
        _clause_pattern = r'(第[一二三四五六七八九十百]+条|第\d+条|\d+\.[\d.]+|[一二三四五六七八九十]+、)'

        def _split_clauses_for_optimize(text: str) -> list[str]:
            """按条款编号正则拆分全文（与split_clauses节点相同的确定性逻辑）"""
            parts = _re.split(f'({_clause_pattern})', text)
            clauses_raw, current = [], ""
            for part in parts:
                if part and _re.match(_clause_pattern, part):
                    if current.strip():
                        clauses_raw.append(current.strip())
                    current = part
                elif part:
                    current += part
            if current.strip():
                clauses_raw.append(current.strip())
            return clauses_raw

        def _is_valid_orig(o: str) -> bool:
            """建议原文是否有效（排除LLM复述prompt占位符的情况）"""
            if not o or len(o) < 8:
                return False
            # 占位符特征：纯"原文"/"缺失条款"/形如"[N] 原文"
            if o.replace(" ", "") in ("原文", "缺失条款") or _re.match(r'^\[\d+\]\s*原文$', o):
                return False
            return True

        full_clauses = _split_clauses_for_optimize(original_text) if original_text else []
        optimized_text = original_text
        replaced_count = 0
        unlocated_revisions: list[dict] = []  # 定位失败的修订（收入附录B）

        for idx in sorted(revisions.keys()):
            s = suggestions[idx - 1]
            orig = str(s.get("original_text", "")).strip()
            clause_idx = s.get("clause_index")
            rev = revisions[idx]

            # 策略a：有效原文 → 全文精确匹配替换
            if _is_valid_orig(orig) and orig in optimized_text:
                optimized_text = optimized_text.replace(orig, rev["revised"], 1)
                replaced_count += 1
                continue

            # 策略b：按clause_index从拆分条款列表定位
            located_text = None
            if isinstance(clause_idx, int) and 0 <= clause_idx < len(full_clauses):
                candidate = full_clauses[clause_idx]
                # 校验：候选条款与建议原文有包含关系（防止索引错位误替换）
                if _is_valid_orig(orig) and (orig[:15] in candidate or candidate[:15] in orig):
                    located_text = candidate
                elif not _is_valid_orig(orig) and 10 <= len(candidate) <= 600:
                    # 原文无效时信任条款索引（编号来自审查时的条款列表），
                    # 但限制候选长度在合理条款范围，防止误替换合同头部整块
                    located_text = candidate
            if located_text and located_text in optimized_text:
                optimized_text = optimized_text.replace(located_text, rev["revised"], 1)
                replaced_count += 1
                continue

            # 策略c：定位失败，收入附录B
            unlocated_revisions.append({
                "idx": idx,
                "suggestion": s,
                "revision": rev,
            })

        # ---------- 5. 组装精美专业的Markdown文档 ----------
        now = time.strftime("%Y年%m月%d日 %H:%M")
        score = report.overall_score
        level_map = {"low": "低", "medium": "中", "high": "高", "critical": "严重"}
        level_cn = level_map.get(report.risk_level or "low", "低")

        # 5.1 文档头部：合同名+优化标识+生成信息（引用块+分隔线营造正式感）
        md_parts = [
            f"# {contract_title}",
            "",
            "> 📄 **智法通 · 合同优化版**",
            "> ",
            f"> 本文档由智法通AI基于《{contract_title}》审查报告的修改建议自动优化生成  ",
            f"> 原始评分：**{score}分**（风险等级：{level_cn}）｜ 生成时间：{now}  ",
            f"> 建议条目：{len(suggestions)} 条 ｜ 正文已应用修订：{replaced_count} 条"
            + (f" ｜ 附录修订指引：{len(unlocated_revisions)} 条" if unlocated_revisions else ""),
            "",
            "---",
            "",
        ]

        # 5.2 正文：优化后全文（按条款分段为Markdown段落）
        for para in optimized_text.split("\n"):
            line = para.strip()
            if not line:
                md_parts.append("")
                continue
            # "第X条"样式的行加粗为条款标题，增强层次感
            if len(line) <= 30 and ("条" in line[:8] or "章" in line[:4]):
                md_parts.append(f"**{line}**")
            else:
                md_parts.append(line)

        # 5.3 附录A：修订对照表（原条款/优化后/法律依据，一眼看清变化）
        md_parts.extend([
            "",
            "---",
            "",
            "## 附录A：修订对照表",
            "",
            "| # | 修订要点 | 法律依据 | 修订方式 |",
            "| :---: | :--- | :--- | :---: |",
        ])
        for i, s in enumerate(suggestions):
            if not isinstance(s, dict):
                continue
            idx = i + 1
            advice = str(s.get("suggestion", "")).strip().replace("|", "／").replace("\n", " ")
            law = str(s.get("legal_basis", "") or "—").replace("|", "／").replace("\n", " ")
            source = "AI改写" if revisions.get(idx, {}).get("source") == "llm" else "原文+修订说明"
            md_parts.append(f"| {idx} | {advice[:80]} | {law[:40]} | {source} |")

        # 5.4 附录B：AI修订条款全文（未能自动定位到正文的修订，可直接复制替换）
        if unlocated_revisions:
            md_parts.extend([
                "",
                "---",
                "",
                "## 附录B：AI修订条款全文（待人工应用）",
                "",
                "> 以下修订未能自动定位到正文的对应条款（原条款定位失败），",
                "> 请将修订文本直接复制替换原合同中的对应条款。",
                "",
            ])
            for item in unlocated_revisions:
                idx = item["idx"]
                s = item["suggestion"]
                rev = item["revision"]
                law = str(s.get("legal_basis", "") or "").strip()
                md_parts.append(f"### 修订 {idx}")
                if law:
                    md_parts.append(f"*法律依据：{law}*")
                md_parts.append("")
                md_parts.append(rev["revised"])
                md_parts.append("")

        # 5.5 文末声明（专业提示：AI生成文档的使用边界）
        md_parts.extend([
            "",
            "---",
            "",
            "> ⚠️ **重要声明**：本文档由AI辅助生成，仅供参考。正式签署前请交由执业律师审核确认。",
            "",
        ])

        markdown = "\n".join(md_parts)

        # 下载文件名：合同标题 + "_优化后.md"（统一markdown格式）
        # 使用合同标题（用户可见名称）而非内部存储文件名，保证命名语义清晰
        file_name = f"{contract_title}_优化后.md"

        logger.info(
            f"[optimize_contract] 合同{contract_id}优化完成：建议{len(suggestions)}条，"
            f"LLM改写{sum(1 for r in revisions.values() if r['source'] == 'llm')}条，"
            f"全文替换{replaced_count}处"
        )

        return {
            "markdown": markdown,
            "file_name": file_name,
            "suggestion_count": len(suggestions),
            "replaced_count": replaced_count,
        }
