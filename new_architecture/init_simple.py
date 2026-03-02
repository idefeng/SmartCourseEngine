#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化数据库初始化脚本
==================

使用SQLite初始化SmartCourseEngine数据库。

作者: SmartCourseEngine Team
日期: 2026-03-01
"""

import os
import sys
import sqlite3
from pathlib import Path

def create_tables(cursor):
    """创建数据库表"""
    print("创建数据库表...")
    
    # 课程表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            type TEXT DEFAULT 'video',
            language TEXT DEFAULT 'zh-CN',
            author TEXT,
            is_published INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 知识点表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            importance INTEGER DEFAULT 3,
            confidence REAL DEFAULT 1.0,
            start_time INTEGER NOT NULL,
            end_time INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
        )
    """)
    
    # 标签表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            type TEXT DEFAULT 'custom',
            description TEXT,
            color TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 课程-标签关联表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS course_tags (
            course_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (course_id, tag_id),
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        )
    """)
    
    # 用户表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            is_verified INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    print("数据库表创建完成")

def insert_demo_data(cursor):
    """插入演示数据"""
    print("插入演示数据...")
    
    # 插入演示标签
    demo_tags = [
        ('编程', 'category', '编程相关课程', '#3498db'),
        ('数据科学', 'category', '数据科学和机器学习', '#2ecc71'),
        ('人工智能', 'category', '人工智能和深度学习', '#e74c3c'),
        ('Python', 'topic', 'Python编程语言', '#3776ab'),
        ('入门', 'difficulty', '适合初学者的内容', '#1abc9c'),
        ('中级', 'difficulty', '需要一定基础', '#f1c40f'),
        ('实战项目', 'topic', '包含实际项目', '#34495e')
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
    
    # 关联课程和标签
    cursor.execute("SELECT id FROM tags WHERE name IN ('编程', 'Python', '入门')")
    tag_ids = [row[0] for row in cursor.fetchall()]
    
    for tag_id in tag_ids:
        cursor.execute(
            "INSERT OR IGNORE INTO course_tags (course_id, tag_id) VALUES (?, ?)",
            (course_id, tag_id)
        )
    
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
    
    print("演示数据插入完成")

def main():
    """主函数"""
    print("=" * 60)
    print("SmartCourseEngine 简化数据库初始化")
    print("=" * 60)
    
    # 数据库路径
    db_path = Path("./data/smartcourse.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 连接到数据库
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    try:
        cursor = conn.cursor()
        
        # 创建表
        create_tables(cursor)
        
        # 插入演示数据
        insert_demo_data(cursor)
        
        # 提交事务
        conn.commit()
        
        # 验证数据
        print("\n验证数据库内容...")
        
        cursor.execute("SELECT COUNT(*) as count FROM courses")
        course_count = cursor.fetchone()['count']
        print(f"课程数量: {course_count}")
        
        cursor.execute("SELECT COUNT(*) as count FROM knowledge_points")
        kp_count = cursor.fetchone()['count']
        print(f"知识点数量: {kp_count}")
        
        cursor.execute("SELECT COUNT(*) as count FROM tags")
        tag_count = cursor.fetchone()['count']
        print(f"标签数量: {tag_count}")
        
        cursor.execute("SELECT COUNT(*) as count FROM users")
        user_count = cursor.fetchone()['count']
        print(f"用户数量: {user_count}")
        
        # 查询演示课程详情
        cursor.execute("""
            SELECT c.title, c.description, 
                   GROUP_CONCAT(t.name) as tags,
                   COUNT(kp.id) as knowledge_point_count
            FROM courses c
            LEFT JOIN course_tags ct ON c.id = ct.course_id
            LEFT JOIN tags t ON ct.tag_id = t.id
            LEFT JOIN knowledge_points kp ON c.id = kp.course_id
            WHERE c.id = 1
            GROUP BY c.id
        """)
        
        course_info = cursor.fetchone()
        if course_info:
            print(f"\n演示课程详情:")
            print(f"  标题: {course_info['title']}")
            print(f"  描述: {course_info['description']}")
            print(f"  标签: {course_info['tags']}")
            print(f"  知识点数量: {course_info['knowledge_point_count']}")
        
        print("\n" + "=" * 60)
        print("✅ 数据库初始化成功!")
        print(f"数据库文件: {db_path.absolute()}")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ 数据库初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        conn.close()

if __name__ == "__main__":
    sys.exit(main())