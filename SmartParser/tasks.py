#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异步任务模块 (Celery Tasks)
============================

使用 Celery + Redis 实现异步任务队列：
- 课件生成任务
- PDF 解析任务
- 视频生成任务
- 知识库索引任务

作者: SmartCourseEngine Team
日期: 2026-01-31
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from celery import Celery
from celery.result import AsyncResult

# ============================================================================
# Celery 配置
# ============================================================================
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

# 创建 Celery 应用
app = Celery(
    "smartcourse_tasks",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

# Celery 配置
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 小时超时
    task_soft_time_limit=3300,  # 55 分钟软超时
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)


# ============================================================================
# 任务进度更新
# ============================================================================
def update_progress(task, current: int, total: int, status: str = "处理中"):
    """更新任务进度"""
    task.update_state(
        state='PROGRESS',
        meta={
            'current': current,
            'total': total,
            'percent': int(current / total * 100) if total > 0 else 0,
            'status': status
        }
    )


# ============================================================================
# 课件生成任务
# ============================================================================
@app.task(bind=True, name='tasks.generate_courseware')
def generate_courseware_task(
    self,
    topic: str,
    knowledge_base_id: str = None,
    options: Dict = None
) -> Dict[str, Any]:
    """
    异步生成课件
    
    Args:
        topic: 课程主题
        knowledge_base_id: 知识库 ID
        options: 生成选项
        
    Returns:
        生成的课件数据
    """
    try:
        from content_generator import ContentGenerator
        
        update_progress(self, 0, 100, "初始化课件生成器...")
        
        generator = ContentGenerator()
        
        update_progress(self, 10, 100, "生成课程大纲...")
        outline = generator.generate_outline(topic)
        
        update_progress(self, 30, 100, "生成讲解脚本...")
        scripts = generator.generate_script(outline)
        
        update_progress(self, 60, 100, "生成练习题库...")
        quizzes = generator.generate_quiz(outline.get("title", topic), scripts)
        
        update_progress(self, 90, 100, "整理课件数据...")
        
        courseware = {
            "topic": topic,
            "outline": outline,
            "scripts": scripts,
            "quizzes": quizzes,
            "generated_at": datetime.now().isoformat(),
            "task_id": self.request.id
        }
        
        update_progress(self, 100, 100, "课件生成完成！")
        
        return {
            "success": True,
            "courseware": courseware,
            "message": "课件生成成功"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"课件生成失败: {e}"
        }


# ============================================================================
# PDF 解析任务
# ============================================================================
@app.task(bind=True, name='tasks.parse_pdf')
def parse_pdf_task(
    self,
    file_path: str,
    options: Dict = None
) -> Dict[str, Any]:
    """
    异步解析 PDF 文档
    
    Args:
        file_path: PDF 文件路径
        options: 解析选项
        
    Returns:
        解析结果
    """
    try:
        from file_parser import FileParser
        
        update_progress(self, 0, 100, "初始化解析器...")
        
        parser = FileParser()
        
        update_progress(self, 10, 100, "读取 PDF 文件...")
        
        # 检查文件大小估算进度
        file_size = Path(file_path).stat().st_size
        estimated_pages = file_size // 50000  # 粗略估计
        
        update_progress(self, 20, 100, f"解析中 (预计 {estimated_pages} 页)...")
        
        result = parser.parse_file(file_path)
        
        update_progress(self, 80, 100, "生成 Markdown...")
        
        # 保存解析结果
        output_dir = Path("data/output_markdown")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = output_dir / f"{Path(file_path).stem}.md"
        output_path.write_text(result.get("markdown", ""), encoding='utf-8')
        
        update_progress(self, 100, 100, "解析完成！")
        
        return {
            "success": True,
            "output_path": str(output_path),
            "page_count": result.get("page_count", 0),
            "word_count": len(result.get("text", "")),
            "message": "PDF 解析成功"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"PDF 解析失败: {e}"
        }


# ============================================================================
# 视频生成任务
# ============================================================================
@app.task(bind=True, name='tasks.generate_video')
def generate_video_task(
    self,
    script: str,
    avatar_id: str,
    voice_id: str,
    options: Dict = None
) -> Dict[str, Any]:
    """
    异步生成数字人视频
    
    Args:
        script: 视频脚本
        avatar_id: 数字人形象 ID
        voice_id: 语音 ID
        options: 视频选项
        
    Returns:
        视频生成结果
    """
    try:
        from video_creator import VideoCreator
        
        update_progress(self, 0, 100, "初始化视频生成器...")
        
        creator = VideoCreator()
        
        update_progress(self, 10, 100, "提交视频生成请求...")
        
        result = creator.create_video(
            text=script,
            avatar_id=avatar_id,
            voice_id=voice_id
        )
        
        if not result.get("video_id"):
            return {
                "success": False,
                "error": "视频生成请求失败",
                "message": result.get("error", "未知错误")
            }
        
        video_id = result["video_id"]
        
        # 轮询等待视频生成
        max_wait = 600  # 最多等待 10 分钟
        wait_time = 0
        poll_interval = 10
        
        while wait_time < max_wait:
            update_progress(
                self, 
                20 + int(wait_time / max_wait * 70), 
                100, 
                f"视频生成中... ({wait_time}s)"
            )
            
            status = creator.get_video_status(video_id)
            
            if status.get("status") == "completed":
                update_progress(self, 100, 100, "视频生成完成！")
                return {
                    "success": True,
                    "video_id": video_id,
                    "video_url": status.get("video_url"),
                    "message": "视频生成成功"
                }
            
            if status.get("status") == "failed":
                return {
                    "success": False,
                    "error": status.get("error", "视频生成失败"),
                    "message": "视频生成失败"
                }
            
            time.sleep(poll_interval)
            wait_time += poll_interval
        
        return {
            "success": False,
            "error": "视频生成超时",
            "message": "视频生成超时，请稍后查看"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"视频生成失败: {e}"
        }


# ============================================================================
# 知识库索引任务
# ============================================================================
@app.task(bind=True, name='tasks.index_knowledge')
def index_knowledge_task(
    self,
    file_paths: list,
    collection_name: str = "default"
) -> Dict[str, Any]:
    """
    异步索引知识库
    
    Args:
        file_paths: 文件路径列表
        collection_name: 集合名称
        
    Returns:
        索引结果
    """
    try:
        from knowledge_manager import KnowledgeManager
        
        update_progress(self, 0, 100, "初始化知识管理器...")
        
        manager = KnowledgeManager()
        
        total_files = len(file_paths)
        indexed_count = 0
        
        for i, file_path in enumerate(file_paths):
            update_progress(
                self, 
                int((i / total_files) * 90), 
                100, 
                f"索引文件 {i+1}/{total_files}..."
            )
            
            try:
                manager.load_and_store(file_path)
                indexed_count += 1
            except Exception as e:
                print(f"索引失败: {file_path}, 错误: {e}")
        
        update_progress(self, 100, 100, "索引完成！")
        
        return {
            "success": True,
            "indexed_count": indexed_count,
            "total_files": total_files,
            "message": f"成功索引 {indexed_count}/{total_files} 个文件"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"知识库索引失败: {e}"
        }


# ============================================================================
# 辅助函数
# ============================================================================
def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    获取任务状态
    
    Args:
        task_id: 任务 ID
        
    Returns:
        任务状态信息
    """
    result = AsyncResult(task_id, app=app)
    
    response = {
        "task_id": task_id,
        "status": result.status,
        "ready": result.ready(),
    }
    
    if result.status == 'PROGRESS':
        response.update(result.info)
    elif result.ready():
        if result.successful():
            response["result"] = result.result
        else:
            response["error"] = str(result.result)
    
    return response


def cancel_task(task_id: str) -> bool:
    """
    取消任务
    
    Args:
        task_id: 任务 ID
        
    Returns:
        是否成功取消
    """
    result = AsyncResult(task_id, app=app)
    result.revoke(terminate=True)
    return True


# ============================================================================
# CLI 入口
# ============================================================================
if __name__ == "__main__":
    # 启动 worker: celery -A tasks worker --loglevel=info
    app.start()
