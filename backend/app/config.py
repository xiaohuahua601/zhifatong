"""
智法通 - 企业级智能法律顾问平台 配置管理模块

使用 pydantic-settings 的 BaseSettings 管理所有配置项，
支持从环境变量和 .env 文件中读取配置。
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from typing import Optional


class Settings(BaseSettings):
    """应用全局配置类

    所有配置项均可通过环境变量覆盖，环境变量前缀为 ZHIFATONG_。
    例如：ZHIFATONG_DB_HOST=127.0.0.1 可覆盖 DB_HOST 配置。
    """

    model_config = SettingsConfigDict(
        env_prefix="ZHIFATONG_",          # 环境变量前缀
        env_file=".env",                  # 从 .env 文件加载
        env_file_encoding="utf-8",
        case_sensitive=False,             # 环境变量不区分大小写
        extra="ignore",                   # 忽略多余的环境变量
    )

    # ==================== 应用基础配置 ====================
    APP_NAME: str = "智法通"                             # 应用名称
    APP_VERSION: str = "1.0.0"                           # 应用版本
    DEBUG: bool = True                                   # 调试模式
    API_PREFIX: str = "/api/v1"                          # API路由前缀

    # ==================== 数据库配置（MySQL 8.0）====================
    DB_HOST: str = "127.0.0.1"                           # 数据库主机
    DB_PORT: int = 3306                                  # 数据库端口
    DB_USER: str = "root"                                # 数据库用户名
    DB_PASSWORD: str = "root"                            # 数据库密码
    DB_NAME: str = "zhifatong"                           # 数据库名称
    DB_POOL_SIZE: int = 10                               # 连接池大小
    DB_MAX_OVERFLOW: int = 20                            # 连接池最大溢出
    DB_POOL_RECYCLE: int = 3600                          # 连接回收时间（秒）
    DB_ECHO: bool = False                                # 是否打印SQL语句

    @property
    def DATABASE_URL(self) -> str:
        """异步MySQL连接URL（使用aiomysql驱动）"""
        return (
            f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset=utf8mb4"
        )

    @property
    def DATABASE_URL_SYNC(self) -> str:
        """同步MySQL连接URL（用于数据库迁移等场景）"""
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?charset=utf8mb4"
        )

    # ==================== Redis配置 ====================
    REDIS_HOST: str = "127.0.0.1"                        # Redis主机
    REDIS_PORT: int = 6379                               # Redis端口
    REDIS_PASSWORD: str = ""                             # Redis密码
    REDIS_DB: int = 0                                    # Redis数据库编号
    REDIS_POOL_SIZE: int = 10                            # 连接池大小
    REDIS_URL: str = ""                                  # 完整URL，优先使用（为空时自动拼接）

    @model_validator(mode='after')
    def _build_redis_url(self) -> 'Settings':
        """若未显式提供 REDIS_URL，则根据各组件自动拼接"""
        if not self.REDIS_URL:
            if self.REDIS_PASSWORD:
                self.REDIS_URL = (
                    f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}"
                    f":{self.REDIS_PORT}/{self.REDIS_DB}"
                )
            else:
                self.REDIS_URL = (
                    f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
                )
        return self

    # ==================== JWT认证配置 ====================
    JWT_SECRET_KEY: str = "zhifatong-secret-key-change-in-production"  # JWT密钥（生产环境务必更换）
    JWT_ALGORITHM: str = "HS256"                        # JWT算法
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60           # 访问令牌过期时间（分钟）
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7              # 刷新令牌过期时间（天）

    # ==================== Ollama配置 ====================
    OLLAMA_BASE_URL: str = "http://localhost:11434"     # Ollama服务地址
    OLLAMA_MODEL: str = "qwen2.5:7b-instruct-q4_K_M"                 # 主对话模型
    # Embedding嵌入模型：bge-large-zh-v1.5，1024维中文语义嵌入模型
    # 替代原nomic-embed-text（英文通用），提升中文法律场景检索质量
    OLLAMA_EMBEDDING_MODEL: str = "quentinz/bge-large-zh-v1.5:latest"
    OLLAMA_TIMEOUT: int = 120                           # 请求超时时间（秒）
    OLLAMA_MAX_TOKENS: int = 4096                       # 最大生成token数
    OLLAMA_TEMPERATURE: float = 0.7                     # 生成温度

    # ==================== Rerank精排服务配置（两阶段检索架构）====================
    # Rerank服务地址：本地Docker容器 my-rerank 提供 Cross-Encoder 精排服务
    # 模型：BAAI/bge-reranker-v2-m3，支持中英文，精度优于LLM打分
    # Docker部署时使用 host.docker.internal 连接宿主机服务
    RERANK_SERVICE_URL: str = "http://host.docker.internal:9999"
    RERANK_TIMEOUT: int = 30                            # Rerank请求超时（秒）

    # ==================== LangSmith 追踪配置 ====================
    LANGSMITH_API_KEY: str = ""                         # LangSmith API密钥
    LANGSMITH_PROJECT_NAME: str = "zhifatong-production"  # LangSmith项目名称
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"  # LangSmith端点
    LANGSMITH_TRACING_ENABLED: bool = False             # 是否启用LangSmith追踪

    # ==================== Neo4j 知识图谱配置 =====================
    NEO4J_URI: str = "bolt://localhost:7687"           # Neo4j Bolt连接地址
    NEO4J_USER: str = "neo4j"                           # Neo4j用户名
    NEO4J_PASSWORD: str = "zhifatong_graph_2026"        # Neo4j密码
    NEO4J_DATABASE: str = "neo4j"                       # 数据库名称
    NEO4J_ENABLED: bool = True                          # 是否启用Neo4j图谱（不可用时自动降级）

    # ==================== 向量数据库配置（ChromaDB）====================
    CHROMA_PERSIST_DIR: str = "./data/chroma"           # Chroma持久化目录
    CHROMA_COLLECTION_NAME: str = "zhifatong_legal"     # 默认集合名称
    # bge-large-zh-v1.5 输出1024维向量（替代原768维nomic-embed-text）
    CHROMA_EMBEDDING_DIM: int = 1024

    # ==================== 文件上传配置 ====================
    UPLOAD_DIR: str = "./data/uploads"                  # 上传文件存储目录
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024             # 最大上传大小（50MB）
    ALLOWED_EXTENSIONS: list[str] = [                   # 允许的文件扩展名
        ".pdf", ".doc", ".docx", ".txt",
        ".png", ".jpg", ".jpeg",
    ]

    # ==================== RAG配置（两阶段检索架构）====================
    # 第一阶段：粗排（ANN召回）— ChromaDB HNSW 近邻检索 + BM25 稀疏检索，RRF融合
    # 第二阶段：精排（Cross-Encoder）— 调用Rerank服务对候选进行精排
    RAG_RECALL_TOP_K: int = 20                          # 粗排召回候选数量（作为精排输入）
    RAG_TOP_K: int = 5                                  # 最终返回的文档数量
    RAG_CHUNK_SIZE: int = 500                           # 文档分块大小（字符）
    RAG_CHUNK_OVERLAP: int = 50                         # 分块重叠大小（字符）
    RAG_RRF_K: int = 60                                 # RRF融合参数K
    RAG_RERANK_TOP_N: int = 5                           # 精排后保留的数量

    # ==================== RAG高级配置 ====================
    RAG_SIMILARITY_THRESHOLD: float = 0.7               # 相似度阈值
    RAG_RERETRIVAL_MAX_RETRIES: int = 2                 # 重检索最大次数
    RAG_RERETRIVAL_CONFIDENCE_THRESHOLD: float = 0.6    # 重检索置信度阈值

    # ==================== 合同审查配置 ====================
    CONTRACT_REVIEW_HIGH_RISK_THRESHOLD: int = 80       # 高风险阈值
    CONTRACT_REVIEW_INTERRUPT_ENABLED: bool = True      # 是否启用中断恢复

    # ==================== CORS配置 ====================
    CORS_ORIGINS: list[str] = [                         # 允许的跨域来源
        "http://localhost",
        "http://localhost:80",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1",
        "http://127.0.0.1:80",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
    ]


# 创建全局配置实例
settings = Settings()
