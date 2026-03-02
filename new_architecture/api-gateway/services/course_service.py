#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
课程服务
========

提供课程相关的业务逻辑。

作者: SmartCourseEngine Team
日期: 2026-03-01
"""

import sqlite3
from typing import List, Dict, Any, Optional
from pathlib import Path

from shared.utils import setup_logger

# 设置日志
logger = setup_logger(
    name="course-service",
    level="INFO",
    format_str="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

class CourseService:
    """课程服务类"""
    
    def __init__(self, db_path: str = "./data/smartcourse.db"):
        """初始化课程服务
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def list_courses(self, page: int = 1, page_size: int = 10, 
                    is_published: Optional[bool] = None,
                    search: Optional[str] = None) -> Dict[str, Any]:
        """列出课程
        
        Args:
            page: 页码
            page_size: 每页大小
            is_published: 是否已发布
            search: 搜索关键词
            
        Returns:
            Dict[str, Any]: 课程列表和分页信息
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 构建查询条件
            conditions = []
            params = []
            
            if is_published is not None:
                conditions.append("is_published = ?")
                params.append(1 if is_published else 0)
            
            if search:
                conditions.append("(title LIKE ? OR description LIKE ?)")
                params.extend([f"%{search}%", f"%{search}%"])
            
            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            
            # 查询总数
            count_query = f"SELECT COUNT(*) as total FROM courses {where_clause}"
            cursor.execute(count_query, params)
            total = cursor.fetchone()['total']
            
            # 查询课程数据
            offset = (page - 1) * page_size
            query = f"""
                SELECT c.*, 
                       GROUP_CONCAT(DISTINCT t.name) as tags,
                       COUNT(DISTINCT kp.id) as knowledge_point_count
                FROM courses c
                LEFT JOIN course_tags ct ON c.id = ct.course_id
                LEFT JOIN tags t ON ct.tag_id = t.id
                LEFT JOIN knowledge_points kp ON c.id = kp.course_id
                {where_clause}
                GROUP BY c.id
                ORDER BY c.created_at DESC
                LIMIT ? OFFSET ?
            """
            
            cursor.execute(query, params + [page_size, offset])
            rows = cursor.fetchall()
            
            # 转换为字典列表
            courses = []
            for row in rows:
                course = dict(row)
                # 处理标签字符串
                if course['tags']:
                    course['tags'] = list(set(course['tags'].split(',')))
                else:
                    course['tags'] = []
                courses.append(course)
            
            conn.close()
            
            return {
                "courses": courses,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "total_pages": (total + page_size - 1) // page_size
                }
            }
            
        except Exception as e:
            logger.error(f"列出课程失败: {e}")
            raise
    
    def get_course(self, course_id: int) -> Optional[Dict[str, Any]]:
        """获取课程详情
        
        Args:
            course_id: 课程ID
            
        Returns:
            Optional[Dict[str, Any]]: 课程详情，如果不存在返回None
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 查询课程基本信息
            query = """
                SELECT c.*, 
                       GROUP_CONCAT(DISTINCT t.name) as tags,
                       GROUP_CONCAT(DISTINCT t.id) as tag_ids,
                       COUNT(DISTINCT kp.id) as knowledge_point_count
                FROM courses c
                LEFT JOIN course_tags ct ON c.id = ct.course_id
                LEFT JOIN tags t ON ct.tag_id = t.id
                LEFT JOIN knowledge_points kp ON c.id = kp.course_id
                WHERE c.id = ?
                GROUP BY c.id
            """
            
            cursor.execute(query, (course_id,))
            row = cursor.fetchone()
            
            if not row:
                conn.close()
                return None
            
            course = dict(row)
            
            # 处理标签
            if course['tags']:
                course['tags'] = list(set(course['tags'].split(',')))
                course['tag_ids'] = list(set(map(int, course['tag_ids'].split(','))))
            else:
                course['tags'] = []
                course['tag_ids'] = []
            
            # 查询知识点
            kp_query = """
                SELECT id, name, description, category, importance, 
                       confidence, start_time, end_time, created_at
                FROM knowledge_points
                WHERE course_id = ?
                ORDER BY start_time
            """
            
            cursor.execute(kp_query, (course_id,))
            knowledge_points = [dict(row) for row in cursor.fetchall()]
            course['knowledge_points'] = knowledge_points
            
            conn.close()
            return course
            
        except Exception as e:
            logger.error(f"获取课程详情失败: {e}")
            raise
    
    def create_course(self, course_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建课程
        
        Args:
            course_data: 课程数据
            
        Returns:
            Dict[str, Any]: 创建的课程信息
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 提取标签数据
            tags = course_data.pop('tags', [])
            
            # 插入课程
            columns = []
            placeholders = []
            values = []
            
            for key, value in course_data.items():
                if value is not None:
                    columns.append(key)
                    placeholders.append('?')
                    values.append(value)
            
            query = f"""
                INSERT INTO courses ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
            """
            
            cursor.execute(query, values)
            course_id = cursor.lastrowid
            
            # 处理标签
            if tags:
                for tag_name in tags:
                    # 检查标签是否存在
                    cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
                    tag_row = cursor.fetchone()
                    
                    if tag_row:
                        tag_id = tag_row['id']
                    else:
                        # 创建新标签
                        cursor.execute(
                            "INSERT INTO tags (name, type) VALUES (?, ?)",
                            (tag_name, 'custom')
                        )
                        tag_id = cursor.lastrowid
                    
                    # 关联课程和标签
                    cursor.execute(
                        "INSERT OR IGNORE INTO course_tags (course_id, tag_id) VALUES (?, ?)",
                        (course_id, tag_id)
                    )
            
            conn.commit()
            conn.close()
            
            # 返回创建的课程
            return self.get_course(course_id)
            
        except Exception as e:
            logger.error(f"创建课程失败: {e}")
            raise
    
    def update_course(self, course_id: int, course_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """更新课程
        
        Args:
            course_id: 课程ID
            course_data: 更新的课程数据
            
        Returns:
            Optional[Dict[str, Any]]: 更新后的课程信息，如果课程不存在返回None
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 检查课程是否存在
            cursor.execute("SELECT id FROM courses WHERE id = ?", (course_id,))
            if not cursor.fetchone():
                conn.close()
                return None
            
            # 提取标签数据
            tags = course_data.pop('tags', None)
            
            # 更新课程基本信息
            if course_data:
                set_clause = ', '.join([f"{key} = ?" for key in course_data.keys()])
                values = list(course_data.values())
                values.append(course_id)
                
                query = f"UPDATE courses SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
                cursor.execute(query, values)
            
            # 处理标签更新
            if tags is not None:
                # 删除现有标签关联
                cursor.execute("DELETE FROM course_tags WHERE course_id = ?", (course_id,))
                
                # 添加新标签关联
                for tag_name in tags:
                    # 检查标签是否存在
                    cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
                    tag_row = cursor.fetchone()
                    
                    if tag_row:
                        tag_id = tag_row['id']
                    else:
                        # 创建新标签
                        cursor.execute(
                            "INSERT INTO tags (name, type) VALUES (?, ?)",
                            (tag_name, 'custom')
                        )
                        tag_id = cursor.lastrowid
                    
                    # 关联课程和标签
                    cursor.execute(
                        "INSERT INTO course_tags (course_id, tag_id) VALUES (?, ?)",
                        (course_id, tag_id)
                    )
            
            conn.commit()
            conn.close()
            
            # 返回更新后的课程
            return self.get_course(course_id)
            
        except Exception as e:
            logger.error(f"更新课程失败: {e}")
            raise
    
    def delete_course(self, course_id: int) -> bool:
        """删除课程
        
        Args:
            course_id: 课程ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 检查课程是否存在
            cursor.execute("SELECT id FROM courses WHERE id = ?", (course_id,))
            if not cursor.fetchone():
                conn.close()
                return False
            
            # 删除课程（级联删除会处理关联数据）
            cursor.execute("DELETE FROM courses WHERE id = ?", (course_id,))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"删除课程失败: {e}")
            raise
    
    def search_courses(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """搜索课程
        
        Args:
            query: 搜索关键词
            limit: 返回结果数量限制
            
        Returns:
            List[Dict[str, Any]]: 搜索结果
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            search_query = """
                SELECT c.*, 
                       GROUP_CONCAT(DISTINCT t.name) as tags,
                       COUNT(DISTINCT kp.id) as knowledge_point_count
                FROM courses c
                LEFT JOIN course_tags ct ON c.id = ct.course_id
                LEFT JOIN tags t ON ct.tag_id = t.id
                LEFT JOIN knowledge_points kp ON c.id = kp.course_id
                WHERE c.title LIKE ? OR c.description LIKE ? OR t.name LIKE ?
                GROUP BY c.id
                ORDER BY c.created_at DESC
                LIMIT ?
            """
            
            search_pattern = f"%{query}%"
            cursor.execute(search_query, (search_pattern, search_pattern, search_pattern, limit))
            rows = cursor.fetchall()
            
            # 转换为字典列表
            courses = []
            for row in rows:
                course = dict(row)
                # 处理标签字符串
                if course['tags']:
                    course['tags'] = list(set(course['tags'].split(',')))
                else:
                    course['tags'] = []
                courses.append(course)
            
            conn.close()
            return courses
            
        except Exception as e:
            logger.error(f"搜索课程失败: {e}")
            raise


# 全局服务实例
course_service = CourseService()

if __name__ == "__main__":
    # 测试课程服务
    service = CourseService()
    
    # 测试列出课程
    print("测试列出课程...")
    result = service.list_courses(page=1, page_size=5)
    print(f"找到 {len(result['courses'])} 个课程")
    
    # 测试获取课程详情
    if result['courses']:
        course_id = result['courses'][0]['id']
        print(f"\n测试获取课程详情 (ID: {course_id})...")
        course = service.get_course(course_id)
        if course:
            print(f"课程标题: {course['title']}")
            print(f"知识点数量: {len(course.get('knowledge_points', []))}")
    
    # 测试搜索课程
    print("\n测试搜索课程...")
    search_results = service.search_courses("Python", limit=5)
    print(f"搜索到 {len(search_results)} 个相关课程")