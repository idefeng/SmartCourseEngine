#!/bin/bash
# SmartCourseEngine 开发环境启动脚本

set -e  # 遇到错误退出

echo "🚀 启动 SmartCourseEngine 开发环境"
echo "======================================"

# 检查Python版本
echo "检查Python版本..."
python3 --version

# 创建虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "安装依赖..."
pip install --upgrade pip
pip install -r shared/requirements.txt
pip install -r api-gateway/requirements.txt

# 创建必要的目录
echo "创建数据目录..."
mkdir -p data logs cache

# 初始化数据库
echo "初始化数据库..."
if [ -f "init_database.py" ]; then
    python init_database.py
else
    echo "警告: init_database.py 不存在，跳过数据库初始化"
fi

# 启动API网关
echo "启动API网关服务..."
cd api-gateway
python main.py &

# 获取进程ID
API_PID=$!
echo "API网关进程ID: $API_PID"

# 等待服务启动
echo "等待服务启动..."
sleep 3

# 检查服务状态
echo "检查服务状态..."
curl -f http://localhost:8000/health || echo "服务启动失败"

echo ""
echo "✅ 开发环境启动完成!"
echo ""
echo "访问以下地址:"
echo "  API文档: http://localhost:8000/docs"
echo "  健康检查: http://localhost:8000/health"
echo ""
echo "按 Ctrl+C 停止服务"

# 等待用户中断
wait $API_PID

echo ""
echo "👋 服务已停止"