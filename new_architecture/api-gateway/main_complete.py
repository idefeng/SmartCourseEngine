#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整API网关 - 集成所有微服务
==========

集成7个微服务的完整API网关：
1. api-gateway (自身): 8000
2. course-generator: 8001
3. video-analyzer: 8002
4. knowledge-extractor: 8003
5. search-engine: 8004
6. recommendation: 8005
7. notification: 8006

作者: SmartCourseEngine Team
日期: 2026-03-07
"""

import os
import sys
import json
import httpx
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status, Depends, Query, Body, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from pydantic import BaseModel, Field

# ============================================================================
# 配置和路径设置
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
        success_response,
        error_response,
        ErrorCode,
    )
    from shared.config import get_settings
    from shared.database import get_db, DatabaseManager
    from shared.models import Course, KnowledgePoint, User, VideoAnalysis
    from shared.auth import get_current_user, verify_token
    API_RESPONSE_ENABLED = True
    print("✅ 共享模块导入成功")
except ImportError as e:
    print(f"⚠️  共享模块导入失败: {e}")
    API_RESPONSE_ENABLED = False
    
    # 创建简化版本
    class ErrorCode:
        UNKNOWN_ERROR = ("0000", "未知错误")
        VALIDATION_ERROR = ("0001", "参数验证失败")
        DATABASE_ERROR = ("0002", "数据库错误")
        RESOURCE_NOT_FOUND = ("0005", "资源不存在")
        SERVICE_UNAVAILABLE = ("9001", "服务不可用")
    
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
# 微服务配置
# ============================================================================

# 微服务端点配置
MICROSERVICES = {
    "course_generator": {
        "name": "课件生成服务",
        "url": "http://course-generator:8001",
        "port": 8001,
        "health_endpoint": "/health"
    },
    "video_analyzer": {
        "name": "视频分析服务",
        "url": "http://video-analyzer:8002",
        "port": 8002,
        "health_endpoint": "/health"
    },
    "knowledge_extractor": {
        "name": "知识提取服务",
        "url": "http://knowledge-extractor:8003",
        "port": 8003,
        "health_endpoint": "/health"
    },
    "search_engine": {
        "name": "搜索服务",
        "url": "http://search-engine:8004",
        "port": 8004,
        "health_endpoint": "/health"
    },
    "recommendation": {
        "name": "推荐服务",
        "url": "http://recommendation:8005",
        "port": 8005,
        "health_endpoint": "/health"
    },
    "notification": {
        "name": "通知服务",
        "url": "http://notification:8006",
        "port": 8006,
        "health_endpoint": "/health"
    }
}

# ============================================================================
# 数据模型
# ============================================================================

# 课件生成相关
class CourseGenerationRequest(BaseModel):
    course_id: int
    template_id: Optional[int] = None
    format: str = "ppt"
    include_video_summary: bool = True
    include_knowledge_graph: bool = True
    include_exercises: bool = False
    custom_prompt: Optional[str] = None

# 视频分析相关
class VideoAnalysisRequest(BaseModel):
    video_url: str
    video_file: Optional[str] = None
    language: str = "zh"
    analyze_scenes: bool = True
    extract_keyframes: bool = True
    generate_summary: bool = True

# 知识提取相关
class KnowledgeExtractionRequest(BaseModel):
    text: str
    source_type: str = "video_transcript"  # video_transcript, document, article
    extract_entities: bool = True
    extract_relations: bool = True
    build_graph: bool = True

# 搜索相关
class SearchRequest(BaseModel):
    query: str
    search_type: str = "hybrid"  # text, vector, hybrid
    filters: Optional[Dict[str, Any]] = None
    limit: int = 20
    offset: int = 0

# 推荐相关
class RecommendationRequest(BaseModel):
    user_id: Optional[int] = None
    course_id: Optional[int] = None
    knowledge_point_id: Optional[int] = None
    strategy: str = "hybrid"
    limit: int = 10
    include_explanations: bool = True

# 通知相关
class NotificationRequest(BaseModel):
    user_id: Optional[int] = None
    user_ids: Optional[List[int]] = None
    channel: str = "in_app"
    type: str = "info"
    title: str
    content: str
    template_id: Optional[int] = None
    template_data: Optional[Dict[str, Any]] = None
    priority: str = "normal"
    scheduled_at: Optional[datetime] = None

# ============================================================================
# 服务客户端
# ============================================================================

class MicroserviceClient:
    """微服务客户端"""
    
    def __init__(self):
        self.clients = {}
        self.timeout = 30.0
        
    async def initialize(self):
        """初始化所有客户端"""
        print("🔗 初始化微服务客户端...")
        
        # 为每个微服务创建异步HTTP客户端
        for service_name, config in MICROSERVICES.items():
            try:
                client = httpx.AsyncClient(
                    base_url=config["url"],
                    timeout=self.timeout,
                    headers={"Content-Type": "application/json"}
                )
                self.clients[service_name] = client
                print(f"✅ 已连接: {config['name']} ({config['url']})")
            except Exception as e:
                print(f"⚠️  连接失败 {config['name']}: {e}")
        
        print(f"🔗 已初始化 {len(self.clients)} 个微服务客户端")
    
    async def close(self):
        """关闭所有客户端"""
        for client in self.clients.values():
            await client.aclose()
        print("🔗 已关闭所有微服务客户端")
    
    async def call_service(self, service_name: str, method: str, endpoint: str, 
                          data: Dict[str, Any] = None, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """调用微服务"""
        if service_name not in self.clients:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"服务 {service_name} 不可用"
            )
        
        client = self.clients[service_name]
        
        try:
            if method == "GET":
                response = await client.get(endpoint, params=params)
            elif method == "POST":
                response = await client.post(endpoint, json=data)
            elif method == "PUT":
                response = await client.put(endpoint, json=data)
            elif method == "DELETE":
                response = await client.delete(endpoint)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"服务 {service_name} 响应超时"
            )
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"服务 {service_name} 错误: {e.response.text}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"服务 {service_name} 调用失败: {str(e)}"
            )
    
    async def health_check_all(self) -> Dict[str, Any]:
        """检查所有微服务健康状态"""
        health_status = {}
        
        for service_name, config in MICROSERVICES.items():
            try:
                if service_name in self.clients:
                    response = await self.clients[service_name].get(config["health_endpoint"])
                    health_status[service_name] = {
                        "status": "healthy" if response.status_code == 200 else "unhealthy",
                        "response_time": response.elapsed.total_seconds(),
                        "details": response.json() if response.status_code == 200 else None
                    }
                else:
                    health_status[service_name] = {
                        "status": "disconnected",
                        "response_time": None,
                        "details": "客户端未初始化"
                    }
            except Exception as e:
                health_status[service_name] = {
                    "status": "error",
                    "response_time": None,
                    "details": str(e)
                }
        
        return health_status

# ============================================================================
# 生命周期管理
# ============================================================================

microservice_client = MicroserviceClient()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print(f"🚀 启动完整API网关，端口: 8000")
    
    # 启动时初始化
    await microservice_client.initialize()
    
    yield
    
    # 关闭时清理
    await microservice_client.close()
    print(f"👋 关闭API网关")

# ============================================================================
# FastAPI应用
# ============================================================================

app = FastAPI(
    title="SmartCourseEngine API网关",
    description="集成7个微服务的完整API网关",
    version="2.0.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# 健康检查和监控
# ============================================================================

@app.get("/health")
async def health_check():
    """健康检查"""
    services_health = await microservice_client.health_check_all()
    
    healthy_count = sum(1 for status in services_health.values() if status["status"] == "healthy")
    total_count = len(services_health)
    
    return success_response({
        "service": "api-gateway",
        "status": "healthy",
        "port": 8000,
        "timestamp": datetime.utcnow().isoformat(),
        "microservices": services_health,
        "summary": {
            "total": total_count,
            "healthy": healthy_count,
            "unhealthy": total_count - healthy_count
        }
    })

@app.get("/")
async def root():
    """根端点"""
    return success_response({
        "service": "SmartCourseEngine API网关",
        "description": "集成7个微服务的完整API网关",
        "version": "2.0.0",
        "microservices": [
            {"name": "课件生成服务", "port": 8001, "endpoint": "/api/v1/courses/generate"},
            {"name": "视频分析服务", "port": 8002, "endpoint": "/api/v1/videos/analyze"},
            {"name": "知识提取服务", "port": 8003, "endpoint": "/api/v1/knowledge/extract"},
            {"name": "搜索服务", "port": 8004, "endpoint": "/api/v1/search"},
            {"name": "推荐服务", "port": 8005, "endpoint": "/api/v1/recommendations"},
            {"name": "通知服务", "port": 8006, "endpoint": "/api/v1/notifications"}
        ],
        "endpoints": [
            "/health - 健康检查",
            "/docs - API文档",
            "/api/v1/courses - 课程管理",
            "/api/v1/videos - 视频管理",
            "/api/v1/knowledge - 知识管理",
            "/api/v1/search - 智能搜索",
            "/api/v1/recommendations - 个性化推荐",
            "/api/v1/notifications - 通知管理"
        ]
    })

# ============================================================================
# 课程管理API
# ============================================================================

@app.get("/api/v1/courses")
async def list_courses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    category: Optional[str] = None
):
    """列出课程"""
    # 这里应该查询数据库
    # 暂时返回模拟数据
    
    courses = [
        {
            "id": 1,
            "title": "Python编程入门",
            "description": "学习Python基础语法和编程思维",
            "category": "编程",
            "difficulty": "beginner",
            "duration": 120,
            "created_at": datetime.utcnow().isoformat()
        },
        {
            "id": 2,
            "title": "机器学习实战",
            "description": "从零开始学习机器学习算法",
            "category": "AI",
            "difficulty": "intermediate",
            "duration": 180,
            "created_at": datetime.utcnow().isoformat()
        }
    ]
    
    return success_response({
        "courses": courses,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": len(courses),
            "total_pages": 1
        }
    }, "课程列表获取成功")

@app.post("/api/v1/courses")
async def create_course(course_data: Dict[str, Any]):
    """创建课程"""
    # 这里应该保存到数据库
    # 暂时返回模拟数据
    
    course_id = 3  # 模拟ID
    
    return success_response({
        "id": course_id,
        **course_data,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }, "课程创建成功")

@app.get("/api/v1/courses/{course_id}")
async def get_course(course_id: int):
    """获取课程详情"""
    # 这里应该查询数据库
    # 暂时返回模拟数据
    
    course = {
        "id": course_id,
        "title": f"课程 {course_id}",
        "description": f"这是课程 {course_id} 的详细描述",
        "category": "编程",
        "difficulty": "beginner",
        "duration": 120,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    
    return success_response(course, "课程详情获取成功")

# ============================================================================
# 课件生成API
# ============================================================================

@app.post("/api/v1/courses/{course_id}/generate")
async def generate_course_materials(
    course_id: int,
    request: CourseGenerationRequest,
    background_tasks: BackgroundTasks
):
    """生成课件"""
    try:
        # 调用课件生成服务
        result = await microservice_client.call_service(
            "course_generator",
            "POST",
            "/generate",
            data={
                "course_id": course_id,
                **request.dict(exclude_none=True)
            }
        )
        
        return success_response(result, "课件生成任务已提交")
        
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(ErrorCode.SERVICE_UNAVAILABLE, f"课件生成失败: {str(e)}")

@app.get("/api/v1/courses/{course_id}/generations")
async def get_course_generations(course_id: int):
    """获取课程的生成记录"""
    try:
        # 调用课件生成服务
        result = await microservice_client.call_service(
            "course_generator",
            "GET",
            f"/courses/{course_id}/generations"
        )
        
        return success_response(result, "生成记录获取成功")
        
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(ErrorCode.SERVICE_UNAVAILABLE, f"获取生成记录失败: {str(e)}")

# ============================================================================
# 视频分析API
# ============================================================================

@app.post("/api/v1/videos/analyze")
async def analyze_video(
    request: VideoAnalysisRequest,
    background_tasks: BackgroundTasks
):
    """分析视频"""
    try:
        # 调用视频分析服务
        result = await microservice_client.call_service(
            "video_analyzer",
            "POST",
            "/analyze",
            data=request.dict(exclude_none=True)
        )
        
        return success_response(result, "视频分析任务已提交")
        
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(ErrorCode.SERVICE_UNAVAILABLE, f"视频分析失败: {str(e)}")

@app.get("/api/v1/videos/analyses/{analysis_id}")
async def get_video_analysis(analysis_id: str):
    """获取视频分析结果"""
    try:
        # 调用视频分析服务
        result = await microservice_client.call_service(
            "video_analyzer",
            "GET",
            f"/analyses/{analysis_id}"
        )
        
        return success_response(result, "视频分析结果获取成功")
        
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(ErrorCode.SERVICE_UNAVAILABLE, f"获取分析结果失败: {str(e)}")

# ============================================================================
# 知识管理API
# ============================================================================

@app.post("/api/v1/knowledge/extract")
async def extract_knowledge(request: KnowledgeExtractionRequest):
    """提取知识"""
    try:
        # 调用知识提取服务
        result = await microservice_client.call_service(
            "knowledge_extractor",
            "POST",
            "/extract",
            data=request.dict(exclude_none=True)
        )
        
        return success_response(result, "知识提取成功")
        
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(ErrorCode.SERVICE_UNAVAILABLE, f"知识提取失败: {str(e)}")

@app.get("/api/v1/knowledge/graph")
async def get_knowledge_graph(
    root_id: Optional[int] = None,
    depth: int = Query(2, ge=1, le=5)
):
    """获取知识图谱"""
    try:
        # 调用知识提取服务
        params = {"depth": depth}
        if root_id:
            params["root_id"] = root_id
            
        result = await microservice_client.call_service(
            "knowledge_extractor",
            "GET",
            "/graph",
            params=params
        )
        
        return success_response(result, "知识图谱获取成功")
        
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(ErrorCode.SERVICE_UNAVAILABLE, f"获取知识图谱失败: {str(e)}")

# ============================================================================
# 搜索API
# ============================================================================

@app.post("/api/v1/search")
async def search(request: SearchRequest):
    """智能搜索"""
    try:
        # 调用搜索服务
        result = await microservice_client.call_service(
            "search_engine",
            "POST",
            "/search",
            data=request.dict(exclude_none=True)
        )
        
        return success_response(result, "搜索成功")
        
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(ErrorCode.SERVICE_UNAVAILABLE, f"搜索失败: {str(e)}")

@app.get("/api/v1/search/suggestions")
async def get_search_suggestions(
    query: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=20)
):
    """获取搜索建议"""
    try:
        # 调用搜索服务
        result = await microservice_client.call_service(
            "search_engine",
            "GET",
            "/suggestions",
            params={"query": query, "limit": limit}
        )
        
        return success_response(result, "搜索建议获取成功")
        
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(ErrorCode.SERVICE_UNAVAILABLE, f"获取搜索建议失败: {str(e)}")

# ============================================================================
# 推荐API
# ============================================================================

@app.post("/api/v1/recommendations")
async def get_recommendations(request: RecommendationRequest):
    """获取推荐"""
    try:
        # 调用推荐服务
        result = await microservice_client.call_service(
            "recommendation",
            "POST",
            "/recommend",
            data=request.dict(exclude_none=True)
        )
        
        return success_response(result, "推荐获取成功")
        
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(ErrorCode.SERVICE_UNAVAILABLE, f"获取推荐失败: {str(e)}")

@app.get("/api/v1/users/{user_id}/recommendations")
async def get_user_recommendations(
    user_id: int,
    strategy: str = Query("hybrid"),
    limit: int = Query(10, ge=1, le=50)
):
    """获取用户的推荐"""
    try:
        # 调用推荐服务
        result = await microservice_client.call_service(
            "recommendation",
            "GET",
            f"/users/{user_id}/recommendations",
            params={"strategy": strategy, "limit": limit}
        )
        
        return success_response(result, "用户推荐获取成功")
        
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(ErrorCode.SERVICE_UNAVAILABLE, f"获取用户推荐失败: {str(e)}")

@app.get("/api/v1/courses/{course_id}/related")
async def get_related_courses(
    course_id: int,
    limit: int = Query(5, ge=1, le=20)
):
    """获取相关课程"""
    try:
        # 调用推荐服务
        result = await microservice_client.call_service(
            "recommendation",
            "GET",
            f"/courses/{course_id}/related",
            params={"limit": limit}
        )
        
        return success_response(result, "相关课程获取成功")
        
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(ErrorCode.SERVICE_UNAVAILABLE, f"获取相关课程失败: {str(e)}")

# ============================================================================
# 通知API
# ============================================================================

@app.post("/api/v1/notifications")
async def send_notification(
    request: NotificationRequest,
    background_tasks: BackgroundTasks
):
    """发送通知"""
    try:
        # 调用通知服务
        result = await microservice_client.call_service(
            "notification",
            "POST",
            "/send",
            data=request.dict(exclude_none=True)
        )
        
        return success_response(result, "通知发送成功")
        
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(ErrorCode.SERVICE_UNAVAILABLE, f"发送通知失败: {str(e)}")

@app.post("/api/v1/notifications/email")
async def send_email_notification(email_request: Dict[str, Any]):
    """发送邮件通知"""
    try:
        # 调用通知服务
        result = await microservice_client.call_service(
            "notification",
            "POST",
            "/email",
            data=email_request
        )
        
        return success_response(result, "邮件发送成功")
        
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(ErrorCode.SERVICE_UNAVAILABLE, f"发送邮件失败: {str(e)}")

@app.get("/api/v1/users/{user_id}/notifications")
async def get_user_notifications(
    user_id: int,
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    channel: Optional[str] = Query(None)
):
    """获取用户的通知"""
    try:
        # 调用通知服务
        params = {"limit": limit, "unread_only": unread_only}
        if channel:
            params["channel"] = channel
            
        result = await microservice_client.call_service(
            "notification",
            "GET",
            f"/users/{user_id}/notifications",
            params=params
        )
        
        return success_response(result, "用户通知获取成功")
        
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(ErrorCode.SERVICE_UNAVAILABLE, f"获取用户通知失败: {str(e)}")

@app.post("/api/v1/users/{user_id}/notifications/{notification_id}/read")
async def mark_notification_as_read(user_id: int, notification_id: int):
    """标记通知为已读"""
    try:
        # 调用通知服务
        result = await microservice_client.call_service(
            "notification",
            "POST",
            f"/users/{user_id}/notifications/{notification_id}/read"
        )
        
        return success_response(result, "通知已标记为已读")
        
    except HTTPException as e:
        raise e
    except Exception as e:
        return error_response(ErrorCode.SERVICE_UNAVAILABLE, f"标记通知为已读失败: {str(e)}")

# ============================================================================
# 系统管理API
# ============================================================================

@app.get("/api/v1/system/status")
async def get_system_status():
    """获取系统状态"""
    try:
        # 获取所有微服务健康状态
        services_health = await microservice_client.health_check_all()
        
        # 获取系统统计
        stats = {
            "timestamp": datetime.utcnow().isoformat(),
            "services": services_health,
            "system": {
                "uptime": "24h",  # 这里应该计算实际运行时间
                "memory_usage": "45%",
                "cpu_usage": "32%",
                "active_connections": 150
            }
        }
        
        return success_response(stats, "系统状态获取成功")
        
    except Exception as e:
        return error_response(ErrorCode.SERVICE_UNAVAILABLE, f"获取系统状态失败: {str(e)}")

@app.get("/api/v1/system/metrics")
async def get_system_metrics(
    time_range: str = Query("1h", description="时间范围: 1h, 24h, 7d, 30d")
):
    """获取系统指标"""
    try:
        # 这里应该从监控系统获取指标
        # 暂时返回模拟数据
        
        metrics = {
            "requests_per_second": 42.5,
            "average_response_time": 125.3,
            "error_rate": 0.02,
            "active_users": 850,
            "cpu_usage": [45, 48, 42, 47, 43, 46, 44],
            "memory_usage": [65, 67, 64, 66, 65, 68, 66],
            "service_health": {
                "api_gateway": 99.8,
                "course_generator": 99.5,
                "video_analyzer": 98.7,
                "knowledge_extractor": 99.2,
                "search_engine": 99.9,
                "recommendation": 99.6,
                "notification": 99.3
            }
        }
        
        return success_response(metrics, "系统指标获取成功")
        
    except Exception as e:
        return error_response(ErrorCode.SERVICE_UNAVAILABLE, f"获取系统指标失败: {str(e)}")

# ============================================================================
# 错误处理
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP异常处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(
            ErrorCode.UNKNOWN_ERROR,
            exc.detail,
            {"path": request.url.path}
        )
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """通用异常处理"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response(
            ErrorCode.UNKNOWN_ERROR,
            "服务器内部错误",
            {"path": request.url.path, "error": str(exc)}
        )
    )

# ============================================================================
# 主函数
# ============================================================================

if __name__ == "__main__":
    print(f"🚀 启动完整API网关...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )