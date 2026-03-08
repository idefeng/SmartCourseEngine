#!/bin/bash

# SmartCourseEngine 完整系统启动脚本
# 启动所有7个微服务和基础设施

set -e

echo "🚀 启动 SmartCourseEngine 完整系统..."
echo "=========================================="

# 检查Docker和Docker Compose
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose 未安装"
    exit 1
fi

# 进入部署目录
cd "$(dirname "$0")/deploy"

echo "📦 启动基础设施服务..."
echo "------------------------------------------"

# 启动数据库和消息队列
docker-compose up -d \
    postgres \
    neo4j \
    redis \
    minio \
    rabbitmq \
    prometheus \
    grafana

echo "⏳ 等待基础设施服务启动..."
sleep 10

echo "🔧 启动微服务..."
echo "------------------------------------------"

# 启动所有微服务
docker-compose up -d \
    api-gateway \
    course-generator \
    video-analyzer \
    knowledge-extractor \
    search-engine \
    recommendation \
    notification \
    nginx

echo "⏳ 等待微服务启动..."
sleep 15

echo "📊 检查服务状态..."
echo "------------------------------------------"

# 检查服务健康状态
echo "🔍 检查API网关..."
curl -f http://localhost:80/health || echo "⚠️  API网关未就绪"

echo "🔍 检查课件生成服务..."
curl -f http://localhost:80/course-generator/health || echo "⚠️  课件生成服务未就绪"

echo "🔍 检查视频分析服务..."
curl -f http://localhost:80/video-analyzer/health || echo "⚠️  视频分析服务未就绪"

echo "🔍 检查知识提取服务..."
curl -f http://localhost:80/knowledge-extractor/health || echo "⚠️  知识提取服务未就绪"

echo "🔍 检查搜索服务..."
curl -f http://localhost:80/search-engine/health || echo "⚠️  搜索服务未就绪"

echo "🔍 检查推荐服务..."
curl -f http://localhost:80/recommendation/health || echo "⚠️  推荐服务未就绪"

echo "🔍 检查通知服务..."
curl -f http://localhost:80/notification/health || echo "⚠️  通知服务未就绪"

echo ""
echo "✅ SmartCourseEngine 系统启动完成！"
echo "=========================================="
echo ""
echo "🌐 访问地址:"
echo "  API网关:      http://localhost:80"
echo "  API文档:      http://localhost:80/docs"
echo "  MinIO控制台:  http://localhost:9001 (admin/admin123)"
echo "  Grafana监控:  http://localhost:3000 (admin/admin123)"
echo "  RabbitMQ管理: http://localhost:15672 (admin/admin123)"
echo "  Neo4j浏览器:  http://localhost:7474 (neo4j/admin123)"
echo ""
echo "🔧 微服务直接访问:"
echo "  课件生成:     http://localhost:8001"
echo "  视频分析:     http://localhost:8002"
echo "  知识提取:     http://localhost:8003"
echo "  搜索服务:     http://localhost:8004"
echo "  推荐服务:     http://localhost:8005"
echo "  通知服务:     http://localhost:8006"
echo ""
echo "📋 查看服务日志:"
echo "  docker-compose logs -f [服务名]"
echo ""
echo "🛑 停止所有服务:"
echo "  docker-compose down"
echo ""