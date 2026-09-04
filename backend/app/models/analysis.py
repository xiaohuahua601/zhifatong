"""
智法通 - 分析模型模块

定义数据分析相关的数据库模型，包括查询日志和引用统计。
用于数据看板和热点分析功能。
"""

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Float, JSON
)
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class QueryLog(Base):
    """查询日志模型

    记录用户的每次法律查询，用于分析热门法律问题、
    用户行为模式和数据看板展示。
    """
    __tablename__ = "query_logs"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="日志ID")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True, comment="用户ID")
    # 原始查询文本
    query_text = Column(Text, nullable=False, comment="查询文本")
    # 重写后的查询（查询重写器输出）
    rewritten_query = Column(Text, nullable=True, comment="重写后的查询")
    # 查询分类（如：劳动法、合同法、知识产权等）
    category = Column(String(50), nullable=True, index=True, comment="查询分类")
    # 子查询列表（JSON格式）
    sub_queries = Column(Text, nullable=True, comment="子查询列表（JSON格式）")
    # 检索到的文档数量
    retrieved_count = Column(Integer, default=0, comment="检索到的文档数量")
    # AI回答的置信度
    confidence = Column(Float, nullable=True, comment="回答置信度")
    # 自评估分数
    self_eval_score = Column(Float, nullable=True, comment="自评估分数")
    # 是否来自流式回答
    is_streaming = Column(Integer, default=0, comment="是否流式回答（0=否，1=是）")
    # 响应耗时（毫秒）
    latency_ms = Column(Integer, nullable=True, comment="响应耗时（毫秒）")
    # 用户反馈（1=正面，-1=负面，0=无反馈）
    feedback_score = Column(Integer, default=0, comment="用户反馈分数")
    # 客户端IP
    client_ip = Column(String(50), nullable=True, comment="客户端IP")
    # 用户代理
    user_agent = Column(String(500), nullable=True, comment="用户代理")
    created_at = Column(DateTime, default=datetime.utcnow, index=True, comment="创建时间")

    def __repr__(self):
        return f"<QueryLog(id={self.id}, category='{self.category}')>"


class CitationStat(Base):
    """引用统计模型

    统计法律文档被引用的频次，用于热门法规分析、
    知识库价值评估和推荐排序。
    """
    __tablename__ = "citation_stats"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="统计ID")
    # 被引用的文档ID
    document_id = Column(
        Integer,
        ForeignKey("legal_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="文档ID"
    )
    # 被引用的分块ID
    chunk_id = Column(Integer, ForeignKey("document_chunks.id", ondelete="SET NULL"), nullable=True, comment="分块ID")
    # 统计日期（按天聚合）
    stat_date = Column(DateTime, nullable=False, index=True, comment="统计日期")
    # 当日被引用次数
    citation_count = Column(Integer, default=0, comment="引用次数")
    # 当日被引用后获得正面反馈的次数
    positive_feedback_count = Column(Integer, default=0, comment="正面反馈次数")
    # 当日被引用后获得负面反馈的次数
    negative_feedback_count = Column(Integer, default=0, comment="负面反馈次数")
    # 平均置信度
    avg_confidence = Column(Float, nullable=True, comment="平均置信度")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def __repr__(self):
        return f"<CitationStat(id={self.id}, doc_id={self.document_id})>"
