"""
智法通 - 数据库连接管理模块

使用 SQLAlchemy 2.0 异步ORM，配合 aiomysql 异步驱动，
提供数据库引擎、会话工厂和依赖注入函数。
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator

from app.config import settings


# ==================== 异步数据库引擎 ====================
# 创建异步引擎，配置连接池和超时参数
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,           # 连接池大小
    max_overflow=settings.DB_MAX_OVERFLOW,     # 最大溢出连接数
    pool_recycle=settings.DB_POOL_RECYCLE,     # 连接回收时间
    echo=settings.DB_ECHO,                     # 是否打印SQL
    pool_pre_ping=True,                        # 连接前检测可用性
)

# ==================== 异步会话工厂 ====================
# 创建异步会话工厂，用于生成数据库会话
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,   # 提交后不过期对象，避免懒加载问题
)


# ==================== ORM基类 ====================
class Base(DeclarativeBase):
    """SQLAlchemy声明式基类

    所有模型类都应继承此类，以获得ORM映射能力。
    """
    pass


# ==================== 依赖注入：获取数据库会话 ====================
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取异步数据库会话

    作为FastAPI依赖注入使用，确保每个请求使用独立的数据库会话，
    请求结束后自动关闭会话。

    用法:
        @router.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()      # 请求成功时自动提交
        except Exception:
            await session.rollback()    # 发生异常时回滚
            raise
        finally:
            await session.close()       # 确保会话关闭
