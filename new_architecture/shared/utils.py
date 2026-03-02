#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
共享工具函数
===========

所有微服务共享的工具函数和辅助类。

作者: SmartCourseEngine Team
日期: 2026-03-01
"""

import os
import sys
import json
import logging
import hashlib
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Callable
from pathlib import Path
from uuid import UUID, uuid4
from functools import wraps
from contextlib import contextmanager

import aiohttp
from redis import Redis
import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential


# ============================================================================
# 日志配置
# ============================================================================

def setup_logger(
    name: str,
    level: str = "INFO",
    format_str: Optional[str] = None,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    设置日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别
        format_str: 日志格式字符串
        log_file: 日志文件路径
        
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    if format_str is None:
        format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # 清除现有的处理器
    logger.handlers.clear()
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    console_formatter = logging.Formatter(format_str)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（如果指定了日志文件）
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(getattr(logging, level.upper()))
        file_formatter = logging.Formatter(format_str)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # 防止日志传播到根记录器
    logger.propagate = False
    
    return logger


# ============================================================================
# 缓存工具
# ============================================================================

class CacheManager:
    """缓存管理器"""
    
    def __init__(self, redis_client: Redis, prefix: str = "smartcourse"):
        """
        初始化缓存管理器
        
        Args:
            redis_client: Redis客户端
            prefix: 缓存键前缀
        """
        self.redis = redis_client
        self.prefix = prefix
    
    def make_key(self, *parts) -> str:
        """
        生成缓存键
        
        Args:
            *parts: 键的组成部分
            
        Returns:
            str: 完整的缓存键
        """
        key_parts = [self.prefix] + [str(part) for part in parts]
        return ":".join(key_parts)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            default: 默认值
            
        Returns:
            Any: 缓存值或默认值
        """
        try:
            value = self.redis.get(key)
            if value is not None:
                return json.loads(value)
            return default
        except (json.JSONDecodeError, Exception):
            return default
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒）
            
        Returns:
            bool: 是否设置成功
        """
        try:
            serialized = json.dumps(value, ensure_ascii=False)
            if ttl:
                return self.redis.setex(key, ttl, serialized)
            else:
                return self.redis.set(key, serialized)
        except Exception:
            return False
    
    def delete(self, key: str) -> bool:
        """
        删除缓存键
        
        Args:
            key: 缓存键
            
        Returns:
            bool: 是否删除成功
        """
        try:
            return bool(self.redis.delete(key))
        except Exception:
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """
        清除匹配模式的缓存键
        
        Args:
            pattern: 键模式
            
        Returns:
            int: 删除的键数量
        """
        try:
            keys = self.redis.keys(pattern)
            if keys:
                return self.redis.delete(*keys)
            return 0
        except Exception:
            return 0


def cache_result(
    key_func: Callable,
    ttl: int = 3600,
    prefix: str = "cache"
):
    """
    缓存函数结果的装饰器
    
    Args:
        key_func: 生成缓存键的函数
        ttl: 缓存过期时间（秒）
        prefix: 缓存键前缀
        
    Returns:
        Callable: 装饰器函数
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 获取缓存管理器
            from .config import config
            from .database import get_redis
            
            redis_client = get_redis()
            cache_manager = CacheManager(redis_client, prefix)
            
            # 生成缓存键
            cache_key = key_func(*args, **kwargs)
            
            # 尝试从缓存获取
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # 执行函数
            result = await func(*args, **kwargs)
            
            # 缓存结果
            cache_manager.set(cache_key, result, ttl)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 获取缓存管理器
            from .config import config
            from .database import get_redis
            
            redis_client = get_redis()
            cache_manager = CacheManager(redis_client, prefix)
            
            # 生成缓存键
            cache_key = key_func(*args, **kwargs)
            
            # 尝试从缓存获取
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 缓存结果
            cache_manager.set(cache_key, result, ttl)
            
            return result
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# ============================================================================
# 时间工具
# ============================================================================

def format_duration(seconds: int) -> str:
    """
    格式化时长
    
    Args:
        seconds: 秒数
        
    Returns:
        str: 格式化的时长字符串
    """
    if seconds < 60:
        return f"{seconds}秒"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes}分{remaining_seconds}秒"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        remaining_seconds = seconds % 60
        return f"{hours}小时{minutes}分{remaining_seconds}秒"


def parse_timestamp(timestamp_str: str) -> Optional[datetime]:
    """
    解析时间戳字符串
    
    Args:
        timestamp_str: 时间戳字符串
        
    Returns:
        Optional[datetime]: 解析后的datetime对象
    """
    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d"
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(timestamp_str, fmt)
        except ValueError:
            continue
    
    return None


def time_range_overlap(
    start1: int, end1: int,
    start2: int, end2: int
) -> bool:
    """
    检查两个时间范围是否重叠
    
    Args:
        start1: 第一个范围的开始时间
        end1: 第一个范围的结束时间
        start2: 第二个范围的开始时间
        end2: 第二个范围的结束时间
        
    Returns:
        bool: 是否重叠
    """
    return max(start1, start2) <= min(end1, end2)


# ============================================================================
# 文本处理工具
# ============================================================================

def clean_text(text: str) -> str:
    """
    清理文本
    
    Args:
        text: 原始文本
        
    Returns:
        str: 清理后的文本
    """
    if not text:
        return ""
    
    # 移除多余的空格和换行
    text = ' '.join(text.split())
    
    # 移除控制字符
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
    
    return text.strip()


def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """
    提取关键词（简化版本）
    
    Args:
        text: 文本
        max_keywords: 最大关键词数量
        
    Returns:
        List[str]: 关键词列表
    """
    # 移除标点符号
    import re
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # 分词
    words = text.lower().split()
    
    # 过滤停用词（简化版本）
    stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
    words = [word for word in words if word not in stop_words and len(word) > 1]
    
    # 统计词频
    from collections import Counter
    word_counts = Counter(words)
    
    # 返回最常见的词
    return [word for word, _ in word_counts.most_common(max_keywords)]


def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    计算文本相似度（基于Jaccard相似度）
    
    Args:
        text1: 第一个文本
        text2: 第二个文本
        
    Returns:
        float: 相似度分数（0-1）
    """
    if not text1 or not text2:
        return 0.0
    
    # 分词
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    # 计算Jaccard相似度
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    if union == 0:
        return 0.0
    
    return intersection / union


# ============================================================================
# 文件处理工具
# ============================================================================

def get_file_hash(file_path: Union[str, Path], algorithm: str = "sha256") -> str:
    """
    计算文件哈希值
    
    Args:
        file_path: 文件路径
        algorithm: 哈希算法
        
    Returns:
        str: 文件哈希值
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    hash_func = hashlib.new(algorithm)
    
    with open(file_path, 'rb') as f:
        # 分块读取大文件
        for chunk in iter(lambda: f.read(4096), b''):
            hash_func.update(chunk)
    
    return hash_func.hexdigest()


def get_file_metadata(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    获取文件元数据
    
    Args:
        file_path: 文件路径
        
    Returns:
        Dict[str, Any]: 文件元数据
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    stat = file_path.stat()
    
    return {
        "filename": file_path.name,
        "extension": file_path.suffix.lower(),
        "size": stat.st_size,
        "created_at": datetime.fromtimestamp(stat.st_ctime),
        "modified_at": datetime.fromtimestamp(stat.st_mtime),
        "hash": get_file_hash(file_path),
        "path": str(file_path.absolute())
    }


def safe_filename(filename: str) -> str:
    """
    生成安全的文件名
    
    Args:
        filename: 原始文件名
        
    Returns:
        str: 安全的文件名
    """
    import re
    
    # 移除非法字符
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # 限制长度
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255 - len(ext)] + ext
    
    return filename


# ============================================================================
# 网络工具
# ============================================================================

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def fetch_url(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    data: Optional[Any] = None,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    异步获取URL内容
    
    Args:
        url: URL地址
        method: HTTP方法
        headers: 请求头
        data: 请求数据
        timeout: 超时时间（秒）
        
    Returns:
        Dict[str, Any]: 响应结果
    """
    if headers is None:
        headers = {}
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.request(
                method=method,
                url=url,
                headers=headers,
                data=data,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                content = await response.read()
                
                return {
                    "status": response.status,
                    "headers": dict(response.headers),
                    "content": content,
                    "text": content.decode('utf-8', errors='ignore'),
                    "url": str(response.url)
                }
        except Exception as e:
            raise Exception(f"请求失败: {str(e)}")


def validate_url(url: str) -> bool:
    """
    验证URL格式
    
    Args:
        url: URL地址
        
    Returns:
        bool: 是否有效
    """
    import re
    
    pattern = re.compile(
        r'^(https?://)?'  # 协议
        r'(([A-Z0-9][A-Z0-9_-]*)(\.[A-Z0-9][A-Z0-9_-]*)+)'  # 域名
        r'(:\d+)?'  # 端口
        r'(/.*)?$',  # 路径
        re.IGNORECASE
    )
    
    return bool(pattern.match(url))


# ============================================================================
# 数学工具
# ============================================================================

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    计算余弦相似度
    
    Args:
        vec1: 第一个向量
        vec2: 第二个向量
        
    Returns:
        float: 余弦相似度
    """
    if not vec1 or not vec2:
        return 0.0
    
    if len(vec1) != len(vec2):
        raise ValueError("向量长度必须相同")
    
    vec1_np = np.array(vec1)
    vec2_np = np.array(vec2)
    
    dot_product = np.dot(vec1_np, vec2_np)
    norm1 = np.linalg.norm(vec1_np)
    norm2 = np.linalg.norm(vec2_np)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return dot_product / (norm1 * norm2)


def normalize_vector(vec: List[float]) -> List[float]:
    """
    归一化向量
    
    Args:
        vec: 原始向量
        
    Returns:
        List[float]: 归一化后的向量
    """
    if not vec:
        return []
    
    vec_np = np.array(vec)
    norm = np.linalg.norm(vec_np)
    
    if norm == 0:
        return vec
    
    normalized = vec_np / norm
    return normalized.tolist()


# ============================================================================
# 上下文管理器
# ============================================================================

@contextmanager
def timer(name: str = "操作"):
    """
    计时上下文管理器
    
    Args:
        name: 操作名称
    """
    start_time = datetime.now()
    try:
        yield
    finally:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        print(f"{name}耗时: {duration:.2f}秒")


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics = {}
    
    def start(self, operation: str):
        """开始计时"""
        self.metrics[operation] = {
            "start": datetime.now(),
            "end": None,
            "duration": None
        }
    
    def end(self, operation: str):
        """结束计时"""
        if operation in self.metrics:
            end_time = datetime.now()
            self.metrics[operation]["end"] = end_time
            duration = (end_time - self.metrics[operation]["start"]).total_seconds()
            self.metrics[operation]["duration"] = duration
    
    def get_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        report = {
            "total_operations": len(self.metrics),
            "operations": {},
            "summary": {
                "total_duration": 0.0,
                "average_duration": 0.0,
                "slowest_operation": None,
                "fastest_operation": None
            }
        }
        
        durations = []
        for op, data in self.metrics.items():
            if data["duration"] is not None:
                report["operations"][op] = data["duration"]
                durations.append(data["duration"])
                report["summary"]["total_duration"] += data["duration"]
        
        if durations:
            report["summary"]["average_duration"] = sum(durations) / len(durations)
            report["summary"]["slowest_operation"] = max(durations)
            report["summary"]["fastest_operation"] = min(durations)
        
        return report


# ============================================================================
# 错误处理
# ============================================================================

class SmartCourseError(Exception):
    """SmartCourseEngine基础异常"""
    
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "error": {
                "code": self.code,
                "message": str(self),
                "details": self.details
            }
        }


class ValidationError(SmartCourseError):
    """验证错误"""
    
    def __init__(self, message: str, field: Optional[str] = None):
        details = {"field": field} if field else {}
        super().__init__(message, "VALIDATION_ERROR", details)


class NotFoundError(SmartCourseError):
    """未找到错误"""
    
    def __init__(self, resource: str, resource_id: Any):
        details = {"resource": resource, "resource_id": str(resource_id)}
        super().__init__(f"{resource}未找到: {resource_id}", "NOT_FOUND", details)


class ExternalServiceError(SmartCourseError):
    """外部服务错误"""
    
    def __init__(self, service: str, message: str):
        details = {"service": service}
        super().__init__(f"{service}服务错误: {message}", "EXTERNAL_SERVICE_ERROR", details)


def handle_exceptions(func):
    """
    异常处理装饰器
    
    Args:
        func: 被装饰的函数
        
    Returns:
        Callable: 包装后的函数
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except SmartCourseError as e:
            # 已知异常，直接抛出
            raise e
        except Exception as e:
            # 未知异常，包装为SmartCourseError
            raise SmartCourseError(f"内部错误: {str(e)}")
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SmartCourseError as e:
            # 已知异常，直接抛出
            raise e
        except Exception as e:
            # 未知异常，包装为SmartCourseError
            raise SmartCourseError(f"内部错误: {str(e)}")
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


# ============================================================================
# 配置验证
# ============================================================================

def validate_config(config_dict: Dict[str, Any]) -> List[str]:
    """
    验证配置
    
    Args:
        config_dict: 配置字典
        
    Returns:
        List[str]: 错误消息列表
    """
    errors = []
    
    # 检查必需字段
    required_fields = ["database", "service"]
    for field in required_fields:
        if field not in config_dict:
            errors.append(f"缺少必需字段: {field}")
    
    # 检查数据库配置
    if "database" in config_dict:
        db_config = config_dict["database"]
        if "postgres_url" not in db_config:
            errors.append("数据库配置缺少postgres_url")
    
    # 检查服务配置
    if "service" in config_dict:
        service_config = config_dict["service"]
        if "service_name" not in service_config:
            errors.append("服务配置缺少service_name")
        if "service_port" not in service_config:
            errors.append("服务配置缺少service_port")
    
    return errors


# ============================================================================
# 主函数
# ============================================================================

if __name__ == "__main__":
    # 测试工具函数
    logger = setup_logger("test")
    logger.info("工具模块测试开始")
    
    # 测试文本处理
    text = "这是一个测试文本，用于测试工具函数。"
    keywords = extract_keywords(text)
    print(f"关键词: {keywords}")
    
    # 测试时间格式化
    duration = 3665
    formatted = format_duration(duration)
    print(f"时长格式化: {formatted}")
    
    # 测试向量计算
    vec1 = [1, 2, 3]
    vec2 = [4, 5, 6]
    similarity = cosine_similarity(vec1, vec2)
    print(f"余弦相似度: {similarity}")
    
    logger.info("工具模块测试完成")