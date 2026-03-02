#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户认证路由
==========

用户注册、登录、令牌刷新等认证相关API。

作者: SmartCourseEngine Team
日期: 2026-03-01
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from shared.auth import (
    UserCreate,
    UserLogin,
    UserUpdate,
    UserResponse,
    TokenResponse,
    UserService,
    JWTUtils,
    AuthMiddleware,
    PasswordUtils,
    create_user_response,
    create_token_response,
    get_current_user,
    get_current_active_user,
    require_admin,
    security,
)
from shared.api_response import (
    success_response,
    error_response,
    ApiException,
    ErrorCode,
)

# 创建路由
router = APIRouter(prefix="/api/v1/auth", tags=["认证"])

# 创建用户服务实例（这里使用模拟数据库）
user_service = UserService(db=None)

# ============================================================================
# 公开路由（无需认证）
# ============================================================================

@router.post("/register", response_model=dict)
async def register(user_data: UserCreate):
    """用户注册"""
    try:
        # 创建用户
        user = user_service.create_user(user_data)
        
        # 创建令牌
        token_response = create_token_response(user)
        
        return success_response(
            data=token_response.dict(),
            message="注册成功"
        )
        
    except ApiException as e:
        return error_response(
            error_code=e.error_code,
            message=e.message,
            details=e.details
        )
    except Exception as e:
        return error_response(
            error_code=ErrorCode.UNKNOWN_ERROR,
            message="注册失败",
            details={"error": str(e)}
        )


@router.post("/login", response_model=dict)
async def login(login_data: UserLogin):
    """用户登录"""
    try:
        # 验证用户凭证
        user = user_service.authenticate_user(login_data.email, login_data.password)
        
        if not user:
            return error_response(
                error_code=ErrorCode.INVALID_CREDENTIALS,
                message="邮箱或密码不正确"
            )
        
        # 创建令牌
        token_response = create_token_response(user)
        
        return success_response(
            data=token_response.dict(),
            message="登录成功"
        )
        
    except ApiException as e:
        return error_response(
            error_code=e.error_code,
            message=e.message,
            details=e.details
        )
    except Exception as e:
        return error_response(
            error_code=ErrorCode.UNKNOWN_ERROR,
            message="登录失败",
            details={"error": str(e)}
        )


@router.post("/refresh", response_model=dict)
async def refresh_token(refresh_token: str):
    """刷新访问令牌"""
    try:
        # 验证刷新令牌
        payload = JWTUtils.verify_token(refresh_token)
        
        if payload.get("type") != "refresh":
            return error_response(
                error_code=ErrorCode.TOKEN_INVALID,
                message="无效的刷新令牌"
            )
        
        # 获取用户信息
        user_id = int(payload.get("sub"))
        user = user_service.get_user_by_id(user_id)
        
        if not user:
            return error_response(
                error_code=ErrorCode.USER_NOT_FOUND,
                message="用户不存在"
            )
        
        # 创建新的访问令牌
        token_response = create_token_response(user)
        
        return success_response(
            data=token_response.dict(),
            message="令牌刷新成功"
        )
        
    except ApiException as e:
        return error_response(
            error_code=e.error_code,
            message=e.message,
            details=e.details
        )
    except Exception as e:
        return error_response(
            error_code=ErrorCode.UNKNOWN_ERROR,
            message="令牌刷新失败",
            details={"error": str(e)}
        )


@router.post("/forgot-password")
async def forgot_password(email: str):
    """忘记密码（发送重置邮件）"""
    try:
        # 检查用户是否存在
        user = user_service.get_user_by_email(email)
        
        if not user:
            # 出于安全考虑，不透露用户是否存在
            return success_response(
                message="如果邮箱存在，重置链接已发送"
            )
        
        # 这里应该发送密码重置邮件
        # 为了简化，我们只返回成功消息
        
        return success_response(
            message="密码重置链接已发送到您的邮箱"
        )
        
    except Exception as e:
        return error_response(
            error_code=ErrorCode.UNKNOWN_ERROR,
            message="发送重置邮件失败",
            details={"error": str(e)}
        )


# ============================================================================
# 需要认证的路由
# ============================================================================

@router.get("/me", response_model=dict)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    try:
        user_data = user_service.get_user_by_id(current_user["id"])
        
        if not user_data:
            return error_response(
                error_code=ErrorCode.USER_NOT_FOUND,
                message="用户不存在"
            )
        
        user_response = create_user_response(user_data)
        
        return success_response(
            data=user_response.dict(),
            message="获取用户信息成功"
        )
        
    except Exception as e:
        return error_response(
            error_code=ErrorCode.UNKNOWN_ERROR,
            message="获取用户信息失败",
            details={"error": str(e)}
        )


@router.put("/me", response_model=dict)
async def update_current_user_info(
    update_data: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    """更新当前用户信息"""
    try:
        updated_user = user_service.update_user(current_user["id"], update_data)
        user_response = create_user_response(updated_user)
        
        return success_response(
            data=user_response.dict(),
            message="用户信息更新成功"
        )
        
    except ApiException as e:
        return error_response(
            error_code=e.error_code,
            message=e.message,
            details=e.details
        )
    except Exception as e:
        return error_response(
            error_code=ErrorCode.UNKNOWN_ERROR,
            message="更新用户信息失败",
            details={"error": str(e)}
        )


@router.post("/change-password")
async def change_password(
    old_password: str,
    new_password: str,
    current_user: dict = Depends(get_current_user)
):
    """修改密码"""
    try:
        user_service.change_password(current_user["id"], old_password, new_password)
        
        return success_response(
            message="密码修改成功"
        )
        
    except ApiException as e:
        return error_response(
            error_code=e.error_code,
            message=e.message,
            details=e.details
        )
    except Exception as e:
        return error_response(
            error_code=ErrorCode.UNKNOWN_ERROR,
            message="修改密码失败",
            details={"error": str(e)}
        )


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """用户登出"""
    try:
        # 在实际应用中，这里应该将令牌加入黑名单
        # 为了简化，我们只返回成功消息
        
        return success_response(
            message="登出成功"
        )
        
    except Exception as e:
        return error_response(
            error_code=ErrorCode.UNKNOWN_ERROR,
            message="登出失败",
            details={"error": str(e)}
        )


# ============================================================================
# 管理员路由
# ============================================================================

@router.get("/users", response_model=dict)
async def list_users(
    page: int = 1,
    page_size: int = 10,
    search: Optional[str] = None,
    role: Optional[str] = None,
    current_user: dict = Depends(require_admin)
):
    """列出所有用户（管理员）"""
    try:
        # 这里应该从数据库获取用户列表
        # 为了简化，我们返回模拟数据
        
        users = [
            {
                "id": 1,
                "email": "admin@smartcourse.com",
                "username": "admin",
                "full_name": "系统管理员",
                "role": "admin",
                "is_active": True,
                "created_at": "2026-03-01T00:00:00Z",
                "updated_at": "2026-03-01T00:00:00Z"
            },
            {
                "id": 2,
                "email": "teacher@smartcourse.com",
                "username": "teacher",
                "full_name": "教师用户",
                "role": "teacher",
                "is_active": True,
                "created_at": "2026-03-01T00:00:00Z",
                "updated_at": "2026-03-01T00:00:00Z"
            },
            {
                "id": 3,
                "email": "student@smartcourse.com",
                "username": "student",
                "full_name": "学生用户",
                "role": "student",
                "is_active": True,
                "created_at": "2026-03-01T00:00:00Z",
                "updated_at": "2026-03-01T00:00:00Z"
            }
        ]
        
        # 应用筛选
        if role:
            users = [u for u in users if u["role"] == role]
        
        if search:
            search_lower = search.lower()
            users = [
                u for u in users 
                if search_lower in u["email"].lower() 
                or search_lower in u["username"].lower()
                or (u["full_name"] and search_lower in u["full_name"].lower())
            ]
        
        # 应用分页
        total = len(users)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_users = users[start:end]
        
        response_data = {
            "items": [create_user_response(u).dict() for u in paginated_users],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
        
        return success_response(
            data=response_data,
            message="获取用户列表成功"
        )
        
    except Exception as e:
        return error_response(
            error_code=ErrorCode.UNKNOWN_ERROR,
            message="获取用户列表失败",
            details={"error": str(e)}
        )


@router.get("/users/{user_id}", response_model=dict)
async def get_user_by_id(
    user_id: int,
    current_user: dict = Depends(require_admin)
):
    """获取用户详情（管理员）"""
    try:
        user_data = user_service.get_user_by_id(user_id)
        
        if not user_data:
            return error_response(
                error_code=ErrorCode.USER_NOT_FOUND,
                message="用户不存在"
            )
        
        user_response = create_user_response(user_data)
        
        return success_response(
            data=user_response.dict(),
            message="获取用户详情成功"
        )
        
    except Exception as e:
        return error_response(
            error_code=ErrorCode.UNKNOWN_ERROR,
            message="获取用户详情失败",
            details={"error": str(e)}
        )


@router.put("/users/{user_id}/activate")
async def activate_user(
    user_id: int,
    current_user: dict = Depends(require_admin)
):
    """激活用户（管理员）"""
    try:
        user_data = user_service.get_user_by_id(user_id)
        
        if not user_data:
            return error_response(
                error_code=ErrorCode.USER_NOT_FOUND,
                message="用户不存在"
            )
        
        # 激活用户
        user_data["is_active"] = True
        user_data["updated_at"] = "2026-03-01T00:00:00Z"  # 模拟更新时间
        
        return success_response(
            message="用户激活成功"
        )
        
    except Exception as e:
        return error_response(
            error_code=ErrorCode.UNKNOWN_ERROR,
            message="激活用户失败",
            details={"error": str(e)}
        )


@router.put("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    current_user: dict = Depends(require_admin)
):
    """禁用用户（管理员）"""
    try:
        user_data = user_service.get_user_by_id(user_id)
        
        if not user_data:
            return error_response(
                error_code=ErrorCode.USER_NOT_FOUND,
                message="用户不存在"
            )
        
        # 不能禁用自己
        if user_id == current_user["id"]:
            return error_response(
                error_code=ErrorCode.PERMISSION_DENIED,
                message="不能禁用自己的账户"
            )
        
        # 禁用用户
        user_data["is_active"] = False
        user_data["updated_at"] = "2026-03-01T00:00:00Z"  # 模拟更新时间
        
        return success_response(
            message="用户禁用成功"
        )
        
    except Exception as e:
        return error_response(
            error_code=ErrorCode.UNKNOWN_ERROR,
            message="禁用用户失败",
            details={"error": str(e)}
        )


# ============================================================================
# 健康检查
# ============================================================================

@router.get("/health")
async def auth_health():
    """认证服务健康检查"""
    return success_response(
        data={
            "status": "healthy",
            "service": "auth-service",
            "timestamp": "2026-03-01T00:00:00Z"
        },
        message="认证服务运行正常"
    )