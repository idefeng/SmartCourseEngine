#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
课件质量评估器 (Courseware Quality Evaluator)
==============================================

自动分析课件质量，生成评估报告：
- 内容完整性检查
- 知识点覆盖度分析
- 结构合理性评估
- 可读性评分

作者: SmartCourseEngine Team
日期: 2026-01-31
"""

import re
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress

console = Console()


# ============================================================================
# 评估标准配置
# ============================================================================
QUALITY_CRITERIA = {
    "结构完整性": {
        "weight": 0.25,
        "description": "课件是否包含完整的教学结构（导入、核心、案例、总结）"
    },
    "内容丰富度": {
        "weight": 0.25,
        "description": "内容是否足够详细，知识点是否充分展开"
    },
    "知识点覆盖": {
        "weight": 0.20,
        "description": "课件是否覆盖了素材中的关键知识点"
    },
    "练习题质量": {
        "weight": 0.15,
        "description": "练习题是否多样化、与内容相关"
    },
    "可读性": {
        "weight": 0.15,
        "description": "内容表达是否清晰易懂"
    }
}

# 必需的大纲部分
REQUIRED_SECTIONS = ["introduction", "core_content", "case_analysis", "summary"]
SECTION_NAMES = {
    "introduction": "导入部分",
    "core_content": "核心讲解",
    "case_analysis": "案例分析",
    "summary": "总结部分"
}


# ============================================================================
# 评估结果数据类
# ============================================================================
@dataclass
class QualityScore:
    """单项评估分数"""
    criterion: str
    score: float  # 0-100
    max_score: float
    weight: float
    details: str
    suggestions: List[str] = field(default_factory=list)


@dataclass
class QualityReport:
    """质量评估报告"""
    topic: str
    generated_at: str
    overall_score: float
    grade: str  # A/B/C/D/F
    scores: List[QualityScore]
    summary: str
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]


# ============================================================================
# 课件质量评估器
# ============================================================================
class CoursewareEvaluator:
    """
    课件质量评估器
    
    分析课件各方面质量并生成评估报告。
    """
    
    def __init__(self):
        """初始化评估器"""
        self.criteria = QUALITY_CRITERIA
    
    def evaluate(self, courseware: Dict, knowledge_sources: List[Dict] = None) -> QualityReport:
        """
        评估课件质量
        
        Args:
            courseware: 课件数据
            knowledge_sources: 原始知识点（用于对比覆盖度）
            
        Returns:
            质量评估报告
        """
        topic = courseware.get("topic", "未命名课件")
        console.print(Panel(f"正在评估课件质量: [bold]{topic}[/bold]", style="blue"))
        
        scores = []
        
        # 1. 评估结构完整性
        structure_score = self._evaluate_structure(courseware)
        scores.append(structure_score)
        console.print(f"  [dim]结构完整性: {structure_score.score:.0f}/100[/dim]")
        
        # 2. 评估内容丰富度
        content_score = self._evaluate_content_richness(courseware)
        scores.append(content_score)
        console.print(f"  [dim]内容丰富度: {content_score.score:.0f}/100[/dim]")
        
        # 3. 评估知识点覆盖
        coverage_score = self._evaluate_knowledge_coverage(courseware, knowledge_sources)
        scores.append(coverage_score)
        console.print(f"  [dim]知识点覆盖: {coverage_score.score:.0f}/100[/dim]")
        
        # 4. 评估练习题质量
        quiz_score = self._evaluate_quiz_quality(courseware)
        scores.append(quiz_score)
        console.print(f"  [dim]练习题质量: {quiz_score.score:.0f}/100[/dim]")
        
        # 5. 评估可读性
        readability_score = self._evaluate_readability(courseware)
        scores.append(readability_score)
        console.print(f"  [dim]可读性: {readability_score.score:.0f}/100[/dim]")
        
        # 计算总分
        overall_score = sum(s.score * s.weight for s in scores)
        grade = self._calculate_grade(overall_score)
        
        # 生成报告
        report = self._generate_report(topic, scores, overall_score, grade)
        
        console.print(f"\n[green]✓[/green] 评估完成! 总分: [bold]{overall_score:.1f}[/bold] 等级: [bold]{grade}[/bold]")
        
        return report
    
    def _evaluate_structure(self, courseware: Dict) -> QualityScore:
        """评估结构完整性"""
        outline = courseware.get("outline", {})
        scripts = courseware.get("scripts", [])
        
        score = 0
        max_score = 100
        suggestions = []
        details_parts = []
        
        # 检查大纲是否存在
        if not outline:
            return QualityScore(
                criterion="结构完整性",
                score=0,
                max_score=max_score,
                weight=self.criteria["结构完整性"]["weight"],
                details="缺少课程大纲",
                suggestions=["需要生成完整的课程大纲"]
            )
        
        # 检查必需部分
        present_sections = []
        missing_sections = []
        
        for section in REQUIRED_SECTIONS:
            if outline.get(section):
                present_sections.append(SECTION_NAMES[section])
                score += 20  # 每个部分 20 分
            else:
                missing_sections.append(SECTION_NAMES[section])
                suggestions.append(f"建议添加「{SECTION_NAMES[section]}」")
        
        # 检查脚本是否与大纲对应
        if len(scripts) >= len(REQUIRED_SECTIONS):
            score += 20  # 脚本完整性加分
        else:
            script_count = len(scripts)
            section_count = len([s for s in REQUIRED_SECTIONS if outline.get(s)])
            if script_count < section_count:
                suggestions.append(f"脚本数量({script_count})少于大纲章节数({section_count})")
        
        details = f"包含: {', '.join(present_sections) if present_sections else '无'}"
        if missing_sections:
            details += f"; 缺少: {', '.join(missing_sections)}"
        
        return QualityScore(
            criterion="结构完整性",
            score=min(score, max_score),
            max_score=max_score,
            weight=self.criteria["结构完整性"]["weight"],
            details=details,
            suggestions=suggestions
        )
    
    def _evaluate_content_richness(self, courseware: Dict) -> QualityScore:
        """评估内容丰富度"""
        scripts = courseware.get("scripts", []) or courseware.get("audio_scripts", [])
        
        score = 0
        max_score = 100
        suggestions = []
        
        if not scripts:
            return QualityScore(
                criterion="内容丰富度",
                score=0,
                max_score=max_score,
                weight=self.criteria["内容丰富度"]["weight"],
                details="没有任何脚本内容",
                suggestions=["需要生成讲解脚本"]
            )
        
        # 统计内容
        total_chars = 0
        section_stats = []
        
        for script in scripts:
            content = script.get("content", "")
            char_count = len(content)
            total_chars += char_count
            
            section = script.get("section", "未命名")
            section_stats.append((section, char_count))
        
        # 评分标准
        # - 总字数 >= 3000: 满分
        # - 总字数 >= 2000: 80分
        # - 总字数 >= 1000: 60分
        # - 总字数 >= 500: 40分
        # - 总字数 < 500: 20分
        
        if total_chars >= 3000:
            score = 100
        elif total_chars >= 2000:
            score = 80
        elif total_chars >= 1000:
            score = 60
        elif total_chars >= 500:
            score = 40
        else:
            score = 20
            suggestions.append("内容较少，建议扩充讲解内容")
        
        # 检查各部分是否均衡
        if section_stats:
            avg_chars = total_chars / len(section_stats)
            for section, chars in section_stats:
                if chars < avg_chars * 0.3:
                    suggestions.append(f"「{section}」内容较少，建议补充")
        
        details = f"总内容量: {total_chars} 字 ({len(scripts)} 个章节)"
        
        return QualityScore(
            criterion="内容丰富度",
            score=score,
            max_score=max_score,
            weight=self.criteria["内容丰富度"]["weight"],
            details=details,
            suggestions=suggestions
        )
    
    def _evaluate_knowledge_coverage(
        self, 
        courseware: Dict, 
        knowledge_sources: List[Dict] = None
    ) -> QualityScore:
        """评估知识点覆盖度"""
        scripts = courseware.get("scripts", []) or courseware.get("audio_scripts", [])
        outline = courseware.get("outline", {})
        
        score = 0
        max_score = 100
        suggestions = []
        
        # 提取课件中的关键词
        all_content = " ".join([s.get("content", "") for s in scripts])
        
        # 从大纲中提取知识点
        knowledge_points = []
        for section in REQUIRED_SECTIONS:
            section_data = outline.get(section, {})
            points = section_data.get("points", [])
            knowledge_points.extend(points)
        
        if not knowledge_points:
            # 如果没有明确的知识点，基于内容长度给分
            if len(all_content) > 1000:
                score = 60
                details = "大纲中未定义明确知识点，基于内容量评估"
            else:
                score = 30
                details = "知识点不明确，内容量较少"
            
            return QualityScore(
                criterion="知识点覆盖",
                score=score,
                max_score=max_score,
                weight=self.criteria["知识点覆盖"]["weight"],
                details=details,
                suggestions=["建议在大纲中明确定义知识点"]
            )
        
        # 检查每个知识点是否在内容中有体现
        covered_points = []
        uncovered_points = []
        
        for point in knowledge_points:
            # 提取关键词（简单分词）
            keywords = [w for w in point.split() if len(w) > 1]
            if not keywords:
                keywords = [point[:10]] if len(point) >= 10 else [point]
            
            # 检查是否在内容中出现
            covered = any(kw in all_content for kw in keywords) or point[:10] in all_content
            
            if covered:
                covered_points.append(point)
            else:
                uncovered_points.append(point)
        
        # 计算覆盖率
        coverage_rate = len(covered_points) / len(knowledge_points) if knowledge_points else 0
        score = coverage_rate * 100
        
        if uncovered_points:
            for point in uncovered_points[:3]:  # 最多显示3个
                suggestions.append(f"知识点「{point[:20]}...」可能未充分展开")
        
        details = f"覆盖率: {coverage_rate*100:.0f}% ({len(covered_points)}/{len(knowledge_points)} 个知识点)"
        
        return QualityScore(
            criterion="知识点覆盖",
            score=score,
            max_score=max_score,
            weight=self.criteria["知识点覆盖"]["weight"],
            details=details,
            suggestions=suggestions
        )
    
    def _evaluate_quiz_quality(self, courseware: Dict) -> QualityScore:
        """评估练习题质量"""
        quizzes = courseware.get("quizzes", [])
        
        score = 0
        max_score = 100
        suggestions = []
        
        if not quizzes:
            return QualityScore(
                criterion="练习题质量",
                score=30,  # 没有练习题给基础分
                max_score=max_score,
                weight=self.criteria["练习题质量"]["weight"],
                details="未包含练习题",
                suggestions=["建议添加练习题以巩固学习效果"]
            )
        
        # 统计题目类型
        question_types = {}
        has_answer = 0
        has_explanation = 0
        
        for quiz in quizzes:
            # 统计各类题型
            for q_type in ["choice", "judgment", "case"]:
                if quiz.get(q_type):
                    question_types[q_type] = question_types.get(q_type, 0) + 1
                    
                    q = quiz[q_type]
                    if q.get("answer"):
                        has_answer += 1
                    if q.get("explanation"):
                        has_explanation += 1
        
        total_questions = sum(question_types.values())
        
        # 评分
        # - 题目数量分 (30分): 每题10分，最高30分
        score += min(total_questions * 10, 30)
        
        # - 题型多样性分 (30分): 每种类型10分
        score += len(question_types) * 10
        
        # - 答案解析完整性 (40分)
        if total_questions > 0:
            answer_rate = has_answer / total_questions
            explain_rate = has_explanation / total_questions
            score += answer_rate * 20
            score += explain_rate * 20
            
            if explain_rate < 0.8:
                suggestions.append("部分题目缺少详细解析")
        
        # 检查建议
        if len(question_types) < 3:
            missing_types = []
            if "choice" not in question_types:
                missing_types.append("选择题")
            if "judgment" not in question_types:
                missing_types.append("判断题")
            if "case" not in question_types:
                missing_types.append("案例分析题")
            if missing_types:
                suggestions.append(f"建议添加: {', '.join(missing_types)}")
        
        type_names = {"choice": "选择", "judgment": "判断", "case": "案例"}
        type_summary = ", ".join([f"{type_names.get(t, t)}题{c}道" for t, c in question_types.items()])
        details = f"共 {total_questions} 道题 ({type_summary})"
        
        return QualityScore(
            criterion="练习题质量",
            score=min(score, max_score),
            max_score=max_score,
            weight=self.criteria["练习题质量"]["weight"],
            details=details,
            suggestions=suggestions
        )
    
    def _evaluate_readability(self, courseware: Dict) -> QualityScore:
        """评估可读性"""
        scripts = courseware.get("scripts", []) or courseware.get("audio_scripts", [])
        
        score = 0
        max_score = 100
        suggestions = []
        
        if not scripts:
            return QualityScore(
                criterion="可读性",
                score=0,
                max_score=max_score,
                weight=self.criteria["可读性"]["weight"],
                details="没有内容可评估",
                suggestions=["需要生成内容"]
            )
        
        all_content = " ".join([s.get("content", "") for s in scripts])
        
        # 分析指标
        total_chars = len(all_content)
        
        # 1. 句子长度分析
        sentences = re.split(r'[。！？；]', all_content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if sentences:
            avg_sentence_len = sum(len(s) for s in sentences) / len(sentences)
            
            # 理想句长 30-60 字
            if 30 <= avg_sentence_len <= 60:
                score += 30
            elif 20 <= avg_sentence_len <= 80:
                score += 20
            else:
                score += 10
                if avg_sentence_len > 80:
                    suggestions.append("部分句子较长，建议适当拆分")
                elif avg_sentence_len < 20:
                    suggestions.append("句子较短，可以适当补充信息")
        
        # 2. 段落结构分析
        paragraphs = all_content.split("\n")
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        if len(paragraphs) >= 5:
            score += 25
        elif len(paragraphs) >= 3:
            score += 15
        else:
            score += 5
            suggestions.append("建议增加段落划分，提高层次感")
        
        # 3. 标点符号使用
        punctuation_count = len(re.findall(r'[，。！？；：、""''（）]', all_content))
        punctuation_density = punctuation_count / total_chars if total_chars > 0 else 0
        
        if 0.03 <= punctuation_density <= 0.10:
            score += 25
        elif punctuation_density > 0:
            score += 15
        else:
            suggestions.append("标点符号使用较少，影响阅读节奏")
        
        # 4. 过渡词使用
        transition_words = ["首先", "其次", "然后", "接下来", "最后", "总之", 
                           "因此", "所以", "但是", "然而", "例如", "比如"]
        transition_count = sum(1 for w in transition_words if w in all_content)
        
        if transition_count >= 5:
            score += 20
        elif transition_count >= 2:
            score += 10
        else:
            score += 5
            suggestions.append("建议使用更多过渡词增强逻辑连贯性")
        
        details = f"平均句长: {avg_sentence_len:.0f}字, 段落数: {len(paragraphs)}, 过渡词: {transition_count}个"
        
        return QualityScore(
            criterion="可读性",
            score=min(score, max_score),
            max_score=max_score,
            weight=self.criteria["可读性"]["weight"],
            details=details,
            suggestions=suggestions
        )
    
    def _calculate_grade(self, score: float) -> str:
        """计算等级"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    def _generate_report(
        self, 
        topic: str, 
        scores: List[QualityScore], 
        overall_score: float,
        grade: str
    ) -> QualityReport:
        """生成评估报告"""
        # 识别优势和劣势
        strengths = []
        weaknesses = []
        recommendations = []
        
        for s in scores:
            if s.score >= 80:
                strengths.append(f"{s.criterion}: {s.details}")
            elif s.score < 60:
                weaknesses.append(f"{s.criterion}: {s.details}")
                recommendations.extend(s.suggestions)
        
        # 生成总结
        if grade == "A":
            summary = "课件质量优秀，内容完整、结构清晰，适合直接使用。"
        elif grade == "B":
            summary = "课件质量良好，整体结构合理，少数方面可进一步优化。"
        elif grade == "C":
            summary = "课件质量中等，基本满足教学需求，建议参考改进建议进行优化。"
        elif grade == "D":
            summary = "课件质量待提升，存在明显不足，建议重点改进后使用。"
        else:
            summary = "课件质量较差，需要重新生成或大幅修改。"
        
        return QualityReport(
            topic=topic,
            generated_at=datetime.now().isoformat(),
            overall_score=overall_score,
            grade=grade,
            scores=scores,
            summary=summary,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=list(set(recommendations))  # 去重
        )
    
    def print_report(self, report: QualityReport):
        """打印评估报告"""
        console.print("\n")
        console.print(Panel(
            f"[bold]课件质量评估报告[/bold]\n\n"
            f"主题: {report.topic}\n"
            f"评估时间: {report.generated_at}\n\n"
            f"[bold green]总分: {report.overall_score:.1f} / 100[/bold green]\n"
            f"[bold]等级: {report.grade}[/bold]",
            title="📊 评估结果",
            style="blue"
        ))
        
        # 评分详情表格
        table = Table(title="评分详情", show_header=True, header_style="bold")
        table.add_column("评估维度", style="cyan")
        table.add_column("得分", justify="right")
        table.add_column("权重", justify="right")
        table.add_column("说明")
        
        for s in report.scores:
            score_style = "green" if s.score >= 80 else ("yellow" if s.score >= 60 else "red")
            table.add_row(
                s.criterion,
                f"[{score_style}]{s.score:.0f}[/{score_style}]",
                f"{s.weight*100:.0f}%",
                s.details
            )
        
        console.print(table)
        
        # 总结
        console.print(f"\n[bold]📝 总结:[/bold] {report.summary}")
        
        # 优势
        if report.strengths:
            console.print("\n[bold green]✅ 优势:[/bold green]")
            for s in report.strengths:
                console.print(f"  • {s}")
        
        # 劣势
        if report.weaknesses:
            console.print("\n[bold yellow]⚠️ 待改进:[/bold yellow]")
            for w in report.weaknesses:
                console.print(f"  • {w}")
        
        # 建议
        if report.recommendations:
            console.print("\n[bold blue]💡 改进建议:[/bold blue]")
            for r in report.recommendations:
                console.print(f"  • {r}")
    
    def export_report(self, report: QualityReport, output_path: str = None) -> str:
        """导出报告为 Markdown 文件"""
        if not output_path:
            safe_topic = re.sub(r'[\\/:"*?<>|]', '_', report.topic)
            output_path = f"quality_report_{safe_topic}.md"
        
        content = f"""# 课件质量评估报告

## 基本信息

- **主题**: {report.topic}
- **评估时间**: {report.generated_at}
- **总分**: {report.overall_score:.1f} / 100
- **等级**: {report.grade}

---

## 评估总结

{report.summary}

---

## 评分详情

| 评估维度 | 得分 | 权重 | 说明 |
|----------|------|------|------|
"""
        for s in report.scores:
            content += f"| {s.criterion} | {s.score:.0f} | {s.weight*100:.0f}% | {s.details} |\n"
        
        if report.strengths:
            content += "\n---\n\n## ✅ 优势\n\n"
            for s in report.strengths:
                content += f"- {s}\n"
        
        if report.weaknesses:
            content += "\n---\n\n## ⚠️ 待改进\n\n"
            for w in report.weaknesses:
                content += f"- {w}\n"
        
        if report.recommendations:
            content += "\n---\n\n## 💡 改进建议\n\n"
            for r in report.recommendations:
                content += f"- {r}\n"
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        console.print(f"\n[green]✓[/green] 报告已导出: {output_path}")
        return output_path


# ============================================================================
# CLI 入口
# ============================================================================
def main():
    """主入口函数"""
    console.print(Panel("""
╔═══════════════════════════════════════════════════════════╗
║     Courseware Quality Evaluator - 课件质量评估器          ║
║                                                           ║
║     自动分析课件质量，生成评估报告                         ║
╚═══════════════════════════════════════════════════════════╝
    """, style="blue"))
    
    # 示例使用
    console.print("[dim]使用方法: 在 Python 中导入并调用[/dim]")
    console.print("""
    from quality_evaluator import CoursewareEvaluator
    
    evaluator = CoursewareEvaluator()
    report = evaluator.evaluate(courseware)
    evaluator.print_report(report)
    """)


if __name__ == "__main__":
    main()
