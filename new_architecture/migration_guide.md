# SmartCourseEngine 迁移指南

从旧架构（单体应用）迁移到新架构（微服务）的详细指南。

## 📋 迁移概述

### 迁移目标
- 将现有的SmartParser单体应用迁移到新的微服务架构
- 保留所有现有功能
- 添加新的AI课程知识库功能
- 确保数据完整性和一致性

### 迁移策略
1. **并行运行**: 新旧系统并行运行一段时间
2. **逐步迁移**: 按功能模块逐步迁移
3. **数据同步**: 确保数据实时同步
4. **流量切换**: 逐步将用户流量切换到新系统

## 🔄 迁移步骤

### 阶段一：环境准备（第1周）

#### 1.1 基础设施部署
```bash
# 部署新架构的基础设施
cd new_architecture/deploy
docker-compose up -d postgres neo4j redis minio rabbitmq

# 验证服务状态
docker-compose ps

# 检查数据库连接
docker-compose exec postgres psql -U admin -d smartcourse -c "SELECT 1"
```

#### 1.2 数据备份
```bash
# 备份旧系统数据
cd ../SmartParser
python backup_data.py --output old_data_backup.json

# 备份ChromaDB向量数据
python backup_chromadb.py --output chroma_backup.json
```

#### 1.3 配置迁移
```bash
# 迁移配置文件
python migrate_config.py \
    --old-config config.json \
    --new-config new_architecture/shared/config.json
```

### 阶段二：数据迁移（第2周）

#### 2.1 数据库架构创建
```sql
-- 在新PostgreSQL中创建表结构
\i new_architecture/deploy/sql/schema.sql

-- 在Neo4j中创建图结构
:source new_architecture/deploy/cypher/schema.cypher
```

#### 2.2 数据迁移脚本
```python
# 运行数据迁移
cd new_architecture
python migrate_data.py \
    --old-data old_data_backup.json \
    --chroma-data chroma_backup.json \
    --output migrated_data.json
```

#### 2.3 数据验证
```python
# 验证数据完整性
python validate_migration.py \
    --old-data old_data_backup.json \
    --new-data migrated_data.json \
    --report migration_report.html
```

### 阶段三：服务迁移（第3-4周）

#### 3.1 API网关部署
```bash
# 构建和启动API网关
cd new_architecture/api-gateway
docker build -t smartcourse/api-gateway:1.0.0 .
docker-compose -f ../deploy/docker-compose.yml up -d api-gateway

# 测试API网关
curl http://localhost:80/health
curl http://localhost:80/docs
```

#### 3.2 课件生成服务迁移
```bash
# 迁移SmartParser的课件生成功能
cd new_architecture/course-generator

# 复制相关代码
cp -r ../../SmartParser/content_generator.py .
cp -r ../../SmartParser/main_parser.py .

# 适配新架构
python adapt_course_generator.py
```

#### 3.3 视频生成服务保留
```bash
# HeyGen视频生成功能保持不变
# 只需更新API调用方式
cp -r ../../SmartParser/video_creator.py new_architecture/course-generator/
```

### 阶段四：功能增强（第5-6周）

#### 4.1 视频分析服务开发
```bash
# 开发视频分析服务
cd new_architecture/video-analyzer

# 集成Whisper语音识别
pip install openai-whisper

# 集成CLIP视觉分析
pip install transformers clip

# 开发分析流水线
python develop_analysis_pipeline.py
```

#### 4.2 知识库服务开发
```bash
# 开发知识库服务
cd new_architecture/knowledge-base

# 集成Pinecone向量数据库
pip install pinecone-client

# 开发知识图谱构建
python develop_knowledge_graph.py
```

#### 4.3 检索服务开发
```bash
# 开发检索服务
cd new_architecture/search-engine

# 开发混合检索算法
python develop_hybrid_search.py

# 开发时间戳定位
python develop_temporal_search.py
```

### 阶段五：系统集成（第7-8周）

#### 5.1 服务间通信
```python
# 配置服务发现
# new_architecture/shared/service_discovery.py

# 配置消息队列
# new_architecture/shared/message_queue.py

# 配置事件总线
# new_architecture/shared/event_bus.py
```

#### 5.2 统一认证
```python
# 实现JWT认证
# new_architecture/shared/auth.py

# 实现API密钥管理
# new_architecture/shared/api_keys.py
```

#### 5.3 监控和日志
```bash
# 部署监控栈
cd new_architecture/deploy
docker-compose up -d prometheus grafana

# 配置应用指标
# 在每个服务中添加Prometheus指标
```

### 阶段六：测试和切换（第9-10周）

#### 6.1 功能测试
```bash
# 运行功能测试
cd new_architecture
pytest tests/functional/ --cov --cov-report=html

# 运行集成测试
pytest tests/integration/ --cov

# 运行性能测试
python tests/performance/load_test.py
```

#### 6.2 用户验收测试
```bash
# 邀请测试用户
python invite_test_users.py --count=10

# 收集用户反馈
python collect_feedback.py --output feedback_report.json
```

#### 6.3 流量切换
```bash
# 配置负载均衡器
# 逐步将流量从旧系统切换到新系统

# 第1天: 10%流量
python switch_traffic.py --percentage=10

# 第3天: 50%流量
python switch_traffic.py --percentage=50

# 第7天: 100%流量
python switch_traffic.py --percentage=100
```

#### 6.4 旧系统下线
```bash
# 停止旧系统服务
cd ../SmartParser
docker-compose down

# 归档旧系统代码
tar -czf smartparser_legacy_$(date +%Y%m%d).tar.gz .

# 更新文档
python update_documentation.py --new-arch-only
```

## 📊 数据迁移详情

### 课程数据迁移
```python
# 课程数据迁移映射
course_mapping = {
    "old_field": "new_field",
    "title": "title",
    "description": "description",
    "video_url": "video_url",
    "created_at": "created_at",
    # ... 其他字段映射
}
```

### 知识点数据迁移
```python
# 从ChromaDB迁移向量数据
def migrate_vector_data(old_chroma_db, new_pinecone_index):
    # 读取ChromaDB中的所有向量
    vectors = old_chroma_db.get_all_vectors()
    
    # 转换格式并导入Pinecone
    for vector in vectors:
        pinecone_vector = {
            "id": vector["id"],
            "values": vector["embedding"],
            "metadata": vector["metadata"]
        }
        new_pinecone_index.upsert([pinecone_vector])
```

### 用户数据迁移
```python
# 用户数据迁移（保持密码哈希）
def migrate_user_data(old_users, new_database):
    for user in old_users:
        # 保持密码哈希不变
        new_user = {
            "username": user["username"],
            "email": user["email"],
            "password_hash": user["password_hash"],  # 不重新哈希
            "created_at": user["created_at"]
        }
        new_database.insert_user(new_user)
```

## 🔧 常见问题解决

### 问题1: 数据库连接失败
```bash
# 检查数据库服务状态
docker-compose ps | grep postgres

# 检查连接字符串
echo $DATABASE_URL

# 手动测试连接
docker-compose exec postgres psql -U admin -d smartcourse
```

### 问题2: 数据迁移失败
```python
# 启用详细日志
python migrate_data.py --verbose --log-level=DEBUG

# 分步迁移
python migrate_data.py --step-by-step --checkpoint-file=checkpoint.json

# 跳过错误继续
python migrate_data.py --skip-errors --error-log=errors.log
```

### 问题3: 服务启动失败
```bash
# 查看服务日志
docker-compose logs api-gateway

# 检查端口冲突
netstat -tulpn | grep :8000

# 检查依赖服务
docker-compose ps | grep -E "(postgres|redis|neo4j)"
```

### 问题4: 性能问题
```python
# 启用性能监控
from shared.utils import PerformanceMonitor

monitor = PerformanceMonitor()
monitor.start("migration")

# ... 迁移代码 ...

monitor.end("migration")
print(monitor.get_report())
```

## 📈 迁移指标

### 成功标准
- ✅ 数据迁移完整性: > 99.9%
- ✅ 功能迁移完整性: 100%
- ✅ 性能提升: > 30%
- ✅ 用户无感知迁移: 100%
- ✅ 零数据丢失: 100%

### 监控指标
- 迁移进度百分比
- 数据验证通过率
- 服务可用性
- 用户满意度
- 系统性能指标

## 🚨 回滚计划

### 回滚条件
- 数据丢失超过0.1%
- 关键功能失效
- 性能下降超过50%
- 用户投诉率超过5%

### 回滚步骤
```bash
# 1. 停止新系统
docker-compose -f new_architecture/deploy/docker-compose.yml down

# 2. 恢复旧系统
cd SmartParser
docker-compose up -d

# 3. 恢复流量
python switch_traffic.py --percentage=0

# 4. 通知用户
python notify_users.py --message="系统维护中，已恢复旧版本"
```

### 回滚检查点
1. 数据迁移前备份
2. 服务部署前快照
3. 流量切换前状态
4. 用户验收测试前

## 📝 迁移检查清单

### 准备阶段
- [ ] 基础设施部署完成
- [ ] 数据备份完成
- [ ] 配置迁移完成
- [ ] 团队培训完成

### 迁移阶段
- [ ] 数据库架构创建完成
- [ ] 数据迁移完成
- [ ] 数据验证通过
- [ ] 服务部署完成
- [ ] 服务集成测试通过

### 切换阶段
- [ ] 功能测试通过
- [ ] 性能测试通过
- [ ] 用户验收测试通过
- [ ] 流量切换完成
- [ ] 监控告警配置完成

### 完成阶段
- [ ] 旧系统下线
- [ ] 文档更新完成
- [ ] 团队总结完成
- [ ] 迁移报告完成

## 📞 支持资源

### 内部资源
- 迁移团队: migration-team@example.com
- 技术支持: tech-support@example.com
- 紧急联系人: +86-138-0013-8000

### 外部资源
- PostgreSQL文档: https://www.postgresql.org/docs/
- Neo4j文档: https://neo4j.com/docs/
- Docker文档: https://docs.docker.com/
- FastAPI文档: https://fastapi.tiangolo.com/

### 监控面板
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090
- 应用日志: Kibana (如果部署)

---
**迁移版本**: 1.0.0  
**预计完成时间**: 2026-06-30  
**负责人**: 迁移项目经理  
**最后更新**: 2026-03-01