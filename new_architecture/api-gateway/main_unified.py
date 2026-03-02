#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一API网关
==========

使用统一API响应格式的API网关服务。

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

# 添加共享模块路径
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))

try:
    from shared.api_response import (
        ApiResponse,
        PaginatedResponse,
        ApiException,
        NotFoundException,
        ValidationException,
        PermissionDeniedException,
        ErrorCode,
        setup_exception_handlers,
        create_api_response,
        success_response,
        error_response,
        create_paginated_response,
    )
except ImportError:
    # 如果导入失败，创建简化版本
    class ErrorCode:
        UNKNOWN_ERROR = ("0000", "未知错误")
        VALIDATION_ERROR = ("0001", "参数验证失败")
        DATABASE_ERROR = ("0002", "数据库错误")
        RESOURCE_NOT_FOUND = ("0005", "资源不存在")
        SEARCH_FAILED = ("5001", "搜索失败")
    
    def success_response(data: Any = None, message: str = "成功") -> Dict[str, Any]:
        return {
            "success": True,
            "message": message,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
    
    def error_response(error_code: ErrorCode, message: str = None, details: Dict[str, Any] = None) -> Dict[str, Any]:
        return {
            "success": False,
            "message": message or error_code[1],
            "error_code": error_code[0],
            "error_message": error_code[1],
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }
    
    def create_paginated_response(items: List, total: int, page: int, page_size: int) -> Dict[str, Any]:
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }

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
                "items": courses,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }
            
        except Exception as e:
            raise Exception(f"数据库查询失败: {str(e)}")
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
            
        except Exception as e:
            raise Exception(f"数据库查询失败: {str(e)}")
        finally:
            conn.close()
    
    def search_courses(self, query: str, page: int = 1, page_size: int = 10) -> Dict[str, Any]:
        """搜索课程"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
            # 构建搜索条件
            search_pattern = f"%{query}%"
            
            # 查询总数
            count_query = """
                SELECT COUNT(DISTINCT c.id) as total
                FROM courses c
                LEFT JOIN course_tags ct ON c.id = ct.course_id
                LEFT JOIN tags t ON ct.tag_id = t.id
                WHERE c.title LIKE ? OR c.description LIKE ? OR t.name LIKE ?
            """
            
            cursor.execute(count_query, (search_pattern, search_pattern, search_pattern))
            total = cursor.fetchone()['total']
            
            # 查询课程数据
            offset = (page - 1) * page_size
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
                LIMIT ? OFFSET ?
            """
            
            cursor.execute(search_query, (search_pattern, search_pattern, search_pattern, page_size, offset))
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
                "items": courses,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size,
                "query": query
            }
            
        except Exception as e:
            raise Exception(f"数据库查询失败: {str(e)}")
        finally:
            conn.close()

# ============================================================================
# FastAPI应用
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    print("🚀 启动 SmartCourseEngine 统一API网关")
    
    # 检查数据库
    db_path = Path("../data/smartcourse.db")
    if not db_path.exists():
        print("⚠️  数据库文件不存在，请先运行数据库初始化")
    
    yield
    
    # 关闭时
    print("👋 关闭 SmartCourseEngine 统一API网关")

# 创建FastAPI应用
app = FastAPI(
    title="SmartCourseEngine Unified API Gateway",
    version="1.0.0",
    description="使用统一API响应格式的SmartCourseEngine API网关服务",
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
# 导入认证路由
# ============================================================================

try:
    from auth_routes import router as auth_router
    app.include_router(auth_router)
    AUTH_ENABLED = True
except ImportError:
    print("⚠️  认证路由导入失败，认证功能将不可用")
    AUTH_ENABLED = False

# ============================================================================
# 导入WebSocket路由
# ============================================================================

try:
    from shared.websocket import router as websocket_router
    app.include_router(websocket_router)
    WEBSOCKET_ENABLED = True
except ImportError as e:
    print(f"⚠️  WebSocket路由导入失败: {e}")
    WEBSOCKET_ENABLED = False

# ============================================================================
# 导入文件上传路由
# ============================================================================

try:
    from shared.file_upload import upload_router
    app.include_router(upload_router)
    FILE_UPLOAD_ENABLED = True
except ImportError as e:
    print(f"⚠️  文件上传路由导入失败: {e}")
    FILE_UPLOAD_ENABLED = False

# ============================================================================
# 路由
# ============================================================================

@app.get("/")
async def root():
    """根路径"""
    endpoints = {
        "health": "/health",
        "courses": "/api/v1/courses",
        "course_detail": "/api/v1/courses/{id}",
        "course_search": "/api/v1/courses/search"
    }
    
    if AUTH_ENABLED:
        endpoints.update({
            "auth_register": "/api/v1/auth/register",
            "auth_login": "/api/v1/auth/login",
            "auth_refresh": "/api/v1/auth/refresh",
            "auth_me": "/api/v1/auth/me",
            "auth_users": "/api/v1/auth/users"
        })
    
    if WEBSOCKET_ENABLED:
        endpoints.update({
            "websocket": "/ws",
            "websocket_online_users": "/ws/online-users",
            "websocket_user_tasks": "/ws/user-tasks/{user_id}"
        })
    
    if FILE_UPLOAD_ENABLED:
        endpoints.update({
            "upload_init": "/api/v1/upload/init",
            "upload_chunk": "/api/v1/upload/chunk/{upload_id}/{chunk_index}",
            "upload_complete": "/api/v1/upload/complete/{upload_id}",
            "upload_cancel": "/api/v1/upload/cancel/{upload_id}",
            "upload_status": "/api/v1/upload/status/{upload_id}",
            "user_uploads": "/api/v1/upload/user/{user_id}"
        })
    
    return success_response(
        data={
            "service": "SmartCourseEngine Unified API Gateway",
            "version": "1.0.0",
            "status": "running",
            "authentication": "enabled" if AUTH_ENABLED else "disabled",
            "websocket": "enabled" if WEBSOCKET_ENABLED else "disabled",
            "file_upload": "enabled" if FILE_UPLOAD_ENABLED else "disabled",
            "documentation": "/docs",
            "endpoints": endpoints
        },
        message="统一API网关服务运行正常"
    )

@app.get("/health")
async def health_check():
    """健康检查"""
    db_path = Path("../data/smartcourse.db")
    
    return success_response(
        data={
            "status": "healthy" if db_path.exists() else "degraded",
            "service": "unified-api-gateway",
            "timestamp": datetime.now().isoformat(),
            "database": {
                "exists": db_path.exists(),
                "path": str(db_path.absolute())
            }
        },
        message="服务健康检查完成"
    )

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
        
        return success_response(
            data=result,
            message="获取课程列表成功"
        )
    except Exception as e:
        return error_response(
            error_code=ErrorCode.DATABASE_ERROR,
            message="获取课程列表失败",
            details={"error": str(e)}
        )

@app.get("/api/v1/courses/search")
async def search_courses(
    query: str = Query(..., description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页大小"),
    course_service: CourseService = Depends(get_course_service)
):
    """搜索课程"""
    try:
        if not query or len(query.strip()) == 0:
            return error_response(
                error_code=ErrorCode.VALIDATION_ERROR,
                message="搜索关键词不能为空"
            )
        
        result = course_service.search_courses(query, page=page, page_size=page_size)
        
        return success_response(
            data=result,
            message="搜索成功"
        )
    except Exception as e:
        return error_response(
            error_code=ErrorCode.SEARCH_FAILED,
            message="搜索课程失败",
            details={"error": str(e)}
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
            return error_response(
                error_code=ErrorCode.RESOURCE_NOT_FOUND,
                message="课程不存在",
                details={"course_id": course_id}
            )
        
        return success_response(
            data=course,
            message="获取课程详情成功"
        )
    except Exception as e:
        return error_response(
            error_code=ErrorCode.DATABASE_ERROR,
            message="获取课程详情失败",
            details={"error": str(e)}
        )

# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数"""
    print("=" * 60)
    print("SmartCourseEngine 统一API网关")
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
    print(f"  名称: SmartCourseEngine Unified API Gateway")
    print(f"  版本: 1.0.0")
    print(f"  端口: 8001")
    print(f"  文档: http://localhost:8001/docs")
    print(f"  健康检查: http://localhost:8001/health")
    print()
    print("API端点:")
    print(f"  课程列表: GET /api/v1/courses")
    print(f"  课程详情: GET /api/v1/courses/{{id}}")
    print(f"  课程搜索: GET /api/v1/courses/search?query=Python")
    print()
    print("响应格式:")
    print(f"  成功: {{'success': true, 'message': '...', 'data': {{...}}}}")
    print(f"  失败: {{'success': false, 'message': '...', 'error_code': '...'}}")
    print()
    print("=" * 60)
    
    # 启动服务
    uvicorn.run(
        "main_unified:app",
        host="0.0.0.0",
        port=8001,
        log_level="info",
        reload=False
    )

if __name__ == "__main__":
    main()