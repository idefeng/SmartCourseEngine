# SmartCourseEngine 重构项目

基于AI课程知识库技术方案的重构版本，从智能课件生成引擎升级为AI驱动的智能课程知识库与生成平台。

## 🎯 新架构目标

### 核心能力扩展
1. **视频智能分析**: 支持现有课程视频的知识点提取和标签分类
2. **多模态知识库**: 构建包含文本、语音、视觉的多模态知识库
3. **智能检索系统**: 支持知识点级别的视频检索和时间戳定位
4. **动态知识更新**: 支持新内容（如法律法规）的录入和已有课程更新
5. **个性化学习**: 基于知识图谱的个性化学习路径推荐

## 🏗️ 架构设计

### 五层微服务架构
```
用户界面层 (Streamlit/REST API/Telegram Bot)
        ↓
    API网关层 (FastAPI + GraphQL)
        ↓
   业务逻辑层 (7个微服务)
        ↓
   数据处理层 (PostgreSQL + Neo4j + Pinecone)
        ↓
   AI模型服务层 (Whisper + CLIP + LLM)
```

### 微服务划分
1. **api-gateway**: API网关服务（端口: 8000）
2. **course-generator**: 课件生成服务（端口: 8001）
3. **video-analyzer**: 视频分析服务（端口: 8002）
4. **knowledge-base**: 知识库管理服务（端口: 8003）
5. **search-engine**: 智能检索服务（端口: 8004）
6. **recommendation**: 推荐服务（端口: 8005）
7. **notification**: 通知服务（端口: 8006）

## 🚀 快速开始

### 环境要求
- Docker 20.10+
- Docker Compose 2.20+
- Python 3.10+（开发环境）

### 启动所有服务
```bash
cd deploy
docker-compose up -d
```

### 访问服务
- **API网关**: http://localhost:80
- **API文档**: http://localhost:80/docs
- **MinIO控制台**: http://localhost:9001 (admin/admin123)
- **Grafana监控**: http://localhost:3000 (admin/admin123)
- **RabbitMQ管理**: http://localhost:15672 (admin/admin123)
- **Neo4j浏览器**: http://localhost:7474 (neo4j/admin123)

### 停止服务
```bash
cd deploy
docker-compose down
```

## 📁 项目结构

```
new_architecture/
├── api-gateway/          # API网关服务
│   ├── main.py          # 主应用
│   ├── Dockerfile       # 容器配置
│   └── requirements.txt # Python依赖
├── course-generator/    # 课件生成服务（待开发）
├── video-analyzer/      # 视频分析服务（待开发）
├── knowledge-base/      # 知识库服务（待开发）
├── search-engine/       # 检索服务（待开发）
├── recommendation/      # 推荐服务（待开发）
├── notification/        # 通知服务（待开发）
├── shared/              # 共享模块
│   ├── config.py       # 配置管理
│   ├── models.py       # 数据模型
│   └── utils.py        # 工具函数
└── deploy/              # 部署配置
    ├── docker-compose.yml  # 服务编排
    ├── nginx.conf      # 反向代理
    ├── prometheus.yml  # 监控配置
    └── grafana/        # 仪表板配置
```

## 🔧 开发指南

### 1. 设置开发环境
```bash
# 克隆项目
git clone https://github.com/idefeng/SmartCourseEngine.git
cd SmartCourseEngine/new_architecture

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装共享模块依赖
pip install -r shared/requirements.txt
```

### 2. 启动基础设施
```bash
cd deploy
docker-compose up -d postgres neo4j redis minio rabbitmq
```

### 3. 开发API网关
```bash
cd api-gateway
pip install -r requirements.txt
python main.py
```

### 4. 运行测试
```bash
# 运行单元测试
pytest tests/

# 运行集成测试
pytest tests/integration/

# 运行性能测试
python tests/performance.py
```

## 📊 数据库设计

### PostgreSQL（主数据存储）
- `courses`: 课程信息
- `knowledge_points`: 知识点
- `tags`: 标签
- `users`: 用户信息
- `analyses`: 分析记录

### Neo4j（知识图谱）
- 课程-知识点关系
- 知识点-知识点关系
- 用户-知识点关系
- 标签-知识点关系

### Pinecone（向量搜索）
- 知识点向量嵌入
- 课程向量嵌入
- 用户偏好向量

### Redis（缓存）
- 会话缓存
- 查询结果缓存
- 实时数据缓存

## 🔌 API接口

### 核心API端点
```
GET    /api/v1/courses           # 列出课程
POST   /api/v1/courses           # 创建课程
GET    /api/v1/courses/{id}      # 获取课程详情
PUT    /api/v1/courses/{id}      # 更新课程
DELETE /api/v1/courses/{id}      # 删除课程

POST   /api/v1/videos/analyze    # 分析视频
GET    /api/v1/analyses/{id}     # 获取分析结果

GET    /api/v1/knowledge/search  # 搜索知识点
POST   /api/v1/knowledge/update  # 更新知识库

GET    /api/v1/recommendations   # 获取推荐
POST   /api/v1/notifications     # 发送通知
```

### GraphQL端点
```
POST   /graphql                  # GraphQL查询
```

## 📈 监控和日志

### 监控指标
- **系统指标**: CPU、内存、磁盘、网络
- **应用指标**: 请求延迟、错误率、吞吐量
- **业务指标**: 视频分析成功率、检索准确率
- **AI模型指标**: 推理延迟、模型准确率

### 日志级别
- DEBUG: 开发调试信息
- INFO: 常规操作信息
- WARNING: 警告信息
- ERROR: 错误信息
- CRITICAL: 严重错误

## 🔒 安全配置

### 认证和授权
- JWT令牌认证
- API密钥验证
- 基于角色的访问控制（RBAC）
- CORS配置

### 数据安全
- 数据库连接加密
- 敏感数据加密存储
- 输入验证和清理
- SQL注入防护

## 🐳 容器化部署

### 生产环境配置
```bash
# 构建所有服务
docker-compose -f docker-compose.prod.yml build

# 启动生产环境
docker-compose -f docker-compose.prod.yml up -d

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

### Kubernetes部署
```bash
# 应用Kubernetes配置
kubectl apply -f k8s/

# 查看部署状态
kubectl get all -n smartcourse

# 查看日志
kubectl logs -f deployment/api-gateway -n smartcourse
```

## 📋 迁移计划

### 阶段一：基础架构升级（2-3周）
1. 数据库迁移（ChromaDB → PostgreSQL + Pinecone + Neo4j）
2. API架构重构（单体 → 微服务）
3. 容器化升级

### 阶段二：核心功能增强（3-4周）
1. 视频分析服务开发
2. 知识库服务升级
3. 检索服务开发

### 阶段三：功能集成与优化（2-3周）
1. 原有功能迁移
2. 系统集成
3. 测试和部署

## 🤝 贡献指南

### 开发流程
1. Fork项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

### 代码规范
- 使用Black进行代码格式化
- 使用isort进行导入排序
- 使用mypy进行类型检查
- 遵循PEP 8规范

### 测试要求
- 新功能必须包含单元测试
- 关键功能必须包含集成测试
- 保持测试覆盖率在80%以上

## 📄 许可证

MIT License

## 📞 支持

- 问题反馈: GitHub Issues
- 文档: [项目Wiki](https://github.com/idefeng/SmartCourseEngine/wiki)
- 讨论: GitHub Discussions

---
**版本**: 1.0.0  
**最后更新**: 2026-03-01  
**状态**: 开发中