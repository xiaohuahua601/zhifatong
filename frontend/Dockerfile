# ============================================================
# 智法通 - 前端 Dockerfile
# 多阶段构建
# 阶段1: 使用node:20-alpine构建Vue3项目
# 阶段2: 使用nginx:alpine提供静态文件服务
# ============================================================

# ----------------------------------------------------------
# 阶段1: 构建阶段
# 使用Node.js编译Vue3前端项目
# ----------------------------------------------------------
FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/node:20-alpine AS builder

# 维护者信息
LABEL maintainer="zhifatong-team"
LABEL stage="builder"

# 设置环境变量
# npm镜像源（使用国内镜像加速）
# 注意: 构建阶段需要devDependencies(vue-tsc等)，不能设置NODE_ENV=production
ENV NPM_CONFIG_REGISTRY=https://registry.npmmirror.com

# 设置工作目录
WORKDIR /app

# 先复制依赖文件，利用Docker缓存层
# 只要package.json和lock文件不变，依赖安装层就会被缓存
COPY package.json package-lock.json* ./

# 安装依赖
# 使用--legacy-peer-deps避免依赖冲突
RUN npm install --legacy-peer-deps

# 复制前端源代码
COPY . .

# 构建参数：API基础地址
# 在构建时注入，用于前端API请求配置
ARG VITE_API_BASE_URL=/api

# 设置构建时环境变量
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

# 执行构建（跳过vue-tsc类型检查，直接使用Vite构建，提升构建速度和可靠性）
# 输出目录默认为dist/
RUN npx vite build

# ----------------------------------------------------------
# 阶段2: 运行阶段
# 将构建产物复制到Nginx中提供静态文件服务
# ----------------------------------------------------------
FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/nginx:alpine AS production

# 维护者信息
LABEL maintainer="zhifatong-team"
LABEL description="智法通 - 企业级智能法律顾问平台前端服务"
LABEL version="1.0.0"

# 设置时区
ENV TZ=Asia/Shanghai

# 安装tzdata设置时区，并安装netcat-openbsd用于启动脚本检测后端可达性
RUN apk add --no-cache tzdata netcat-openbsd && \
    cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo "Asia/Shanghai" > /etc/timezone && \
    apk del tzdata

# 从构建阶段复制构建产物到Nginx默认静态文件目录
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制自定义Nginx配置（前端SPA路由支持 + 反向代理 + 负载均衡）
COPY nginx/default.conf /etc/nginx/conf.d/default.conf

# 复制启动脚本（等待backend可达后启动Nginx，避免upstream DNS解析失败）
COPY start.sh /start.sh
RUN chmod +x /start.sh

# 暴露端口
EXPOSE 80

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s \
    CMD wget --quiet --tries=1 --spider http://127.0.0.1/ || exit 1

# 启动Nginx（通过start.sh脚本启动，前台运行模式）
# start.sh 会先等待 backend:8000 可达，再执行 exec nginx -g "daemon off;"
ENTRYPOINT ["/start.sh"]
CMD ["nginx", "-g", "daemon off;"]
