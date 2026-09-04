#!/bin/bash
# ============================================================
# 智法通 - Linux/Mac 启动脚本
# 说明: 检查环境、启动Docker Compose、等待服务就绪、初始化数据库
# 使用: chmod +x scripts/start.sh && ./scripts/start.sh
# ============================================================

set -e

# 颜色定义（用于终端输出美化）
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # 无颜色

# 项目根目录（脚本所在目录的上级目录）
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# ============================================================
# 辅助函数
# ============================================================

# 打印信息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 打印分隔线
print_separator() {
    echo "============================================================"
}

# ============================================================
# 步骤1: 环境检查
# ============================================================
check_environment() {
    print_separator
    print_info "正在检查运行环境..."

    # 检查Docker是否安装
    if ! command -v docker &> /dev/null; then
        print_error "Docker未安装，请先安装Docker"
        print_info "安装指南: https://docs.docker.com/get-docker/"
        exit 1
    fi
    print_success "Docker已安装: $(docker --version)"

    # 检查Docker Compose是否安装
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
        print_success "Docker Compose已安装: $(docker compose version)"
    elif command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
        print_success "Docker Compose已安装: $(docker-compose --version)"
    else
        print_error "Docker Compose未安装，请先安装Docker Compose"
        print_info "安装指南: https://docs.docker.com/compose/install/"
        exit 1
    fi

    # 检查Docker守护进程是否运行
    if ! docker info &> /dev/null; then
        print_error "Docker守护进程未运行，请启动Docker"
        exit 1
    fi
    print_success "Docker守护进程正在运行"

    # 检查.env文件是否存在
    if [ ! -f "$PROJECT_DIR/.env" ]; then
        print_warning ".env文件不存在，正在从.env.example创建..."
        cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
        print_success ".env文件已创建，请根据实际情况修改配置"
    else
        print_success ".env配置文件已存在"
    fi

    # 检查Python是否安装（用于数据库初始化）
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        print_warning "Python未安装，数据库初始化脚本将无法在本地运行"
        print_info "数据库初始化将通过Docker容器内的MySQL自动执行"
        PYTHON_CMD=""
    fi

    print_success "环境检查完成"
}

# ============================================================
# 步骤2: 启动Docker Compose服务
# ============================================================
start_services() {
    print_separator
    print_info "正在启动Docker Compose服务..."

    cd "$PROJECT_DIR"

    # 停止已有的服务（如果存在）
    $COMPOSE_CMD down --remove-orphans 2>/dev/null || true

    # 构建并启动所有服务（后台运行）
    $COMPOSE_CMD up -d --build

    print_success "Docker Compose服务已启动"
}

# ============================================================
# 步骤3: 等待服务就绪
# ============================================================
wait_for_services() {
    print_separator
    print_info "正在等待服务就绪..."

    # 等待MySQL就绪（最多等待120秒）
    print_info "等待MySQL服务..."
    MAX_WAIT=120
    WAITED=0
    while [ $WAITED -lt $MAX_WAIT ]; do
        if docker exec zhifatong-mysql mysqladmin ping -h localhost -u root -p"${MYSQL_ROOT_PASSWORD:-zhifatong_root_2026}" &> /dev/null; then
            print_success "MySQL服务已就绪（等待了${WAITED}秒）"
            break
        fi
        sleep 3
        WAITED=$((WAITED + 3))
        echo -n "."
    done

    if [ $WAITED -ge $MAX_WAIT ]; then
        print_error "MySQL服务启动超时（${MAX_WAIT}秒）"
        print_info "请检查日志: docker logs zhifatong-mysql"
        exit 1
    fi

    # 等待后端服务就绪（最多等待60秒）
    print_info "等待后端服务..."
    WAITED=0
    MAX_WAIT=60
    while [ $WAITED -lt $MAX_WAIT ]; do
        if curl -s http://localhost:8000/health &> /dev/null; then
            print_success "后端服务已就绪（等待了${WAITED}秒）"
            break
        fi
        sleep 3
        WAITED=$((WAITED + 3))
        echo -n "."
    done

    if [ $WAITED -ge $MAX_WAIT ]; then
        print_warning "后端服务未在预期时间内就绪，但可能仍在启动中"
        print_info "请检查日志: docker logs zhifatong-backend"
    fi

    # 等待Nginx就绪
    print_info "等待Nginx服务..."
    WAITED=0
    MAX_WAIT=30
    while [ $WAITED -lt $MAX_WAIT ]; do
        if curl -s http://localhost/health &> /dev/null; then
            print_success "Nginx服务已就绪（等待了${WAITED}秒）"
            break
        fi
        sleep 2
        WAITED=$((WAITED + 2))
    done

    print_success "所有服务已就绪"
}

# ============================================================
# 步骤4: 初始化数据库
# ============================================================
initialize_database() {
    print_separator
    print_info "正在初始化数据库..."

    # MySQL容器启动时会自动执行 /docker-entrypoint-initdb.d/ 下的SQL文件
    # 此处检查数据库是否已成功初始化
    if docker exec zhifatong-mysql mysql -u root -p"${MYSQL_ROOT_PASSWORD:-zhifatong_root_2026}" -e "USE zhifatong; SELECT COUNT(*) FROM users;" &> /dev/null; then
        print_success "数据库已通过Docker自动初始化"
    else
        print_warning "Docker自动初始化可能未完成，尝试手动初始化..."

        # 如果本地有Python，运行初始化脚本
        if [ -n "$PYTHON_CMD" ]; then
            print_info "使用Python脚本初始化数据库..."
            pip install pymysql -q 2>/dev/null || true
            $PYTHON_CMD "$PROJECT_DIR/scripts/init_db.py"
        else
            # 通过Docker执行SQL
            print_info "通过Docker执行SQL初始化..."
            docker exec -i zhifatong-mysql mysql -u root -p"${MYSQL_ROOT_PASSWORD:-zhifatong_root_2026}" < "$PROJECT_DIR/sql/init.sql"
        fi
    fi

    print_success "数据库初始化完成"
}

# ============================================================
# 步骤5: 显示服务信息
# ============================================================
show_service_info() {
    print_separator
    echo ""
    print_success "🎉 智法通平台已成功启动！"
    echo ""
    print_info "服务访问地址:"
    echo "  前端界面:  http://localhost"
    echo "  后端API:   http://localhost/api"
    echo "  API文档:   http://localhost/api/docs"
    echo "  MySQL:     localhost:3306"
    echo ""
    print_info "默认管理员账号:"
    echo "  用户名: admin"
    echo "  密码:   admin123"
    echo ""
    print_warning "⚠ 请在生产环境中修改默认密码和密钥！"
    echo ""
    print_info "常用命令:"
    echo "  查看服务状态:  $COMPOSE_CMD ps"
    echo "  查看服务日志:  $COMPOSE_CMD logs -f [服务名]"
    echo "  停止所有服务:  $COMPOSE_CMD down"
    echo "  重启某个服务:  $COMPOSE_CMD restart [服务名]"
    echo ""
    print_separator
}

# ============================================================
# 主流程
# ============================================================
main() {
    echo ""
    print_separator
    echo -e "${BLUE}  智法通 - 企业级智能法律顾问平台${NC}"
    echo -e "${BLUE}  启动脚本 v1.0${NC}"
    print_separator
    echo ""

    check_environment
    start_services
    wait_for_services
    initialize_database
    show_service_info
}

# 执行主函数
main
