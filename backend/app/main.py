"""
智法通 - 企业级智能法律顾问平台 FastAPI应用入口

包含应用初始化、CORS配置、路由注册、
生命周期管理和全局异常处理。
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
import time
import asyncio

from app.config import settings
from app.database import engine, Base

# ==================== 日志配置 ====================
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def _build_chroma_index():
    """构建ChromaDB索引（从MySQL法律文档到向量数据库）

    将MySQL中的法律文档分块、向量化后写入ChromaDB。
    使用配置的Embedding模型（bge-large-zh-v1.5）生成1024维向量。

    调用时机：
        - 首次启动时集合为空
        - 切换Embedding模型导致维度变更后旧索引被清除

    注意：此函数会调用Ollama embedding API，如果Ollama不可用会降级到本地哈希向量。
    """
    from app.database import async_session_factory
    from app.models.knowledge import LegalDocument, DocumentChunk
    from app.rag.vector_store import ChromaVectorStore
    from app.rag.embedding import EmbeddingService
    from sqlalchemy import select

    async with async_session_factory() as db:
        # 查询所有有内容的法律文档
        result = await db.execute(
            select(LegalDocument).where(LegalDocument.content.isnot(None))
        )
        documents = result.scalars().all()

        if not documents:
            logger.warning("⚠️ 无可索引的法律文档，跳过索引构建")
            return

        logger.info(f"📄 找到 {len(documents)} 个文档需要索引")

        vector_store = ChromaVectorStore()
        embedding_service = EmbeddingService()
        total_chunks = 0

        for doc in documents:
            # 查询该文档的分块
            chunk_result = await db.execute(
                select(DocumentChunk)
                .where(DocumentChunk.document_id == doc.id)
                .order_by(DocumentChunk.chunk_index)
            )
            chunks = chunk_result.scalars().all()

            if not chunks:
                # 无分块记录时按固定大小切分
                content = doc.content or ""
                chunk_size = settings.RAG_CHUNK_SIZE
                chunk_texts = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
            else:
                chunk_texts = [c.content for c in chunks]

            # 批量生成embedding并写入ChromaDB
            ids = []
            embeddings = []
            documents_text = []
            metadatas = []

            for idx, chunk_text in enumerate(chunk_texts):
                if not chunk_text.strip():
                    continue
                embedding = await embedding_service.embed_text(chunk_text)
                vector_id = f"doc_{doc.id}_chunk_{idx}"
                ids.append(vector_id)
                embeddings.append(embedding)
                documents_text.append(chunk_text)
                metadatas.append({
                    "document_id": doc.id,
                    "chunk_index": idx,
                    "doc_type": doc.doc_type or "法律",
                    "title": doc.title,
                    "law_name": doc.title,
                    "effectiveness": "有效",
                })

            if ids:
                vector_store.add(
                    ids=ids,
                    documents=documents_text,
                    embeddings=embeddings,
                    metadatas=metadatas,
                )
                total_chunks += len(ids)
                logger.info(f"  📝 {doc.title}: 索引 {len(ids)} 个分块")

        logger.info(f"✅ 索引构建完成，共 {total_chunks} 个分块")


# ==================== 生命周期管理 ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理

    启动时：初始化数据库连接、创建表结构
    关闭时：关闭数据库连接
    """
    # ===== 启动阶段 =====
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 启动中...")

    # ---- 第一步：等待数据库就绪 ----
    # 容器编排场景下，MySQL首次启动需要执行初始化脚本并预热InnoDB，
    # 健康检查(mysqladmin ping)通过后仍可能短暂拒绝业务连接。
    # 此处以指数退避方式轮询连接，最多等待约60秒，确保建表前数据库可达。
    import time as _time
    from sqlalchemy import text
    db_ready = False
    max_conn_retries = 10
    for attempt in range(max_conn_retries):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            db_ready = True
            logger.info("✅ 数据库连接就绪")
            break
        except Exception as e:
            wait_sec = min(3 * (attempt + 1), 10)
            logger.warning(
                f"⏳ 等待数据库就绪...（第 {attempt + 1}/{max_conn_retries} 次尝试，"
                f"{wait_sec}s 后重试）：{e}"
            )
            _time.sleep(wait_sec)
    if not db_ready:
        # 数据库最终不可达属致命错误：记录后仍继续启动（保持健康检查可观测），
        # 但表结构与种子数据将缺失，需依赖下方重试机制或人工介入
        logger.error("❌ 数据库连接超时，表结构初始化将失败")

    # ---- 第二步：创建数据库表 ----
    # 创建数据库表（开发环境使用，生产环境应使用Alembic迁移）
    # 使用 checkfirst=True（默认）确保表已存在时跳过创建
    # 多worker并发启动时可能出现"Table already exists"竞争，需捕获并继续
    try:
        async with engine.begin() as conn:
            # 导入所有模型以确保Base.metadata包含所有表定义
            import app.models  # noqa: F401
            import app.models.notification  # noqa: F401
            # 分别创建每张表，避免单张表失败影响其他表创建
            # checkfirst=True 确保幂等，但并发场景下仍需捕获异常
            await conn.run_sync(Base.metadata.create_all, checkfirst=True)
        logger.info("✅ 数据库表结构初始化完成")
    except Exception as e:
        # 并发worker竞争时可能报"Table already exists"，属于预期行为，仅记录警告
        err_msg = str(e)
        if "already exists" in err_msg:
            logger.warning(f"⚠️ 数据库表已存在（多worker并发建表，属正常现象）：{e}")
        else:
            logger.error(f"❌ 数据库初始化失败：{e}")

    # 注入种子数据（角色、内置账号、示例法条、欢迎通知）
    # 幂等设计：重复启动不会产生重复数据
    # 多worker并发时，重试机制确保表结构就绪后再注入种子数据
    import time
    max_table_retries = 5
    for retry in range(max_table_retries):
        try:
            from app.database import async_session_factory
            from app.init_data import init_seed_data
            async with async_session_factory() as seed_session:
                await init_seed_data(seed_session)
            logger.info("✅ 种子数据初始化完成")
            break
        except Exception as e:
            err_msg = str(e)
            # 表未创建完成或数据库连接尚未就绪时，均等待后重试（幂等）
            retryable = ("doesn't exist" in err_msg) or ("Can't connect" in err_msg) or ("Connection refused" in err_msg)
            if retryable and retry < max_table_retries - 1:
                # 表尚未创建完成（多worker并发建表延迟）或连接未就绪，等待后重试
                logger.warning(f"⏳ 等待表结构/连接就绪...（第 {retry+1}/{max_table_retries} 次重试）")
                time.sleep(3)
                # 重试前再次确保表结构
                try:
                    async with engine.begin() as conn:
                        import app.models  # noqa: F401
                        import app.models.notification  # noqa: F401
                        await conn.run_sync(Base.metadata.create_all, checkfirst=True)
                except Exception:
                    pass
            else:
                logger.error(f"❌ 种子数据初始化失败：{e}", exc_info=True)
                break

    # 确保必要目录存在
    import os
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
    logger.info("✅ 目录初始化完成")

    # ChromaDB索引自动构建：如果集合为空或维度不匹配，自动构建索引
    # 场景：首次启动、切换Embedding模型后（维度变更导致旧索引被清除）
    # 多worker并发保护：使用Redis分布式锁（SET NX EX）确保仅一个worker执行构建，
    # 其余worker短暂等待锁释放后重新检查集合数量，避免并发重建导致
    # "Collection does not exist"告警与重复的Embedding计算开销
    try:
        from app.rag.vector_store import ChromaVectorStore
        vector_store = ChromaVectorStore()
        doc_count = vector_store.count()

        # 尝试获取索引构建锁（锁持有时间300s，覆盖正常构建耗时）
        import redis.asyncio as aioredis
        lock_acquired = False
        redis_client = None
        try:
            redis_client = aioredis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                socket_connect_timeout=2,
            )
            lock_acquired = await redis_client.set(
                "zhifatong:chroma_index_build_lock", "1", nx=True, ex=300
            )
        except Exception as lock_err:
            # Redis不可用时降级为无锁模式（维持旧行为，功能不受影响）
            logger.warning(f"⚠️ 索引构建锁获取失败（降级为无锁模式）：{lock_err}")

        try:
            if doc_count == 0:
                if lock_acquired:
                    logger.info("📦 ChromaDB集合为空，开始构建索引...")
                    await _build_chroma_index()
                else:
                    # 未抢到锁：等待持锁worker完成构建后复查
                    logger.info("⏳ 其他worker正在构建索引，等待其完成...")
                    for _ in range(60):
                        await asyncio.sleep(5)
                        if vector_store.count() > 0:
                            logger.info(f"✅ 索引已由其他worker构建（{vector_store.count()} 条）")
                            break
                    else:
                        logger.warning("⚠️ 等待索引构建超时，本worker跳过构建")
            else:
                logger.info(f"✅ ChromaDB已有 {doc_count} 条向量索引")
        finally:
            # 释放锁（仅持锁worker），连接无论成功与否均关闭
            if lock_acquired and redis_client is not None:
                try:
                    await redis_client.delete("zhifatong:chroma_index_build_lock")
                except Exception:
                    pass
            if redis_client is not None:
                try:
                    await redis_client.aclose()
                except Exception:
                    pass
    except Exception as e:
        logger.warning(f"⚠️ ChromaDB索引构建跳过: {e}")

    # Neo4j法律知识图谱初始化：空图时自动从本地法律数据构建（幂等）
    # 非阻塞设计：Neo4j不可用时仅降级为内存模式，不影响服务启动
    if settings.NEO4J_ENABLED:
        try:
            from app.services.graph_service import ensure_graph_built, close_driver
            graph_ready = await ensure_graph_built()
            if graph_ready:
                logger.info("✅ Neo4j知识图谱就绪")
            else:
                logger.warning("⚠️ Neo4j知识图谱未就绪，已降级为内存模式（可稍后POST /graph/build重建）")
            await close_driver()
        except Exception as e:
            logger.warning(f"⚠️ Neo4j知识图谱初始化跳过：{e}")

    logger.info(f"🎉 {settings.APP_NAME} 启动完成！")

    yield  # 应用运行中

    # ===== 关闭阶段 =====
    logger.info(f"🛑 {settings.APP_NAME} 正在关闭...")

    # 关闭数据库引擎
    await engine.dispose()
    logger.info("✅ 数据库连接已关闭")

    logger.info(f"👋 {settings.APP_NAME} 已关闭")


# ==================== 创建FastAPI应用 ====================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    智法通 - 企业级智能法律顾问平台 API

    ## 功能模块
    - 🔐 认证管理：用户注册、登录、令牌管理
    - ⚖️ 法律问答：智能法律咨询、多轮对话
    - 📋 合同审查：AI合同风险检测、合规性检查
    - 📚 知识库：法律文档管理、语义检索
    - 📊 数据分析：热点分析、引用统计、用户聚类
    - 📈 仪表盘：概览统计、趋势数据
    """,
    lifespan=lifespan,
    docs_url="/docs",            # Swagger UI地址
    redoc_url="/redoc",          # ReDoc地址
    openapi_url="/openapi.json", # OpenAPI规范地址
)


# ==================== CORS中间件配置 ====================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,       # 允许的来源
    allow_credentials=True,                     # 允许携带凭证
    allow_methods=["*"],                        # 允许所有HTTP方法
    allow_headers=["*"],                        # 允许所有请求头
)


# ==================== 请求计时中间件 ====================

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """添加请求处理时间到响应头"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(round(process_time * 1000, 2)) + "ms"
    return response


# ==================== 全局异常处理 ====================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """请求参数验证异常处理

    将Pydantic验证错误转换为JSON可序列化格式，
    处理field_validator中ValueError对象无法序列化的问题。
    """
    logger.warning(f"参数验证失败：{exc.errors()}")
    # 使用jsonable_encoder将错误详情转换为JSON可序列化格式
    # 解决field_validator抛出ValueError时ctx包含不可序列化对象的问题
    from fastapi.encoders import jsonable_encoder
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": 422,
            "message": "请求参数验证失败",
            "details": jsonable_encoder(exc.errors()),
        },
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """业务逻辑异常处理"""
    logger.warning(f"业务异常：{str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "code": 400,
            "message": str(exc),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """全局未捕获异常处理"""
    logger.error(f"未捕获异常：{str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": 500,
            "message": "服务器内部错误，请稍后重试",
            "detail": str(exc) if settings.DEBUG else None,
        },
    )


# ==================== 注册路由 ====================

from app.api import auth, qa, contract, knowledge, analysis, dashboard, notification, user

# 认证路由
app.include_router(auth.router, prefix=settings.API_PREFIX)

# 法律问答路由
app.include_router(qa.router, prefix=settings.API_PREFIX)

# 合同审查路由
app.include_router(contract.router, prefix=settings.API_PREFIX)

# 知识库路由
app.include_router(knowledge.router, prefix=settings.API_PREFIX)

# 数据分析路由
app.include_router(analysis.router, prefix=settings.API_PREFIX)

# 仪表盘路由
app.include_router(dashboard.router, prefix=settings.API_PREFIX)

# 通知路由
app.include_router(notification.router, prefix=settings.API_PREFIX)

# 用户管理路由（管理员专用，RBAC：仅is_superuser=True可访问）
app.include_router(user.router, prefix=settings.API_PREFIX)


# ==================== 静态文件服务（头像等上传文件） ====================

from fastapi.staticfiles import StaticFiles

# 确保上传目录存在后挂载静态文件服务
# 挂载路径包含API前缀，使Nginx(/api/)和Vite代理(/api)均可正确转发到此处
import os as _os
_os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount(f"{settings.API_PREFIX}/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


# ==================== 健康检查端点 ====================

@app.get("/health", tags=["系统"], summary="健康检查")
async def health_check():
    """系统健康检查端点

    用于监控系统和负载均衡器检测服务是否正常运行。
    """
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": "development" if settings.DEBUG else "production",
    }


@app.get("/", tags=["系统"], summary="根路径")
async def root():
    """根路径，返回API基本信息"""
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs_url": "/docs",
        "health_url": "/health",
    }
