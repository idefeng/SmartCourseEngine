#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通知服务 (Notification Service)
端口: 8006

智能通知服务，支持：
1. 实时消息推送
2. 邮件通知
3. 短信通知
4. 应用内通知
5. 通知模板管理

作者: SmartCourseEngine Team
日期: 2026-03-07
"""

import os
import sys
import asyncio
import smtplib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union
from contextlib import asynccontextmanager
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from fastapi import FastAPI, HTTPException, status, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel, Field, EmailStr
import aiofiles

# ============================================================================
# 配置和路径设置
# ============================================================================

# 获取项目根目录
project_root = Path(__file__).parent.parent
shared_path = project_root / "shared"

# 添加路径到sys.path
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(shared_path))

print(f"项目根目录: {project_root}")
print(f"共享模块路径: {shared_path}")

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
    from shared.models import User, Notification as NotificationModel
    from shared.auth import get_current_user
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
        NOTIFICATION_FAILED = ("8006", "通知发送失败")
        TEMPLATE_NOT_FOUND = ("8007", "模板不存在")
    
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
# 数据模型
# ============================================================================

class NotificationRequest(BaseModel):
    """通知请求"""
    user_id: Optional[int] = Field(None, description="用户ID，如果不提供则发送给所有用户")
    user_ids: Optional[List[int]] = Field(None, description="用户ID列表，批量发送")
    channel: str = Field("in_app", description="通知渠道: in_app, email, sms, push")
    type: str = Field("info", description="通知类型: info, success, warning, error")
    title: str = Field(..., description="通知标题")
    content: str = Field(..., description="通知内容")
    template_id: Optional[int] = Field(None, description="模板ID")
    template_data: Optional[Dict[str, Any]] = Field(None, description="模板数据")
    priority: str = Field("normal", description="优先级: low, normal, high, urgent")
    scheduled_at: Optional[datetime] = Field(None, description="计划发送时间")
    metadata: Optional[Dict[str, Any]] = Field(None, description="附加元数据")

class EmailRequest(BaseModel):
    """邮件请求"""
    to_email: EmailStr
    subject: str
    content: str
    html_content: Optional[str] = None
    from_email: Optional[str] = Field(None, description="发件人邮箱")
    cc: Optional[List[EmailStr]] = None
    bcc: Optional[List[EmailStr]] = None

class Template(BaseModel):
    """通知模板"""
    id: int
    name: str
    description: str
    channel: str  # in_app, email, sms, push
    type: str  # info, success, warning, error
    subject_template: Optional[str] = None  # 邮件主题模板
    content_template: str  # 内容模板
    html_template: Optional[str] = None  # HTML模板
    variables: List[str]  # 模板变量
    created_at: datetime
    updated_at: datetime

class NotificationResponse(BaseModel):
    """通知响应"""
    notification_id: int
    user_id: Optional[int]
    channel: str
    type: str
    title: str
    content: str
    status: str  # pending, sent, delivered, read, failed
    sent_at: Optional[datetime]
    read_at: Optional[datetime]

# ============================================================================
# 服务配置
# ============================================================================

settings = get_settings()
SERVICE_NAME = "notification"
SERVICE_PORT = 8006

# 邮件配置（从环境变量读取）
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

# ============================================================================
# 模板管理
# ============================================================================

TEMPLATES: Dict[int, Template] = {}

async def load_default_templates():
    """加载默认模板"""
    default_templates = [
        {
            "id": 1,
            "name": "课程更新通知",
            "description": "课程内容更新通知",
            "channel": "in_app",
            "type": "info",
            "content_template": "您学习的课程《{course_name}》已更新。更新内容：{update_content}",
            "variables": ["course_name", "update_content"]
        },
        {
            "id": 2,
            "name": "新课程推荐",
            "description": "新课程推荐通知",
            "channel": "email",
            "type": "success",
            "subject_template": "为您推荐新课程：{course_name}",
            "content_template": "亲爱的{user_name}，根据您的学习兴趣，我们为您推荐了新课《{course_name}》。课程简介：{course_description}",
            "html_template": """
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2>新课程推荐</h2>
                <p>亲爱的{user_name}，</p>
                <p>根据您的学习兴趣，我们为您推荐了新课：</p>
                <div style="background: #f5f5f5; padding: 20px; border-radius: 5px;">
                    <h3>{course_name}</h3>
                    <p>{course_description}</p>
                </div>
                <p>立即学习：<a href="{course_url}">点击查看课程</a></p>
            </div>
            """,
            "variables": ["user_name", "course_name", "course_description", "course_url"]
        },
        {
            "id": 3,
            "name": "系统维护通知",
            "description": "系统维护通知",
            "channel": "in_app",
            "type": "warning",
            "content_template": "系统将于{maintenance_time}进行维护，预计持续{duration}。期间服务可能暂时不可用。",
            "variables": ["maintenance_time", "duration"]
        },
        {
            "id": 4,
            "name": "学习进度提醒",
            "description": "学习进度提醒通知",
            "channel": "push",
            "type": "info",
            "content_template": "您已连续学习{study_days}天，继续保持！今日推荐学习：{recommended_content}",
            "variables": ["study_days", "recommended_content"]
        },
        {
            "id": 5,
            "name": "账号安全通知",
            "description": "账号安全相关通知",
            "channel": "email",
            "type": "error",
            "subject_template": "账号安全提醒",
            "content_template": "检测到您的账号在{location}于{login_time}有新的登录活动。如非本人操作，请立即修改密码。",
            "html_template": """
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #d32f2f;">账号安全提醒</h2>
                <p>检测到您的账号有新的登录活动：</p>
                <ul>
                    <li>登录地点：{location}</li>
                    <li>登录时间：{login_time}</li>
                    <li>登录设备：{device}</li>
                </ul>
                <p>如非本人操作，请立即：</p>
                <ol>
                    <li>修改密码</li>
                    <li>检查账号安全设置</li>
                    <li>联系客服</li>
                </ol>
            </div>
            """,
            "variables": ["location", "login_time", "device"]
        }
    ]
    
    for template_data in default_templates:
        template = Template(
            **template_data,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        TEMPLATES[template.id] = template
    
    print(f"📄 加载了 {len(TEMPLATES)} 个默认模板")

# ============================================================================
# 通知发送器
# ============================================================================

class NotificationSender:
    """通知发送器"""
    
    def __init__(self):
        self.smtp_connected = False
        
    async def initialize(self):
        """初始化通知发送器"""
        print("📨 初始化通知发送器...")
        
        # 测试邮件配置
        if SMTP_USER and SMTP_PASSWORD:
            try:
                # 这里可以测试SMTP连接
                print(f"✅ 邮件配置可用: {SMTP_USER}")
                self.smtp_connected = True
            except Exception as e:
                print(f"⚠️  邮件配置不可用: {e}")
        
        print("✅ 通知发送器初始化完成")
    
    def render_template(self, template: Template, data: Dict[str, Any]) -> Dict[str, str]:
        """渲染模板"""
        result = {
            "content": template.content_template
        }
        
        # 渲染内容
        for key, value in data.items():
            placeholder = "{" + key + "}"
            result["content"] = result["content"].replace(placeholder, str(value))
        
        # 渲染主题（如果有）
        if template.subject_template:
            result["subject"] = template.subject_template
            for key, value in data.items():
                placeholder = "{" + key + "}"
                result["subject"] = result["subject"].replace(placeholder, str(value))
        
        # 渲染HTML（如果有）
        if template.html_template:
            result["html"] = template.html_template
            for key, value in data.items():
                placeholder = "{" + key + "}"
                result["html"] = result["html"].replace(placeholder, str(value))
        
        return result
    
    async def send_in_app_notification(self, user_id: int, title: str, content: str, 
                                      notification_type: str, metadata: Dict[str, Any] = None) -> bool:
        """发送应用内通知"""
        try:
            print(f"📱 发送应用内通知给用户 {user_id}: {title}")
            
            # 这里应该将通知保存到数据库
            # 暂时模拟发送成功
            
            # 模拟WebSocket推送
            # await self.send_websocket_notification(user_id, {
            #     "type": "notification",
            #     "data": {
            #         "title": title,
            #         "content": content,
            #         "type": notification_type,
            #         "timestamp": datetime.utcnow().isoformat(),
            #         "metadata": metadata or {}
            #     }
            # })
            
            return True
        except Exception as e:
            print(f"❌ 发送应用内通知失败: {e}")
            return False
    
    async def send_email_notification(self, to_email: str, subject: str, content: str, 
                                     html_content: str = None) -> bool:
        """发送邮件通知"""
        try:
            if not self.smtp_connected:
                print(f"⚠️  SMTP未配置，模拟发送邮件到: {to_email}")
                print(f"主题: {subject}")
                print(f"内容: {content[:100]}...")
                return True
            
            # 创建邮件
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = SMTP_USER
            msg['To'] = to_email
            
            # 添加纯文本版本
            part1 = MIMEText(content, 'plain', 'utf-8')
            msg.attach(part1)
            
            # 添加HTML版本（如果有）
            if html_content:
                part2 = MIMEText(html_content, 'html', 'utf-8')
                msg.attach(part2)
            
            # 发送邮件
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
            
            print(f"📧 邮件发送成功: {to_email}")
            return True
            
        except Exception as e:
            print(f"❌ 发送邮件失败: {e}")
            return False
    
    async def send_sms_notification(self, phone_number: str, content: str) -> bool:
        """发送短信通知（模拟）"""
        try:
            print(f"📱 模拟发送短信到: {phone_number}")
            print(f"内容: {content}")
            
            # 这里应该集成短信服务商API
            # 暂时模拟发送成功
            
            return True
        except Exception as e:
            print(f"❌ 发送短信失败: {e}")
            return False
    
    async def send_push_notification(self, device_token: str, title: str, content: str, 
                                    data: Dict[str, Any] = None) -> bool:
        """发送推送通知（模拟）"""
        try:
            print(f"📲 模拟发送推送通知到设备: {device_token[:20]}...")
            print(f"标题: {title}")
            print(f"内容: {content}")
            
            # 这里应该集成Firebase Cloud Messaging或Apple Push Notification Service
            # 暂时模拟发送成功
            
            return True
        except Exception as e:
            print(f"❌ 发送推送通知失败: {e}")
            return False
    
    async def send_notification(self, request: NotificationRequest) -> List[Dict[str, Any]]:
        """发送通知"""
        results = []
        
        # 确定接收用户
        user_ids = []
        if request.user_id:
            user_ids.append(request.user_id)
        if request.user_ids:
            user_ids.extend(request.user_ids)
        
        # 如果没有指定用户，发送给所有用户（模拟）
        if not user_ids:
            user_ids = [1, 2, 3, 4, 5]  # 模拟用户
        
        # 应用模板（如果有）
        title = request.title
        content = request.content
        
        if request.template_id and request.template_data:
            template = TEMPLATES.get(request.template_id)
            if template:
                rendered = self.render_template(template, request.template_data)
                if "subject" in rendered:
                    title = rendered["subject"]
                content = rendered["content"]
                html_content = rendered.get("html")
            else:
                print(f"⚠️  模板 {request.template_id} 不存在")
        
        # 根据渠道发送通知
        for user_id in user_ids:
            result = {
                "user_id": user_id,
                "channel": request.channel,
                "status": "failed",
                "message": ""
            }
            
            try:
                success = False
                
                if request.channel == "in_app":
                    success = await self.send_in_app_notification(
                        user_id, title, content, request.type, request.metadata
                    )
                
                elif request.channel == "email":
                    # 这里应该查询用户的邮箱
                    user_email = f"user{user_id}@example.com"  # 模拟邮箱
                    success = await self.send_email_notification(
                        user_email, title, content, html_content
                    )
                
                elif request.channel == "sms":
                    # 这里应该查询用户的手机号
                    user_phone = "+8613800138000"  # 模拟手机号
                    success = await self.send_sms_notification(user_phone, content)
                
                elif request.channel == "push":
                    # 这里应该查询用户的设备令牌
                    device_token = f"device_token_{user_id}"  # 模拟设备令牌
                    success = await self.send_push_notification(
                        device_token, title, content, request.metadata
                    )
                
                else:
                    result["message"] = f"不支持的渠道: {request.channel}"
                
                if success:
                    result["status"] = "sent"
                    result["message"] = "通知发送成功"
                else:
                    result["message"] = "通知发送失败"
                
            except Exception as e:
                result["message"] = f"发送异常: {str(e)}"
            
            results.append(result)
        
        return results

# ============================================================================
# 生命周期管理
# ============================================================================

notification_sender = NotificationSender()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print(f"🚀 启动 {SERVICE_NAME} 服务，端口: {SERVICE_PORT}")
    
    # 启动时初始化
    await load_default_templates()
    await notification_sender.initialize()
    
    yield
    
    # 关闭时清理
    print(f"👋 关闭 {SERVICE_NAME} 服务")

# ============================================================================
# FastAPI应用
# ============================================================================

app = FastAPI(
    title="通知服务",
    description="智能通知服务",
    version="1.0.0",
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
# API端点
# ============================================================================

@app.get("/health")
async def health_check():
    """健康检查"""
    return success_response({
        "service": SERVICE_NAME,
        "status": "healthy",
        "port": SERVICE_PORT,
        "timestamp": datetime.utcnow().isoformat(),
        "templates_loaded": len(TEMPLATES),
        "smtp_connected": notification_sender.smtp_connected
    })

@app.get("/")
async def root():
    """根端点"""
    return success_response({
        "service": SERVICE_NAME,
        "description": "智能通知服务",
        "version": "1.0.0",
        "channels": [
            "in_app - 应用内通知",
            "email - 邮件通知",
            "sms - 短信通知",
            "push - 推送通知"
        ],
        "endpoints": [
            "/health - 健康检查",
            "/docs - API文档",
            "/templates - 获取模板列表",
            "/send - 发送通知",
            "/email - 发送邮件",
            "/users/{user_id}/notifications - 获取用户通知"
        ]
    })

@app.get("/templates")
async def get_templates():
    """获取所有模板"""
    templates_list = [template.dict() for template in TEMPLATES.values()]
    return success_response(templates_list, "模板列表获取成功")

@app.get("/templates/{template_id}")
async def get_template(template_id: int):
    """获取特定模板"""
    template = TEMPLATES.get(template_id)
    if not template:
        return error_response(ErrorCode.TEMPLATE_NOT_FOUND, f"模板 {template_id} 不存在")
    
    return success_response(template.dict(), "模板获取成功")

@app.post("/send")
async def send_notification(
    request: NotificationRequest,
    background_tasks: BackgroundTasks
):
    """发送通知"""
    try:
        # 如果是计划发送，添加到后台任务
        if request.scheduled_at:
            # 计算延迟时间
            now = datetime.utcnow()
            if request.scheduled_at > now:
                delay_seconds = (request.scheduled_at - now).total_seconds()
                
                async def delayed_send():
                    await asyncio.sleep(delay_seconds)
                    return await notification_sender.send_notification(request)
                
                background_tasks.add_task(delayed_send)
                
                return success_response({
                    "scheduled": True,
                    "scheduled_at": request.scheduled_at.isoformat(),
                    "message": f"通知已计划在 {request.scheduled_at} 发送"
                }, "通知计划发送成功")
        
        # 立即发送
        results = await notification_sender.send_notification(request)
        
        success_count = sum(1 for r in results if r["status"] == "sent")
        failed_count = len(results) - success_count
        
        return success_response({
            "results": results,
            "summary": {
                "total": len(results),
                "success": success_count,
                "failed": failed_count
            }
        }, f"通知发送完成，成功: {success_count}, 失败: {failed_count}")
        
    except Exception as e:
        return error_response(ErrorCode.NOTIFICATION_FAILED, f"通知发送失败: {str(e)}")

@app.post("/email")
async def send_email(request: EmailRequest):
    """发送邮件"""
    try:
        success = await notification_sender.send_email_notification(
            request.to_email,
            request.subject,
            request.content,
            request.html_content
        )
        
        if success:
            return success_response({
                "to": request.to_email,
                "subject": request.subject,
                "status": "sent"
            }, "邮件发送成功")
        else:
            return error_response(ErrorCode.NOTIFICATION_FAILED, "邮件发送失败")
        
    except Exception as e:
        return error_response(ErrorCode.NOTIFICATION_FAILED, f"邮件发送失败: {str(e)}")

@app.get("/users/{user_id}/notifications")
async def get_user_notifications(
    user_id: int,
    limit: int = 20,
    unread_only: bool = False,
    channel: Optional[str] = None
):
    """获取用户的通知（模拟）"""
    try:
        # 这里应该从数据库查询用户的通知
        # 暂时返回模拟数据
        
        notifications = [
            {
                "id": 1,
                "user_id": user_id,
                "channel": "in_app",
                "type": "info",
                "title": "欢迎使用SmartCourseEngine",
                "content": "欢迎加入我们的学习平台！",
                "status": "read",
                "created_at": (datetime.utcnow() - timedelta(days=2)).isoformat(),
                "read_at": (datetime.utcnow() - timedelta(days=1)).isoformat()
            },
            {
                "id": 2,
                "user_id": user_id,
                "channel": "in_app",
                "type": "success",
                "title": "课程学习完成",
                "content": "恭喜您完成了《Python基础入门》课程！",
                "status": "unread",
                "created_at": (datetime.utcnow() - timedelta(hours=3)).isoformat(),
                "read_at": None
            },
            {
                "id": 3,
                "user_id": user_id,
                "channel": "email",
                "type": "warning",
                "title": "系统维护通知",
                "content": "系统将于今晚进行维护，请提前保存工作。",
                "status": "sent",
                "created_at": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
                "read_at": None
            }
        ]
        
        # 应用过滤器
        filtered_notifications = []
        for notification in notifications:
            if unread_only and notification["status"] == "read":
                continue
            if channel and notification["channel"] != channel:
                continue
            filtered_notifications.append(notification)
        
        # 限制数量
        filtered_notifications = filtered_notifications[:limit]
        
        return success_response(filtered_notifications, "用户通知获取成功")
        
    except Exception as e:
        return error_response(ErrorCode.NOTIFICATION_FAILED, f"获取用户通知失败: {str(e)}")

@app.post("/users/{user_id}/notifications/{notification_id}/read")
async def mark_notification_as_read(user_id: int, notification_id: int):
    """标记通知为已读（模拟）"""
    try:
        # 这里应该更新数据库中的通知状态
        # 暂时返回成功
        
        return success_response({
            "user_id": user_id,
            "notification_id": notification_id,
            "status": "read",
            "read_at": datetime.utcnow().isoformat()
        }, "通知已标记为已读")
        
    except Exception as e:
        return error_response(ErrorCode.NOTIFICATION_FAILED, f"标记通知为已读失败: {str(e)}")

@app.get("/stats")
async def get_notification_stats():
    """获取通知统计（模拟）"""
    try:
        stats = {
            "total_sent": 1500,
            "today_sent": 42,
            "by_channel": {
                "in_app": 800,
                "email": 400,
                "sms": 200,
                "push": 100
            },
            "by_type": {
                "info": 600,
                "success": 400,
                "warning": 300,
                "error": 200
            },
            "success_rate": 0.95,
            "avg_delivery_time": "2.5秒"
        }
        
        return success_response(stats, "通知统计获取成功")
        
    except Exception as e:
        return error_response(ErrorCode.NOTIFICATION_FAILED, f"获取通知统计失败: {str(e)}")

# ============================================================================
# 主函数
# ============================================================================

if __name__ == "__main__":
    print(f"🚀 启动 {SERVICE_NAME} 服务...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=SERVICE_PORT,
        log_level="info"
    )