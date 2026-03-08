#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import aio_pika
import httpx
from prometheus_client import Counter, Gauge, Histogram, start_http_server

from shared.task_queue import get_rabbitmq_url, get_video_analysis_queue_name

TASK_TOTAL = Counter(
    "video_analysis_tasks_total",
    "视频分析任务总数",
    ["status"],
)
TASK_DURATION_SECONDS = Histogram(
    "video_analysis_task_duration_seconds",
    "视频分析任务耗时（秒）",
)
WORKER_IN_PROGRESS = Gauge(
    "video_analysis_worker_in_progress",
    "当前正在处理的视频分析任务数",
)


class VideoAnalysisWorker:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.rabbitmq_url = get_rabbitmq_url()
        self.queue_name = get_video_analysis_queue_name()
        self.analyzer_url = os.getenv("VIDEO_ANALYZER_URL", "http://localhost:8002")
        self.knowledge_extractor_url = os.getenv("KNOWLEDGE_EXTRACTOR_URL", "http://knowledge-extractor:8003")
        self.enable_knowledge_pipeline = os.getenv("ENABLE_KNOWLEDGE_PIPELINE", "true").lower() == "true"
        self.max_retries = int(os.getenv("ANALYZER_MAX_RETRIES", "3"))
        self.retry_delay = float(os.getenv("ANALYZER_RETRY_DELAY", "2.0"))

    async def call_video_analyzer(self, file_path: str, course_id: Optional[int] = None, task_id: Optional[str] = None, user_id: Optional[int] = None) -> Dict[str, Any]:
        url = f"{self.analyzer_url.rstrip('/')}/api/v1/videos/analyze"
        params: Dict[str, Any] = {"video_path": file_path, "sync": "true"}
        if course_id is not None:
            params["course_id"] = course_id
        if task_id is not None:
            params["task_id"] = task_id
        if user_id is not None:
            params["user_id"] = user_id
        
        # 延长超时时间到3600秒（1小时），因为Whisper转录大文件可能非常耗时
        timeout = httpx.Timeout(3600.0, connect=60.0)
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            last_error: Optional[Exception] = None
            max_retries = self.max_retries
            
            for attempt in range(1, max_retries + 1):
                try:
                    self.logger.info(f"调用视频分析服务 (尝试 {attempt}/{max_retries}): {url}, 参数: {params}")
                    response = await client.post(url, params=params)
                    
                    # 404不重试，直接抛出
                    if response.status_code == 404:
                        self.logger.error(f"视频文件不存在 (404): {file_path}")
                        response.raise_for_status()
                        
                    # 其他错误码重试
                    if response.status_code in (400, 401, 403, 422, 500, 502, 503, 504):
                        self.logger.warning(f"服务返回错误状态码: {response.status_code} - {response.text[:200]}")
                        response.raise_for_status()
                        
                    response.raise_for_status()
                    payload = response.json()
                    return payload.get("data", payload)
                    
                except (httpx.HTTPError, json.JSONDecodeError, OSError) as e:
                    last_error = e
                    # 如果是404，不重试
                    if isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 404:
                        raise
                        
                    self.logger.warning(f"调用视频分析服务失败({attempt}/{max_retries}): {type(e).__name__} - {e}")
                    
                    # 指数退避策略
                    if attempt < max_retries:
                        sleep_time = self.retry_delay * (2 ** (attempt - 1))
                        self.logger.info(f"等待 {sleep_time:.2f} 秒后重试...")
                        await asyncio.sleep(sleep_time)
            
            raise RuntimeError(f"调用视频分析服务失败，已重试{max_retries}次: {last_error}")

    async def call_knowledge_extractor(self, analysis_result: Dict[str, Any], course_id: Optional[int] = None) -> Dict[str, Any]:
        url = f"{self.knowledge_extractor_url.rstrip('/')}/api/v1/knowledge/process"
        payload: Dict[str, Any] = {"video_analysis": analysis_result}
        if course_id is not None:
            payload["course_id"] = course_id
        timeout = httpx.Timeout(3600.0, connect=60.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            body = response.json()
            return body.get("data", body)

    def _resolve_metadata_path(self, upload_id: str, file_path: Optional[str]) -> Path:
        if file_path:
            upload_root = Path(file_path).expanduser().resolve().parent
            return upload_root / "temp" / f"{upload_id}.json"
        default_upload_dir = Path(os.getenv("UPLOAD_DIR", "uploads")).expanduser().resolve()
        return default_upload_dir / "temp" / f"{upload_id}.json"

    def update_upload_metadata(
        self,
        upload_id: str,
        status: str,
        file_path: Optional[str] = None,
        analysis_result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        worker_stage: Optional[str] = None,
    ) -> None:
        metadata_path = self._resolve_metadata_path(upload_id, file_path)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        if metadata_path.exists():
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        else:
            metadata = {"upload_id": upload_id}
        metadata["status"] = status
        metadata["updated_at"] = datetime.utcnow().isoformat()
        metadata.setdefault("metadata", {})
        metadata["metadata"]["worker"] = {"updated_at": datetime.utcnow().isoformat()}
        if worker_stage:
            metadata["metadata"]["worker"]["stage"] = worker_stage
        if analysis_result is not None:
            metadata["metadata"]["analysis_result"] = analysis_result
        if error:
            metadata["metadata"]["analysis_error"] = error
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False)

    async def call_notification_service(self, user_id: int, title: str, content: str, type: str = "info", metadata: Dict[str, Any] = None) -> None:
        """调用通知服务"""
        url = f"{os.getenv('NOTIFICATION_SERVICE_URL', 'http://notification:8006').rstrip('/')}/api/v1/notifications"
        payload = {
            "user_id": user_id,
            "channel": "in_app",
            "type": type,
            "title": title,
            "content": content,
            "metadata": metadata or {}
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                self.logger.info(f"已向通知服务发送消息: {title}")
        except Exception as e:
            self.logger.error(f"发送通知失败: {e}")

    async def call_course_generator(self, course_id: int, knowledge_points: List[Dict[str, Any]]) -> Dict[str, Any]:
        """可选：触发课件生成"""
        url = f"{os.getenv('COURSE_GENERATOR_URL', 'http://course-generator:8001').rstrip('/')}/api/v1/courses/{course_id}/generate"
        payload = {
            "course_id": course_id,
            "format": "ppt",
            "include_video_summary": True,
            "include_knowledge_graph": True,
            "custom_prompt": f"请结合提取到的 {len(knowledge_points)} 个知识点生成课件。"
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            self.logger.error(f"自动触发课件生成失败: {e}")
            return {"success": False, "error": str(e)}

    async def push_websocket_progress(self, task_id: str, user_id: int, progress: int, stage: str, message: str, metadata: Dict[str, Any] = None) -> None:
        """向API网关推送WebSocket进度更新"""
        url = f"{os.getenv('GATEWAY_INTERNAL_URL', 'http://api-gateway:8000').rstrip('/')}/api/v1/internal/ws/task-progress"
        payload = {
            "task_id": task_id,
            "user_id": user_id,
            "progress": progress,
            "stage": stage,
            "message": message,
            "metadata": metadata or {}
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
        except Exception as e:
            self.logger.error(f"推送WebSocket进度失败: {e}")

    async def process_message(self, message: aio_pika.IncomingMessage) -> None:
        async with message.process(requeue=False):
            payload = json.loads(message.body.decode("utf-8"))
            upload_id = payload["upload_id"]
            file_path = payload.get("file_path")
            user_id = payload.get("user_id", 1)
            file_name = payload.get("file_name", "视频文件")
            course_id = payload.get("metadata", {}).get("course_id")
            
            # 初始化进度推送
            await self.push_websocket_progress(
                task_id=upload_id,
                user_id=user_id,
                progress=5,
                stage="started",
                message="分析任务已启动",
                metadata={"file_name": file_name, "course_id": course_id}
            )
            
            self.update_upload_metadata(upload_id, "processing", file_path=file_path)
            TASK_TOTAL.labels(status="processing").inc()
            self.logger.info(f"开始处理视频分析任务: {upload_id}")
            WORKER_IN_PROGRESS.inc()
            
            try:
                with TASK_DURATION_SECONDS.time():
                    # 1. 视频分析阶段 (20% - 70%)
                    await self.push_websocket_progress(
                        task_id=upload_id,
                        user_id=user_id,
                        progress=20,
                        stage="analyzing",
                        message="正在进行视频AI分析（语音转写与视觉识别）..."
                    )
                    
                    self.update_upload_metadata(
                        upload_id,
                        "processing",
                        file_path=file_path,
                        worker_stage="analyzing"
                    )
                    analysis_result = await self.call_video_analyzer(
                        file_path=file_path, 
                        course_id=course_id,
                        task_id=upload_id,
                        user_id=user_id
                    )
                    
                    # 2. 知识提取阶段 (70% - 95%)
                    await self.push_websocket_progress(
                        task_id=upload_id,
                        user_id=user_id,
                        progress=75,
                        stage="knowledge_processing",
                        message="视频分析完成，正在提取结构化知识点..."
                    )
                    
                    final_result = analysis_result
                    if self.enable_knowledge_pipeline:
                        self.update_upload_metadata(
                            upload_id,
                            "processing",
                            file_path=file_path,
                            worker_stage="knowledge_processing"
                        )
                        knowledge_result = await self.call_knowledge_extractor(analysis_result=analysis_result, course_id=course_id)
                        final_result = knowledge_result
                        
                        # 3. (可选) 自动触发课件生成
                        if course_id and os.getenv("AUTO_GENERATE_COURSE", "false").lower() == "true":
                            await self.push_websocket_progress(
                                task_id=upload_id,
                                user_id=user_id,
                                progress=90,
                                stage="generating_course",
                                message="知识点提取完成，正在自动生成课件演示文档..."
                            )
                            kp_list = knowledge_result.get("knowledge_points", [])
                            await self.call_course_generator(course_id, kp_list)

                    self.update_upload_metadata(
                        upload_id,
                        "completed",
                        file_path=file_path,
                        analysis_result=final_result,
                        worker_stage="completed"
                    )
                
                # 4. 推送最终完成状态到WebSocket (100%)
                await self.push_websocket_progress(
                    task_id=upload_id,
                    user_id=user_id,
                    progress=100,
                    stage="completed",
                    message="任务全部处理完成！",
                    metadata={"result_summary": "提取了多项核心知识点"}
                )
                
                # 5. 发送正式通知
                await self.call_notification_service(
                    user_id=user_id,
                    title="视频分析与知识提取完成",
                    content=f"您的视频《{file_name}》已处理完成，成功提取知识点。",
                    type="success",
                    metadata={"upload_id": upload_id, "course_id": course_id}
                )
                
                TASK_TOTAL.labels(status="completed").inc()
                self.logger.info(f"视频分析任务成功完成: {upload_id}")
                
            except Exception as e:
                self.update_upload_metadata(
                    upload_id,
                    "failed",
                    file_path=file_path,
                    error=str(e),
                )
                
                # 推送失败状态到WebSocket
                await self.push_websocket_progress(
                    task_id=upload_id,
                    user_id=user_id,
                    progress=0,
                    stage="failed",
                    message=f"处理失败: {str(e)}"
                )
                
                # 发送失败通知
                await self.call_notification_service(
                    user_id=user_id,
                    title="视频处理失败",
                    content=f"处理视频《{file_name}》时发生错误: {str(e)}",
                    type="error",
                    metadata={"upload_id": upload_id}
                )
                
                TASK_TOTAL.labels(status="failed").inc()
                self.logger.error(f"视频分析任务失败 {upload_id}: {e}")
            finally:
                WORKER_IN_PROGRESS.dec()

    async def run(self) -> None:
        try:
            connection = await aio_pika.connect_robust(self.rabbitmq_url)
            self.logger.info(f"连接消息队列成功: {self.rabbitmq_url}")
            async with connection:
                channel = await connection.channel()
                await channel.set_qos(prefetch_count=1)
                queue = await channel.declare_queue(self.queue_name, durable=True)
                self.logger.info(f"开始消费视频处理队列: {self.queue_name}")
                async with queue.iterator() as queue_iter:
                    async for message in queue_iter:
                        await self.process_message(message)
        except Exception as e:
            self.logger.error(f"视频工作线程运行时异常: {e}")
            await asyncio.sleep(5)
            raise


async def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    metrics_port = int(os.getenv("WORKER_METRICS_PORT", "9108"))
    start_http_server(metrics_port)
    worker = VideoAnalysisWorker()
    worker.logger.info(f"指标服务已启动: 0.0.0.0:{metrics_port}")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
