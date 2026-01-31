#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自适应反馈引擎 (Adaptive Feedback Engine)
=========================================

实现"以测促练，以练补学"的数据闭环：
- 获取实训表现：从 Nexus Learn AI 读取学员实训得分
- 诊断薄弱点：识别低于60分的环节，自动触发重学申请
- 动态更新课件：调用 content_generator 生成专项强化训练材料

作者: SmartCourseEngine Team
日期: 2026-02-01
"""

import os
import json
import hashlib
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

# Rich 美化输出
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

# ============================================================================
# 配置
# ============================================================================
NEXUS_API_URL = os.getenv("NEXUS_API_URL", "http://localhost:8001")
NEXUS_API_KEY = os.getenv("NEXUS_API_KEY", "")

# 阈值配置
PASS_THRESHOLD = 60           # 及格分数线
WEAKNESS_THRESHOLD = 60       # 薄弱点判定阈值
AUTO_RELEARN_TRIGGER = 3      # 连续低分次数触发自动重学


# ============================================================================
# 数据模型
# ============================================================================
class RelearningStatus(Enum):
    """重学申请状态"""
    PENDING = "pending"           # 待处理
    IN_PROGRESS = "in_progress"   # 进行中
    COMPLETED = "completed"       # 已完成
    CANCELLED = "cancelled"       # 已取消


@dataclass
class StepScore:
    """步骤得分"""
    step_id: str
    step_name: str
    score: float                  # 0-100
    max_score: float = 100.0
    criteria_scores: Dict[str, float] = field(default_factory=dict)
    feedback: str = ""
    
    @property
    def percentage(self) -> float:
        """百分比得分"""
        return (self.score / self.max_score * 100) if self.max_score > 0 else 0
    
    @property
    def is_passing(self) -> bool:
        """是否及格"""
        return self.percentage >= PASS_THRESHOLD


@dataclass
class TraineePerformance:
    """学员实训表现"""
    trainee_id: str
    assessment_id: str
    assessment_title: str
    course_id: str
    step_scores: List[StepScore]
    total_score: float
    max_score: float = 100.0
    completed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    time_spent_minutes: float = 0
    attempt_number: int = 1
    
    @property
    def percentage(self) -> float:
        """总分百分比"""
        return (self.total_score / self.max_score * 100) if self.max_score > 0 else 0
    
    @property
    def is_passing(self) -> bool:
        """是否及格"""
        return self.percentage >= PASS_THRESHOLD
    
    def get_weak_steps(self, threshold: float = WEAKNESS_THRESHOLD) -> List[StepScore]:
        """获取薄弱环节（低于阈值的步骤）"""
        return [step for step in self.step_scores if step.percentage < threshold]
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "trainee_id": self.trainee_id,
            "assessment_id": self.assessment_id,
            "assessment_title": self.assessment_title,
            "course_id": self.course_id,
            "step_scores": [asdict(s) for s in self.step_scores],
            "total_score": self.total_score,
            "max_score": self.max_score,
            "percentage": self.percentage,
            "is_passing": self.is_passing,
            "completed_at": self.completed_at,
            "time_spent_minutes": self.time_spent_minutes,
            "attempt_number": self.attempt_number
        }


@dataclass
class WeakPointDiagnosis:
    """薄弱点诊断"""
    step_id: str
    step_name: str
    average_score: float
    attempt_count: int
    problem_description: str
    recommended_focus: List[str]
    severity: str = "moderate"    # mild, moderate, severe
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class RelearningRequest:
    """重学申请"""
    request_id: str
    trainee_id: str
    course_id: str
    assessment_id: str
    weak_points: List[WeakPointDiagnosis]
    status: RelearningStatus = RelearningStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str = ""
    generated_materials: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "request_id": self.request_id,
            "trainee_id": self.trainee_id,
            "course_id": self.course_id,
            "assessment_id": self.assessment_id,
            "weak_points": [wp.to_dict() for wp in self.weak_points],
            "status": self.status.value,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "generated_materials": self.generated_materials
        }


# ============================================================================
# 自适应反馈引擎
# ============================================================================
class AdaptiveFeedbackEngine:
    """
    自适应反馈引擎
    
    实现"以测促练，以练补学"的数据闭环。
    """
    
    def __init__(
        self,
        nexus_api_url: str = NEXUS_API_URL,
        nexus_api_key: str = NEXUS_API_KEY,
        output_dir: str = None
    ):
        """
        初始化自适应反馈引擎
        
        Args:
            nexus_api_url: Nexus Learn AI API 地址
            nexus_api_key: API 密钥
            output_dir: 输出目录
        """
        self.nexus_api_url = nexus_api_url.rstrip("/")
        self.nexus_api_key = nexus_api_key
        
        # 输出目录
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path(__file__).parent / "generated_courseware" / "reinforcement"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 缓存
        self._performance_cache: Dict[str, List[TraineePerformance]] = {}
        self._relearning_requests: Dict[str, RelearningRequest] = {}
        
        # 初始化依赖模块
        self.content_generator = None
        self.video_creator = None
        self.knowledge_manager = None
        
        self._init_dependencies()
    
    def _init_dependencies(self):
        """初始化依赖模块"""
        try:
            from content_generator import ContentGenerator
            self.content_generator = ContentGenerator()
            console.print("[green]✓[/green] 内容生成器初始化成功")
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] 内容生成器初始化失败: {e}")
        
        try:
            from video_creator import HeyGenVideoCreator
            self.video_creator = HeyGenVideoCreator()
            console.print("[green]✓[/green] 视频创建器初始化成功")
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] 视频创建器初始化失败: {e}")
        
        try:
            from knowledge_manager import KnowledgeManager
            base_dir = Path(__file__).parent
            self.knowledge_manager = KnowledgeManager(
                db_path=str(base_dir / "chroma_db")
            )
            console.print("[green]✓[/green] 知识管理器初始化成功")
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] 知识管理器初始化失败: {e}")
    
    def _get_headers(self) -> Dict:
        """获取 API 请求头"""
        headers = {"Content-Type": "application/json"}
        if self.nexus_api_key:
            headers["Authorization"] = f"Bearer {self.nexus_api_key}"
        return headers
    
    # ========================================================================
    # 获取实训表现
    # ========================================================================
    def fetch_trainee_scores(
        self,
        trainee_id: str,
        course_id: str = None,
        limit: int = 10
    ) -> List[TraineePerformance]:
        """
        从 Nexus Learn AI 获取学员实训得分
        
        Args:
            trainee_id: 学员ID
            course_id: 课程ID（可选）
            limit: 返回数量限制
            
        Returns:
            实训表现列表
        """
        console.print(f"[blue]→[/blue] 获取学员 {trainee_id} 的实训得分...")
        
        try:
            params = {"trainee_id": trainee_id, "limit": limit}
            if course_id:
                params["course_id"] = course_id
            
            response = requests.get(
                f"{self.nexus_api_url}/api/training-scores",
                headers=self._get_headers(),
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                performances = self._parse_performances(data.get("scores", []))
                console.print(f"[green]✓[/green] 获取到 {len(performances)} 条实训记录")
                return performances
            else:
                console.print(f"[yellow]⚠[/yellow] API 响应异常: {response.status_code}")
                return []
                
        except requests.exceptions.RequestException as e:
            console.print(f"[yellow]⚠[/yellow] 无法连接 Nexus API: {e}")
            console.print("[dim]将使用模拟数据进行演示[/dim]")
            return self._get_mock_performances(trainee_id, course_id)
    
    def _parse_performances(self, scores_data: List[Dict]) -> List[TraineePerformance]:
        """解析 API 返回的得分数据"""
        performances = []
        
        for score in scores_data:
            step_scores = []
            for step in score.get("step_scores", []):
                step_scores.append(StepScore(
                    step_id=step.get("step_id", ""),
                    step_name=step.get("step_name", ""),
                    score=step.get("score", 0),
                    max_score=step.get("max_score", 100),
                    criteria_scores=step.get("criteria_scores", {}),
                    feedback=step.get("feedback", "")
                ))
            
            performances.append(TraineePerformance(
                trainee_id=score.get("trainee_id", ""),
                assessment_id=score.get("assessment_id", ""),
                assessment_title=score.get("assessment_title", ""),
                course_id=score.get("course_id", ""),
                step_scores=step_scores,
                total_score=score.get("total_score", 0),
                max_score=score.get("max_score", 100),
                completed_at=score.get("completed_at", ""),
                time_spent_minutes=score.get("time_spent_minutes", 0),
                attempt_number=score.get("attempt_number", 1)
            ))
        
        return performances
    
    def _get_mock_performances(
        self,
        trainee_id: str,
        course_id: str = None
    ) -> List[TraineePerformance]:
        """生成模拟实训表现数据（用于演示）"""
        # 模拟场景：紧急包扎环节得分较低
        mock_steps = [
            StepScore(
                step_id="step_1",
                step_name="确认伤情",
                score=85,
                feedback="观察准确，判断正确"
            ),
            StepScore(
                step_id="step_2",
                step_name="准备材料",
                score=78,
                feedback="材料准备基本齐全"
            ),
            StepScore(
                step_id="step_3",
                step_name="紧急包扎",
                score=48,  # 低于60分，需要重学
                feedback="包扎手法不规范，力度控制不当"
            ),
            StepScore(
                step_id="step_4",
                step_name="固定检查",
                score=55,  # 低于60分
                feedback="固定不够牢固"
            ),
            StepScore(
                step_id="step_5",
                step_name="后续观察",
                score=72,
                feedback="观察项目基本完整"
            )
        ]
        
        total_score = sum(s.score for s in mock_steps) / len(mock_steps)
        
        return [TraineePerformance(
            trainee_id=trainee_id,
            assessment_id="assessment_mock_001",
            assessment_title="婴幼儿急救操作考核",
            course_id=course_id or "childcare_first_aid",
            step_scores=mock_steps,
            total_score=total_score,
            time_spent_minutes=18.5,
            attempt_number=1
        )]
    
    # ========================================================================
    # 诊断薄弱点
    # ========================================================================
    def diagnose_weak_points(
        self,
        performances: List[TraineePerformance],
        threshold: float = WEAKNESS_THRESHOLD
    ) -> List[WeakPointDiagnosis]:
        """
        诊断薄弱点
        
        Args:
            performances: 实训表现列表
            threshold: 薄弱点判定阈值
            
        Returns:
            薄弱点诊断列表
        """
        console.print("[blue]→[/blue] 分析薄弱环节...")
        
        # 统计每个步骤的得分情况
        step_stats: Dict[str, Dict] = {}
        
        for perf in performances:
            for step in perf.step_scores:
                if step.step_id not in step_stats:
                    step_stats[step.step_id] = {
                        "step_name": step.step_name,
                        "scores": [],
                        "feedbacks": []
                    }
                step_stats[step.step_id]["scores"].append(step.percentage)
                if step.feedback:
                    step_stats[step.step_id]["feedbacks"].append(step.feedback)
        
        # 识别薄弱点
        weak_points = []
        
        for step_id, stats in step_stats.items():
            avg_score = sum(stats["scores"]) / len(stats["scores"])
            
            if avg_score < threshold:
                # 确定严重程度
                if avg_score < 40:
                    severity = "severe"
                elif avg_score < 55:
                    severity = "moderate"
                else:
                    severity = "mild"
                
                # 生成问题描述
                problem_desc = self._generate_problem_description(
                    stats["step_name"],
                    avg_score,
                    stats["feedbacks"]
                )
                
                # 生成建议
                focus_areas = self._generate_focus_areas(
                    stats["step_name"],
                    stats["feedbacks"]
                )
                
                weak_points.append(WeakPointDiagnosis(
                    step_id=step_id,
                    step_name=stats["step_name"],
                    average_score=round(avg_score, 1),
                    attempt_count=len(stats["scores"]),
                    problem_description=problem_desc,
                    recommended_focus=focus_areas,
                    severity=severity
                ))
        
        # 按严重程度排序
        severity_order = {"severe": 0, "moderate": 1, "mild": 2}
        weak_points.sort(key=lambda x: (severity_order.get(x.severity, 3), x.average_score))
        
        console.print(f"[green]✓[/green] 发现 {len(weak_points)} 个薄弱环节")
        
        # 显示诊断结果
        self._display_diagnosis(weak_points)
        
        return weak_points
    
    def _generate_problem_description(
        self,
        step_name: str,
        avg_score: float,
        feedbacks: List[str]
    ) -> str:
        """生成问题描述"""
        if avg_score < 40:
            level = "严重不足"
        elif avg_score < 55:
            level = "有待提高"
        else:
            level = "略有欠缺"
        
        desc = f"「{step_name}」环节平均得分 {avg_score:.1f} 分，{level}。"
        
        if feedbacks:
            # 提取常见问题
            common_issues = list(set(feedbacks))[:3]
            desc += f"主要问题：{'；'.join(common_issues)}"
        
        return desc
    
    def _generate_focus_areas(
        self,
        step_name: str,
        feedbacks: List[str]
    ) -> List[str]:
        """生成建议关注领域"""
        focus = []
        
        # 基于步骤名称生成通用建议
        if "包扎" in step_name:
            focus.extend(["绷带缠绕手法", "力度控制", "固定方式"])
        elif "急救" in step_name:
            focus.extend(["操作规范", "时间控制", "安全意识"])
        elif "检查" in step_name or "观察" in step_name:
            focus.extend(["检查项目完整性", "观察方法", "记录规范"])
        elif "准备" in step_name:
            focus.extend(["物料清单", "工具摆放", "环境准备"])
        else:
            focus.extend(["操作规范", "注意事项", "关键要点"])
        
        # 基于反馈提取关键词
        for fb in feedbacks:
            if "力度" in fb:
                if "力度控制" not in focus:
                    focus.append("力度控制")
            if "手法" in fb or "手势" in fb:
                if "操作手法" not in focus:
                    focus.append("操作手法")
            if "固定" in fb:
                if "固定技术" not in focus:
                    focus.append("固定技术")
        
        return focus[:5]  # 最多5项
    
    def _display_diagnosis(self, weak_points: List[WeakPointDiagnosis]):
        """显示诊断结果"""
        if not weak_points:
            console.print("[green]✓[/green] 未发现明显薄弱环节")
            return
        
        table = Table(title="📊 薄弱点诊断结果")
        table.add_column("环节", style="cyan")
        table.add_column("平均分", justify="center")
        table.add_column("严重程度", justify="center")
        table.add_column("问题描述")
        
        severity_style = {
            "severe": "[red]严重[/red]",
            "moderate": "[yellow]中等[/yellow]",
            "mild": "[blue]轻微[/blue]"
        }
        
        for wp in weak_points:
            table.add_row(
                wp.step_name,
                f"{wp.average_score:.1f}",
                severity_style.get(wp.severity, wp.severity),
                wp.problem_description[:50] + "..." if len(wp.problem_description) > 50 else wp.problem_description
            )
        
        console.print(table)
    
    # ========================================================================
    # 创建重学申请
    # ========================================================================
    def create_relearning_request(
        self,
        trainee_id: str,
        course_id: str,
        assessment_id: str,
        weak_points: List[WeakPointDiagnosis]
    ) -> Optional[RelearningRequest]:
        """
        创建重学申请
        
        Args:
            trainee_id: 学员ID
            course_id: 课程ID
            assessment_id: 评估ID
            weak_points: 薄弱点列表
            
        Returns:
            重学申请对象
        """
        if not weak_points:
            console.print("[yellow]⚠[/yellow] 没有需要重学的薄弱点")
            return None
        
        console.print(Panel(
            f"为学员 [bold]{trainee_id}[/bold] 创建重学申请\n"
            f"薄弱环节数: {len(weak_points)}",
            title="📝 重学申请",
            style="yellow"
        ))
        
        # 生成请求ID
        request_id = hashlib.md5(
            f"{trainee_id}_{assessment_id}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        request = RelearningRequest(
            request_id=request_id,
            trainee_id=trainee_id,
            course_id=course_id,
            assessment_id=assessment_id,
            weak_points=weak_points,
            status=RelearningStatus.PENDING
        )
        
        # 缓存请求
        self._relearning_requests[request_id] = request
        
        # 尝试保存到 Nexus
        self._save_relearning_request(request)
        
        console.print(f"[green]✓[/green] 重学申请已创建: {request_id}")
        
        return request
    
    def _save_relearning_request(self, request: RelearningRequest):
        """保存重学申请到 Nexus 或本地"""
        try:
            response = requests.post(
                f"{self.nexus_api_url}/api/relearning-requests",
                headers=self._get_headers(),
                json=request.to_dict(),
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                console.print("[green]✓[/green] 重学申请已同步到 Nexus")
            else:
                self._save_request_local(request)
                
        except requests.exceptions.RequestException:
            self._save_request_local(request)
    
    def _save_request_local(self, request: RelearningRequest):
        """保存重学申请到本地"""
        filepath = self.output_dir / f"request_{request.request_id}.json"
        filepath.write_text(
            json.dumps(request.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        console.print(f"[dim]重学申请已保存到本地: {filepath}[/dim]")
    
    # ========================================================================
    # 生成专项强化材料
    # ========================================================================
    def generate_reinforcement_material(
        self,
        request: RelearningRequest,
        generate_video: bool = False
    ) -> Dict[str, Any]:
        """
        生成专项强化训练材料
        
        Args:
            request: 重学申请
            generate_video: 是否生成视频
            
        Returns:
            生成的材料信息
        """
        console.print(Panel(
            f"为 {len(request.weak_points)} 个薄弱环节生成专项强化材料",
            title="📚 专项强化训练",
            style="blue"
        ))
        
        # 更新状态
        request.status = RelearningStatus.IN_PROGRESS
        
        results = {
            "request_id": request.request_id,
            "materials": [],
            "videos": [],
            "success": True,
            "errors": []
        }
        
        for wp in request.weak_points:
            console.print(f"\n[blue]→[/blue] 处理薄弱环节: {wp.step_name}")
            
            # 1. 从知识库检索相关内容
            related_knowledge = self._retrieve_related_knowledge(wp)
            
            # 2. 生成专项强化教案
            material = self._generate_reinforcement_courseware(wp, related_knowledge)
            
            if material:
                results["materials"].append(material)
                request.generated_materials.append(material["filepath"])
                
                # 3. 可选：生成补充视频
                if generate_video and self.video_creator:
                    video_result = self._generate_reinforcement_video(
                        wp, material
                    )
                    if video_result:
                        results["videos"].append(video_result)
            else:
                results["errors"].append(f"无法为「{wp.step_name}」生成材料")
        
        # 更新状态
        if results["materials"]:
            request.status = RelearningStatus.COMPLETED
            request.completed_at = datetime.now().isoformat()
        else:
            results["success"] = False
        
        # 显示结果
        self._display_generation_results(results)
        
        return results
    
    def _retrieve_related_knowledge(
        self,
        weak_point: WeakPointDiagnosis
    ) -> List[Dict]:
        """检索与薄弱点相关的知识"""
        if not self.knowledge_manager:
            return []
        
        query = f"{weak_point.step_name} {' '.join(weak_point.recommended_focus)}"
        
        try:
            results = self.knowledge_manager.query_knowledge(query, top_k=5)
            console.print(f"  [dim]检索到 {len(results)} 个相关知识点[/dim]")
            return results
        except Exception as e:
            console.print(f"  [yellow]⚠[/yellow] 知识检索失败: {e}")
            return []
    
    def _generate_reinforcement_courseware(
        self,
        weak_point: WeakPointDiagnosis,
        related_knowledge: List[Dict]
    ) -> Optional[Dict]:
        """生成专项强化教案"""
        # 构建主题
        topic = f"专项强化训练：{weak_point.step_name}"
        
        # 构建知识上下文
        knowledge_context = ""
        for kp in related_knowledge:
            knowledge_context += f"\n{kp.get('content', '')[:500]}"
        
        # 添加薄弱点信息
        focus_info = f"""
【需要强化的要点】
- 问题描述：{weak_point.problem_description}
- 建议关注：{', '.join(weak_point.recommended_focus)}
- 严重程度：{weak_point.severity}
"""
        
        try:
            if self.content_generator:
                # 使用内容生成器生成教案
                courseware = self.content_generator.generate_courseware(topic)
                
                # 保存教案
                filepath = self._save_courseware(weak_point, courseware)
                
                return {
                    "weak_point": weak_point.step_name,
                    "topic": topic,
                    "filepath": filepath,
                    "sections": len(courseware.get("scripts", [])),
                    "quizzes": len(courseware.get("quizzes", []))
                }
            else:
                # 生成基础模板
                return self._generate_template_material(weak_point, knowledge_context)
                
        except Exception as e:
            console.print(f"  [red]✗[/red] 教案生成失败: {e}")
            return None
    
    def _generate_template_material(
        self,
        weak_point: WeakPointDiagnosis,
        knowledge_context: str
    ) -> Optional[Dict]:
        """生成模板材料（当内容生成器不可用时）"""
        template = {
            "title": f"专项强化训练：{weak_point.step_name}",
            "generated_at": datetime.now().isoformat(),
            "weak_point": weak_point.to_dict(),
            "sections": [
                {
                    "title": "问题分析",
                    "content": weak_point.problem_description
                },
                {
                    "title": "重点强化",
                    "content": "、".join(weak_point.recommended_focus)
                },
                {
                    "title": "知识要点",
                    "content": knowledge_context[:1000] if knowledge_context else "请参阅相关培训材料"
                },
                {
                    "title": "练习建议",
                    "content": f"建议针对「{weak_point.step_name}」进行至少3次完整练习，注意纠正上述问题。"
                }
            ]
        }
        
        # 保存
        filename = f"reinforcement_{weak_point.step_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.output_dir / filename
        filepath.write_text(
            json.dumps(template, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        console.print(f"  [green]✓[/green] 已生成模板材料: {filepath.name}")
        
        return {
            "weak_point": weak_point.step_name,
            "topic": template["title"],
            "filepath": str(filepath),
            "sections": len(template["sections"]),
            "quizzes": 0
        }
    
    def _save_courseware(
        self,
        weak_point: WeakPointDiagnosis,
        courseware: Dict
    ) -> str:
        """保存生成的教案"""
        filename = f"reinforcement_{weak_point.step_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.output_dir / filename
        
        # 添加元数据
        courseware["weak_point"] = weak_point.to_dict()
        courseware["material_type"] = "reinforcement"
        
        filepath.write_text(
            json.dumps(courseware, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        console.print(f"  [green]✓[/green] 已保存教案: {filepath.name}")
        
        # 同时导出 Word 文档
        if self.content_generator:
            try:
                word_path = self.content_generator.export_to_word(
                    courseware,
                    str(self.output_dir)
                )
                console.print(f"  [green]✓[/green] 已导出 Word: {Path(word_path).name}")
            except Exception as e:
                console.print(f"  [yellow]⚠[/yellow] Word 导出失败: {e}")
        
        return str(filepath)
    
    def _generate_reinforcement_video(
        self,
        weak_point: WeakPointDiagnosis,
        material: Dict
    ) -> Optional[Dict]:
        """生成专项强化视频"""
        if not self.video_creator:
            return None
        
        console.print(f"  [blue]→[/blue] 生成补充视频...")
        
        # 构建视频脚本
        script = f"""
欢迎来到专项强化训练。今天我们将针对「{weak_point.step_name}」环节进行重点讲解。

根据您的实训表现，需要特别注意以下几点：
{', '.join(weak_point.recommended_focus)}

让我们开始详细学习...
"""
        
        try:
            # 创建视频任务
            video_id = self.video_creator.create_video(
                text=script[:1500],  # 限制长度
                title=f"专项强化_{weak_point.step_name}"
            )
            
            if video_id:
                console.print(f"  [green]✓[/green] 视频任务已创建: {video_id}")
                return {
                    "weak_point": weak_point.step_name,
                    "video_id": video_id,
                    "status": "processing"
                }
            else:
                console.print(f"  [yellow]⚠[/yellow] 视频创建失败")
                return None
                
        except Exception as e:
            console.print(f"  [red]✗[/red] 视频生成失败: {e}")
            return None
    
    def _display_generation_results(self, results: Dict):
        """显示生成结果"""
        table = Table(title="📦 生成结果汇总")
        table.add_column("项目", style="cyan")
        table.add_column("数量", justify="center")
        table.add_column("状态")
        
        table.add_row(
            "专项教案",
            str(len(results["materials"])),
            "[green]成功[/green]" if results["materials"] else "[red]失败[/red]"
        )
        
        table.add_row(
            "补充视频",
            str(len(results["videos"])),
            "[green]成功[/green]" if results["videos"] else "[dim]未生成[/dim]"
        )
        
        if results["errors"]:
            table.add_row(
                "错误",
                str(len(results["errors"])),
                "[red]有错误[/red]"
            )
        
        console.print(table)
    
    # ========================================================================
    # 完整闭环执行
    # ========================================================================
    def run_feedback_loop(
        self,
        trainee_id: str,
        course_id: str = None,
        generate_video: bool = False
    ) -> Dict[str, Any]:
        """
        执行完整的自适应反馈闭环
        
        Args:
            trainee_id: 学员ID
            course_id: 课程ID
            generate_video: 是否生成视频
            
        Returns:
            执行结果
        """
        console.print(Panel(
            f"🔄 启动自适应反馈闭环\n"
            f"学员: {trainee_id}\n"
            f"课程: {course_id or '全部'}",
            title="Adaptive Feedback Engine",
            style="green"
        ))
        
        result = {
            "trainee_id": trainee_id,
            "course_id": course_id,
            "performances": [],
            "weak_points": [],
            "relearning_request": None,
            "generated_materials": [],
            "success": True
        }
        
        # 1. 获取实训表现
        performances = self.fetch_trainee_scores(trainee_id, course_id)
        result["performances"] = [p.to_dict() for p in performances]
        
        if not performances:
            console.print("[yellow]⚠[/yellow] 未获取到实训记录")
            result["success"] = False
            return result
        
        # 2. 诊断薄弱点
        weak_points = self.diagnose_weak_points(performances)
        result["weak_points"] = [wp.to_dict() for wp in weak_points]
        
        if not weak_points:
            console.print("[green]✓[/green] 无需生成补充材料")
            return result
        
        # 3. 创建重学申请
        assessment_id = performances[0].assessment_id if performances else "unknown"
        request = self.create_relearning_request(
            trainee_id=trainee_id,
            course_id=course_id or "default",
            assessment_id=assessment_id,
            weak_points=weak_points
        )
        
        if request:
            result["relearning_request"] = request.to_dict()
            
            # 4. 生成专项强化材料
            gen_result = self.generate_reinforcement_material(
                request,
                generate_video=generate_video
            )
            result["generated_materials"] = gen_result.get("materials", [])
        
        console.print(Panel(
            f"✅ 自适应反馈闭环完成\n"
            f"发现薄弱点: {len(weak_points)}\n"
            f"生成材料: {len(result['generated_materials'])}",
            style="green"
        ))
        
        return result


# ============================================================================
# 示例数据
# ============================================================================
BANDAGING_EXAMPLE = {
    "trainee_id": "trainee_demo_001",
    "course_id": "childcare_first_aid",
    "assessment_title": "婴幼儿急救操作考核",
    "steps": [
        {"step_name": "确认伤情", "score": 85},
        {"step_name": "准备材料", "score": 78},
        {"step_name": "紧急包扎", "score": 48},  # 薄弱点
        {"step_name": "固定检查", "score": 55},  # 薄弱点
        {"step_name": "后续观察", "score": 72}
    ]
}


# ============================================================================
# 主函数
# ============================================================================
def main():
    """演示自适应反馈闭环"""
    console.print(Panel(
        "自适应反馈引擎演示\n"
        "实现'以测促练，以练补学'的数据闭环",
        title="🔄 Adaptive Feedback Engine",
        style="bold blue"
    ))
    
    # 初始化引擎
    engine = AdaptiveFeedbackEngine()
    
    # 运行完整闭环
    result = engine.run_feedback_loop(
        trainee_id=BANDAGING_EXAMPLE["trainee_id"],
        course_id=BANDAGING_EXAMPLE["course_id"],
        generate_video=False  # 演示时不生成视频
    )
    
    # 输出结果摘要
    console.print("\n[bold]执行结果:[/bold]")
    console.print(f"  薄弱点数量: {len(result['weak_points'])}")
    console.print(f"  生成材料数: {len(result['generated_materials'])}")
    console.print(f"  执行状态: {'成功' if result['success'] else '失败'}")
    
    return result


if __name__ == "__main__":
    main()
