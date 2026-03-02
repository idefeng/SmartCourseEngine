#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
搜索服务
========

提供全文搜索、向量搜索、混合搜索等功能。

作者: SmartCourseEngine Team
日期: 2026-03-01
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status, Query
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
cfg.service.service_name = "search-engine"
cfg.service.service_port = 8004

# 设置日志
logger = setup_logger(
    name="search-engine",
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
    logger.info(f"🚀 启动搜索服务: {cfg.service.service_name}")
    logger.info(f"📊 服务端口: {cfg.service.service_port}")
    
    # 创建必要的目录
    data_dir = Path(cfg.service.data_dir)
    index_dir = data_dir / "index"
    cache_dir = data_dir / "cache"
    
    for directory in [data_dir, index_dir, cache_dir]:
        directory.mkdir(parents=True, exist_ok=True)
        logger.debug(f"创建目录: {directory}")
    
    # 初始化搜索索引（延迟加载）
    logger.info("🔍 准备搜索索引（延迟加载）")
    
    yield
    
    # 关闭时
    logger.info("👋 关闭搜索服务")

# ============================================================================
# FastAPI应用
# ============================================================================

app = FastAPI(
    title="SmartCourseEngine Search Engine",
    version="1.0.0",
    description="搜索服务 - 提供全文搜索、向量搜索、混合搜索",
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
# 搜索服务
# ============================================================================

class SearchEngine:
    """搜索服务类"""
    
    def __init__(self):
        self.embedding_model = None
        self.search_index = None
        self.vector_index = None
    
    async def load_models(self):
        """加载AI模型和搜索索引（延迟加载）"""
        try:
            logger.info("准备搜索模型...")
            
            # 在开发环境中使用模拟模式
            if cfg.service.debug:
                logger.warning("使用模拟模式（开发环境）")
                self.embedding_model = "mock"
                self.search_index = "mock"
                self.vector_index = "mock"
            else:
                # 实际模型加载逻辑
                logger.info("加载嵌入模型...")
                from sentence_transformers import SentenceTransformer
                self.embedding_model = SentenceTransformer(cfg.ai.embedding_model)
                
                logger.info("初始化搜索索引...")
                self._init_search_index()
                
                logger.info("搜索模型加载完成")
                
        except Exception as e:
            logger.error(f"搜索模型加载失败: {e}")
            # 使用模拟模式
            self.embedding_model = "mock"
            self.search_index = "mock"
            self.vector_index = "mock"
    
    def _init_search_index(self):
        """初始化搜索索引"""
        # 这里可以初始化Elasticsearch、Whoosh等搜索索引
        # 目前使用内存中的模拟索引
        self.search_index = {
            "courses": [],
            "knowledge_points": [],
            "documents": []
        }
    
    async def text_search(self, query: str, 
                         search_type: str = "hybrid",
                         limit: int = 10) -> Dict[str, Any]:
        """文本搜索
        
        Args:
            query: 搜索查询
            search_type: 搜索类型 (text/vector/hybrid)
            limit: 返回结果数量限制
            
        Returns:
            Dict[str, Any]: 搜索结果
        """
        try:
            logger.info(f"开始搜索: '{query}' (类型: {search_type})")
            
            if self.search_index == "mock":
                # 模拟搜索结果
                return self._mock_text_search(query, search_type, limit)
            
            # 实际搜索逻辑
            results = []
            
            if search_type in ["text", "hybrid"]:
                # 全文搜索
                text_results = self._full_text_search(query, limit)
                results.extend(text_results)
            
            if search_type in ["vector", "hybrid"]:
                # 向量搜索
                vector_results = await self._vector_search(query, limit)
                results.extend(vector_results)
            
            # 去重和排序
            unique_results = self._deduplicate_results(results)
            sorted_results = self._rank_results(unique_results, query)
            
            logger.info(f"搜索完成，找到 {len(sorted_results)} 个结果")
            
            return {
                "query": query,
                "search_type": search_type,
                "results": sorted_results[:limit],
                "total": len(sorted_results),
                "search_time": "2026-03-01T20:37:00Z"
            }
            
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            # 返回模拟搜索结果
            return self._mock_text_search(query, search_type, limit)
    
    def _mock_text_search(self, query: str, 
                         search_type: str = "hybrid",
                         limit: int = 10) -> Dict[str, Any]:
        """模拟文本搜索"""
        mock_results = [
            {
                "id": "course_1",
                "type": "course",
                "title": "Python编程入门",
                "description": "学习Python基础编程知识，从零开始掌握Python编程",
                "relevance": 0.95,
                "score": 0.92,
                "metadata": {
                    "course_id": 1,
                    "author": "智能课程团队",
                    "language": "zh-CN",
                    "knowledge_points": 4
                }
            },
            {
                "id": "kp_1",
                "type": "knowledge_point",
                "title": "变量和数据类型",
                "description": "学习Python中的变量声明和基本数据类型",
                "relevance": 0.88,
                "score": 0.85,
                "metadata": {
                    "course_id": 1,
                    "start_time": 0,
                    "end_time": 300,
                    "category": "编程基础"
                }
            },
            {
                "id": "kp_2",
                "type": "knowledge_point",
                "title": "条件语句",
                "description": "学习if-else条件判断",
                "relevance": 0.75,
                "score": 0.72,
                "metadata": {
                    "course_id": 1,
                    "start_time": 300,
                    "end_time": 600,
                    "category": "控制流"
                }
            },
            {
                "id": "document_1",
                "type": "document",
                "title": "Python基础语法指南",
                "description": "Python基础语法和编程规范",
                "relevance": 0.82,
                "score": 0.78,
                "metadata": {
                    "format": "pdf",
                    "pages": 25,
                    "language": "zh-CN"
                }
            }
        ]
        
        # 根据查询调整相关性
        query_lower = query.lower()
        for result in mock_results:
            if "python" in query_lower and "python" in result["title"].lower():
                result["relevance"] = min(result["relevance"] + 0.1, 1.0)
                result["score"] = min(result["score"] + 0.1, 1.0)
        
        # 按相关性排序
        sorted_results = sorted(mock_results, key=lambda x: x["relevance"], reverse=True)
        
        return {
            "query": query,
            "search_type": search_type,
            "results": sorted_results[:limit],
            "total": len(sorted_results),
            "search_time": "2026-03-01T20:37:00Z"
        }
    
    def _full_text_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """全文搜索（模拟）"""
        # 在实际应用中，这里应该连接Elasticsearch或Whoosh等搜索引擎
        return []
    
    async def _vector_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """向量搜索（模拟）"""
        # 在实际应用中，这里应该使用向量数据库进行相似性搜索
        return []
    
    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重搜索结果"""
        seen_ids = set()
        unique_results = []
        
        for result in results:
            if result["id"] not in seen_ids:
                unique_results.append(result)
                seen_ids.add(result["id"])
        
        return unique_results
    
    def _rank_results(self, results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """排序搜索结果"""
        # 简单的排序逻辑：按相关性排序
        return sorted(results, key=lambda x: x.get("relevance", 0), reverse=True)
    
    async def semantic_search(self, query: str, 
                            search_type: str = "semantic",
                            limit: int = 10) -> Dict[str, Any]:
        """语义搜索
        
        Args:
            query: 搜索查询
            search_type: 搜索类型
            limit: 返回结果数量限制
            
        Returns:
            Dict[str, Any]: 语义搜索结果
        """
        try:
            logger.info(f"开始语义搜索: '{query}'")
            
            # 生成查询嵌入
            if self.embedding_model == "mock":
                query_embedding = [0.1 * i for i in range(10)]
            else:
                query_embedding = self.embedding_model.encode([query])[0].tolist()
            
            # 模拟语义搜索结果
            semantic_results = [
                {
                    "id": "semantic_1",
                    "type": "semantic_match",
                    "title": "Python编程概念",
                    "description": "与查询相关的Python编程概念和知识点",
                    "relevance": 0.92,
                    "score": 0.89,
                    "similarity": 0.87,
                    "metadata": {
                        "embedding_similarity": 0.87,
                        "concepts": ["变量", "函数", "循环", "条件"]
                    }
                },
                {
                    "id": "semantic_2",
                    "type": "semantic_match",
                    "title": "编程基础教学",
                    "description": "编程基础知识和教学资源",
                    "relevance": 0.85,
                    "score": 0.82,
                    "similarity": 0.79,
                    "metadata": {
                        "embedding_similarity": 0.79,
                        "concepts": ["基础", "教学", "入门"]
                    }
                }
            ]
            
            # 根据查询调整
            query_lower = query.lower()
            for result in semantic_results:
                if "编程" in query_lower or "programming" in query_lower:
                    result["similarity"] = min(result["similarity"] + 0.05, 1.0)
                    result["relevance"] = min(result["relevance"] + 0.05, 1.0)
            
            # 按相似度排序
            sorted_results = sorted(semantic_results, key=lambda x: x["similarity"], reverse=True)
            
            logger.info(f"语义搜索完成，找到 {len(sorted_results)} 个结果")
            
            return {
                "query": query,
                "search_type": search_type,
                "query_embedding": query_embedding[:5],  # 只返回前5维用于展示
                "results": sorted_results[:limit],
                "total": len(sorted_results),
                "search_time": "2026-03-01T20:37:00Z"
            }
            
        except Exception as e:
            logger.error(f"语义搜索失败: {e}")
            raise
    
    async def hybrid_search(self, query: str, 
                          weights: Dict[str, float] = None,
                          limit: int = 10) -> Dict[str, Any]:
        """混合搜索（结合文本和语义搜索）
        
        Args:
            query: 搜索查询
            weights: 各搜索类型的权重
            limit: 返回结果数量限制
            
        Returns:
            Dict[str, Any]: 混合搜索结果
        """
        try:
            logger.info(f"开始混合搜索: '{query}'")
            
            # 默认权重
            if weights is None:
                weights = {
                    "text": 0.4,
                    "vector": 0.4,
                    "semantic": 0.2
                }
            
            # 并行执行各种搜索
            tasks = [
                self.text_search(query, "text", limit * 2),
                self.text_search(query, "vector", limit * 2),
                self.semantic_search(query, "semantic", limit * 2)
            ]
            
            search_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 合并结果
            all_results = []
            result_types = ["text", "vector", "semantic"]
            
            for i, result in enumerate(search_results):
                if isinstance(result, Exception):
                    logger.error(f"{result_types[i]}搜索失败: {result}")
                    continue
                
                for item in result.get("results", []):
                    # 添加搜索类型和权重
                    item["search_type"] = result_types[i]
                    item["weighted_score"] = item.get("score", 0) * weights.get(result_types[i], 0.33)
                    all_results.append(item)
            
            # 去重和排序
            unique_results = self._deduplicate_results(all_results)
            sorted_results = sorted(unique_results, key=lambda x: x.get("weighted_score", 0), reverse=True)
            
            logger.info(f"混合搜索完成，找到 {len(sorted_results)} 个结果")
            
            return {
                "query": query,
                "search_type": "hybrid",
                "weights": weights,
                "results": sorted_results[:limit],
                "total": len(sorted_results),
                "search_time": "2026-03-01T20:37:00Z"
            }
            
        except Exception as e:
            logger.error(f"混合搜索失败: {e}")
            raise

# 全局搜索引擎实例
search_engine = SearchEngine()

# ============================================================================
# API路由
# ============================================================================

@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "SmartCourseEngine Search Engine",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "search": "/api/v1/search",
            "semantic": "/api/v1/search/semantic",
            "hybrid": "/api/v1/search/hybrid"
        }
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": cfg.service.service_name,
        "timestamp": "2026-03-01T20:37:00Z",
        "models_loaded": search_engine.embedding_model is not None
    }

@app.get("/api/v1/search")
async def search(
    query: str = Query(..., description="搜索查询"),
    search_type: str = Query("hybrid", description="搜索类型 (text/vector/hybrid)"),
    limit: int = Query(10, ge=1, le=100, description="结果数量限制")
):
    """通用搜索"""
    try:
        # 确保模型已加载
        if search_engine.search_index is None:
            await search_engine.load_models()
        
        logger.info(f"搜索请求: '{query}' (类型: {search_type})")
        
        # 执行搜索
        if search_type == "semantic":
            result = await search_engine.semantic_search(query, search_type, limit)
        elif search_type == "hybrid":
            result = await search_engine.hybrid_search(query, limit=limit)
        else:
            result = await search_engine.text_search(query, search_type, limit)
        
        return {
            "success": True,
            "message": "搜索完成",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜索失败: {str(e)}"
        )

@app.get("/api/v1/search/knowledge")
async def search_knowledge(
    query: str = Query(..., description="知识点搜索查询"),
    course_id: int = Query(None, description="课程ID筛选"),
    category: str = Query(None, description="知识点类别筛选"),
    limit: int = Query(10, ge=1, le=100, description="结果数量限制")
):
    """知识点搜索"""
    try:
        # 确保模型已加载
        if search_engine.search_index is None:
            await search_engine.load_models()
        
        logger.info(f"知识点搜索: '{query}' (课程ID: {course_id}, 类别: {category})")
        
        # 执行搜索
        search_result = await search_engine.text_search(query, "hybrid", limit * 2)
        
        # 筛选结果
        filtered_results = []
        for item in search_result.get("results", []):
            # 按类型筛选
            if item.get("type") != "knowledge_point":
                continue
            
            # 按课程ID筛选
            if course_id is not None:
                metadata = item.get("metadata", {})
                if metadata.get("course_id") != course_id:
                    continue
            
            # 按类别筛选
            if category is not None:
                metadata = item.get("metadata", {})
                if metadata.get("category") != category:
                    continue
            
            filtered_results.append(item)
        
        # 构建响应
        result = {
            "query": query,
            "search_type": "knowledge",
            "filters": {
                "course_id": course_id,
                "category": category
            },
            "results": filtered_results[:limit],
            "total": len(filtered_results),
            "search_time": "2026-03-01T20:37:00Z"
        }
        
        return {
            "success": True,
            "message": "知识点搜索完成",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"知识点搜索失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"知识点搜索失败: {str(e)}"
        )

@app.get("/api/v1/search/courses")
async def search_courses(
    query: str = Query(..., description="课程搜索查询"),
    language: str = Query(None, description="语言筛选"),
    is_published: bool = Query(None, description="是否已发布"),
    limit: int = Query(10, ge=1, le=100, description="结果数量限制")
):
    """课程搜索"""
    try:
        # 确保模型已加载
        if search_engine.search_index is None:
            await search_engine.load_models()
        
        logger.info(f"课程搜索: '{query}' (语言: {language}, 已发布: {is_published})")
        
        # 执行搜索
        search_result = await search_engine.text_search(query, "hybrid", limit * 2)
        
        # 筛选结果
        filtered_results = []
        for item in search_result.get("results", []):
            # 按类型筛选
            if item.get("type") != "course":
                continue
            
            # 按语言筛选
            if language is not None:
                metadata = item.get("metadata", {})
                if metadata.get("language") != language:
                    continue
            
            # 按发布状态筛选
            if is_published is not None:
                # 这里需要根据实际数据结构调整
                pass
            
            filtered_results.append(item)
        
        # 构建响应
        result = {
            "query": query,
            "search_type": "course",
            "filters": {
                "language": language,
                "is_published": is_published
            },
            "results": filtered_results[:limit],
            "total": len(filtered_results),
            "search_time": "2026-03-01T20:37:00Z"
        }
        
        return {
            "success": True,
            "message": "课程搜索完成",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"课程搜索失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"课程搜索失败: {str(e)}"
        )

# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数"""
    logger.info(f"🚀 启动搜索服务: {cfg.service.service_name}")
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