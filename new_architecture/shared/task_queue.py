#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from datetime import datetime
from typing import Any, Dict

import aio_pika

try:
    from .config import config
except ImportError:
    from shared.config import config


def get_rabbitmq_url() -> str:
    return (
        os.getenv("MQ_RABBITMQ_URL")
        or os.getenv("RABBITMQ_URL")
        or config.message_queue.rabbitmq_url
    )


def get_video_analysis_queue_name() -> str:
    return os.getenv("MQ_VIDEO_ANALYSIS_QUEUE") or config.message_queue.video_analysis_queue


async def publish_video_analysis_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    rabbitmq_url = get_rabbitmq_url()
    queue_name = get_video_analysis_queue_name()
    task_id = payload.get("task_id") or payload.get("upload_id")
    message_payload = {
        **payload,
        "task_type": "video_analysis",
        "queued_at": datetime.utcnow().isoformat(),
    }
    connection = await aio_pika.connect_robust(rabbitmq_url)
    try:
        channel = await connection.channel(publisher_confirms=True)
        queue = await channel.declare_queue(queue_name, durable=True)
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(message_payload, ensure_ascii=False).encode("utf-8"),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                message_id=str(task_id),
                timestamp=datetime.utcnow(),
            ),
            routing_key=queue.name,
        )
    finally:
        await connection.close()
    return {
        "task_id": task_id,
        "queue": queue_name,
        "queued_at": message_payload["queued_at"],
    }
