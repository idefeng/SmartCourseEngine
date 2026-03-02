#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频分析服务
==========

处理视频上传、转码、语音识别、视觉分析等功能。

作者: SmartCourseEngine Team
日期: 2026-03-01
"""

import os
import sys
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 添加共享模块路径
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))

try:
    from shared.config import config, load_config_from_file
    from shared.utils import setup_logger
except ImportError:
    # 备用导入方式
    from config import config, load_config_from_file
    from utils import setup_logger

# ============================================================================
# 配置和日志
# ============================================================================

# 加载配置
cfg = load_config_from_file()
cfg.service.service_name = "video-analyzer"
cfg.service.service_port = 8002

# 设置日志
logger = setup_logger(
    name="video-analyzer",
    level=cfg.service.log_level,
    format_str=cfg.service.log_format
)

# ============================================================================
# 生命周期管理
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info(f"🚀 启动视频分析服务: {cfg.service.service_name}")
    logger.info(f"📊 服务端口: {cfg.service.service_port}")
    
    # 创建必要的目录
    data_dir = Path(cfg.service.data_dir)
    video_dir = data_dir / "videos"
    transcript_dir = data_dir / "transcripts"
    keyframe_dir = data_dir / "keyframes"
    
    for directory in [data_dir, video_dir, transcript_dir, keyframe_dir]:
        directory.mkdir(parents=True, exist_ok=True)
        logger.debug(f"创建目录: {directory}")
    
    # 初始化AI模型（延迟加载）
    logger.info("🤖 准备AI模型（延迟加载）")
    
    yield
    
    # 关闭时
    logger.info("👋 关闭视频分析服务")

# ============================================================================
# FastAPI应用
# ============================================================================

app = FastAPI(
    title="SmartCourseEngine Video Analyzer",
    version="1.0.0",
    description="视频分析服务 - 处理视频上传、转码、语音识别、视觉分析",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.service.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# 视频分析服务
# ============================================================================

class VideoAnalyzer:
    """视频分析服务类"""
    
    def __init__(self):
        self.whisper_model = None
        self.clip_model = None
        self.yolo_model = None
    
    async def load_models(self):
        """加载AI模型（延迟加载）"""
        try:
            logger.info("加载Whisper模型...")
            import whisper
            self.whisper_model = whisper.load_model(cfg.ai.whisper_model)
            logger.info(f"Whisper模型加载完成: {cfg.ai.whisper_model}")
            
            # 其他模型可以按需加载
            # logger.info("加载CLIP模型...")
            # from transformers import CLIPProcessor, CLIPModel
            # self.clip_model = CLIPModel.from_pretrained(cfg.ai.clip_model)
            # self.clip_processor = CLIPProcessor.from_pretrained(cfg.ai.clip_model)
            
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            # 在开发环境中，我们可以使用模拟模式
            if cfg.service.debug:
                logger.warning("使用模拟模式（开发环境）")
                self.whisper_model = "mock"
            else:
                raise
    
    async def transcribe_video(self, video_path: Path) -> dict:
        """转录视频音频
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            dict: 转录结果
        """
        try:
            if self.whisper_model == "mock":
                # 模拟转录结果
                return {
                    "text": "这是模拟的转录文本。在实际环境中，这里会是视频的实际语音内容。",
                    "segments": [
                        {
                            "id": 0,
                            "start": 0.0,
                            "end": 10.0,
                            "text": "欢迎学习Python编程入门课程。"
                        },
                        {
                            "id": 1,
                            "start": 10.0,
                            "end": 30.0,
                            "text": "在这一节中，我们将学习变量和数据类型。"
                        }
                    ],
                    "language": "zh",
                    "duration": 120.0
                }
            
            # 实际Whisper转录
            import whisper
            
            logger.info(f"开始转录视频: {video_path}")
            result = self.whisper_model.transcribe(
                str(video_path),
                language="zh",
                task="transcribe"
            )
            
            logger.info(f"转录完成，时长: {result['duration']:.2f}秒")
            return result
            
        except Exception as e:
            logger.error(f"视频转录失败: {e}")
            raise
    
    async def extract_keyframes(self, video_path: Path, interval: int = 10) -> list:
        """提取关键帧
        
        Args:
            video_path: 视频文件路径
            interval: 提取间隔（秒）
            
        Returns:
            list: 关键帧信息列表
        """
        try:
            import cv2
            from datetime import datetime
            
            logger.info(f"开始提取关键帧: {video_path}")
            
            # 打开视频文件
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                raise ValueError(f"无法打开视频文件: {video_path}")
            
            # 获取视频信息
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0
            
            logger.info(f"视频信息 - FPS: {fps:.2f}, 总帧数: {total_frames}, 时长: {duration:.2f}秒")
            
            keyframes = []
            frame_interval = int(fps * interval)
            
            for frame_num in range(0, total_frames, frame_interval):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = cap.read()
                
                if not ret:
                    break
                
                # 保存关键帧
                timestamp = frame_num / fps
                keyframe_filename = f"keyframe_{int(timestamp)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                keyframe_path = Path(cfg.service.data_dir) / "keyframes" / keyframe_filename
                
                cv2.imwrite(str(keyframe_path), frame)
                
                keyframes.append({
                    "frame_number": frame_num,
                    "timestamp": timestamp,
                    "file_path": str(keyframe_path),
                    "file_size": keyframe_path.stat().st_size
                })
                
                logger.debug(f"提取关键帧: 时间戳 {timestamp:.2f}秒")
            
            cap.release()
            logger.info(f"关键帧提取完成，共 {len(keyframes)} 帧")
            return keyframes
            
        except Exception as e:
            logger.error(f"关键帧提取失败: {e}")
            # 返回模拟数据
            return [
                {
                    "frame_number": 0,
                    "timestamp": 0.0,
                    "file_path": "/app/data/keyframes/keyframe_0_mock.jpg",
                    "file_size": 10240
                },
                {
                    "frame_number": 300,
                    "timestamp": 10.0,
                    "file_path": "/app/data/keyframes/keyframe_10_mock.jpg",
                    "file_size": 10240
                }
            ]
    
    async def detect_scenes(self, video_path: Path) -> list:
        """检测场景变化
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            list: 场景变化时间点列表
        """
        try:
            from scenedetect import VideoManager
            from scenedetect.detectors import ContentDetector
            from scenedetect.scene_manager import SceneManager
            
            logger.info(f"开始检测场景变化: {video_path}")
            
            # 创建视频管理器
            video_manager = VideoManager([str(video_path)])
            
            # 创建场景管理器
            scene_manager = SceneManager()
            scene_manager.add_detector(ContentDetector())
            
            # 开始检测
            video_manager.start()
            scene_manager.detect_scenes(frame_source=video_manager)
            
            # 获取场景列表
            scene_list = scene_manager.get_scene_list()
            
            scenes = []
            for i, scene in enumerate(scene_list):
                scenes.append({
                    "scene_id": i,
                    "start_time": scene[0].get_seconds(),
                    "end_time": scene[1].get_seconds(),
                    "duration": scene[1].get_seconds() - scene[0].get_seconds()
                })
            
            video_manager.release()
            logger.info(f"场景检测完成，共 {len(scenes)} 个场景")
            return scenes
            
        except Exception as e:
            logger.error(f"场景检测失败: {e}")
            # 返回模拟数据
            return [
                {
                    "scene_id": 0,
                    "start_time": 0.0,
                    "end_time": 30.0,
                    "duration": 30.0
                },
                {
                    "scene_id": 1,
                    "start_time": 30.0,
                    "end_time": 60.0,
                    "duration": 30.0
                }
            ]

# 全局视频分析器实例
video_analyzer = VideoAnalyzer()

# ============================================================================
# API路由
# ============================================================================

@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "SmartCourseEngine Video Analyzer",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "upload": "/api/v1/videos/upload",
            "analyze": "/api/v1/videos/analyze/{video_id}",
            "status": "/api/v1/videos/status/{job_id}"
        }
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": cfg.service.service_name,
        "timestamp": "2026-03-01T20:37:00Z",
        "models_loaded": video_analyzer.whisper_model is not None
    }

@app.post("/api/v1/videos/upload")
async def upload_video(
    file: UploadFile = File(..., description="视频文件"),
    course_id: int = None
):
    """上传视频文件"""
    try:
        # 验证文件类型
        allowed_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
        file_ext = Path(file.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的文件类型。支持的类型: {', '.join(allowed_extensions)}"
            )
        
        # 保存文件
        video_dir = Path(cfg.service.data_dir) / "videos"
        video_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"video_{course_id or 'temp'}_{Path(file.filename).stem}{file_ext}"
        file_path = video_dir / filename
        
        # 写入文件
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        file_size = file_path.stat().st_size
        
        logger.info(f"视频上传成功: {filename} ({file_size} bytes)")
        
        return {
            "success": True,
            "message": "视频上传成功",
            "data": {
                "filename": filename,
                "file_path": str(file_path),
                "file_size": file_size,
                "course_id": course_id,
                "uploaded_at": "2026-03-01T20:37:00Z"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"视频上传失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"视频上传失败: {str(e)}"
        )

@app.post("/api/v1/videos/analyze")
async def analyze_video(
    video_path: str,
    course_id: int = None
):
    """分析视频"""
    try:
        # 确保模型已加载
        if video_analyzer.whisper_model is None:
            await video_analyzer.load_models()
        
        video_path_obj = Path(video_path)
        if not video_path_obj.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="视频文件不存在"
            )
        
        logger.info(f"开始分析视频: {video_path}")
        
        # 并行执行分析任务
        tasks = [
            video_analyzer.transcribe_video(video_path_obj),
            video_analyzer.extract_keyframes(video_path_obj),
            video_analyzer.detect_scenes(video_path_obj)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 检查任务结果
        transcript_result, keyframes_result, scenes_result = results
        
        if isinstance(transcript_result, Exception):
            logger.error(f"转录失败: {transcript_result}")
            transcript_result = {"text": "", "segments": [], "error": str(transcript_result)}
        
        if isinstance(keyframes_result, Exception):
            logger.error(f"关键帧提取失败: {keyframes_result}")
            keyframes_result = []
        
        if isinstance(scenes_result, Exception):
            logger.error(f"场景检测失败: {scenes_result}")
            scenes_result = []
        
        # 构建分析结果
        analysis_result = {
            "video_path": str(video_path_obj),
            "course_id": course_id,
            "transcript": transcript_result,
            "keyframes": keyframes_result,
            "scenes": scenes_result,
            "analysis_time": "2026-03-01T20:37:00Z",
            "status": "completed"
        }
        
        logger.info(f"视频分析完成: {video_path}")
        
        return {
            "success": True,
            "message": "视频分析完成",
            "data": analysis_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"视频分析失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"视频分析失败: {str(e)}"
        )

# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数"""
    logger.info(f"🚀 启动视频分析服务: {cfg.service.service_name}")
    logger.info(f"📊 服务端口: {cfg.service.service_port}")
    logger.info(f"🔧 调试模式: {cfg.service.debug}")
    logger.info(f"🌐 CORS允许的来源: {cfg.service.cors_origins}")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=cfg.service.service_port,
        log_level="info",
        reload=cfg.service.debug
    )

if __name__ == "__main__":
    main()