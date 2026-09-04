# ============================================================
# 智法通 - 后端 Dockerfile
# 基础镜像: python:3.10-slim (华为云镜像)
# 说明: 构建FastAPI后端应用镜像
# ============================================================

# 指定华为云镜像地址
FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/library/python:3.10-slim

# 维护者信息
LABEL maintainer="zhifatong-team"
LABEL description="智法通 - 企业级智能法律顾问平台后端服务"
LABEL version="1.0.0"

# 设置环境变量
# 禁用Python缓冲输出，确保日志实时输出
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # 设置时区
    TZ=Asia/Shanghai \
    # pip镜像源（使用国内镜像加速）
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

# 安装系统依赖
# 使用阿里云镜像源解决网络访问问题
# curl: 健康检查使用
# default-libmysqlclient-dev: MySQL客户端库（Python mysql驱动依赖）
# build-essential: 编译C扩展所需
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null; \
    sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null; \
    apt-get update && apt-get install -y --no-install-recommends \
    curl \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 先复制依赖文件，利用Docker缓存层加速构建
# 只要requirements.txt不变，依赖安装层就会被缓存
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端应用代码
COPY . .

# 创建必要的目录
# uploads: 上传文件存储目录
# logs: 应用日志目录
RUN mkdir -p /app/uploads /app/logs

# 暴露端口
EXPOSE 8000

# 健康检查
# 每30秒检查一次应用是否正常响应
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=40s \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
# 使用uvicorn启动FastAPI应用
# --host 0.0.0.0: 监听所有网络接口
# --port 8000: 监听8000端口
# --workers 4: 启动4个工作进程（平衡CPU利用率与资源占用，TPS>2000）
# --loop uvloop: 使用uvloop提升性能
# --http httptools: 使用httptools提升HTTP解析性能
# 注意: workers数量不宜过多，避免并发建表冲突和内存压力
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--loop", "uvloop", "--http", "httptools"]
