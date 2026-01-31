#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识管理器 (Knowledge Manager)
=============================

基于语义分块和向量数据库的知识点管理系统。
功能包括：语义分块、知识点提取、向量存储、智能检索。

作者: SmartCourseEngine Team
日期: 2026-01-31
"""

import os
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any

# Rich 美化输出
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.table import Table

console = Console()

# ============================================================================
# API 配置 - 请在此处配置您的 API 密钥
# ============================================================================

# DeepSeek API 配置
API_KEY = os.getenv("DEEPSEEK_API_KEY", "your-deepseek-api-key-here")
BASE_URL = os.getenv("API_BASE_URL", "https://api.deepseek.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-chat")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")

# 如果使用 Qwen (通义千问)，请取消下面的注释：
# BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
# MODEL_NAME = "qwen-turbo"

# 如果使用 OpenAI，请取消下面的注释：
# BASE_URL = "https://api.openai.com/v1"
# MODEL_NAME = "gpt-4o-mini"


# ============================================================================
# 知识点提取的 Prompt 模板
# ============================================================================
KNOWLEDGE_EXTRACTION_PROMPT = """请分析以下文本内容，提取知识点信息。

【文本内容】
{content}

请以 JSON 格式返回以下信息（必须是有效的 JSON）：
{{
    "knowledge_name": "知识点名称（简洁明了，10字以内）",
    "core_concept": "核心概念说明（50字以内）",
    "category": "所属学科/类别（如：教育培训、项目管理、政策法规等）",
    "importance": 重要程度（1-5的整数，5最重要）,
    "keywords": ["关键词1", "关键词2", "关键词3"]
}}

仅返回 JSON，不要添加任何其他文字或 markdown 标记。"""


# ============================================================================
# 知识管理器主类
# ============================================================================
class KnowledgeManager:
    """
    知识管理器
    
    实现知识点的语义分块、提取、存储和检索功能。
    """
    
    def __init__(
        self,
        api_key: str = API_KEY,
        base_url: str = BASE_URL,
        model_name: str = MODEL_NAME,
        db_path: str = "./chroma_db"
    ):
        """
        初始化知识管理器
        
        Args:
            api_key: API 密钥
            base_url: API 基础 URL
            model_name: 模型名称
            db_path: ChromaDB 存储路径
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.db_path = Path(db_path)
        
        # 初始化组件
        self._init_llm()
        self._init_embeddings()
        self._init_vector_db()
        self._init_text_splitter()
    
    def _init_llm(self):
        """初始化大语言模型"""
        try:
            from langchain_openai import ChatOpenAI
            
            self.llm = ChatOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model_name,
                temperature=0.3
            )
            console.print("[green]✓[/green] 大语言模型初始化成功")
        except Exception as e:
            console.print(f"[red]✗[/red] LLM 初始化失败: {e}")
            self.llm = None
    
    def _init_embeddings(self):
        """初始化 Embedding 模型"""
        try:
            from langchain_openai import OpenAIEmbeddings
            
            self.embeddings = OpenAIEmbeddings(
                api_key=self.api_key,
                base_url=self.base_url,
                model=EMBEDDING_MODEL
            )
            console.print("[green]✓[/green] Embedding 模型初始化成功")
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Embedding 初始化失败，将使用默认模型: {e}")
            # 使用 ChromaDB 默认的 sentence-transformers
            self.embeddings = None
    
    def _init_vector_db(self):
        """初始化向量数据库"""
        try:
            import chromadb
            from chromadb.config import Settings
            
            self.db_path.mkdir(parents=True, exist_ok=True)
            
            self.chroma_client = chromadb.PersistentClient(
                path=str(self.db_path),
                settings=Settings(anonymized_telemetry=False)
            )
            
            # 获取或创建集合
            self.collection = self.chroma_client.get_or_create_collection(
                name="knowledge_base",
                metadata={"description": "SmartParser 知识库"}
            )
            
            console.print(f"[green]✓[/green] 向量数据库初始化成功 (已有 {self.collection.count()} 条记录)")
        except Exception as e:
            console.print(f"[red]✗[/red] 向量数据库初始化失败: {e}")
            self.chroma_client = None
            self.collection = None
    
    def _init_text_splitter(self):
        """初始化语义分块器"""
        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            
            # 使用递归字符分割器（在无法使用语义分块时的备选方案）
            # 语义分块需要 embedding，可能会消耗较多 API 调用
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=100,
                separators=["\n\n", "\n", "。", "；", "，", " ", ""],
                length_function=len
            )
            console.print("[green]✓[/green] 文本分块器初始化成功")
        except Exception as e:
            console.print(f"[red]✗[/red] 文本分块器初始化失败: {e}")
            self.text_splitter = None
    
    def load_markdown_files(self, folder_path: str) -> List[Dict[str, Any]]:
        """
        加载 Markdown 文件
        
        Args:
            folder_path: Markdown 文件夹路径
            
        Returns:
            文档列表，每个文档包含 content 和 metadata
        """
        folder = Path(folder_path)
        documents = []
        
        if not folder.exists():
            console.print(f"[red]✗[/red] 文件夹不存在: {folder}")
            return documents
        
        md_files = list(folder.glob("*.md"))
        console.print(f"[blue]→[/blue] 发现 {len(md_files)} 个 Markdown 文件")
        
        for md_file in md_files:
            try:
                content = md_file.read_text(encoding='utf-8')
                documents.append({
                    "content": content,
                    "metadata": {
                        "source": md_file.name,
                        "file_path": str(md_file),
                        "load_time": datetime.now().isoformat()
                    }
                })
                console.print(f"  [dim]已加载: {md_file.name}[/dim]")
            except Exception as e:
                console.print(f"  [red]加载失败 {md_file.name}: {e}[/red]")
        
        return documents
    
    def semantic_chunk(self, content: str, metadata: Dict = None) -> List[Dict]:
        """
        对文本进行语义分块
        
        Args:
            content: 文本内容
            metadata: 元数据
            
        Returns:
            分块列表
        """
        if not self.text_splitter:
            return [{"content": content, "metadata": metadata or {}}]
        
        chunks = self.text_splitter.split_text(content)
        
        result = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = (metadata or {}).copy()
            chunk_metadata["chunk_index"] = i
            chunk_metadata["total_chunks"] = len(chunks)
            result.append({
                "content": chunk,
                "metadata": chunk_metadata
            })
        
        return result
    
    def extract_knowledge_point(self, chunk_content: str) -> Optional[Dict]:
        """
        使用大模型提取知识点信息
        
        Args:
            chunk_content: 分块内容
            
        Returns:
            知识点元数据字典
        """
        if not self.llm:
            # 如果 LLM 不可用，返回默认值
            return {
                "knowledge_name": "未命名知识点",
                "core_concept": chunk_content[:50] + "...",
                "category": "未分类",
                "importance": 3,
                "keywords": []
            }
        
        try:
            prompt = KNOWLEDGE_EXTRACTION_PROMPT.format(content=chunk_content[:1000])
            response = self.llm.invoke(prompt)
            
            # 解析 JSON 响应
            response_text = response.content.strip()
            
            # 尝试清理可能的 markdown 代码块
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1])
            
            knowledge_info = json.loads(response_text)
            return knowledge_info
            
        except json.JSONDecodeError as e:
            console.print(f"[yellow]⚠[/yellow] JSON 解析失败，使用默认值")
            return {
                "knowledge_name": "解析错误",
                "core_concept": chunk_content[:50],
                "category": "未分类",
                "importance": 3,
                "keywords": []
            }
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] 知识点提取失败: {e}")
            return None
    
    def store_to_vector_db(
        self,
        chunks: List[Dict],
        extract_knowledge: bool = True
    ) -> int:
        """
        将分块存储到向量数据库
        
        Args:
            chunks: 分块列表
            extract_knowledge: 是否提取知识点信息
            
        Returns:
            成功存储的数量
        """
        if not self.collection:
            console.print("[red]✗[/red] 向量数据库不可用")
            return 0
        
        success_count = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("存储知识点...", total=len(chunks))
            
            for chunk in chunks:
                try:
                    content = chunk["content"]
                    metadata = chunk["metadata"].copy()
                    
                    # 提取知识点信息
                    if extract_knowledge:
                        knowledge_info = self.extract_knowledge_point(content)
                        if knowledge_info:
                            metadata.update({
                                "knowledge_name": knowledge_info.get("knowledge_name", ""),
                                "core_concept": knowledge_info.get("core_concept", ""),
                                "category": knowledge_info.get("category", ""),
                                "importance": knowledge_info.get("importance", 3),
                                "keywords": ",".join(knowledge_info.get("keywords", []))
                            })
                    
                    # 生成唯一 ID
                    doc_id = hashlib.md5(content.encode()).hexdigest()
                    
                    # 检查是否已存在
                    existing = self.collection.get(ids=[doc_id])
                    if existing and existing['ids']:
                        progress.advance(task)
                        continue
                    
                    # 存储到数据库
                    self.collection.add(
                        documents=[content],
                        metadatas=[metadata],
                        ids=[doc_id]
                    )
                    
                    success_count += 1
                    progress.advance(task)
                    
                except Exception as e:
                    console.print(f"[red]存储失败: {e}[/red]")
                    progress.advance(task)
        
        return success_count
    
    def query_knowledge(
        self,
        user_query: str,
        top_k: int = 3
    ) -> List[Dict]:
        """
        知识检索接口
        
        Args:
            user_query: 用户查询
            top_k: 返回的结果数量
            
        Returns:
            检索结果列表
        """
        if not self.collection:
            console.print("[red]✗[/red] 向量数据库不可用")
            return []
        
        if self.collection.count() == 0:
            console.print("[yellow]⚠[/yellow] 知识库为空，请先导入文档")
            return []
        
        try:
            # 执行查询
            results = self.collection.query(
                query_texts=[user_query],
                n_results=min(top_k, self.collection.count())
            )
            
            # 格式化结果
            formatted_results = []
            
            if results and results['documents']:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                    distance = results['distances'][0][i] if results['distances'] else 0
                    
                    formatted_results.append({
                        "rank": i + 1,
                        "content": doc,
                        "source": metadata.get("source", "未知来源"),
                        "knowledge_name": metadata.get("knowledge_name", ""),
                        "core_concept": metadata.get("core_concept", ""),
                        "category": metadata.get("category", ""),
                        "importance": metadata.get("importance", 0),
                        "relevance_score": 1 - distance  # 转换为相似度分数
                    })
            
            return formatted_results
            
        except Exception as e:
            console.print(f"[red]✗[/red] 查询失败: {e}")
            return []
    
    def process_documents(
        self,
        folder_path: str,
        extract_knowledge: bool = True
    ) -> Dict:
        """
        处理文档的完整流程
        
        Args:
            folder_path: Markdown 文件夹路径
            extract_knowledge: 是否提取知识点
            
        Returns:
            处理统计
        """
        stats = {
            "files_loaded": 0,
            "chunks_created": 0,
            "chunks_stored": 0
        }
        
        console.print(Panel("开始处理文档...", style="blue"))
        
        # 1. 加载文档
        documents = self.load_markdown_files(folder_path)
        stats["files_loaded"] = len(documents)
        
        if not documents:
            console.print("[yellow]没有找到要处理的文档[/yellow]")
            return stats
        
        # 2. 语义分块
        all_chunks = []
        for doc in documents:
            chunks = self.semantic_chunk(doc["content"], doc["metadata"])
            all_chunks.extend(chunks)
        
        stats["chunks_created"] = len(all_chunks)
        console.print(f"[blue]→[/blue] 共创建 {len(all_chunks)} 个文本块")
        
        # 3. 存储到向量数据库
        stored = self.store_to_vector_db(all_chunks, extract_knowledge)
        stats["chunks_stored"] = stored
        
        # 显示统计
        table = Table(title="处理统计")
        table.add_column("指标", style="cyan")
        table.add_column("数量", style="magenta")
        table.add_row("加载文件数", str(stats["files_loaded"]))
        table.add_row("创建分块数", str(stats["chunks_created"]))
        table.add_row("存储知识点", str(stats["chunks_stored"]))
        table.add_row("数据库总量", str(self.collection.count() if self.collection else 0))
        console.print(table)
        
        return stats
    
    def display_results(self, results: List[Dict]):
        """
        美化显示查询结果
        
        Args:
            results: 查询结果列表
        """
        if not results:
            console.print("[yellow]未找到相关知识点[/yellow]")
            return
        
        console.print(f"\n[green]找到 {len(results)} 个相关知识点：[/green]\n")
        
        for r in results:
            console.print(Panel(
                f"[bold]{r.get('knowledge_name', '未命名')}[/bold]\n\n"
                f"[dim]核心概念：[/dim]{r.get('core_concept', '')}\n"
                f"[dim]来源文件：[/dim]{r.get('source', '未知')}\n"
                f"[dim]所属类别：[/dim]{r.get('category', '未分类')} | "
                f"[dim]重要程度：[/dim]{'⭐' * r.get('importance', 0)}\n\n"
                f"[dim]相关内容：[/dim]\n{r.get('content', '')[:300]}...",
                title=f"#{r['rank']} (相关度: {r.get('relevance_score', 0):.2%})",
                border_style="blue"
            ))


# ============================================================================
# 命令行入口
# ============================================================================
def main():
    """主入口函数"""
    console.print(Panel("""
╔═══════════════════════════════════════════════════════════╗
║           Knowledge Manager - 知识管理器                  ║
║                                                           ║
║  功能：语义分块 | 知识提取 | 向量存储 | 智能检索          ║
╚═══════════════════════════════════════════════════════════╝
    """, style="blue"))
    
    # 检查 API Key
    if API_KEY == "your-deepseek-api-key-here":
        console.print("[yellow]⚠ 警告：未配置 API_KEY，知识点提取功能将使用默认值[/yellow]")
        console.print("[dim]请设置环境变量 DEEPSEEK_API_KEY 或修改代码中的 API_KEY[/dim]\n")
    
    # 初始化管理器
    base_dir = Path(__file__).parent
    manager = KnowledgeManager(
        db_path=str(base_dir / "chroma_db")
    )
    
    # 处理文档
    output_folder = base_dir / "output_markdown"
    
    # 检查是否需要提取知识点（有 API Key 时才提取）
    extract_knowledge = API_KEY != "your-deepseek-api-key-here"
    
    manager.process_documents(
        str(output_folder),
        extract_knowledge=extract_knowledge
    )
    
    console.print("\n[green]✓ 文档处理完成！[/green]")
    console.print("[dim]使用 test_query.py 进行知识检索测试[/dim]")


if __name__ == "__main__":
    main()
