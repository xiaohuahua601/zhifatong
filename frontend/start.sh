#!/bin/sh
# ============================================================
# 智法通 - 前端Nginx容器启动脚本
#
# 功能：
#   1. 等待后端 backend:8000 可达，避免Nginx启动时DNS解析失败
#   2. 超时后使用 resolver 动态解析兜底启动Nginx
#   3. 启动Nginx前台运行
#
# 设计原因：
#   Nginx upstream 块在配置加载时会立即解析主机名，
#   若 backend 尚未启动或DNS未就绪，Nginx会启动失败。
#   本脚本通过循环检测 backend 可达性，
#   确保Nginx启动时 upstream 中的 server 主机名可解析。
#   若超时仍不可达，则强制启动（依赖Docker DNS自动恢复）。
# ============================================================

set -e

# 后端主机名（与 docker-compose.yml 中 service 名一致）
BACKEND_HOST="${BACKEND_HOST:-backend}"
BACKEND_PORT="${BACKEND_PORT:-8000}"

echo "[start.sh] 智法通前端启动脚本开始..."
echo "[start.sh] 等待后端 ${BACKEND_HOST}:${BACKEND_PORT} 可达..."

# 最大等待次数（每次3秒，最多等60次=180秒=3分钟）
MAX_RETRIES=60
RETRY_COUNT=0
BACKEND_READY=0

# 循环检测后端主机名是否可解析且端口可达
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    RETRY_COUNT=$((RETRY_COUNT + 1))

    # 方式1: 使用 getent 检测主机名解析（alpine glibc自带）
    if getent hosts "${BACKEND_HOST}" >/dev/null 2>&1; then
        # 方式2: 使用 nc 检测端口可达性
        if nc -z -w 3 "${BACKEND_HOST}" "${BACKEND_PORT}" 2>/dev/null; then
            echo "[start.sh] ✅ 后端 ${BACKEND_HOST}:${BACKEND_PORT} 已可达（第 ${RETRY_COUNT} 次尝试）"
            BACKEND_READY=1
            break
        else
            echo "[start.sh] ⏳ DNS已解析，但端口未就绪...（第 ${RETRY_COUNT}/${MAX_RETRIES} 次）"
        fi
    else
        echo "[start.sh] ⏳ 等待DNS解析...（第 ${RETRY_COUNT}/${MAX_RETRIES} 次）"
    fi

    sleep 3
done

# 检查是否超时
if [ $BACKEND_READY -eq 0 ]; then
    echo "[start.sh] ⚠️ 等待后端超时（${MAX_RETRIES} 次），强制启动Nginx（依赖Docker DNS自动恢复）"
else
    echo "[start.sh] 🚀 后端已就绪，启动Nginx..."
fi

# 执行Dockerfile CMD（即 nginx -g "daemon off;"）
exec "$@"
