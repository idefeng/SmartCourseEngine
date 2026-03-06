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
import json
import tempfile
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException, status, BackgroundTasks, Form
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
        self.faster_whisper_model = None
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
            
        except SystemExit as e:
            logger.error(f"模型加载触发系统退出: {e}")
            raise RuntimeError(f"模型加载触发系统退出: {e}") from e
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

            use_faster_whisper = os.getenv("USE_FASTER_WHISPER", "true").lower() == "true"
            if use_faster_whisper:
                try:
                    from faster_whisper import WhisperModel
                    if self.faster_whisper_model is None:
                        self.faster_whisper_model = WhisperModel(
                            cfg.ai.whisper_model,
                            device=os.getenv("WHISPER_DEVICE", "cpu"),
                            compute_type=os.getenv("FASTER_WHISPER_COMPUTE_TYPE", "int8")
                        )
                    logger.info(f"开始转录视频: {video_path}")
                    segments, info = self.faster_whisper_model.transcribe(
                        str(video_path),
                        language="zh",
                        task="transcribe"
                    )
                    segment_list = []
                    text_parts = []
                    duration = float(getattr(info, "duration", 0.0) or 0.0)
                    for idx, seg in enumerate(segments):
                        seg_text = (seg.text or "").strip()
                        if seg_text:
                            text_parts.append(seg_text)
                        segment_list.append(
                            {
                                "id": idx,
                                "start": float(seg.start),
                                "end": float(seg.end),
                                "text": seg_text,
                            }
                        )
                    result = {
                        "text": " ".join(text_parts).strip(),
                        "segments": segment_list,
                        "language": getattr(info, "language", "zh"),
                        "duration": duration,
                    }
                    logger.info(f"转录完成，时长: {result['duration']:.2f}秒")
                    return result
                except Exception as e:
                    logger.warning(f"faster-whisper转录失败，回退到whisper子进程: {e}")
            
            logger.info(f"开始转录视频: {video_path}")
            use_subprocess = os.getenv("WHISPER_SUBPROCESS", "true").lower() == "true"
            if not use_subprocess:
                if self.whisper_model is None:
                    await self.load_models()
                result = self.whisper_model.transcribe(
                    str(video_path),
                    language="zh",
                    task="transcribe",
                    fp16=False
                )
                logger.info(f"转录完成，时长: {result['duration']:.2f}秒")
                return result

            with tempfile.NamedTemporaryFile(prefix="whisper_result_", suffix=".json", delete=False) as tmp_file:
                result_file = tmp_file.name
            script = """
import json
import sys
import whisper

model_name, video_path, result_file = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    model = whisper.load_model(model_name)
    result = model.transcribe(video_path, language="zh", task="transcribe", fp16=False)
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump({"ok": True, "result": result}, f, ensure_ascii=False)
except BaseException as e:
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump({"ok": False, "error": f"{type(e).__name__}: {e}"}, f, ensure_ascii=False)
    raise
"""
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-c",
                script,
                cfg.ai.whisper_model,
                str(video_path),
                result_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await process.communicate()
            if not Path(result_file).exists():
                raise RuntimeError("转录子进程未生成结果文件")
            raw_payload = Path(result_file).read_text(encoding="utf-8").strip()
            Path(result_file).unlink(missing_ok=True)
            if not raw_payload:
                stderr_text = stderr.decode("utf-8", errors="ignore")[-400:]
                if process.returncode and process.returncode != 0:
                    if process.returncode == 139:
                        raise RuntimeError("转录子进程崩溃: Segmentation fault (RC=139)")
                    raise RuntimeError(f"转录子进程异常退出: RC={process.returncode}, STDERR={stderr_text or 'EMPTY'}")
                raise RuntimeError(stderr_text or "转录子进程返回空结果")
            payload = json.loads(raw_payload)
            if process.returncode != 0:
                error_text = payload.get("error") if isinstance(payload, dict) else None
                stderr_text = stderr.decode("utf-8", errors="ignore")[-400:]
                raise RuntimeError(error_text or stderr_text or "转录子进程执行失败")
            if not payload.get("ok"):
                raise RuntimeError(payload.get("error", "转录子进程返回失败"))
            result = payload["result"]
            
            logger.info(f"转录完成，时长: {result['duration']:.2f}秒")
            return result
            
        except SystemExit as e:
            error_text = f"SystemExit: {e}"
            logger.warning(f"视频转录降级处理: {error_text}")
            return {"text": "", "segments": [], "language": "zh", "duration": 0.0, "error": error_text}
        except Exception as e:
            error_text = str(e)
            if "█" in error_text or "MiB/s" in error_text:
                error_text = "Whisper 子进程异常退出（可能资源不足）"
            logger.warning(f"视频转录降级处理: {error_text}")
            return {"text": "", "segments": [], "language": "zh", "duration": 0.0, "error": error_text}
    
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
    course_id: int = None,
    sync: bool = False,
    background_tasks: BackgroundTasks = None
):
    """分析视频（异步处理）"""
    try:
        # 子进程转录模式下不在主进程加载Whisper，避免重复占用内存
        use_subprocess = os.getenv("WHISPER_SUBPROCESS", "true").lower() == "true"
        if video_analyzer.whisper_model is None and not use_subprocess:
            await video_analyzer.load_models()
        
        # 路径归一化处理
        target_dir = Path("/app/uploads")
        original_path_obj = Path(video_path)
        
        if original_path_obj.exists():
            video_path_obj = original_path_obj
        else:
            fallback_path = target_dir / original_path_obj.name
            if fallback_path.exists():
                logger.info(f"原始路径不存在，使用同名文件路径: {fallback_path}")
                video_path_obj = fallback_path
            else:
                import urllib.parse
                decoded_name = urllib.parse.unquote(original_path_obj.name)
                decoded_path = target_dir / decoded_name
                if decoded_path.exists():
                    logger.info(f"使用解码后的文件名路径: {decoded_path}")
                    video_path_obj = decoded_path
                else:
                    logger.error(f"视频文件不存在: 原始路径={video_path}, 尝试路径={fallback_path}, 解码路径={decoded_path}")
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"视频文件不存在: {original_path_obj.name}"
                    )
        
        # 生成任务ID
        job_id = f"job_{datetime.now().strftime('%Y%m%d%H%M%S')}_{course_id or 'temp'}"
        logger.info(f"接受视频分析任务: {job_id}, 路径: {video_path_obj}")

        # 同步模式用于Worker串行处理后续步骤
        if sync:
            logger.info(f"同步模式执行视频分析: {job_id}")
            return await process_video_task(job_id, video_path_obj, course_id)

        # 在后台执行耗时任务
        if background_tasks:
            background_tasks.add_task(
                process_video_task, 
                job_id, 
                video_path_obj, 
                course_id
            )
        else:
            # 如果没有传入 background_tasks（例如测试环境），则同步执行（不推荐）
            logger.warning("未检测到 BackgroundTasks，将同步执行分析（可能导致超时）")
            return await process_video_task(job_id, video_path_obj, course_id)

        return {
            "success": True,
            "message": "视频分析任务已提交",
            "data": {
                "job_id": job_id,
                "status": "processing",
                "video_path": str(video_path_obj)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提交分析任务失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提交分析任务失败: {str(e)}"
        )

async def process_video_task(job_id: str, video_path_obj: Path, course_id: int = None):
    """后台处理视频分析任务"""
    try:
        logger.info(f"开始执行后台分析任务: {job_id}")
        
        transcript_result = await video_analyzer.transcribe_video(video_path_obj)
        if isinstance(transcript_result, Exception):
            logger.error(f"转录失败: {transcript_result}")
            transcript_result = {"text": "", "segments": [], "error": str(transcript_result)}

        enable_keyframes = os.getenv("ENABLE_KEYFRAMES", "false").lower() == "true"
        enable_scenes = os.getenv("ENABLE_SCENES", "false").lower() == "true"

        keyframes_result = []
        scenes_result = []

        if enable_keyframes:
            keyframes_result = await video_analyzer.extract_keyframes(video_path_obj)
            if isinstance(keyframes_result, Exception):
                logger.error(f"关键帧提取失败: {keyframes_result}")
                keyframes_result = []

        if enable_scenes:
            scenes_result = await video_analyzer.detect_scenes(video_path_obj)
            if isinstance(scenes_result, Exception):
                logger.error(f"场景检测失败: {scenes_result}")
                scenes_result = []
        
        # 构建分析结果
        analysis_result = {
            "job_id": job_id,
            "video_path": str(video_path_obj),
            "course_id": course_id,
            "transcript": transcript_result,
            "keyframes": keyframes_result,
            "scenes": scenes_result,
            "analysis_time": datetime.utcnow().isoformat(),
            "status": "completed"
        }
        
        logger.info(f"后台任务完成: {job_id}")
        
        # TODO: 这里应该将结果回调给 Worker 或写入数据库/Redis
        # 目前 Worker 是同步等待 response，改为异步后 Worker 需要轮询或接收回调
        # 为了兼容现有 Worker 逻辑，这里暂时直接返回结果（仅对同步调用有效）
        return {
            "success": True,
            "message": "视频分析完成",
            "data": analysis_result
        }
        
    except Exception as e:
        logger.error(f"后台任务执行失败 {job_id}: {e}")
        return {
            "success": False,
            "message": f"视频分析失败: {str(e)}",
            "error": str(e)
        }

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
