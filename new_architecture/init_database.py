#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库初始化脚本
===============

初始化SmartCourseEngine的数据库（PostgreSQL和Neo4j）。

作者: SmartCourseEngine Team
日期: 2026-03-01
"""

import os
import sys
import asyncio
from pathlib import Path

# 添加共享模块路径
sys.path.insert(0, str(Path(__file__).parent / "shared"))

from config import config, load_config_from_file
from utils import setup_logger

# ============================================================================
# 配置和日志
# ============================================================================

# 加载配置
cfg = load_config_from_file()

# 设置日志
logger = setup_logger(
    name="database-init",
    level=cfg.service.log_level,
    format_str=cfg.service.log_format
)

# ============================================================================
# PostgreSQL初始化
# ============================================================================

async def init_postgresql():
    """初始化PostgreSQL数据库"""
    try:
        import asyncpg
        
        logger.info("开始初始化PostgreSQL数据库...")
        
        # 读取SQL schema文件
        schema_file = Path(__file__).parent / "deploy" / "sql" / "schema.sql"
        if not schema_file.exists():
            logger.error(f"SQL schema文件不存在: {schema_file}")
            return False
        
        with open(schema_file, 'r', encoding='utf-8') as f:
            sql_commands = f.read()
        
        # 连接到PostgreSQL
        conn = await asyncpg.connect(cfg.database.postgres_url)
        
        try:
            # 执行SQL命令
            await conn.execute(sql_commands)
            logger.info("PostgreSQL数据库初始化成功")
            return True
        except Exception as e:
            logger.error(f"PostgreSQL初始化失败: {e}")
            return False
        finally:
            await conn.close()
            
    except ImportError:
        logger.error("未安装asyncpg，跳过PostgreSQL初始化")
        return False
    except Exception as e:
        logger.error(f"PostgreSQL连接失败: {e}")
        return False

# ============================================================================
# Neo4j初始化
# ============================================================================

async def init_neo4j():
    """初始化Neo4j知识图谱"""
    try:
        from neo4j import AsyncGraphDatabase
        
        logger.info("开始初始化Neo4j知识图谱...")
        
        # 读取Cypher schema文件
        cypher_file = Path(__file__).parent / "deploy" / "cypher" / "schema.cypher"
        if not cypher_file.exists():
            logger.error(f"Cypher schema文件不存在: {cypher_file}")
            return False
        
        with open(cypher_file, 'r', encoding='utf-8') as f:
            cypher_script = f.read()
        
        # 分割Cypher语句
        statements = []
        current_statement = []
        
        for line in cypher_script.split('\n'):
            line = line.strip()
            if line.startswith('--'):  # 跳过注释
                continue
            if line:
                current_statement.append(line)
                if line.endswith(';'):
                    statements.append(' '.join(current_statement))
                    current_statement = []
        
        if current_statement:  # 处理最后一条语句
            statements.append(' '.join(current_statement))
        
        # 连接到Neo4j
        driver = AsyncGraphDatabase.driver(
            cfg.database.neo4j_url,
            auth=(cfg.database.neo4j_user, cfg.database.neo4j_password)
        )
        
        try:
            async with driver.session() as session:
                for i, statement in enumerate(statements, 1):
                    try:
                        await session.run(statement)
                        logger.debug(f"执行Cypher语句 {i}/{len(statements)}: {statement[:50]}...")
                    except Exception as e:
                        logger.warning(f"Cypher语句执行失败 ({i}): {e}")
            
            logger.info("Neo4j知识图谱初始化成功")
            return True
        except Exception as e:
            logger.error(f"Neo4j初始化失败: {e}")
            return False
        finally:
            await driver.close()
            
    except ImportError:
        logger.error("未安装neo4j，跳过Neo4j初始化")
        return False
    except Exception as e:
        logger.error(f"Neo4j连接失败: {e}")
        return False

# ============================================================================
# Redis初始化
# ============================================================================

async def init_redis():
    """初始化Redis缓存"""
    try:
        import redis.asyncio as redis
        
        logger.info("开始初始化Redis缓存...")
        
        # 连接到Redis
        redis_client = redis.from_url(cfg.database.redis_url)
        
        try:
            # 测试连接
            await redis_client.ping()
            
            # 设置一些初始缓存键
            initial_data = {
                "system:status": "initialized",
                "system:version": "1.0.0",
                "system:initialized_at": "2026-03-01T19:39:00Z",
                "cache:stats": "{}"
            }
            
            # 批量设置
            pipeline = redis_client.pipeline()
            for key, value in initial_data.items():
                pipeline.set(key, value)
            await pipeline.execute()
            
            logger.info("Redis缓存初始化成功")
            return True
        except Exception as e:
            logger.error(f"Redis初始化失败: {e}")
            return False
        finally:
            await redis_client.close()
            
    except ImportError:
        logger.error("未安装redis，跳过Redis初始化")
        return False
    except Exception as e:
        logger.error(f"Redis连接失败: {e}")
        return False

# ============================================================================
# Pinecone初始化
# ============================================================================

async def init_pinecone():
    """初始化Pinecone向量数据库"""
    try:
        import pinecone
        
        logger.info("开始初始化Pinecone向量数据库...")
        
        # 检查配置
        if not cfg.database.pinecone_api_key:
            logger.warning("未配置Pinecone API密钥，跳过初始化")
            return False
        
        # 初始化Pinecone
        pinecone.init(
            api_key=cfg.database.pinecone_api_key,
            environment=cfg.database.pinecone_environment
        )
        
        # 检查索引是否存在
        index_name = cfg.database.pinecone_index_name
        existing_indexes = pinecone.list_indexes()
        
        if index_name not in existing_indexes:
            logger.info(f"创建Pinecone索引: {index_name}")
            
            # 创建索引（1536维是text-embedding-ada-002的维度）
            pinecone.create_index(
                name=index_name,
                dimension=1536,
                metric="cosine",
                metadata_config={
                    "indexed": ["course_id", "knowledge_point_id", "type", "category"]
                }
            )
            
            # 等待索引就绪
            import time
            while index_name not in pinecone.list_indexes():
                logger.info("等待索引创建...")
                time.sleep(1)
        
        logger.info("Pinecone向量数据库初始化成功")
        return True
        
    except ImportError:
        logger.error("未安装pinecone-client，跳过Pinecone初始化")
        return False
    except Exception as e:
        logger.error(f"Pinecone初始化失败: {e}")
        return False

# ============================================================================
# 主函数
# ============================================================================

async def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("SmartCourseEngine 数据库初始化")
    logger.info("=" * 60)
    
    results = {}
    
    # 初始化PostgreSQL
    logger.info("\n1. 初始化PostgreSQL...")
    results['postgresql'] = await init_postgresql()
    
    # 初始化Neo4j
    logger.info("\n2. 初始化Neo4j...")
    results['neo4j'] = await init_neo4j()
    
    # 初始化Redis
    logger.info("\n3. 初始化Redis...")
    results['redis'] = await init_redis()
    
    # 初始化Pinecone
    logger.info("\n4. 初始化Pinecone...")
    results['pinecone'] = await init_pinecone()
    
    # 输出结果
    logger.info("\n" + "=" * 60)
    logger.info("初始化结果汇总:")
    logger.info("=" * 60)
    
    for db, success in results.items():
        status = "✅ 成功" if success else "❌ 失败"
        logger.info(f"{db:15} {status}")
    
    # 统计
    total = len(results)
    successful = sum(1 for success in results.values() if success)
    
    logger.info("=" * 60)
    logger.info(f"总计: {successful}/{total} 个数据库初始化成功")
    
    if successful == total:
        logger.info("🎉 所有数据库初始化完成!")
    elif successful >= total // 2:
        logger.info("⚠️  部分数据库初始化完成，核心功能可用")
    else:
        logger.error("❌ 数据库初始化失败较多，请检查配置")
    
    return successful == total

if __name__ == "__main__":
    # 运行异步主函数
    success = asyncio.run(main())
    sys.exit(0 if success else 1)