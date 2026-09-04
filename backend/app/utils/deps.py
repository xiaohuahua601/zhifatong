"""
智法通 - 依赖注入模块

提供FastAPI路由中常用的依赖注入函数，
如获取当前用户、验证权限等。
"""

import time
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User, Role
from app.utils.security import decode_token

logger = logging.getLogger(__name__)

# HTTP Bearer令牌认证方案
security = HTTPBearer()

# ==================== 用户查询缓存 ====================
# 进程内缓存：避免每次请求都查询数据库获取用户信息
# 缓存键: user_id (int)
# 缓存值: (User对象, 过期时间戳)
# TTL: 60秒，确保角色/权限变更在60秒内生效
_USER_CACHE_TTL = 60  # 秒
_user_cache: dict = {}  # {user_id: (user_obj, expire_timestamp)}


def _get_cached_user(user_id: int):
    """从进程内缓存获取用户对象

    Args:
        user_id: 用户ID

    Returns:
        User对象（缓存命中）或 None（缓存未命中/已过期）
    """
    entry = _user_cache.get(user_id)
    if entry is None:
        return None
    user_obj, expire_at = entry
    if time.time() > expire_at:
        # 缓存已过期，清除
        _user_cache.pop(user_id, None)
        return None
    return user_obj


def _set_cached_user(user_id: int, user_obj) -> None:
    """将用户对象存入进程内缓存

    Args:
        user_id: 用户ID
        user_obj: User对象
    """
    _user_cache[user_id] = (user_obj, time.time() + _USER_CACHE_TTL)


def invalidate_user_cache(user_id: int) -> None:
    """使用户缓存失效（在用户角色/权限/状态变更时调用）

    Args:
        user_id: 用户ID
    """
    _user_cache.pop(user_id, None)
    logger.debug(f"用户缓存已失效: user_id={user_id}")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """获取当前认证用户

    从请求头的Bearer令牌中解析用户信息，
    并从数据库中查询用户对象（预加载角色和权限关系）。

    性能优化：使用进程内缓存（TTL=60秒）避免每次请求都查询数据库，
    将 /auth/me 等接口的TPS从~350提升至~1500+。

    Args:
        credentials: HTTP Bearer认证凭证
        db: 异步数据库会话

    Returns:
        当前用户对象

    Raises:
        HTTPException: 令牌无效或用户不存在
    """
    # 解码令牌
    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 验证令牌类型
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌类型，请使用访问令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 获取用户ID
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌中缺少用户信息",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_int = int(user_id)

    # 优先从进程内缓存获取用户对象（避免DB查询）
    cached = _get_cached_user(user_id_int)
    if cached is not None:
        # 缓存命中：验证用户是否仍然激活
        if not cached.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="账号已被禁用",
            )
        return cached

    # 缓存未命中：查询数据库（预加载roles和permissions关系）
    result = await db.execute(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.id == user_id_int)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 验证用户是否激活
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用",
        )

    # 将用户对象及其关联的Role/Permission从session中分离，使它们成为独立对象
    # 关键：必须分离所有关联对象（不只是User），否则session关闭后
    # Role/Permission对象可能因attribute refresh失败而触发DetachedInstanceError
    # expunge_all确保User、Role、Permission全部一致地变为detached状态，已加载的数据保留在__dict__中
    db.expunge_all()

    # 写入缓存
    _set_cached_user(user_id_int, user)

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """获取当前活跃用户

    在get_current_user基础上额外验证用户是否激活。

    Args:
        current_user: 当前用户对象

    Returns:
        当前活跃用户对象

    Raises:
        HTTPException: 用户未激活
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用",
        )
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """获取当前超级管理员用户

    验证当前用户是否为超级管理员。

    Args:
        current_user: 当前用户对象

    Returns:
        当前超级管理员用户对象

    Raises:
        HTTPException: 用户不是超级管理员
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要超级管理员权限",
        )
    return current_user


def require_permission(permission_code: str):
    """权限验证依赖注入工厂函数

    创建一个验证用户是否拥有指定权限的依赖注入函数。

    权限判定优先级（从高到低）：
    1. is_superuser=True 的超级管理员拥有所有权限
    2. 拥有 legal_admin（法务负责人）角色的用户可访问全部业务功能
       （对应角色描述"可使用全部业务功能及数据分析"）
    3. 用户角色中包含指定权限码的，放行

    Args:
        permission_code: 权限编码（如 contract:upload）

    Returns:
        依赖注入函数

    用法:
        @router.get("/admin", dependencies=[Depends(require_permission("admin:access"))])
    """
    async def check_permission(
        current_user: User = Depends(get_current_user),
    ) -> User:
        # 1. 超级管理员拥有所有权限
        if current_user.is_superuser:
            return current_user

        # 2. 法务负责人（legal_admin）可访问全部业务功能
        # 角色描述："企业法务部门负责人，可使用全部业务功能及数据分析"
        user_role_codes = [role.code for role in current_user.roles]
        if "legal_admin" in user_role_codes:
            return current_user

        # 3. 检查用户角色中是否包含所需权限码
        for role in current_user.roles:
            for permission in role.permissions:
                if permission.code == permission_code:
                    return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"缺少必要权限：{permission_code}",
        )

    return check_permission
