#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
演示脚本：PPT 大纲与讲稿生成
==========================
基于提取的中医知识点，自动生成符合教学逻辑的 PPT 结构。
"""

import os
import json
from pathlib import Path
from knowledge_manager import KnowledgeManager

class PPTGenerator:
    def __init__(self, manager: KnowledgeManager):
        self.manager = manager

    def generate_outline(self, topic: str):
        print(f"\n正在为主题 [{topic}] 检索相关知识点...")
        context = self.manager.query_knowledge(topic, top_k=5)
        
        context_text = "\n".join([f"- {r['knowledge_name']}: {r['content']}" for r in context])
        
        prompt = f"""
你是中医教育专家，请根据以下知识点内容，为课程《{topic}》生成一份演示 PPT 大纲。

【参考知识点】
{context_text}

【要求】
1. 包含 5-8 页 PPT 页面内容。
2. 每页包含：[标题]、[核心要点]、[讲稿（30-50字）]、[视觉设计建议]。
3. 风格专业，逻辑清晰。

请以 Markdown 格式输出。
"""
        print("正在调用 LLM 生成 PPT 大纲...")
        response = self.manager.llm.invoke(prompt)
        return response.content

def main():
    manager = KnowledgeManager()
    gen = PPTGenerator(manager)
    
    topic = "阴阳五行学说入门"
    outline = gen.generate_outline(topic)
    
    output_path = Path(__file__).parent / "generated_courseware" / "ppt_outline_demo.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(outline, encoding='utf-8')
    
    print("\n" + "="*50)
    print(f"PPT 大纲生成完成！已保存至: {output_path}")
    print("="*50)
    print("\n预览内容：\n")
    print(outline[:500] + "...")

if __name__ == "__main__":
    main()
