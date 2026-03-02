#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite数据库初始化脚本
====================

初始化SmartCourseEngine的SQLite数据库。

作者: SmartCourseEngine Team
日期: 2026-03-01
"""

import os
import sys
import sqlite3
from pathlib import Path

# ============================================================================
# 配置
# ============================================================================

# 数据库路径
DB_PATH = Path("./data/smartcourse.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# ============================================================================
# SQLite初始化
# ============================================================================

def init_sqlite():
    """初始化SQLite数据库"""
    print("开始初始化SQLite数据库...")
    
    # 读取SQL schema文件
    schema_file = Path(__file__).parent / "deploy" / "sql" / "schema.sql"
    if not schema_file.exists():
        print(f"错误: SQL schema文件不存在: {schema_file}")
        return False
    
    with open(schema_file, 'r', encoding='utf-8') as f:
        sql_commands = f.read()
    
    # 连接到SQLite
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 允许按列名访问
    
    try:
        cursor = conn.cursor()
        
        # 分割SQL命令（简化处理）
        # 移除PostgreSQL特定的扩展和类型
        sql_commands = sql_commands.replace('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";', '')
        sql_commands = sql_commands.replace('CREATE EXTENSION IF NOT EXISTS "pg_trgm";', '')
        sql_commands = sql_commands.replace('CREATE EXTENSION IF NOT EXISTS "vector";', '')
        
        # 替换PostgreSQL特定的语法
        sql_commands = sql_commands.replace('CREATE TYPE course_type AS ENUM', '')
        sql_commands = sql_commands.replace('CREATE TYPE knowledge_importance AS ENUM', '')
        sql_commands = sql_commands.replace('CREATE TYPE tag_type AS ENUM', '')
        sql_commands = sql_commands.replace('CREATE TYPE analysis_status AS ENUM', '')
        sql_commands = sql_commands.replace('CREATE TYPE video_quality AS ENUM', '')
        
        # 替换UUID为INTEGER PRIMARY KEY AUTOINCREMENT
        sql_commands = sql_commands.replace('UUID PRIMARY KEY DEFAULT uuid_generate_v4()', 'INTEGER PRIMARY KEY AUTOINCREMENT')
        sql_commands = sql_commands.replace('UUID NOT NULL REFERENCES', 'INTEGER NOT NULL REFERENCES')
        sql_commands = sql_commands.replace('UUID REFERENCES', 'INTEGER REFERENCES')
        
        # 替换PostgreSQL特定的数据类型
        sql_commands = sql_commands.replace('TIMESTAMP WITH TIME ZONE', 'TIMESTAMP')
        sql_commands = sql_commands.replace('VARCHAR', 'TEXT')
        sql_commands = sql_commands.replace('FLOAT', 'REAL')
        sql_commands = sql_commands.replace('JSONB', 'TEXT')
        
        # 移除PostgreSQL特定的约束
        sql_commands = sql_commands.replace('CONSTRAINT valid_video_url CHECK (video_url IS NULL OR video_url ~ \'^https?://\'),', '')
        sql_commands = sql_commands.replace('CONSTRAINT valid_document_url CHECK (document_url IS NULL OR document_url ~ \'^https?://\')', '')
        sql_commands = sql_commands.replace('CONSTRAINT valid_time_range CHECK (end_time > start_time),', '')
        sql_commands = sql_commands.replace('CONSTRAINT valid_color CHECK (color IS NULL OR color ~ \'^#[0-9A-Fa-f]{6}$\'),', '')
        sql_commands = sql_commands.replace('CONSTRAINT unique_tag_name UNIQUE (name),', 'UNIQUE (name),')
        
        # 移除PostgreSQL特定的索引语法
        sql_commands = sql_commands.replace('INDEX idx_knowledge_points_course_id (course_id),', '')
        sql_commands = sql_commands.replace('INDEX idx_knowledge_points_category (category),', '')
        sql_commands = sql_commands.replace('INDEX idx_knowledge_points_importance (importance)', '')
        sql_commands = sql_commands.replace('INDEX idx_tags_type (type),', '')
        sql_commands = sql_commands.replace('INDEX idx_tags_usage_count (usage_count DESC)', '')
        sql_commands = sql_commands.replace('INDEX idx_course_tags_course_id (course_id),', '')
        sql_commands = sql_commands.replace('INDEX idx_course_tags_tag_id (tag_id)', '')
        sql_commands = sql_commands.replace('INDEX idx_kp_tags_kp_id (knowledge_point_id),', '')
        sql_commands = sql_commands.replace('INDEX idx_kp_tags_tag_id (tag_id)', '')
        sql_commands = sql_commands.replace('INDEX idx_video_analyses_course_id (course_id),', '')
        sql_commands = sql_commands.replace('INDEX idx_video_analyses_status (status),', '')
        sql_commands = sql_commands.replace('INDEX idx_video_analyses_created_at (created_at DESC)', '')
        sql_commands = sql_commands.replace('INDEX idx_users_email (email),', '')
        sql_commands = sql_commands.replace('INDEX idx_users_username (username),', '')
        sql_commands = sql_commands.replace('INDEX idx_users_created_at (created_at DESC)', '')
        sql_commands = sql_commands.replace('INDEX idx_ulr_user_id (user_id),', '')
        sql_commands = sql_commands.replace('INDEX idx_ulr_course_id (course_id),', '')
        sql_commands = sql_commands.replace('INDEX idx_ulr_knowledge_point_id (knowledge_point_id),', '')
        sql_commands = sql_commands.replace('INDEX idx_ulr_start_time (start_time DESC)', '')
        sql_commands = sql_commands.replace('INDEX idx_api_keys_user_id (user_id),', '')
        sql_commands = sql_commands.replace('INDEX idx_api_keys_is_active (is_active),', '')
        sql_commands = sql_commands.replace('INDEX idx_api_keys_expires_at (expires_at)', '')
        sql_commands = sql_commands.replace('INDEX idx_system_logs_level (level),', '')
        sql_commands = sql_commands.replace('INDEX idx_system_logs_service (service),', '')
        sql_commands = sql_commands.replace('INDEX idx_system_logs_created_at (created_at DESC),', '')
        sql_commands = sql_commands.replace('INDEX idx_system_logs_trace_id (trace_id)', '')
        
        # 移除PostgreSQL特定的函数和触发器
        sql_commands = sql_commands.split('-- ============================================================================')[0]
        
        # 执行SQL命令
        cursor.executescript(sql_commands)
        
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_points_course_id ON knowledge_points (course_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_points_category ON knowledge_points (category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_name ON tags (name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_courses_title ON courses (title)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users (username)")
        
        # 插入演示数据
        insert_demo_data(cursor)
        
        conn.commit()
        print("SQLite数据库初始化成功")
        return True
        
    except Exception as e:
        print(f"SQLite初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

def insert_demo_data(cursor):
    """插入演示数据"""
    print("插入演示数据...")
    
    # 插入演示标签
    demo_tags = [
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
    ]
    
    for tag in demo_tags:
        cursor.execute(
            "INSERT OR IGNORE INTO tags (name, type, description, color) VALUES (?, ?, ?, ?)",
            tag
        )
    
    # 插入演示课程
    cursor.execute("""
        INSERT OR IGNORE INTO courses (title, description, type, language, author, is_published)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        'Python编程入门',
        '学习Python基础编程知识，从零开始掌握Python编程',
        'video',
        'zh-CN',
        '智能课程团队',
        1
    ))
    
    # 获取课程ID
    course_id = cursor.lastrowid
    
    # 插入演示知识点
    demo_knowledge_points = [
        (course_id, '变量和数据类型', '学习Python中的变量声明和基本数据类型', '编程基础', 3, 1.0, 0, 300),
        (course_id, '条件语句', '学习if-else条件判断', '控制流', 4, 1.0, 300, 600),
        (course_id, '循环语句', '学习for和while循环', '控制流', 4, 1.0, 600, 900),
        (course_id, '函数定义', '学习如何定义和调用函数', '函数', 5, 1.0, 900, 1200)
    ]
    
    for kp in demo_knowledge_points:
        cursor.execute("""
            INSERT INTO knowledge_points 
            (course_id, name, description, category, importance, confidence, start_time, end_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, kp)
    
    # 插入演示用户
    cursor.execute("""
        INSERT OR IGNORE INTO users (username, email, password_hash, full_name, is_verified)
        VALUES (?, ?, ?, ?, ?)
    """, (
        'demo_user',
        'demo@example.com',
        '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
        '演示用户',
        1
    ))
    
    print(f"插入演示数据完成: 课程1个, 知识点4个, 标签10个, 用户1个")

# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数"""
    print("=" * 60)
    print("SmartCourseEngine SQLite数据库初始化")
    print("=" * 60)
    
    # 初始化SQLite
    success = init_sqlite()
    
    if success:
        print("\n✅ SQLite数据库初始化完成!")
        print(f"数据库文件: {DB_PATH.absolute()}")
        
        # 测试查询
        print("\n测试查询...")
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 查询表数量
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"创建的表数量: {len(tables)}")
        
        # 查询课程
        cursor.execute("SELECT COUNT(*) as count FROM courses")
        course_count = cursor.fetchone()['count']
        print(f"课程数量: {course_count}")
        
        # 查询知识点
        cursor.execute("SELECT COUNT(*) as count FROM knowledge_points")
        kp_count = cursor.fetchone()['count']
        print(f"知识点数量: {kp_count}")
        
        # 查询标签
        cursor.execute("SELECT COUNT(*) as count FROM tags")
        tag_count = cursor.fetchone()['count']
        print(f"标签数量: {tag_count}")
        
        # 查询用户
        cursor.execute("SELECT COUNT(*) as count FROM users")
        user_count = cursor.fetchone()['count']
        print(f"用户数量: {user_count}")
        
        conn.close()
        
        print("\n🎉 数据库初始化验证通过!")
    else:
        print("\n❌ 数据库初始化失败")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())