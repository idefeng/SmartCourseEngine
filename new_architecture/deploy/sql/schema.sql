-- SmartCourseEngine 数据库架构
-- 版本: 1.0.0
-- 创建时间: 2026-03-01

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- 用于文本搜索
CREATE EXTENSION IF NOT EXISTS "vector";   -- 用于向量操作（如果安装）

-- 创建枚举类型
CREATE TYPE course_type AS ENUM ('video', 'document', 'interactive', 'live', 'hybrid');
CREATE TYPE knowledge_importance AS ENUM ('1', '2', '3', '4', '5');
CREATE TYPE tag_type AS ENUM ('category', 'topic', 'skill', 'difficulty', 'custom');
CREATE TYPE analysis_status AS ENUM ('pending', 'processing', 'completed', 'failed');
CREATE TYPE video_quality AS ENUM ('sd', 'hd', 'fhd', 'uhd');

-- ============================================================================
-- 核心表
-- ============================================================================

-- 课程表
CREATE TABLE courses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    type course_type NOT NULL DEFAULT 'video',
    
    -- 视频相关字段
    video_url VARCHAR(500),
    video_duration INTEGER CHECK (video_duration >= 0),
    video_quality video_quality,
    thumbnail_url VARCHAR(500),
    
    -- 文档相关字段
    document_url VARCHAR(500),
    document_format VARCHAR(50),
    
    -- 元数据
    author VARCHAR(100),
    institution VARCHAR(200),
    language VARCHAR(10) NOT NULL DEFAULT 'zh-CN',
    
    -- 统计信息
    view_count INTEGER NOT NULL DEFAULT 0 CHECK (view_count >= 0),
    like_count INTEGER NOT NULL DEFAULT 0 CHECK (like_count >= 0),
    share_count INTEGER NOT NULL DEFAULT 0 CHECK (share_count >= 0),
    
    -- 状态
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    is_featured BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引
    CONSTRAINT valid_video_url CHECK (video_url IS NULL OR video_url ~ '^https?://'),
    CONSTRAINT valid_document_url CHECK (document_url IS NULL OR document_url ~ '^https?://')
);

-- 知识点表
CREATE TABLE knowledge_points (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    
    -- 分类信息
    category VARCHAR(100) NOT NULL,
    subcategory VARCHAR(100),
    
    -- 重要性评估
    importance knowledge_importance NOT NULL DEFAULT '3',
    confidence FLOAT NOT NULL DEFAULT 1.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    
    -- 时间戳
    start_time INTEGER NOT NULL CHECK (start_time >= 0),
    end_time INTEGER NOT NULL CHECK (end_time >= 0),
    
    -- 向量嵌入（存储为JSON，实际使用Pinecone）
    embedding JSONB,
    
    -- 视觉特征
    visual_features JSONB,
    
    -- 音频特征
    audio_features JSONB,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引
    CONSTRAINT valid_time_range CHECK (end_time > start_time),
    INDEX idx_knowledge_points_course_id (course_id),
    INDEX idx_knowledge_points_category (category),
    INDEX idx_knowledge_points_importance (importance)
);

-- 标签表
CREATE TABLE tags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL,
    type tag_type NOT NULL DEFAULT 'custom',
    description VARCHAR(200),
    
    -- 统计信息
    usage_count INTEGER NOT NULL DEFAULT 0 CHECK (usage_count >= 0),
    
    -- 颜色和图标
    color VARCHAR(7),  -- 十六进制颜色代码
    icon VARCHAR(100),
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- 约束和索引
    CONSTRAINT unique_tag_name UNIQUE (name),
    CONSTRAINT valid_color CHECK (color IS NULL OR color ~ '^#[0-9A-Fa-f]{6}$'),
    INDEX idx_tags_type (type),
    INDEX idx_tags_usage_count (usage_count DESC)
);

-- 课程-标签关联表
CREATE TABLE course_tags (
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (course_id, tag_id),
    INDEX idx_course_tags_course_id (course_id),
    INDEX idx_course_tags_tag_id (tag_id)
);

-- 知识点-标签关联表
CREATE TABLE knowledge_point_tags (
    knowledge_point_id UUID NOT NULL REFERENCES knowledge_points(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (knowledge_point_id, tag_id),
    INDEX idx_kp_tags_kp_id (knowledge_point_id),
    INDEX idx_kp_tags_tag_id (tag_id)
);

-- 视频分析表
CREATE TABLE video_analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    video_url VARCHAR(500) NOT NULL,
    
    -- 分析状态
    status analysis_status NOT NULL DEFAULT 'pending',
    progress FLOAT NOT NULL DEFAULT 0.0 CHECK (progress >= 0.0 AND progress <= 1.0),
    
    -- 分析结果
    transcript TEXT,
    transcript_timestamps JSONB,
    
    -- 视觉分析
    keyframes JSONB,
    scene_changes JSONB,
    visual_concepts JSONB,
    
    -- 音频分析
    speaker_diarization JSONB,
    audio_emotions JSONB,
    
    -- 错误信息
    error_message TEXT,
    
    -- 分析统计
    analysis_duration INTEGER CHECK (analysis_duration >= 0),
    model_used VARCHAR(200),
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- 索引
    CONSTRAINT valid_video_url_analysis CHECK (video_url ~ '^https?://'),
    INDEX idx_video_analyses_course_id (course_id),
    INDEX idx_video_analyses_status (status),
    INDEX idx_video_analyses_created_at (created_at DESC)
);

-- ============================================================================
-- 用户相关表
-- ============================================================================

-- 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    
    -- 用户偏好
    preferences JSONB DEFAULT '{}',
    
    -- 统计信息
    total_learning_time INTEGER NOT NULL DEFAULT 0 CHECK (total_learning_time >= 0),
    completed_courses INTEGER NOT NULL DEFAULT 0 CHECK (completed_courses >= 0),
    
    -- 状态
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE,
    
    -- 索引
    INDEX idx_users_email (email),
    INDEX idx_users_username (username),
    INDEX idx_users_created_at (created_at DESC)
);

-- 用户学习记录表
CREATE TABLE user_learning_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    knowledge_point_id UUID REFERENCES knowledge_points(id) ON DELETE SET NULL,
    
    -- 学习数据
    start_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP WITH TIME ZONE,
    duration INTEGER CHECK (duration >= 0),
    
    -- 掌握程度
    mastery_level FLOAT CHECK (mastery_level >= 0.0 AND mastery_level <= 1.0),
    confidence FLOAT CHECK (confidence >= 0.0 AND confidence <= 1.0),
    
    -- 交互数据
    interactions JSONB DEFAULT '[]',
    notes TEXT,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引
    INDEX idx_ulr_user_id (user_id),
    INDEX idx_ulr_course_id (course_id),
    INDEX idx_ulr_knowledge_point_id (knowledge_point_id),
    INDEX idx_ulr_start_time (start_time DESC)
);

-- ============================================================================
-- 系统表
-- ============================================================================

-- API密钥表
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    -- 权限
    permissions JSONB DEFAULT '[]',
    rate_limit INTEGER NOT NULL DEFAULT 1000 CHECK (rate_limit > 0),
    
    -- 状态
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    expires_at TIMESTAMP WITH TIME ZONE,
    
    -- 使用统计
    total_requests INTEGER NOT NULL DEFAULT 0 CHECK (total_requests >= 0),
    last_used_at TIMESTAMP WITH TIME ZONE,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引
    INDEX idx_api_keys_user_id (user_id),
    INDEX idx_api_keys_is_active (is_active),
    INDEX idx_api_keys_expires_at (expires_at)
);

-- 系统日志表
CREATE TABLE system_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    level VARCHAR(20) NOT NULL,
    service VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    
    -- 上下文
    context JSONB DEFAULT '{}',
    trace_id VARCHAR(100),
    
    -- 错误信息
    error_type VARCHAR(100),
    error_message TEXT,
    stack_trace TEXT,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- 索引
    INDEX idx_system_logs_level (level),
    INDEX idx_system_logs_service (service),
    INDEX idx_system_logs_created_at (created_at DESC),
    INDEX idx_system_logs_trace_id (trace_id)
);

-- ============================================================================
-- 视图
-- ============================================================================

-- 课程统计视图
CREATE VIEW course_statistics AS
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
CREATE VIEW knowledge_point_statistics AS
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
-- 函数和触发器
-- ============================================================================

-- 自动更新updated_at时间戳的函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为所有表创建updated_at触发器
CREATE TRIGGER update_courses_updated_at BEFORE UPDATE ON courses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_knowledge_points_updated_at BEFORE UPDATE ON knowledge_points
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tags_updated_at BEFORE UPDATE ON tags
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_video_analyses_updated_at BEFORE UPDATE ON video_analyses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_learning_records_updated_at BEFORE UPDATE ON user_learning_records
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_api_keys_updated_at BEFORE UPDATE ON api_keys
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 更新标签使用次数的函数
CREATE OR REPLACE FUNCTION update_tag_usage_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE tags SET usage_count = usage_count + 1 WHERE id = NEW.tag_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE tags SET usage_count = usage_count - 1 WHERE id = OLD.tag_id;
    END IF;
    RETURN NULL;
END;
$$ language 'plpgsql';

-- 为关联表创建标签使用次数触发器
CREATE TRIGGER update_course_tag_usage AFTER INSERT OR DELETE ON course_tags
    FOR EACH ROW EXECUTE FUNCTION update_tag_usage_count();

CREATE TRIGGER update_knowledge_point_tag_usage AFTER INSERT OR DELETE ON knowledge_point_tags
    FOR EACH ROW EXECUTE FUNCTION update_tag_usage_count();

-- ============================================================================
-- 索引优化
-- ============================================================================

-- 全文搜索索引
CREATE INDEX idx_courses_title_description_gin ON courses 
    USING gin(to_tsvector('chinese', coalesce(title, '') || ' ' || coalesce(description, '')));

CREATE INDEX idx_knowledge_points_name_description_gin ON knowledge_points 
    USING gin(to_tsvector('chinese', coalesce(name, '') || ' ' || coalesce(description, '')));

-- 复合索引
CREATE INDEX idx_courses_type_published ON courses (type, is_published) WHERE is_published = TRUE;
CREATE INDEX idx_knowledge_points_course_time ON knowledge_points (course_id, start_time, end_time);
CREATE INDEX idx_video_analyses_status_progress ON video_analyses (status, progress);

-- ============================================================================
-- 注释
-- ============================================================================

COMMENT ON TABLE courses IS '课程信息表';
COMMENT ON TABLE knowledge_points IS '知识点表';
COMMENT ON TABLE tags IS '标签表';
COMMENT ON TABLE video_analyses IS '视频分析结果表';
COMMENT ON TABLE users IS '用户表';
COMMENT ON TABLE user_learning_records IS '用户学习记录表';

COMMENT ON COLUMN courses.video_duration IS '视频时长（秒）';
COMMENT ON COLUMN knowledge_points.start_time IS '知识点开始时间（秒）';
COMMENT ON COLUMN knowledge_points.end_time IS '知识点结束时间（秒）';
COMMENT ON COLUMN knowledge_points.embedding IS '知识点向量嵌入（JSON格式）';

-- ============================================================================
-- 初始化数据
-- ============================================================================

-- 插入默认标签
INSERT INTO tags (name, type, description, color) VALUES
    ('编程', 'category', '编程相关课程', '#3498db'),
    ('数据科学', 'category', '数据科学和机器学习', '#2ecc71'),
    ('人工智能', 'category', '人工智能和深度学习', '#e74c3c'),
    ('前端开发', 'category', 'Web前端开发', '#f39c12'),
    ('后端开发', 'category', '服务器端开发', '#9b59b6'),
    ('入门', 'difficulty', '适合初学者的内容', '#1abc9c'),
    ('中级', 'difficulty', '需要一定基础', '#f1c40f'),
    ('高级', 'difficulty', '深入专业内容', '#e67e22'),
    ('实战项目', 'topic', '包含实际项目', '#34495e'),
    ('理论讲解', 'topic', '理论概念讲解', '#7f8c8d')
ON CONFLICT (name) DO NOTHING;

-- 插入演示用户
INSERT INTO users (username, email, password_hash, full_name, is_verified) VALUES
    ('demo_user', 'demo@example.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', '演示用户', TRUE)
ON CONFLICT (email) DO NOTHING;

-- 插入演示API密钥
INSERT INTO api_keys (key_hash, name, user_id, permissions, rate_limit) VALUES
    ('demo_api_key_hash', '演示API密钥', (SELECT id FROM users WHERE email = 'demo@example.com'), '["read", "write"]', 10000)
ON CONFLICT (key_hash) DO NOTHING;

-- ============================================================================
-- 完成
-- ============================================================================

-- 记录架构版本
INSERT INTO system_logs (level, service, message, context) VALUES
    ('INFO', 'database', '数据库架构初始化完成', '{"version": "1.0.0", "timestamp": "2026-03-01T19:39:00Z"}');