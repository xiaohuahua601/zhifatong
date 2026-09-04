"""
智法通 - 用户管理路由模块（管理员专用）

提供用户CRUD、角色分配、状态管理等管理员功能。
所有接口均需超级管理员权限（is_superuser=True）。

RBAC权限策略：
- admin（超级管理员）：可访问全部用户管理接口
- legal_admin（法务负责人）：无用户管理权限
- user（普通用户）：无用户管理权限
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.models.user import User, Role, user_role
from app.utils.deps import get_current_superuser, invalidate_user_cache
from app.utils.security import hash_password

router = APIRouter(prefix="/users", tags=["用户管理"])


# ==================== 弱密码黑名单 ====================
WEAK_PASSWORDS = {
    "password", "123456", "12345678", "123456789", "1234567890",
    "qwerty", "abc123", "111111", "000000", "admin123",
    "password1", "iloveyou", "sunshine", "letmein",
}


# ==================== 请求/响应模型 ====================

class UserCreateRequest(BaseModel):
    """管理员创建用户请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., min_length=6, max_length=50, description="密码")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    role_codes: list[str] = Field(default=["user"], description="角色编码列表")
    is_active: bool = Field(default=True, description="是否启用")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """密码强度校验，拒绝常见弱密码"""
        if v.lower() in WEAK_PASSWORDS:
            raise ValueError("密码过于简单，请使用更复杂的密码")
        return v


class UserUpdateRequest(BaseModel):
    """管理员编辑用户请求"""
    email: Optional[EmailStr] = Field(None, description="新邮箱")
    phone: Optional[str] = Field(None, max_length=20, description="新手机号")
    is_active: Optional[bool] = Field(None, description="是否启用")


class RoleAssignRequest(BaseModel):
    """角色分配请求"""
    role_codes: list[str] = Field(..., description="角色编码列表（会完全替换现有角色）")


class UserStatusRequest(BaseModel):
    """用户状态切换请求"""
    is_active: bool = Field(..., description="目标状态：True启用/False禁用")


class RoleResponse(BaseModel):
    """角色信息响应"""
    id: int
    name: str
    code: str
    description: Optional[str] = None
    is_default: bool = False

    class Config:
        from_attributes = True


class UserManageResponse(BaseModel):
    """用户管理列表项响应"""
    id: int
    username: str
    email: str
    phone: Optional[str] = None
    avatar: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False
    last_login: Optional[datetime] = None
    created_at: datetime
    roles: list[RoleResponse] = []

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """用户列表分页响应"""
    total: int
    page: int
    page_size: int
    items: list[UserManageResponse]


# ==================== 辅助函数 ====================

async def _get_user_with_roles(db: AsyncSession, user_id: int) -> Optional[User]:
    """根据ID查询用户（预加载角色关系）

    Args:
        db: 异步数据库会话
        user_id: 用户ID

    Returns:
        用户对象（含roles），不存在返回None
    """
    result = await db.execute(
        select(User)
        .options(selectinload(User.roles))
        .where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def _get_roles_by_codes(db: AsyncSession, role_codes: list[str]) -> list[Role]:
    """根据角色编码列表查询角色对象

    Args:
        db: 异步数据库会话
        role_codes: 角色编码列表（如 ["admin", "user"]）

    Returns:
        角色对象列表

    Raises:
        HTTPException: 角色编码不存在时抛出400错误
    """
    result = await db.execute(
        select(Role).where(Role.code.in_(role_codes))
    )
    roles = result.scalars().all()
    # 校验：所有请求的角色编码都必须存在
    found_codes = {r.code for r in roles}
    missing_codes = set(role_codes) - found_codes
    if missing_codes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"角色编码不存在：{', '.join(missing_codes)}",
        )
    return list(roles)


# ==================== API端点 ====================

@router.get("", response_model=UserListResponse, summary="用户列表（管理员专用）")
async def list_users(
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量，1-100"),
    keyword: Optional[str] = Query(None, description="搜索关键词（用户名/邮箱/手机号）"),
    role_code: Optional[str] = Query(None, description="按角色编码筛选"),
    is_active: Optional[bool] = Query(None, description="按状态筛选：True启用/False禁用"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """获取用户列表（分页+搜索+筛选）

    支持按用户名/邮箱/手机号模糊搜索，按角色和状态筛选。
    仅超级管理员可访问。

    Args:
        page: 页码
        page_size: 每页数量
        keyword: 搜索关键词
        role_code: 角色编码筛选
        is_active: 状态筛选
        db: 数据库会话
        current_user: 当前超级管理员

    Returns:
        分页用户列表
    """
    # 构建基础查询
    query = select(User).options(selectinload(User.roles))

    # 关键词搜索（用户名/邮箱/手机号）
    if keyword:
        like_pattern = f"%{keyword}%"
        query = query.where(
            or_(
                User.username.ilike(like_pattern),
                User.email.ilike(like_pattern),
                User.phone.ilike(like_pattern),
            )
        )

    # 状态筛选
    if is_active is not None:
        query = query.where(User.is_active == is_active)

    # 角色筛选（通过子查询关联user_role表）
    if role_code:
        query = query.join(user_role, user_role.c.user_id == User.id) \
                     .join(Role, Role.id == user_role.c.role_id) \
                     .where(Role.code == role_code)

    # 统计总数（不含分页）
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页查询
    query = query.order_by(User.created_at.desc()) \
                 .offset((page - 1) * page_size) \
                 .limit(page_size)
    result = await db.execute(query)
    users = result.scalars().unique().all()

    return UserListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[UserManageResponse.model_validate(u) for u in users],
    )


@router.get("/roles", response_model=list[RoleResponse], summary="角色列表（管理员专用）")
async def list_roles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """获取所有角色列表

    用于用户管理界面的角色分配下拉框。
    仅超级管理员可访问。

    Returns:
        角色列表
    """
    result = await db.execute(select(Role).order_by(Role.id))
    roles = result.scalars().all()
    return [RoleResponse.model_validate(r) for r in roles]


@router.post("", response_model=UserManageResponse, summary="创建用户（管理员专用）")
async def create_user(
    request: UserCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """管理员创建用户

    - 可指定用户名、邮箱、密码、手机号
    - 可分配多个角色
    - 可设置初始启用状态

    Args:
        request: 创建用户请求
        db: 数据库会话
        current_user: 当前超级管理员

    Returns:
        创建的用户信息

    Raises:
        HTTPException: 用户名/邮箱/手机号已存在
    """
    # 校验用户名唯一性
    existing = await db.execute(select(User).where(User.username == request.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在")

    # 校验邮箱唯一性
    existing = await db.execute(select(User).where(User.email == request.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已存在")

    # 校验手机号唯一性（如果提供了手机号）
    if request.phone:
        existing = await db.execute(select(User).where(User.phone == request.phone))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="手机号已存在")

    # 查询角色对象
    roles = await _get_roles_by_codes(db, request.role_codes)

    # 创建用户
    user = User(
        username=request.username,
        email=request.email,
        hashed_password=hash_password(request.password),
        phone=request.phone,
        is_active=request.is_active,
        is_superuser=False,  # 管理员创建的用户默认不是超级管理员
    )
    user.roles = roles
    db.add(user)
    await db.flush()
    await db.refresh(user, ["roles"])

    return UserManageResponse.model_validate(user)


@router.put("/{user_id}/roles", response_model=UserManageResponse, summary="分配角色（管理员专用）")
async def assign_roles(
    user_id: int,
    request: RoleAssignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """为用户分配角色（完全替换现有角色）

    Args:
        user_id: 目标用户ID
        request: 角色分配请求
        db: 数据库会话
        current_user: 当前超级管理员

    Returns:
        更新后的用户信息

    Raises:
        HTTPException: 用户不存在
    """
    user = await _get_user_with_roles(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    # 防止管理员取消自己的admin角色（避免系统无管理员）
    if current_user.id == user_id and "admin" not in request.role_codes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能取消当前登录管理员的admin角色，避免系统无管理员",
        )

    # 查询角色对象并完全替换
    roles = await _get_roles_by_codes(db, request.role_codes)
    user.roles = roles
    await db.flush()
    await db.refresh(user, ["roles"])

    # 角色变更后使用户缓存失效（确保权限立即生效）
    invalidate_user_cache(user_id)

    return UserManageResponse.model_validate(user)


@router.put("/{user_id}/status", response_model=UserManageResponse, summary="切换用户状态（管理员专用）")
async def update_user_status(
    user_id: int,
    request: UserStatusRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """启用/禁用用户账号

    Args:
        user_id: 目标用户ID
        request: 状态切换请求
        db: 数据库会话
        current_user: 当前超级管理员

    Returns:
        更新后的用户信息

    Raises:
        HTTPException: 用户不存在 / 禁用自己
    """
    # 防止管理员禁用自己
    if current_user.id == user_id and not request.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能禁用当前登录的管理员账号",
        )

    user = await _get_user_with_roles(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    user.is_active = request.is_active
    await db.flush()
    await db.refresh(user, ["roles"])

    # 状态变更后使用户缓存失效（确保禁用立即生效）
    invalidate_user_cache(user_id)

    return UserManageResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserManageResponse, summary="编辑用户信息（管理员专用）")
async def update_user(
    user_id: int,
    request: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """管理员编辑用户信息（邮箱/手机号/状态）

    Args:
        user_id: 目标用户ID
        request: 编辑请求
        db: 数据库会话
        current_user: 当前超级管理员

    Returns:
        更新后的用户信息

    Raises:
        HTTPException: 用户不存在 / 邮箱/手机号已被占用
    """
    user = await _get_user_with_roles(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    # 更新邮箱（校验唯一性）
    if request.email and request.email != user.email:
        existing = await db.execute(select(User).where(User.email == request.email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已被占用")
        user.email = request.email

    # 更新手机号（校验唯一性）
    if request.phone is not None and request.phone != (user.phone or ""):
        if request.phone:
            existing = await db.execute(select(User).where(User.phone == request.phone))
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="手机号已被占用")
        user.phone = request.phone or None

    # 更新状态
    if request.is_active is not None:
        if current_user.id == user_id and not request.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不能禁用当前登录的管理员账号",
            )
        user.is_active = request.is_active

    await db.flush()
    await db.refresh(user, ["roles"])

    # 用户信息变更后使用户缓存失效
    invalidate_user_cache(user_id)

    return UserManageResponse.model_validate(user)


@router.delete("/{user_id}", summary="删除用户（管理员专用）")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """删除用户

    - 物理删除用户记录（关联角色关系通过外键CASCADE自动清理）
    - 防止管理员删除自己

    Args:
        user_id: 目标用户ID
        db: 数据库会话
        current_user: 当前超级管理员

    Returns:
        删除成功消息

    Raises:
        HTTPException: 用户不存在 / 删除自己
    """
    # 防止管理员删除自己
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除当前登录的管理员账号",
        )

    user = await _get_user_with_roles(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    username = user.username
    await db.delete(user)
    await db.flush()

    # 删除用户后使其缓存失效
    invalidate_user_cache(user_id)

    return {"message": f"用户 {username} 已删除"}


@router.post("/{user_id}/reset-password", summary="重置用户密码（管理员专用）")
async def reset_user_password(
    user_id: int,
    new_password: str = Query(..., min_length=6, max_length=50, description="新密码"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """管理员重置用户密码

    - 管理员无需旧密码即可重置任意用户密码
    - 新密码需通过弱密码校验

    Args:
        user_id: 目标用户ID
        new_password: 新密码
        db: 数据库会话
        current_user: 当前超级管理员

    Returns:
        重置成功消息

    Raises:
        HTTPException: 用户不存在 / 密码过于简单
    """
    # 弱密码校验
    if new_password.lower() in WEAK_PASSWORDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="新密码过于简单，请使用更复杂的密码",
        )

    user = await _get_user_with_roles(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    user.hashed_password = hash_password(new_password)
    await db.flush()

    return {"message": f"用户 {user.username} 的密码已重置"}
