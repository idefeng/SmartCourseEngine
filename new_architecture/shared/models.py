#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
共享数据模型
===========

所有微服务共享的Pydantic数据模型，确保数据一致性。

作者: SmartCourseEngine Team
日期: 2026-03-01
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, validator
from uuid import UUID, uuid4


# ============================================================================
# 枚举类型
# ============================================================================

class CourseType(str, Enum):
    """课程类型"""
    VIDEO = "video"
    DOCUMENT = "document"
    INTERACTIVE = "interactive"
    LIVE = "live"
    HYBRID = "hybrid"


class KnowledgeImportance(int, Enum):
    """知识点重要性"""
    VERY_LOW = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    VERY_HIGH = 5


class TagType(str, Enum):
    """标签类型"""
    CATEGORY = "category"      # 分类标签
    TOPIC = "topic"            # 主题标签
    SKILL = "skill"            # 技能标签
    DIFFICULTY = "difficulty"  # 难度标签
    CUSTOM = "custom"          # 自定义标签


class AnalysisStatus(str, Enum):
    """分析状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class VideoQuality(str, Enum):
    """视频质量"""
    SD = "sd"      # 标清
    HD = "hd"      # 高清
    FHD = "fhd"    # 全高清
    UHD = "uhd"    # 超高清


# ============================================================================
# 基础模型
# ============================================================================

class BaseEntity(BaseModel):
    """基础实体"""
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class TimestampMixin(BaseModel):
    """时间戳混合"""
    start_time: int = Field(..., ge=0, description="开始时间（秒）")
    end_time: int = Field(..., ge=0, description="结束时间（秒）")
    
    @validator('end_time')
    def validate_times(cls, v, values):
        if 'start_time' in values and v < values['start_time']:
            raise ValueError('结束时间必须大于开始时间')
        return v


# ============================================================================
# 核心业务模型
# ============================================================================

class Course(BaseEntity):
    """课程模型"""
    title: str = Field(..., min_length=1, max_length=200, description="课程标题")
    description: Optional[str] = Field(None, max_length=1000, description="课程描述")
    type: CourseType = Field(default=CourseType.VIDEO, description="课程类型")
    
    # 视频相关字段
    video_url: Optional[str] = Field(None, description="视频URL")
    video_duration: Optional[int] = Field(None, ge=0, description="视频时长（秒）")
    video_quality: Optional[VideoQuality] = Field(None, description="视频质量")
    thumbnail_url: Optional[str] = Field(None, description="缩略图URL")
    
    # 文档相关字段
    document_url: Optional[str] = Field(None, description="文档URL")
    document_format: Optional[str] = Field(None, description="文档格式")
    
    # 元数据
    author: Optional[str] = Field(None, description="作者")
    institution: Optional[str] = Field(None, description="机构")
    language: str = Field(default="zh-CN", description="语言")
    
    # 统计信息
    view_count: int = Field(default=0, ge=0, description="观看次数")
    like_count: int = Field(default=0, ge=0, description="点赞数")
    share_count: int = Field(default=0, ge=0, description="分享数")
    
    # 状态
    is_published: bool = Field(default=False, description="是否发布")
    is_featured: bool = Field(default=False, description="是否推荐")
    
    # 关系字段（不会存储在数据库中）
    knowledge_points: List['KnowledgePoint'] = Field(default_factory=list, description="知识点列表")
    tags: List['Tag'] = Field(default_factory=list, description="标签列表")


class KnowledgePoint(BaseEntity, TimestampMixin):
    """知识点模型"""
    course_id: UUID = Field(..., description="所属课程ID")
    name: str = Field(..., min_length=1, max_length=100, description="知识点名称")
    description: str = Field(..., min_length=1, max_length=500, description="知识点描述")
    
    # 分类信息
    category: str = Field(..., description="分类")
    subcategory: Optional[str] = Field(None, description="子分类")
    
    # 重要性评估
    importance: KnowledgeImportance = Field(default=KnowledgeImportance.MEDIUM, description="重要性")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="置信度")
    
    # 关键词
    keywords: List[str] = Field(default_factory=list, description="关键词列表")
    
    # 向量嵌入
    embedding: Optional[List[float]] = Field(None, description="向量嵌入")
    
    # 视觉特征
    visual_features: Optional[List[float]] = Field(None, description="视觉特征向量")
    
    # 音频特征
    audio_features: Optional[List[float]] = Field(None, description="音频特征向量")
    
    # 关系字段
    tags: List['Tag'] = Field(default_factory=list, description="标签列表")
    related_points: List['KnowledgePoint'] = Field(default_factory=list, description="相关知识点")


class Tag(BaseEntity):
    """标签模型"""
    name: str = Field(..., min_length=1, max_length=50, description="标签名称")
    type: TagType = Field(default=TagType.CUSTOM, description="标签类型")
    description: Optional[str] = Field(None, max_length=200, description="标签描述")
    
    # 统计信息
    usage_count: int = Field(default=0, ge=0, description="使用次数")
    
    # 颜色和图标（用于可视化）
    color: Optional[str] = Field(None, description="标签颜色（十六进制）")
    icon: Optional[str] = Field(None, description="标签图标")


class VideoAnalysis(BaseEntity):
    """视频分析结果模型"""
    course_id: UUID = Field(..., description="课程ID")
    video_url: str = Field(..., description="视频URL")
    
    # 分析状态
    status: AnalysisStatus = Field(default=AnalysisStatus.PENDING, description="分析状态")
    progress: float = Field(default=0.0, ge=0.0, le=1.0, description="分析进度")
    
    # 分析结果
    transcript: Optional[str] = Field(None, description="转录文本")
    transcript_timestamps: Optional[List[Dict[str, Any]]] = Field(None, description="时间戳转录")
    
    # 视觉分析
    keyframes: Optional[List[Dict[str, Any]]] = Field(None, description="关键帧")
    scene_changes: Optional[List[int]] = Field(None, description="场景变化时间点")
    visual_concepts: Optional[List[str]] = Field(None, description="视觉概念")
    
    # 音频分析
    speaker_diarization: Optional[List[Dict[str, Any]]] = Field(None, description="说话人分离")
    audio_emotions: Optional[List[Dict[str, Any]]] = Field(None, description="音频情感分析")
    
    # 提取的知识点
    extracted_knowledge_points: Optional[List[KnowledgePoint]] = Field(None, description="提取的知识点")
    
    # 错误信息
    error_message: Optional[str] = Field(None, description="错误信息")
    
    # 分析统计
    analysis_duration: Optional[int] = Field(None, ge=0, description="分析耗时（秒）")
    model_used: Optional[str] = Field(None, description="使用的模型")


class SearchQuery(BaseModel):
    """搜索查询模型"""
    query: str = Field(..., min_length=1, description="搜索查询")
    filters: Optional[Dict[str, Any]] = Field(None, description="过滤条件")
    limit: int = Field(default=10, ge=1, le=100, description="返回结果数量")
    offset: int = Field(default=0, ge=0, description="偏移量")
    
    # 搜索类型
    search_type: str = Field(default="hybrid", description="搜索类型（keyword/vector/hybrid）")
    
    # 时间范围过滤
    min_duration: Optional[int] = Field(None, ge=0, description="最小时长（秒）")
    max_duration: Optional[int] = Field(None, ge=0, description="最大时长（秒）")
    
    # 重要性过滤
    min_importance: Optional[KnowledgeImportance] = Field(None, description="最小重要性")


class SearchResult(BaseModel):
    """搜索结果模型"""
    query: str = Field(..., description="搜索查询")
    total_results: int = Field(..., ge=0, description="总结果数")
    results: List[Dict[str, Any]] = Field(..., description="搜索结果列表")
    
    # 分页信息
    page: int = Field(..., ge=1, description="当前页码")
    total_pages: int = Field(..., ge=1, description="总页数")
    has_next: bool = Field(..., description="是否有下一页")
    has_previous: bool = Field(..., description="是否有上一页")
    
    # 搜索统计
    search_time: float = Field(..., ge=0, description="搜索耗时（秒）")
    search_type: str = Field(..., description="搜索类型")


class TemporalSearchResult(SearchResult):
    """时间戳搜索结果模型"""
    temporal_results: List[Dict[str, Any]] = Field(..., description="时间戳结果")
    
    # 时间戳统计
    total_temporal_matches: int = Field(..., ge=0, description="时间戳匹配总数")
    average_precision: Optional[float] = Field(None, ge=0.0, le=1.0, description="平均精度")


class KnowledgeGraphNode(BaseModel):
    """知识图谱节点"""
    id: str = Field(..., description="节点ID")
    label: str = Field(..., description="节点标签")
    type: str = Field(..., description="节点类型")
    properties: Dict[str, Any] = Field(default_factory=dict, description="节点属性")


class KnowledgeGraphEdge(BaseModel):
    """知识图谱边"""
    source: str = Field(..., description="源节点ID")
    target: str = Field(..., description="目标节点ID")
    label: str = Field(..., description="边标签")
    type: str = Field(..., description="边类型")
    properties: Dict[str, Any] = Field(default_factory=dict, description="边属性")


class KnowledgeGraph(BaseModel):
    """知识图谱"""
    nodes: List[KnowledgeGraphNode] = Field(..., description="节点列表")
    edges: List[KnowledgeGraphEdge] = Field(..., description="边列表")
    
    # 图谱统计
    node_count: int = Field(..., ge=0, description="节点数量")
    edge_count: int = Field(..., ge=0, description="边数量")
    density: float = Field(..., ge=0.0, le=1.0, description="图谱密度")


# ============================================================================
# 请求/响应模型
# ============================================================================

class CreateCourseRequest(BaseModel):
    """创建课程请求"""
    title: str = Field(..., min_length=1, max_length=200, description="课程标题")
    description: Optional[str] = Field(None, max_length=1000, description="课程描述")
    type: CourseType = Field(default=CourseType.VIDEO, description="课程类型")
    video_url: Optional[str] = Field(None, description="视频URL")
    document_url: Optional[str] = Field(None, description="文档URL")
    author: Optional[str] = Field(None, description="作者")
    institution: Optional[str] = Field(None, description="机构")
    language: str = Field(default="zh-CN", description="语言")
    tags: List[str] = Field(default_factory=list, description="标签列表")


class AnalyzeVideoRequest(BaseModel):
    """分析视频请求"""
    course_id: UUID = Field(..., description="课程ID")
    video_url: str = Field(..., description="视频URL")
    
    # 分析选项
    extract_transcript: bool = Field(default=True, description="是否提取转录")
    extract_keyframes: bool = Field(default=True, description="是否提取关键帧")
    detect_scenes: bool = Field(default=True, description="是否检测场景变化")
    extract_knowledge: bool = Field(default=True, description="是否提取知识点")
    
    # 模型选项
    whisper_model: Optional[str] = Field(None, description="Whisper模型")
    clip_model: Optional[str] = Field(None, description="CLIP模型")


class UpdateKnowledgeRequest(BaseModel):
    """更新知识请求"""
    course_id: UUID = Field(..., description="课程ID")
    updates: List[Dict[str, Any]] = Field(..., description="更新内容列表")
    
    # 更新选项
    update_type: str = Field(default="merge", description="更新类型（merge/replace）")
    notify_users: bool = Field(default=True, description="是否通知用户")


class SearchRequest(BaseModel):
    """搜索请求"""
    query: str = Field(..., min_length=1, description="搜索查询")
    filters: Optional[Dict[str, Any]] = Field(None, description="过滤条件")
    limit: int = Field(default=10, ge=1, le=100, description="返回结果数量")
    page: int = Field(default=1, ge=1, description="页码")


# ============================================================================
# 响应模型
# ============================================================================

class BaseResponse(BaseModel):
    """基础响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[Dict[str, Any]] = Field(None, description="响应数据")
    error_code: Optional[str] = Field(None, description="错误代码")


class CourseResponse(BaseResponse):
    """课程响应"""
    data: Optional[Course] = Field(None, description="课程数据")


class KnowledgePointResponse(BaseResponse):
    """知识点响应"""
    data: Optional[KnowledgePoint] = Field(None, description="知识点数据")


class VideoAnalysisResponse(BaseResponse):
    """视频分析响应"""
    data: Optional[VideoAnalysis] = Field(None, description="视频分析数据")


class SearchResponse(BaseResponse):
    """搜索响应"""
    data: Optional[SearchResult] = Field(None, description="搜索数据")


class KnowledgeGraphResponse(BaseResponse):
    """知识图谱响应"""
    data: Optional[KnowledgeGraph] = Field(None, description="知识图谱数据")


# ============================================================================
# 事件模型
# ============================================================================

class BaseEvent(BaseModel):
    """基础事件"""
    event_id: UUID = Field(default_factory=uuid4, description="事件ID")
    event_type: str = Field(..., description="事件类型")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="时间戳")
    source: str = Field(..., description="事件源")
    payload: Dict[str, Any] = Field(..., description="事件负载")


class VideoAnalysisEvent(BaseEvent):
    """视频分析事件"""
    event_type: str = "video.analysis"
    course_id: UUID = Field(..., description="课程ID")
    video_url: str = Field(..., description="视频URL")
    status: AnalysisStatus = Field(..., description="分析状态")


class KnowledgeUpdateEvent(BaseEvent):
    """知识更新事件"""
    event_type: str = "knowledge.update"
    course_id: UUID = Field(..., description="课程ID")
    update_type: str = Field(..., description="更新类型")
    affected_knowledge_points: List[UUID] = Field(..., description="受影响的知识点")


# ============================================================================
# 更新引用
# ============================================================================

# 更新模型引用
Course.update_forward_refs()
KnowledgePoint.update_forward_refs()
Tag.update_forward_refs()


if __name__ == "__main__":
    # 测试模型
    course = Course(
        title="Python编程入门",
        description="学习Python基础编程",
        type=CourseType.VIDEO,
        video_url="https://example.com/video.mp4"
    )
    
    print(f"Course ID: {course.id}")
    print(f"Course Title: {course.title}")
    print(f"Created At: {course.created_at}")