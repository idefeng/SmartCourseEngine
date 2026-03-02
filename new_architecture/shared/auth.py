#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户认证系统
==========

用户认证、授权和会话管理。

作者: SmartCourseEngine Team
日期: 2026-03-01
"""

import os
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field
from enum import Enum

# 尝试导入JWT库
try:
    from jose import jwt
    JWT_AVAILABLE = True
except ImportError:
    # 回退到pyjwt
    try:
        import jwt
        JWT_AVAILABLE = True
    except ImportError:
        JWT_AVAILABLE = False
        print("⚠️  JWT库未安装，认证功能将不可用")

from .api_response import ApiException, ErrorCode

# ============================================================================
# 配置
# ============================================================================

class AuthConfig:
    """认证配置"""
    
    # JWT配置
    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24小时
    REFRESH_TOKEN_EXPIRE_DAYS = 30  # 30天
    
    # 密码配置
    BCRYPT_ROUNDS = 12
    
    # 权限配置
    DEFAULT_ROLE = "user"
    ADMIN_ROLE = "admin"
    TEACHER_ROLE = "teacher"
    STUDENT_ROLE = "student"


# ============================================================================
# 数据模型
# ============================================================================

class UserRole(str, Enum):
    """用户角色"""
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"
    USER = "user"


class UserCreate(BaseModel):
    """用户创建模型"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = Field(None, max_length=100)
    role: UserRole = Field(default=UserRole.USER)


class UserLogin(BaseModel):
    """用户登录模型"""
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """用户更新模型"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = None


class UserResponse(BaseModel):
    """用户响应模型"""
    id: int
    email: str
    username: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TokenData(BaseModel):
    """Token数据模型"""
    user_id: int
    email: str
    role: UserRole
    exp: datetime


class TokenResponse(BaseModel):
    """Token响应模型"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


# ============================================================================
# 密码工具
# ============================================================================

class PasswordUtils:
    """密码工具类"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """哈希密码"""
        salt = bcrypt.gensalt(rounds=AuthConfig.BCRYPT_ROUNDS)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    
    @staticmethod
    def validate_password_strength(password: str) -> bool:
        """验证密码强度"""
        if len(password) < 8:
            return False
        
        # 检查是否包含数字
        if not any(char.isdigit() for char in password):
            return False
        
        # 检查是否包含字母
        if not any(char.isalpha() for char in password):
            return False
        
        # 检查是否包含特殊字符
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(char in special_chars for char in password):
            return False
        
        return True


# ============================================================================
# JWT工具
# ============================================================================

class JWTUtils:
    """JWT工具类"""
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """创建访问令牌"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=AuthConfig.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, AuthConfig.SECRET_KEY, algorithm=AuthConfig.ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """创建刷新令牌"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=AuthConfig.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, AuthConfig.SECRET_KEY, algorithm=AuthConfig.ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """验证令牌"""
        try:
            payload = jwt.decode(token, AuthConfig.SECRET_KEY, algorithms=[AuthConfig.ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise ApiException(
                error_code=ErrorCode.TOKEN_EXPIRED,
                message="Token已过期"
            )
        except jwt.InvalidTokenError:
            raise ApiException(
                error_code=ErrorCode.TOKEN_INVALID,
                message="无效的Token"
            )
    
    @staticmethod
    def decode_token(token: str) -> Optional[Dict[str, Any]]:
        """解码令牌（不验证过期）"""
        try:
            payload = jwt.decode(token, AuthConfig.SECRET_KEY, algorithms=[AuthConfig.ALGORITHM], options={"verify_exp": False})
            return payload
        except jwt.InvalidTokenError:
            return None
    
    @staticmethod
    def create_tokens(user_data: Dict[str, Any]) -> Dict[str, str]:
        """创建访问令牌和刷新令牌"""
        token_data = {
            "sub": str(user_data["id"]),
            "email": user_data["email"],
            "role": user_data["role"],
            "username": user_data["username"]
        }
        
        access_token = JWTUtils.create_access_token(token_data)
        refresh_token = JWTUtils.create_refresh_token(token_data)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": AuthConfig.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # 转换为秒
        }


# ============================================================================
# 权限检查
# ============================================================================

class PermissionChecker:
    """权限检查器"""
    
    @staticmethod
    def has_permission(user_role: UserRole, required_role: UserRole) -> bool:
        """检查用户是否有权限"""
        role_hierarchy = {
            UserRole.ADMIN: 4,
            UserRole.TEACHER: 3,
            UserRole.STUDENT: 2,
            UserRole.USER: 1
        }
        
        user_level = role_hierarchy.get(user_role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        return user_level >= required_level
    
    @staticmethod
    def is_admin(user_role: UserRole) -> bool:
        """检查是否是管理员"""
        return user_role == UserRole.ADMIN
    
    @staticmethod
    def is_teacher(user_role: UserRole) -> bool:
        """检查是否是教师"""
        return user_role in [UserRole.ADMIN, UserRole.TEACHER]
    
    @staticmethod
    def is_student(user_role: UserRole) -> bool:
        """检查是否是学生"""
        return user_role in [UserRole.ADMIN, UserRole.TEACHER, UserRole.STUDENT]
    
    @staticmethod
    def check_permission(user_role: UserRole, required_role: UserRole, action: str, resource: str):
        """检查权限，如果没有权限则抛出异常"""
        if not PermissionChecker.has_permission(user_role, required_role):
            raise ApiException(
                error_code=ErrorCode.PERMISSION_DENIED,
                message=f"没有权限执行 {action} 操作",
                details={"action": action, "resource": resource, "required_role": required_role}
            )


# ============================================================================
# 用户服务
# ============================================================================

class UserService:
    """用户服务"""
    
    def __init__(self, db):
        self.db = db
    
    def create_user(self, user_data: UserCreate) -> Dict[str, Any]:
        """创建用户"""
        # 检查邮箱是否已存在
        existing_user = self.get_user_by_email(user_data.email)
        if existing_user:
            raise ApiException(
                error_code=ErrorCode.USER_ALREADY_EXISTS,
                message="邮箱已被注册"
            )
        
        # 检查用户名是否已存在
        existing_username = self.get_user_by_username(user_data.username)
        if existing_username:
            raise ApiException(
                error_code=ErrorCode.USER_ALREADY_EXISTS,
                message="用户名已被使用"
            )
        
        # 验证密码强度
        if not PasswordUtils.validate_password_strength(user_data.password):
            raise ApiException(
                error_code=ErrorCode.VALIDATION_ERROR,
                message="密码强度不足，必须包含字母、数字和特殊字符，且长度至少8位"
            )
        
        # 哈希密码
        hashed_password = PasswordUtils.hash_password(user_data.password)
        
        # 创建用户
        user = {
            "email": user_data.email,
            "username": user_data.username,
            "password_hash": hashed_password,
            "full_name": user_data.full_name,
            "role": user_data.role.value,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # 保存到数据库（这里需要根据实际数据库实现）
        # user_id = self.db.save_user(user)
        # user["id"] = user_id
        
        # 模拟用户ID
        user["id"] = 1
        
        return user
    
    def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """用户认证"""
        user = self.get_user_by_email(email)
        if not user:
            return None
        
        if not PasswordUtils.verify_password(password, user["password_hash"]):
            return None
        
        if not user.get("is_active", True):
            raise ApiException(
                error_code=ErrorCode.PERMISSION_DENIED,
                message="用户账户已被禁用"
            )
        
        return user
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """通过邮箱获取用户"""
        # 这里需要根据实际数据库实现
        # 返回模拟数据
        if email == "admin@smartcourse.com":
            return {
                "id": 1,
                "email": "admin@smartcourse.com",
                "username": "admin",
                "full_name": "系统管理员",
                "password_hash": PasswordUtils.hash_password("Admin@123"),
                "role": UserRole.ADMIN.value,
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        return None
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """通过用户名获取用户"""
        # 这里需要根据实际数据库实现
        # 返回模拟数据
        if username == "admin":
            return {
                "id": 1,
                "email": "admin@smartcourse.com",
                "username": "admin",
                "full_name": "系统管理员",
                "password_hash": PasswordUtils.hash_password("Admin@123"),
                "role": UserRole.ADMIN.value,
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        return None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """通过ID获取用户"""
        # 这里需要根据实际数据库实现
        # 返回模拟数据
        if user_id == 1:
            return {
                "id": 1,
                "email": "admin@smartcourse.com",
                "username": "admin",
                "full_name": "系统管理员",
                "password_hash": PasswordUtils.hash_password("Admin@123"),
                "role": UserRole.ADMIN.value,
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        return None
    
    def update_user(self, user_id: int, update_data: UserUpdate) -> Dict[str, Any]:
        """更新用户信息"""
        user = self.get_user_by_id(user_id)
        if not user:
            raise ApiException(
                error_code=ErrorCode.USER_NOT_FOUND,
                message="用户不存在"
            )
        
        # 更新用户信息
        if update_data.username is not None:
            # 检查用户名是否已被其他用户使用
            existing = self.get_user_by_username(update_data.username)
            if existing and existing["id"] != user_id:
                raise ApiException(
                    error_code=ErrorCode.USER_ALREADY_EXISTS,
                    message="用户名已被使用"
                )
            user["username"] = update_data.username
        
        if update_data.full_name is not None:
            user["full_name"] = update_data.full_name
        
        if update_data.avatar_url is not None:
            user["avatar_url"] = update_data.avatar_url
        
        user["updated_at"] = datetime.utcnow()
        
        # 保存到数据库
        # self.db.update_user(user_id, user)
        
        return user
    
    def change_password(self, user_id: int, old_password: str, new_password: str):
        """修改密码"""
        user = self.get_user_by_id(user_id)
        if not user:
            raise ApiException(
                error_code=ErrorCode.USER_NOT_FOUND,
                message="用户不存在"
            )
        
        # 验证旧密码
        if not PasswordUtils.verify_password(old_password, user["password_hash"]):
            raise ApiException(
                error_code=ErrorCode.INVALID_CREDENTIALS,
                message="旧密码不正确"
            )
        
        # 验证新密码强度
        if not PasswordUtils.validate_password_strength(new_password):
            raise ApiException(
                error_code=ErrorCode.VALIDATION_ERROR,
                message="新密码强度不足，必须包含字母、数字和特殊字符，且长度至少8位"
            )
        
        # 更新密码
        new_password_hash = PasswordUtils.hash_password(new_password)
        user["password_hash"] = new_password_hash
        user["updated_at"] = datetime.utcnow()
        
        # 保存到数据库
        # self.db.update_user(user_id, user)


# ============================================================================
# 认证中间件
# ============================================================================

class AuthMiddleware:
    """认证中间件"""
    
    @staticmethod
    def get_current_user(token: str) -> Dict[str, Any]:
        """获取当前用户"""
        if not token:
            raise ApiException(
                error_code=ErrorCode.TOKEN_INVALID,
                message="缺少认证令牌"
            )
        
        # 验证令牌
        payload = JWTUtils.verify_token(token)
        
        # 获取用户信息
        user_id = int(payload.get("sub"))
        email = payload.get("email")
        role = payload.get("role")
        
        if not user_id or not email or not role:
            raise ApiException(
                error_code=ErrorCode.TOKEN_INVALID,
                message="无效的令牌数据"
            )
        
        # 这里应该从数据库获取用户信息
        # 为了简化，我们返回令牌中的数据
        return {
            "id": user_id,
            "email": email,
            "role": UserRole(role),
            "username": payload.get("username", "")
        }
    
    @staticmethod
    def require_auth(token: Optional[str] = None) -> Dict[str, Any]:
        """要求认证"""
        if not token:
            raise ApiException(
                error_code=ErrorCode.PERMISSION_DENIED,
                message="需要认证"
            )
        
        return AuthMiddleware.get_current_user(token)
    
    @staticmethod
    def require_role(token: Optional[str] = None, required_role: UserRole = UserRole.USER) -> Dict[str, Any]:
        """要求特定角色"""
        user = AuthMiddleware.require_auth(token)
        
        # 检查角色权限
        if not PermissionChecker.has_permission(user["role"], required_role):
            raise ApiException(
                error_code=ErrorCode.PERMISSION_DENIED,
                message=f"需要 {required_role.value} 角色权限"
            )
        
        return user


# ============================================================================
# 工具函数
# ============================================================================

def create_user_response(user_data: Dict[str, Any]) -> UserResponse:
    """创建用户响应"""
    return UserResponse(
        id=user_data["id"],
        email=user_data["email"],
        username=user_data["username"],
        full_name=user_data.get("full_name"),
        avatar_url=user_data.get("avatar_url"),
        role=UserRole(user_data["role"]),
        is_active=user_data.get("is_active", True),
        created_at=user_data["created_at"],
        updated_at=user_data["updated_at"]
    )


def create_token_response(user_data: Dict[str, Any]) -> TokenResponse:
    """创建令牌响应"""
    tokens = JWTUtils.create_tokens(user_data)
    
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        expires_in=tokens["expires_in"],
        user=create_user_response(user_data)
    )


# ============================================================================
# FastAPI依赖项
# ============================================================================

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """获取当前用户（FastAPI依赖项）"""
    try:
        return AuthMiddleware.get_current_user(credentials.credentials)
    except ApiException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"}
        )


def get_current_active_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """获取当前活跃用户"""
    if not current_user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户账户已被禁用"
        )
    return current_user


def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """要求管理员权限"""
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user


def require_teacher(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """要求教师权限"""
    if current_user["role"] not in [UserRole.ADMIN, UserRole.TEACHER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要教师权限"
        )
    return current_user


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    # 测试密码工具
    password = "Test@1234"
    hashed = PasswordUtils.hash_password(password)
    print(f"原始密码: {password}")
    print(f"哈希密码: {hashed}")
    print(f"验证密码: {PasswordUtils.verify_password(password, hashed)}")
    
    # 测试JWT工具
    user_data = {
        "id": 1,
        "email": "test@example.com",
        "username": "testuser",
        "role": UserRole.USER.value
    }
    
    tokens = JWTUtils.create_tokens(user_data)
    print(f"\n访问令牌: {tokens['access_token'][:50]}...")
    print(f"刷新令牌: {tokens['refresh_token'][:50]}...")
    
    # 测试令牌验证
    try:
        payload = JWTUtils.verify_token(tokens["access_token"])
        print(f"\n令牌验证成功: {payload}")
    except Exception as e:
        print(f"\n令牌验证失败: {e}")
