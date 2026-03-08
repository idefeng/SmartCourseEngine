#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
共享配置模块 - 修复版
============

所有微服务共享的配置管理，支持环境变量和配置文件。

作者: SmartCourseEngine Team
日期: 2026-03-01
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator


class DatabaseConfig(BaseSettings):
    """数据库配置"""
    postgres_url: str = Field(
        default="postgresql://admin:admin123@localhost:5432/smartcourse",
        description="PostgreSQL连接URL"
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis连接URL"
    )
    neo4j_url: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j连接URL"
    )
    neo4j_user: str = Field(default="neo4j", description="Neo4j用户名")
    neo4j_password: str = Field(default="admin123", description="Neo4j密码")
    
    # Pinecone向量数据库配置
    pinecone_api_key: Optional[str] = Field(default=None, description="Pinecone API密钥")
    pinecone_environment: Optional[str] = Field(default=None, description="Pinecone环境")
    pinecone_index_name: str = Field(default="smartcourse-knowledge", description="Pinecone索引名称")
    
    model_config = SettingsConfigDict(
        env_prefix="DATABASE_",
        case_sensitive=False
    )


class StorageConfig(BaseSettings):
    """存储配置"""
    minio_endpoint: str = Field(default="localhost:9000", description="MinIO端点")
    minio_access_key: str = Field(default="admin", description="MinIO访问密钥")
    minio_secret_key: str = Field(default="admin123", description="MinIO密钥")
    minio_secure: bool = Field(default=False, description="MinIO是否使用SSL")
    
    # 存储桶配置
    video_bucket: str = Field(default="videos", description="视频存储桶")
    document_bucket: str = Field(default="documents", description="文档存储桶")
    thumbnail_bucket: str = Field(default="thumbnails", description="缩略图存储桶")
    
    model_config = SettingsConfigDict(
        env_prefix="STORAGE_",
        case_sensitive=False
    )


class AIConfig(BaseSettings):
    """AI模型配置"""
    # OpenAI/DeepSeek配置
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API密钥")
    openai_base_url: str = Field(
        default="https://api.deepseek.com/v1",
        description="OpenAI API基础URL"
    )
    openai_model: str = Field(default="deepseek-chat", description="OpenAI模型")
    embedding_model: str = Field(default="text-embedding-ada-002", description="嵌入模型")
    
    # Whisper配置
    whisper_model: str = Field(default="base", description="Whisper模型")
    whisper_device: str = Field(default="cuda", description="Whisper设备")
    
    # 视觉模型配置
    clip_model: str = Field(default="openai/clip-vit-base-patch32", description="CLIP模型")
    yolo_model: str = Field(default="yolov8n.pt", description="YOLO模型")
    
    # 本地LLM配置
    local_llm_enabled: bool = Field(default=False, description="是否启用本地LLM")
    local_llm_url: str = Field(default="http://localhost:11434", description="本地LLM URL")
    local_llm_model: str = Field(default="llama3", description="本地LLM模型")
    
    model_config = SettingsConfigDict(
        env_prefix="AI_",
        case_sensitive=False
    )


class MessageQueueConfig(BaseSettings):
    """消息队列配置"""
    rabbitmq_url: str = Field(
        default="amqp://admin:admin123@localhost:5672",
        description="RabbitMQ连接URL"
    )
    
    # 队列名称
    video_analysis_queue: str = Field(default="video_analysis", description="视频分析队列")
    knowledge_extraction_queue: str = Field(default="knowledge_extraction", description="知识提取队列")
    course_generation_queue: str = Field(default="course_generation", description="课程生成队列")
    notification_queue: str = Field(default="notification", description="通知队列")
    
    model_config = SettingsConfigDict(
        env_prefix="MQ_",
        case_sensitive=False
    )


class ServiceConfig(BaseSettings):
    """服务配置"""
    service_name: str = Field(default="unknown", description="服务名称")
    service_port: int = Field(default=8000, description="服务端口")
    debug: bool = Field(default=False, description="调试模式")
    
    # CORS配置
    cors_origins: list = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
            "http://localhost:8501"
        ],
        description="CORS允许的源"
    )
    
    @validator('cors_origins', pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    # 日志配置
    log_level: str = Field(default="INFO", description="日志级别")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="日志格式"
    )
    
    # 目录配置
    data_dir: str = Field(default="./data", description="数据目录")
    log_dir: str = Field(default="./logs", description="日志目录")
    cache_dir: str = Field(default="./cache", description="缓存目录")
    
    model_config = SettingsConfigDict(
        env_prefix="SERVICE_",
        case_sensitive=False
    )


class MonitoringConfig(BaseSettings):
    """监控配置"""
    prometheus_enabled: bool = Field(default=True, description="是否启用Prometheus")
    metrics_port: int = Field(default=9091, description="指标端口")
    
    # 健康检查配置
    health_check_interval: int = Field(default=30, description="健康检查间隔")
    readiness_timeout: int = Field(default=10, description="就绪超时")
    liveness_timeout: int = Field(default=30, description="存活超时")
    
    model_config = SettingsConfigDict(
        env_prefix="MONITORING_",
        case_sensitive=False
    )


class SecurityConfig(BaseSettings):
    """安全配置"""
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        description="密钥"
    )
    algorithm: str = Field(default="HS256", description="算法")
    access_token_expire_minutes: int = Field(default=30, description="访问令牌过期时间")
    
    # API密钥验证
    api_key_header: str = Field(default="X-API-Key", description="API密钥头")
    require_api_key: bool = Field(default=False, description="是否需要API密钥")
    
    model_config = SettingsConfigDict(
        env_prefix="SECURITY_",
        case_sensitive=False
    )


class Config(BaseSettings):
    """主配置类"""
    database: DatabaseConfig = DatabaseConfig()
    storage: StorageConfig = StorageConfig()
    ai: AIConfig = AIConfig()
    message_queue: MessageQueueConfig = MessageQueueConfig()
    service: ServiceConfig = ServiceConfig()
    monitoring: MonitoringConfig = MonitoringConfig()
    security: SecurityConfig = SecurityConfig()
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # 忽略额外的环境变量
    )


# 全局配置实例
config = Config()


def get_settings():
    """获取全局配置实例 (向后兼容)"""
    return config


def load_config_from_file(config_path: Optional[str] = None) -> Config:
    """
    从配置文件加载配置
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        Config: 配置实例
    """
    if config_path is None:
        config_path = os.getenv("CONFIG_PATH", "config.json")
    
    config_file = Path(config_path)
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            file_config = json.load(f)
        
        # 更新环境变量
        for key, value in file_config.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    env_key = f"{key.upper()}_{sub_key.upper()}"
                    if env_key not in os.environ:
                        os.environ[env_key] = str(sub_value)
            else:
                if key.upper() not in os.environ:
                    os.environ[key.upper()] = str(value)
    
    return Config()


def get_service_config(service_name: str) -> Dict[str, Any]:
    """
    获取特定服务的配置
    
    Args:
        service_name: 服务名称
        
    Returns:
        Dict[str, Any]: 服务配置字典
    """
    # 加载基础配置
    cfg = load_config_from_file()
    
    # 设置服务名称
    cfg.service.service_name = service_name
    
    # 根据服务名称设置特定配置
    if service_name == "api-gateway":
        cfg.service.service_port = 8000
    elif service_name == "course-generator":
        cfg.service.service_port = 8001
    elif service_name == "video-analyzer":
        cfg.service.service_port = 8002
        # 视频分析服务需要GPU
        cfg.ai.whisper_device = os.getenv("WHISPER_DEVICE", "cuda")
    elif service_name == "knowledge-base":
        cfg.service.service_port = 8003
    elif service_name == "search-engine":
        cfg.service.service_port = 8004
    elif service_name == "recommendation":
        cfg.service.service_port = 8005
    elif service_name == "notification":
        cfg.service.service_port = 8006
    
    return cfg.dict()


if __name__ == "__main__":
    # 测试配置加载
    cfg = load_config_from_file()
    print(f"Service: {cfg.service.service_name}")
    print(f"Database URL: {cfg.database.postgres_url}")
    print(f"AI Model: {cfg.ai.openai_model}")
