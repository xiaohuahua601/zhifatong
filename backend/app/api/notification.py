"""
智法通 - 通知路由模块

提供用户通知查询、未读数量统计、标记已读等API端点。
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.services.notification_service import NotificationService
from app.utils.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/notifications", tags=["通知"])


@router.get("/", summary="获取通知列表")
async def get_notifications(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    is_read: Optional[bool] = Query(None, description="已读状态筛选"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户的通知列表

    - 支持按已读/未读筛选
    - 返回通知列表、总数和未读数量
    - 按时间倒序排列
    """
    service = NotificationService(db)
    result = await service.get_notifications(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        is_read=is_read,
    )
    return result


@router.get("/unread-count", summary="获取未读通知数量")
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户的未读通知数量

    - 用于导航栏通知图标徽章数字显示
    """
    service = NotificationService(db)
    count = await service.get_unread_count(current_user.id)
    return {"unread_count": count}


@router.put("/{notification_id}/read", summary="标记通知为已读")
async def mark_notification_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """标记单条通知为已读

    - 只能标记自己的通知
    """
    service = NotificationService(db)
    await service.mark_as_read(notification_id, current_user.id)
    return {"message": "已标记为已读"}


@router.put("/read-all", summary="标记所有通知为已读")
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """标记当前用户的所有未读通知为已读

    - 一键清除所有未读标记
    - 返回标记为已读的通知数量
    """
    service = NotificationService(db)
    count = await service.mark_all_as_read(current_user.id)
    return {"message": f"已将 {count} 条通知标记为已读", "marked_count": count}
