#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nexus Mapper - 智课灵境集成模块
==============================

实现理论知识与实操考核的智能映射：
- 提取操作要领：读取"实操类"知识点，转化为结构化评分指标
- 生成评价量表：自动生成评分项、权重和判别标准
- 对接接口：将评分标准写入 Nexus Learn AI 数据库

作者: SmartCourseEngine Team
日期: 2026-01-31
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
import re

# Rich 美化输出
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

# ============================================================================
# API 配置
# ============================================================================
API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
BASE_URL = os.getenv("API_BASE_URL", "https://api.deepseek.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-chat")

# Nexus Learn AI 后端配置
NEXUS_API_URL = os.getenv("NEXUS_API_URL", "http://localhost:8001")
NEXUS_API_KEY = os.getenv("NEXUS_API_KEY", "")


# ============================================================================
# 数据模型
# ============================================================================
class KnowledgeType(Enum):
    """知识点类型枚举"""
    THEORETICAL = "theoretical"     # 理论知识
    PRACTICAL = "practical"         # 实操类知识
    PROCEDURAL = "procedural"       # 流程性知识
    MIXED = "mixed"                 # 混合类型


class AssessmentLevel(Enum):
    """评估等级"""
    CRITICAL = "critical"           # 关键项（安全相关）
    MAJOR = "major"                 # 主要项
    MINOR = "minor"                 # 次要项


@dataclass
class AssessmentCriterion:
    """评分标准项"""
    criterion_id: str               # 标准唯一ID
    name: str                       # 评分项名称
    description: str                # 详细描述
    weight: float                   # 权重 (0-1)
    level: AssessmentLevel          # 评估等级
    pass_threshold: float           # 通过阈值 (0-1)
    scoring_rubric: Dict[str, Any]  # 评分细则
    detection_hints: List[str]      # 视觉检测提示（用于 CV 模块）
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "criterion_id": self.criterion_id,
            "name": self.name,
            "description": self.description,
            "weight": self.weight,
            "level": self.level.value,
            "pass_threshold": self.pass_threshold,
            "scoring_rubric": self.scoring_rubric,
            "detection_hints": self.detection_hints
        }


@dataclass
class SOPStep:
    """SOP 步骤"""
    step_id: str                    # 步骤ID
    step_number: int                # 步骤序号
    action: str                     # 操作描述
    expected_duration: float        # 预期时长（秒）
    criteria: List[AssessmentCriterion]  # 该步骤的评分标准
    prerequisites: List[str]        # 前置步骤ID
    tools_required: List[str]       # 所需工具
    safety_notes: List[str]         # 安全注意事项


@dataclass
class PracticalAssessment:
    """实操评估方案"""
    assessment_id: str              # 评估方案ID
    title: str                      # 评估标题
    description: str                # 评估描述
    course_id: str                  # 关联课程ID
    knowledge_point_id: str         # 关联知识点ID
    knowledge_type: KnowledgeType   # 知识点类型
    total_score: float              # 总分
    pass_score: float               # 及格分
    time_limit: int                 # 时间限制（分钟）
    sop_steps: List[SOPStep]        # SOP 步骤列表
    criteria: List[AssessmentCriterion]  # 总体评分标准
    created_at: str                 # 创建时间
    updated_at: str                 # 更新时间
    
    def to_json(self) -> str:
        """导出为 JSON"""
        data = {
            "assessment_id": self.assessment_id,
            "title": self.title,
            "description": self.description,
            "course_id": self.course_id,
            "knowledge_point_id": self.knowledge_point_id,
            "knowledge_type": self.knowledge_type.value,
            "total_score": self.total_score,
            "pass_score": self.pass_score,
            "time_limit": self.time_limit,
            "sop_steps": [
                {
                    "step_id": step.step_id,
                    "step_number": step.step_number,
                    "action": step.action,
                    "expected_duration": step.expected_duration,
                    "criteria": [c.to_dict() for c in step.criteria],
                    "prerequisites": step.prerequisites,
                    "tools_required": step.tools_required,
                    "safety_notes": step.safety_notes
                }
                for step in self.sop_steps
            ],
            "criteria": [c.to_dict() for c in self.criteria],
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
        return json.dumps(data, ensure_ascii=False, indent=2)


# ============================================================================
# Prompt 模板
# ============================================================================
CLASSIFY_KNOWLEDGE_PROMPT = """你是一位教育评估专家。请分析以下知识点内容，判断其类型并提取关键信息。

【知识点内容】
{content}

请以 JSON 格式返回以下信息：
{{
    "knowledge_type": "theoretical/practical/procedural/mixed",
    "is_practical": true/false,
    "practical_elements": ["操作要素1", "操作要素2", ...],
    "safety_considerations": ["安全注意事项1", ...],
    "tools_or_equipment": ["工具或设备1", ...],
    "estimated_practice_time_minutes": 数字,
    "complexity_level": "basic/intermediate/advanced",
    "key_competencies": ["核心能力1", "核心能力2", ...]
}}

仅返回 JSON，不要添加任何其他文字。"""


GENERATE_RUBRIC_PROMPT = """你是一位职业培训评估专家。请为以下实操知识点生成详细的评分量表。

【知识点标题】{title}
【知识点内容】
{content}

【实操要素】
{practical_elements}

【工具/设备】
{tools}

请生成一份包含评分标准的 JSON 评分量表：
{{
    "sop_steps": [
        {{
            "step_number": 1,
            "action": "操作步骤描述",
            "expected_duration_seconds": 60,
            "tools_required": ["工具1"],
            "safety_notes": ["安全提示"],
            "criteria": [
                {{
                    "name": "评分项名称",
                    "description": "详细评分描述",
                    "weight": 0.3,
                    "level": "critical/major/minor",
                    "pass_threshold": 0.8,
                    "scoring_rubric": {{
                        "excellent": "优秀表现描述（得分90-100%）",
                        "good": "良好表现描述（得分70-89%）",
                        "acceptable": "合格表现描述（得分60-69%）",
                        "poor": "不合格表现描述（得分<60%）"
                    }},
                    "detection_hints": ["视觉识别提示（用于AI视觉评估）"]
                }}
            ]
        }}
    ],
    "overall_criteria": [
        {{
            "name": "总体评分项",
            "description": "描述",
            "weight": 0.2,
            "level": "major",
            "pass_threshold": 0.6,
            "scoring_rubric": {{}},
            "detection_hints": []
        }}
    ],
    "total_score": 100,
    "pass_score": 60,
    "time_limit_minutes": 30
}}

要求：
1. 所有权重之和必须为 1.0
2. critical 级别的评分项权重应较高
3. 针对安全相关的操作必须设置为 critical 级别
4. detection_hints 要具体，便于视觉AI识别判断

仅返回 JSON，不要添加任何其他文字。"""


# ============================================================================
# Knowledge_to_Skill_Bridge 类
# ============================================================================
class Knowledge_to_Skill_Bridge:
    """
    知识点与实操技能映射桥梁
    
    实现理论知识点与实操考核点的一一对应关系管理。
    """
    
    def __init__(
        self,
        api_key: str = API_KEY,
        base_url: str = BASE_URL,
        model_name: str = MODEL_NAME
    ):
        """
        初始化映射桥梁
        
        Args:
            api_key: LLM API 密钥
            base_url: API 基础 URL
            model_name: 模型名称
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.llm = None
        self.knowledge_manager = None
        
        # 映射缓存
        self._mapping_cache: Dict[str, PracticalAssessment] = {}
        
        self._init_llm()
        self._init_knowledge_manager()
    
    def _init_llm(self):
        """初始化大语言模型"""
        if not self.api_key:
            console.print("[yellow]⚠[/yellow] 未配置 API Key，评分量表生成功能将受限")
            return
        
        try:
            from langchain_openai import ChatOpenAI
            
            self.llm = ChatOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model_name,
                temperature=0.3  # 低温度以保持一致性
            )
            console.print("[green]✓[/green] LLM 初始化成功")
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
            console.print("[green]✓[/green] 知识管理器连接成功")
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] 知识管理器连接失败: {e}")
    
    def _call_llm(self, prompt: str) -> Optional[str]:
        """调用 LLM"""
        if not self.llm:
            return None
        
        try:
            response = self.llm.invoke(prompt)
            return response.content.strip()
        except Exception as e:
            console.print(f"[red]LLM 调用失败: {e}[/red]")
            return None
    
    def _parse_json(self, text: str) -> Optional[Dict]:
        """安全解析 JSON"""
        if not text:
            return None
        
        try:
            # 清理可能的 markdown 代码块
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1])
            
            return json.loads(text)
        except json.JSONDecodeError:
            console.print("[yellow]⚠[/yellow] JSON 解析失败")
            return None
    
    def classify_knowledge_point(
        self,
        content: str
    ) -> Tuple[KnowledgeType, Dict]:
        """
        对知识点进行分类
        
        Args:
            content: 知识点内容
            
        Returns:
            (知识点类型, 分析结果字典)
        """
        prompt = CLASSIFY_KNOWLEDGE_PROMPT.format(content=content[:2000])
        response = self._call_llm(prompt)
        
        if not response:
            # 使用启发式规则进行分类
            return self._heuristic_classification(content)
        
        analysis = self._parse_json(response)
        
        if not analysis:
            return self._heuristic_classification(content)
        
        # 确定知识点类型
        type_map = {
            "theoretical": KnowledgeType.THEORETICAL,
            "practical": KnowledgeType.PRACTICAL,
            "procedural": KnowledgeType.PROCEDURAL,
            "mixed": KnowledgeType.MIXED
        }
        
        knowledge_type = type_map.get(
            analysis.get("knowledge_type", "theoretical"),
            KnowledgeType.THEORETICAL
        )
        
        return knowledge_type, analysis
    
    def _heuristic_classification(self, content: str) -> Tuple[KnowledgeType, Dict]:
        """使用启发式规则进行知识点分类"""
        practical_keywords = [
            "操作", "实操", "步骤", "流程", "按压", "手法", "姿势",
            "急救", "心肺复苏", "CPR", "包扎", "消毒", "注射",
            "培训", "演练", "考核", "实训", "实践"
        ]
        
        procedural_keywords = [
            "第一步", "第二步", "首先", "然后", "接下来", "最后",
            "1.", "2.", "3.", "步骤一", "步骤二"
        ]
        
        content_lower = content.lower()
        
        practical_score = sum(1 for kw in practical_keywords if kw in content)
        procedural_score = sum(1 for kw in procedural_keywords if kw in content)
        
        if practical_score >= 3:
            knowledge_type = KnowledgeType.PRACTICAL
        elif procedural_score >= 2:
            knowledge_type = KnowledgeType.PROCEDURAL
        elif practical_score >= 1 and procedural_score >= 1:
            knowledge_type = KnowledgeType.MIXED
        else:
            knowledge_type = KnowledgeType.THEORETICAL
        
        return knowledge_type, {
            "is_practical": knowledge_type in [
                KnowledgeType.PRACTICAL, 
                KnowledgeType.PROCEDURAL,
                KnowledgeType.MIXED
            ],
            "practical_elements": [],
            "safety_considerations": [],
            "tools_or_equipment": [],
            "estimated_practice_time_minutes": 30,
            "complexity_level": "intermediate",
            "key_competencies": []
        }
    
    def _generate_default_rubric(
        self,
        title: str,
        content: str,
        analysis: Dict
    ) -> Dict:
        """
        生成默认评分量表模板
        
        当 LLM 不可用时，基于知识点分析结果生成标准化评分量表。
        
        Args:
            title: 知识点标题
            content: 知识点内容
            analysis: 分析结果
            
        Returns:
            评分量表数据字典
        """
        # 从分析结果提取信息
        practical_elements = analysis.get("practical_elements", [])
        safety_notes = analysis.get("safety_considerations", [])
        tools = analysis.get("tools_or_equipment", [])
        time_estimate = analysis.get("estimated_practice_time_minutes", 30)
        
        # 从内容中提取步骤（简单启发式）
        steps = []
        lines = content.split("\n")
        step_number = 0
        for line in lines:
            line = line.strip()
            # 识别步骤标记
            if any(marker in line for marker in ["1.", "2.", "3.", "4.", "5.", "6.", "7.",
                                                   "第一", "第二", "第三", "第四", "第五",
                                                   "步骤一", "步骤二", "步骤三", "步骤四"]):
                step_number += 1
                # 清理步骤描述
                action = line
                for prefix in ["1.", "2.", "3.", "4.", "5.", "6.", "7.",
                               "第一步", "第二步", "第三步", "第四步", "第五步",
                               "步骤一", "步骤二", "步骤三", "步骤四", "步骤五"]:
                    action = action.replace(prefix, "").strip()
                
                if action and len(action) > 2:
                    steps.append({
                        "step_number": step_number,
                        "action": action[:100],  # 限制长度
                        "expected_duration_seconds": 60,
                        "tools_required": tools[:2] if tools else [],
                        "safety_notes": safety_notes[:1] if safety_notes else [],
                        "criteria": [
                            {
                                "name": f"步骤{step_number}操作规范性",
                                "description": f"正确执行：{action[:50]}",
                                "weight": 0.15,
                                "level": "major",
                                "pass_threshold": 0.6,
                                "scoring_rubric": {
                                    "excellent": "操作完全正确，动作规范流畅",
                                    "good": "操作基本正确，有轻微瑕疵",
                                    "acceptable": "操作达到基本要求",
                                    "poor": "操作不规范或遗漏关键动作"
                                },
                                "detection_hints": [f"检测步骤{step_number}是否完成"]
                            }
                        ]
                    })
        
        # 如果没有提取到步骤，创建默认步骤
        if not steps:
            default_actions = practical_elements[:5] if practical_elements else ["准备工作", "执行操作", "完成检查"]
            for i, action in enumerate(default_actions, 1):
                steps.append({
                    "step_number": i,
                    "action": action,
                    "expected_duration_seconds": 60,
                    "tools_required": [],
                    "safety_notes": [],
                    "criteria": [
                        {
                            "name": f"步骤{i}操作规范性",
                            "description": f"规范执行：{action}",
                            "weight": round(0.8 / len(default_actions), 2),
                            "level": "major",
                            "pass_threshold": 0.6,
                            "scoring_rubric": {
                                "excellent": "操作规范，表现优秀",
                                "good": "操作基本正确",
                                "acceptable": "操作达到基本要求",
                                "poor": "操作不规范"
                            },
                            "detection_hints": [f"检测{action}是否完成"]
                        }
                    ]
                })
        
        # 构建评分量表
        return {
            "sop_steps": steps,
            "overall_criteria": [
                {
                    "name": "操作完整性",
                    "description": "所有步骤均已完成",
                    "weight": 0.1,
                    "level": "major",
                    "pass_threshold": 0.6,
                    "scoring_rubric": {},
                    "detection_hints": ["检查所有步骤是否完成"]
                },
                {
                    "name": "时间控制",
                    "description": f"在规定时间（{time_estimate}分钟）内完成",
                    "weight": 0.1,
                    "level": "minor",
                    "pass_threshold": 0.5,
                    "scoring_rubric": {},
                    "detection_hints": ["检查完成时间"]
                }
            ],
            "total_score": 100,
            "pass_score": 60,
            "time_limit_minutes": time_estimate
        }
    
    def extract_practical_knowledge(
        self,
        query: str = "实操 培训 考核",
        top_k: int = 20
    ) -> List[Dict]:
        """
        从知识库中提取实操类知识点
        
        Args:
            query: 检索查询
            top_k: 返回数量
            
        Returns:
            实操类知识点列表
        """
        if not self.knowledge_manager:
            console.print("[red]✗[/red] 知识管理器不可用")
            return []
        
        # 检索相关知识点
        results = self.knowledge_manager.query_knowledge(query, top_k=top_k)
        
        practical_points = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("分析知识点类型...", total=len(results))
            
            for result in results:
                content = result.get("content", "")
                knowledge_type, analysis = self.classify_knowledge_point(content)
                
                if analysis.get("is_practical", False):
                    practical_points.append({
                        "content": content,
                        "source": result.get("source", ""),
                        "knowledge_name": result.get("knowledge_name", ""),
                        "core_concept": result.get("core_concept", ""),
                        "category": result.get("category", ""),
                        "knowledge_type": knowledge_type.value,
                        "analysis": analysis
                    })
                
                progress.advance(task)
        
        console.print(f"[green]✓[/green] 从 {len(results)} 个知识点中识别出 {len(practical_points)} 个实操类知识点")
        
        return practical_points
    
    def generate_assessment_rubric(
        self,
        knowledge_point: Dict,
        course_id: str = "default_course"
    ) -> Optional[PracticalAssessment]:
        """
        生成评分量表
        
        Args:
            knowledge_point: 知识点数据
            course_id: 课程ID
            
        Returns:
            实操评估方案
        """
        content = knowledge_point.get("content", "")
        analysis = knowledge_point.get("analysis", {})
        title = knowledge_point.get("knowledge_name", "未命名实操项目")
        
        # 准备 prompt 参数
        practical_elements = "\n".join([
            f"- {elem}" for elem in analysis.get("practical_elements", ["暂无"])
        ])
        tools = "\n".join([
            f"- {tool}" for tool in analysis.get("tools_or_equipment", ["暂无"])
        ])
        
        prompt = GENERATE_RUBRIC_PROMPT.format(
            title=title,
            content=content[:1500],
            practical_elements=practical_elements,
            tools=tools
        )
        
        response = self._call_llm(prompt)
        rubric_data = self._parse_json(response)
        
        if not rubric_data:
            # 使用默认模板生成基础评分量表
            console.print(f"[yellow]⚠[/yellow] LLM 不可用，使用默认模板为「{title}」生成评分量表")
            rubric_data = self._generate_default_rubric(title, content, analysis)
        
        # 构建评估方案
        now = datetime.now().isoformat()
        assessment_id = hashlib.md5(
            f"{course_id}_{title}_{now}".encode()
        ).hexdigest()[:16]
        
        knowledge_point_id = hashlib.md5(
            content[:100].encode()
        ).hexdigest()[:12]
        
        # 解析 SOP 步骤
        sop_steps = []
        for step_data in rubric_data.get("sop_steps", []):
            step_criteria = []
            for crit in step_data.get("criteria", []):
                step_criteria.append(AssessmentCriterion(
                    criterion_id=hashlib.md5(
                        f"{assessment_id}_{crit.get('name', '')}".encode()
                    ).hexdigest()[:12],
                    name=crit.get("name", ""),
                    description=crit.get("description", ""),
                    weight=crit.get("weight", 0.1),
                    level=AssessmentLevel(crit.get("level", "minor")),
                    pass_threshold=crit.get("pass_threshold", 0.6),
                    scoring_rubric=crit.get("scoring_rubric", {}),
                    detection_hints=crit.get("detection_hints", [])
                ))
            
            sop_steps.append(SOPStep(
                step_id=f"step_{step_data.get('step_number', 0)}",
                step_number=step_data.get("step_number", 0),
                action=step_data.get("action", ""),
                expected_duration=step_data.get("expected_duration_seconds", 60),
                criteria=step_criteria,
                prerequisites=[
                    f"step_{i}" for i in range(1, step_data.get("step_number", 1))
                ],
                tools_required=step_data.get("tools_required", []),
                safety_notes=step_data.get("safety_notes", [])
            ))
        
        # 解析总体评分标准
        overall_criteria = []
        for crit in rubric_data.get("overall_criteria", []):
            overall_criteria.append(AssessmentCriterion(
                criterion_id=hashlib.md5(
                    f"{assessment_id}_overall_{crit.get('name', '')}".encode()
                ).hexdigest()[:12],
                name=crit.get("name", ""),
                description=crit.get("description", ""),
                weight=crit.get("weight", 0.1),
                level=AssessmentLevel(crit.get("level", "minor")),
                pass_threshold=crit.get("pass_threshold", 0.6),
                scoring_rubric=crit.get("scoring_rubric", {}),
                detection_hints=crit.get("detection_hints", [])
            ))
        
        # 确定知识点类型
        type_str = knowledge_point.get("knowledge_type", "practical")
        type_map = {
            "theoretical": KnowledgeType.THEORETICAL,
            "practical": KnowledgeType.PRACTICAL,
            "procedural": KnowledgeType.PROCEDURAL,
            "mixed": KnowledgeType.MIXED
        }
        knowledge_type = type_map.get(type_str, KnowledgeType.PRACTICAL)
        
        assessment = PracticalAssessment(
            assessment_id=assessment_id,
            title=title,
            description=knowledge_point.get("core_concept", ""),
            course_id=course_id,
            knowledge_point_id=knowledge_point_id,
            knowledge_type=knowledge_type,
            total_score=rubric_data.get("total_score", 100),
            pass_score=rubric_data.get("pass_score", 60),
            time_limit=rubric_data.get("time_limit_minutes", 30),
            sop_steps=sop_steps,
            criteria=overall_criteria,
            created_at=now,
            updated_at=now
        )
        
        # 缓存映射关系
        self._mapping_cache[knowledge_point_id] = assessment
        
        console.print(f"[green]✓[/green] 已生成评分量表: {title}")
        
        return assessment
    
    def get_mapping(self, knowledge_point_id: str) -> Optional[PracticalAssessment]:
        """
        获取知识点到技能评估的映射
        
        Args:
            knowledge_point_id: 知识点ID
            
        Returns:
            对应的实操评估方案
        """
        return self._mapping_cache.get(knowledge_point_id)
    
    def list_mappings(self) -> List[Dict]:
        """列出所有映射关系"""
        return [
            {
                "knowledge_point_id": kp_id,
                "assessment_id": assessment.assessment_id,
                "title": assessment.title,
                "sop_steps_count": len(assessment.sop_steps),
                "criteria_count": sum(
                    len(step.criteria) for step in assessment.sop_steps
                ) + len(assessment.criteria)
            }
            for kp_id, assessment in self._mapping_cache.items()
        ]


# ============================================================================
# NexusMapper 主类
# ============================================================================
class NexusMapper:
    """
    Nexus Learn AI 集成映射器
    
    实现 SmartCourseEngine 与 Nexus Learn AI 的数据对接。
    """
    
    def __init__(
        self,
        nexus_api_url: str = NEXUS_API_URL,
        nexus_api_key: str = NEXUS_API_KEY
    ):
        """
        初始化 Nexus 映射器
        
        Args:
            nexus_api_url: Nexus Learn AI 后端 URL
            nexus_api_key: API 密钥
        """
        self.nexus_api_url = nexus_api_url.rstrip("/")
        self.nexus_api_key = nexus_api_key
        
        # 初始化知识技能桥梁
        self.bridge = Knowledge_to_Skill_Bridge()
        
        # 检查 Nexus 连接
        self._check_connection()
    
    def _check_connection(self) -> bool:
        """检查与 Nexus Learn AI 的连接"""
        try:
            response = requests.get(
                f"{self.nexus_api_url}/health",
                timeout=5
            )
            if response.status_code == 200:
                console.print(f"[green]✓[/green] Nexus Learn AI 连接成功: {self.nexus_api_url}")
                return True
            else:
                console.print(f"[yellow]⚠[/yellow] Nexus Learn AI 响应异常: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            console.print(f"[yellow]⚠[/yellow] Nexus Learn AI 连接失败: {e}")
            console.print("[dim]评分标准将保存到本地文件[/dim]")
            return False
    
    def _get_headers(self) -> Dict:
        """获取 API 请求头"""
        headers = {"Content-Type": "application/json"}
        if self.nexus_api_key:
            headers["Authorization"] = f"Bearer {self.nexus_api_key}"
        return headers
    
    def process_practical_knowledge(
        self,
        query: str = "实操 培训 急救 护理",
        course_id: str = "default_course",
        top_k: int = 10
    ) -> List[PracticalAssessment]:
        """
        处理实操类知识点，生成评分量表
        
        Args:
            query: 检索查询
            course_id: 课程ID
            top_k: 处理数量
            
        Returns:
            生成的评估方案列表
        """
        console.print(Panel(
            f"开始处理实操类知识点\n"
            f"查询: {query}\n"
            f"课程ID: {course_id}",
            title="📋 Nexus Mapper",
            style="blue"
        ))
        
        # 1. 提取实操类知识点
        practical_points = self.bridge.extract_practical_knowledge(query, top_k)
        
        if not practical_points:
            console.print("[yellow]未找到实操类知识点[/yellow]")
            return []
        
        # 2. 为每个知识点生成评分量表
        assessments = []
        
        for point in practical_points:
            assessment = self.bridge.generate_assessment_rubric(
                point, 
                course_id=course_id
            )
            if assessment:
                assessments.append(assessment)
        
        console.print(f"\n[green]✓[/green] 共生成 {len(assessments)} 份评分量表")
        
        return assessments
    
    def push_to_nexus(
        self,
        assessments: List[PracticalAssessment]
    ) -> Dict[str, Any]:
        """
        将评分标准推送到 Nexus Learn AI
        
        Args:
            assessments: 评估方案列表
            
        Returns:
            推送结果统计
        """
        results = {
            "total": len(assessments),
            "success": 0,
            "failed": 0,
            "local_saved": 0,
            "errors": []
        }
        
        # 确保输出目录存在
        output_dir = Path(__file__).parent / "generated_courseware" / "assessments"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for assessment in assessments:
            # 尝试推送到 Nexus
            try:
                response = requests.post(
                    f"{self.nexus_api_url}/api/assessments",
                    headers=self._get_headers(),
                    json=json.loads(assessment.to_json()),
                    timeout=10
                )
                
                if response.status_code in [200, 201]:
                    results["success"] += 1
                    console.print(f"[green]✓[/green] 已推送: {assessment.title}")
                else:
                    results["failed"] += 1
                    results["errors"].append(
                        f"{assessment.title}: HTTP {response.status_code}"
                    )
                    # 保存到本地
                    self._save_local(assessment, output_dir)
                    results["local_saved"] += 1
                    
            except requests.exceptions.RequestException as e:
                results["failed"] += 1
                results["errors"].append(f"{assessment.title}: {str(e)}")
                # 保存到本地
                self._save_local(assessment, output_dir)
                results["local_saved"] += 1
        
        # 显示结果摘要
        self._display_results(results)
        
        return results
    
    def _save_local(self, assessment: PracticalAssessment, output_dir: Path):
        """保存评估方案到本地文件"""
        filename = f"{assessment.assessment_id}_{assessment.title[:20]}.json"
        # 清理文件名中的非法字符
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        filepath = output_dir / filename
        filepath.write_text(assessment.to_json(), encoding="utf-8")
        console.print(f"[dim]已保存到本地: {filepath}[/dim]")
    
    def _display_results(self, results: Dict):
        """显示推送结果"""
        table = Table(title="📊 推送结果统计")
        table.add_column("指标", style="cyan")
        table.add_column("数值", style="magenta")
        
        table.add_row("总计", str(results["total"]))
        table.add_row("成功推送", f"[green]{results['success']}[/green]")
        table.add_row("推送失败", f"[red]{results['failed']}[/red]")
        table.add_row("本地保存", f"[yellow]{results['local_saved']}[/yellow]")
        
        console.print(table)
        
        if results["errors"]:
            console.print("\n[red]错误详情:[/red]")
            for error in results["errors"][:5]:
                console.print(f"  [dim]• {error}[/dim]")
    
    def generate_training_task(
        self,
        assessment: PracticalAssessment,
        trainee_id: str = "default_trainee"
    ) -> Dict:
        """
        基于评估方案生成实训任务
        
        Args:
            assessment: 评估方案
            trainee_id: 学员ID
            
        Returns:
            实训任务数据
        """
        task_id = hashlib.md5(
            f"{assessment.assessment_id}_{trainee_id}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        return {
            "task_id": task_id,
            "trainee_id": trainee_id,
            "assessment_id": assessment.assessment_id,
            "title": f"实训: {assessment.title}",
            "description": assessment.description,
            "course_id": assessment.course_id,
            "status": "pending",  # pending, in_progress, completed, failed
            "time_limit_minutes": assessment.time_limit,
            "pass_score": assessment.pass_score,
            "total_score": assessment.total_score,
            "sop_checklist": [
                {
                    "step_id": step.step_id,
                    "step_number": step.step_number,
                    "action": step.action,
                    "completed": False,
                    "score": 0,
                    "feedback": ""
                }
                for step in assessment.sop_steps
            ],
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "final_score": None,
            "feedback": None
        }


# ============================================================================
# 示例场景：托育急救评分量表生成
# ============================================================================
CHILDCARE_EMERGENCY_EXAMPLE = {
    "title": "托育急救 - 婴幼儿心肺复苏",
    "content": """
婴幼儿心肺复苏（CPR）是托育从业人员必须掌握的急救技能。
当发现婴幼儿出现心跳呼吸骤停时，需要立即进行心肺复苏抢救。

【操作步骤】
1. 确认现场安全，呼叫帮助
2. 判断意识：轻拍婴儿足底，观察反应
3. 开放气道：仰头抬颏法（婴儿头部后仰角度不宜过大）
4. 检查呼吸：看、听、感觉，不超过10秒
5. 胸外按压：
   - 按压位置：两乳头连线中点下方
   - 按压深度：胸廓前后径的1/3（约4cm）
   - 按压频率：100-120次/分钟
   - 双指按压法（单人施救）
6. 人工呼吸：口对口鼻人工呼吸
   - 按压与呼吸比例：30:2
7. 持续进行，每2分钟评估一次

【安全注意事项】
- 按压力度不宜过大，避免造成肋骨骨折
- 人工呼吸时吹气量要适当
- 操作过程中注意观察面色变化
    """,
    "analysis": {
        "is_practical": True,
        "practical_elements": [
            "判断意识",
            "开放气道",
            "胸外按压",
            "人工呼吸",
            "按压频率控制",
            "按压深度控制"
        ],
        "safety_considerations": [
            "按压力度控制",
            "避免肋骨骨折",
            "吹气量适当"
        ],
        "tools_or_equipment": [
            "婴儿模拟人",
            "计时器",
            "节拍器"
        ],
        "estimated_practice_time_minutes": 20,
        "complexity_level": "intermediate",
        "key_competencies": ["急救技能", "婴幼儿护理", "应急响应"]
    }
}


# ============================================================================
# 命令行入口
# ============================================================================
def main():
    """主入口函数"""
    console.print(Panel("""
╔══════════════════════════════════════════════════════════════╗
║             Nexus Mapper - 智课灵境集成模块                  ║
║                                                              ║
║  功能：知识提取 | 评分量表生成 | 实训任务对接                ║
╚══════════════════════════════════════════════════════════════╝
    """, style="blue"))
    
    # 检查 API Key
    if not API_KEY:
        console.print("[yellow]⚠ 警告：未配置 DEEPSEEK_API_KEY[/yellow]")
        console.print("[dim]评分量表生成功能将受限[/dim]\n")
    
    # 初始化映射器
    mapper = NexusMapper()
    
    # 演示模式：使用示例数据
    console.print("\n[cyan]>>> 演示模式：生成托育急救评分量表[/cyan]\n")
    
    # 使用示例数据生成评分量表
    bridge = mapper.bridge
    example_point = {
        "content": CHILDCARE_EMERGENCY_EXAMPLE["content"],
        "knowledge_name": CHILDCARE_EMERGENCY_EXAMPLE["title"],
        "core_concept": "婴幼儿心肺复苏急救技能培训",
        "category": "托育培训",
        "knowledge_type": "practical",
        "analysis": CHILDCARE_EMERGENCY_EXAMPLE["analysis"]
    }
    
    assessment = bridge.generate_assessment_rubric(
        example_point,
        course_id="childcare_training_2026"
    )
    
    if assessment:
        # 显示生成的评分量表
        console.print(Panel(
            assessment.to_json(),
            title=f"📋 评分量表: {assessment.title}",
            style="green"
        ))
        
        # 保存到本地
        output_dir = Path(__file__).parent / "generated_courseware" / "assessments"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"{assessment.assessment_id}_托育急救.json"
        output_file.write_text(assessment.to_json(), encoding="utf-8")
        console.print(f"\n[green]✓ 已保存到: {output_file}[/green]")
        
        # 生成实训任务示例
        task = mapper.generate_training_task(assessment, trainee_id="trainee_001")
        console.print(Panel(
            json.dumps(task, ensure_ascii=False, indent=2),
            title="📝 实训任务",
            style="cyan"
        ))
    
    # 显示映射关系
    mappings = bridge.list_mappings()
    if mappings:
        table = Table(title="📊 知识点-技能映射关系")
        table.add_column("知识点ID", style="dim")
        table.add_column("评估ID", style="cyan")
        table.add_column("标题", style="magenta")
        table.add_column("步骤数", style="green")
        table.add_column("评分项数", style="yellow")
        
        for m in mappings:
            table.add_row(
                m["knowledge_point_id"][:8] + "...",
                m["assessment_id"][:8] + "...",
                m["title"][:20],
                str(m["sop_steps_count"]),
                str(m["criteria_count"])
            )
        
        console.print(table)
    
    console.print("\n[green]✓ Nexus Mapper 演示完成！[/green]")
    console.print("[dim]使用 mapper.process_practical_knowledge() 处理知识库中的实操知识点[/dim]")


if __name__ == "__main__":
    main()
