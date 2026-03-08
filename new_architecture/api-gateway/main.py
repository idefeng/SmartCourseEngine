#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API网关服务
===========

SmartCourseEngine的API网关，提供统一的API入口、认证、路由和限流功能。

作者: SmartCourseEngine Team
日期: 2026-03-01
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

# 添加共享模块路径
# 将 api-gateway 的父目录 (new_architecture) 添加到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
# 将 shared 目录添加到 sys.path (为了直接导入 shared 内部模块)
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))

from fastapi import FastAPI, Depends, HTTPException, status, Query, Body
from fastapi.params import Path as FastAPIPath
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
import uvicorn

# 添加共享模块路径
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from shared.config import config, load_config_from_file
    from shared.utils import setup_logger, handle_exceptions, SmartCourseError
    from shared.models import BaseResponse
    from shared.database import check_database_health
except ImportError:
    # 备用导入方式
    from config import config, load_config_from_file
    from utils import setup_logger, handle_exceptions, SmartCourseError
    from models import BaseResponse
    from database import check_database_health


# ============================================================================
# 配置和日志
# ============================================================================

# 加载配置
cfg = load_config_from_file()
service_config = cfg.service

# 设置日志
logger = setup_logger(
    name="api-gateway",
    level=service_config.log_level,
    format_str=service_config.log_format
)

try:
    from auth_routes import router as auth_router
    AUTH_ENABLED = True
except ImportError as e:
    auth_router = None
    AUTH_ENABLED = False
    logger.warning(f"认证路由导入失败: {e}")

try:
    from shared.websocket import router as websocket_router
    WEBSOCKET_ENABLED = True
except ImportError as e:
    websocket_router = None
    WEBSOCKET_ENABLED = False
    logger.warning(f"WebSocket路由导入失败: {e}")

try:
    from shared.file_upload import upload_router
    FILE_UPLOAD_ENABLED = True
except ImportError as e:
    upload_router = None
    FILE_UPLOAD_ENABLED = False
    logger.warning(f"文件上传路由导入失败: {e}")

# ============================================================================
# FastAPI应用
# ============================================================================

app = FastAPI(
    title="SmartCourseEngine API Gateway",
    description="智能课程知识库系统API网关",
    version="1.0.0",
    docs_url=None,  # 自定义文档URL
    redoc_url=None,
    openapi_url="/openapi.json"
)

# 挂载上传文件目录，供前端直接访问
import os
os.makedirs("/app/uploads", exist_ok=True)
app.mount("/app/uploads", StaticFiles(directory="/app/uploads"), name="uploads")

if AUTH_ENABLED and auth_router:
    app.include_router(auth_router)
    logger.info("认证路由已注册: /api/v1/auth")

if WEBSOCKET_ENABLED and websocket_router:
    app.include_router(websocket_router)
    logger.info("WebSocket路由已注册: /ws")

if FILE_UPLOAD_ENABLED and upload_router:
    app.include_router(upload_router)
    logger.info("文件上传路由已注册: /api/v1/upload")

# ============================================================================
# 中间件
# ============================================================================

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=service_config.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# 可信主机中间件
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # 生产环境应该限制
)

# 自定义中间件：请求日志
@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"请求: {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    logger.info(f"响应: {request.method} {request.url.path} - {response.status_code}")
    
    return response

# ============================================================================
# 异常处理
# ============================================================================

@app.exception_handler(SmartCourseError)
async def smartcourse_exception_handler(request, exc: SmartCourseError):
    """处理SmartCourseEngine异常"""
    logger.error(f"业务异常: {exc.code} - {exc}")
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=exc.to_dict()
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """处理HTTP异常"""
    logger.error(f"HTTP异常: {exc.status_code} - {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content=BaseResponse(
            success=False,
            message=exc.detail,
            error_code=f"HTTP_{exc.status_code}"
        ).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """处理通用异常"""
    logger.error(f"未处理异常: {type(exc).__name__} - {exc}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=BaseResponse(
            success=False,
            message="内部服务器错误",
            error_code="INTERNAL_ERROR"
        ).dict()
    )

# ============================================================================
# 认证依赖
# ============================================================================

async def verify_api_key(api_key: str = Depends(lambda: "")):
    """验证API密钥"""
    if not cfg.security.require_api_key:
        return True
    
    # 这里应该实现实际的API密钥验证逻辑
    # 例如从数据库或Redis中验证
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少API密钥"
        )
    
    # 简单的演示验证
    if api_key != "demo-api-key":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的API密钥"
        )
    
    return True

# ============================================================================
# 路由
# ============================================================================

@app.get("/", tags=["根路径"])
async def root():
    """根路径"""
    return {
        "service": "SmartCourseEngine API Gateway",
        "version": "1.0.0",
        "status": "running",
        "documentation": "/docs"
    }

@app.get("/health", tags=["健康检查"])
async def health_check():
    """健康检查端点"""
    # 检查数据库健康状态
    db_health = await check_database_health()
    
    # 确定整体状态
    all_healthy = all(db_health.values())
    status = "healthy" if all_healthy else "degraded"
    
    return {
        "status": status,
        "service": service_config.service_name,
        "timestamp": datetime.now().isoformat(),
        "database_health": db_health
    }

@app.get("/docs", include_in_schema=False)
async def custom_docs():
    """自定义API文档"""
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="SmartCourseEngine API 文档",
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png"
    )

@app.get("/openapi.json", include_in_schema=False)
async def get_openapi_endpoint():
    """获取OpenAPI规范"""
    return get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes
    )

# ============================================================================
# 服务路由（代理到实际服务）
# ============================================================================

@app.get("/api/v1/courses", tags=["课程"])
@handle_exceptions
async def list_courses(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页大小"),
    is_published: Optional[bool] = Query(None, description="是否已发布"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    authenticated: bool = Depends(verify_api_key)
):
    """列出课程"""
    try:
        from services.course_service import course_service
        
        result = course_service.list_courses(
            page=page,
            page_size=page_size,
            is_published=is_published,
            search=search
        )
        
        return BaseResponse(
            success=True,
            message="获取课程列表成功",
            data=result
        )
    except Exception as e:
        logger.error(f"列出课程失败: {e}")
        return BaseResponse(
            success=False,
            message="获取课程列表失败",
            error_code="COURSE_LIST_ERROR"
        )

@app.post("/api/v1/courses", tags=["课程"])
@handle_exceptions
async def create_course(
    payload: Dict[str, Any] = Body(...),
    authenticated: bool = Depends(verify_api_key)
):
    """创建课程"""
    from services.course_service import course_service
    course = course_service.create_course(payload)
    return BaseResponse(
        success=True,
        message="课程创建成功",
        data=course
    )

@app.put("/api/v1/courses/{course_id}", tags=["课程"])
@handle_exceptions
async def update_course(
    course_id: int,
    payload: Dict[str, Any] = Body(...),
    authenticated: bool = Depends(verify_api_key)
):
    """更新课程"""
    from services.course_service import course_service
    course = course_service.update_course(course_id, payload)
    if not course:
        return BaseResponse(
            success=False,
            message="课程不存在",
            error_code="COURSE_NOT_FOUND"
        )
    return BaseResponse(
        success=True,
        message="课程更新成功",
        data=course
    )

@app.delete("/api/v1/courses/{course_id}", tags=["课程"])
@handle_exceptions
async def delete_course(
    course_id: int,
    authenticated: bool = Depends(verify_api_key)
):
    """删除课程"""
    from services.course_service import course_service
    success = course_service.delete_course(course_id)
    if not success:
        return BaseResponse(
            success=False,
            message="课程未找到或删除失败",
            error_code="COURSE_DELETE_ERROR"
        )
    return BaseResponse(
        success=True,
        message="课程删除成功"
    )

@app.post("/api/v1/videos/analyze", tags=["视频分析"])
@handle_exceptions
async def analyze_video(
    authenticated: bool = Depends(verify_api_key)
):
    """分析视频"""
    # 这里应该代理到video-analyzer服务
    return BaseResponse(
        success=True,
        message="视频分析请求已接收",
        data={"analysis_id": "demo-analysis-id"}
    )

@app.get("/api/v1/videos", tags=["视频"])
@handle_exceptions
async def list_videos(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页大小"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    authenticated: bool = Depends(verify_api_key)
):
    upload_root = Path("/app/uploads")
    metadata_dir = upload_root / "temp"
    records: List[Dict[str, Any]] = []
    if metadata_dir.exists():
        for metadata_file in metadata_dir.glob("*.json"):
            try:
                payload = json.loads(metadata_file.read_text(encoding="utf-8"))
            except Exception:
                continue
            upload_id = payload.get("upload_id") or metadata_file.stem
            file_name = payload.get("file_name") or ""
            ext = Path(file_name).suffix.lower().lstrip(".")
            custom_meta = payload.get("metadata") or {}
            analysis_result = custom_meta.get("analysis_result")
            worker_meta = custom_meta.get("worker") if isinstance(custom_meta.get("worker"), dict) else {}
            knowledge_points_count = 0
            if isinstance(analysis_result, dict) and isinstance(analysis_result.get("knowledge_points"), list):
                knowledge_points_count = len(analysis_result.get("knowledge_points") or [])
            transcript = None
            if isinstance(analysis_result, dict):
                transcript = analysis_result.get("transcript")
            created_at = payload.get("created_at") or datetime.now().isoformat()
            updated_at = payload.get("updated_at") or created_at
            item: Dict[str, Any] = {
                "id": str(upload_id),
                "title": Path(file_name).stem or str(upload_id),
                "description": str(custom_meta.get("description") or ""),
                "file_path": payload.get("file_path") or f"/uploads/{file_name}",
                "thumbnail_url": "",
                "duration": float((transcript or {}).get("duration", 0) or 0),
                "file_size": int(payload.get("file_size") or 0),
                "format": ext or "mp4",
                "status": str(payload.get("status") or "processing"),
                "progress": int((len(payload.get("uploaded_chunks") or []) / max(int(payload.get("total_chunks") or 1), 1)) * 100),
                "course_id": custom_meta.get("course_id"),
                "created_at": created_at,
                "updated_at": updated_at,
                "analysis_result": analysis_result,
                "transcript": transcript,
                "pipeline_stage": worker_meta.get("stage"),
                "knowledge_points_count": knowledge_points_count,
            }
            records.append(item)
    records.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    if search:
        key = search.strip().lower()
        records = [
            item for item in records
            if key in (item.get("title") or "").lower()
            or key in (item.get("description") or "").lower()
            or key in (item.get("id") or "").lower()
        ]
    total = len(records)
    start = (page - 1) * page_size
    end = start + page_size
    return BaseResponse(
        success=True,
        message="获取视频列表成功",
        data={
            "items": records[start:end],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    )

@app.delete("/api/v1/videos/{video_id}", tags=["视频"])
async def delete_video(
    video_id: str = FastAPIPath(..., description="视频ID"),
    authenticated: bool = Depends(verify_api_key)
):
    upload_root = Path("/app/uploads").resolve()
    metadata_dir = upload_root / "temp"
    chunk_dir = upload_root / "chunks"
    metadata_file = metadata_dir / f"{video_id}.json"

    if not metadata_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="视频不存在"
        )

    payload: Dict[str, Any] = {}
    try:
        payload = json.loads(metadata_file.read_text(encoding="utf-8"))
    except Exception:
        payload = {}

    deleted_files = 0

    file_candidates: List[Path] = []
    file_path_value = payload.get("file_path")
    if isinstance(file_path_value, str) and file_path_value.strip():
        file_candidates.append(Path(file_path_value.strip()))

    file_name = payload.get("file_name")
    if isinstance(file_name, str) and file_name.strip():
        file_candidates.append(upload_root / file_name.strip())

    for candidate in file_candidates:
        try:
            resolved = candidate if candidate.is_absolute() else (upload_root / candidate)
            resolved = resolved.resolve()
            if upload_root in resolved.parents and resolved.exists() and resolved.is_file():
                resolved.unlink()
                deleted_files += 1
        except Exception:
            continue

    for chunk_file in chunk_dir.glob(f"{video_id}_*.chunk"):
        try:
            chunk_file.unlink()
            deleted_files += 1
        except Exception:
            continue

    try:
        metadata_file.unlink()
        deleted_files += 1
    except Exception:
        pass

    return BaseResponse(
        success=True,
        message="视频删除成功",
        data={
            "id": video_id,
            "deleted_files": deleted_files
        }
    )

@app.get("/api/v1/knowledge/search", tags=["知识检索"])
@handle_exceptions
async def search_knowledge(
    query: str,
    limit: int = 10,
    authenticated: bool = Depends(verify_api_key)
):
    """搜索知识点"""
    # 这里应该代理到search-engine服务
    return BaseResponse(
        success=True,
        message="搜索成功",
        data={
            "query": query,
            "results": [],
            "total": 0
        }
    )

@app.get("/api/v1/knowledge/points", tags=["知识点"])
@handle_exceptions
async def list_knowledge_points(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=200, description="每页大小"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    authenticated: bool = Depends(verify_api_key)
):
    metadata_dir = Path("/app/uploads/temp")
    points: List[Dict[str, Any]] = []
    if metadata_dir.exists():
        for metadata_file in metadata_dir.glob("*.json"):
            try:
                payload = json.loads(metadata_file.read_text(encoding="utf-8"))
            except Exception:
                continue
            meta = payload.get("metadata") or {}
            analysis_result = meta.get("analysis_result") or {}
            kp_list = analysis_result.get("knowledge_points") if isinstance(analysis_result, dict) else None
            if not isinstance(kp_list, list):
                continue
            course_id = analysis_result.get("course_id") or meta.get("course_id")
            created_at = payload.get("created_at") or datetime.now().isoformat()
            updated_at = payload.get("updated_at") or created_at
            for idx, kp in enumerate(kp_list):
                if not isinstance(kp, dict):
                    continue
                start_time = kp.get("timestamp")
                end_time = kp.get("timestamp")
                if isinstance(start_time, str) and ":" in start_time:
                    parts = start_time.split(":")
                    try:
                        start_time = int(parts[0]) * 60 + int(parts[1])
                        end_time = start_time
                    except Exception:
                        start_time = 0
                        end_time = 0
                else:
                    start_time = float(start_time or 0)
                    end_time = float(end_time or start_time)
                concepts = kp.get("keywords")
                if not isinstance(concepts, list):
                    concepts = []
                point = {
                    "id": int(f"{abs(hash(str(payload.get('upload_id') or metadata_file.stem))) % 100000}{idx}"),
                    "name": kp.get("title") or f"知识点{idx + 1}",
                    "description": kp.get("content") or "",
                    "category": kp.get("category") or "通用",
                    "importance": int(kp.get("importance") or 3),
                    "confidence": float(kp.get("confidence") or 0.8),
                    "start_time": float(start_time),
                    "end_time": float(end_time),
                    "course_id": int(course_id) if course_id is not None else 0,
                    "concepts": concepts,
                    "embedding": kp.get("embedding") if isinstance(kp.get("embedding"), list) else [],
                    "created_at": created_at,
                    "updated_at": updated_at
                }
                points.append(point)
    if search:
        key = search.strip().lower()
        points = [
            item for item in points
            if key in (item.get("name") or "").lower()
            or key in (item.get("description") or "").lower()
            or key in (item.get("category") or "").lower()
            or any(key in str(concept).lower() for concept in (item.get("concepts") or []))
        ]
    points.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    total = len(points)
    start = (page - 1) * page_size
    end = start + page_size
    return BaseResponse(
        success=True,
        message="获取知识点列表成功",
        data={
            "items": points[start:end],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    )

@app.post("/api/v1/knowledge/graph", tags=["知识点"])
@handle_exceptions
async def build_knowledge_graph(
    payload: Dict[str, Any] = Body(...),
    authenticated: bool = Depends(verify_api_key)
):
    """
    构建知识图谱：基于知识点列表生成节点和边
    此版本为 Mock 实现，直接基于传入的知识点生成简单的拓扑结构
    """
    knowledge_points = payload.get("knowledge_points", [])
    if not isinstance(knowledge_points, list):
        knowledge_points = []
        
    nodes = []
    edges = []
    
    # 模拟生成节点
    for kp in knowledge_points:
        # 知识点节点
        nodes.append({
            "id": f"kp_{kp.get('id')}",
            "type": "knowledge_point",
            "name": kp.get("name"),
            "category": kp.get("category"),
            "importance": kp.get("importance")
        })
        
        # 提取概念并建立连接
        concepts = kp.get("concepts", [])
        for concept in concepts:
            concept_id = f"concept_{concept}"
            # 如果概念节点已存在则不重复添加
            if not any(n["id"] == concept_id for n in nodes):
                nodes.append({
                    "id": concept_id,
                    "type": "concept",
                    "name": concept,
                    "category": "概念"
                })
            
            # 建立知识点到概念的边
            edges.append({
                "source": f"kp_{kp.get('id')}",
                "target": concept_id,
                "type": "MENTIONS",
                "weight": 1.0
            })
            
    return BaseResponse(
        success=True,
        message="构建知识图谱成功",
        data={
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "knowledge_points": len(knowledge_points),
                "generated_at": datetime.now().isoformat()
            }
        }
    )

@app.get("/api/v1/users", tags=["用户"])
@handle_exceptions
async def list_users(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=200, description="每页大小"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    authenticated: bool = Depends(verify_api_key)
):
    """
    获取用户列表（Mock 实现）
    """
    mock_users = [
        {
            "id": 1,
            "username": "learning_wizard",
            "email": "wizard@example.com",
            "role": "admin",
            "status": "active",
            "last_login": (datetime.now() - timedelta(hours=2)).isoformat(),
            "learning_progress": 95,
            "enrolled_courses": 12,
            "created_at": "2024-01-10T10:00:00"
        },
        {
            "id": 2,
            "username": "codemaster_99",
            "email": "code@example.com",
            "role": "master",
            "status": "active",
            "last_login": (datetime.now() - timedelta(days=1)).isoformat(),
            "learning_progress": 78,
            "enrolled_courses": 5,
            "created_at": "2024-02-15T14:30:00"
        },
        {
            "id": 3,
            "username": "student_007",
            "email": "james@edu.com",
            "role": "student",
            "status": "active",
            "last_login": (datetime.now() - timedelta(minutes=45)).isoformat(),
            "learning_progress": 42,
            "enrolled_courses": 8,
            "created_at": "2024-03-01T09:15:00"
        },
        {
            "id": 4,
            "username": "data_explorer",
            "email": "explorer@lab.io",
            "role": "student",
            "status": "inactive",
            "last_login": (datetime.now() - timedelta(weeks=2)).isoformat(),
            "learning_progress": 15,
            "enrolled_courses": 2,
            "created_at": "2024-02-20T11:20:00"
        }
    ]
    
    if search:
        s = search.lower()
        mock_users = [u for u in mock_users if s in u["username"].lower() or s in u["email"].lower()]
        
    return BaseResponse(
        success=True,
        message="获取用户列表成功",
        data={
            "items": mock_users,
            "total": len(mock_users),
            "page": page,
            "page_size": page_size
        }
    )

# ============================================================================
# 数据分析端点 (Mock)
# ============================================================================

@app.get("/api/v1/analytics/overview", tags=["分析"])
@handle_exceptions
async def get_analytics_overview(authenticated: bool = Depends(verify_api_key)):
    """获取数据分析概览"""
    return BaseResponse(
        success=True,
        message="获取概览成功",
        data={
            "total_learning_hours": 2840,
            "knowledge_coverage": 84,
            "active_users": 1248,
            "completion_rate": 68,
            "trends": {
                "hours": "+12.5%",
                "coverage": "+4.2%",
                "users": "-2.1%",
                "completion": "+8.1%"
            }
        }
    )

@app.get("/api/v1/analytics/trends", tags=["分析"])
@handle_exceptions
async def get_learning_trends(authenticated: bool = Depends(verify_api_key)):
    """获取学习趋势数据"""
    return BaseResponse(
        success=True,
        message="获取趋势成功",
        data={
            "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "datasets": [
                {"label": "Learning Activity", "data": [40, 70, 45, 90, 65, 80, 50]},
                {"label": "Knowledge Acquisition", "data": [20, 50, 30, 70, 40, 60, 30]}
            ]
        }
    )

# ============================================================================

# GraphQL端点（预留）
# ============================================================================

# 这里可以添加GraphQL支持
# from strawberry.fastapi import GraphQLRouter
# import strawberry
# 
# @strawberry.type
# class Query:
#     @strawberry.field
#     def hello(self) -> str:
#         return "Hello World"
# 
# schema = strawberry.Schema(query=Query)
# graphql_app = GraphQLRouter(schema)
# 
# app.include_router(graphql_app, prefix="/graphql")

# ============================================================================
# 内部实时通信API (供内部微服务调用)
# ============================================================================

@app.post("/api/v1/internal/ws/broadcast", tags=["内部服务"])
async def internal_ws_broadcast(
    payload: Dict[str, Any] = Body(...)
):
    """
    内部广播接口：允许微服务通过网关向WebSocket客户端推送消息
    """
    if not WEBSOCKET_ENABLED or not websocket_router:
        return error_response(ErrorCode.SERVICE_UNAVAILABLE, "WebSocket服务未启用")
        
    try:
        from shared.websocket import websocket_service, MessageType
        
        target_user_id = payload.get("user_id")
        message_type_str = payload.get("type")
        data = payload.get("data", {})
        
        try:
            message_type = MessageType(message_type_str)
        except ValueError:
            return error_response(ErrorCode.VALIDATION_ERROR, f"无效的消息类型: {message_type_str}")
            
        if target_user_id:
            await websocket_service.connection_manager.send_to_user(
                int(target_user_id),
                message_type,
                data
            )
            logger.info(f"内部推送消息到用户 {target_user_id}: {message_type}")
        else:
            await websocket_service.connection_manager.broadcast(
                message_type,
                data
            )
            logger.info(f"内部广播消息: {message_type}")
            
        return success_response(message="已推送到WebSocket")
    except Exception as e:
        logger.error(f"内部实时通信推送失败: {e}")
        return error_response(ErrorCode.UNKNOWN_ERROR, str(e))

@app.post("/api/v1/internal/ws/task-progress", tags=["内部服务"])
async def internal_ws_task_progress(
    task_id: str = Body(...),
    user_id: int = Body(...),
    progress: int = Body(...),
    stage: str = Body(...),
    message: str = Body(None),
    metadata: Dict[str, Any] = Body(None)
):
    """
    内部进度更新接口：供Worker更新处理进度
    """
    if not WEBSOCKET_ENABLED or not websocket_router:
        return error_response(ErrorCode.SERVICE_UNAVAILABLE, "WebSocket服务未启用")
        
    try:
        from shared.websocket import websocket_service
        
        # 确保任务已在跟踪器中
        if not websocket_service.task_tracker.get_task(task_id):
            websocket_service.task_tracker.create_task(
                task_id=task_id,
                task_type="video_analysis",
                user_id=user_id,
                metadata=metadata or {}
            )
            
        await websocket_service.update_video_analysis_progress(
            task_id=task_id,
            progress=progress,
            stage=stage,
            message=message
        )
        
        # 如果是100%或完成状态，标记为完成
        if progress >= 100 or stage in ["completed", "success"]:
            await websocket_service.complete_task(task_id, result=metadata)
            
        return success_response(message="进度已更新")
    except Exception as e:
        logger.error(f"内部进度更新失败: {e}")
        return error_response(ErrorCode.UNKNOWN_ERROR, str(e))

# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数"""
    logger.info(f"启动API网关服务: {service_config.service_name}")
    logger.info(f"服务端口: {service_config.service_port}")
    logger.info(f"调试模式: {service_config.debug}")
    logger.info(f"CORS允许的来源: {service_config.cors_origins}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=service_config.service_port,
        log_level="info",
        reload=service_config.debug
    )

if __name__ == "__main__":
    main()
