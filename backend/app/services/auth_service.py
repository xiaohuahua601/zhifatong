"""
智法通 - 认证服务模块

提供JWT令牌生成/验证、密码哈希、用户CRUD等核心认证功能。
"""

from __future__ import annotations

import re
import logging

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from typing import Optional

from app.models.user import User, Role
from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.config import settings

logger = logging.getLogger(__name__)

# ==================== 登录防护配置 ====================
# 登录失败次数上限：连续失败达到该值后锁定账号
LOGIN_FAIL_MAX_ATTEMPTS = 5
# 锁定时长（秒）：与失败计数 Redis key 的 TTL 保持一致
LOGIN_LOCK_TTL_SECONDS = 30 * 60  # 30 分钟
# 登录失败计数 Redis key 前缀
LOGIN_FAIL_KEY_PREFIX = "login_fail"


class AuthService:
    """认证服务类

    封装用户注册、登录、令牌管理等业务逻辑。
    登录方法通过 Redis 计数实现暴力破解防护。
    """

    def __init__(self, db: AsyncSession):
        """初始化认证服务

        Args:
            db: 异步数据库会话
        """
        self.db = db
        # 懒加载 Redis 异步客户端，按全局配置创建
        # 使用 redis.asyncio 模块以支持异步操作
        self._redis: Optional[aioredis.Redis] = None

    @property
    def redis(self) -> aioredis.Redis:
        """获取 Redis 异步客户端（懒加载）

        首次访问时根据 settings 配置创建客户端并缓存，
        后续直接复用。优先使用 settings.REDIS_URL 完整URL。

        Returns:
            Redis 异步客户端实例
        """
        if self._redis is None:
            if settings.REDIS_URL:
                self._redis = aioredis.from_url(
                    settings.REDIS_URL,
                    max_connections=settings.REDIS_POOL_SIZE,
                    decode_responses=True,  # 自动将字节解码为字符串
                )
            else:
                # 兜底：使用主机/端口/密码/DB单独配置创建
                self._redis = aioredis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    password=settings.REDIS_PASSWORD or None,
                    db=settings.REDIS_DB,
                    max_connections=settings.REDIS_POOL_SIZE,
                    decode_responses=True,
                )
        return self._redis

    @staticmethod
    def _validate_password_strength(password: str) -> None:
        """校验密码强度

        密码强度要求：
        1. 长度至少 8 位
        2. 必须同时包含大写字母、小写字母和数字

        Args:
            password: 明文密码

        Raises:
            ValueError: 密码不符合强度要求
        """
        if not password or len(password) < 8:
            raise ValueError("密码强度不足：需至少8位，包含大小写字母和数字")
        # 必须包含大写字母
        if not re.search(r"[A-Z]", password):
            raise ValueError("密码强度不足：需至少8位，包含大小写字母和数字")
        # 必须包含小写字母
        if not re.search(r"[a-z]", password):
            raise ValueError("密码强度不足：需至少8位，包含大小写字母和数字")
        # 必须包含数字
        if not re.search(r"[0-9]", password):
            raise ValueError("密码强度不足：需至少8位，包含大小写字母和数字")

    async def register(
        self,
        username: str,
        email: str,
        password: str,
        phone: Optional[str] = None,
    ) -> dict:
        """用户注册

        创建新用户并自动分配默认角色，返回访问令牌。
        注册前会校验密码强度（P1修复）。

        Args:
            username: 用户名
            email: 邮箱
            password: 明文密码
            phone: 手机号（可选）

        Returns:
            包含访问令牌和刷新令牌的字典

        Raises:
            ValueError: 用户名或邮箱已存在 / 密码强度不足
        """
        # 密码强度校验（P1修复）：在执行任何数据库操作前先校验
        self._validate_password_strength(password)

        # 检查用户名是否已存在
        existing_user = await self.db.execute(
            select(User).where(User.username == username)
        )
        if existing_user.scalar_one_or_none():
            raise ValueError("用户名已存在")

        # 检查邮箱是否已存在
        existing_email = await self.db.execute(
            select(User).where(User.email == email)
        )
        if existing_email.scalar_one_or_none():
            raise ValueError("邮箱已被注册")

        # 创建用户
        user = User(
            username=username,
            email=email,
            hashed_password=hash_password(password),
            phone=phone,
        )
        self.db.add(user)
        await self.db.flush()

        # 分配默认角色（查找"普通用户"角色）
        default_role = await self.db.execute(
            select(Role).where(Role.is_default == True)
        )
        role = default_role.scalar_one_or_none()
        if role:
            # 刷新用户对象以加载roles关系（避免async lazy-load错误）
            await self.db.refresh(user, ["roles"])
            user.roles.append(role)

        await self.db.flush()

        # 生成令牌
        return self._generate_tokens(user.id)

    async def login(self, username: str, password: str) -> dict:
        """用户登录

        验证用户凭证并返回访问令牌。
        实现 Redis 计数暴力破解防护：连续失败5次锁定账号30分钟（P1修复）。

        Args:
            username: 用户名或邮箱
            password: 明文密码

        Returns:
            包含访问令牌和刷新令牌的字典

        Raises:
            ValueError: 账号已锁定 / 用户名或密码错误 / 账号已被禁用
        """
        # ==================== 1. 账号锁定检查（暴力破解防护）====================
        fail_key = f"{LOGIN_FAIL_KEY_PREFIX}:{username}"
        try:
            fail_count = int(await self.redis.get(fail_key) or 0)
        except Exception as e:
            # Redis 异常时降级：不阻止登录，仅记录日志
            logger.warning(f"[AuthService] Redis 查询失败计数异常 key={fail_key}: {e}")
            fail_count = 0

        if fail_count >= LOGIN_FAIL_MAX_ATTEMPTS:
            # 账号已锁定，提示用户稍后重试
            raise ValueError("账号已锁定，请30分钟后再试")

        # ==================== 2. 凭证验证 ====================
        # 支持用户名或邮箱登录
        query = select(User).where(
            (User.username == username) | (User.email == username)
        )
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        # 验证用户存在且密码正确
        if not user or not verify_password(password, user.hashed_password):
            # 登录失败：递增失败计数，并设置 TTL
            await self._record_login_failure(fail_key)
            raise ValueError("用户名或密码错误")

        # 验证用户是否激活
        if not user.is_active:
            # 账号被禁用不计入失败次数
            raise ValueError("账号已被禁用")

        # ==================== 3. 登录成功：清除失败计数 ====================
        try:
            await self.redis.delete(fail_key)
        except Exception as e:
            # 清除失败不影响登录主流程
            logger.warning(f"[AuthService] 清除登录失败计数失败 key={fail_key}: {e}")

        # 更新最后登录时间
        user.last_login = datetime.utcnow()
        await self.db.flush()

        # 生成令牌
        return self._generate_tokens(user.id)

    async def _record_login_failure(self, fail_key: str) -> None:
        """记录一次登录失败

        使用 Redis INCR 原子递增失败计数，首次失败时设置 TTL。
        TTL 与锁定时长一致（30分钟），窗口内无新失败则计数自然过期。

        Args:
            fail_key: 失败计数的 Redis key
        """
        try:
            # 原子递增计数
            new_count = await self.redis.incr(fail_key)
            # 仅在首次失败时设置 TTL，避免每次失败都重置过期时间
            if new_count == 1:
                await self.redis.expire(fail_key, LOGIN_LOCK_TTL_SECONDS)
        except Exception as e:
            # Redis 异常不影响登录失败返回，仅记录日志
            logger.error(f"[AuthService] 记录登录失败计数异常 key={fail_key}: {e}")

    async def refresh_token(self, refresh_token: str) -> dict:
        """刷新访问令牌

        使用刷新令牌获取新的访问令牌。

        Args:
            refresh_token: 刷新令牌

        Returns:
            包含新访问令牌和刷新令牌的字典

        Raises:
            ValueError: 刷新令牌无效或已过期
        """
        # 解码刷新令牌
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise ValueError("无效的刷新令牌")

        # 验证用户是否存在
        user_id = payload.get("sub")
        user = await self.db.get(User, int(user_id))
        if not user or not user.is_active:
            raise ValueError("用户不存在或已被禁用")

        # 生成新令牌
        return self._generate_tokens(user.id)

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """根据ID获取用户

        Args:
            user_id: 用户ID

        Returns:
            用户对象，不存在则返回None
        """
        return await self.db.get(User, user_id)

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户

        Args:
            username: 用户名

        Returns:
            用户对象，不存在则返回None
        """
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def update_profile(
        self,
        user_id: int,
        email: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> User:
        """更新用户个人信息

        Args:
            user_id: 用户ID
            email: 新邮箱（可选）
            phone: 新手机号（可选）

        Returns:
            更新后的用户对象

        Raises:
            ValueError: 邮箱已被其他用户使用
        """
        user = await self.db.get(User, user_id)
        if not user:
            raise ValueError("用户不存在")

        # 邮箱唯一性校验
        if email and email != user.email:
            existing = await self.db.execute(
                select(User).where(User.email == email, User.id != user_id)
            )
            if existing.scalar_one_or_none():
                raise ValueError("该邮箱已被其他用户使用")
            user.email = email

        if phone is not None:
            user.phone = phone

        await self.db.flush()
        # 刷新以加载roles关系
        await self.db.refresh(user, ["roles"])

        # 失效用户缓存：个人信息变更后，后续请求应重新加载最新数据
        from app.utils.deps import invalidate_user_cache
        invalidate_user_cache(user_id)
        return user

    async def update_avatar(self, user_id: int, avatar_url: str) -> User:
        """更新用户头像

        Args:
            user_id: 用户ID
            avatar_url: 头像访问URL路径

        Returns:
            更新后的用户对象
        """
        user = await self.db.get(User, user_id)
        if not user:
            raise ValueError("用户不存在")

        user.avatar = avatar_url
        await self.db.flush()
        await self.db.refresh(user, ["roles"])

        # 失效用户缓存：头像变更后，后续请求应重新加载最新数据
        from app.utils.deps import invalidate_user_cache
        invalidate_user_cache(user_id)
        return user

    async def remove_avatar(self, user_id: int) -> User:
        """删除用户头像

        清除用户头像URL字段。若用户当前头像对应本地文件，
        尝试删除该文件以释放存储空间（失败时静默忽略，不影响数据库操作）。

        Args:
            user_id: 用户ID

        Returns:
            更新后的用户对象

        Raises:
            ValueError: 用户不存在
        """
        import os
        from app.config import settings

        user = await self.db.get(User, user_id)
        if not user:
            raise ValueError("用户不存在")

        # 尝试删除本地头像文件（仅清理 /uploads/avatars/ 下的本地文件）
        old_avatar = user.avatar
        if old_avatar and "/uploads/avatars/" in old_avatar:
            try:
                # 从URL路径提取实际文件名
                filename = old_avatar.split("/avatars/")[-1]
                file_path = os.path.join(settings.UPLOAD_DIR, "avatars", filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
            except OSError:
                # 文件删除失败不影响业务流程
                pass

        user.avatar = None
        await self.db.flush()
        await self.db.refresh(user, ["roles"])

        # 失效用户缓存：头像删除后，后续请求应重新加载最新数据
        from app.utils.deps import invalidate_user_cache
        invalidate_user_cache(user_id)
        return user

    async def change_password(
        self,
        user_id: int,
        old_password: str,
        new_password: str,
    ) -> None:
        """修改用户密码

        修改前会校验新密码强度（与注册一致，防止密码降级为弱口令），
        修改后会失效该用户的本地缓存，确保后续请求重新加载最新身份信息。

        Args:
            user_id: 用户ID
            old_password: 旧密码明文
            new_password: 新密码明文

        Raises:
            ValueError: 用户不存在 / 旧密码错误 / 新密码强度不足
        """
        # 新密码强度校验（与注册一致，防止通过改密降级为弱口令）
        self._validate_password_strength(new_password)

        user = await self.db.get(User, user_id)
        if not user:
            raise ValueError("用户不存在")

        # 验证旧密码
        if not verify_password(old_password, user.hashed_password):
            raise ValueError("旧密码错误")

        # 更新密码
        user.hashed_password = hash_password(new_password)
        await self.db.flush()

        # 失效用户缓存：密码变更后，后续请求应重新从数据库加载用户身份
        # 注意：进程内缓存仅对当前 worker 生效，多 worker 场景下其他 worker
        # 会在 TTL(60s) 内自然过期，如需即时失效可引入 Redis pub/sub 广播
        from app.utils.deps import invalidate_user_cache
        invalidate_user_cache(user_id)

    def _generate_tokens(self, user_id: int) -> dict:
        """生成访问令牌和刷新令牌

        Args:
            user_id: 用户ID

        Returns:
            包含令牌信息的字典
        """
        # 访问令牌
        access_token = create_access_token(
            data={"sub": str(user_id)},
            expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        # 刷新令牌
        refresh_token = create_refresh_token(
            data={"sub": str(user_id)},
            expires_delta=timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }
