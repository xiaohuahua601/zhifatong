"""
智法通 - 合同审查路由模块

提供合同上传、审查、获取报告和历史记录的API端点。
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional

from app.database import get_db
from app.services.contract_service import ContractService
from app.services.quota_service import QuotaService
from app.utils.deps import get_current_user
from app.models.user import User
from app.config import settings

router = APIRouter(prefix="/contract", tags=["合同审查"])


# ==================== 请求/响应模型 ====================

class ContractUploadResponse(BaseModel):
    """合同上传响应"""
    id: int = Field(..., description="合同ID")
    title: str = Field(..., description="合同标题")
    file_name: str = Field(..., description="文件名")
    status: str = Field(..., description="合同状态")


class ReviewRequest(BaseModel):
    """审查请求"""
    contract_id: int = Field(..., description="合同ID")
    contract_type: Optional[str] = Field(None, description="合同类型（如：劳动合同、租赁合同）")


class ContractTypeUpdateRequest(BaseModel):
    """合同分类更新请求"""
    contract_type: Optional[str] = Field(None, description="合同类型（如：劳动合同、租赁合同、采购合同），传空值清除分类")


class ReviewReportResponse(BaseModel):
    """审查报告响应

    V4.0新增字段（多Agent对抗式审查，参考文档4.3节）：
    - primary_risks: 主审Agent风险清单（JSON字符串）
    - review_check: 复核Agent规则复检结果（JSON字符串）
    - adverse_opinions: 反方Agent反对意见（JSON字符串）
    - debate_log: 对抗辩论记录（JSON字符串）
    - unresolved_issues: 未达成共识问题（JSON字符串）
    - adverse_opinion_count: 反对意见数量
    - unresolved_count: 未解决问题数量
    """
    id: int
    contract_id: int
    overall_score: Optional[float] = None
    risk_level: Optional[str] = None
    risk_clause_count: int = 0
    summary: Optional[str] = None
    suggestions: Optional[str] = None
    completeness: Optional[str] = None
    compliance: Optional[str] = None
    consistency: Optional[str] = None
    review_duration_ms: Optional[int] = None
    risk_clauses: list = []
    # V4.0新增：多Agent对抗式审查结果（前端解析JSON字符串展示）
    primary_risks: Optional[str] = "[]"
    review_check: Optional[str] = "{}"
    adverse_opinions: Optional[str] = "[]"
    debate_log: Optional[str] = "[]"
    unresolved_issues: Optional[str] = "[]"
    adverse_opinion_count: int = 0
    unresolved_count: int = 0

    class Config:
        from_attributes = True


class ContractListItem(BaseModel):
    """合同列表项"""
    id: int
    title: str
    file_name: str
    contract_type: Optional[str] = None
    status: str
    overall_score: Optional[float] = None
    risk_level: Optional[str] = None
    created_at: str = ""

    class Config:
        from_attributes = True


# ==================== API端点 ====================

@router.post("/upload", response_model=ContractUploadResponse, summary="上传合同")
async def upload_contract(
    file: UploadFile = File(..., description="合同文件（PDF/Word/TXT）"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传合同文件

    - 支持PDF、Word、TXT格式
    - 文件大小不超过50MB
    - 上传后自动解析合同内容
    """
    # 文件名安全校验：防止路径遍历攻击（拒绝含".."或路径分隔符的文件名）
    if not file.filename or ".." in file.filename or "/" in file.filename or "\\" in file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件名非法：禁止包含路径分隔符或路径遍历字符",
        )
    # 验证文件类型
    file_ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件格式，允许的格式：{settings.ALLOWED_EXTENSIONS}",
        )

    contract_service = ContractService(db)
    result = await contract_service.upload_contract(
        user_id=current_user.id,
        file=file,
    )
    return ContractUploadResponse(**result)


@router.post("/review", summary="启动合同审查")
async def review_contract(
    request: ReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """启动AI合同审查

    - 使用LangGraph Agent工作流进行多维度审查
    - 包括：完整性检查、风险检测、合规性检查、一致性检查
    - 审查完成后生成详细报告
    - 普通用户每日限制10份合同审查，超额返回429
    """
    # 额度检查：校验用户今日剩余合同审查次数
    quota_service = QuotaService(db)
    allowed, remaining, limit = await quota_service.check_and_consume(
        user_id=current_user.id, resource_type="contract"
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"今日合同审查次数已用完（限制{limit}份/日），请明日再试",
            headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Limit": str(limit)},
        )

    contract_service = ContractService(db)
    # 捕获业务校验异常（合同不存在/正在审查中/内容为空等）转为400，
    # 避免以500"服务器内部错误"形式返回，前端无法展示具体原因
    try:
        result = await contract_service.review_contract(
            user_id=current_user.id,
            contract_id=request.contract_id,
            contract_type=request.contract_type,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    return result


class OptimizeRequest(BaseModel):
    """合同优化请求（V6.0.6新增）"""
    contract_id: int = Field(..., description="合同ID")


@router.post("/optimize", summary="优化合同并生成Markdown（V6.0.6新增）")
async def optimize_contract(
    request: OptimizeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """基于审查报告修改建议优化原合同，返回Markdown格式优化版全文

    - 仅reviewed（已审查）状态且报告含修改建议的合同可优化
    - LLM逐条改写风险条款，失败时规则兜底（原文+修订说明）
    - 返回markdown全文与建议文件名（原合同名_优化后.md），由前端触发下载
    """
    contract_service = ContractService(db)
    # 业务校验异常（未审查/无建议等）转400，便于前端展示具体原因
    try:
        result = await contract_service.optimize_contract(
            user_id=current_user.id,
            contract_id=request.contract_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    return result


@router.get("/report/{contract_id}", response_model=ReviewReportResponse, summary="获取审查报告")
async def get_review_report(
    contract_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取合同的审查报告

    - 包含总体评分、风险等级和详细风险条款
    - 如果合同尚未审查完成，返回当前进度
    """
    contract_service = ContractService(db)
    result = await contract_service.get_review_report(
        user_id=current_user.id,
        contract_id=contract_id,
    )
    return ReviewReportResponse(**result)


@router.get("/history", summary="获取合同历史记录")
async def get_contract_history(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status_filter: Optional[str] = Query(None, description="状态筛选"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户的合同历史记录

    - 按创建时间倒序排列
    - 支持按状态筛选
    - 支持分页
    """
    contract_service = ContractService(db)
    result = await contract_service.get_contract_history(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        status_filter=status_filter,
    )
    return result


@router.get("/{contract_id}", summary="获取合同详情")
async def get_contract_detail(
    contract_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取合同详细信息

    - 包含合同基本信息、全文内容
    - 如果已审查，包含审查报告摘要
    """
    contract_service = ContractService(db)
    result = await contract_service.get_contract_detail(
        user_id=current_user.id,
        contract_id=contract_id,
    )
    return result


@router.delete("/{contract_id}", summary="删除合同")
async def delete_contract(
    contract_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除合同及其关联的审查报告

    - 同时删除文件存储
    - 只能删除自己的合同
    """
    contract_service = ContractService(db)
    await contract_service.delete_contract(
        user_id=current_user.id,
        contract_id=contract_id,
    )
    return {"message": "合同已删除"}


@router.patch("/{contract_id}/type", summary="更新合同分类")
async def update_contract_type(
    contract_id: int,
    request: ContractTypeUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新合同分类（支持「未分类」合同归档管理）

    - 仅允许修改本人合同的分类，防止越权修改他人数据
    - 可用于将「未分类」合同归入劳动合同、租赁合同等类别
    - 传空值可清除已有分类
    """
    contract_service = ContractService(db)
    try:
        result = await contract_service.update_contract_type(
            user_id=current_user.id,
            contract_id=contract_id,
            contract_type=request.contract_type,
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
