#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能优化模块 (Performance Optimizer)
=====================================

提供缓存、批处理、异步操作等性能优化功能。

主要优化点：
1. LRU 缓存 - 避免重复 API 调用
2. 批量 Embedding - 减少网络请求次数
3. 异步处理 - 提高并发能力
4. 结果预计算 - 加速热门查询

作者: SmartCourseEngine Team
日期: 2026-01-31
"""

import os
import json
import hashlib
import asyncio
import time
from pathlib import Path
from functools import lru_cache, wraps
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import OrderedDict
import threading


# ============================================================================
# 缓存配置
# ============================================================================
CACHE_DIR = Path(__file__).parent / ".cache"
CACHE_TTL_HOURS = 24  # 缓存过期时间（小时）
MAX_MEMORY_CACHE_SIZE = 100  # 内存缓存最大条目数


# ============================================================================
# 磁盘缓存装饰器
# ============================================================================
class DiskCache:
    """
    磁盘缓存类
    
    将 API 调用结果缓存到磁盘，避免重复调用。
    """
    
    def __init__(self, cache_dir: Path = CACHE_DIR, ttl_hours: int = CACHE_TTL_HOURS):
        self.cache_dir = cache_dir
        self.ttl = timedelta(hours=ttl_hours)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """生成缓存键"""
        key_data = {
            "func": func_name,
            "args": str(args),
            "kwargs": str(sorted(kwargs.items()))
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{cache_key}.json"
    
    def get(self, func_name: str, args: tuple, kwargs: dict) -> Optional[Any]:
        """获取缓存值"""
        cache_key = self._get_cache_key(func_name, args, kwargs)
        cache_path = self._get_cache_path(cache_key)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cached = json.load(f)
            
            # 检查是否过期
            cached_time = datetime.fromisoformat(cached["timestamp"])
            if datetime.now() - cached_time > self.ttl:
                cache_path.unlink()  # 删除过期缓存
                return None
            
            return cached["value"]
        except Exception:
            return None
    
    def set(self, func_name: str, args: tuple, kwargs: dict, value: Any):
        """设置缓存值"""
        cache_key = self._get_cache_key(func_name, args, kwargs)
        cache_path = self._get_cache_path(cache_key)
        
        try:
            cached = {
                "timestamp": datetime.now().isoformat(),
                "value": value
            }
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cached, f, ensure_ascii=False, indent=2)
        except Exception:
            pass  # 缓存写入失败不影响正常流程
    
    def clear(self):
        """清空缓存"""
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
            except Exception:
                pass


# 全局磁盘缓存实例
_disk_cache = DiskCache()


def disk_cache(func: Callable) -> Callable:
    """磁盘缓存装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 尝试从缓存获取
        cached = _disk_cache.get(func.__name__, args, kwargs)
        if cached is not None:
            return cached
        
        # 调用原函数
        result = func(*args, **kwargs)
        
        # 缓存结果
        if result is not None:
            _disk_cache.set(func.__name__, args, kwargs, result)
        
        return result
    
    return wrapper


# ============================================================================
# LRU 内存缓存
# ============================================================================
class LRUCache:
    """
    线程安全的 LRU 内存缓存
    """
    
    def __init__(self, max_size: int = MAX_MEMORY_CACHE_SIZE):
        self.max_size = max_size
        self.cache = OrderedDict()
        self.lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self.lock:
            if key in self.cache:
                # 移动到末尾（最近使用）
                self.cache.move_to_end(key)
                return self.cache[key]
            return None
    
    def set(self, key: str, value: Any):
        """设置缓存值"""
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            else:
                if len(self.cache) >= self.max_size:
                    # 移除最老的项
                    self.cache.popitem(last=False)
            self.cache[key] = value
    
    def clear(self):
        """清空缓存"""
        with self.lock:
            self.cache.clear()
    
    def __len__(self):
        return len(self.cache)


# 全局 LRU 缓存
_lru_cache = LRUCache()


def memory_cache(key_func: Callable = None):
    """内存缓存装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # 尝试从缓存获取
            cached = _lru_cache.get(cache_key)
            if cached is not None:
                return cached
            
            # 调用原函数
            result = func(*args, **kwargs)
            
            # 缓存结果
            if result is not None:
                _lru_cache.set(cache_key, result)
            
            return result
        
        return wrapper
    
    return decorator


# ============================================================================
# 批量处理器
# ============================================================================
@dataclass
class BatchProcessor:
    """
    批量处理器
    
    将多个小任务合并为批量操作，减少 API 调用次数。
    """
    
    batch_size: int = 10
    max_wait_seconds: float = 0.5
    
    def process_in_batches(
        self,
        items: List[Any],
        processor: Callable[[List[Any]], List[Any]],
        progress_callback: Callable[[int, int], None] = None
    ) -> List[Any]:
        """
        批量处理项目
        
        Args:
            items: 待处理项目列表
            processor: 批量处理函数
            progress_callback: 进度回调 (current, total)
            
        Returns:
            处理结果列表
        """
        results = []
        total = len(items)
        
        for i in range(0, total, self.batch_size):
            batch = items[i:i + self.batch_size]
            batch_results = processor(batch)
            results.extend(batch_results)
            
            if progress_callback:
                progress_callback(min(i + self.batch_size, total), total)
        
        return results


# ============================================================================
# 性能计时器
# ============================================================================
@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    operation: str
    duration_ms: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    details: Dict = field(default_factory=dict)


class PerformanceTimer:
    """
    性能计时器
    
    用于测量代码块的执行时间。
    """
    
    def __init__(self, operation: str, details: Dict = None):
        self.operation = operation
        self.details = details or {}
        self.start_time = None
        self.end_time = None
        self.metrics = []
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        duration_ms = (self.end_time - self.start_time) * 1000
        
        metric = PerformanceMetrics(
            operation=self.operation,
            duration_ms=duration_ms,
            details=self.details
        )
        self.metrics.append(metric)
        
        # 记录到全局性能日志
        _performance_log.append(metric)
        
        return False
    
    @property
    def duration_ms(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0


# 全局性能日志
_performance_log: List[PerformanceMetrics] = []


def get_performance_summary() -> Dict:
    """获取性能统计摘要"""
    if not _performance_log:
        return {"message": "暂无性能数据"}
    
    # 按操作分组
    operations = {}
    for metric in _performance_log:
        if metric.operation not in operations:
            operations[metric.operation] = []
        operations[metric.operation].append(metric.duration_ms)
    
    summary = {}
    for op, durations in operations.items():
        summary[op] = {
            "count": len(durations),
            "total_ms": sum(durations),
            "avg_ms": sum(durations) / len(durations),
            "min_ms": min(durations),
            "max_ms": max(durations)
        }
    
    return summary


def clear_performance_log():
    """清空性能日志"""
    global _performance_log
    _performance_log = []


# ============================================================================
# 异步执行器
# ============================================================================
class AsyncExecutor:
    """
    异步执行器
    
    提供简单的异步任务执行能力。
    """
    
    @staticmethod
    async def run_async(func: Callable, *args, **kwargs) -> Any:
        """在异步环境中运行同步函数"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
    
    @staticmethod
    async def run_parallel(tasks: List[Callable]) -> List[Any]:
        """并行执行多个任务"""
        async def wrap(task):
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, task)
        
        return await asyncio.gather(*[wrap(t) for t in tasks])
    
    @staticmethod
    def run_in_background(func: Callable, *args, **kwargs) -> threading.Thread:
        """在后台线程运行任务"""
        thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        return thread


# ============================================================================
# 优化的 Embedding 批量处理
# ============================================================================
class OptimizedEmbedding:
    """
    优化的 Embedding 处理器
    
    支持批量处理和缓存。
    """
    
    def __init__(self, embedding_func: Callable, batch_size: int = 20):
        self.embedding_func = embedding_func
        self.batch_size = batch_size
        self.cache = LRUCache(max_size=500)
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        批量生成 Embedding
        
        Args:
            texts: 文本列表
            
        Returns:
            Embedding 向量列表
        """
        results = [None] * len(texts)
        uncached_indices = []
        uncached_texts = []
        
        # 检查缓存
        for i, text in enumerate(texts):
            cache_key = hashlib.md5(text.encode()).hexdigest()
            cached = self.cache.get(cache_key)
            if cached is not None:
                results[i] = cached
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)
        
        # 批量处理未缓存的文本
        if uncached_texts:
            processor = BatchProcessor(batch_size=self.batch_size)
            embeddings = processor.process_in_batches(
                uncached_texts,
                self.embedding_func
            )
            
            # 存入缓存和结果
            for idx, (orig_idx, text) in enumerate(zip(uncached_indices, uncached_texts)):
                embedding = embeddings[idx]
                cache_key = hashlib.md5(text.encode()).hexdigest()
                self.cache.set(cache_key, embedding)
                results[orig_idx] = embedding
        
        return results


# ============================================================================
# 预热缓存
# ============================================================================
def warm_up_cache(topics: List[str], search_func: Callable):
    """
    预热缓存
    
    对常见查询进行预计算，加速后续检索。
    
    Args:
        topics: 热门主题列表
        search_func: 搜索函数
    """
    for topic in topics:
        with PerformanceTimer("cache_warm_up", {"topic": topic}):
            search_func(topic)


# ============================================================================
# 导出工具函数
# ============================================================================
def get_cache_stats() -> Dict:
    """获取缓存统计信息"""
    cache_files = list(CACHE_DIR.glob("*.json")) if CACHE_DIR.exists() else []
    
    return {
        "disk_cache": {
            "path": str(CACHE_DIR),
            "file_count": len(cache_files),
            "total_size_kb": sum(f.stat().st_size for f in cache_files) / 1024
        },
        "memory_cache": {
            "current_size": len(_lru_cache),
            "max_size": MAX_MEMORY_CACHE_SIZE
        }
    }


def clear_all_caches():
    """清空所有缓存"""
    _disk_cache.clear()
    _lru_cache.clear()
    clear_performance_log()
