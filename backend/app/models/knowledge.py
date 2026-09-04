"""
智法通 - 知识库模型模块

定义法律知识库相关的数据库模型，包括法律文档和文档分块。
文档分块用于RAG检索增强生成。
"""

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean, Enum
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class DocumentStatus(str, enum.Enum):
    """文档状态枚举"""
    PENDING = "pending"           # 待处理
    PROCESSING = "processing"     # 处理中
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"             # 处理失败


class DocumentSource(str, enum.Enum):
    """文档来源枚举"""
    UPLOAD = "upload"             # 用户上传
    CRAWL = "crawl"               # 网络爬取
    MANUAL = "manual"             # 手动录入
    API = "api"                   # API导入


class LegalDocument(Base):
    """法律文档模型

    存储法律知识库中的文档元数据，包括法律法规、案例、合同模板等。
    文档内容会被分块索引到向量数据库中。
    """
    __tablename__ = "legal_documents"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="文档ID")
    title = Column(String(300), nullable=False, comment="文档标题")
    # 文档类型（如：法律、法规、司法解释、案例、合同模板等）
    doc_type = Column(String(50), nullable=True, index=True, comment="文档类型")
    # 文档来源
    source = Column(Enum(DocumentSource), default=DocumentSource.UPLOAD, comment="文档来源")
    # 文件路径（用户上传的文档）
    file_path = Column(String(500), nullable=True, comment="文件存储路径")
    file_name = Column(String(255), nullable=True, comment="原始文件名")
    file_size = Column(Integer, nullable=True, comment="文件大小（字节）")
    # 文档全文内容
    content = Column(Text, nullable=True, comment="文档全文内容")
    # 文档摘要
    summary = Column(Text, nullable=True, comment="文档摘要")
    # 文档状态
    status = Column(Enum(DocumentStatus), default=DocumentStatus.PENDING, comment="处理状态")
    # 向量化进度（0-100）
    indexing_progress = Column(Integer, default=0, comment="向量化进度")
    # 分块数量
    chunk_count = Column(Integer, default=0, comment="分块数量")
    # 上传用户ID
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="上传用户ID")
    # 标签（JSON格式存储）
    tags = Column(String(500), nullable=True, comment="标签（JSON格式）")
    # 发布日期（法律生效日期）
    publish_date = Column(DateTime, nullable=True, comment="发布/生效日期")
    # 有效状态
    is_effective = Column(Boolean, default=True, comment="是否有效")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # 关系：文档的分块列表
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<LegalDocument(id={self.id}, title='{self.title}')>"


class DocumentChunk(Base):
    """文档分块模型

    文档被切分为多个分块，每个分块对应向量数据库中的一条记录。
    用于RAG检索时定位到具体的文档片段。
    """
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="分块ID")
    document_id = Column(
        Integer,
        ForeignKey("legal_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="文档ID"
    )
    # 分块在文档中的序号
    chunk_index = Column(Integer, nullable=False, comment="分块序号")
    # 分块文本内容
    content = Column(Text, nullable=False, comment="分块内容")
    # 在向量数据库中的ID
    vector_id = Column(String(100), nullable=True, unique=True, comment="向量数据库中的ID")
    # 分块的token数量
    token_count = Column(Integer, nullable=True, comment="Token数量")
    # 分块在原文中的起始字符位置
    start_char = Column(Integer, nullable=True, comment="起始字符位置")
    # 分块在原文中的结束字符位置
    end_char = Column(Integer, nullable=True, comment="结束字符位置")
    # 分块元数据（JSON格式，如页码、段落等）
    chunk_metadata = Column("metadata", Text, nullable=True, comment="元数据（JSON格式）")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    # 关系：所属文档
    document = relationship("LegalDocument", back_populates="chunks")

    def __repr__(self):
        return f"<DocumentChunk(id={self.id}, chunk_index={self.chunk_index})>"
