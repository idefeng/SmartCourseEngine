#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
推荐服务 (Recommendation Service)
端口: 8005

基于AI的个性化推荐服务，支持：
1. 基于用户行为的协同过滤
2. 基于内容的推荐
3. 基于知识图谱的推荐
4. 混合推荐策略

作者: SmartCourseEngine Team
日期: 2026-03-07
"""

import os
import sys
import json
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel, Field

# ============================================================================
# 配置和路径设置
# ============================================================================

# 获取项目根目录
project_root = Path(__file__).parent.parent
shared_path = project_root / "shared"

# 添加路径到sys.path
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(shared_path))

print(f"项目根目录: {project_root}")
print(f"共享模块路径: {shared_path}")

# ============================================================================
# 导入共享模块
# ============================================================================

try:
    from shared.api_response import (
        ApiResponse,
        success_response,
        error_response,
        ErrorCode,
    )
    from shared.config import get_settings
    from shared.database import get_db, DatabaseManager
    from shared.models import Course, KnowledgePoint, User, UserInteraction
    from shared.auth import get_current_user
    API_RESPONSE_ENABLED = True
    print("✅ 共享模块导入成功")
except ImportError as e:
    print(f"⚠️  共享模块导入失败: {e}")
    API_RESPONSE_ENABLED = False
    
    # 创建简化版本
    class ErrorCode:
        UNKNOWN_ERROR = ("0000", "未知错误")
        VALIDATION_ERROR = ("0001", "参数验证失败")
        DATABASE_ERROR = ("0002", "数据库错误")
        RESOURCE_NOT_FOUND = ("0005", "资源不存在")
        RECOMMENDATION_FAILED = ("8005", "推荐失败")
    
    def success_response(data: Any = None, message: str = "操作成功"):
        return {
            "success": True,
            "message": message,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def error_response(
        error_code: ErrorCode,
        message: str = "操作失败",
        details: Dict[str, Any] = None
    ):
        return {
            "success": False,
            "message": message,
            "error_code": error_code[0],
            "error_message": error_code[1],
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat()
        }

# ============================================================================
# 数据模型
# ============================================================================

class RecommendationRequest(BaseModel):
    """推荐请求"""
    user_id: Optional[int] = Field(None, description="用户ID，如果不提供则使用匿名推荐")
    course_id: Optional[int] = Field(None, description="课程ID，用于基于内容的推荐")
    knowledge_point_id: Optional[int] = Field(None, description="知识点ID，用于知识图谱推荐")
    strategy: str = Field("hybrid", description="推荐策略: collaborative, content, knowledge_graph, hybrid")
    limit: int = Field(10, description="返回推荐数量")
    include_explanations: bool = Field(True, description="是否包含推荐解释")

class RecommendedItem(BaseModel):
    """推荐项"""
    id: int
    type: str  # course, knowledge_point, video
    title: str
    description: str
    score: float  # 推荐分数 0-1
    explanation: Optional[str] = None  # 推荐解释
    metadata: Dict[str, Any] = {}

class RecommendationResponse(BaseModel):
    """推荐响应"""
    user_id: Optional[int]
    strategy: str
    recommendations: List[RecommendedItem]
    generated_at: datetime

# ============================================================================
# 服务配置
# ============================================================================

settings = get_settings()
SERVICE_NAME = "recommendation"
SERVICE_PORT = 8005

# ============================================================================
# 推荐引擎
# ============================================================================

class RecommendationEngine:
    """推荐引擎"""
    
    def __init__(self):
        self.user_profiles = {}  # 用户画像缓存
        self.course_similarity = {}  # 课程相似度缓存
        self.last_update = None
        
    async def initialize(self):
        """初始化推荐引擎"""
        print("🧠 初始化推荐引擎...")
        await self.load_sample_data()
        self.last_update = datetime.utcnow()
        print("✅ 推荐引擎初始化完成")
    
    async def load_sample_data(self):
        """加载样本数据"""
        # 模拟用户-课程交互矩阵
        self.user_course_matrix = {
            1: {1: 5, 2: 3, 3: 4},  # 用户1对课程1评分5，课程2评分3，课程3评分4
            2: {2: 4, 3: 5, 4: 3},
            3: {1: 2, 4: 5, 5: 4},
            4: {3: 3, 5: 5, 6: 4},
            5: {2: 5, 6: 4, 7: 3},
        }
        
        # 模拟课程特征
        self.course_features = {
            1: {"tags": ["python", "编程", "基础"], "difficulty": "beginner", "duration": 120},
            2: {"tags": ["python", "高级", "算法"], "difficulty": "intermediate", "duration": 180},
            3: {"tags": ["机器学习", "AI", "python"], "difficulty": "advanced", "duration": 240},
            4: {"tags": ["数据分析", "pandas", "可视化"], "difficulty": "intermediate", "duration": 150},
            5: {"tags": ["深度学习", "pytorch", "神经网络"], "difficulty": "advanced", "duration": 300},
            6: {"tags": ["web开发", "django", "后端"], "difficulty": "intermediate", "duration": 200},
            7: {"tags": ["前端", "react", "javascript"], "difficulty": "beginner", "duration": 160},
        }
        
        # 模拟知识图谱关系
        self.knowledge_graph = {
            1: {"name": "Python基础", "related": [2, 4], "prerequisites": []},
            2: {"name": "Python高级", "related": [1, 3], "prerequisites": [1]},
            3: {"name": "机器学习", "related": [2, 5], "prerequisites": [2]},
            4: {"name": "数据分析", "related": [1, 6], "prerequisites": [1]},
            5: {"name": "深度学习", "related": [3, 7], "prerequisites": [3]},
            6: {"name": "Web开发", "related": [4, 7], "prerequisites": [1]},
            7: {"name": "前端开发", "related": [6], "prerequisites": [1]},
        }
    
    def calculate_cosine_similarity(self, vec1: Dict[int, float], vec2: Dict[int, float]) -> float:
        """计算余弦相似度"""
        common_keys = set(vec1.keys()) & set(vec2.keys())
        if not common_keys:
            return 0.0
        
        dot_product = sum(vec1[k] * vec2[k] for k in common_keys)
        norm1 = np.sqrt(sum(v ** 2 for v in vec1.values()))
        norm2 = np.sqrt(sum(v ** 2 for v in vec2.values()))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    async def collaborative_filtering(self, user_id: int, limit: int = 10) -> List[RecommendedItem]:
        """协同过滤推荐"""
        if user_id not in self.user_course_matrix:
            return []
        
        user_ratings = self.user_course_matrix[user_id]
        recommendations = []
        
        # 找到相似用户
        similar_users = []
        for other_user_id, other_ratings in self.user_course_matrix.items():
            if other_user_id == user_id:
                continue
            
            similarity = self.calculate_cosine_similarity(user_ratings, other_ratings)
            if similarity > 0:
                similar_users.append((other_user_id, similarity))
        
        # 按相似度排序
        similar_users.sort(key=lambda x: x[1], reverse=True)
        
        # 生成推荐
        recommended_courses = {}
        for other_user_id, similarity in similar_users[:5]:  # 取前5个相似用户
            other_ratings = self.user_course_matrix[other_user_id]
            
            for course_id, rating in other_ratings.items():
                if course_id not in user_ratings:  # 用户还没看过
                    if course_id not in recommended_courses:
                        recommended_courses[course_id] = 0
                    recommended_courses[course_id] += similarity * rating
        
        # 转换为推荐项
        for course_id, score in sorted(recommended_courses.items(), key=lambda x: x[1], reverse=True)[:limit]:
            recommendations.append(
                RecommendedItem(
                    id=course_id,
                    type="course",
                    title=f"课程 {course_id}",
                    description=f"基于协同过滤推荐: 相似用户也喜欢这门课程",
                    score=min(score / 10, 1.0),  # 归一化到0-1
                    explanation=f"与您学习习惯相似的{len(similar_users)}个用户也学习了这门课程",
                    metadata=self.course_features.get(course_id, {})
                )
            )
        
        return recommendations
    
    async def content_based_recommendation(self, course_id: int, limit: int = 10) -> List[RecommendedItem]:
        """基于内容的推荐"""
        if course_id not in self.course_features:
            return []
        
        target_features = self.course_features[course_id]
        recommendations = []
        
        # 计算与其他课程的相似度
        similarities = []
        for other_course_id, other_features in self.course_features.items():
            if other_course_id == course_id:
                continue
            
            # 简单相似度计算（基于标签匹配）
            target_tags = set(target_features.get("tags", []))
            other_tags = set(other_features.get("tags", []))
            
            if target_tags and other_tags:
                tag_similarity = len(target_tags & other_tags) / len(target_tags | other_tags)
                
                # 难度相似度
                difficulty_similarity = 1.0 if target_features.get("difficulty") == other_features.get("difficulty") else 0.5
                
                # 综合相似度
                similarity = (tag_similarity * 0.7 + difficulty_similarity * 0.3)
                similarities.append((other_course_id, similarity))
        
        # 按相似度排序
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        for other_course_id, similarity in similarities[:limit]:
            other_features = self.course_features[other_course_id]
            recommendations.append(
                RecommendedItem(
                    id=other_course_id,
                    type="course",
                    title=f"课程 {other_course_id}",
                    description=f"基于内容推荐: 与课程{course_id}相似",
                    score=similarity,
                    explanation=f"这门课程与您正在学习的课程在内容和难度上相似",
                    metadata=other_features
                )
            )
        
        return recommendations
    
    async def knowledge_graph_recommendation(self, knowledge_point_id: int, limit: int = 10) -> List[RecommendedItem]:
        """基于知识图谱的推荐"""
        if knowledge_point_id not in self.knowledge_graph:
            return []
        
        target_node = self.knowledge_graph[knowledge_point_id]
        recommendations = []
        
        # 推荐相关知识点
        for related_id in target_node.get("related", [])[:limit]:
            if related_id in self.knowledge_graph:
                related_node = self.knowledge_graph[related_id]
                recommendations.append(
                    RecommendedItem(
                        id=related_id,
                        type="knowledge_point",
                        title=related_node["name"],
                        description=f"相关知识点: {related_node['name']}",
                        score=0.8,  # 相关知识点分数较高
                        explanation=f"这个知识点与您正在学习的'{target_node['name']}'密切相关",
                        metadata={"relation_type": "related"}
                    )
                )
        
        # 推荐前置知识点
        for prereq_id in target_node.get("prerequisites", []):
            if prereq_id in self.knowledge_graph:
                prereq_node = self.knowledge_graph[prereq_id]
                recommendations.append(
                    RecommendedItem(
                        id=prereq_id,
                        type="knowledge_point",
                        title=prereq_node["name"],
                        description=f"前置知识点: {prereq_node['name']}",
                        score=0.9,  # 前置知识点分数最高
                        explanation=f"建议先学习这个前置知识点，以便更好地理解'{target_node['name']}'",
                        metadata={"relation_type": "prerequisite"}
                    )
                )
        
        return recommendations[:limit]
    
    async def hybrid_recommendation(self, user_id: Optional[int], course_id: Optional[int], 
                                   knowledge_point_id: Optional[int], limit: int = 10) -> List[RecommendedItem]:
        """混合推荐"""
        all_recommendations = []
        
        # 收集各种推荐结果
        if user_id:
            cf_recs = await self.collaborative_filtering(user_id, limit)
            all_recommendations.extend(cf_recs)
        
        if course_id:
            cb_recs = await self.content_based_recommendation(course_id, limit)
            all_recommendations.extend(cb_recs)
        
        if knowledge_point_id:
            kg_recs = await self.knowledge_graph_recommendation(knowledge_point_id, limit)
            all_recommendations.extend(kg_recs)
        
        # 如果没有特定输入，使用热门推荐
        if not all_recommendations:
            all_recommendations = await self.popular_recommendations(limit)
        
        # 去重和排序
        seen = set()
        unique_recs = []
        for rec in all_recommendations:
            key = (rec.id, rec.type)
            if key not in seen:
                seen.add(key)
                unique_recs.append(rec)
        
        # 按分数排序
        unique_recs.sort(key=lambda x: x.score, reverse=True)
        
        return unique_recs[:limit]
    
    async def popular_recommendations(self, limit: int = 10) -> List[RecommendedItem]:
        """热门推荐"""
        # 模拟热门课程
        popular_courses = [
            (1, "Python编程入门", "学习Python基础语法和编程思维", 0.95),
            (3, "机器学习实战", "从零开始学习机器学习算法", 0.92),
            (4, "数据分析与可视化", "使用Python进行数据分析和可视化", 0.88),
            (6, "Web开发全栈", "学习Django和React全栈开发", 0.85),
        ]
        
        recommendations = []
        for course_id, title, description, score in popular_courses[:limit]:
            recommendations.append(
                RecommendedItem(
                    id=course_id,
                    type="course",
                    title=title,
                    description=description,
                    score=score,
                    explanation="这是当前最受欢迎的课程之一",
                    metadata=self.course_features.get(course_id, {})
                )
            )
        
        return recommendations

# ============================================================================
# 生命周期管理
# ============================================================================

recommendation_engine = RecommendationEngine()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print(f"🚀 启动 {SERVICE_NAME} 服务，端口: {SERVICE_PORT}")
    
    # 启动时初始化
    await recommendation_engine.initialize()
    
    yield
    
    # 关闭时清理
    print(f"👋 关闭 {SERVICE_NAME} 服务")

# ============================================================================
# FastAPI应用
# ============================================================================

app = FastAPI(
    title="推荐服务",
    description="基于AI的个性化推荐服务",
    version="1.0.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# API端点
# ============================================================================

@app.get("/health")
async def health_check():
    """健康检查"""
    return success_response({
        "service": SERVICE_NAME,
        "status": "healthy",
        "port": SERVICE_PORT,
        "timestamp": datetime.utcnow().isoformat(),
        "engine_initialized": recommendation_engine.last_update is not None
    })

@app.get("/")
async def root():
    """根端点"""
    return success_response({
        "service": SERVICE_NAME,
        "description": "基于AI的个性化推荐服务",
        "version": "1.0.0",
        "strategies": [
            "collaborative - 协同过滤推荐",
            "content - 基于内容的推荐", 
            "knowledge_graph - 基于知识图谱的推荐",
            "hybrid - 混合推荐",
            "popular - 热门推荐"
        ],
        "endpoints": [
            "/health - 健康检查",
            "/docs - API文档",
            "/recommend - 获取推荐",
            "/strategies - 获取推荐策略"
        ]
    })

@app.get("/strategies")
async def get_strategies():
    """获取所有推荐策略"""
    strategies = [
        {
            "id": "collaborative",
            "name": "协同过滤推荐",
            "description": "基于用户行为相似度的推荐",
            "requires": ["user_id"],
            "best_for": "发现新内容，基于群体智慧"
        },
        {
            "id": "content",
            "name": "基于内容的推荐",
            "description": "基于内容相似度的推荐",
            "requires": ["course_id"],
            "best_for": "发现相似内容，深化学习"
        },
        {
            "id": "knowledge_graph",
            "name": "基于知识图谱的推荐",
            "description": "基于知识关联关系的推荐",
            "requires": ["knowledge_point_id"],
            "best_for": "系统化学习，构建知识体系"
        },
        {
            "id": "hybrid",
            "name": "混合推荐",
            "description": "综合多种策略的智能推荐",
            "requires": [],
            "best_for": "个性化推荐，综合最优"
        },
        {
            "id": "popular",
            "name": "热门推荐",
            "description": "基于热门度的推荐",
            "requires": [],
            "best_for": "新用户入门，发现热门内容"
        }
    ]
    
    return success_response(strategies, "推荐策略获取成功")

@app.post("/recommend")
async def get_recommendations(request: RecommendationRequest):
    """获取推荐"""
    try:
        recommendations = []
        
        if request.strategy == "collaborative":
            if not request.user_id:
                return error_response(ErrorCode.VALIDATION_ERROR, "协同过滤推荐需要user_id参数")
            recommendations = await recommendation_engine.collaborative_filtering(
                request.user_id, request.limit
            )
        
        elif request.strategy == "content":
            if not request.course_id:
                return error_response(ErrorCode.VALIDATION_ERROR, "基于内容的推荐需要course_id参数")
            recommendations = await recommendation_engine.content_based_recommendation(
                request.course_id, request.limit
            )
        
        elif request.strategy == "knowledge_graph":
            if not request.knowledge_point_id:
                return error_response(ErrorCode.VALIDATION_ERROR, "知识图谱推荐需要knowledge_point_id参数")
            recommendations = await recommendation_engine.knowledge_graph_recommendation(
                request.knowledge_point_id, request.limit
            )
        
        elif request.strategy == "hybrid":
            recommendations = await recommendation_engine.hybrid_recommendation(
                request.user_id, request.course_id, request.knowledge_point_id, request.limit
            )
        
        elif request.strategy == "popular":
            recommendations = await recommendation_engine.popular_recommendations(request.limit)
        
        else:
            return error_response(ErrorCode.VALIDATION_ERROR, f"不支持的推荐策略: {request.strategy}")
        
        # 如果不包含解释，移除解释字段
        if not request.include_explanations:
            for rec in recommendations:
                rec.explanation = None
        
        response = RecommendationResponse(
            user_id=request.user_id,
            strategy=request.strategy,
            recommendations=recommendations,
            generated_at=datetime.utcnow()
        )
        
        return success_response(response.dict(), "推荐获取成功")
        
    except Exception as e:
        return error_response(ErrorCode.RECOMMENDATION_FAILED, f"推荐失败: {str(e)}")

@app.get("/users/{user_id}/recommendations")
async def get_user_recommendations(
    user_id: int,
    strategy: str = Query("hybrid", description="推荐策略"),
    limit: int = Query(10, description="返回数量")
):
    """获取用户的推荐"""
    try:
        request = RecommendationRequest(
            user_id=user_id,
            strategy=strategy,
            limit=limit
        )
        
        return await get_recommendations(request)
        
    except Exception as e:
        return error_response(ErrorCode.RECOMMENDATION_FAILED, f"获取用户推荐失败: {str(e)}")

@app.get("/courses/{course_id}/related")
async def get_related_courses(
    course_id: int,
    limit: int = Query(5, description="返回数量")
):
    """获取相关课程"""
    try:
        recommendations = await recommendation_engine.content_based_recommendation(course_id, limit)
        
        return success_response(
            [rec.dict() for rec in recommendations],
            "相关课程获取成功"
        )
        
    except Exception as e:
        return error_response(ErrorCode.RECOMMENDATION_FAILED, f"获取相关课程失败: {str(e)}")

@app.get("/knowledge/{knowledge_point_id}/related")
async def get_related_knowledge(
    knowledge_point_id: int,
    limit: int = Query(5, description="返回数量")
):
    """获取相关知识"""
    try:
        recommendations = await recommendation_engine.knowledge_graph_recommendation(
            knowledge_point_id, limit
        )
        
        return success_response(
            [rec.dict() for rec in recommendations],
            "相关知识获取成功"
        )
        
    except Exception as e:
        return error_response(ErrorCode.RECOMMENDATION_FAILED, f"获取相关知识失败: {str(e)}")

# ============================================================================
# 主函数
# ============================================================================

if __name__ == "__main__":
    print(f"🚀 启动 {SERVICE_NAME} 服务...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=SERVICE_PORT,
        log_level="info"
    )