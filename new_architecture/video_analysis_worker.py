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

    async def call_video_analyzer(self, file_path: str, course_id: Optional[int] = None) -> Dict[str, Any]:
        url = f"{self.analyzer_url.rstrip('/')}/api/v1/videos/analyze"
        params: Dict[str, Any] = {"video_path": file_path, "sync": "true"}
        if course_id is not None:
            params["course_id"] = course_id
        
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

    async def process_message(self, message: aio_pika.IncomingMessage) -> None:
        async with message.process(requeue=False):
            payload = json.loads(message.body.decode("utf-8"))
            upload_id = payload["upload_id"]
            file_path = payload.get("file_path")
            course_id = payload.get("metadata", {}).get("course_id")
            self.update_upload_metadata(upload_id, "processing", file_path=file_path)
            TASK_TOTAL.labels(status="processing").inc()
            self.logger.info(f"开始处理视频分析任务: {upload_id}")
            WORKER_IN_PROGRESS.inc()
            try:
                with TASK_DURATION_SECONDS.time():
                    self.update_upload_metadata(
                        upload_id,
                        "processing",
                        file_path=file_path,
                        worker_stage="analyzing"
                    )
                    analysis_result = await self.call_video_analyzer(file_path=file_path, course_id=course_id)
                    result = analysis_result
                    if self.enable_knowledge_pipeline:
                        self.update_upload_metadata(
                            upload_id,
                            "processing",
                            file_path=file_path,
                            worker_stage="knowledge_processing"
                        )
                        result = await self.call_knowledge_extractor(analysis_result=analysis_result, course_id=course_id)
                    self.update_upload_metadata(
                        upload_id,
                        "processing",
                        file_path=file_path,
                        worker_stage="knowledge_completed"
                    )
                self.update_upload_metadata(
                    upload_id,
                    "completed",
                    file_path=file_path,
                    analysis_result=result,
                )
                TASK_TOTAL.labels(status="completed").inc()
                self.logger.info(f"视频分析任务完成: {upload_id}")
            except Exception as e:
                self.update_upload_metadata(
                    upload_id,
                    "failed",
                    file_path=file_path,
                    error=str(e),
                )
                TASK_TOTAL.labels(status="failed").inc()
                self.logger.error(f"视频分析任务失败 {upload_id}: {e}")
            finally:
                WORKER_IN_PROGRESS.dec()

    async def run(self) -> None:
        connection = await aio_pika.connect_robust(self.rabbitmq_url)
        self.logger.info(f"连接队列成功: {self.rabbitmq_url}")
        async with connection:
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=1)
            queue = await channel.declare_queue(self.queue_name, durable=True)
            self.logger.info(f"开始消费队列: {self.queue_name}")
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    await self.process_message(message)


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
