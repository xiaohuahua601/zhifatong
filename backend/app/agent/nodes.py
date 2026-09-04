"""
智法通 - 工作流节点函数模块

定义LangGraph合同审查工作流中的各个节点函数，
每个节点负责一个独立的审查步骤。

V2.0增强内容（参考文档6.2.1节）：
- parse_document: 合同类型识别 + 当事方提取 + 关键信息提取
- split_clauses: 正则模式匹配 + LLM回退
- check_completeness: 标准模板字典 + 关键词匹配
- detect_risk_clauses: 规则引擎 + LLM合并
- check_compliance: RAG法条检索 + LLM冲突判断
- check_consistency: 两两条款比对（限制前20个）
- calculate_risk_score: 文档6.2.1节加权评分公式
- generate_suggestions: 风险条款 + 合规问题建议
- generate_report: needs_manual_review + parties + review_timestamp

保留现有LLM调用作为fallback，在其基础上增加规则引擎和模板比对。
"""

from __future__ import annotations

import re
import httpx
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from app.agent.state import ContractReviewState
from app.config import settings

logger = logging.getLogger(__name__)


# ==================== 自定义异常（P1修复）====================

class OllamaCallError(Exception):
    """Ollama 模型调用异常

    当 _call_ollama 调用 Ollama 服务失败（网络错误、超时、HTTP错误等）时抛出。
    调用方应捕获此异常并使用规则引擎兜底，避免错误字符串混入业务数据。
    """
    pass


# ==================== 标准合同模板（V2.0新增）====================

# 5种合同类型的必备条款清单（参考文档6.2.1节）
# 每种类型包含必备条款及其关键词（用于关键词匹配检测）
CONTRACT_TEMPLATES: Dict[str, dict] = {
    "买卖合同": {
        "required_clauses": [
            {"name": "当事人信息", "keywords": ["甲方", "乙方", "买方", "卖方"]},
            {"name": "标的物", "keywords": ["标的", "货物", "商品", "产品"]},
            {"name": "数量", "keywords": ["数量", "规格"]},
            {"name": "价款", "keywords": ["价款", "金额", "总价", "单价"]},
            {"name": "交付方式", "keywords": ["交付", "交货", "运输", "发货"]},
            {"name": "质量标准", "keywords": ["质量", "标准", "检验"]},
            {"name": "违约责任", "keywords": ["违约", "赔偿", "违约金"]},
            {"name": "争议解决", "keywords": ["争议", "仲裁", "诉讼", "管辖"]},
            {"name": "合同生效", "keywords": ["生效", "签署", "签订"]},
        ],
    },
    "租赁合同": {
        "required_clauses": [
            {"name": "当事人信息", "keywords": ["甲方", "乙方", "出租", "承租"]},
            {"name": "租赁物", "keywords": ["租赁", "标的", "房屋", "设备"]},
            {"name": "租赁期限", "keywords": ["期限", "租期", "月", "年"]},
            {"name": "租金", "keywords": ["租金", "费用", "金额"]},
            {"name": "支付方式", "keywords": ["支付", "付款", "缴纳"]},
            {"name": "维修责任", "keywords": ["维修", "保养", "维护"]},
            {"name": "违约责任", "keywords": ["违约", "赔偿", "违约金"]},
            {"name": "争议解决", "keywords": ["争议", "仲裁", "诉讼"]},
            {"name": "合同生效", "keywords": ["生效", "签署", "签订"]},
        ],
    },
    "劳动合同": {
        "required_clauses": [
            {"name": "当事人信息", "keywords": ["甲方", "乙方", "用人单位", "劳动者"]},
            {"name": "合同期限", "keywords": ["期限", "合同期", "试用期"]},
            {"name": "工作内容", "keywords": ["岗位", "职位", "工作内容", "职责"]},
            {"name": "工作地点", "keywords": ["地点", "工作地"]},
            {"name": "工作时间", "keywords": ["工时", "工作时间", "休息"]},
            {"name": "劳动报酬", "keywords": ["工资", "报酬", "薪资", "薪酬"]},
            {"name": "社会保险", "keywords": ["社保", "保险", "公积金"]},
            {"name": "违约责任", "keywords": ["违约", "赔偿", "违约金"]},
            {"name": "争议解决", "keywords": ["争议", "仲裁", "诉讼"]},
            {"name": "合同生效", "keywords": ["生效", "签署", "签订"]},
        ],
    },
    "服务合同": {
        "required_clauses": [
            {"name": "当事人信息", "keywords": ["甲方", "乙方", "委托方", "受托方"]},
            {"name": "服务内容", "keywords": ["服务", "内容", "范围", "项目"]},
            {"name": "服务期限", "keywords": ["期限", "周期", "时间"]},
            {"name": "服务费用", "keywords": ["费用", "报酬", "金额", "价款"]},
            {"name": "支付方式", "keywords": ["支付", "付款", "结算"]},
            {"name": "验收标准", "keywords": ["验收", "标准", "质量"]},
            {"name": "违约责任", "keywords": ["违约", "赔偿", "违约金"]},
            {"name": "保密条款", "keywords": ["保密", "机密"]},
            {"name": "争议解决", "keywords": ["争议", "仲裁", "诉讼"]},
            {"name": "合同生效", "keywords": ["生效", "签署", "签订"]},
        ],
    },
    "保密合同": {
        "required_clauses": [
            {"name": "当事人信息", "keywords": ["甲方", "乙方", "披露方", "接收方"]},
            {"name": "保密信息范围", "keywords": ["保密", "机密", "信息", "资料"]},
            {"name": "保密义务", "keywords": ["义务", "不得", "禁止"]},
            {"name": "保密期限", "keywords": ["期限", "期间", "年"]},
            {"name": "例外情形", "keywords": ["例外", "除外", "不受"]},
            {"name": "违约责任", "keywords": ["违约", "赔偿", "违约金"]},
            {"name": "返还义务", "keywords": ["返还", "销毁", "归还"]},
            {"name": "争议解决", "keywords": ["争议", "仲裁", "诉讼"]},
            {"name": "合同生效", "keywords": ["生效", "签署", "签订"]},
        ],
    },
    "通用合同": {
        "required_clauses": [
            {"name": "当事人信息", "keywords": ["甲方", "乙方"]},
            {"name": "合同标的", "keywords": ["标的", "内容", "事项"]},
            {"name": "价款/报酬", "keywords": ["价款", "报酬", "金额", "费用"]},
            {"name": "履行期限", "keywords": ["期限", "时间", "周期"]},
            {"name": "违约责任", "keywords": ["违约", "赔偿", "违约金"]},
            {"name": "争议解决", "keywords": ["争议", "仲裁", "诉讼"]},
            {"name": "合同生效", "keywords": ["生效", "签署", "签订"]},
        ],
    },
}

# 合同类型识别关键词（用于parse_document节点的合同类型识别）
CONTRACT_TYPE_KEYWORDS: Dict[str, list] = {
    "买卖合同": ["买卖", "购销", "销售", "购买", "买方", "卖方", "供货"],
    "租赁合同": ["租赁", "出租", "承租", "租金"],
    "劳动合同": ["劳动", "用人单位", "劳动者", "雇佣", "工资", "社保"],
    "服务合同": ["服务", "委托", "受托", "咨询", "技术服务"],
    "保密合同": ["保密", "机密", "不披露", "nda"],
}


# ==================== 风险规则引擎（V2.0新增）====================

# 确定性风险模式规则（参考文档6.2.1节）
# 每条规则包含：模式、风险类型、风险等级(1-4)、风险说明
# risk_level数值：1=low, 2=medium, 3=high, 4=critical
RISK_RULES: List[dict] = [
    {
        "pattern": r"无条件服从|无条件接受",
        "risk_type": "权利不对等",
        "severity": 4,
        "description": "包含'无条件服从/接受'表述，严重权利不对等",
    },
    {
        "pattern": r"随时解除|随时终止",
        "risk_type": "解除权滥用",
        "severity": 3,
        "description": "包含'随时解除/终止'表述，解除权滥用风险",
    },
    {
        "pattern": r"无需承担(任何)?(违约|法律)?责任|不承担任何责任",
        "risk_type": "免责条款",
        "severity": 4,
        "description": "包含免责条款，可能违反法律强制性规定",
    },
    {
        "pattern": r"最终解释权",
        "risk_type": "格式条款违规",
        "severity": 3,
        "description": "包含'最终解释权'条款，违反《民法典》格式条款规定",
    },
    {
        "pattern": r"概不负责|概不退换|概不退款",
        "risk_type": "免责条款",
        "severity": 3,
        "description": "包含'概不负责'等免责表述",
    },
    {
        "pattern": r"不得(提出|主张)?(任何)?异议",
        "risk_type": "权利限制",
        "severity": 3,
        "description": "限制异议权，可能损害一方利益",
    },
    {
        "pattern": r"有权(单方面|单方|自行)(变更|修改|解除|终止)",
        "risk_type": "单方权利过大",
        "severity": 3,
        "description": "单方变更/解除权过大，权利不对等",
    },
    {
        # P1修复：原模式 [超过|高于] 会被正则解释为字符集
        # （匹配"超""过""|""高""于"中任意单字符），与预期不符。
        # 改用非捕获分组 (?:超过|高于) 实现"超过"或"高于"二选一。
        "pattern": r"违约金.*[0-9]+%.*(?:超过|高于)",
        "risk_type": "违约金过高",
        "severity": 2,
        "description": "违约金比例可能过高，超过实际损失30%可能不被支持",
    },
    {
        "pattern": r"自动续约|自动续期|自动延长",
        "risk_type": "自动续约风险",
        "severity": 2,
        "description": "自动续约条款，需注意续约通知义务",
    },
    {
        "pattern": r"不可抗力.*不承担|不可抗力.*免除全部",
        "risk_type": "不可抗力滥用",
        "severity": 2,
        "description": "不可抗力免责范围过大",
    },
    {
        "pattern": r"放弃.*(所有|一切)?(权利|诉权|索赔权)",
        "risk_type": "权利放弃",
        "severity": 4,
        "description": "要求放弃权利，可能无效",
    },
    {
        "pattern": r"(甲方|乙方).*全权负责.*(乙方|甲方).*无权",
        "risk_type": "权利不对等",
        "severity": 3,
        "description": "权利义务明显不对等",
    },
]


# ==================== Ollama调用辅助函数 ====================

async def _call_ollama(prompt: str, temperature: float = 0.3, max_tokens: int = 2000) -> str:
    """调用Ollama生成文本

    Args:
        prompt: 提示词
        temperature: 生成温度
        max_tokens: 最大生成token数

    Returns:
        生成的文本

    Raises:
        OllamaCallError: 当 Ollama 服务调用失败（网络错误、超时、HTTP错误等）时抛出。
            调用方应捕获此异常并使用规则引擎兜底，避免错误字符串混入业务数据。
    """
    try:
        async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT) as client:
            response = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
    except Exception as e:
        # P1修复：原代码返回错误字符串 f"错误：{str(e)}"
        # 这会让错误信息混入业务数据（如 parsed_text、completeness 等字段），
        # 导致下游分析结果被污染。改为抛出 OllamaCallError，
        # 由调用方捕获并使用规则引擎兜底。
        logger.error(f"[nodes._call_ollama] Ollama 调用失败: {e}")
        raise OllamaCallError(f"AI模型调用失败: {str(e)}") from e


def _extract_json(text: str, is_array: bool = True):
    """从LLM响应文本中提取JSON

    Args:
        text: LLM响应文本
        is_array: True提取数组，False提取对象

    Returns:
        解析后的JSON对象，失败返回None
    """
    try:
        if is_array:
            start = text.find("[")
            end = text.rfind("]") + 1
        else:
            start = text.find("{")
            end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except (json.JSONDecodeError, ValueError):
        pass
    return None


# ==================== RAG检索辅助函数（V2.0新增）====================

async def _rag_search_laws(query: str, top_k: int = 3) -> list[dict]:
    """调用RAG检索相关法条

    使用rag_pipeline的retriever进行混合检索，返回相关法条列表。
    检索失败时返回空列表（不影响主流程）。

    Args:
        query: 查询文本（条款内容）
        top_k: 返回结果数量

    Returns:
        法条列表，每个元素含 content/citation/metadata
    """
    try:
        from app.rag.retriever import HybridRetriever
        retriever = HybridRetriever()
        docs = await retriever.retrieve(query, top_k=top_k)
        # 格式化为法条引用结构
        laws = []
        for doc in docs:
            metadata = doc.get("metadata", {})
            laws.append({
                "content": doc.get("content", ""),
                "citation": metadata.get("doc_type", "法律条文") + "：" + doc.get("content", "")[:50],
                "metadata": metadata,
                "score": doc.get("rrf_score", doc.get("score", 0)),
            })
        return laws
    except Exception:
        # RAG检索失败不影响主流程，返回空列表
        return []


# ==================== 条款格式辅助函数（V2.0新增）====================

def _get_clause_text(clause) -> str:
    """从条款中提取文本（兼容list[str]和list[dict]两种格式）

    Args:
        clause: 条款（字符串或字典）

    Returns:
        条款文本
    """
    if isinstance(clause, dict):
        return clause.get("text", clause.get("original_text", ""))
    return str(clause) if clause else ""


def _get_clause_index(clause, default: int = 0) -> int:
    """从条款中提取序号

    Args:
        clause: 条款（字符串或字典）
        default: 默认序号

    Returns:
        条款序号
    """
    if isinstance(clause, dict):
        return clause.get("index", default)
    return default


# ==================== 节点函数 ====================

async def parse_document(state: ContractReviewState) -> dict:
    """文档解析节点（V2.0增强版）

    在原有LLM格式清理基础上，增加：
    1. 合同类型识别（基于关键词匹配：买卖/租赁/劳动/服务/保密）
    2. 当事方信息提取（甲方/乙方正则匹配）
    3. 关键信息提取（金额、期限、签订日期）

    Args:
        state: 当前工作流状态

    Returns:
        状态更新字典
    """
    # 兼容 contract_content 和 contract_text 两种字段名
    content = state.get("contract_text") or state.get("contract_content", "")
    existing_type = state.get("contract_type", "通用合同")

    # ==================== 1. 合同类型识别（关键词匹配）====================
    detected_type = existing_type
    if not existing_type or existing_type == "通用合同":
        # 基于关键词匹配识别合同类型
        type_scores = {}
        for ctype, keywords in CONTRACT_TYPE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in content)
            if score > 0:
                type_scores[ctype] = score
        if type_scores:
            detected_type = max(type_scores, key=type_scores.get)

    # ==================== 2. 当事方信息提取（正则匹配）====================
    parties = []
    # 甲方匹配：甲方/出租方/买方/用人单位/委托方/披露方
    party_a_patterns = [
        r'(甲方|出租方|买方|用人单位|委托方|披露方|卖方)[：:]\s*([^\n，,。；;]{2,50})',
        r'(甲方|出租方|买方|用人单位|委托方|披露方|卖方)[（(]([^)）]{2,50})[)）]',
    ]
    # 乙方匹配：乙方/承租方/卖方/劳动者/受托方/接收方
    party_b_patterns = [
        r'(乙方|承租方|卖方|劳动者|受托方|接收方|买方)[：:]\s*([^\n，,。；;]{2,50})',
        r'(乙方|承租方|卖方|劳动者|受托方|接收方|买方)[（(]([^)）]{2,50})[)）]',
    ]

    for pattern in party_a_patterns:
        match = re.search(pattern, content)
        if match:
            parties.append({"role": "甲方", "name": match.group(2).strip(), "id": ""})
            break
    for pattern in party_b_patterns:
        match = re.search(pattern, content)
        if match:
            parties.append({"role": "乙方", "name": match.group(2).strip(), "id": ""})
            break

    # ==================== 3. 关键信息提取（金额、期限、签订日期）====================
    key_info = {}
    # 金额提取
    amount_match = re.search(r'(金额|价款|总价|租金|报酬|费用)[：:]*\s*(人民币)?\s*([0-9,，.]+)\s*(元|万元|万)?', content)
    if amount_match:
        amount_str = amount_match.group(3).replace(",", "").replace("，", "")
        try:
            amount = float(amount_str)
            if amount_match.group(4) in ("万元", "万"):
                amount *= 10000
            key_info["amount"] = amount
        except ValueError:
            pass

    # 期限提取
    duration_match = re.search(r'(期限|租期|合同期|周期)[：:]*\s*(自|从)?\s*(\d{4}年\d{1,2}月\d{1,2}日)?.*?(至|到|为期)\s*(\d+)?\s*(年|个月|月|天|日)?', content)
    if duration_match:
        if duration_match.group(5) and duration_match.group(6):
            key_info["duration"] = f"{duration_match.group(5)}{duration_match.group(6)}"
        elif duration_match.group(3):
            key_info["duration"] = duration_match.group(3)

    # 签订日期提取
    sign_date_match = re.search(r'(签订日期|签署日期|订立日期|日期)[：:]*\s*(\d{4}年\d{1,2}月\d{1,2}日|\d{4}-\d{1,2}-\d{1,2})', content)
    if sign_date_match:
        key_info["sign_date"] = sign_date_match.group(2)

    # ==================== 4. LLM格式清理（保留原逻辑作为补充）====================
    prompt = f"""请对以下合同文本进行格式清理和标准化处理：
1. 去除多余的空白字符
2. 统一条款编号格式
3. 保留所有原文内容，不要删减

合同文本：
{content[:3000]}

请输出清理后的合同文本："""

    # P1修复：捕获 OllamaCallError，使用原文兜底，避免错误字符串混入 parsed_text
    try:
        parsed_text = await _call_ollama(prompt, temperature=0.1)
        # 防御性处理：若返回空文本，回退到原文
        if not parsed_text or not parsed_text.strip():
            parsed_text = content
    except OllamaCallError as e:
        logger.warning(f"[parse_document] LLM 格式清理失败，使用原文兜底: {e}")
        parsed_text = content

    return {
        # V2.0标准字段
        "contract_text": content,
        "contract_type": detected_type,
        "parties": parties,
        "current_step": "parse_doc",
        # 向后兼容字段
        "contract_content": content,
        "parsed_text": parsed_text,
        # 关键信息
        **key_info,
    }


async def split_clauses(state: ContractReviewState) -> dict:
    """条款分割节点（V2.0增强版）

    在原有LLM拆分基础上，增加：
    1. 正则模式匹配：第X条/第N条/数字编号/中文编号
    2. 正则匹配失败时回退到LLM拆分
    3. 为每个条款添加序号和上下文（返回list[dict]格式）

    Args:
        state: 当前工作流状态

    Returns:
        状态更新字典
    """
    text = state.get("parsed_text") or state.get("contract_text") or state.get("contract_content", "")

    # ==================== 1. 正则模式匹配拆分（V2.0新增）====================
    # 匹配条款编号模式：第X条/第N条/数字编号/中文编号
    clause_pattern = r'(第[一二三四五六七八九十百]+条|第\d+条|\d+\.[\d.]+|[一二三四五六七八九十]+、)'

    # 使用正则分割：保留分隔符
    parts = re.split(f'({clause_pattern})', text)
    clauses_raw = []
    current_clause = ""

    for part in parts:
        if part and re.match(clause_pattern, part):
            # 这是条款编号，开始新条款
            if current_clause.strip():
                clauses_raw.append(current_clause.strip())
            current_clause = part
        elif part:
            current_clause += part

    # 添加最后一个条款
    if current_clause.strip():
        clauses_raw.append(current_clause.strip())

    # 如果正则匹配到的条款太少（<2），回退到LLM拆分
    if len(clauses_raw) < 2:
        clauses_raw = await _llm_split_clauses(text)

    # ==================== 2. 为每个条款添加序号和上下文（V2.0格式）====================
    clause_list = []
    for i, clause_text in enumerate(clauses_raw):
        clause_text = clause_text.strip()
        if clause_text:
            clause_list.append({
                "index": i,
                "text": clause_text,
                "type": None,        # 待分类
                "risk_level": None,  # 待评估
            })

    # 兜底：如果拆分结果为空，将整段文本作为一个条款
    if not clause_list:
        clause_list = [{
            "index": 0,
            "text": text,
            "type": None,
            "risk_level": None,
        }]

    return {
        # V2.0标准字段（list[dict]格式）
        "clauses": clause_list,
        "clause_count": len(clause_list),
        "current_step": "split_clauses",
    }


async def _llm_split_clauses(text: str) -> list[str]:
    """使用LLM拆分条款（fallback）

    当正则匹配失败时，调用LLM进行条款拆分。

    Args:
        text: 合同文本

    Returns:
        条款文本列表
    """
    prompt = f"""请将以下合同文本按条款分割，识别出每个独立的条款。
以JSON数组格式返回，每个元素是一个条款文本。

合同文本：
{text[:3000]}

请以JSON数组格式返回条款列表："""

    # P1修复：捕获 OllamaCallError，使用段落分割兜底
    try:
        result = await _call_ollama(prompt, temperature=0.1)
        clauses = _extract_json(result, is_array=True) or []
    except OllamaCallError as e:
        logger.warning(f"[_llm_split_clauses] LLM 拆分失败，使用段落分割兜底: {e}")
        clauses = []

    if not clauses:
        # LLM 也失败或返回空，按段落分割
        clauses = [c.strip() for c in text.split("\n\n") if c.strip()]
    return clauses


async def check_completeness(state: ContractReviewState) -> dict:
    """完整性检查节点（V2.0增强版）

    在原有LLM检查基础上，增加：
    1. 标准模板字典CONTRACT_TEMPLATES（5种合同类型的必备条款清单）
    2. 使用关键词匹配检查必备条款是否缺失
    3. LLM作为补充判断

    Args:
        state: 当前工作流状态

    Returns:
        状态更新字典
    """
    contract_type = state.get("contract_type", "通用合同")
    clauses = state.get("clauses", [])

    # 合并所有条款文本用于关键词匹配
    clauses_text = " ".join([_get_clause_text(c) for c in clauses])

    # ==================== 1. 标准模板比对（V2.0新增）====================
    # 获取该类型合同的标准必备条款清单
    template = CONTRACT_TEMPLATES.get(contract_type, CONTRACT_TEMPLATES["通用合同"])
    required_clauses = template["required_clauses"]

    # 检查每个必备条款是否在合同中出现（关键词匹配）
    missing = []
    present = []
    for req in required_clauses:
        # 任一关键词匹配即视为存在
        if any(kw in clauses_text for kw in req["keywords"]):
            present.append(req["name"])
        else:
            missing.append(req)

    total_required = len(required_clauses)
    missing_count = len(missing)
    completeness_ratio = 1 - (missing_count / total_required) if total_required > 0 else 1.0
    completeness_score = completeness_ratio * 100

    # 构建V2.0标准结构
    completeness_check = {
        "total_required": total_required,
        "missing_count": missing_count,
        "missing_clauses": missing,
        "present_clauses": present,
        "completeness_ratio": completeness_ratio,
    }

    # ==================== 2. LLM补充判断（保留原逻辑）====================
    missing_names = [m["name"] for m in missing]
    llm_prompt = f"""请检查以下{contract_type}的完整性，判断是否包含必要条款。
已知通过关键词匹配检测到以下可能缺失的条款：{', '.join(missing_names) if missing_names else '无'}

合同条款（前20条）：
{clauses_text[:2000]}

请以JSON格式返回补充判断结果：
{{
    "completeness_score": 0-100的评分,
    "missing_clauses": ["确认缺失的条款名称"],
    "details": "详细说明"
}}"""

    # P1修复：捕获 OllamaCallError，仅使用规则引擎结果兜底
    try:
        llm_result = await _call_ollama(llm_prompt, temperature=0.2)
        llm_completeness = _extract_json(llm_result, is_array=False) or {}
    except OllamaCallError as e:
        logger.warning(f"[check_completeness] LLM 检查失败，仅使用规则引擎结果: {e}")
        llm_completeness = {}

    # 合并LLM结果（LLM可能识别出关键词匹配遗漏的条款）
    llm_missing = llm_completeness.get("missing_clauses", [])
    llm_raw_score = llm_completeness.get("completeness_score")

    # ==================== V6.0.4修复：LLM评分有效性校验 ====================
    # 小参数模型（qwen2.5:1.5b）对JSON输出的遵循度不稳定，可能返回
    # 0或负数等畸形分值，污染规则引擎的合理评分（表现为三维度全0%）。
    # 仅当LLM分处于有效区间(0,100]时才参与综合，否则回退规则引擎分。
    if isinstance(llm_raw_score, (int, float)) and 0 < llm_raw_score <= 100:
        llm_score = float(llm_raw_score)
        # 综合评分：取规则引擎和LLM的较低值（更保守）
        final_score = min(completeness_score, llm_score)
    else:
        # LLM未给分或给畸形分：采用规则引擎（模板关键词比对）结果
        final_score = completeness_score

    # 合并缺失条款
    all_missing_names = list(set(missing_names + llm_missing))

    return {
        # V2.0标准字段
        "completeness_check": completeness_check,
        "current_step": "completeness_check",
        # 向后兼容字段
        "completeness": {
            **completeness_check,
            "details": llm_completeness.get("details", ""),
            "llm_missing": llm_missing,
        },
        "missing_clauses": all_missing_names,
        "completeness_score": final_score,
    }


async def classify_clauses(state: ContractReviewState) -> dict:
    """条款分类节点

    对每个条款进行分类，识别条款类型（如：定义条款、权利义务条款、
    违约条款、保密条款等）。

    Args:
        state: 当前工作流状态

    Returns:
        状态更新字典
    """
    clauses = state.get("clauses", [])

    # 对每个条款分类（简化处理，合并请求）
    clauses_text = "\n".join([
        f"[{_get_clause_index(c, i)}] {_get_clause_text(c)}"
        for i, c in enumerate(clauses[:15])
    ])

    prompt = f"""请对以下合同条款进行分类，识别每个条款的类型。
常见类型：定义条款、标的条款、价格条款、期限条款、权利义务条款、
违约条款、保密条款、不可抗力条款、争议解决条款、其他条款。

合同条款：
{clauses_text[:2000]}

请以JSON数组格式返回：
[{{"index": 1, "category": "条款类型", "is_key": true/false}}]"""

    # P1修复：捕获 OllamaCallError，使用默认分类兜底
    try:
        result = await _call_ollama(prompt, temperature=0.2)
        clause_categories = _extract_json(result, is_array=True) or []
    except OllamaCallError as e:
        logger.warning(f"[classify_clauses] LLM 分类失败，使用默认分类兜底: {e}")
        clause_categories = []

    key_clauses = [c for c in clause_categories if c.get("is_key")]

    # 默认分类（LLM失败时）
    if not clause_categories:
        clause_categories = [
            {"index": _get_clause_index(c, i), "category": "其他条款", "is_key": False}
            for i, c in enumerate(clauses)
        ]

    return {
        "clause_categories": clause_categories,
        "key_clauses": key_clauses,
        "current_step": "classify_clauses",
    }


async def detect_risk_clauses(state: ContractReviewState) -> dict:
    """风险检测节点（V2.0增强版）

    在原有LLM检测基础上，增加：
    1. 规则引擎RISK_RULES（确定性风险模式，如"无条件服从"、"随时解除"等）
    2. 规则引擎检测结果与LLM检测结果合并
    3. 风险等级取最高值

    Args:
        state: 当前工作流状态

    Returns:
        状态更新字典
    """
    clauses = state.get("clauses", [])
    contract_type = state.get("contract_type", "通用合同")

    # ==================== 1. 规则引擎检测（V2.0新增）====================
    rule_risk_clauses = []
    for clause in clauses:
        clause_text = _get_clause_text(clause)
        clause_index = _get_clause_index(clause, 0)
        clause_risks = []

        for rule in RISK_RULES:
            if re.search(rule["pattern"], clause_text):
                clause_risks.append({
                    "rule_type": rule["risk_type"],
                    "severity": rule["severity"],
                    "description": rule["description"],
                    "matched_pattern": rule["pattern"],
                })

        if clause_risks:
            # 取该条款的最高风险等级
            max_severity = max(r["severity"] for r in clause_risks)
            severity_to_level = {1: "low", 2: "medium", 3: "high", 4: "critical"}
            rule_risk_clauses.append({
                "clause_index": clause_index,
                "original_text": clause_text,
                "risk_type": "；".join(set(r["rule_type"] for r in clause_risks)),
                "risk_level": severity_to_level[max_severity],
                "risk_score": max_severity / 4.0,
                "risk_description": "；".join(r["description"] for r in clause_risks),
                "source": "rule_engine",
            })

    # ==================== 2. LLM语义检测（保留原逻辑）====================
    clauses_text = "\n".join([
        f"[{_get_clause_index(c, i)}] {_get_clause_text(c)}"
        for i, c in enumerate(clauses[:15])
    ])

    prompt = f"""请检测以下{contract_type}条款中的风险，包括但不限于：
1. 权利义务不对等
2. 模糊不清的表述
3. 可能违反法律强制性规定的条款
4. 损害一方利益的条款
5. 缺乏约束力的条款

合同条款：
{clauses_text[:2000]}

请以JSON数组格式返回风险条款：
[{{"clause_index": 1, "original_text": "原文", "risk_type": "风险类型", "risk_level": "low/medium/high/critical", "risk_score": 0-1, "risk_description": "风险说明"}}]"""

    # P1修复：捕获 OllamaCallError，仅使用规则引擎结果兜底
    try:
        result = await _call_ollama(prompt, temperature=0.3)
        llm_risk_clauses = _extract_json(result, is_array=True) or []
        # 标记来源
        for rc in llm_risk_clauses:
            rc["source"] = "llm"
    except OllamaCallError as e:
        logger.warning(f"[detect_risk_clauses] LLM 检测失败，仅使用规则引擎结果: {e}")
        llm_risk_clauses = []

    # ==================== 3. 合并规则引擎和LLM检测结果====================
    # 按 clause_index 合并，同一条款的风险取最高等级
    merged = {}
    level_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    level_to_severity = {"low": 1, "medium": 2, "high": 3, "critical": 4}

    for rc in rule_risk_clauses + llm_risk_clauses:
        idx = rc.get("clause_index", 0)
        if idx not in merged:
            merged[idx] = rc
        else:
            existing = merged[idx]
            # 取最高风险等级
            existing_level = existing.get("risk_level", "low")
            new_level = rc.get("risk_level", "low")
            if level_order.get(new_level, 0) > level_order.get(existing_level, 0):
                # 合并描述
                merged_desc = existing.get("risk_description", "") + "；" + rc.get("risk_description", "")
                merged[idx] = {**rc, "risk_description": merged_desc}

    risk_clauses = list(merged.values())

    # 确定最高风险等级
    max_risk_level = "low"
    for rc in risk_clauses:
        level = rc.get("risk_level", "low")
        if level_order.get(level, 0) > level_order.get(max_risk_level, 0):
            max_risk_level = level

    return {
        # V2.0标准字段
        "risk_clauses": risk_clauses,
        "current_step": "risk_detect",
        # 向后兼容字段
        "risk_clause_count": len(risk_clauses),
        "max_risk_level": max_risk_level,
    }


async def check_compliance(state: ContractReviewState) -> dict:
    """合规性检查节点（V2.0增强版）

    在原有LLM检查基础上，增加：
    1. 调用RAG检索相关法条（使用rag_pipeline的retriever）
    2. LLM判断条款是否与法条冲突
    3. 记录冲突法条引用

    Args:
        state: 当前工作流状态

    Returns:
        状态更新字典
    """
    contract_type = state.get("contract_type", "通用合同")
    clauses = state.get("clauses", [])

    # ==================== 1. RAG检索相关法条 + LLM冲突判断（V2.0新增）====================
    compliance_issues = []
    # 限制检查前15个条款，避免过多RAG调用
    for clause in clauses[:15]:
        clause_text = _get_clause_text(clause)
        clause_index = _get_clause_index(clause, 0)
        if not clause_text or len(clause_text) < 5:
            continue

        # 调用RAG检索相关法条
        relevant_laws = await _rag_search_laws(clause_text, top_k=3)

        # LLM判断条款是否与每条法条冲突
        for law in relevant_laws:
            conflict = await _llm_check_conflict(clause_text, law["content"])
            if conflict.get("has_conflict"):
                compliance_issues.append({
                    "clause_index": clause_index,
                    "clause_text": clause_text,
                    "conflicting_law": law["citation"],
                    "conflict_description": conflict.get("description", ""),
                    "severity": conflict.get("severity", "medium"),
                })

    # ==================== 2. LLM整体合规性检查（保留原逻辑作为补充）====================
    clauses_text = "\n".join([_get_clause_text(c) for c in clauses[:15]])
    prompt = f"""请对以下{contract_type}进行合规性检查，判断是否违反相关法律法规。
重点关注：
1. 《民法典》合同编的相关规定
2. 《消费者权益保护法》（如适用）
3. 《劳动法》/《劳动合同法》（如适用）
4. 其他相关法律法规

合同条款：
{clauses_text[:2000]}

请以JSON格式返回：
{{
    "compliance_score": 0-100的评分,
    "violation_clauses": [{{"clause_index": 1, "violation": "违规描述", "law_reference": "法律依据"}}],
    "details": "详细说明"
}}"""

    # P1修复：捕获 OllamaCallError，仅使用RAG检测结果兜底
    try:
        result = await _call_ollama(prompt, temperature=0.2)
        llm_compliance = _extract_json(result, is_array=False) or {}
    except OllamaCallError as e:
        logger.warning(f"[check_compliance] LLM 整体检查失败，仅使用RAG检测结果: {e}")
        llm_compliance = {}

    violation_clauses = llm_compliance.get("violation_clauses", [])
    # ==================== V6.0.4修复：LLM评分有效性校验 ====================
    # 小模型可能返回0等畸形分（JSON遵循度低），无效时回退基准分70，
    # 再按问题数量扣减，避免合规分被污染为0%
    llm_raw_score = llm_compliance.get("compliance_score")
    if isinstance(llm_raw_score, (int, float)) and 0 < llm_raw_score <= 100:
        compliance_score = float(llm_raw_score)
    else:
        compliance_score = 70.0

    # 将LLM检测的违规条款也加入compliance_issues（统一格式）
    for vc in violation_clauses:
        compliance_issues.append({
            "clause_index": vc.get("clause_index", 0),
            "clause_text": vc.get("violation", ""),
            "conflicting_law": vc.get("law_reference", ""),
            "conflict_description": vc.get("violation", ""),
            "severity": "medium",
            "source": "llm",
        })

    # ==================== V6.0.4优化：合规评分非线性扣减 ====================
    # 此前每条问题扣5分且无下限：问题数≥14即归0，多问题合同的合规分
    # 直接显示0%（与"综合评分非0但维度全0"的观感缺陷叠加）。
    # 改为每条扣3分+保底20分：既保持问题数量与分数的负相关区分度，
    # 又确保"存在大量问题"体现为极低分（20%）而非无意义的全0。
    if compliance_issues:
        compliance_score = max(20.0, compliance_score - len(compliance_issues) * 3)

    return {
        # V2.0标准字段
        "compliance_issues": compliance_issues,
        "current_step": "compliance_check",
        # 向后兼容字段
        "compliance": {
            **llm_compliance,
            "compliance_issues_count": len(compliance_issues),
        },
        "violation_clauses": violation_clauses,
        "compliance_score": compliance_score,
    }


async def _llm_check_conflict(clause_text: str, law_content: str) -> dict:
    """使用LLM判断条款是否与法条冲突

    Args:
        clause_text: 合同条款文本
        law_content: 法条内容

    Returns:
        冲突判断结果 {"has_conflict": bool, "description": str, "severity": str}
    """
    prompt = f"""请判断以下合同条款是否与法条存在冲突。

合同条款：{clause_text[:500]}

法条内容：{law_content[:500]}

请以JSON格式返回：
{{
    "has_conflict": true/false,
    "description": "冲突描述（如有）",
    "severity": "low/medium/high/critical"
}}"""

    # P1修复：捕获 OllamaCallError，返回"无冲突"兜底（避免错误字符串污染）
    try:
        result = await _call_ollama(prompt, temperature=0.2, max_tokens=500)
        return _extract_json(result, is_array=False) or {"has_conflict": False}
    except OllamaCallError as e:
        logger.warning(f"[_llm_check_conflict] LLM 冲突判断失败，按无冲突处理: {e}")
        return {"has_conflict": False}


async def check_consistency(state: ContractReviewState) -> dict:
    """一致性检查节点（V2.0增强版）

    在原有LLM检查基础上，增加：
    1. 实现两两条款比对逻辑（for i...for j...）
    2. 为避免过多LLM调用，限制最多检查前20个条款的两两组合
    3. LLM判断条款间是否存在矛盾

    Args:
        state: 当前工作流状态

    Returns:
        状态更新字典
    """
    clauses = state.get("clauses", [])

    # ==================== 1. 两两条款比对（V2.0新增）====================
    # 限制最多检查前20个条款的两两组合，避免过多LLM调用
    check_clauses = clauses[:20]
    consistency_issues = []

    n = len(check_clauses)
    for i in range(n):
        for j in range(i + 1, n):
            clause_a = check_clauses[i]
            clause_b = check_clauses[j]
            text_a = _get_clause_text(clause_a)
            text_b = _get_clause_text(clause_b)
            idx_a = _get_clause_index(clause_a, i)
            idx_b = _get_clause_index(clause_b, j)

            # 跳过过短条款
            if len(text_a) < 10 or len(text_b) < 10:
                continue

            conflict = await _llm_check_consistency(text_a, text_b)
            if conflict.get("has_conflict"):
                consistency_issues.append({
                    "clause_a": idx_a,
                    "clause_b": idx_b,
                    "conflict_description": conflict.get("description", ""),
                    "severity": conflict.get("severity", "medium"),
                })

    # ==================== 2. LLM整体一致性检查（保留原逻辑作为补充）====================
    clauses_text = "\n".join([
        f"[{_get_clause_index(c, i)}] {_get_clause_text(c)}"
        for i, c in enumerate(clauses[:15])
    ])

    prompt = f"""请检查以下合同条款之间是否存在矛盾或不一致的地方。
重点关注：
1. 条款间的逻辑矛盾
2. 金额/日期/期限的不一致
3. 权利义务的冲突
4. 定义与使用的不一致

合同条款：
{clauses_text[:2000]}

请以JSON格式返回：
{{
    "consistency_score": 0-100的评分,
    "contradiction_pairs": [{{"clause_a": "条款1索引", "clause_b": "条款2索引", "description": "矛盾描述"}}],
    "details": "详细说明"
}}"""

    # P1修复：捕获 OllamaCallError，仅使用两两比对结果兜底
    try:
        result = await _call_ollama(prompt, temperature=0.2)
        llm_consistency = _extract_json(result, is_array=False) or {}
    except OllamaCallError as e:
        logger.warning(f"[check_consistency] LLM 整体检查失败，仅使用两两比对结果: {e}")
        llm_consistency = {}

    contradiction_pairs = llm_consistency.get("contradiction_pairs", [])
    # ==================== V6.0.4修复：LLM评分有效性校验 ====================
    # 同上：小模型畸形分回退基准分80，避免一致性分被污染为0%
    llm_raw_score = llm_consistency.get("consistency_score")
    if isinstance(llm_raw_score, (int, float)) and 0 < llm_raw_score <= 100:
        consistency_score = float(llm_raw_score)
    else:
        consistency_score = 80.0

    # 将LLM检测的矛盾对也加入consistency_issues（统一格式）
    for cp in contradiction_pairs:
        consistency_issues.append({
            "clause_a": cp.get("clause_a", 0),
            "clause_b": cp.get("clause_b", 0),
            "conflict_description": cp.get("description", ""),
            "severity": "medium",
            "source": "llm",
        })

    # ==================== V6.0.4优化：一致性评分非线性扣减 ====================
    # 同合规评分：每条扣3分+保底20分，避免多矛盾合同一致性归0%
    if consistency_issues:
        consistency_score = max(20.0, consistency_score - len(consistency_issues) * 3)

    return {
        # V2.0标准字段
        "consistency_issues": consistency_issues,
        "current_step": "consistency_check",
        # 向后兼容字段
        "consistency": {
            **llm_consistency,
            "consistency_issues_count": len(consistency_issues),
        },
        "contradiction_pairs": contradiction_pairs,
        "consistency_score": consistency_score,
    }


async def _llm_check_consistency(text_a: str, text_b: str) -> dict:
    """使用LLM判断两个条款是否矛盾

    Args:
        text_a: 条款A文本
        text_b: 条款B文本

    Returns:
        矛盾判断结果 {"has_conflict": bool, "description": str, "severity": str}
    """
    prompt = f"""请判断以下两个合同条款是否存在矛盾或不一致。

条款A：{text_a[:300]}

条款B：{text_b[:300]}

请以JSON格式返回：
{{
    "has_conflict": true/false,
    "description": "矛盾描述（如有）",
    "severity": "low/medium/high"
}}"""

    # P1修复：捕获 OllamaCallError，返回"无矛盾"兜底（避免错误字符串污染）
    try:
        result = await _call_ollama(prompt, temperature=0.2, max_tokens=300)
        return _extract_json(result, is_array=False) or {"has_conflict": False}
    except OllamaCallError as e:
        logger.warning(f"[_llm_check_consistency] LLM 矛盾判断失败，按无矛盾处理: {e}")
        return {"has_conflict": False}


# ==================== 多Agent对抗式审查节点（V4.0新增，参考文档4.3节）====================

async def adverse_agent_attack(state: ContractReviewState) -> dict:
    """反方Agent审查节点（V4.0新增，参考文档4.3.5节）

    三阶段处理：
    1. 主审Agent结论汇总：将risk_clauses + compliance_issues + consistency_issues
       汇总为primary_risks（中立专业审查结论）
    2. 复核Agent规则复检：基于RISK_RULES对主审结论进行二次校验，
       标记approved/disputed/missed
    3. 反方Agent弱势方质疑：站在合同弱势方立场，对每一条款提出反对意见

    本节点是"多Agent对抗式审查"的核心，通过引入弱势方立场，
    降低风险漏报率（参考文档P1-01需求：风险召回率较单Agent提升≥10%）。

    Args:
        state: 当前工作流状态（已包含risk_clauses/compliance_issues等主审结论）

    Returns:
        状态更新字典，包含 primary_risks/review_check/adverse_opinions
    """
    contract_type = state.get("contract_type", "通用合同")
    clauses = state.get("clauses", [])
    parties = state.get("parties", [])
    risk_clauses = state.get("risk_clauses", [])
    compliance_issues = state.get("compliance_issues", [])

    # ==================== 1. 主审Agent结论汇总 ====================
    # 将风险条款与合规问题合并为统一的主审风险清单
    primary_risks = []
    for rc in risk_clauses:
        primary_risks.append({
            "clause_index": rc.get("clause_index", 0),
            "clause_text": rc.get("original_text", ""),
            "risk_type": rc.get("risk_type", ""),
            "risk_level": rc.get("risk_level", "low"),
            "description": rc.get("risk_description", ""),
            "legal_basis": rc.get("legal_basis", ""),
            "source": "primary_agent",
        })
    for ci in compliance_issues:
        primary_risks.append({
            "clause_index": ci.get("clause_index", 0),
            "clause_text": ci.get("clause_text", ""),
            "risk_type": "合规问题",
            "risk_level": ci.get("severity", "medium"),
            "description": ci.get("conflict_description", ""),
            "legal_basis": ci.get("conflicting_law", ""),
            "source": "primary_agent",
        })

    # ==================== 2. 复核Agent规则复检 ====================
    # 基于RISK_RULES对主审结论进行二次校验
    approved = []   # 复核通过的风险点
    disputed = []   # 复核有异议的风险点
    missed = []     # 主审遗漏的风险点

    # 检查主审识别的每个风险是否被规则引擎确认
    for pr in primary_risks:
        clause_text = pr.get("clause_text", "")
        rule_matched = False
        for rule in RISK_RULES:
            if re.search(rule["pattern"], clause_text):
                rule_matched = True
                break
        if rule_matched:
            approved.append(pr)
        else:
            # 规则引擎未匹配但LLM识别的风险，标记为待争议（保留但标记）
            disputed.append(pr)

    # 检查规则引擎是否识别出主审遗漏的风险
    identified_indices = {pr.get("clause_index") for pr in primary_risks}
    for clause in clauses:
        clause_text = _get_clause_text(clause)
        clause_index = _get_clause_index(clause, 0)
        if clause_index in identified_indices:
            continue
        for rule in RISK_RULES:
            if re.search(rule["pattern"], clause_text):
                missed.append({
                    "clause_index": clause_index,
                    "clause_text": clause_text,
                    "risk_type": rule["risk_type"],
                    "risk_level": {1: "low", 2: "medium", 3: "high", 4: "critical"}[rule["severity"]],
                    "description": rule["description"],
                    "source": "review_agent_rule_engine",
                })
                break

    review_check = {
        "approved": approved,
        "disputed": disputed,
        "missed": missed,
        "approved_count": len(approved),
        "disputed_count": len(disputed),
        "missed_count": len(missed),
    }

    # ==================== 3. 反方Agent弱势方质疑（LLM驱动）====================
    # 站在合同弱势方立场，对每一条款提出质疑
    clauses_text = "\n".join([
        f"[{_get_clause_index(c, i)}] {_get_clause_text(c)}"
        for i, c in enumerate(clauses[:15])
    ])
    parties_str = "、".join([f"{p.get('role', '')}{p.get('name', '')}" for p in parties]) if parties else "甲方、乙方"

    adverse_prompt = f"""你是合同弱势方的代理律师，立场是最大化保护弱势方权益。
请站在弱势方立场，对以下{contract_type}的每一条款提出质疑。

合同类型：{contract_type}
当事方：{parties_str}
条款列表：
{clauses_text[:2000]}

质疑维度：
1. 权利义务是否对等（如单方解除权、单方调价权）
2. 是否存在免除强势方责任的格式条款
3. 违约责任是否对等
4. 争议解决条款是否公平
5. 隐性风险（自动续期、单方变更、不可抗力定义过窄等）

请以JSON数组格式返回反对意见（最多5条最严重的）：
[{{"clause_index": 0, "opposition": "反对意见", "weak_party_impact": "对弱势方的影响", "legal_basis": "法律依据", "demanded_revision": "要求修改为"}}]"""

    # 捕获OllamaCallError，使用规则兜底
    # V4.0.2修复：LLM可能返回无意义字面值（如直接照搬prompt示例的"反对意见"），
    # 需检测内容质量，质量过低时同样使用规则兜底
    adverse_opinions = []
    try:
        result = await _call_ollama(adverse_prompt, temperature=0.4, max_tokens=1500)
        parsed_opinions = _extract_json(result, is_array=True) or []
        # 质量校验：过滤掉opposition字段为空或无意义字面值的条目
        # 无意义字面值指：直接照搬prompt示例的"反对意见"等模板词
        invalid_literals = {"反对意见", "无", "暂无", "", "null"}
        for ao in parsed_opinions:
            opp_text = str(ao.get("opposition", "")).strip()
            if opp_text and opp_text not in invalid_literals and len(opp_text) >= 5:
                adverse_opinions.append(ao)
        if len(adverse_opinions) < len(parsed_opinions):
            logger.warning(
                f"[adverse_agent_attack] LLM返回的反对意见中{len(parsed_opinions) - len(adverse_opinions)}条内容无效，已过滤"
            )
    except OllamaCallError as e:
        logger.warning(f"[adverse_agent_attack] 反方Agent LLM质疑失败，使用规则兜底: {e}")
        adverse_opinions = []

    # 规则兜底：LLM失败或返回内容无效时，基于risk_clauses生成基础反对意见
    # 兜底内容包含具体风险类型，比LLM无意义字面值更有参考价值
    if not adverse_opinions and risk_clauses:
        for rc in risk_clauses[:5]:
            adverse_opinions.append({
                "clause_index": rc.get("clause_index", 0),
                "opposition": f"该条款存在{rc.get('risk_type', '风险')}，损害弱势方权益",
                "weak_party_impact": rc.get("risk_description", "权利义务不对等"),
                "legal_basis": "建议引用相关法律条款",
                "demanded_revision": "建议修改为权利义务对等的表述",
            })

    return {
        "primary_risks": primary_risks,
        "review_check": review_check,
        "adverse_opinions": adverse_opinions,
        "current_step": "adverse_attack",
    }


async def debate_round(state: ContractReviewState) -> dict:
    """对抗辩论节点（V4.0新增，参考文档4.3.5节）

    主持主审Agent与反方Agent的对抗辩论：
    1. 主审必须逐条回应反方的质疑
    2. 双方达成共识的条款进入最终结论
    3. 未达成共识的条款标记为"需仲裁"，计入unresolved_issues

    辩论记录完整留痕（debate_log），实现"可审计、可回溯"（参考文档P1-01需求）。

    Args:
        state: 当前工作流状态（已包含primary_risks和adverse_opinions）

    Returns:
        状态更新字典，包含 debate_log/unresolved_issues
    """
    primary_risks = state.get("primary_risks", [])
    adverse_opinions = state.get("adverse_opinions", [])
    review_check = state.get("review_check", {})

    # 如果没有反方意见，无需辩论
    if not adverse_opinions:
        return {
            "debate_log": [],
            "unresolved_issues": [],
            "current_step": "debate",
        }

    # 构建主审立场与反方立场的摘要
    primary_summary = "\n".join([
        f"[条款{pr.get('clause_index', 0)}] {pr.get('risk_type', '')}: {pr.get('description', '')}"
        for pr in primary_risks[:8]
    ])
    adverse_summary = "\n".join([
        f"[条款{ao.get('clause_index', 0)}] {ao.get('opposition', '')}（要求：{ao.get('demanded_revision', '')}）"
        for ao in adverse_opinions[:8]
    ])

    debate_prompt = f"""你是合同审查仲裁员，主持主审Agent与反方Agent的辩论。

主审立场（中立专业审查结论）：
{primary_summary[:1500]}

反方立场（弱势方代理律师质疑）：
{adverse_summary[:1500]}

辩论规则：
1. 主审必须逐条回应反方的质疑
2. 主审可以坚持原判、调整风险等级或撤销风险点
3. 双方达成共识的条款进入最终结论
4. 未达成共识的条款标记为"需仲裁"

请以JSON格式返回辩论结果：
{{
    "debate_log": [
        {{"round": 1, "issue": "争议条款", "primary_response": "主审回应", "adverse_response": "反方回应", "status": "consensus"}}
    ],
    "unresolved": [
        {{"clause_index": 0, "issue": "未解决问题", "primary_position": "主审立场", "adverse_position": "反方立场"}}
    ]
}}"""

    # 捕获OllamaCallError，使用规则兜底
    try:
        result = await _call_ollama(debate_prompt, temperature=0.3, max_tokens=1500)
        debate_result = _extract_json(result, is_array=False) or {}
    except OllamaCallError as e:
        logger.warning(f"[debate_round] 辩论LLM失败，使用规则兜底: {e}")
        debate_result = {}

    debate_log = debate_result.get("debate_log", [])
    unresolved_issues = debate_result.get("unresolved", [])

    # 规则兜底：LLM失败时，将所有反方意见标记为未解决
    if not debate_log and adverse_opinions:
        for i, ao in enumerate(adverse_opinions[:5]):
            debate_log.append({
                "round": i + 1,
                "issue": ao.get("opposition", ""),
                "primary_response": "维持原审查结论",
                "adverse_response": ao.get("demanded_revision", ""),
                "status": "unresolved",
            })
            unresolved_issues.append({
                "clause_index": ao.get("clause_index", 0),
                "issue": ao.get("opposition", ""),
                "primary_position": "维持原判",
                "adverse_position": ao.get("demanded_revision", ""),
            })

    return {
        "debate_log": debate_log,
        "unresolved_issues": unresolved_issues,
        "current_step": "debate",
    }


async def calculate_risk_score(state: ContractReviewState) -> dict:
    """风险评分节点（V2.0增强版）

    使用文档6.2.1节的加权评分公式：
    - 风险条款: sum(risk_level * 10)
    - 合规问题: len(compliance_issues) * 15
    - 一致性问题: len(consistency_issues) * 8
    - 完整性: (1 - completeness_ratio) * 20
    - 上限100

    risk_score越高表示风险越大（与overall_score相反）。

    Args:
        state: 当前工作流状态

    Returns:
        状态更新字典
    """
    risk_clauses = state.get("risk_clauses", [])
    compliance_issues = state.get("compliance_issues", [])
    consistency_issues = state.get("consistency_issues", [])
    completeness_check = state.get("completeness_check", {})

    # ==================== 1. 加权评分（文档6.2.1节公式）====================
    # 风险条款评分：sum(risk_level * 10)
    # risk_level映射为数值：low=1, medium=2, high=3, critical=4
    level_to_severity = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    risk_clauses_score = sum(
        level_to_severity.get(rc.get("risk_level", "low"), 1) * 10
        for rc in risk_clauses
    )

    # 合规问题评分：len(compliance_issues) * 15
    compliance_score = len(compliance_issues) * 15

    # 一致性问题评分：len(consistency_issues) * 8
    consistency_score_val = len(consistency_issues) * 8

    # 完整性评分：(1 - completeness_ratio) * 20
    completeness_ratio = completeness_check.get("completeness_ratio", 1.0)
    completeness_score_val = (1 - completeness_ratio) * 20

    # V4.0新增：未达成共识问题评分（对抗辩论后仍存分歧的条款，每条加5分）
    unresolved_issues = state.get("unresolved_issues", [])
    unresolved_score = len(unresolved_issues) * 5

    # 总风险评分（上限100）
    risk_score = risk_clauses_score + compliance_score + consistency_score_val + completeness_score_val + unresolved_score
    risk_score = min(risk_score, 100)

    # ==================== 2. 确定风险等级====================
    # risk_score越高越危险
    if risk_score >= 80:
        risk_level = "critical"
    elif risk_score >= 60:
        risk_level = "high"
    elif risk_score >= 40:
        risk_level = "medium"
    elif risk_score >= 20:
        risk_level = "low"
    else:
        risk_level = "low"

    # ==================== 3. 综合安全评分（V6.0.5修复）====================
    # 此前：overall_score = 100 - risk_score。风险分四项加和极易封顶100，
    # 导致综合评分强制归0，而完整性/合规性/一致性维度分却非0——
    # "综合0分但维度非0%"逻辑上自相矛盾，用户无法理解。
    # 修复：综合评分 = 维度健康分与风险安全分的加权融合：
    #   维度健康分 = 完整性×0.3 + 合规性×0.4 + 一致性×0.3（质量维度）
    #   风险安全分 = 100 - risk_score（风险维度）
    #   综合评分 = 维度健康分×0.5 + 风险安全分×0.5
    # 性质保证：
    #   1) 维度任一非0 → 综合非0（消除"维度非0但综合0"的矛盾）
    #   2) 风险越高综合越低（单调性保持，高风险合同仍得极低分）
    #   3) 全维度满分且无风险 → 综合100（上限保持）
    # 风险等级risk_level仍由risk_score独立判定（critical/high...），
    # 与综合评分解耦，确保风险警示语义不受影响。
    # 维度分取自各检查节点产出的顶层评分（0-100），畸形值防御为0
    def _safe_dim(v) -> float:
        try:
            v = float(v)
            return v if 0 <= v <= 100 else 0.0
        except (TypeError, ValueError):
            return 0.0

    completeness_dim = _safe_dim(state.get("completeness_score", 0))
    compliance_dim = _safe_dim(state.get("compliance_score", 0))
    consistency_dim = _safe_dim(state.get("consistency_score", 0))

    dimension_health = (
        completeness_dim * 0.3 + compliance_dim * 0.4 + consistency_dim * 0.3
    )
    risk_safety = 100 - risk_score
    overall_score = dimension_health * 0.5 + risk_safety * 0.5
    overall_score = max(0.0, min(100.0, overall_score))

    return {
        # V2.0标准字段
        "risk_score": round(risk_score, 1),
        "current_step": "risk_score",
        # 向后兼容字段
        "overall_score": round(overall_score, 1),
        "risk_level": risk_level,
    }


async def generate_suggestions(state: ContractReviewState) -> dict:
    """修改建议生成节点（V2.0增强版）

    在原有风险条款建议基础上，增加：
    1. 为风险条款生成修改建议
    2. 为合规问题生成修改建议（文档6.2.1节要求）

    Args:
        state: 当前工作流状态

    Returns:
        状态更新字典
    """
    risk_clauses = state.get("risk_clauses", [])
    compliance_issues = state.get("compliance_issues", [])
    missing_clauses = state.get("missing_clauses", [])
    contract_type = state.get("contract_type", "通用合同")

    suggestions_list = []

    # ==================== 1. 为风险条款生成修改建议====================
    if risk_clauses:
        risk_text = "\n".join([
            f"[{rc.get('clause_index', i+1)}] {rc.get('original_text', '')} - 风险：{rc.get('risk_description', '')}"
            for i, rc in enumerate(risk_clauses[:10])
        ])

        prompt = f"""请为以下{contract_type}中的风险条款提供具体的修改建议。

风险条款：
{risk_text[:2000]}

缺失条款：{', '.join(missing_clauses) if missing_clauses else '无'}

请以JSON数组格式返回修改建议：
[{{"clause_index": 1, "original_text": "原文", "suggestion": "修改建议", "legal_basis": "法律依据", "issue_type": "risk_clause"}}]"""

        # P1修复：捕获 OllamaCallError，跳过LLM建议（后续兜底逻辑会处理）
        try:
            result = await _call_ollama(prompt, temperature=0.3)
            risk_suggestions = _extract_json(result, is_array=True) or []
            # 标记建议类型
            for s in risk_suggestions:
                s.setdefault("issue_type", "risk_clause")

            # ==================== V6.0.5修复：建议有效性后处理 ====================
            # 小模型（qwen2.5:1.5b）JSON遵循度低，可能把"原条款文本"直接填入
            # suggestion字段（建议=原文，对用户毫无价值）。校验规则：
            #   1) suggestion与original_text相同或为其子串 → 判定为无效建议
            #   2) suggestion过短（<10字符）→ 无效
            # 无效时用风险条款识别阶段已生成的建议（rc.suggestion）替换
            def _is_invalid_suggestion(s_item: dict, compare_orig: str = "") -> bool:
                sug = str(s_item.get("suggestion", "") or "").strip()
                orig = compare_orig or str(s_item.get("original_text", "") or "").strip()
                if len(sug) < 10:
                    return True
                if orig and (sug == orig or sug in orig or orig in sug):
                    return True
                return False

            # 建立clause_index到风险条款的映射（用于无效建议的规则化替换）
            rc_map = {
                rc.get("clause_index"): rc
                for rc in risk_clauses
            }
            # 无效建议的修复结果（无风险误报条目直接剔除，不保留在列表）
            valid_risk_suggestions = []
            replaced = 0
            for s in risk_suggestions:
                # 比对基准：建议自身的original_text，为空时回退风险条款的原文
                # （LLM可能漏填s.original_text，导致原文比对失效而漏判）
                rc = rc_map.get(s.get("clause_index"), {})
                compare_orig = str(s.get("original_text") or "").strip() or str(rc.get("original_text") or "").strip()
                if not _is_invalid_suggestion(s, compare_orig):
                    valid_risk_suggestions.append(s)
                    continue
                # 误报过滤：风险描述显示"无风险/表述清晰"的条款是LLM误报，
                # 为其生成"存在风险：表述清晰无风险"式建议自相矛盾，直接剔除
                risk_desc_raw = (rc.get("risk_description") or rc.get("risk_type") or "").strip()
                if ("无风险" in risk_desc_raw) or ("清晰" in risk_desc_raw and "风险" not in risk_desc_raw):
                    replaced += 1
                    continue
                # 优先用风险条款识别阶段已生成的建议（若LLM输出过）
                fallback_sug = (rc.get("suggestion") or "").strip()
                if not fallback_sug:
                    # 无现成建议时基于风险字段规则化组装：
                    # 明确指出风险类型/等级/描述，给出可操作的修订指引
                    level_cn = {"low": "低", "medium": "中", "high": "高", "critical": "严重"}.get(
                        rc.get("risk_level", "medium"), "中"
                    )
                    risk_desc = risk_desc_raw or "存在法律风险"
                    fallback_sug = (
                        f"该条款存在{level_cn}风险（{rc.get('risk_type', '法律风险')}）：{risk_desc}。"
                        f"建议修订或删除相关表述，使之符合法律规定；必要时与对方协商补充对等约束条款。"
                    )
                s["suggestion"] = fallback_sug
                # 同时补全legal_basis（若LLM也漏填）
                if not (s.get("legal_basis") or "").strip() and rc.get("legal_basis"):
                    s["legal_basis"] = rc["legal_basis"]
                replaced += 1
                valid_risk_suggestions.append(s)
            if replaced:
                logger.info(f"[generate_suggestions] {replaced}条无效建议已规则化修复/剔除")
            risk_suggestions = valid_risk_suggestions

            suggestions_list.extend(risk_suggestions)
        except OllamaCallError as e:
            logger.warning(f"[generate_suggestions] 风险条款建议生成失败，跳过: {e}")

    # ==================== 2. 为合规问题生成修改建议（V2.0新增）====================
    if compliance_issues:
        compliance_text = "\n".join([
            f"[条款{ci.get('clause_index', i+1)}] {ci.get('clause_text', '')} - 冲突法条：{ci.get('conflicting_law', '')} - 问题描述：{ci.get('conflict_description', '')}"
            for i, ci in enumerate(compliance_issues[:10])
        ])

        prompt = f"""请为以下合规问题提供具体的修改建议，使条款符合相关法律规定。

合规问题：
{compliance_text[:2000]}

请以JSON数组格式返回修改建议：
[{{"clause_index": 1, "original_text": "原文", "suggestion": "修改建议", "legal_basis": "法律依据", "issue_type": "compliance_issue"}}]"""

        # P1修复：捕获 OllamaCallError，跳过LLM建议（后续兜底逻辑会处理）
        try:
            result = await _call_ollama(prompt, temperature=0.3)
            compliance_suggestions = _extract_json(result, is_array=True) or []
            for s in compliance_suggestions:
                s.setdefault("issue_type", "compliance_issue")

            # ==================== V6.0.5修复：合规建议有效性后处理 ====================
            # 同风险建议段：小模型可能把原文/短文本填入suggestion字段。
            # 校验基准为合规问题自身的clause_text；无效时用冲突法条+问题描述规则化组装
            ci_map = {ci.get("clause_index"): ci for ci in compliance_issues}
            valid_compliance_suggestions = []
            for s in compliance_suggestions:
                ci = ci_map.get(s.get("clause_index"), {})
                compare_orig = str(s.get("original_text") or "").strip() or str(ci.get("clause_text") or "").strip()
                sug = str(s.get("suggestion", "") or "").strip()
                is_invalid = len(sug) < 10 or (compare_orig and (sug == compare_orig or sug in compare_orig or compare_orig in sug))
                if not is_invalid:
                    valid_compliance_suggestions.append(s)
                    continue
                # 规则化组装：明确指出冲突法条与问题描述，给出修订指引
                law = (ci.get("conflicting_law") or "相关法律规定").strip()
                desc = (ci.get("conflict_description") or "与法律强制性规定不一致").strip()
                if desc and "一致" not in desc[:6]:
                    s["suggestion"] = (
                        f"该条款与{law}存在冲突：{desc}。"
                        f"建议按该法条要求修订条款表述，确保约定合法有效。"
                    )
                else:
                    s["suggestion"] = (
                        f"该条款可能与{law}不一致。建议逐字核对法条要求，"
                        f"修订条款表述使其符合法律强制性规定。"
                    )
                if not (s.get("legal_basis") or "").strip():
                    s["legal_basis"] = law
                valid_compliance_suggestions.append(s)
            suggestions_list.extend(valid_compliance_suggestions)
        except OllamaCallError as e:
            logger.warning(f"[generate_suggestions] 合规问题建议生成失败，跳过: {e}")

    # ==================== 3. 确定性兜底与规整（V6.0.5）====================
    # 小模型输出随机性大，LLM建议数量波动（0~12条）。为保证建议质量下限：
    #   a) 按suggestion文本去重（LLM可能输出重复建议）
    #   b) 清理双句号等标点瑕疵
    #   c) 建议不足（<3条）且存在风险/合规/缺失问题时规则化补齐
    if suggestions_list:
        # 去重（保持顺序）
        _seen = set()
        _deduped = []
        for s in suggestions_list:
            key = str(s.get("suggestion", "")).strip()
            if key and key not in _seen:
                _seen.add(key)
                s["suggestion"] = key.replace("。。", "。")
                _deduped.append(s)
        suggestions_list = _deduped

    if len(suggestions_list) < 3 and (risk_clauses or compliance_issues or missing_clauses):
        level_cn = {"low": "低", "medium": "中", "high": "高", "critical": "严重"}
        # a. 风险条款规则化建议（仅补充已有clause_index未覆盖的）
        covered_idx = {s.get("clause_index") for s in suggestions_list if s.get("issue_type") == "risk_clause"}
        for rc in risk_clauses:
            if rc.get("clause_index") in covered_idx:
                continue
            risk_desc = (rc.get("risk_description") or rc.get("risk_type") or "存在法律风险").strip()
            # 跳过LLM误报的无风险条目
            if "无风险" in risk_desc:
                continue
            suggestions_list.append({
                "clause_index": rc.get("clause_index", 0),
                "original_text": rc.get("original_text", ""),
                "suggestion": (
                    f"该条款存在{level_cn.get(rc.get('risk_level', 'medium'), '中')}风险"
                    f"（{rc.get('risk_type', '法律风险')}）：{risk_desc}。"
                    f"建议修订或删除相关表述，使之符合法律规定；必要时与对方协商补充对等约束条款。"
                ),
                "legal_basis": rc.get("legal_basis", ""),
                "issue_type": "risk_clause",
            })
        # b. 缺失条款补全建议（模板要求但合同未包含的条款）
        if missing_clauses:
            suggestions_list.append({
                "suggestion": f"建议补充完善以下缺失条款：{ '、'.join(missing_clauses[:8]) }，以增强合同完备性与可执行性。",
                "issue_type": "missing_clause",
            })
        # c. 合规问题兜底建议
        if compliance_issues and not any(s.get("issue_type") == "compliance_issue" for s in suggestions_list):
            suggestions_list.append({
                "suggestion": (
                    f"合同存在{len(compliance_issues)}处合规性问题（与相关法律强制性规定不一致），"
                    f"建议逐条核对该清单中的冲突条款并修订至合法合规。"
                ),
                "issue_type": "compliance_issue",
            })

    # 最终兜底
    if not suggestions_list and (risk_clauses or compliance_issues):
        suggestions_list = [{"suggestion": "建议咨询专业律师进行人工审查"}]

    return {
        # V2.0标准字段
        "modification_suggestions": suggestions_list,
        "current_step": "suggestions",
        # 向后兼容字段
        "suggestions": suggestions_list,
    }


async def generate_report(state: ContractReviewState) -> dict:
    """报告生成节点（V2.0增强版）

    在原有报告基础上，增加：
    1. needs_manual_review = risk_score >= 80
    2. parties 信息
    3. review_timestamp

    Args:
        state: 当前工作流状态

    Returns:
        状态更新字典
    """
    # 兼容 risk_score 和 overall_score
    risk_score = state.get("risk_score", 0)
    # 先读取各维度评分（V6.0.5：兜底公式需要引用，必须在使用前定义）
    completeness_score = state.get("completeness_score", 0)
    compliance_score = state.get("compliance_score", 0)
    consistency_score = state.get("consistency_score", 0)
    # V6.0.5：兜底综合评分与calculate_risk_score节点采用相同的维度加权融合公式
    # （正常流程state中已有overall_score，此兜底仅防御异常路径），避免公式不一致
    overall_score = state.get("overall_score")
    if overall_score is None:
        _dim = (
            float(completeness_score if isinstance(completeness_score, (int, float)) else 0) * 0.3
            + float(compliance_score if isinstance(compliance_score, (int, float)) else 0) * 0.4
            + float(consistency_score if isinstance(consistency_score, (int, float)) else 0) * 0.3
        )
        overall_score = max(0.0, min(100.0, _dim * 0.5 + (100 - risk_score) * 0.5))
    risk_level = state.get("risk_level", "low")
    risk_clause_count = state.get("risk_clause_count", len(state.get("risk_clauses", [])))
    missing_clauses = state.get("missing_clauses", [])

    # V2.0新增字段
    parties = state.get("parties", [])
    contract_type = state.get("contract_type", "通用合同")
    compliance_issues = state.get("compliance_issues", [])
    consistency_issues = state.get("consistency_issues", [])
    completeness_check = state.get("completeness_check", {})
    modification_suggestions = state.get("modification_suggestions", state.get("suggestions", []))

    # ==================== V6.0.4修复：修改建议兜底（防LLM失败导致建议为空）====================
    # 建议列表为空但存在风险条款/合规问题时，直接提取各风险条款已生成的
    # suggestion字段组装建议，保证任何审查结果都携带可操作的修改建议
    # （特别是极高风险合同——此前路由跳过建议节点导致评分为0时建议栏空白）
    if not modification_suggestions:
        risk_clauses = state.get("risk_clauses", [])
        fallback_suggestions = [
            {
                "clause_index": rc.get("clause_index", i + 1),
                "original_text": rc.get("original_text", ""),
                "suggestion": rc.get("suggestion") or "建议咨询专业律师复核该条款",
                "legal_basis": rc.get("legal_basis", ""),
                "issue_type": "risk_clause",
            }
            for i, rc in enumerate(risk_clauses)
            if rc.get("suggestion")
        ]
        if fallback_suggestions:
            modification_suggestions = fallback_suggestions
            logger.info(f"[generate_report] LLM建议为空，已从{len(fallback_suggestions)}条风险条款提取兜底建议")
        elif risk_clauses or compliance_issues:
            # 风险条款也没有suggestion字段的极端情况，给出通用指引
            modification_suggestions = [{"suggestion": "合同存在多处风险，建议咨询专业律师进行人工复核并逐条修订"}]

    # V4.0新增：多Agent对抗式审查结果
    primary_risks = state.get("primary_risks", [])
    review_check = state.get("review_check", {})
    adverse_opinions = state.get("adverse_opinions", [])
    debate_log = state.get("debate_log", [])
    unresolved_issues = state.get("unresolved_issues", [])

    # ==================== 1. 生成审查摘要（保留LLM调用）====================
    summary_prompt = f"""请根据以下合同审查数据生成一份简洁的审查摘要：

- 合同类型：{contract_type}
- 风险评分：{risk_score}/100（越高越危险）
- 风险等级：{risk_level}
- 风险条款数：{risk_clause_count}
- 合规问题数：{len(compliance_issues)}
- 一致性问题数：{len(consistency_issues)}
- 完整性评分：{completeness_score}/100
- 缺失条款：{', '.join(missing_clauses) if missing_clauses else '无'}

请生成200字以内的审查摘要："""

    # P1修复：捕获 OllamaCallError，使用规则兜底摘要，避免错误字符串混入报告
    # V4.0.2修复：LLM可能返回空字符串（非异常），此时也需触发兜底，否则summary为空影响用户体验
    # V6.0.4修复：小模型（qwen2.5:1.5b）对合同文本存在内容审核过敏，可能返回
    # "包含敏感内容，无法生成摘要"等推脱文本——此类文本对用户毫无价值，
    # 通过推脱关键词检测识别并触发规则兜底摘要
    _REFUSAL_KEYWORDS = ("无法", "敏感", "抱歉", "不能提供", "不方便", "抱歉，我")
    summary = ""
    try:
        summary = await _call_ollama(summary_prompt, temperature=0.3, max_tokens=500)
        # 去除空白字符后判断是否为空（LLM可能返回纯空白）
        if not summary or not summary.strip():
            logger.warning("[generate_report] LLM 返回空摘要，使用规则兜底摘要")
            summary = ""
        elif any(kw in summary for kw in _REFUSAL_KEYWORDS):
            # 推脱性回复视为无效摘要，回退规则模板
            logger.warning(f"[generate_report] LLM 返回推脱性摘要（疑似内容审核过敏），使用规则兜底：{summary[:60]}")
            summary = ""
    except OllamaCallError as e:
        logger.warning(f"[generate_report] LLM 摘要生成失败，使用规则兜底摘要: {e}")
        summary = ""

    # 兜底：LLM异常或返回空时，用模板生成结构化摘要（包含V4.0对抗式审查关键指标）
    if not summary:
        summary = (
            f"合同类型：{contract_type}；"
            f"风险评分：{risk_score}/100（等级：{risk_level}）；"
            f"风险条款数：{risk_clause_count}；"
            f"合规问题数：{len(compliance_issues)}；"
            f"一致性问题数：{len(consistency_issues)}；"
            f"完整性评分：{completeness_score}/100；"
            f"缺失条款：{'、'.join(missing_clauses) if missing_clauses else '无'}；"
            f"主审Agent识别风险：{len(primary_risks)}条；"
            f"反方Agent反对意见：{len(adverse_opinions)}条；"
            f"对抗辩论：{len(debate_log)}轮，未解决问题：{len(unresolved_issues)}条；"
            f"{'需人工审查（高风险）。' if risk_score >= 80 else '建议关注上述风险点。'}"
        )

    # ==================== 2. 组装V2.0标准报告====================
    review_report = {
        "contract_type": contract_type,
        "parties": parties,
        "risk_score": risk_score,
        "overall_score": overall_score,
        "risk_level": risk_level,
        # V2.0新增：高风险标记人工审查
        "needs_manual_review": risk_score >= 80,
        "risk_clause_count": risk_clause_count,
        "completeness_score": completeness_score,
        "compliance_score": compliance_score,
        "consistency_score": consistency_score,
        "missing_clauses": missing_clauses,
        "completeness_check": completeness_check,
        "risk_clauses": state.get("risk_clauses", []),
        "compliance_issues": compliance_issues,
        "consistency_issues": consistency_issues,
        "modification_suggestions": modification_suggestions,
        "suggestions": state.get("suggestions", modification_suggestions),
        "completeness": state.get("completeness", {}),
        "compliance": state.get("compliance", {}),
        "consistency": state.get("consistency", {}),
        # V2.0新增：审查时间戳
        "review_timestamp": datetime.now().isoformat(),
        # V4.0新增：多Agent对抗式审查结果（参考文档4.3节）
        "primary_risks": primary_risks,
        "review_check": review_check,
        "adverse_opinions": adverse_opinions,
        "debate_log": debate_log,
        "unresolved_issues": unresolved_issues,
        "adverse_opinion_count": len(adverse_opinions),
        "unresolved_count": len(unresolved_issues),
        # V4.0.2修复：将summary纳入report字典，确保workflow.run()返回时能携带summary字段
        # （workflow.run()返回 result.get("report")，而report是review_report的副本）
        "summary": summary,
    }

    # 向后兼容的report字段（与review_report内容一致）
    report = dict(review_report)

    return {
        # V2.0标准字段
        "review_report": review_report,
        "current_step": "report_generate",
        # 向后兼容字段
        "summary": summary,
        "report": report,
    }


# ==================== 向后兼容别名 ====================
# 旧代码通过 parse_doc/risk_detect/risk_score/suggestions/report_generate 等名称引用节点函数
# 这里提供别名以保持向后兼容（测试文件、服务层等）
# 注意：check_compliance/check_consistency 是V2.0文档命名，原代码使用 compliance_check/consistency_check
parse_doc = parse_document
risk_detect = detect_risk_clauses
risk_score = calculate_risk_score
suggestions = generate_suggestions
report_generate = generate_report
compliance_check = check_compliance
consistency_check = check_consistency
# V4.0新增节点别名（多Agent对抗式审查）
adverse_attack = adverse_agent_attack
debate = debate_round
