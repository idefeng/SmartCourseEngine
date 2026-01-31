#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交互引擎 (Interaction Engine)
==============================

实现"学-测-补"自适应学习闭环：
- 视频内嵌互动：知识点结束时弹出练习题
- 智能错因分析：LLM 分析答错原因
- 个性化补漏路径：连续答错时推荐补充材料
- 学习数据追踪：记录学习进度和表现

作者: SmartCourseEngine Team
日期: 2026-01-31
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import re

# Rich 美化输出（命令行）
from rich.console import Console

console = Console()

# ============================================================================
# API 配置
# ============================================================================
API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
BASE_URL = os.getenv("API_BASE_URL", "https://api.deepseek.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-chat")


# ============================================================================
# 数据模型
# ============================================================================
class AnswerResult(Enum):
    """答题结果枚举"""
    CORRECT = "correct"
    INCORRECT = "incorrect"
    SKIPPED = "skipped"


@dataclass
class QuizAttempt:
    """单次答题记录"""
    quiz_id: str
    knowledge_point: str
    question: str
    user_answer: str
    correct_answer: str
    result: AnswerResult
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    time_spent_seconds: float = 0
    error_analysis: str = ""


@dataclass
class KnowledgePointProgress:
    """知识点学习进度"""
    knowledge_point: str
    total_attempts: int = 0
    correct_count: int = 0
    consecutive_errors: int = 0
    last_attempt_time: str = ""
    total_watch_time_seconds: float = 0
    remediation_shown: bool = False
    mastery_level: float = 0.0  # 0-1
    
    @property
    def accuracy_rate(self) -> float:
        """正确率"""
        if self.total_attempts == 0:
            return 0.0
        return self.correct_count / self.total_attempts


@dataclass
class LearningSession:
    """学习会话"""
    session_id: str
    user_id: str = "default_user"
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    end_time: str = ""
    course_topic: str = ""
    current_section_index: int = 0
    current_video_position: float = 0.0
    is_paused_for_quiz: bool = False
    quiz_attempts: List[QuizAttempt] = field(default_factory=list)
    knowledge_progress: Dict[str, KnowledgePointProgress] = field(default_factory=dict)
    unlocked_sections: List[int] = field(default_factory=lambda: [0])  # 默认解锁第一节


@dataclass
class RemediationContent:
    """补漏内容"""
    knowledge_point: str
    content_type: str  # "text", "video", "example"
    content: str
    source: str = ""
    difficulty_level: str = "basic"  # basic, intermediate, advanced


# ============================================================================
# Prompts
# ============================================================================
ERROR_ANALYSIS_PROMPT = """你是一位经验丰富的教育诊断专家。学生在一道关于"{knowledge_point}"的题目中选择了错误答案。

【题目】
{question}

【选项】
{options}

【学生答案】{user_answer}
【正确答案】{correct_answer}

请分析学生答错的可能原因，并给出针对性的解释。要求：
1. 分析学生选择该错误选项可能的思维误区
2. 解释正确答案的依据
3. 给出帮助理解的小技巧或记忆方法
4. 语言要友善鼓励，不要让学生感到挫败

请用300字以内回答。"""

REMEDIATION_SUGGESTION_PROMPT = """学生在"{knowledge_point}"这个知识点上连续答错了两次或以上。

【错误记录】
{error_history}

请生成一段补充学习材料，帮助学生从更基础的角度理解这个知识点。要求：
1. 使用更简单的语言和例子
2. 从日常生活场景切入
3. 逐步引导到核心概念
4. 约200字

请直接输出补充材料内容。"""


# ============================================================================
# 交互引擎主类
# ============================================================================
class InteractionEngine:
    """
    交互引擎
    
    管理"学-测-补"自适应学习闭环。
    """
    
    def __init__(
        self,
        api_key: str = API_KEY,
        base_url: str = BASE_URL,
        model_name: str = MODEL_NAME
    ):
        """初始化交互引擎"""
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.llm = None
        self.knowledge_manager = None
        
        self._init_llm()
        self._init_knowledge_manager()
    
    def _init_llm(self):
        """初始化大语言模型"""
        if not self.api_key:
            console.print("[yellow]⚠[/yellow] 未配置 API Key，错因分析功能将受限")
            return
        
        try:
            from langchain_openai import ChatOpenAI
            
            self.llm = ChatOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model_name,
                temperature=0.7
            )
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] LLM 初始化失败: {e}")
    
    def _init_knowledge_manager(self):
        """初始化知识管理器"""
        try:
            from knowledge_manager import KnowledgeManager
            
            base_dir = Path(__file__).parent
            self.knowledge_manager = KnowledgeManager(
                db_path=str(base_dir / "chroma_db")
            )
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] 知识库连接失败: {e}")
    
    def create_session(self, course_topic: str, user_id: str = "default_user") -> LearningSession:
        """
        创建新的学习会话
        
        Args:
            course_topic: 课程主题
            user_id: 用户ID
            
        Returns:
            学习会话对象
        """
        session_id = hashlib.md5(
            f"{user_id}_{course_topic}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        
        return LearningSession(
            session_id=session_id,
            user_id=user_id,
            course_topic=course_topic
        )
    
    def get_quiz_for_section(
        self,
        courseware: Dict,
        section_index: int
    ) -> Optional[Dict]:
        """
        获取指定章节的练习题
        
        Args:
            courseware: 课件数据
            section_index: 章节索引
            
        Returns:
            练习题字典
        """
        quizzes = courseware.get("quizzes", [])
        
        if section_index < len(quizzes):
            quiz = quizzes[section_index]
            quiz["quiz_id"] = f"quiz_{section_index}"
            return quiz
        
        return None
    
    def check_answer(
        self,
        session: LearningSession,
        quiz: Dict,
        user_answer: str,
        question_type: str = "single_choice"
    ) -> Tuple[bool, QuizAttempt]:
        """
        检查用户答案
        
        Args:
            session: 学习会话
            quiz: 练习题
            user_answer: 用户答案
            question_type: 题型
            
        Returns:
            (是否正确, 答题记录)
        """
        quiz_data = quiz.get(question_type, {})
        correct_answer = quiz_data.get("answer", "")
        knowledge_point = quiz.get("knowledge_point", "未知知识点")
        
        # 判断正误
        if question_type == "true_false":
            # 判断题
            is_correct = (user_answer.lower() in ["true", "正确", "是"] and correct_answer == True) or \
                        (user_answer.lower() in ["false", "错误", "否"] and correct_answer == False)
            correct_answer_str = "正确" if correct_answer else "错误"
        else:
            # 选择题
            is_correct = user_answer.upper() == str(correct_answer).upper()
            correct_answer_str = str(correct_answer)
        
        result = AnswerResult.CORRECT if is_correct else AnswerResult.INCORRECT
        
        # 创建答题记录
        attempt = QuizAttempt(
            quiz_id=quiz.get("quiz_id", "unknown"),
            knowledge_point=knowledge_point,
            question=quiz_data.get("question", ""),
            user_answer=user_answer,
            correct_answer=correct_answer_str,
            result=result
        )
        
        # 更新会话记录
        session.quiz_attempts.append(attempt)
        
        # 更新知识点进度
        if knowledge_point not in session.knowledge_progress:
            session.knowledge_progress[knowledge_point] = KnowledgePointProgress(
                knowledge_point=knowledge_point
            )
        
        progress = session.knowledge_progress[knowledge_point]
        progress.total_attempts += 1
        progress.last_attempt_time = datetime.now().isoformat()
        
        if is_correct:
            progress.correct_count += 1
            progress.consecutive_errors = 0
            progress.mastery_level = min(1.0, progress.mastery_level + 0.2)
        else:
            progress.consecutive_errors += 1
            progress.mastery_level = max(0.0, progress.mastery_level - 0.1)
        
        return is_correct, attempt
    
    def analyze_error(
        self,
        quiz: Dict,
        user_answer: str,
        question_type: str = "single_choice"
    ) -> str:
        """
        分析答错原因
        
        Args:
            quiz: 练习题
            user_answer: 用户答案
            question_type: 题型
            
        Returns:
            错因分析文本
        """
        if not self.llm:
            # LLM 不可用时返回默认解析
            quiz_data = quiz.get(question_type, {})
            return quiz_data.get("explanation", "请查看正确答案的解析。")
        
        quiz_data = quiz.get(question_type, {})
        knowledge_point = quiz.get("knowledge_point", "")
        
        # 格式化选项
        if question_type == "single_choice":
            options = quiz_data.get("options", {})
            options_str = "\n".join([f"{k}. {v}" for k, v in options.items()])
        elif question_type == "true_false":
            options_str = "A. 正确\nB. 错误"
        else:
            options_str = ""
        
        prompt = ERROR_ANALYSIS_PROMPT.format(
            knowledge_point=knowledge_point,
            question=quiz_data.get("question", ""),
            options=options_str,
            user_answer=user_answer,
            correct_answer=quiz_data.get("answer", "")
        )
        
        try:
            response = self.llm.invoke(prompt)
            return response.content.strip()
        except Exception as e:
            return f"错因分析暂时不可用。正确答案解析：{quiz_data.get('explanation', '')}"
    
    def needs_remediation(self, session: LearningSession, knowledge_point: str) -> bool:
        """
        判断是否需要补漏
        
        Args:
            session: 学习会话
            knowledge_point: 知识点
            
        Returns:
            是否需要补漏
        """
        progress = session.knowledge_progress.get(knowledge_point)
        
        if not progress:
            return False
        
        # 连续答错 2 次或以上，且未展示过补漏内容
        return progress.consecutive_errors >= 2 and not progress.remediation_shown
    
    def get_remediation_content(
        self,
        knowledge_point: str,
        error_history: List[QuizAttempt]
    ) -> RemediationContent:
        """
        获取补漏内容
        
        Args:
            knowledge_point: 知识点
            error_history: 错误历史
            
        Returns:
            补漏内容
        """
        # 从知识库检索补充材料
        supplementary_content = ""
        
        if self.knowledge_manager:
            try:
                results = self.knowledge_manager.query_knowledge(
                    f"{knowledge_point} 基础概念 入门",
                    top_k=3
                )
                if results:
                    supplementary_content = "\n\n".join([
                        r.get("content", "")[:500] for r in results
                    ])
            except Exception:
                pass
        
        # 如果有 LLM，生成个性化补漏材料
        if self.llm and error_history:
            error_summary = "\n".join([
                f"- 问题: {e.question[:50]}... 选择: {e.user_answer}, 正确: {e.correct_answer}"
                for e in error_history[-3:]
            ])
            
            prompt = REMEDIATION_SUGGESTION_PROMPT.format(
                knowledge_point=knowledge_point,
                error_history=error_summary
            )
            
            try:
                response = self.llm.invoke(prompt)
                generated_content = response.content.strip()
                
                return RemediationContent(
                    knowledge_point=knowledge_point,
                    content_type="text",
                    content=generated_content,
                    source="AI 生成",
                    difficulty_level="basic"
                )
            except Exception:
                pass
        
        # 返回从知识库检索的内容
        if supplementary_content:
            return RemediationContent(
                knowledge_point=knowledge_point,
                content_type="text",
                content=supplementary_content,
                source="知识库",
                difficulty_level="basic"
            )
        
        # 兜底内容
        return RemediationContent(
            knowledge_point=knowledge_point,
            content_type="text",
            content=f"关于"{knowledge_point}"的基础知识：请回顾课程前面的内容，特别注意核心概念的定义和应用场景。",
            source="默认",
            difficulty_level="basic"
        )
    
    def unlock_next_section(self, session: LearningSession) -> bool:
        """
        解锁下一章节
        
        Args:
            session: 学习会话
            
        Returns:
            是否成功解锁
        """
        next_section = session.current_section_index + 1
        
        if next_section not in session.unlocked_sections:
            session.unlocked_sections.append(next_section)
            session.current_section_index = next_section
            return True
        
        return False
    
    def get_section_checkpoint_time(
        self,
        courseware: Dict,
        section_index: int,
        estimated_section_duration: float = 120.0
    ) -> float:
        """
        获取章节检查点时间（秒）
        
        Args:
            courseware: 课件数据
            section_index: 章节索引
            estimated_section_duration: 预估章节时长（秒）
            
        Returns:
            检查点时间（秒）
        """
        # 简单实现：每个章节结束时触发
        # 可以根据实际视频时间戳进行优化
        return (section_index + 1) * estimated_section_duration
    
    def generate_learning_report(self, session: LearningSession) -> Dict:
        """
        生成学习报告
        
        Args:
            session: 学习会话
            
        Returns:
            学习报告数据
        """
        # 计算总体统计
        total_attempts = len(session.quiz_attempts)
        correct_count = sum(
            1 for a in session.quiz_attempts
            if a.result == AnswerResult.CORRECT
        )
        
        # 按知识点统计
        knowledge_stats = []
        for kp, progress in session.knowledge_progress.items():
            knowledge_stats.append({
                "knowledge_point": kp,
                "total_attempts": progress.total_attempts,
                "correct_count": progress.correct_count,
                "accuracy_rate": progress.accuracy_rate,
                "mastery_level": progress.mastery_level,
                "watch_time_minutes": progress.total_watch_time_seconds / 60,
                "needs_review": progress.accuracy_rate < 0.6
            })
        
        # 识别薄弱知识点
        weak_points = [
            ks["knowledge_point"]
            for ks in knowledge_stats
            if ks["accuracy_rate"] < 0.6
        ]
        
        # 识别掌握较好的知识点
        strong_points = [
            ks["knowledge_point"]
            for ks in knowledge_stats
            if ks["accuracy_rate"] >= 0.8
        ]
        
        # 计算学习时长
        if session.end_time:
            end = datetime.fromisoformat(session.end_time)
        else:
            end = datetime.now()
        start = datetime.fromisoformat(session.start_time)
        total_duration = (end - start).total_seconds()
        
        return {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "course_topic": session.course_topic,
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_questions": total_attempts,
                "correct_answers": correct_count,
                "overall_accuracy": correct_count / total_attempts if total_attempts > 0 else 0,
                "total_duration_minutes": total_duration / 60,
                "sections_completed": len(session.unlocked_sections) - 1
            },
            "knowledge_breakdown": knowledge_stats,
            "weak_points": weak_points,
            "strong_points": strong_points,
            "recommendations": self._generate_recommendations(knowledge_stats, weak_points)
        }
    
    def _generate_recommendations(
        self,
        knowledge_stats: List[Dict],
        weak_points: List[str]
    ) -> List[str]:
        """生成学习建议"""
        recommendations = []
        
        if weak_points:
            recommendations.append(
                f"建议重点复习以下知识点：{', '.join(weak_points[:3])}"
            )
        
        low_attempt_points = [
            ks["knowledge_point"]
            for ks in knowledge_stats
            if ks["total_attempts"] < 2
        ]
        if low_attempt_points:
            recommendations.append(
                f"以下知识点练习不足，建议多做练习：{', '.join(low_attempt_points[:3])}"
            )
        
        if not weak_points and not low_attempt_points:
            recommendations.append("您的学习表现优秀！继续保持，可以挑战更高难度的内容。")
        
        return recommendations


# ============================================================================
# PDF 报告生成器
# ============================================================================
class LearningReportPDF:
    """
    学习报告 PDF 生成器
    """
    
    def __init__(self):
        self.pdf_available = False
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            self.pdf_available = True
        except ImportError:
            console.print("[yellow]⚠[/yellow] reportlab 未安装，PDF 导出功能不可用")
    
    def generate(self, report_data: Dict, output_path: str) -> Optional[str]:
        """
        生成 PDF 报告
        
        Args:
            report_data: 报告数据
            output_path: 输出路径
            
        Returns:
            PDF 文件路径，失败返回 None
        """
        if not self.pdf_available:
            return None
        
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            
            # 尝试注册中文字体
            try:
                # Windows 系统字体
                font_path = "C:/Windows/Fonts/simhei.ttf"
                if Path(font_path).exists():
                    pdfmetrics.registerFont(TTFont('SimHei', font_path))
                    chinese_font = 'SimHei'
                else:
                    chinese_font = 'Helvetica'
            except Exception:
                chinese_font = 'Helvetica'
            
            # 创建文档
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )
            
            styles = getSampleStyleSheet()
            
            # 自定义样式
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontName=chinese_font,
                fontSize=24,
                spaceAfter=30,
                alignment=1  # 居中
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontName=chinese_font,
                fontSize=14,
                spaceBefore=20,
                spaceAfter=10
            )
            
            body_style = ParagraphStyle(
                'CustomBody',
                parent=styles['Normal'],
                fontName=chinese_font,
                fontSize=11,
                leading=16
            )
            
            story = []
            
            # 标题
            story.append(Paragraph("学习诊断书", title_style))
            story.append(Spacer(1, 20))
            
            # 基本信息
            summary = report_data.get("summary", {})
            story.append(Paragraph("一、学习概况", heading_style))
            
            info_data = [
                ["课程主题", report_data.get("course_topic", "")],
                ["学习时长", f"{summary.get('total_duration_minutes', 0):.1f} 分钟"],
                ["完成章节", f"{summary.get('sections_completed', 0)} 节"],
                ["答题总数", str(summary.get("total_questions", 0))],
                ["正确数量", str(summary.get("correct_answers", 0))],
                ["总体正确率", f"{summary.get('overall_accuracy', 0) * 100:.1f}%"]
            ]
            
            info_table = Table(info_data, colWidths=[120, 300])
            info_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), chinese_font),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('PADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(info_table)
            story.append(Spacer(1, 20))
            
            # 知识点分析
            story.append(Paragraph("二、知识点掌握情况", heading_style))
            
            kp_data = [["知识点", "答题次数", "正确率", "掌握程度"]]
            for ks in report_data.get("knowledge_breakdown", []):
                mastery = "优秀" if ks["mastery_level"] >= 0.8 else "良好" if ks["mastery_level"] >= 0.6 else "待提升"
                kp_data.append([
                    ks["knowledge_point"][:15],
                    str(ks["total_attempts"]),
                    f"{ks['accuracy_rate'] * 100:.0f}%",
                    mastery
                ])
            
            if len(kp_data) > 1:
                kp_table = Table(kp_data, colWidths=[150, 80, 80, 80])
                kp_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), chinese_font),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('PADDING', (0, 0), (-1, -1), 6),
                ]))
                story.append(kp_table)
            
            story.append(Spacer(1, 20))
            
            # 薄弱点和建议
            story.append(Paragraph("三、学习建议", heading_style))
            
            weak_points = report_data.get("weak_points", [])
            if weak_points:
                story.append(Paragraph(
                    f"薄弱知识点：{', '.join(weak_points)}",
                    body_style
                ))
            
            for rec in report_data.get("recommendations", []):
                story.append(Paragraph(f"• {rec}", body_style))
            
            story.append(Spacer(1, 30))
            
            # 生成时间
            story.append(Paragraph(
                f"生成时间：{datetime.now().strftime('%Y年%m月%d日 %H:%M')}",
                body_style
            ))
            
            # 构建 PDF
            doc.build(story)
            
            return output_path
            
        except Exception as e:
            console.print(f"[red]PDF 生成失败: {e}[/red]")
            return None


# ============================================================================
# 导出函数
# ============================================================================
def create_interaction_engine() -> InteractionEngine:
    """创建交互引擎实例"""
    return InteractionEngine()


def session_to_dict(session: LearningSession) -> Dict:
    """将会话转换为字典（用于 session_state 存储）"""
    return {
        "session_id": session.session_id,
        "user_id": session.user_id,
        "start_time": session.start_time,
        "end_time": session.end_time,
        "course_topic": session.course_topic,
        "current_section_index": session.current_section_index,
        "current_video_position": session.current_video_position,
        "is_paused_for_quiz": session.is_paused_for_quiz,
        "quiz_attempts": [asdict(a) for a in session.quiz_attempts],
        "knowledge_progress": {
            k: asdict(v) for k, v in session.knowledge_progress.items()
        },
        "unlocked_sections": session.unlocked_sections
    }


def dict_to_session(data: Dict) -> LearningSession:
    """从字典恢复会话"""
    session = LearningSession(
        session_id=data["session_id"],
        user_id=data["user_id"],
        start_time=data["start_time"],
        end_time=data["end_time"],
        course_topic=data["course_topic"],
        current_section_index=data["current_section_index"],
        current_video_position=data["current_video_position"],
        is_paused_for_quiz=data["is_paused_for_quiz"],
        unlocked_sections=data["unlocked_sections"]
    )
    
    # 恢复答题记录
    for a in data.get("quiz_attempts", []):
        session.quiz_attempts.append(QuizAttempt(
            quiz_id=a["quiz_id"],
            knowledge_point=a["knowledge_point"],
            question=a["question"],
            user_answer=a["user_answer"],
            correct_answer=a["correct_answer"],
            result=AnswerResult(a["result"]),
            timestamp=a["timestamp"],
            time_spent_seconds=a.get("time_spent_seconds", 0),
            error_analysis=a.get("error_analysis", "")
        ))
    
    # 恢复知识点进度
    for k, v in data.get("knowledge_progress", {}).items():
        session.knowledge_progress[k] = KnowledgePointProgress(
            knowledge_point=v["knowledge_point"],
            total_attempts=v["total_attempts"],
            correct_count=v["correct_count"],
            consecutive_errors=v["consecutive_errors"],
            last_attempt_time=v["last_attempt_time"],
            total_watch_time_seconds=v.get("total_watch_time_seconds", 0),
            remediation_shown=v.get("remediation_shown", False),
            mastery_level=v.get("mastery_level", 0)
        )
    
    return session
