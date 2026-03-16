#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
演示脚本：知识点提取与存储
========================
用于将中医演示素材解析并存入向量数据库。
"""

import os
from pathlib import Path
from knowledge_manager import KnowledgeManager

def main():
    # 确保 API 配置
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("未发现 DEEPSEEK_API_KEY 环境变量，请确保已在 .env 中设置。")
        # return

    # 初始化管理器
    # 根据 .env 配置，它将尝试连接远程 ChromaDB (HttpClient)
    manager = KnowledgeManager()

    # 指向演示文件夹
    demo_folder = Path(__file__).parent / "output_markdown"
    
    print(f"正在启动中医演示素材处理流程...")
    print(f"扫描目录: {demo_folder}")

    # 处理文档
    stats = manager.process_documents(
        str(demo_folder),
        extract_knowledge=True # 提取深层结构化数据
    )

    print("\n" + "="*50)
    print(f"处理完成！统计信息：")
    print(f"- 加载文件: {stats['files_loaded']}")
    print(f"- 语义分块: {stats['chunks_created']}")
    print(f"- 存入数据库: {stats['chunks_stored']}")
    print("="*50)

    # 简单检索验证
    print("\n正在执行测试检索 [阴阳的基本概念]...")
    results = manager.query_knowledge("阴阳的基本概念", top_k=2)
    manager.display_results(results)

if __name__ == "__main__":
    main()
