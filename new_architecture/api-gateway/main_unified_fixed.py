#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一API网关 - 修复版本
==========

使用统一API响应格式的API网关服务。

作者: SmartCourseEngine Team
日期: 2026-03-02
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
# 修复Python路径
# ============================================================================

# 获取项目根目录
project_root = Path(__file__).parent.parent
shared_path = project_root / "shared"
api_gateway_path = project_root / "api-gateway"

# 添加路径到sys.path
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(shared_path))
sys.path.insert(0, str(api_gateway_path))

print(f"项目根目录: {project_root}")
print(f"共享模块路径: {shared_path}")
print(f"API网关路径: {api_gateway_path}")

# ============================================================================
# 导入共享模块
# ============================================================================

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
    API_RESPONSE_ENABLED = True
    print("✅ API响应模块导入成功")
except ImportError as e:
    print(f"⚠️  API响应模块导入失败: {e}")
    API_RESPONSE_ENABLED = False
    
    # 创建简化版本
    class ErrorCode:
        UNKNOWN_ERROR = ("0000", "未知错误")
        VALIDATION_ERROR = ("0001", "参数验证失败")
        DATABASE_ERROR = ("0002", "数据库错误")
        RESOURCE_NOT_FOUND = ("0005", "资源不存在")
        SEARCH_FAILED = ("5001", "搜索失败")
    
    def success_response(data: Any = None, message: str = "操作成功"):
        return {
            "success": True,
            "message": message,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def error_response(
        error_code: ErrorCode,
        message: str = "操作失败",
        details: Dict[str, Any] = None
    ):
        return {
            "success": False,
            "message": message,
            "error_code": error_code[0],
            "error_message": error_code[1],
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat()
        }

# ============================================================================
# 数据库服务
# ============================================================================

class CourseService:
    """课程服务"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # 使用相对路径
            self.db_path = str(project_root / "data" / "smartcourse.db")
        else:
            self.db_path = db_path
    
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def list_courses(self, page: int = 1, page_size: int = 10):
        """获取课程列表"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 计算总数
            cursor.execute("SELECT COUNT(*) as total FROM courses")
            total = cursor.fetchone()["total"]
            
            # 查询课程数据
            offset = (page - 1) * page_size
            query = """
                SELECT c.*, 
                       GROUP_CONCAT(DISTINCT t.name) as tags,
                       COUNT(DISTINCT kp.id) as knowledge_point_count
                FROM courses c
                LEFT JOIN course_tags ct ON c.id = ct.course_id
                LEFT JOIN tags t ON ct.tag_id = t.id
                LEFT JOIN knowledge_points kp ON c.id = kp.course_id
                GROUP BY c.id
                ORDER BY c.created_at DESC
                LIMIT ? OFFSET ?
            """
            
            cursor.execute(query, (page_size, offset))
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
    
    def get_course(self, course_id: int):
        """获取课程详情"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 查询课程基本信息
            query = """
                SELECT c.*, 
                       GROUP_CONCAT(DISTINCT t.name) as tags
                FROM courses c
                LEFT JOIN course_tags ct ON c.id = ct.course_id
                LEFT JOIN tags t ON ct.tag_id = t.id
                WHERE c.id = ?
                GROUP BY c.id
            """
            
            cursor.execute(query, (course_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            course = dict(row)
            if course['tags']:
                course['tags'] = list(set(course['tags'].split(',')))
            else:
                course['tags'] = []
            
            # 查询知识点
            cursor.execute("""
                SELECT * FROM knowledge_points 
                WHERE course_id = ? 
                ORDER BY timestamp_seconds
            """, (course_id,))
            
            knowledge_points = [dict(row) for row in cursor.fetchall()]
            course['knowledge_points'] = knowledge_points
            
            return course
            
        except Exception as e:
            raise Exception(f"数据库查询失败: {str(e)}")
        finally:
            conn.close()
    
    def search_courses(self, query: str, page: int = 1, page_size: int = 10):
        """搜索课程"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            search_pattern = f"%{query}%"
            
            # 计算总数
            count_query = """
                SELECT COUNT(DISTINCT c.id) as total
                FROM courses c
                LEFT JOIN course_tags ct ON c.id = ct.course_id
                LEFT JOIN tags t ON ct.tag_id = t.id
                WHERE c.title LIKE ? OR c.description LIKE ? OR t.name LIKE ?
            """
            
            cursor.execute(count_query, (search_pattern, search_pattern, search_pattern))
            total = cursor.fetchone()["total"]
            
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

def get_course_service():
    """获取课程服务实例"""
    return CourseService()

# ============================================================================
# FastAPI应用
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    print("🚀 启动 SmartCourseEngine 统一API网关 (修复版本)")
    
    # 检查数据库
    db_path = project_root / "data" / "smartcourse.db"
    if not db_path.exists():
        print("⚠️  警告: 数据库文件不存在")
    
    yield
    
    # 关闭时
    print("👋 停止 SmartCourseEngine 统一API网关")

app = FastAPI(
    title="SmartCourseEngine Unified API Gateway",
    description="智能课程知识库统一API网关",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 设置异常处理器
if API_RESPONSE_ENABLED:
    setup_exception_handlers(app)

# ============================================================================
# 导入其他路由
# ============================================================================

AUTH_ENABLED = False
WEBSOCKET_ENABLED = False
FILE_UPLOAD_ENABLED = False

# 尝试导入认证路由
try:
    # 动态导入auth_routes
    auth_routes_path = api_gateway_path / "auth_routes.py"
    if auth_routes_path.exists():
        import importlib.util
        spec = importlib.util.spec_from_file_location("auth_routes", auth_routes_path)
        auth_routes = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(auth_routes)
        app.include_router(auth_routes.router)
        AUTH_ENABLED = True
        print("✅ 认证路由导入成功")
    else:
        print("⚠️  认证路由文件不存在")
except Exception as e:
    print(f"⚠️  认证路由导入失败: {e}")

# 尝试导入WebSocket路由
try:
    from shared.websocket import router as websocket_router
    app.include_router(websocket_router)
    WEBSOCKET_ENABLED = True
    print("✅ WebSocket路由导入成功")
except ImportError as e:
    print(f"⚠️  WebSocket路由导入失败: {e}")

# 尝试导入文件上传路由
try:
    from shared.file_upload import upload_router
    app.include_router(upload_router)
    FILE_UPLOAD_ENABLED = True
    print("✅ 文件上传路由导入成功")
except ImportError as e:
    print(f"⚠️  文件上传路由导入失败: {e}")

# ============================================================================
# 路由定义
# ============================================================================

@app.get("/health")
async def health_check():
    """健康检查"""
    db_path = project_root / "data" / "smartcourse.db"
    
    return success_response(
        data={
            "status": "healthy",
            "service": "unified-api-gateway",
            "timestamp": datetime.utcnow().isoformat(),
            "database": {
                "exists": db_path.exists(),
                "path": str(db_path)
            }
        },
        message="服务健康检查完成"
    )

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

@app.get("/api/v1/courses")
async def list_courses(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    course_service: CourseService = Depends(get_course_service)
):
    """获取课程列表"""
    try:
        result = course_service.list_courses(page, page_size)
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

@app.get("/api/v1/courses/search")
async def search_courses(
    query: str = Query(..., description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    course_service: CourseService = Depends(get_course_service)
):
    """搜索课程"""
    try:
        result = course_service.search_courses(query, page, page_size)
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

# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数"""
    print("=" * 60)
    print("SmartCourseEngine 统一API网关 (修复版本)")
    print("=" * 60)
    
    # 检查数据库
    db_path = project_root / "data" / "smartcourse.db"
    if not db_path.exists():
        print("⚠️  警告: 数据库文件不存在")
        print("请先运行数据库初始化脚本:")
        print(f"  cd {project_root}")
        print("  python init_simple.py")
    
    print("\n服务信息:")
    print(f"  名称: SmartCourseEngine Unified API Gateway")
    print(f"  版本: 1.0.0")
    print(f"  端口: 8001")
    print(f"  文档: http://localhost:8001/docs")
    print(f"  健康检查: http://localhost:8001/health")
    
    print("\nAPI端点:")
    print(f"  课程列表: GET /api/v1/courses")
    print(f"  课程详情: GET /api/v1/courses/{{id}}")
    print(f"  课程搜索: GET /api/v1/courses/search?query=Python")
    
    if AUTH_ENABLED:
        print("\n认证端点:")
        print(f"  用户注册: POST /api/v1/auth/register")
        print(f"  用户登录: POST /api/v1/auth/login")
        print(f"  用户信息: GET /api/v1/auth/me")
    
    if WEBSOCKET_ENABLED:
        print("\nWebSocket端点:")
        print(f"  WebSocket连接: ws://localhost:8001/ws")
        print(f"  在线用户: GET /ws/online-users")
    
    if FILE