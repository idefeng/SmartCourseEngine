#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频服务
========

提供视频相关的业务逻辑。

作者: SmartCourseEngine Team
日期: 2026-03-03
"""

import sqlite3
from typing import List, Dict, Any, Optional
from pathlib import Path

from shared.utils import setup_logger

# 设置日志
logger = setup_logger(
    name="video-service",
    level="INFO",
    format_str="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

class VideoService:
    """视频服务类"""
    
    def __init__(self, db_path: str = "./data/smartcourse.db"):
        """初始化视频服务
        
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
    
    def list_videos(self, page: int = 1, page_size: int = 10, 
                    search: Optional[str] = None) -> Dict[str, Any]:
        """列出视频
        
        Args:
            page: 页码
            page_size: 每页大小
            search: 搜索关键词
            
        Returns:
            Dict[str, Any]: 视频列表和分页信息
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 构建查询条件
            conditions = ["type = 'video'"]
            params = []
            
            if search and search.strip():
                conditions.append("(title LIKE ? OR description LIKE ?)")
                search_term = f"%{search.strip()}%"
                params.extend([search_term, search_term])
            
            where_clause = f"WHERE {' AND '.join(conditions)}"
            
            # 查询总数
            count_query = f"SELECT COUNT(*) as total FROM courses {where_clause}"
            cursor.execute(count_query, params)
            total = cursor.fetchone()['total']
            
            # 查询视频数据
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
            videos = []
            for row in rows:
                video = dict(row)
                if video['tags']:
                    video['tags'] = video['tags'].split(',')
                else:
                    video['tags'] = []
                videos.append(video)
                
            return {
                "items": videos,
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": (total + page_size - 1) // page_size
            }
            
        except Exception as e:
            logger.error(f"查询视频列表失败: {e}")
            raise e
        finally:
            if conn:
                conn.close()

    def get_video(self, video_id: int) -> Optional[Dict[str, Any]]:
        """获取视频详情
        
        Args:
            video_id: 视频ID
            
        Returns:
            Optional[Dict[str, Any]]: 视频详情，如果不存在返回None
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 查询视频基本信息
            query = """
                SELECT c.*, 
                       GROUP_CONCAT(DISTINCT t.name) as tags,
                       COUNT(DISTINCT kp.id) as knowledge_point_count
                FROM courses c
                LEFT JOIN course_tags ct ON c.id = ct.course_id
                LEFT JOIN tags t ON ct.tag_id = t.id
                LEFT JOIN knowledge_points kp ON c.id = kp.course_id
                WHERE c.id = ? AND c.type = 'video'
                GROUP BY c.id
            """
            
            cursor.execute(query, (video_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            video = dict(row)
            if video['tags']:
                video['tags'] = video['tags'].split(',')
            else:
                video['tags'] = []
                
            return video
            
        except Exception as e:
            logger.error(f"获取视频详情失败: {e}")
            raise e
        finally:
            if conn:
                conn.close()

    def delete_video(self, video_id: int) -> bool:
        """删除视频
        
        Args:
            video_id: 视频ID
            
        Returns:
            bool: 是否删除成功
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM courses WHERE id = ? AND type = 'video'", (video_id,))
            conn.commit()
            
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"删除视频失败: {e}")
            raise e
        finally:
            if conn:
                conn.close()

# 单例实例
video_service = VideoService()
