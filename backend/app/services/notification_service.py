"""
智法通 - 通知服务模块

提供用户通知的创建、查询、标记已读等业务逻辑。
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from typing import Optional
from datetime import datetime, timedelta

from app.models.notification import Notification, NotificationType


class NotificationService:
    """通知服务类

    封装通知的查询、创建、标记已读等业务逻辑。
    """

    def __init__(self, db: AsyncSession):
        """初始化通知服务

        Args:
            db: 异步数据库会话
        """
        self.db = db

    async def get_notifications(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        is_read: Optional[bool] = None,
    ) -> dict:
        """获取用户通知列表

        Args:
            user_id: 用户ID
            page: 页码
            page_size: 每页数量
            is_read: 已读状态筛选（None=全部）

        Returns:
            包含通知列表和分页信息的字典
        """
        # 构建查询条件
        conditions = [Notification.user_id == user_id]
        if is_read is not None:
            conditions.append(Notification.is_read == is_read)

        # 查询总数
        count_query = select(func.count(Notification.id)).where(*conditions)
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # 查询未读数量
        unread_result = await self.db.execute(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id,
                Notification.is_read == False,
            )
        )
        unread_count = unread_result.scalar() or 0

        # 查询通知列表（按时间倒序）
        query = (
            select(Notification)
            .where(*conditions)
            .order_by(Notification.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        notifications = result.scalars().all()

        return {
            "items": [
                {
                    "id": n.id,
                    "type": n.type.value if n.type else "system",
                    "title": n.title,
                    "content": n.content,
                    "is_read": n.is_read,
                    "resource_type": n.resource_type,
                    "resource_id": n.resource_id,
                    "created_at": n.created_at.isoformat() if n.created_at else "",
                }
                for n in notifications
            ],
            "total": total,
            "unread_count": unread_count,
            "page": page,
            "page_size": page_size,
        }

    async def get_unread_count(self, user_id: int) -> int:
        """获取用户未读通知数量

        Args:
            user_id: 用户ID

        Returns:
            未读通知数量
        """
        result = await self.db.execute(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id,
                Notification.is_read == False,
            )
        )
        return result.scalar() or 0

    async def mark_as_read(self, notification_id: int, user_id: int) -> None:
        """标记单条通知为已读

        Args:
            notification_id: 通知ID
            user_id: 用户ID（用于权限校验）
        """
        await self.db.execute(
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
            .values(is_read=True)
        )
        await self.db.flush()

    async def mark_all_as_read(self, user_id: int) -> int:
        """标记用户所有未读通知为已读

        Args:
            user_id: 用户ID

        Returns:
            标记为已读的通知数量
        """
        result = await self.db.execute(
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read == False,
            )
            .values(is_read=True)
        )
        await self.db.flush()
        return result.rowcount

    async def create_notification(
        self,
        user_id: int,
        title: str,
        content: Optional[str] = None,
        notif_type: NotificationType = NotificationType.SYSTEM,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
    ) -> Notification:
        """创建通知（供其他模块调用）

        Args:
            user_id: 接收用户ID
            title: 通知标题
            content: 通知内容
            notif_type: 通知类型
            resource_type: 关联资源类型
            resource_id: 关联资源ID

        Returns:
            创建的通知对象
        """
        notification = Notification(
            user_id=user_id,
            type=notif_type,
            title=title,
            content=content,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        self.db.add(notification)
        await self.db.flush()
        return notification
