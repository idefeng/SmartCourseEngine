#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket实时通信服务
==================

实时消息推送、视频分析进度通知、在线状态管理。

作者: SmartCourseEngine Team
日期: 2026-03-01
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect

# ============================================================================
# 消息类型定义
# ============================================================================

class MessageType(str, Enum):
    """消息类型枚举"""
    # 系统消息
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    PING = "ping"
    PONG = "pong"
    ERROR = "error"
    
    # 用户消息
    USER_ONLINE = "user_online"
    USER_OFFLINE = "user_offline"
    USER_TYPING = "user_typing"
    USER_MESSAGE = "user_message"
    
    # 视频处理
    VIDEO_UPLOAD_PROGRESS = "video_upload_progress"
    VIDEO_ANALYSIS_STARTED = "video_analysis_started"
    VIDEO_ANALYSIS_PROGRESS = "video_analysis_progress"
    VIDEO_ANALYSIS_COMPLETED = "video_analysis_completed"
    VIDEO_ANALYSIS_FAILED = "video_analysis_failed"
    
    # 知识处理
    KNOWLEDGE_EXTRACTION_STARTED = "knowledge_extraction_started"
    KNOWLEDGE_EXTRACTION_PROGRESS = "knowledge_extraction_progress"
    KNOWLEDGE_EXTRACTION_COMPLETED = "knowledge_extraction_completed"
    KNOWLEDGE_GRAPH_UPDATED = "knowledge_graph_updated"
    
    # 系统通知
    SYSTEM_NOTIFICATION = "system_notification"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"


@dataclass
class WebSocketMessage:
    """WebSocket消息数据类"""
    type: MessageType
    data: Dict[str, Any]
    timestamp: str
    message_id: Optional[str] = None
    user_id: Optional[int] = None
    
    def __post_init__(self):
        if self.message_id is None:
            self.message_id = str(uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


# ============================================================================
# 连接管理器
# ============================================================================

class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[int, Set[str]] = {}
        self.connection_users: Dict[str, int] = {}
        self.logger = logging.getLogger(__name__)
    
    async def connect(self, websocket: WebSocket, connection_id: str, user_id: Optional[int] = None):
        """连接WebSocket"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        
        if user_id:
            self.connection_users[connection_id] = user_id
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)
            
            # 通知用户上线
            await self.broadcast_to_user(
                user_id,
                MessageType.USER_ONLINE,
                {"user_id": user_id, "connection_id": connection_id}
            )
        
        self.logger.info(f"WebSocket连接建立: {connection_id}, 用户: {user_id}")
    
    def disconnect(self, connection_id: str):
        """断开WebSocket连接"""
        websocket = self.active_connections.pop(connection_id, None)
        
        if connection_id in self.connection_users:
            user_id = self.connection_users.pop(connection_id)
            if user_id in self.user_connections:
                self.user_connections[user_id].remove(connection_id)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
        
        self.logger.info(f"WebSocket连接断开: {connection_id}")
    
    async def send_personal_message(self, message: WebSocketMessage, connection_id: str):
        """发送个人消息"""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_text(message.to_json())
                self.logger.debug(f"发送消息到 {connection_id}: {message.type}")
            except Exception as e:
                self.logger.error(f"发送消息失败 {connection_id}: {e}")
                self.disconnect(connection_id)
    
    async def send_to_user(self, user_id: int, message_type: MessageType, data: Dict[str, Any]):
        """发送消息给特定用户"""
        if user_id in self.user_connections:
            message = WebSocketMessage(
                type=message_type,
                data=data,
                timestamp=datetime.utcnow().isoformat()
            )
            
            for connection_id in list(self.user_connections[user_id]):
                await self.send_personal_message(message, connection_id)
    
    async def broadcast_to_user(self, user_id: int, message_type: MessageType, data: Dict[str, Any]):
        """广播消息给特定用户（不包括自己）"""
        message = WebSocketMessage(
            type=message_type,
            data=data,
            timestamp=datetime.utcnow().isoformat()
        )
        
        for connection_id, conn_user_id in list(self.connection_users.items()):
            if conn_user_id != user_id:
                await self.send_personal_message(message, connection_id)
    
    async def broadcast(self, message_type: MessageType, data: Dict[str, Any]):
        """广播消息给所有连接"""
        message = WebSocketMessage(
            type=message_type,
            data=data,
            timestamp=datetime.utcnow().isoformat()
        )
        
        for connection_id in list(self.active_connections.keys()):
            await self.send_personal_message(message, connection_id)
    
    def get_online_users(self) -> List[int]:
        """获取在线用户列表"""
        return list(self.user_connections.keys())
    
    def get_user_connections(self, user_id: int) -> List[str]:
        """获取用户的连接ID列表"""
        return list(self.user_connections.get(user_id, set()))
    
    def is_user_online(self, user_id: int) -> bool:
        """检查用户是否在线"""
        return user_id in self.user_connections and len(self.user_connections[user_id]) > 0


# ============================================================================
# 消息处理器
# ============================================================================

class MessageHandler:
    """消息处理器"""
    
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager
        self.logger = logging.getLogger(__name__)
    
    async def handle_message(self, connection_id: str, message_data: Dict[str, Any]):
        """处理接收到的消息"""
        try:
            message_type = MessageType(message_data.get("type"))
            data = message_data.get("data", {})
            user_id = data.get("user_id")
            
            self.logger.debug(f"处理消息: {message_type}, 连接: {connection_id}")
            
            # 根据消息类型处理
            if message_type == MessageType.PING:
                await self.handle_ping(connection_id)
            elif message_type == MessageType.USER_TYPING:
                await self.handle_user_typing(connection_id, data)
            elif message_type == MessageType.USER_MESSAGE:
                await self.handle_user_message(connection_id, data)
            else:
                self.logger.warning(f"未知消息类型: {message_type}")
                
        except ValueError as e:
            self.logger.error(f"消息类型错误: {e}")
            await self.send_error(connection_id, "无效的消息类型")
        except Exception as e:
            self.logger.error(f"处理消息失败: {e}")
            await self.send_error(connection_id, "处理消息失败")
    
    async def handle_ping(self, connection_id: str):
        """处理Ping消息"""
        message = WebSocketMessage(
            type=MessageType.PONG,
            data={"timestamp": datetime.utcnow().isoformat()},
            timestamp=datetime.utcnow().isoformat()
        )
        await self.connection_manager.send_personal_message(message, connection_id)
    
    async def handle_user_typing(self, connection_id: str, data: Dict[str, Any]):
        """处理用户正在输入"""
        user_id = data.get("user_id")
        chat_id = data.get("chat_id")
        
        if user_id and chat_id:
            # 广播给聊天室的其他用户
            await self.connection_manager.broadcast_to_user(
                user_id,
                MessageType.USER_TYPING,
                {"user_id": user_id, "chat_id": chat_id}
            )
    
    async def handle_user_message(self, connection_id: str, data: Dict[str, Any]):
        """处理用户消息"""
        user_id = data.get("user_id")
        chat_id = data.get("chat_id")
        content = data.get("content")
        
        if user_id and chat_id and content:
            # 广播给聊天室的所有用户
            message_data = {
                "user_id": user_id,
                "chat_id": chat_id,
                "content": content,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.connection_manager.broadcast(
                MessageType.USER_MESSAGE,
                message_data
            )
    
    async def send_error(self, connection_id: str, error_message: str):
        """发送错误消息"""
        message = WebSocketMessage(
            type=MessageType.ERROR,
            data={"message": error_message},
            timestamp=datetime.utcnow().isoformat()
        )
        await self.connection_manager.send_personal_message(message, connection_id)


# ============================================================================
# 任务进度跟踪器
# ============================================================================

class TaskProgressTracker:
    """任务进度跟踪器"""
    
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)
    
    def create_task(self, task_id: str, task_type: str, user_id: int, metadata: Dict[str, Any] = None):
        """创建新任务"""
        self.tasks[task_id] = {
            "task_id": task_id,
            "task_type": task_type,
            "user_id": user_id,
            "status": "pending",
            "progress": 0,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        self.logger.info(f"创建任务: {task_id}, 类型: {task_type}, 用户: {user_id}")
    
    async def update_progress(self, task_id: str, progress: int, message: str = None):
        """更新任务进度"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task["progress"] = progress
            task["updated_at"] = datetime.utcnow().isoformat()
            
            if progress < 100:
                task["status"] = "processing"
            
            # 发送进度通知
            await self.connection_manager.send_to_user(
                task["user_id"],
                MessageType.VIDEO_ANALYSIS_PROGRESS,
                {
                    "task_id": task_id,
                    "task_type": task["task_type"],
                    "progress": progress,
                    "message": message,
                    "metadata": task["metadata"]
                }
            )
            
            self.logger.debug(f"任务进度更新: {task_id}, 进度: {progress}%")
    
    async def complete_task(self, task_id: str, result: Dict[str, Any] = None):
        """完成任务"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task["status"] = "completed"
            task["progress"] = 100
            task["updated_at"] = datetime.utcnow().isoformat()
            task["result"] = result or {}
            
            # 发送完成通知
            await self.connection_manager.send_to_user(
                task["user_id"],
                MessageType.TASK_COMPLETED,
                {
                    "task_id": task_id,
                    "task_type": task["task_type"],
                    "result": task["result"],
                    "metadata": task["metadata"]
                }
            )
            
            self.logger.info(f"任务完成: {task_id}")
    
    async def fail_task(self, task_id: str, error: str, details: Dict[str, Any] = None):
        """任务失败"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task["status"] = "failed"
            task["updated_at"] = datetime.utcnow().isoformat()
            task["error"] = error
            task["error_details"] = details or {}
            
            # 发送失败通知
            await self.connection_manager.send_to_user(
                task["user_id"],
                MessageType.TASK_FAILED,
                {
                    "task_id": task_id,
                    "task_type": task["task_type"],
                    "error": error,
                    "error_details": task["error_details"],
                    "metadata": task["metadata"]
                }
            )
            
            self.logger.error(f"任务失败: {task_id}, 错误: {error}")
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务信息"""
        return self.tasks.get(task_id)
    
    def get_user_tasks(self, user_id: int) -> List[Dict[str, Any]]:
        """获取用户的任务列表"""
        return [
            task for task in self.tasks.values()
            if task["user_id"] == user_id
        ]


# ============================================================================
# WebSocket服务
# ============================================================================

class WebSocketService:
    """WebSocket服务"""
    
    def __init__(self):
        self.connection_manager = ConnectionManager()
        self.message_handler = MessageHandler(self.connection_manager)
        self.task_tracker = TaskProgressTracker(self.connection_manager)
        self.logger = logging.getLogger(__name__)
    
    async def handle_connection(self, websocket: WebSocket, connection_id: str, user_id: Optional[int] = None):
        """处理WebSocket连接"""
        await self.connection_manager.connect(websocket, connection_id, user_id)
        
        try:
            while True:
                # 接收消息
                data = await websocket.receive_text()
                
                try:
                    message_data = json.loads(data)
                    await self.message_handler.handle_message(connection_id, message_data)
                except json.JSONDecodeError:
                    self.logger.error(f"JSON解析失败: {data}")
                    await self.message_handler.send_error(connection_id, "无效的JSON格式")
                
        except WebSocketDisconnect:
            self.logger.info(f"WebSocket连接断开: {connection_id}")
        except Exception as e:
            self.logger.error(f"WebSocket连接错误: {e}")
        finally:
            self.connection_manager.disconnect(connection_id)
    
    async def send_video_upload_progress(self, user_id: int, task_id: str, progress: int, file_name: str):
        """发送视频上传进度"""
        await self.connection_manager.send_to_user(
            user_id,
            MessageType.VIDEO_UPLOAD_PROGRESS,
            {
                "task_id": task_id,
                "progress": progress,
                "file_name": file_name,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def send_video_analysis_started(self, user_id: int, task_id: str, video_id: str):
        """发送视频分析开始通知"""
        await self.connection_manager.send_to_user(
            user_id,
            MessageType.VIDEO_ANALYSIS_STARTED,
            {
                "task_id": task_id,
                "video_id": video_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def send_system_notification(self, user_id: int, title: str, message: str, level: str = "info"):
        """发送系统通知"""
        await self.connection_manager.send_to_user(
            user_id,
            MessageType.SYSTEM_NOTIFICATION,
            {
                "title": title,
                "message": message,
                "level": level,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    def create_video_analysis_task(self, task_id: str, user_id: int, video_id: str, video_name: str):
        """创建视频分析任务"""
        self.task_tracker.create_task(
            task_id=task_id,
            task_type="video_analysis",
            user_id=user_id,
            metadata={
                "video_id": video_id,
                "video_name": video_name,
                "stages": ["upload", "transcription", "keyframe", "scene", "knowledge"]
            }
        )
    
    async def update_video_analysis_progress(self, task_id: str, progress: int, stage: str, message: str = None):
        """更新视频分析进度"""
        await self.task_tracker.update_progress(task_id, progress, message)
    
    async def complete_video_analysis(self, task_id: str, result: Dict[str, Any]):
        """完成视频分析"""
        await self.task_tracker.complete_task(task_id, result)
    
    async def fail_video_analysis(self, task_id: str, error: str, details: Dict[str, Any] = None):
        """视频分析失败"""
        await self.task_tracker.fail_task(task_id, error, details)


# ============================================================================
# 全局实例
# ============================================================================

# 创建全局WebSocket服务实例
websocket_service = WebSocketService()


# ============================================================================
# FastAPI路由
# ============================================================================

from fastapi import APIRouter, WebSocket, Depends, Query
from typing import Optional
import uuid

# 创建WebSocket路由
router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None)
):
    """WebSocket端点"""
    connection_id = str(uuid.uuid4())
    
    # 这里应该验证token并获取用户ID
    # 为了简化，我们直接使用传入的user_id
    
    await websocket_service.handle_connection(
        websocket=websocket,
        connection_id=connection_id,
        user_id=user_id
    )


@router.get("/ws/online-users")
async def get_online_users():
    """获取在线用户列表"""
    online_users = websocket_service.connection_manager.get_online_users()
    return {
        "success": True,
        "data": {
            "online_users": online_users,
            "total": len(online_users),
            "timestamp": datetime.utcnow().isoformat()
        },
        "message": "获取在线用户成功"
    }


@router.get("/ws/user-tasks/{user_id}")
async def get_user_tasks(user_id: int):
    """获取用户的任务列表"""
    tasks = websocket_service.task_tracker.get_user_tasks(user_id)
    return {
        "success": True,
        "data": {
            "tasks": tasks,
            "total": len(tasks),
            "timestamp": datetime.utcnow().isoformat()
        },
        "message": "获取用户任务成功"
    }


# ============================================================================
# 工具函数
# ============================================================================

def get_websocket_service() -> WebSocketService:
    """获取WebSocket服务实例"""
    return websocket_service


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test_websocket():
        """测试WebSocket服务"""
        print("测试WebSocket服务...")
        
        # 创建服务实例
        service = WebSocketService()
        
        # 测试任务创建和进度更新
        task_id = "test_task_001"
        user_id = 1
        
        service.create_video_analysis_task(
            task_id=task_id,
            user_id=user_id,
            video_id="video_001",
            video_name="test_video.mp4"
        )
        
        print(f"创建任务: {task_id}")
        
        # 模拟进度更新
        for progress in [10, 30, 60, 90, 100]:
            await service.update_video_analysis_progress(
                task_id=task_id,
                progress=progress,
                stage="processing",
                message=f"处理进度: {progress}%"
            )
            print(f"更新进度: {progress}%")
            await asyncio.sleep(0.5)
        
        # 完成任务
        await service.complete_video_analysis(
            task_id=task_id,
            result={
                "video_id": "video_001",
                "analysis_result": "success",
                "duration": 300,
                "keyframes": 50,
                "scenes": 10
            }
        )
        
        print("任务完成")
        
        # 获取任务信息
        task = service.task_tracker.get_task(task_id)
        print(f"任务信息: {task}")
    
    # 运行测试
    asyncio.run(test_websocket())