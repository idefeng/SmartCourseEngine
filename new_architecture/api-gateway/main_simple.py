#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版API网关
============

SmartCourseEngine的简化API网关，用于快速验证基础架构。

作者: SmartCourseEngine Team
日期: 2026-03-01
"""

import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# ============================================================================
# 数据库连接
# ============================================================================

class Database:
    """数据库连接管理"""
    
    def __init__(self, db_path: str = "../data/smartcourse.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

# ============================================================================
# 课程服务
# ============================================================================

class CourseService:
    """课程服务"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def list_courses(self, page: int = 1, page_size: int = 10, 
                    is_published: Optional[bool] = None,
                    search: Optional[str] = None) -> Dict[str, Any]:
        """列出课程"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
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
            
            return {
                "courses": courses,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "total_pages": (total + page_size - 1) // page_size
                }
            }
            
        finally:
            conn.close()
    
    def get_course(self, course_id: int) -> Optional[Dict[str, Any]]:
        """获取课程详情"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
            # 查询课程基本信息
            query = """
                SELECT c.*, 
                       GROUP_CONCAT(DISTINCT t.name) as tags,
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
                return None
            
            course = dict(row)
            
            # 处理标签
            if course['tags']:
                course['tags'] = list(set(course['tags'].split(',')))
            else:
                course['tags'] = []
            
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
            
            return course
            
        finally:
            conn.close()
    
    def search_courses(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """搜索课程"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
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
            
            return courses
            
        finally:
            conn.close()

# ============================================================================
# FastAPI应用
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    print("🚀 启动 SmartCourseEngine API 网关")
    
    # 检查数据库
    db_path = Path("./data/smartcourse.db")
    if not db_path.exists():
        print("⚠️  数据库文件不存在，请先运行数据库初始化")
    
    yield
    
    # 关闭时
    print("👋 关闭 SmartCourseEngine API 网关")

# 创建FastAPI应用
app = FastAPI(
    title="SmartCourseEngine API Gateway",
    version="1.0.0",
    description="SmartCourseEngine的API网关服务",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# 依赖注入
# ============================================================================

def get_db():
    """获取数据库实例"""
    return Database()

def get_course_service():
    """获取课程服务实例"""
    db = get_db()
    return CourseService(db)

# ============================================================================
# 路由
# ============================================================================

@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "SmartCourseEngine API Gateway",
        "version": "1.0.0",
        "status": "running",
        "documentation": "/docs"
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    db_path = Path("../data/smartcourse.db")
    
    return {
        "status": "healthy" if db_path.exists() else "degraded",
        "service": "api-gateway",
        "timestamp": datetime.now().isoformat(),
        "database": {
            "exists": db_path.exists(),
            "path": str(db_path.absolute())
        }
    }

@app.get("/api/v1/courses")
async def list_courses(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页大小"),
    is_published: Optional[bool] = Query(None, description="是否已发布"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    course_service: CourseService = Depends(get_course_service)
):
    """列出课程"""
    try:
        result = course_service.list_courses(
            page=page,
            page_size=page_size,
            is_published=is_published,
            search=search
        )
        
        return {
            "success": True,
            "message": "获取课程列表成功",
            "data": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取课程列表失败: {str(e)}"
        )

@app.get("/api/v1/courses/search")
async def search_courses(
    query: str = Query(..., description="搜索关键词"),
    limit: int = Query(10, ge=1, le=100, description="结果数量限制"),
    course_service: CourseService = Depends(get_course_service)
):
    """搜索课程"""
    try:
        results = course_service.search_courses(query, limit)
        
        return {
            "success": True,
            "message": "搜索成功",
            "data": {
                "query": query,
                "results": results,
                "total": len(results)
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜索课程失败: {str(e)}"
        )

@app.get("/api/v1/courses/{course_id}")
async def get_course(
    course_id: int,
    course_service: CourseService = Depends(get_course_service)
):
    """获取课程详情"""
    try:
        course = course_service.get_course(course_id)
        
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="课程不存在"
            )
        
        return {
            "success": True,
            "message": "获取课程详情成功",
            "data": course
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取课程详情失败: {str(e)}"
        )

# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数"""
    print("=" * 60)
    print("SmartCourseEngine 简化API网关")
    print("=" * 60)
    
    # 检查数据库
    db_path = Path("../data/smartcourse.db")
    if not db_path.exists():
        print("⚠️  警告: 数据库文件不存在")
        print("请先运行数据库初始化脚本:")
        print("  cd /Users/idefeng/.openclaw/workspace/SmartCourseEngine/new_architecture")
        print("  python init_simple.py")
        print()
    
    print("服务信息:")
    print(f"  名称: SmartCourseEngine API Gateway")
    print(f"  版本: 1.0.0")
    print(f"  端口: 8000")
    print(f"  文档: http://localhost:8000/docs")
    print(f"  健康检查: http://localhost:8000/health")
    print()
    print("API端点:")
    print(f"  课程列表: GET /api/v1/courses")
    print(f"  课程详情: GET /api/v1/courses/{{id}}")
    print(f"  课程搜索: GET /api/v1/courses/search?query=Python")
    print()
    print("=" * 60)
    
    # 启动服务
    uvicorn.run(
        "main_simple:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False
    )

if __name__ == "__main__":
    main()