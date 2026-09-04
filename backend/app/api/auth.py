"""
智法通 - 认证路由模块

提供用户注册、登录、令牌刷新和获取当前用户信息的API端点。
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
import os
import time

from app.database import get_db
from app.services.auth_service import AuthService
from app.utils.deps import get_current_user
from app.models.user import User
from app.config import settings

router = APIRouter(prefix="/auth", tags=["认证"])


# ==================== 弱密码黑名单 ====================
# 常见弱密码列表，注册时拒绝使用
WEAK_PASSWORDS = {
    "password", "123456", "12345678", "123456789", "1234567890",
    "qwerty", "abc123", "111111", "000000", "admin123",
    "password1", "iloveyou", "sunshine", "letmein",
}


# ==================== 请求/响应模型 ====================

class RegisterRequest(BaseModel):
    """注册请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., min_length=6, max_length=50, description="密码")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """密码强度校验

        拒绝常见弱密码，提升账户安全性。
        密码需至少6位，且不在弱密码黑名单中。

        Args:
            v: 待校验的密码明文

        Returns:
            通过校验的密码

        Raises:
            ValueError: 密码为常见弱密码时抛出
        """
        if v.lower() in WEAK_PASSWORDS:
            raise ValueError("密码过于简单，请使用更复杂的密码")
        return v


class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")


class TokenResponse(BaseModel):
    """令牌响应"""
    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间（秒）")


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求"""
    refresh_token: str = Field(..., description="刷新令牌")


class UserResponse(BaseModel):
    """用户信息响应"""
    id: int
    username: str
    email: str
    phone: Optional[str] = None
    avatar: Optional[str] = None
    is_active: bool = True
    roles: list[str] = []

    class Config:
        from_attributes = True


# ==================== API端点 ====================

@router.post("/register", response_model=TokenResponse, summary="用户注册")
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """用户注册接口

    - 创建新用户账号
    - 自动分配默认角色
    - 返回访问令牌和刷新令牌
    """
    auth_service = AuthService(db)
    result = await auth_service.register(
        username=request.username,
        email=request.email,
        password=request.password,
        phone=request.phone,
    )
    return TokenResponse(**result)


@router.post("/login", response_model=TokenResponse, summary="用户登录")
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """用户登录接口

    - 验证用户名/邮箱和密码
    - 返回访问令牌和刷新令牌
    """
    auth_service = AuthService(db)
    result = await auth_service.login(
        username=request.username,
        password=request.password,
    )
    return TokenResponse(**result)


@router.post("/refresh", response_model=TokenResponse, summary="刷新令牌")
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """刷新访问令牌

    - 使用刷新令牌获取新的访问令牌
    - 刷新令牌本身也会更新
    """
    auth_service = AuthService(db)
    result = await auth_service.refresh_token(request.refresh_token)
    return TokenResponse(**result)


@router.get("/me", response_model=UserResponse, summary="获取当前用户信息")
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """获取当前登录用户的信息

    - 需要在请求头中携带有效的访问令牌
    - 返回用户基本信息和角色列表
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        phone=current_user.phone,
        avatar=current_user.avatar,
        is_active=current_user.is_active,
        roles=[role.code for role in current_user.roles],
    )


# ==================== 个人信息更新 ====================

class UpdateProfileRequest(BaseModel):
    """更新个人信息请求"""
    email: Optional[EmailStr] = Field(None, description="新邮箱")
    phone: Optional[str] = Field(None, max_length=20, description="新手机号")


@router.put("/me", response_model=UserResponse, summary="更新个人信息")
async def update_profile(
    request: UpdateProfileRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新当前用户的个人信息

    - 可更新邮箱和手机号
    - 用户名不可修改
    - 邮箱需保持唯一
    """
    auth_service = AuthService(db)
    try:
        user = await auth_service.update_profile(
            user_id=current_user.id,
            email=request.email,
            phone=request.phone,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        phone=user.phone,
        avatar=user.avatar,
        is_active=user.is_active,
        roles=[role.code for role in user.roles],
    )


# ==================== 头像上传 ====================

# 允许的头像图片扩展名
AVATAR_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
# 头像最大文件大小：5MB
AVATAR_MAX_SIZE = 5 * 1024 * 1024


@router.post("/avatar", response_model=UserResponse, summary="上传用户头像")
async def upload_avatar(
    file: UploadFile = File(..., description="头像图片文件"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传/更新用户头像

    - 支持 PNG、JPG、JPEG、GIF、WEBP 格式
    - 文件大小限制 5MB
    - 上传后自动更新用户头像URL
    - 返回更新后的用户信息
    """
    # 验证文件类型
    file_ext = os.path.splitext(file.filename)[1].lower() if file.filename else ""
    if file_ext not in AVATAR_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的图片格式，允许：{AVATAR_EXTENSIONS}",
        )

    # 读取文件内容并验证大小
    content = await file.read()
    if len(content) > AVATAR_MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="头像文件大小不能超过5MB",
        )

    # 确保头像目录存在
    avatar_dir = os.path.join(settings.UPLOAD_DIR, "avatars")
    os.makedirs(avatar_dir, exist_ok=True)

    # 生成唯一文件名：{user_id}_{timestamp}{ext}
    timestamp = int(time.time() * 1000)
    saved_filename = f"avatar_{current_user.id}_{timestamp}{file_ext}"
    file_path = os.path.join(avatar_dir, saved_filename)

    # 保存文件
    with open(file_path, "wb") as f:
        f.write(content)

    # 构建头像访问URL（通过后端静态文件服务）
    avatar_url = f"/api/v1/uploads/avatars/{saved_filename}"

    # 更新用户头像
    auth_service = AuthService(db)
    user = await auth_service.update_avatar(current_user.id, avatar_url)

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        phone=user.phone,
        avatar=user.avatar,
        is_active=user.is_active,
        roles=[role.code for role in user.roles],
    )


@router.delete("/avatar", response_model=UserResponse, summary="删除用户头像")
async def delete_avatar(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除当前用户头像

    - 清除用户头像URL
    - 同时删除服务器上存储的头像文件
    - 返回更新后的用户信息
    """
    auth_service = AuthService(db)
    user = await auth_service.remove_avatar(current_user.id)
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        phone=user.phone,
        avatar=user.avatar,
        is_active=user.is_active,
        roles=[role.code for role in user.roles],
    )


# ==================== 修改密码 ====================

class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=50, description="新密码")

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """新密码强度校验，拒绝常见弱密码"""
        weak_passwords = {
            "password", "123456", "12345678", "123456789", "qwerty",
            "abc123", "111111", "000000", "admin123", "password1",
        }
        if v.lower() in weak_passwords:
            raise ValueError("新密码过于简单，请使用更复杂的密码")
        return v


@router.put("/password", summary="修改密码")
async def change_password(
    request: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """修改当前用户密码

    - 需要验证旧密码
    - 新密码需至少6位，且不在弱密码黑名单中
    - 修改成功后建议重新登录
    """
    auth_service = AuthService(db)
    try:
        await auth_service.change_password(
            user_id=current_user.id,
            old_password=request.old_password,
            new_password=request.new_password,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    return {"message": "密码修改成功，请重新登录"}
