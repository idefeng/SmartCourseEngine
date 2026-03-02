#!/bin/bash

# SmartCourseEngine 完整启动脚本
# 作者: SmartCourseEngine Team
# 日期: 2026-03-02

set -e

echo "============================================================"
echo "SmartCourseEngine 完整启动脚本"
echo "============================================================"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        log_error "命令 $1 未找到，请先安装"
        return 1
    fi
    return 0
}

# 检查端口是否被占用
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        log_warn "端口 $1 已被占用"
        return 1
    fi
    return 0
}

# 步骤1：检查依赖
log_info "步骤1：检查系统依赖"
check_command python3 || exit 1
check_command node || exit 1
check_command npm || exit 1

# 步骤2：检查Python虚拟环境
log_info "步骤2：检查Python虚拟环境"
if [ ! -d "venv" ]; then
    log_warn "Python虚拟环境不存在，正在创建..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    log_info "安装Python依赖..."
    pip install fastapi uvicorn sqlite3 pydantic python-jose[cryptography] bcrypt python-multipart pydantic[email]
else
    log_info "Python虚拟环境已存在"
fi

# 步骤3：检查数据库
log_info "步骤3：检查数据库"
if [ ! -f "data/smartcourse.db" ]; then
    log_warn "数据库文件不存在，正在初始化..."
    source venv/bin/activate
    python init_simple.py
else
    log_info "数据库文件已存在"
fi

# 步骤4：检查前端依赖
log_info "步骤4：检查前端依赖"
cd admin-frontend
if [ ! -d "node_modules" ]; then
    log_warn "前端依赖未安装，正在安装..."
    echo "这可能需要几分钟时间，请耐心等待..."
    npm install
else
    log_info "前端依赖已安装"
fi
cd ..

# 步骤5：检查端口
log_info "步骤5：检查端口"
check_port 8001 || {
    log_warn "后端端口8001被占用，尝试使用8002"
    BACKEND_PORT=8002
}
check_port 3000 || {
    log_warn "前端端口3000被占用，尝试使用3001"
    FRONTEND_PORT=3001
}

BACKEND_PORT=${BACKEND_PORT:-8001}
FRONTEND_PORT=${FRONTEND_PORT:-3000}

# 步骤6：启动后端服务
log_info "步骤6：启动后端服务 (端口: $BACKEND_PORT)"
cd api-gateway

# 创建启动脚本
cat > start_backend_temp.py << EOF
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))

from main_unified import app
import uvicorn

if __name__ == "__main__":
    print("=" * 60)
    print(f"启动 SmartCourseEngine 统一API网关 (端口: {BACKEND_PORT})")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=${BACKEND_PORT})
EOF

# 在后端目录中启动服务
(source ../venv/bin/activate && python start_backend_temp.py) &
BACKEND_PID=$!
cd ..

sleep 3  # 等待后端启动

# 步骤7：启动前端服务
log_info "步骤7：启动前端服务 (端口: $FRONTEND_PORT)"
cd admin-frontend

# 修改环境变量（如果需要）
if [ "$BACKEND_PORT" != "8001" ] || [ "$FRONTEND_PORT" != "3000" ]; then
    log_info "更新环境配置..."
    cat > .env.local << EOF
NEXT_PUBLIC_API_BASE_URL=http://localhost:${BACKEND_PORT}
NEXT_PUBLIC_WS_URL=ws://localhost:${BACKEND_PORT}/ws
PORT=${FRONTEND_PORT}
EOF
fi

npm run dev &
FRONTEND_PID=$!
cd ..

# 步骤8：显示启动信息
log_info "步骤8：显示启动信息"
echo ""
echo "============================================================"
echo "🎉 SmartCourseEngine 启动成功！"
echo "============================================================"
echo ""
echo "🔗 访问地址："
echo "   前端管理后台: http://localhost:${FRONTEND_PORT}"
echo "   后端API文档: http://localhost:${BACKEND_PORT}/docs"
echo "   健康检查: http://localhost:${BACKEND_PORT}/health"
echo ""
echo "👤 演示账户："
echo "   邮箱: admin@smartcourse.com"
echo "   密码: Admin@123"
echo ""
echo "📋 快速测试："
echo "   curl http://localhost:${BACKEND_PORT}/health"
echo "   curl \"http://localhost:${BACKEND_PORT}/api/v1/courses?page=1&page_size=10\""
echo ""
echo "🛑 停止服务："
echo "   按 Ctrl+C 停止所有服务"
echo "   或运行: kill $BACKEND_PID $FRONTEND_PID"
echo "============================================================"

# 等待用户中断
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
wait