-- SmartCourseEngine 知识图谱架构
-- Neo4j Cypher脚本
-- 版本: 1.0.0
-- 创建时间: 2026-03-01

-- ============================================================================
-- 创建约束和索引
-- ============================================================================

-- 创建节点唯一性约束
CREATE CONSTRAINT course_id_unique IF NOT EXISTS FOR (c:Course) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT knowledge_point_id_unique IF NOT EXISTS FOR (kp:KnowledgePoint) REQUIRE kp.id IS UNIQUE;
CREATE CONSTRAINT tag_id_unique IF NOT EXISTS FOR (t:Tag) REQUIRE t.id IS UNIQUE;
CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE;

-- 创建索引
CREATE INDEX course_title_index IF NOT EXISTS FOR (c:Course) ON (c.title);
CREATE INDEX knowledge_point_name_index IF NOT EXISTS FOR (kp:KnowledgePoint) ON (kp.name);
CREATE INDEX tag_name_index IF NOT EXISTS FOR (t:Tag) ON (t.name);
CREATE INDEX user_username_index IF NOT EXISTS FOR (u:User) ON (u.username);

-- ============================================================================
-- 创建演示数据
-- ============================================================================

-- 创建演示课程
MERGE (c:Course {
    id: 'demo-course-001',
    title: 'Python编程入门',
    description: '学习Python基础编程知识',
    type: 'video',
    language: 'zh-CN',
    created_at: datetime('2026-03-01T10:00:00Z'),
    updated_at: datetime('2026-03-01T10:00:00Z')
})
RETURN c;

-- 创建演示知识点
MERGE (kp1:KnowledgePoint {
    id: 'demo-kp-001',
    name: '变量和数据类型',
    description: '学习Python中的变量声明和基本数据类型',
    category: '编程基础',
    importance: 3,
    start_time: 0,
    end_time: 300
})
MERGE (kp2:KnowledgePoint {
    id: 'demo-kp-002',
    name: '条件语句',
    description: '学习if-else条件判断',
    category: '控制流',
    importance: 4,
    start_time: 300,
    end_time: 600
})
MERGE (kp3:KnowledgePoint {
    id: 'demo-kp-003',
    name: '循环语句',
    description: '学习for和while循环',
    category: '控制流',
    importance: 4,
    start_time: 600,
    end_time: 900
})
MERGE (kp4:KnowledgePoint {
    id: 'demo-kp-004',
    name: '函数定义',
    description: '学习如何定义和调用函数',
    category: '函数',
    importance: 5,
    start_time: 900,
    end_time: 1200
});

-- 创建演示标签
MERGE (t1:Tag {
    id: 'demo-tag-001',
    name: '编程',
    type: 'category',
    color: '#3498db'
})
MERGE (t2:Tag {
    id: 'demo-tag-002',
    name: 'Python',
    type: 'topic',
    color: '#3776ab'
})
MERGE (t3:Tag {
    id: 'demo-tag-003',
    name: '入门',
    type: 'difficulty',
    color: '#1abc9c'
})
MERGE (t4:Tag {
    id: 'demo-tag-004',
    name: '控制流',
    type: 'topic',
    color: '#e74c3c'
})
MERGE (t5:Tag {
    id: 'demo-tag-005',
    name: '函数',
    type: 'topic',
    color: '#f39c12'
});

-- 创建演示用户
MERGE (u:User {
    id: 'demo-user-001',
    username: 'demo_user',
    email: 'demo@example.com',
    created_at: datetime('2026-03-01T10:00:00Z')
});

-- ============================================================================
-- 创建关系
-- ============================================================================

-- 课程包含知识点
MATCH (c:Course {id: 'demo-course-001'})
MATCH (kp1:KnowledgePoint {id: 'demo-kp-001'})
MATCH (kp2:KnowledgePoint {id: 'demo-kp-002'})
MATCH (kp3:KnowledgePoint {id: 'demo-kp-003'})
MATCH (kp4:KnowledgePoint {id: 'demo-kp-004'})
MERGE (c)-[:CONTAINS {timestamp: 0}]->(kp1)
MERGE (c)-[:CONTAINS {timestamp: 300}]->(kp2)
MERGE (c)-[:CONTAINS {timestamp: 600}]->(kp3)
MERGE (c)-[:CONTAINS {timestamp: 900}]->(kp4);

-- 知识点之间的关系
MATCH (kp1:KnowledgePoint {id: 'demo-kp-001'})
MATCH (kp2:KnowledgePoint {id: 'demo-kp-002'})
MATCH (kp3:KnowledgePoint {id: 'demo-kp-003'})
MATCH (kp4:KnowledgePoint {id: 'demo-kp-004'})
MERGE (kp1)-[:PREREQUISITE_FOR]->(kp2)
MERGE (kp1)-[:PREREQUISITE_FOR]->(kp3)
MERGE (kp2)-[:RELATED_TO {relation: 'similar'}]->(kp3)
MERGE (kp3)-[:LEADS_TO]->(kp4);

-- 课程和标签的关系
MATCH (c:Course {id: 'demo-course-001'})
MATCH (t1:Tag {id: 'demo-tag-001'})
MATCH (t2:Tag {id: 'demo-tag-002'})
MATCH (t3:Tag {id: 'demo-tag-003'})
MERGE (c)-[:HAS_TAG]->(t1)
MERGE (c)-[:HAS_TAG]->(t2)
MERGE (c)-[:HAS_TAG]->(t3);

-- 知识点和标签的关系
MATCH (kp1:KnowledgePoint {id: 'demo-kp-001'})
MATCH (kp2:KnowledgePoint {id: 'demo-kp-002'})
MATCH (kp3:KnowledgePoint {id: 'demo-kp-003'})
MATCH (kp4:KnowledgePoint {id: 'demo-kp-004'})
MATCH (t4:Tag {id: 'demo-tag-004'})
MATCH (t5:Tag {id: 'demo-tag-005'})
MERGE (kp2)-[:HAS_TAG]->(t4)
MERGE (kp3)-[:HAS_TAG]->(t4)
MERGE (kp4)-[:HAS_TAG]->(t5);

-- 用户学习关系
MATCH (u:User {id: 'demo-user-001'})
MATCH (c:Course {id: 'demo-course-001'})
MATCH (kp1:KnowledgePoint {id: 'demo-kp-001'})
MATCH (kp2:KnowledgePoint {id: 'demo-kp-002'})
MERGE (u)-[:STUDIED {
    started_at: datetime('2026-03-01T10:30:00Z'),
    completed_at: datetime('2026-03-01T11:00:00Z'),
    mastery: 0.8
}]->(c)
MERGE (u)-[:LEARNED {
    timestamp: datetime('2026-03-01T10:35:00Z'),
    confidence: 0.9
}]->(kp1)
MERGE (u)-[:LEARNED {
    timestamp: datetime('2026-03-01T10:45:00Z'),
    confidence: 0.7
}]->(kp2);

-- ============================================================================
-- 查询示例
-- ============================================================================

-- 示例1: 查找课程的所有知识点
MATCH (c:Course {id: 'demo-course-001'})-[:CONTAINS]->(kp:KnowledgePoint)
RETURN c.title, kp.name, kp.start_time, kp.end_time
ORDER BY kp.start_time;

-- 示例2: 查找知识点的前置知识点
MATCH (kp:KnowledgePoint {id: 'demo-kp-004'})<-[:PREREQUISITE_FOR*1..3]-(prereq:KnowledgePoint)
RETURN kp.name AS target, prereq.name AS prerequisite
ORDER BY prereq.start_time;

-- 示例3: 查找用户学习过的知识点
MATCH (u:User {username: 'demo_user'})-[:LEARNED]->(kp:KnowledgePoint)
RETURN u.username, kp.name, kp.category, kp.importance
ORDER BY kp.importance DESC;

-- 示例4: 查找相关课程（通过标签）
MATCH (c:Course)-[:HAS_TAG]->(t:Tag {name: 'Python'})
RETURN c.title, c.type, collect(t.name) AS tags
ORDER BY c.title;

-- 示例5: 知识图谱路径查询
MATCH path = (kp1:KnowledgePoint {name: '变量和数据类型'})-[:PREREQUISITE_FOR|LEADS_TO*1..5]->(kp2:KnowledgePoint)
RETURN [node IN nodes(path) | node.name] AS path_nodes,
       [rel IN relationships(path) | type(rel)] AS relationships
ORDER BY length(path);

-- ============================================================================
-- 统计查询
-- ============================================================================

-- 统计课程的知识点数量
MATCH (c:Course)-[:CONTAINS]->(kp:KnowledgePoint)
RETURN c.title, count(kp) AS knowledge_point_count
ORDER BY knowledge_point_count DESC;

-- 统计标签使用情况
MATCH (t:Tag)<-[:HAS_TAG]-(node)
WHERE node:Course OR node:KnowledgePoint
RETURN t.name, t.type, count(node) AS usage_count
ORDER BY usage_count DESC;

-- 统计用户学习进度
MATCH (u:User)-[r:LEARNED]->(kp:KnowledgePoint)
RETURN u.username, count(r) AS learned_count, avg(r.confidence) AS avg_confidence
ORDER BY learned_count DESC;

-- ============================================================================
-- 完成
-- ============================================================================

RETURN '知识图谱架构初始化完成' AS message;