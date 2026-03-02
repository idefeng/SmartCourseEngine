#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API响应格式和错误处理
===============

统一的API响应格式和错误处理机制。

作者: SmartCourseEngine Team
日期: 2026-03-01
"""

from typing import Any, Dict, List, Optional, TypeVar, Generic
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

T = TypeVar('T')

# ============================================================================
# API响应格式
# ============================================================================

class ApiResponse(BaseModel, Generic[T]):
    """统一的API响应格式"""
    success: bool = Field(..., description="请求是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[T] = Field(None, description="响应数据")
    timestamp: str = Field(..., description="响应时间戳")
    
    @classmethod
    def success_response(cls, message: str = "成功", data: Any = None) -> "ApiResponse":
        """创建成功响应"""
        return cls(
            success=True,
            message=message,
            data=data,
            timestamp=datetime.utcnow().isoformat()
        )
    
    @classmethod
    def error_response(cls, message: str = "失败", data: Any = None) -> "ApiResponse":
        """创建错误响应"""
        return cls(
            success=False,
            message=message,
            data=data,
            timestamp=datetime.utcnow().isoformat()
        )


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应格式"""
    items: List[T] = Field(..., description="数据列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")
    total_pages: int = Field(..., description="总页数")


class ApiPaginatedResponse(ApiResponse[PaginatedResponse[T]], Generic[T]):
    """API分页响应"""
    pass


# ============================================================================
# 错误处理
# ============================================================================

class ErrorCode(Enum):
    """错误代码枚举"""
    # 通用错误
    UNKNOWN_ERROR = ("0000", "未知错误")
    VALIDATION_ERROR = ("0001", "参数验证失败")
    DATABASE_ERROR = ("0002", "数据库错误")
    NETWORK_ERROR = ("0003", "网络错误")
    PERMISSION_DENIED = ("0004", "权限不足")
    RESOURCE_NOT_FOUND = ("0005", "资源不存在")
    RESOURCE_ALREADY_EXISTS = ("0006", "资源已存在")
    
    # 业务错误
    USER_NOT_FOUND = ("1001", "用户不存在")
    USER_ALREADY_EXISTS = ("1002", "用户已存在")
    INVALID_CREDENTIALS = ("1003", "无效的凭证")
    TOKEN_EXPIRED = ("1004", "Token已过期")
    TOKEN_INVALID = ("1005", "无效的Token")
    
    # 课程相关错误
    COURSE_NOT_FOUND = ("2001", "课程不存在")
    COURSE_ALREADY_EXISTS = ("2002", "课程已存在")
    COURSE_NOT_PUBLISHED = ("2003", "课程未发布")
    
    # 视频相关错误
    VIDEO_NOT_FOUND = ("3001", "视频不存在")
    VIDEO_UPLOAD_FAILED = ("3002", "视频上传失败")
    VIDEO_ANALYSIS_FAILED = ("3003", "视频分析失败")
    VIDEO_FORMAT_NOT_SUPPORTED = ("3004", "视频格式不支持")
    
    # 知识相关错误
    KNOWLEDGE_POINT_NOT_FOUND = ("4001", "知识点不存在")
    KNOWLEDGE_EXTRACTION_FAILED = ("4002", "知识提取失败")
    KNOWLEDGE_GRAPH_BUILD_FAILED = ("4003", "知识图谱构建失败")
    
    # 搜索相关错误
    SEARCH_FAILED = ("5001", "搜索失败")
    SEARCH_INDEX_NOT_READY = ("5002", "搜索索引未就绪")


class ApiException(Exception):
    """API异常基类"""
    
    def __init__(
        self,
        error_code: ErrorCode,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.error_code = error_code
        self.message = message or error_code.value[1]
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "success": False,
            "message": self.message,
            "error_code": self.error_code.value[0],
            "error_message": self.error_code.value[1],
            "details": self.details,
            "timestamp": datetime.utcnow().isoformat()
        }


class ValidationException(ApiException):
    """参数验证异常"""
    
    def __init__(self, errors: List[Dict[str, Any]]):
        super().__init__(
            error_code=ErrorCode.VALIDATION_ERROR,
            details={"errors": errors}
        )


class NotFoundException(ApiException):
    """资源不存在异常"""
    
    def __init__(self, resource_type: str, resource_id: Any):
        super().__init__(
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
            details={
                "resource_type": resource_type,
                "resource_id": resource_id
            }
        )


class PermissionDeniedException(ApiException):
    """权限不足异常"""
    
    def __init__(self, action: str, resource: str):
        super().__init__(
            error_code=ErrorCode.PERMISSION_DENIED,
            details={
                "action": action,
                "resource": resource
            }
        )


# ============================================================================
# 请求/响应模型
# ============================================================================

class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(10, ge=1, le=100, description="每页大小")
    
    @property
    def offset(self) -> int:
        """计算偏移量"""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """计算限制数量"""
        return self.page_size


class SearchParams(BaseModel):
    """搜索参数"""
    query: str = Field(..., min_length=1, max_length=200, description="搜索关键词")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(10, ge=1, le=100, description="每页大小")


class SortParams(BaseModel):
    """排序参数"""
    sort_by: str = Field("created_at", description="排序字段")
    sort_order: str = Field("desc", description="排序顺序（asc/desc）")


class FilterParams(BaseModel):
    """筛选参数"""
    filters: Dict[str, Any] = Field(default_factory=dict, description="筛选条件")


# ============================================================================
# 工具函数
# ============================================================================

def create_paginated_response(
    items: List[T],
    total: int,
    page: int,
    page_size: int
) -> PaginatedResponse[T]:
    """创建分页响应"""
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


def format_error_response(
    error_code: ErrorCode,
    message: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """格式化错误响应"""
    return ApiException(
        error_code=error_code,
        message=message,
        details=details
    ).to_dict()


def success_response(data: Any = None, message: str = "成功") -> Dict[str, Any]:
    """创建成功响应"""
    return ApiResponse.success_response(message=message, data=data).dict()


def error_response(
    error_code: ErrorCode,
    message: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """创建错误响应"""
    return format_error_response(error_code, message, details)


# ============================================================================
# FastAPI集成
# ============================================================================

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import traceback


def setup_exception_handlers(app: FastAPI):
    """设置异常处理器"""
    
    @app.exception_handler(ApiException)
    async def api_exception_handler(request: Request, exc: ApiException):
        """API异常处理器"""
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=exc.to_dict()
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """参数验证异常处理器"""
        errors = []
        for error in exc.errors():
            errors.append({
                "field": " -> ".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"]
            })
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=format_error_response(
                error_code=ErrorCode.VALIDATION_ERROR,
                details={"errors": errors}
            )
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """通用异常处理器"""
        # 记录错误日志
        error_traceback = traceback.format_exc()
        print(f"Unhandled exception: {exc}")
        print(f"Traceback: {error_traceback}")
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=format_error_response(
                error_code=ErrorCode.UNKNOWN_ERROR,
                message="服务器内部错误",
                details={"error": str(exc)}
            )
        )


def create_api_response(
    data: Any = None,
    message: str = "成功",
    success: bool = True
) -> Dict[str, Any]:
    """创建API响应"""
    return ApiResponse(
        success=success,
        message=message,
        data=data,
        timestamp=datetime.utcnow().isoformat()
    ).dict()


# ============================================================================
# 测试数据
# ============================================================================

if __name__ == "__main__":
    # 测试API响应格式
    response = ApiResponse.success_response(
        message="操作成功",
        data={"id": 1, "name": "测试数据"}
    )
    print("成功响应:", response.dict())
    
    # 测试分页响应
    paginated = create_paginated_response(
        items=[{"id": i, "name": f"Item {i}"} for i in range(1, 6)],
        total=100,
        page=1,
        page_size=10
    )
    print("分页响应:", paginated.dict())
    
    # 测试错误响应
    error = format_error_response(
        error_code=ErrorCode.RESOURCE_NOT_FOUND,
        details={"resource_type": "user", "resource_id": 123}
    )
    print("错误响应:", error)