"""
智法通 - 问答模型模块

定义法律问答相关的数据库模型，包括对话、消息和反馈。
支持多轮对话上下文管理。
"""

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean, Enum
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class MessageRole(str, enum.Enum):
    """消息角色枚举"""
    USER = "user"           # 用户消息
    ASSISTANT = "assistant" # AI助手消息
    SYSTEM = "system"       # 系统消息


class ConversationStatus(str, enum.Enum):
    """对话状态枚举"""
    ACTIVE = "active"       # 进行中
    ARCHIVED = "archived"   # 已归档
    DELETED = "deleted"     # 已删除


class Conversation(Base):
    """对话模型

    表示一次完整的法律咨询对话，包含多条消息。
    每个对话属于一个用户，支持多轮对话上下文。
    """
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="对话ID")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="用户ID")
    title = Column(String(200), nullable=True, comment="对话标题（自动生成）")
    status = Column(
        Enum(ConversationStatus),
        default=ConversationStatus.ACTIVE,
        comment="对话状态"
    )
    message_count = Column(Integer, default=0, comment="消息数量")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # 关系：对话中的消息列表
    messages = relationship(
        "Message",
        back_populates="conversation",
        order_by="Message.created_at",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Conversation(id={self.id}, title='{self.title}')>"


class Message(Base):
    """消息模型

    表示对话中的单条消息，可以是用户提问或AI回答。
    AI回答消息会关联引用的法律文档来源。
    """
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="消息ID")
    conversation_id = Column(
        Integer,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="对话ID"
    )
    role = Column(Enum(MessageRole), nullable=False, comment="消息角色")
    content = Column(Text, nullable=False, comment="消息内容")
    # AI回答的引用来源，存储JSON格式的文档引用列表
    citations = Column(Text, nullable=True, comment="引用来源（JSON格式）")
    # AI回答的置信度分数
    confidence = Column(Float, nullable=True, comment="置信度分数")
    # 生成耗时（毫秒）
    latency_ms = Column(Integer, nullable=True, comment="生成耗时（毫秒）")
    # 使用的token数量
    token_count = Column(Integer, nullable=True, comment="Token数量")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    # 关系：所属对话
    conversation = relationship("Conversation", back_populates="messages")
    # 关系：消息的反馈
    feedback = relationship("QAFeedback", back_populates="message", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Message(id={self.id}, role='{self.role}')>"


class QAFeedback(Base):
    """问答反馈模型

    用户对AI回答的反馈评价，用于持续优化回答质量。
    """
    __tablename__ = "qa_feedbacks"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="反馈ID")
    message_id = Column(
        Integer,
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="消息ID"
    )
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="用户ID")
    is_positive = Column(Boolean, nullable=False, comment="是否正面评价（True=赞，False=踩）")
    rating = Column(Integer, nullable=True, comment="评分（1-5星）")
    comment = Column(Text, nullable=True, comment="反馈内容")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    # 关系：关联的消息
    message = relationship("Message", back_populates="feedback")

    def __repr__(self):
        return f"<QAFeedback(id={self.id}, is_positive={self.is_positive})>"
