#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库连接模块
=============

提供统一的数据库连接管理，支持多种数据库后端。

作者: SmartCourseEngine Team
日期: 2026-03-01
"""

import os
import sys
from typing import Optional, Any, Dict
from pathlib import Path

import sys
from pathlib import Path

# 添加共享模块路径
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from shared.config import config
    from shared.utils import setup_logger
except ImportError:
    # 备用导入方式
    from config import config
    from utils import setup_logger

# 设置日志
logger = setup_logger(
    name="database",
    level=config.service.log_level,
    format_str=config.service.log_format
)

# ============================================================================
# PostgreSQL/SQLite连接
# ============================================================================

def get_database_url() -> str:
    """获取数据库URL"""
    db_url = config.database.postgres_url
    
    # 如果是SQLite，确保数据目录存在
    if db_url.startswith('sqlite:///'):
        data_dir = Path(config.service.data_dir) if hasattr(config.service, 'data_dir') else Path('./data')
        data_dir.mkdir(exist_ok=True)
        
        # 提取SQLite文件路径
        import re
        match = re.match(r'sqlite:///(.+)', db_url)
        if match:
            db_path = Path(match.group(1))
            db_path.parent.mkdir(parents=True, exist_ok=True)
    
    return db_url

async def get_postgres_connection():
    """获取PostgreSQL连接"""
    try:
        import asyncpg
        
        db_url = get_database_url()
        
        # 如果是SQLite，返回None（使用SQLAlchemy）
        if db_url.startswith('sqlite:///'):
            return None
        
        # 连接到PostgreSQL
        conn = await asyncpg.connect(db_url)
        logger.debug("PostgreSQL连接建立成功")
        return conn
        
    except ImportError:
        logger.error("未安装asyncpg，无法连接PostgreSQL")
        return None
    except Exception as e:
        logger.error(f"PostgreSQL连接失败: {e}")
        return None

# ============================================================================
# SQLAlchemy支持（用于SQLite和ORM）
# ============================================================================

def get_sqlalchemy_engine():
    """获取SQLAlchemy引擎"""
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.ext.declarative import declarative_base
        from sqlalchemy.orm import sessionmaker
        
        db_url = get_database_url()
        
        # 创建引擎
        engine = create_engine(
            db_url,
            echo=config.service.debug,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        
        # 创建基类和会话工厂
        Base = declarative_base()
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        logger.debug("SQLAlchemy引擎创建成功")
        return engine, Base, SessionLocal
        
    except ImportError:
        logger.error("未安装SQLAlchemy，无法使用ORM")
        return None, None, None
    except Exception as e:
        logger.error(f"SQLAlchemy引擎创建失败: {e}")
        return None, None, None

# ============================================================================
# Redis连接
# ============================================================================

async def get_redis_connection():
    """获取Redis连接"""
    try:
        import redis.asyncio as redis
        
        redis_url = config.database.redis_url
        
        # 创建Redis连接
        redis_client = redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        
        # 测试连接
        await redis_client.ping()
        logger.debug("Redis连接建立成功")
        return redis_client
        
    except ImportError:
        logger.error("未安装redis，无法连接Redis")
        return None
    except Exception as e:
        logger.error(f"Redis连接失败: {e}")
        return None

# ============================================================================
# Neo4j连接
# ============================================================================

async def get_neo4j_driver():
    """获取Neo4j驱动"""
    try:
        from neo4j import AsyncGraphDatabase
        
        neo4j_url = config.database.neo4j_url
        neo4j_user = config.database.neo4j_user
        neo4j_password = config.database.neo4j_password
        
        # 创建Neo4j驱动
        driver = AsyncGraphDatabase.driver(
            neo4j_url,
            auth=(neo4j_user, neo4j_password)
        )
        
        # 测试连接
        async with driver.session() as session:
            await session.run("RETURN 1")
        
        logger.debug("Neo4j连接建立成功")
        return driver
        
    except ImportError:
        logger.error("未安装neo4j，无法连接Neo4j")
        return None
    except Exception as e:
        logger.error(f"Neo4j连接失败: {e}")
        return None

# ============================================================================
# Pinecone连接
# ============================================================================

def get_pinecone_index():
    """获取Pinecone索引"""
    try:
        import pinecone
        
        # 检查配置
        if not config.database.pinecone_api_key:
            logger.warning("未配置Pinecone API密钥")
            return None
        
        # 初始化Pinecone
        pinecone.init(
            api_key=config.database.pinecone_api_key,
            environment=config.database.pinecone_environment
        )
        
        # 获取索引
        index_name = config.database.pinecone_index_name
        
        if index_name not in pinecone.list_indexes():
            logger.warning(f"Pinecone索引不存在: {index_name}")
            return None
        
        index = pinecone.Index(index_name)
        logger.debug("Pinecone连接建立成功")
        return index
        
    except ImportError:
        logger.error("未安装pinecone-client，无法连接Pinecone")
        return None
    except Exception as e:
        logger.error(f"Pinecone连接失败: {e}")
        return None

# ============================================================================
# 数据库健康检查
# ============================================================================

async def check_database_health() -> Dict[str, bool]:
    """检查数据库健康状态"""
    health_status = {}
    
    # 检查PostgreSQL/SQLite
    try:
        if config.database.postgres_url.startswith('sqlite:///'):
            # 检查SQLite文件
            import re
            match = re.match(r'sqlite:///(.+)', config.database.postgres_url)
            if match:
                db_path = Path(match.group(1))
                health_status['postgresql'] = db_path.exists()
            else:
                health_status['postgresql'] = False
        else:
            conn = await get_postgres_connection()
            if conn:
                await conn.close()
                health_status['postgresql'] = True
            else:
                health_status['postgresql'] = False
    except Exception as e:
        logger.error(f"PostgreSQL健康检查失败: {e}")
        health_status['postgresql'] = False
    
    # 检查Redis
    try:
        redis_client = await get_redis_connection()
        if redis_client:
            await redis_client.close()
            health_status['redis'] = True
        else:
            health_status['redis'] = False
    except Exception as e:
        logger.error(f"Redis健康检查失败: {e}")
        health_status['redis'] = False
    
    # 检查Neo4j
    try:
        driver = await get_neo4j_driver()
        if driver:
            await driver.close()
            health_status['neo4j'] = True
        else:
            health_status['neo4j'] = False
    except Exception as e:
        logger.error(f"Neo4j健康检查失败: {e}")
        health_status['neo4j'] = False
    
    # 检查Pinecone
    try:
        index = get_pinecone_index()
        health_status['pinecone'] = index is not None
    except Exception as e:
        logger.error(f"Pinecone健康检查失败: {e}")
        health_status['pinecone'] = False
    
    return health_status

# ============================================================================
# 数据库工具函数
# ============================================================================

async def execute_sql(sql: str, params: Optional[Dict] = None):
    """执行SQL语句"""
    try:
        if config.database.postgres_url.startswith('sqlite:///'):
            # 使用SQLAlchemy执行SQL
            engine, _, SessionLocal = get_sqlalchemy_engine()
            if not engine:
                return None
            
            from sqlalchemy import text
            
            with engine.connect() as connection:
                result = connection.execute(text(sql), params or {})
                connection.commit()
                return result
        else:
            # 使用asyncpg执行SQL
            conn = await get_postgres_connection()
            if not conn:
                return None
            
            try:
                result = await conn.execute(sql, *(params or {}).values())
                return result
            finally:
                await conn.close()
                
    except Exception as e:
        logger.error(f"SQL执行失败: {e}")
        return None

async def query_sql(sql: str, params: Optional[Dict] = None):
    """查询SQL语句"""
    try:
        if config.database.postgres_url.startswith('sqlite:///'):
            # 使用SQLAlchemy查询
            engine, _, SessionLocal = get_sqlalchemy_engine()
            if not engine:
                return []
            
            from sqlalchemy import text
            
            with engine.connect() as connection:
                result = connection.execute(text(sql), params or {})
                return [dict(row) for row in result]
        else:
            # 使用asyncpg查询
            conn = await get_postgres_connection()
            if not conn:
                return []
            
            try:
                result = await conn.fetch(sql, *(params or {}).values())
                return [dict(row) for row in result]
            finally:
                await conn.close()
                
    except Exception as e:
        logger.error(f"SQL查询失败: {e}")
        return []

# ============================================================================
# 主函数（测试用）
# ============================================================================

async def main():
    """测试数据库连接"""
    logger.info("测试数据库连接...")
    
    # 检查数据库健康状态
    health = await check_database_health()
    
    logger.info("数据库健康状态:")
    for db, status in health.items():
        status_str = "✅ 正常" if status else "❌ 异常"
        logger.info(f"  {db:15} {status_str}")
    
    # 测试SQL执行
    logger.info("\n测试SQL执行...")
    
    # 创建测试表
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS test_table (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    
    result = await execute_sql(create_table_sql)
    if result:
        logger.info("测试表创建成功")
    else:
        logger.error("测试表创建失败")
    
    # 插入测试数据
    insert_sql = "INSERT INTO test_table (name) VALUES (?)"
    insert_params = {"name": "测试数据"}
    
    result = await execute_sql(insert_sql, insert_params)
    if result:
        logger.info("测试数据插入成功")
    else:
        logger.error("测试数据插入失败")
    
    # 查询测试数据
    query_sql = "SELECT * FROM test_table"
    rows = await query_sql(query_sql)
    
    logger.info(f"查询结果: {len(rows)} 条记录")
    for row in rows:
        logger.info(f"  ID: {row['id']}, Name: {row['name']}, Created: {row['created_at']}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())