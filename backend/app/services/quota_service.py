"""
智法通 - 用户额度管理服务模块

基于Redis原子计数器实现用户每日使用额度管理，按自然日重置。
支持多资源类型独立计数，管理员角色不限额度。

设计要点：
1. 使用 Redis INCR 原子命令实现并发安全的计数
2. Redis key 中包含日期（YYYY-MM-DD），按自然日重置
3. TTL 设置为次日 0 点过期，避免内存泄漏
4. 管理员（is_superuser=True 或 角色编码为 admin）不限额度
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Optional

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User, Role

logger = logging.getLogger(__name__)


# ==================== 资源类型与额度配置 ====================

# 各资源类型的每日额度上限（普通用户）
# qa: 法律问答 50次/日
# contract: 合同审查 10份/日
RESOURCE_DAILY_LIMITS: dict[str, int] = {
    "qa": 50,
    "contract": 10,
}

# 管理员角色编码（拥有此角色或 is_superuser=True 的用户不限额度）
ADMIN_ROLE_CODE = "admin"


class QuotaService:
    """用户额度管理服务类

    封装用户每日使用额度的查询与扣减逻辑，
    使用 Redis 原子计数器保证并发安全。

    使用示例：
        quota_svc = QuotaService(db, redis_client)
        allowed, remaining, limit = await quota_svc.check_and_consume(user_id, "qa")
        if not allowed:
            raise ValueError(f"今日额度已用完，剩余 {remaining}/{limit}")
    """

    def __init__(self, db: AsyncSession, redis_client: Optional[aioredis.Redis] = None):
        """初始化额度服务

        Args:
            db: 异步数据库会话（用于查询用户角色判断是否管理员）
            redis_client: 可选的Redis异步客户端，未提供时按配置自动创建
        """
        self.db = db
        # 复用传入的Redis客户端，或按配置创建新客户端
        self._redis = redis_client or self._create_redis_client()

    def _create_redis_client(self) -> aioredis.Redis:
        """根据全局配置创建Redis异步客户端

        优先使用 settings.REDIS_URL（完整URL），否则使用各组件配置拼接。

        Returns:
            Redis异步客户端实例
        """
        if settings.REDIS_URL:
            # 从完整URL创建（解析连接池配置）
            return aioredis.from_url(
                settings.REDIS_URL,
                max_connections=settings.REDIS_POOL_SIZE,
                decode_responses=True,  # 自动将字节解码为字符串
            )
        # 兜底：使用主机/端口/密码/DB单独配置创建
        return aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD or None,
            db=settings.REDIS_DB,
            max_connections=settings.REDIS_POOL_SIZE,
            decode_responses=True,
        )

    async def _is_admin(self, user_id: int) -> bool:
        """判断指定用户是否为管理员（不限额度）

        管理员判定规则（满足任一即视为管理员）：
        1. User.is_superuser 字段为 True（超级管理员标记）
        2. 用户关联的角色中存在 code == "admin" 的角色

        Args:
            user_id: 用户ID

        Returns:
            True 表示是管理员（不限额度），False 表示普通用户
        """
        # 查询用户及其角色关系（selectinload避免异步懒加载错误）
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            # 用户不存在时按非管理员处理，由调用方决定如何应对
            return False

        # 规则1：超级管理员标记
        if user.is_superuser:
            return True

        # 规则2：拥有 admin 角色编码
        for role in user.roles:
            if isinstance(role, Role) and role.code == ADMIN_ROLE_CODE:
                return True
        return False

    @staticmethod
    def _build_key(user_id: int, resource_type: str, day: Optional[date] = None) -> str:
        """构建Redis计数key

        key格式：quota:{user_id}:{resource_type}:{YYYY-MM-DD}
        通过日期分段实现按自然日重置。

        Args:
            user_id: 用户ID
            resource_type: 资源类型（qa/contract）
            day: 指定日期，默认为当天

        Returns:
            Redis key 字符串
        """
        day = day or date.today()
        return f"quota:{user_id}:{resource_type}:{day.isoformat()}"

    @staticmethod
    def _calc_ttl_seconds() -> int:
        """计算key的TTL（秒），使其在次日0点过期

        计算方式：次日0点 - 当前时间，转换为秒数。
        至少保留1秒，避免边界情况下TTL为0导致key立即过期。

        Returns:
            TTL秒数
        """
        now = datetime.now()
        # 次日0点
        tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        ttl = int((tomorrow - now).total_seconds())
        # 保证至少1秒，避免在23:59:59等边界场景TTL为0或负数
        return max(1, ttl)

    async def check_and_consume(
        self,
        user_id: int,
        resource_type: str,
    ) -> tuple[bool, int, int]:
        """检查并扣减用户额度（原子操作）

        在单次Redis调用中完成"检查+扣减"，避免并发条件下的超额问题。
        使用 INCR 原子命令：首次调用时key自增为1，后续调用累加。

        管理员用户直接放行，不写入Redis计数。

        Args:
            user_id: 用户ID
            resource_type: 资源类型（qa/contract）

        Returns:
            三元组 (allowed, remaining, limit)：
            - allowed: 是否允许本次调用
            - remaining: 调用后的剩余次数（管理员返回 -1 表示不限）
            - limit: 每日额度上限（管理员返回 -1 表示不限）
        """
        # 校验资源类型，避免无效类型绕过限制
        if resource_type not in RESOURCE_DAILY_LIMITS:
            raise ValueError(f"未知的资源类型: {resource_type}")

        limit = RESOURCE_DAILY_LIMITS[resource_type]

        # 管理员不限额度
        if await self._is_admin(user_id):
            # 返回 -1 表示不限额，前端可据此隐藏额度提示
            return True, -1, -1

        key = self._build_key(user_id, resource_type)

        try:
            # 原子自增：首次会从0自增到1
            # 使用 pipeline 确保 INCR 与 EXPIRE 在一次往返中完成
            pipe = self._redis.pipeline()
            pipe.incr(key)
            pipe.expire(key, self._calc_ttl_seconds())
            results = await pipe.execute()
            used = int(results[0])  # INCR 返回自增后的值
        except Exception as e:
            # Redis 异常时降级处理：记录日志并放行，避免影响主业务流程
            logger.error(f"[QuotaService] Redis 计数异常 user={user_id} "
                         f"resource={resource_type}: {e}")
            return True, limit - 1, limit

        # 判断是否超额
        if used > limit:
            # 超额：本次调用应被拒绝
            # 注意：INCR 已自增，需回滚计数以保证下次查询的准确性
            try:
                await self._redis.decr(key)
            except Exception as e:
                logger.warning(f"[QuotaService] 回滚计数失败 key={key}: {e}")
            return False, 0, limit

        # 允许调用，计算剩余次数
        remaining = limit - used
        return True, remaining, limit

    async def get_quota(
        self,
        user_id: int,
        resource_type: str,
    ) -> tuple[int, int, int]:
        """查询用户当日额度使用情况（不扣减）

        Args:
            user_id: 用户ID
            resource_type: 资源类型（qa/contract）

        Returns:
            三元组 (used, remaining, limit)：
            - used: 当日已使用次数（管理员返回 0）
            - remaining: 当日剩余次数（管理员返回 -1 表示不限）
            - limit: 每日额度上限（管理员返回 -1 表示不限）
        """
        # 校验资源类型
        if resource_type not in RESOURCE_DAILY_LIMITS:
            raise ValueError(f"未知的资源类型: {resource_type}")

        limit = RESOURCE_DAILY_LIMITS[resource_type]

        # 管理员不限额度
        if await self._is_admin(user_id):
            return 0, -1, -1

        key = self._build_key(user_id, resource_type)
        try:
            used = int(await self._redis.get(key) or 0)
        except Exception as e:
            # Redis 异常时降级：返回满额度，避免误拒
            logger.error(f"[QuotaService] Redis 查询异常 user={user_id} "
                         f"resource={resource_type}: {e}")
            return 0, limit, limit

        # 处理异常情况（理论上不应出现 used > limit）
        if used >= limit:
            return used, 0, limit
        return used, limit - used, limit
