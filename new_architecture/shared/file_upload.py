#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件上传服务
==========

支持分片上传、断点续传、进度跟踪的文件上传服务。

作者: SmartCourseEngine Team
日期: 2026-03-01
"""

import os
import hashlib
import json
import shutil
import asyncio
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Tuple, BinaryIO
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import logging

from .websocket import websocket_service, MessageType
try:
    from .task_queue import publish_video_analysis_task
except ImportError:
    from shared.task_queue import publish_video_analysis_task
try:
    from .auth import get_current_user
except ImportError:
    # Fallback for when running as standalone script or different context
    from shared.auth import get_current_user


# ============================================================================
# 配置
# ============================================================================

class UploadConfig:
    """上传配置"""
    
    # 上传目录
    UPLOAD_DIR = "uploads"
    TEMP_DIR = "uploads/temp"
    CHUNK_DIR = "uploads/chunks"
    
    # 文件大小限制
    MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024  # 10GB
    MAX_CHUNK_SIZE = 10 * 1024 * 1024  # 10MB
    MIN_CHUNK_SIZE = 1 * 1024 * 1024  # 1MB
    
    # 支持的文件类型
    ALLOWED_EXTENSIONS = {
        # 视频文件
        'mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv', 'webm', 'm4v',
        # 音频文件
        'mp3', 'wav', 'ogg', 'flac', 'aac',
        # 文档文件
        'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx',
        # 图片文件
        'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp',
        # 其他
        'txt', 'md', 'json', 'xml', 'csv'
    }
    
    # 视频文件类型
    VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv', 'webm', 'm4v'}
    
    # 清理配置
    CLEANUP_DAYS = 7  # 清理7天前的临时文件


class UploadStatus(str, Enum):
    """上传状态枚举"""
    PENDING = "pending"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    # 兼容性处理：允许直接作为字符串使用
    def __str__(self):
        return self.value


@dataclass
class UploadMetadata:
    """上传元数据"""
    upload_id: str
    file_name: str
    file_size: int
    file_hash: str
    chunk_size: int
    total_chunks: int
    uploaded_chunks: List[int]
    status: UploadStatus
    user_id: int
    created_at: str
    updated_at: str
    file_path: Optional[str] = None
    file_type: Optional[str] = None
    metadata: Optional[Dict[str, any]] = None
    
    def __post_init__(self):
        if self.file_type is None:
            self.file_type = self._detect_file_type()
    
    def _detect_file_type(self) -> str:
        """检测文件类型"""
        ext = self.file_name.split('.')[-1].lower() if '.' in self.file_name else ''
        
        if ext in UploadConfig.VIDEO_EXTENSIONS:
            return "video"
        elif ext in {'mp3', 'wav', 'ogg', 'flac', 'aac'}:
            return "audio"
        elif ext in {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'}:
            return "image"
        elif ext in {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx'}:
            return "document"
        else:
            return "other"
    
    def to_dict(self) -> Dict[str, any]:
        """转换为字典"""
        return asdict(self)
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


# ============================================================================
# 文件工具
# ============================================================================

class FileUtils:
    """文件工具类"""
    
    @staticmethod
    def calculate_file_hash(file_path: Path, chunk_size: int = 8192) -> str:
        """计算文件哈希值"""
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(chunk_size), b""):
                sha256_hash.update(byte_block)
        
        return sha256_hash.hexdigest()
    
    @staticmethod
    def calculate_chunk_hash(chunk_data: bytes) -> str:
        """计算分片哈希值"""
        return hashlib.sha256(chunk_data).hexdigest()
    
    @staticmethod
    def get_file_extension(file_name: str) -> str:
        """获取文件扩展名"""
        return file_name.split('.')[-1].lower() if '.' in file_name else ''
    
    @staticmethod
    def is_allowed_file(file_name: str) -> bool:
        """检查文件类型是否允许"""
        ext = FileUtils.get_file_extension(file_name)
        return ext in UploadConfig.ALLOWED_EXTENSIONS
    
    @staticmethod
    def is_video_file(file_name: str) -> bool:
        """检查是否是视频文件"""
        ext = FileUtils.get_file_extension(file_name)
        return ext in UploadConfig.VIDEO_EXTENSIONS

    @staticmethod
    def normalize_file_name(file_name: str) -> str:
        base = Path(file_name).name
        stem = Path(base).stem
        suffix = Path(base).suffix.lower()
        normalized = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode("ascii")
        safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", normalized).strip("._")
        if not safe_stem:
            safe_stem = "file"
        safe_suffix = re.sub(r"[^A-Za-z0-9.]+", "", suffix)
        return f"{safe_stem}{safe_suffix}"
    
    @staticmethod
    def create_directory(path: Path):
        """创建目录"""
        path.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def cleanup_old_files(directory: Path, days: int):
        """清理旧文件"""
        cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        for file_path in directory.glob("**/*"):
            if file_path.is_file():
                if file_path.stat().st_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        logging.info(f"清理文件: {file_path}")
                    except Exception as e:
                        logging.error(f"清理文件失败 {file_path}: {e}")


# ============================================================================
# 分片上传管理器
# ============================================================================

class ChunkedUploadManager:
    """分片上传管理器"""
    
    def __init__(self, upload_dir: Path = None):
        self.upload_dir = upload_dir or Path(UploadConfig.UPLOAD_DIR)
        self.temp_dir = self.upload_dir / "temp"
        self.chunk_dir = self.upload_dir / "chunks"
        
        # 创建目录
        FileUtils.create_directory(self.upload_dir)
        FileUtils.create_directory(self.temp_dir)
        FileUtils.create_directory(self.chunk_dir)
        
        # 上传任务存储
        self.uploads: Dict[str, UploadMetadata] = {}
        self.logger = logging.getLogger(__name__)
    
    def init_upload(self, upload_id: str, file_name: str, file_size: int, 
                   chunk_size: int, user_id: int, metadata: Dict[str, any] = None) -> UploadMetadata:
        """初始化上传任务"""
        
        # 验证文件大小
        if file_size > UploadConfig.MAX_FILE_SIZE:
            raise ValueError(f"文件大小超过限制: {file_size} > {UploadConfig.MAX_FILE_SIZE}")
        
        # 验证文件类型
        if not FileUtils.is_allowed_file(file_name):
            raise ValueError(f"不支持的文件类型: {file_name}")
        
        # 计算分片数量
        total_chunks = (file_size + chunk_size - 1) // chunk_size
        
        # 创建上传元数据
        upload_metadata = UploadMetadata(
            upload_id=upload_id,
            file_name=file_name,
            file_size=file_size,
            file_hash="",  # 将在合并时计算
            chunk_size=chunk_size,
            total_chunks=total_chunks,
            uploaded_chunks=[],
            status=UploadStatus.PENDING,
            user_id=user_id,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
            metadata=metadata or {}
        )
        
        # 保存上传任务
        self.uploads[upload_id] = upload_metadata
        self._save_upload_metadata(upload_metadata)
        
        self.logger.info(f"初始化上传任务: {upload_id}, 文件: {file_name}, 大小: {file_size}, 分片: {total_chunks}")
        
        return upload_metadata
    
    async def upload_chunk(self, upload_id: str, chunk_index: int, chunk_data: bytes, 
                          chunk_hash: str = None) -> UploadMetadata:
        """上传分片"""
        
        if upload_id not in self.uploads:
            raise ValueError(f"上传任务不存在: {upload_id}")
        
        upload = self.uploads[upload_id]
        
        # 验证分片索引
        if chunk_index < 0 or chunk_index >= upload.total_chunks:
            raise ValueError(f"无效的分片索引: {chunk_index}")
        
        # 验证分片大小
        if len(chunk_data) > UploadConfig.MAX_CHUNK_SIZE:
            raise ValueError(f"分片大小超过限制: {len(chunk_data)} > {UploadConfig.MAX_CHUNK_SIZE}")
        
        # 验证分片哈希（如果提供）
        if chunk_hash and FileUtils.calculate_chunk_hash(chunk_data) != chunk_hash:
            raise ValueError("分片哈希验证失败")
        
        # 保存分片文件
        chunk_file = self.chunk_dir / f"{upload_id}_{chunk_index}.chunk"
        with open(chunk_file, "wb") as f:
            f.write(chunk_data)
        
        # 更新上传状态
        if chunk_index not in upload.uploaded_chunks:
            upload.uploaded_chunks.append(chunk_index)
            upload.uploaded_chunks.sort()
        
        upload.status = UploadStatus.UPLOADING
        upload.updated_at = datetime.utcnow().isoformat()
        
        # 保存元数据
        self._save_upload_metadata(upload)
        
        # 计算进度
        progress = int((len(upload.uploaded_chunks) / upload.total_chunks) * 100)
        
        # 发送进度通知
        await websocket_service.send_video_upload_progress(
            user_id=upload.user_id,
            task_id=upload_id,
            progress=progress,
            file_name=upload.file_name
        )
        
        self.logger.debug(f"上传分片: {upload_id}, 分片: {chunk_index}, 进度: {progress}%")
        
        return upload
    
    async def complete_upload(self, upload_id: str) -> UploadMetadata:
        """完成上传并合并文件"""
        
        if upload_id not in self.uploads:
            raise ValueError(f"上传任务不存在: {upload_id}")
        
        upload = self.uploads[upload_id]
        
        # 检查是否所有分片都已上传
        if len(upload.uploaded_chunks) != upload.total_chunks:
            raise ValueError(f"分片不完整: {len(upload.uploaded_chunks)}/{upload.total_chunks}")
        
        # 更新状态
        upload.status = UploadStatus.PROCESSING
        upload.updated_at = datetime.utcnow().isoformat()
        self._save_upload_metadata(upload)
        
        # 发送处理开始通知
        await websocket_service.send_video_analysis_started(
            user_id=upload.user_id,
            task_id=upload_id,
            video_id=upload_id
        )
        
        # 合并分片文件
        temp_file = self.temp_dir / f"{upload_id}_{upload.file_name}"
        
        try:
            with open(temp_file, "wb") as output_file:
                for chunk_index in range(upload.total_chunks):
                    chunk_file = self.chunk_dir / f"{upload_id}_{chunk_index}.chunk"
                    
                    with open(chunk_file, "rb") as input_file:
                        shutil.copyfileobj(input_file, output_file)
                    
                    # 清理分片文件
                    chunk_file.unlink()
            
            # 计算文件哈希
            upload.file_hash = FileUtils.calculate_file_hash(temp_file)
            
            # 生成最终文件名
            normalized_file_name = FileUtils.normalize_file_name(upload.file_name)
            final_file_name = f"{upload.file_hash[:8]}_{normalized_file_name}"
            final_file_path = self.upload_dir / final_file_name
            
            # 移动文件到最终位置
            shutil.move(temp_file, final_file_path)
            
            # 更新上传状态
            upload.status = UploadStatus.PROCESSING
            upload.file_path = str(final_file_path.resolve())
            upload.updated_at = datetime.utcnow().isoformat()
            self._save_upload_metadata(upload)

            task_info = await publish_video_analysis_task(
                {
                    "task_id": upload_id,
                    "upload_id": upload_id,
                    "user_id": upload.user_id,
                    "file_name": upload.file_name,
                    "file_path": upload.file_path,
                    "file_hash": upload.file_hash,
                    "metadata": upload.metadata or {},
                }
            )
            upload.metadata = upload.metadata or {}
            upload.metadata["queue_task"] = task_info
            self._save_upload_metadata(upload)
            
            self.logger.info(f"上传完成并入队: {upload_id}, 队列: {task_info['queue']}")
            
            return upload
            
        except Exception as e:
            # 上传失败
            upload.status = UploadStatus.FAILED
            upload.updated_at = datetime.utcnow().isoformat()
            self._save_upload_metadata(upload)
            
            self.logger.error(f"上传失败 {upload_id}: {e}")
            raise

    async def _run_post_upload_pipeline(self, upload_id: str):
        """
        上传后处理流程
        注意：实时的分析和知识提取进度现在由 VideoAnalysisWorker 通过内部 API 推送到网关。
        此方法现在仅用于初始化 WebSocket 任务追踪。
        """
        upload = self.uploads.get(upload_id)
        if not upload:
            return

        try:
            # 仅初始化任务追踪，不进行模拟更新
            websocket_service.create_video_analysis_task(
                task_id=upload_id,
                user_id=upload.user_id,
                video_id=upload_id,
                video_name=upload.file_name
            )
            
            self.logger.info(f"已初始化 WebSocket 任务追踪: {upload_id}")
            
        except Exception as e:
            self.logger.error(f"初始化 WebSoket 追踪失败 {upload_id}: {e}")
            upload.updated_at = datetime.utcnow().isoformat()
            self._save_upload_metadata(upload)

            await websocket_service.fail_video_analysis(
                task_id=upload_id,
                error="上传后处理失败",
                details={"error": str(e)}
            )
            self.logger.error(f"上传后处理失败 {upload_id}: {e}")
    
    def cancel_upload(self, upload_id: str) -> UploadMetadata:
        """取消上传"""
        
        if upload_id not in self.uploads:
            raise ValueError(f"上传任务不存在: {upload_id}")
        
        upload = self.uploads[upload_id]
        upload.status = UploadStatus.CANCELLED
        upload.updated_at = datetime.utcnow().isoformat()
        self._save_upload_metadata(upload)
        
        # 清理文件
        self._cleanup_upload_files(upload_id)
        
        self.logger.info(f"取消上传: {upload_id}")
        
        return upload
    
    def get_upload_status(self, upload_id: str) -> Optional[UploadMetadata]:
        """获取上传状态"""
        loaded_upload = self._load_upload_metadata(upload_id)
        if loaded_upload:
            self.uploads[upload_id] = loaded_upload
            return loaded_upload
        return self.uploads.get(upload_id)
    
    def get_user_uploads(self, user_id: int) -> List[UploadMetadata]:
        """获取用户的上传任务"""
        return [
            upload for upload in self.uploads.values()
            if upload.user_id == user_id
        ]
    
    def _save_upload_metadata(self, upload: UploadMetadata):
        """保存上传元数据"""
        metadata_file = self.temp_dir / f"{upload.upload_id}.json"
        with open(metadata_file, "w") as f:
            f.write(upload.to_json())
    
    def _load_upload_metadata(self, upload_id: str) -> Optional[UploadMetadata]:
        """加载上传元数据"""
        metadata_file = self.temp_dir / f"{upload_id}.json"
        
        if metadata_file.exists():
            try:
                with open(metadata_file, "r") as f:
                    data = json.load(f)
                    # 确保status是Enum类型
                    if "status" in data:
                        data["status"] = UploadStatus(data["status"])
                    return UploadMetadata(**data)
            except Exception as e:
                self.logger.error(f"加载上传元数据失败 {upload_id}: {e}")
                return None
        
        return None
    
    def _cleanup_upload_files(self, upload_id: str):
        """清理上传文件"""
        # 清理分片文件
        for chunk_file in self.chunk_dir.glob(f"{upload_id}_*.chunk"):
            try:
                chunk_file.unlink()
            except Exception as e:
                self.logger.error(f"清理分片文件失败 {chunk_file}: {e}")
        
        # 清理元数据文件
        metadata_file = self.temp_dir / f"{upload_id}.json"
        if metadata_file.exists():
            try:
                metadata_file.unlink()
            except Exception as e:
                self.logger.error(f"清理元数据文件失败 {metadata_file}: {e}")
        
        # 从内存中移除
        if upload_id in self.uploads:
            del self.uploads[upload_id]
    
    def cleanup_old_uploads(self, days: int = UploadConfig.CLEANUP_DAYS):
        """清理旧的上传任务"""
        cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        for upload_id, upload in list(self.uploads.items()):
            created_at = datetime.fromisoformat(upload.created_at.replace('Z', '+00:00')).timestamp()
            
            if created_at < cutoff_time and upload.status in [UploadStatus.COMPLETED, UploadStatus.FAILED, UploadStatus.CANCELLED]:
                self._cleanup_upload_files(upload_id)
                self.logger.info(f"清理旧上传任务: {upload_id}")


# ============================================================================
# 文件上传服务
# ============================================================================

class FileUploadService:
    """文件上传服务"""
    
    def __init__(self):
        self.upload_manager = ChunkedUploadManager()
        self.logger = logging.getLogger(__name__)
    
    async def init_upload(self, file_name: str, file_size: int, chunk_size: int, 
                         user_id: int, metadata: Dict[str, any] = None) -> Dict[str, any]:
        """初始化上传"""
        
        # 生成上传ID
        upload_id = hashlib.md5(f"{file_name}_{file_size}_{user_id}_{datetime.utcnow().isoformat()}".encode()).hexdigest()
        
        # 初始化上传任务
        upload_metadata = self.upload_manager.init_upload(
            upload_id=upload_id,
            file_name=file_name,
            file_size=file_size,
            chunk_size=chunk_size,
            user_id=user_id,
            metadata=metadata
        )
        
        return {
            "upload_id": upload_id,
            "chunk_size": chunk_size,
            "total_chunks": upload_metadata.total_chunks,
            "metadata": upload_metadata.to_dict()
        }
    
    async def upload_chunk(self, upload_id: str, chunk_index: int, chunk_data: bytes, 
                          chunk_hash: str = None) -> Dict[str, any]:
        """上传分片"""
        
        upload_metadata = await self.upload_manager.upload_chunk(
            upload_id=upload_id,
            chunk_index=chunk_index,
            chunk_data=chunk_data,
            chunk_hash=chunk_hash
        )
        
        return {
            "upload_id": upload_id,
            "chunk_index": chunk_index,
            "uploaded_chunks": upload_metadata.uploaded_chunks,
            "progress": int((len(upload_metadata.uploaded_chunks) / upload_metadata.total_chunks) * 100),
            "metadata": upload_metadata.to_dict()
        }
    
    async def complete_upload(self, upload_id: str) -> Dict[str, any]:
        """完成上传"""
        
        upload_metadata = await self.upload_manager.complete_upload(upload_id)
        
        # 兼容处理status
        status_str = str(upload_metadata.status)
        if hasattr(upload_metadata.status, 'value'):
             status_str = upload_metadata.status.value

        return {
            "upload_id": upload_id,
            "status": status_str,
            "file_path": upload_metadata.file_path,
            "file_hash": upload_metadata.file_hash,
            "metadata": upload_metadata.to_dict()
        }
    
    def cancel_upload(self, upload_id: str) -> Dict[str, any]:
        """取消上传"""
        
        upload_metadata = self.upload_manager.cancel_upload(upload_id)
        
        # 兼容处理status
        status_str = str(upload_metadata.status)
        if hasattr(upload_metadata.status, 'value'):
             status_str = upload_metadata.status.value

        return {
            "upload_id": upload_id,
            "status": status_str,
            "metadata": upload_metadata.to_dict()
        }
    
    def get_upload_status(self, upload_id: str) -> Dict[str, any]:
        """获取上传状态"""
        
        upload_metadata = self.upload_manager.get_upload_status(upload_id)
        
        if not upload_metadata:
            return {
                "upload_id": upload_id,
                "status": "not_found",
                "error": "上传任务不存在"
            }
        
        # 终极修复：不再访问 .value，直接强制转字符串，利用 str(Enum) 的特性
        status_str = str(upload_metadata.status)
        if hasattr(upload_metadata.status, 'value'):
             status_str = upload_metadata.status.value

        return {
            "upload_id": upload_id,
            "status": status_str,
            "progress": int((len(upload_metadata.uploaded_chunks) / upload_metadata.total_chunks) * 100),
            "metadata": upload_metadata.to_dict()
        }
    
    def get_user_uploads(self, user_id: int) -> Dict[str, any]:
        """获取用户的上传任务"""
        
        uploads = self.upload_manager.get_user_uploads(user_id)
        
        return {
            "user_id": user_id,
            "uploads": [upload.to_dict() for upload in uploads],
            "total": len(uploads)
        }
    
    def cleanup_old_uploads(self, days: int = UploadConfig.CLEANUP_DAYS):
        """清理旧的上传任务"""
        self.upload_manager.cleanup_old_uploads(days)


# ============================================================================
# 全局实例
# ============================================================================

# 创建全局文件上传服务实例
file_upload_service = FileUploadService()


# ============================================================================
# FastAPI路由
# ============================================================================

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Depends
from fastapi.responses import JSONResponse

# 创建文件上传路由
upload_router = APIRouter(prefix="/api/v1/upload", tags=["文件上传"])

@upload_router.post("/init")
async def init_upload(
    file_name: str = Form(...),
    file_size: int = Form(...),
    chunk_size: int = Form(UploadConfig.MAX_CHUNK_SIZE),
    user_id: int = Form(...),
    metadata: str = Form("{}"),
    current_user: dict = Depends(get_current_user)
):
    """初始化上传"""
    # 验证用户ID一致性
    if user_id != current_user["id"]:
        # 如果是管理员，可能允许代传？暂时强制要求一致
        if current_user.get("role") != "admin":
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无法为其他用户初始化上传任务"
            )
    
    try:
        # 解析元数据
        metadata_dict = json.loads(metadata) if metadata else {}
        
        # 初始化上传
        result = await file_upload_service.init_upload(
            file_name=file_name,
            file_size=file_size,
            chunk_size=chunk_size,
            user_id=user_id,
            metadata=metadata_dict
        )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "data": result,
                "message": "上传初始化成功"
            }
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"上传初始化失败: {str(e)}"
        )

@upload_router.post("/chunk/{upload_id}/{chunk_index}")
async def upload_chunk(
    upload_id: str,
    chunk_index: int,
    chunk_hash: str = Form(None),
    chunk_file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """上传分片"""
    try:
        # 读取分片数据
        chunk_data = await chunk_file.read()
        
        # 验证所有权
        upload_metadata = file_upload_service.upload_manager.get_upload_status(upload_id)
        if not upload_metadata:
             raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="上传任务不存在"
            )
            
        if upload_metadata.user_id != current_user["id"] and current_user.get("role") != "admin":
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权操作此上传任务"
            )

        # 上传分片
        result = await file_upload_service.upload_chunk(
            upload_id=upload_id,
            chunk_index=chunk_index,
            chunk_data=chunk_data,
            chunk_hash=chunk_hash
        )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "data": result,
                "message": "分片上传成功"
            }
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"分片上传失败: {str(e)}"
        )

@upload_router.post("/complete/{upload_id}")
async def complete_upload(
    upload_id: str,
    current_user: dict = Depends(get_current_user)
):
    """完成上传"""
    try:
        # 验证所有权
        upload_metadata = file_upload_service.upload_manager.get_upload_status(upload_id)
        if not upload_metadata:
             raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="上传任务不存在"
            )
            
        if upload_metadata.user_id != current_user["id"] and current_user.get("role") != "admin":
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权操作此上传任务"
            )

        result = await file_upload_service.complete_upload(upload_id)
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "data": result,
                "message": "上传完成"
            }
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"上传完成失败: {str(e)}"
        )

@upload_router.post("/cancel/{upload_id}")
async def cancel_upload(
    upload_id: str,
    current_user: dict = Depends(get_current_user)
):
    """取消上传"""
    try:
        # 验证所有权
        upload_metadata = file_upload_service.upload_manager.get_upload_status(upload_id)
        if not upload_metadata:
             raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="上传任务不存在"
            )
            
        if upload_metadata.user_id != current_user["id"] and current_user.get("role") != "admin":
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权操作此上传任务"
            )

        result = file_upload_service.cancel_upload(upload_id)
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "data": result,
                "message": "上传已取消"
            }
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"取消上传失败: {str(e)}"
        )

@upload_router.get("/status/{upload_id}")
async def get_upload_status(
    upload_id: str,
    current_user: dict = Depends(get_current_user)
):
    """获取上传状态"""
    try:
        result = file_upload_service.get_upload_status(upload_id)
        
        # 验证所有权（如果任务存在）
        if result and "metadata" in result:
             metadata = result["metadata"]
             if metadata.get("user_id") != current_user["id"] and current_user.get("role") != "admin":
                  raise HTTPException(
                     status_code=status.HTTP_403_FORBIDDEN,
                     detail="无权查看此上传任务"
                 )
        elif result and "error" in result:
             # 如果任务不存在（status=not_found），不泄露信息，或者直接返回结果
             pass
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "data": result,
                "message": "获取上传状态成功"
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取上传状态失败: {str(e)}"
        )

@upload_router.get("/user/{user_id}")
async def get_user_uploads(
    user_id: int,
    current_user: dict = Depends(get_current_user)
):
    """获取用户的上传任务"""
    # 验证权限：只能查看自己的，管理员查看所有
    if user_id != current_user["id"] and current_user.get("role") != "admin":
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权查看其他用户的上传任务"
        )
    
    try:
        result = file_upload_service.get_user_uploads(user_id)
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "data": result,
                "message": "获取用户上传任务成功"
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取用户上传任务失败: {str(e)}"
        )


# ============================================================================
# 工具函数
# ============================================================================

def get_file_upload_service() -> FileUploadService:
    """获取文件上传服务实例"""
    return file_upload_service


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test_file_upload():
        """测试文件上传服务"""
        print("测试文件上传服务...")
        
        # 创建服务实例
        service = FileUploadService()
        
        # 测试初始化上传
        init_result = await service.init_upload(
            file_name="test_video.mp4",
            file_size=100 * 1024 * 1024,  # 100MB
            chunk_size=10 * 1024 * 1024,  # 10MB
            user_id=1,
            metadata={"description": "测试视频"}
        )
        
        upload_id = init_result["upload_id"]
        total_chunks = init_result["total_chunks"]
        
        print(f"初始化上传: {upload_id}, 总分片: {total_chunks}")
        
        # 模拟上传分片
        for chunk_index in range(total_chunks):
            # 生成模拟分片数据
            chunk_size = 10 * 1024 * 1024 if chunk_index < total_chunks - 1 else 20 * 1024 * 1024
            chunk_data = os.urandom(chunk_size)
            
            chunk_result = await service.upload_chunk(
                upload_id=upload_id,
                chunk_index=chunk_index,
                chunk_data=chunk_data
            )
            
            progress = chunk_result["progress"]
            print(f"上传分片 {chunk_index}: 进度 {progress}%")
        
        # 完成上传
        complete_result = await service.complete_upload(upload_id)
        print(f"上传完成: {complete_result}")
        
        # 获取上传状态
        status_result = service.get_upload_status(upload_id)
        print(f"上传状态: {status_result}")
        
        # 获取用户上传任务
        user_uploads = service.get_user_uploads(1)
        print(f"用户上传任务: {len(user_uploads['uploads'])} 个")
    
    # 运行测试
    asyncio.run(test_file_upload())
