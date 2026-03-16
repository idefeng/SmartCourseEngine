#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
演示脚本：教学质量评估 MVP
========================
模拟课堂转录文本，利用 AI 进行教学指标分析（互动率、知识覆盖、改进建议）。
"""

import os
from pathlib import Path
from knowledge_manager import KnowledgeManager

class QualityEvaluator:
    def __init__(self, manager: KnowledgeManager):
        self.manager = manager

    def evaluate_lesson(self, transcript: str):
        print("\n正在分析课堂转录文本...")
        
        prompt = f"""
你是教育督导专家，请根据以下课堂转录内容，生成一份详细的教学质量评估报告。

【课堂转录片段】
{transcript}

【评估指标】
1. 互动率分析：老师提问与学生回答的频次及效果。
2. 知识覆盖度：是否涵盖了“阴阳五行”的核心要点。
3. 语速与口头禅：分析语言是否流畅，识别高频无用语。
4. 改进建议：给老师的 3 条具体优化建议。

请以 JSON 格式输出，方便前端仪表盘展示。格式如下：
{{
    "interaction_score": 0-100,
    "knowledge_coverage": 0-100,
    "fluency_score": 0-100,
    "metrics": {{
        "questions_asked": 5,
        "student_replies": 3,
        "filler_words": ["那个", "然后"]
    }},
    "summary": "简要评价",
    "suggestions": ["建议1", "建议2"]
}}
"""
        print("正在调用 LLM 进行教学质量评估...")
        response = self.manager.llm.invoke(prompt)
        return response.content

def main():
    manager = KnowledgeManager()
    evaluator = QualityEvaluator(manager)
    
    # 模拟一段课堂对话
    mock_transcript = """
老师：同学们好，今天我们来讲讲中医的阴阳。谁能告诉我生活中什么是阳？
学生A：老师，太阳是阳吗？
老师：非常好。太阳是阳，月亮就是阴。那么，动的是阳还是静的是阳？
学生B：动的是阳。
老师：对。就像中医里，温热的、上升的都属于阳。那个，我们要记住，阴阳是相互转化的。
老师：大家再看看五行，木生火，火生土。这不仅是自然规律，也是人体脏腑的规律。
    """
    
    report = evaluator.evaluate_lesson(mock_transcript)
    
    output_path = Path(__file__).parent / "generated_courseware" / "quality_report_demo.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding='utf-8')
    
    print("\n" + "="*50)
    print(f"教学质量评估完成！已保存至: {output_path}")
    print("="*50)
    print("\n模拟报告预览：\n")
    print(report)

if __name__ == "__main__":
    main()
