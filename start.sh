#!/usr/bin/env bash
#
# start.sh — 一键启动前后端开发服务器
# 动态图谱洞察沙盘 POC (Palantir Ontology Simulator)
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================"
echo "  动态图谱洞察沙盘 POC - 启动脚本"
echo "  Palantir Ontology Simulator"
echo "============================================"
echo ""

# --- Environment checks ---

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}[ERROR] Python 未安装。请安装 Python 3.11+ 后重试。${NC}"
    echo "  推荐: brew install python3 (macOS) 或 apt install python3 (Linux)"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
echo -e "${GREEN}[OK]${NC} $PYTHON_VERSION"

# Check pip
if ! $PYTHON_CMD -m pip --version &> /dev/null; then
    echo -e "${RED}[ERROR] pip 未安装。请安装 pip 后重试。${NC}"
    exit 1
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}[ERROR] Node.js 未安装。请安装 Node.js 20+ 后重试。${NC}"
    echo "  推荐: brew install node (macOS) 或 https://nodejs.org/"
    exit 1
fi

NODE_VERSION=$(node --version)
echo -e "${GREEN}[OK]${NC} Node.js $NODE_VERSION"

# Check npm
if ! command -v npm &> /dev/null; then
    echo -e "${RED}[ERROR] npm 未安装。请安装 npm 后重试。${NC}"
    exit 1
fi

NPM_VERSION=$(npm --version)
echo -e "${GREEN}[OK]${NC} npm $NPM_VERSION"

echo ""

# --- Install dependencies ---

echo -e "${YELLOW}[1/4]${NC} 安装后端 Python 依赖..."
$PYTHON_CMD -m pip install -r "$BACKEND_DIR/requirements.txt" --quiet
echo -e "${GREEN}[OK]${NC} 后端依赖安装完成"

echo -e "${YELLOW}[2/4]${NC} 安装前端 Node.js 依赖..."
(cd "$FRONTEND_DIR" && npm install --silent)
echo -e "${GREEN}[OK]${NC} 前端依赖安装完成"

echo ""

# --- Start services ---

# Trap to clean up background processes on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}正在停止服务...${NC}"
    if [ -n "$BACKEND_PID" ]; then
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
    echo -e "${GREEN}服务已停止。${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

echo -e "${YELLOW}[3/4]${NC} 启动后端服务 (FastAPI on :8000)..."
(cd "$BACKEND_DIR" && $PYTHON_CMD -m uvicorn app.main:app --reload --port 8000) &
BACKEND_PID=$!
echo -e "${GREEN}[OK]${NC} 后端 PID: $BACKEND_PID"

# Wait a moment for backend to initialize
sleep 2

echo -e "${YELLOW}[4/4]${NC} 启动前端服务 (Vite on :5173)..."
(cd "$FRONTEND_DIR" && npm run dev) &
FRONTEND_PID=$!
echo -e "${GREEN}[OK]${NC} 前端 PID: $FRONTEND_PID"

echo ""
echo "============================================"
echo -e "  ${GREEN}服务已启动!${NC}"
echo ""
echo "  前端界面:   http://localhost:5173"
echo "  API 文档:   http://localhost:8000/docs"
echo "  健康检查:   http://localhost:8000/health"
echo ""
echo "  按 Ctrl+C 停止所有服务"
echo "============================================"

# Wait for any background process to exit
wait
