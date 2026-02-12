#!/bin/bash
set -e

# ============================================================
# 动态图谱洞察沙盘 POC - Swarm 部署脚本
# 用法: ./deploy.sh [build|deploy|update|status|logs|remove]
# ============================================================

STACK_NAME="palantir"
COMPOSE_FILE="docker-compose.swarm.yml"
BACKEND_IMAGE="palantir-poc-backend:latest"
FRONTEND_IMAGE="palantir-poc-frontend:latest"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 构建镜像
build() {
    log_info "开始构建后端镜像..."
    docker build -t "$BACKEND_IMAGE" ./backend
    log_info "后端镜像构建完成 ✓"

    log_info "开始构建前端镜像..."
    docker build -t "$FRONTEND_IMAGE" ./frontend
    log_info "前端镜像构建完成 ✓"

    log_info "所有镜像构建完成"
    docker images | grep palantir-poc
}

# 部署到 Swarm
deploy() {
    log_info "部署 Stack: $STACK_NAME ..."
    docker stack deploy -c "$COMPOSE_FILE" "$STACK_NAME"
    log_info "部署命令已发送，等待服务启动..."
    sleep 3
    status
}

# 更新（重新构建 + 部署）
update() {
    log_info "开始更新..."
    build
    deploy
    log_info "更新完成，Swarm 将自动滚动更新服务"
}

# 查看状态
status() {
    log_info "Stack 服务状态："
    docker stack services "$STACK_NAME"
    echo ""
    log_info "各任务详情："
    docker stack ps "$STACK_NAME" --no-trunc
}

# 查看日志
logs() {
    local service="${1:-frontend}"
    log_info "查看 ${STACK_NAME}_${service} 日志..."
    docker service logs "${STACK_NAME}_${service}" --follow --tail 100
}

# 移除 Stack
remove() {
    log_warn "即将移除 Stack: $STACK_NAME"
    read -p "确认移除？(y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker stack rm "$STACK_NAME"
        log_info "Stack 已移除"
    else
        log_info "取消操作"
    fi
}

# 主入口
case "${1:-help}" in
    build)
        build
        ;;
    deploy)
        deploy
        ;;
    update)
        update
        ;;
    status)
        status
        ;;
    logs)
        logs "$2"
        ;;
    remove)
        remove
        ;;
    help|*)
        echo "用法: $0 <command>"
        echo ""
        echo "命令:"
        echo "  build   - 构建前后端 Docker 镜像"
        echo "  deploy  - 部署 Stack 到 Swarm"
        echo "  update  - 重新构建并部署（滚动更新）"
        echo "  status  - 查看服务状态"
        echo "  logs    - 查看日志 (默认 frontend, 可指定: ./deploy.sh logs backend)"
        echo "  remove  - 移除 Stack"
        echo ""
        echo "首次部署: $0 build && $0 deploy"
        echo "后续更新: $0 update"
        ;;
esac
