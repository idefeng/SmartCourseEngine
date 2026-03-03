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
from pathlib import Path
from datetime import datetime

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
    if not service_config.security.require_api_key:
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
        
        return BaseResponse.success(
            message="获取课程列表成功",
            data=result
        )
    except Exception as e:
        logger.error(f"列出课程失败: {e}")
        return BaseResponse.error(
            message="获取课程列表失败",
            error_code="COURSE_LIST_ERROR"
        )

@app.post("/api/v1/courses", tags=["课程"])
@handle_exceptions
async def create_course(
    authenticated: bool = Depends(verify_api_key)
):
    """创建课程"""
    # 这里应该代理到course-generator服务
    return BaseResponse(
        success=True,
        message="创建课程请求已接收",
        data={"job_id": "demo-job-id"}
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