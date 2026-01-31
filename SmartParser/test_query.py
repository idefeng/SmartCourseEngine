#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识检索测试脚本
================

交互式测试知识管理器的检索功能。

使用方法:
    python test_query.py

作者: SmartCourseEngine Team
日期: 2026-01-31
"""

import sys
from pathlib import Path

# Rich 美化输出
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel

console = Console()


def main():
    """主函数"""
    console.print(Panel("""
╔═══════════════════════════════════════════════════════════╗
║           Knowledge Query Test - 知识检索测试             ║
╚═══════════════════════════════════════════════════════════╝
    """, style="blue"))
    
    # 导入知识管理器
    try:
        from knowledge_manager import KnowledgeManager
    except ImportError as e:
        console.print(f"[red]✗ 导入失败: {e}[/red]")
        console.print("[dim]请确保 knowledge_manager.py 在同一目录下[/dim]")
        sys.exit(1)
    
    # 初始化管理器
    base_dir = Path(__file__).parent
    manager = KnowledgeManager(
        db_path=str(base_dir / "chroma_db")
    )
    
    # 检查知识库状态
    if manager.collection:
        count = manager.collection.count()
        if count == 0:
            console.print("[yellow]⚠ 知识库为空[/yellow]")
            console.print("[dim]请先运行 knowledge_manager.py 导入文档[/dim]")
            
            # 提示是否现在处理
            choice = Prompt.ask(
                "是否现在处理 output_markdown 中的文档？",
                choices=["y", "n"],
                default="y"
            )
            
            if choice == "y":
                output_folder = base_dir / "output_markdown"
                manager.process_documents(str(output_folder), extract_knowledge=False)
        else:
            console.print(f"[green]✓ 知识库已加载，共 {count} 条记录[/green]")
    
    console.print("\n[dim]输入问题进行检索，输入 'quit' 或 'exit' 退出[/dim]\n")
    
    # 交互式查询循环
    while True:
        try:
            query = Prompt.ask("[bold blue]请输入您的问题[/bold blue]")
            
            if query.lower() in ['quit', 'exit', 'q']:
                console.print("[dim]再见！[/dim]")
                break
            
            if not query.strip():
                continue
            
            # 执行查询
            console.print("\n[dim]正在检索...[/dim]\n")
            results = manager.query_knowledge(query, top_k=3)
            
            # 显示结果
            manager.display_results(results)
            
            console.print()  # 空行分隔
            
        except KeyboardInterrupt:
            console.print("\n[dim]已取消[/dim]")
            break


if __name__ == "__main__":
    main()
