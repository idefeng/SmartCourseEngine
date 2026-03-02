-- SmartCourseEngine SQLite数据库架构
-- 版本: 1.0.0
-- 创建时间: 2026-03-01

-- ============================================================================
-- 核心表
-- ============================================================================

-- 课程表
CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    type TEXT NOT NULL DEFAULT 'video',
    
    -- 视频相关字段
    video_url TEXT,
    video_duration INTEGER CHECK (video_duration >= 0),
    video_quality TEXT,
    thumbnail_url TEXT,
    
    -- 文档相关字段
    document_url TEXT,
    document_format TEXT,
    
    -- 元数据
    author TEXT,
    institution TEXT,
    language TEXT NOT NULL DEFAULT 'zh-CN',
    
    -- 统计信息
    view_count INTEGER NOT NULL DEFAULT 0 CHECK (view_count >= 0),
    like_count INTEGER NOT NULL DEFAULT 0 CHECK (like_count >= 0),
    share_count INTEGER NOT NULL DEFAULT 0 CHECK (share_count >= 0),
    
    -- 状态
    is_published INTEGER NOT NULL DEFAULT 0,
    is_featured INTEGER NOT NULL DEFAULT 0,
    
    -- 时间戳
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 知识点表
CREATE TABLE IF NOT EXISTS knowledge_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    
    -- 分类信息
    category TEXT NOT NULL,
    subcategory TEXT,
    
    -- 重要性评估 (1-5)
    importance INTEGER NOT NULL DEFAULT 3 CHECK (importance >= 1 AND importance <= 5),
    confidence REAL NOT NULL DEFAULT 1.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    
    -- 时间戳
    start_time INTEGER NOT NULL CHECK (start_time >= 0),
    end_time INTEGER NOT NULL CHECK (end_time >= 0),
    
    -- 向量嵌入（存储为JSON文本）
    embedding TEXT,
    
    -- 视觉特征
    visual_features TEXT,
    
    -- 音频特征
    audio_features TEXT,
    
    -- 时间戳
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);

-- 标签表
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL DEFAULT 'custom',
    description TEXT,
    
    -- 统计信息
    usage_count INTEGER NOT NULL DEFAULT 0 CHECK (usage_count >= 0),
    
    -- 颜色和图标
    color TEXT,
    icon TEXT,
    
    -- 时间戳
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 课程-标签关联表
CREATE TABLE IF NOT EXISTS course_tags (
    course_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (course_id, tag_id),
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

-- 知识点-标签关联表
CREATE TABLE IF NOT EXISTS knowledge_point_tags (
    knowledge_point_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (knowledge_point_id, tag_id),
    FOREIGN KEY (knowledge_point_id) REFERENCES knowledge_points(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

-- 视频分析表
CREATE TABLE IF NOT EXISTS video_analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL,
    video_url TEXT NOT NULL,
    
    -- 分析状态
    status TEXT NOT NULL DEFAULT 'pending',
    progress REAL NOT NULL DEFAULT 0.0 CHECK (progress >= 0.0 AND progress <= 1.0),
    
    -- 分析结果
    transcript TEXT,
    transcript_timestamps TEXT,
    
    -- 视觉分析
    keyframes TEXT,
    scene_changes TEXT,
    visual_concepts TEXT,
    
    -- 音频分析
    speaker_diarization TEXT,
    audio_emotions TEXT,
    
    -- 错误信息
    error_message TEXT,
    
    -- 分析统计
    analysis_duration INTEGER CHECK (analysis_duration >= 0),
    model_used TEXT,
    
    -- 时间戳
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);

-- ============================================================================
-- 用户相关表
-- ============================================================================

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    
    -- 用户偏好
    preferences TEXT DEFAULT '{}',
    
    -- 统计信息
    total_learning_time INTEGER NOT NULL DEFAULT 0 CHECK (total_learning_time >= 0),
    completed_courses INTEGER NOT NULL DEFAULT 0 CHECK (completed_courses >= 0),
    
    -- 状态
    is_active INTEGER NOT NULL DEFAULT 1,
    is_verified INTEGER NOT NULL DEFAULT 0,
    
    -- 时间戳
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP
);

-- 用户学习记录表
CREATE TABLE IF NOT EXISTS user_learning_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    knowledge_point_id INTEGER,
    
    -- 学习数据
    start_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    duration INTEGER CHECK (duration >= 0),
    
    -- 掌握程度
    mastery_level REAL CHECK (mastery_level >= 0.0 AND mastery_level <= 1.0),
    confidence REAL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    
    -- 交互数据
    interactions TEXT DEFAULT '[]',
    notes TEXT,
    
    -- 时间戳
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    FOREIGN KEY (knowledge_point_id) REFERENCES knowledge_points(id) ON DELETE SET NULL
);

-- ============================================================================
-- 系统表
-- ============================================================================

-- API密钥表
CREATE TABLE IF NOT EXISTS api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key_hash TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    user_id INTEGER,
    
    -- 权限
    permissions TEXT DEFAULT '[]',
    rate_limit INTEGER NOT NULL DEFAULT 1000 CHECK (rate_limit > 0),
    
    -- 状态
    is_active INTEGER NOT NULL DEFAULT 1,
    expires_at TIMESTAMP,
    
    -- 使用统计
    total_requests INTEGER NOT NULL DEFAULT 0 CHECK (total_requests >= 0),
    last_used_at TIMESTAMP,
    
    -- 时间戳
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 系统日志表
CREATE TABLE IF NOT EXISTS system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level TEXT NOT NULL,
    service TEXT NOT NULL,
    message TEXT NOT NULL,
    
    -- 上下文
    context TEXT DEFAULT '{}',
    trace_id TEXT,
    
    -- 错误信息
    error_type TEXT,
    error_message TEXT,
    stack_trace TEXT,
    
    -- 时间戳
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 视图
-- ============================================================================

-- 课程统计视图
CREATE VIEW IF NOT EXISTS course_statistics AS
SELECT 
    c.id,
    c.title,
    c.type,
    c.view_count,
    c.like_count,
    c.share_count,
    COUNT(DISTINCT kp.id) as knowledge_point_count,
    COUNT(DISTINCT ct.tag_id) as tag_count,
    COUNT(DISTINCT ulr.user_id) as learner_count,
    AVG(ulr.mastery_level) as average_mastery
FROM courses c
LEFT JOIN knowledge_points kp ON c.id = kp.course_id
LEFT JOIN course_tags ct ON c.id = ct.course_id
LEFT JOIN user_learning_records ulr ON c.id = ulr.course_id
GROUP BY c.id, c.title, c.type, c.view_count, c.like_count, c.share_count;

-- 知识点统计视图
CREATE VIEW IF NOT EXISTS knowledge_point_statistics AS
SELECT 
    kp.id,
    kp.name,
    kp.category,
    kp.importance,
    kp.confidence,
    c.title as course_title,
    COUNT(DISTINCT kpt.tag_id) as tag_count,
    COUNT(DISTINCT ulr.user_id) as learner_count,
    AVG(ulr.mastery_level) as average_mastery
FROM knowledge_points kp
JOIN courses c ON kp.course_id = c.id
LEFT JOIN knowledge_point_tags kpt ON kp.id = kpt.knowledge_point_id
LEFT JOIN user_learning_records ulr ON kp.id = ulr.knowledge_point_id
GROUP BY kp.id, kp.name, kp.category, kp.importance, kp.confidence, c.title;

-- ============================================================================
-- 触发器
-- ============================================================================

-- 自动更新updated_at时间戳的触发器
CREATE TRIGGER IF NOT EXISTS update_courses_updated_at 
AFTER UPDATE ON courses
BEGIN
    UPDATE courses SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_knowledge_points_updated_at 
AFTER UPDATE ON knowledge_points
BEGIN
    UPDATE knowledge_points SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_tags_updated_at 
AFTER UPDATE ON tags
BEGIN
    UPDATE tags SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_video_analyses_updated_at 
AFTER UPDATE ON video_analyses
BEGIN
    UPDATE video_analyses SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_users_updated_at 
AFTER UPDATE ON users
BEGIN
    UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_user_learning_records_updated_at 
AFTER UPDATE ON user_learning_records
BEGIN
    UPDATE user_learning_records SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_api_keys_updated_at 
AFTER UPDATE ON api_keys
BEGIN
    UPDATE api_keys SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- 更新标签使用次数的触发器
CREATE TRIGGER IF NOT EXISTS update_tag_usage_count_insert
AFTER INSERT ON course_tags
BEGIN
    UPDATE tags SET usage_count = usage_count + 1 WHERE id = NEW.tag_id;
END;

CREATE TRIGGER IF NOT EXISTS update_tag_usage_count_delete
AFTER DELETE ON course_tags
BEGIN
    UPDATE tags SET usage_count = usage_count - 1 WHERE id = OLD.tag_id;
END;

CREATE TRIGGER IF NOT EXISTS update_kp_tag_usage_count_insert
AFTER INSERT ON knowledge_point_tags
BEGIN
    UPDATE tags SET usage_count = usage_count + 1 WHERE id = NEW.tag_id;
END;

CREATE TRIGGER IF NOT EXISTS update_kp_tag_usage_count_delete
AFTER DELETE ON knowledge_point_tags
BEGIN
    UPDATE tags SET usage_count = usage_count - 1 WHERE id = OLD.tag_id;
END;

-- ============================================================================
-- 索引
-- ============================================================================

-- 课程索引
CREATE INDEX IF NOT EXISTS idx_courses_title ON courses (title);
CREATE INDEX IF NOT EXISTS idx_courses_type_published ON courses (type, is_published) WHERE is_published = 1;

-- 知识点索引
CREATE INDEX IF NOT EXISTS idx_knowledge_points_course_id ON knowledge_points (course_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_points_category ON knowledge_points (category);
CREATE INDEX IF NOT EXISTS idx_knowledge_points_importance ON knowledge_points (importance);
CREATE INDEX IF NOT EXISTS idx_knowledge_points_course_time ON knowledge_points (course_id, start_time, end_time);

-- 标签索引
CREATE INDEX IF NOT EXISTS idx_tags_name ON tags (name);
CREATE INDEX IF NOT EXISTS idx_tags_type ON tags (type);
CREATE INDEX IF NOT EXISTS idx_tags_usage_count ON tags (usage_count DESC);

-- 关联表索引
CREATE INDEX IF NOT EXISTS idx_course_tags_course_id ON course_tags (course_id);
CREATE INDEX IF NOT EXISTS idx_course_tags_tag_id ON course_tags (tag_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_point_tags_kp_id ON knowledge_point_tags (knowledge_point_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_point_tags_tag_id ON knowledge_point_tags (tag_id);

-- 视频分析索引
CREATE INDEX IF NOT EXISTS idx_video_analyses_course_id ON video_analyses (course_id);
CREATE INDEX IF NOT EXISTS idx_video_analyses_status ON video_analyses (status);
CREATE INDEX IF NOT EXISTS idx_video_analyses_created_at ON video_analyses (created_at DESC);

-- 用户索引
CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users (created_at DESC);

-- 用户学习记录索引
CREATE INDEX IF NOT EXISTS idx_user_learning_records_user_id ON user_learning_records (user_id);
CREATE INDEX IF NOT EXISTS idx_user_learning_records_course_id ON user_learning_records (course_id);
CREATE INDEX IF NOT EXISTS idx_user_learning_records_kp_id ON user_learning_records (knowledge_point_id);
CREATE INDEX IF NOT EXISTS idx_user_learning_records_start_time ON user_learning_records (start_time DESC);

-- API密钥索引
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys (user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_is_active ON api_keys (is_active);
CREATE INDEX IF NOT EXISTS idx_api_keys_expires_at ON api_keys (expires_at);

-- 系统日志索引
CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs (level);
CREATE INDEX IF NOT EXISTS idx_system_logs_service ON system_logs (service);
CREATE INDEX IF NOT EXISTS idx_system_logs_created_at ON system_logs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_logs_trace_id ON system_logs (trace_id);

-- ============================================================================
-- 初始化数据
-- ============================================================================

-- 插入默认标签
INSERT OR IGNORE INTO tags (name, type, description, color) VALUES
    ('编程', 'category', '编程相关课程', '#3498db'),
    ('数据科学', 'category', '数据科学和机器学习', '#2ecc71'),
    ('人工智能', 'category', '人工智能和深度学习', '#e74c3c'),
    ('前端开发', 'category', 'Web前端开发', '#f39c12'),
    ('后端开发', 'category', '服务器端开发', '#9b59b6'),
    ('入门', 'difficulty', '适合初学者的内容', '#1abc9c'),
    ('中级', 'difficulty', '需要一定基础', '#f1c40f'),
    ('高级', 'difficulty', '深入专业内容', '#e67e22'),
    ('实战项目', 'topic', '包含实际项目', '#34495e'),
    ('理论讲解', 'topic', '理论概念讲解', '#7f8c8d');

-- 插入演示用户
INSERT OR IGNORE INTO users (username, email, password_hash, full_name, is_verified) VALUES
    ('demo_user', 'demo@example.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', '演示用户', 1);

-- 插入演示API密钥
INSERT OR IGNORE INTO api_keys (key_hash, name, user_id, permissions, rate_limit) VALUES
    ('demo_api_key_hash', '演示API密钥', (SELECT id FROM users WHERE email = 'demo@example.com'), '["read", "write"]', 10000);

-- 记录架构版本
INSERT INTO system_logs (level, service, message, context) VALUES
    ('INFO', 'database', 'SQLite数据库架构初始化完成', '{"version": "1.0.0", "timestamp": "2026-03-01T20:10:00Z"}');

-- ============================================================================
-- 完成
-- ============================================================================

SELECT '数据库架构初始化完成' AS message;