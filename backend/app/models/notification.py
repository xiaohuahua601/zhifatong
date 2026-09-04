"""
智法通 - 通知模型模块

定义用户通知相关的数据库模型，用于系统消息、合同审查结果、
法规更新等通知的存储与管理。
"""

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Enum
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class NotificationType(str, enum.Enum):
    """通知类型枚举"""
    SYSTEM = "system"           # 系统通知
    CONTRACT = "contract"       # 合同审查通知
    LEGAL_UPDATE = "legal_update"  # 法规更新通知
    QA = "qa"                   # 问答通知
    WARNING = "warning"         # 风险预警通知


class Notification(Base):
    """通知模型

    存储系统向用户推送的各类通知消息，支持已读/未读状态管理。
    """
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="通知ID")
    # 接收通知的用户ID
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="接收用户ID"
    )
    # 通知类型
    type = Column(Enum(NotificationType), default=NotificationType.SYSTEM, comment="通知类型")
    # 通知标题
    title = Column(String(200), nullable=False, comment="通知标题")
    # 通知内容
    content = Column(Text, nullable=True, comment="通知内容")
    # 是否已读
    is_read = Column(Boolean, default=False, index=True, comment="是否已读")
    # 关联资源类型（如合同、文档等，用于点击跳转）
    resource_type = Column(String(50), nullable=True, comment="关联资源类型")
    # 关联资源ID（用于点击跳转到具体页面）
    resource_id = Column(Integer, nullable=True, comment="关联资源ID")
    created_at = Column(DateTime, default=datetime.utcnow, index=True, comment="创建时间")

    # 关系：所属用户
    user = relationship("User", backref="notifications")

    def __repr__(self):
        return f"<Notification(id={self.id}, title='{self.title}', read={self.is_read})>"
