#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
共享配置模块
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
        env="DATABASE_URL"
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL"
    )
    neo4j_url: str = Field(
        default="bolt://localhost:7687",
        env="NEO4J_URL"
    )
    neo4j_user: str = Field(default="neo4j", env="NEO4J_USER")
    neo4j_password: str = Field(default="admin123", env="NEO4J_PASSWORD")
    
    # Pinecone向量数据库配置
    pinecone_api_key: Optional[str] = Field(default=None, env="PINECONE_API_KEY")
    pinecone_environment: Optional[str] = Field(default=None, env="PINECONE_ENVIRONMENT")
    pinecone_index_name: str = Field(default="smartcourse-knowledge", env="PINECONE_INDEX_NAME")


class StorageConfig(BaseSettings):
    """存储配置"""
    minio_endpoint: str = Field(default="localhost:9000", env="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="admin", env="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="admin123", env="MINIO_SECRET_KEY")
    minio_secure: bool = Field(default=False, env="MINIO_SECURE")
    
    # 存储桶配置
    video_bucket: str = Field(default="videos", env="VIDEO_BUCKET")
    document_bucket: str = Field(default="documents", env="DOCUMENT_BUCKET")
    thumbnail_bucket: str = Field(default="thumbnails", env="THUMBNAIL_BUCKET")


class AIConfig(BaseSettings):
    """AI模型配置"""
    # OpenAI/DeepSeek配置
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_base_url: str = Field(
        default="https://api.deepseek.com/v1",
        env="OPENAI_BASE_URL"
    )
    openai_model: str = Field(default="deepseek-chat", env="OPENAI_MODEL")
    embedding_model: str = Field(default="text-embedding-ada-002", env="EMBEDDING_MODEL")
    
    # Whisper配置
    whisper_model: str = Field(default="base", env="WHISPER_MODEL")
    whisper_device: str = Field(default="cuda", env="WHISPER_DEVICE")
    
    # 视觉模型配置
    clip_model: str = Field(default="openai/clip-vit-base-patch32", env="CLIP_MODEL")
    yolo_model: str = Field(default="yolov8n.pt", env="YOLO_MODEL")
    
    # 本地LLM配置
    local_llm_enabled: bool = Field(default=False, env="LOCAL_LLM_ENABLED")
    local_llm_url: str = Field(default="http://localhost:11434", env="LOCAL_LLM_URL")
    local_llm_model: str = Field(default="llama3", env="LOCAL_LLM_MODEL")


class MessageQueueConfig(BaseSettings):
    """消息队列配置"""
    rabbitmq_url: str = Field(
        default="amqp://admin:admin123@localhost:5672",
        env="RABBITMQ_URL"
    )
    
    # 队列名称
    video_analysis_queue: str = Field(default="video_analysis", env="VIDEO_ANALYSIS_QUEUE")
    knowledge_extraction_queue: str = Field(default="knowledge_extraction", env="KNOWLEDGE_EXTRACTION_QUEUE")
    course_generation_queue: str = Field(default="course_generation", env="COURSE_GENERATION_QUEUE")
    notification_queue: str = Field(default="notification", env="NOTIFICATION_QUEUE")


class ServiceConfig(BaseSettings):
    """服务配置"""
    service_name: str = Field(default="unknown", env="SERVICE_NAME")
    service_port: int = Field(default=8000, env="SERVICE_PORT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # CORS配置
    cors_origins: list = Field(
        default=["http://localhost:3000", "http://localhost:8501"],
        env="CORS_ORIGINS"
    )
    
    @validator('cors_origins', pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    # 日志配置
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )


class MonitoringConfig(BaseSettings):
    """监控配置"""
    prometheus_enabled: bool = Field(default=True, env="PROMETHEUS_ENABLED")
    metrics_port: int = Field(default=9091, env="METRICS_PORT")
    
    # 健康检查配置
    health_check_interval: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")
    readiness_timeout: int = Field(default=10, env="READINESS_TIMEOUT")
    liveness_timeout: int = Field(default=30, env="LIVENESS_TIMEOUT")


class SecurityConfig(BaseSettings):
    """安全配置"""
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        env="SECRET_KEY"
    )
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # API密钥验证
    api_key_header: str = Field(default="X-API-Key", env="API_KEY_HEADER")
    require_api_key: bool = Field(default=False, env="REQUIRE_API_KEY")


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
        case_sensitive=False
    )


# 全局配置实例
config = Config()


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