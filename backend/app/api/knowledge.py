"""
智法通 - 知识库路由模块

提供法律知识库文档管理、上传、搜索和统计的API端点。
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional

from app.database import get_db
from app.services.knowledge_service import KnowledgeService
from app.utils.deps import get_current_user, require_permission
from app.models.user import User
from app.config import settings

router = APIRouter(prefix="/knowledge", tags=["知识库"])


# ==================== 请求/响应模型 ====================

class DocumentResponse(BaseModel):
    """文档响应"""
    id: int
    title: str
    doc_type: Optional[str] = None
    source: str = "upload"
    file_name: Optional[str] = None
    status: str = "pending"
    chunk_count: int = 0
    indexing_progress: int = 0
    summary: Optional[str] = None
    tags: Optional[str] = None
    is_effective: bool = True
    created_at: str = ""

    class Config:
        from_attributes = True


class DocumentUploadResponse(BaseModel):
    """文档上传响应"""
    id: int = Field(..., description="文档ID")
    title: str = Field(..., description="文档标题")
    status: str = Field(..., description="处理状态")
    message: str = Field(..., description="提示信息")


class SearchRequest(BaseModel):
    """搜索请求"""
    query: str = Field(..., min_length=1, max_length=500, description="搜索关键词")
    top_k: int = Field(default=5, ge=1, le=20, description="返回结果数量")
    doc_type: Optional[str] = Field(None, description="文档类型筛选")


class SearchResult(BaseModel):
    """搜索结果项"""
    chunk_id: int
    document_id: int
    document_title: str
    content: str
    score: float
    metadata: Optional[dict] = None


class KnowledgeStats(BaseModel):
    """知识库统计"""
    total_documents: int = 0
    total_chunks: int = 0
    doc_type_distribution: dict = {}
    recent_uploads: int = 0
    processing_count: int = 0


# ==================== API端点 ====================

@router.get("/documents", summary="获取文档列表")
async def get_documents(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    doc_type: Optional[str] = Query(None, description="文档类型筛选"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取知识库文档列表

    - 支持按文档类型筛选
    - 支持关键词搜索
    - 支持分页
    """
    knowledge_service = KnowledgeService(db)
    result = await knowledge_service.get_documents(
        page=page,
        page_size=page_size,
        doc_type=doc_type,
        keyword=keyword,
    )
    return result


@router.post("/upload", response_model=DocumentUploadResponse, summary="上传法律文档")
async def upload_document(
    file: UploadFile = File(..., description="法律文档文件"),
    doc_type: str = Query("法律", description="文档类型"),
    tags: Optional[str] = Query(None, description="标签（逗号分隔）"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge:manage")),
):
    """上传法律文档到知识库

    - 支持 PDF、Word、TXT 格式
    - 上传后自动解析、分块、向量化索引
    - 可指定文档类型和标签
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

    knowledge_service = KnowledgeService(db)
    result = await knowledge_service.upload_document(
        user_id=current_user.id,
        file=file,
        doc_type=doc_type,
        tags=tags,
    )
    return DocumentUploadResponse(**result)


@router.post("/search", summary="搜索知识库")
async def search_knowledge(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """语义搜索知识库

    - 使用向量相似度搜索
    - 支持混合检索（稠密+稀疏）
    - 返回最相关的文档片段
    """
    knowledge_service = KnowledgeService(db)
    result = await knowledge_service.search(
        query=request.query,
        top_k=request.top_k,
        doc_type=request.doc_type,
    )
    return {"results": result}


@router.get("/stats", response_model=KnowledgeStats, summary="知识库统计")
async def get_knowledge_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取知识库统计数据

    - 文档总数、分块总数
    - 文档类型分布
    - 最近上传数量
    - 处理中数量
    """
    knowledge_service = KnowledgeService(db)
    result = await knowledge_service.get_stats()
    return KnowledgeStats(**result)


@router.get("/documents/{document_id}", summary="获取文档详情")
async def get_document_detail(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取文档详细信息

    - 包含文档元数据、内容摘要
    - 包含分块列表
    """
    knowledge_service = KnowledgeService(db)
    result = await knowledge_service.get_document_detail(document_id)
    return result


@router.get("/documents/{document_id}/content", summary="获取文档完整内容")
async def get_document_content(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取文档完整内容

    - 返回文档全文内容（解析后的纯文本）
    - 包含所有分块的完整内容（非截断预览）
    - 用于文档详情中点击文件名查看完整内容
    - 需要登录认证，符合系统权限控制要求
    """
    knowledge_service = KnowledgeService(db)
    result = await knowledge_service.get_document_content(document_id)
    return result


@router.delete("/documents/{document_id}", summary="删除文档")
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge:manage")),
):
    """删除知识库文档

    - 同时删除向量数据库中的索引
    - 同时删除文件存储
    """
    knowledge_service = KnowledgeService(db)
    await knowledge_service.delete_document(document_id)
    return {"message": "文档已删除"}
