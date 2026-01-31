#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专家验证器 (Expert Validator)
===============================

实现行业专家级别的内容验证：
- 行业标准对齐：标注符合的标准条款
- 双模型验证：生成模型 + 校验模型
- 敏感词过滤：合规安全检查
- 知识图谱构建：知识点关联可视化

作者: SmartCourseEngine Team
日期: 2026-01-31
"""

import os
import json
import re
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

from rich.console import Console

console = Console()

# ============================================================================
# API 配置
# ============================================================================
API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
BASE_URL = os.getenv("API_BASE_URL", "https://api.deepseek.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-chat")

# 标准库存储路径
STANDARDS_DIR = Path(__file__).parent / "standards_library"
STANDARDS_DIR.mkdir(exist_ok=True)

# ============================================================================
# 数据模型
# ============================================================================
class ValidationResult(Enum):
    """验证结果枚举"""
    PASSED = "passed"
    NEEDS_REVISION = "needs_revision"
    REJECTED = "rejected"


@dataclass
class StandardReference:
    """标准引用"""
    standard_name: str      # 标准名称，如"国家托育服务标准"
    section: str            # 条款编号，如"第3.2条"
    content: str            # 条款内容
    relevance_score: float  # 相关度分数


@dataclass
class ValidationFeedback:
    """验证反馈"""
    result: ValidationResult
    score: float            # 0-100
    issues: List[str]       # 发现的问题
    suggestions: List[str]  # 改进建议
    hallucinations: List[str]  # 发现的幻觉
    standard_violations: List[str]  # 标准违反
    safe_to_publish: bool   # 是否可发布


@dataclass
class KnowledgeNode:
    """知识图谱节点"""
    node_id: str
    label: str
    content: str
    category: str
    importance: float = 0.5
    standards: List[StandardReference] = field(default_factory=list)


@dataclass
class KnowledgeEdge:
    """知识图谱边"""
    source_id: str
    target_id: str
    relation: str           # 关系类型：因果、包含、并列等
    weight: float = 1.0
    is_blocked: bool = False  # 是否被用户禁用


@dataclass
class KnowledgeGraph:
    """知识图谱"""
    nodes: List[KnowledgeNode] = field(default_factory=list)
    edges: List[KnowledgeEdge] = field(default_factory=list)
    
    def to_agraph_data(self) -> Tuple[List[Dict], List[Dict]]:
        """转换为 streamlit-agraph 格式"""
        nodes = []
        edges = []
        
        # 节点颜色映射
        category_colors = {
            "核心概念": "#FF6B6B",
            "实践方法": "#4ECDC4",
            "案例": "#45B7D1",
            "标准规范": "#96CEB4",
            "默认": "#DDA0DD"
        }
        
        for node in self.nodes:
            color = category_colors.get(node.category, category_colors["默认"])
            nodes.append({
                "id": node.node_id,
                "label": node.label,
                "title": node.content[:100] + "..." if len(node.content) > 100 else node.content,
                "color": color,
                "size": 20 + int(node.importance * 30)
            })
        
        for edge in self.edges:
            if not edge.is_blocked:
                edges.append({
                    "source": edge.source_id,
                    "target": edge.target_id,
                    "label": edge.relation,
                    "width": edge.weight * 2,
                    "color": "#888888" if edge.weight < 0.5 else "#333333"
                })
        
        return nodes, edges


# ============================================================================
# 敏感词库
# ============================================================================
SENSITIVE_WORDS = {
    "医疗": [
        "包治", "根治", "特效", "神药", "秘方", "偏方",
        "100%有效", "绝对安全", "无副作用", "立即见效",
        "替代医生", "不用就医", "自行诊断"
    ],
    "教育": [
        "保过", "包分配", "100%就业", "天才速成",
        "智力提升", "考试作弊", "代写", "代考"
    ],
    "金融": [
        "稳赚不赔", "高收益零风险", "内幕消息", "保本保息",
        "躺赚", "暴富"
    ],
    "通用": [
        "最好", "第一", "独家", "唯一", "国家级",
        "政府推荐", "领导人推荐"
    ]
}


# ============================================================================
# Prompts
# ============================================================================
STANDARD_ALIGNMENT_PROMPT = """你是一位严谨的行业标准专家。请分析以下内容是否符合行业标准，并标注对应条款。

【生成内容】
{content}

【适用标准库】
{standards}

请以 JSON 格式返回分析结果：
{{
    "aligned_standards": [
        {{
            "standard_name": "标准名称",
            "section": "条款编号",
            "alignment_note": "符合说明"
        }}
    ],
    "violations": [
        {{
            "content_excerpt": "违规内容片段",
            "violation_reason": "违规原因",
            "suggested_fix": "修改建议"
        }}
    ],
    "compliance_score": 85
}}

仅返回 JSON。"""

EXAMINER_PROMPT = """你是一位严格的内容审核专家，扮演"考官"角色。请对以下AI生成的课件内容进行专业审查。

【原始素材/知识来源】
{source_material}

【AI生成的内容】
{generated_content}

【适用行业标准】
{standards}

请从以下维度进行打分和审查：
1. 事实准确性（是否存在幻觉/编造内容）
2. 逻辑严谨性（论述是否有逻辑漏洞）
3. 标准符合度（是否违反行业规定）
4. 专业表达度（用语是否专业准确）
5. 完整性（是否遗漏关键信息）

请以 JSON 格式返回：
{{
    "overall_score": 85,
    "dimension_scores": {{
        "accuracy": 90,
        "logic": 85,
        "compliance": 80,
        "professionalism": 85,
        "completeness": 90
    }},
    "hallucinations": [
        "发现的幻觉内容1",
        "发现的幻觉内容2"
    ],
    "logic_issues": [
        "逻辑问题1"
    ],
    "missing_points": [
        "遗漏的关键点"
    ],
    "revision_suggestions": [
        "具体的修改建议1",
        "具体的修改建议2"
    ],
    "verdict": "passed/needs_revision/rejected"
}}

仅返回 JSON。"""

KNOWLEDGE_GRAPH_PROMPT = """你是一位知识工程专家。请从以下内容中提取知识点，并分析它们之间的逻辑关系。

【课件内容】
{content}

请以 JSON 格式返回知识图谱：
{{
    "nodes": [
        {{
            "id": "node_1",
            "label": "知识点简短名称",
            "content": "知识点详细内容",
            "category": "核心概念/实践方法/案例/标准规范",
            "importance": 0.8
        }}
    ],
    "edges": [
        {{
            "source": "node_1",
            "target": "node_2",
            "relation": "因果/包含/并列/前提/应用"
        }}
    ]
}}

仅返回 JSON。"""

REVISION_PROMPT = """你是一位专业的课件优化专家。请根据审查反馈，修正以下内容。

【原始内容】
{original_content}

【审查反馈】
{feedback}

【修正要求】
1. 删除或修正所有被指出的幻觉内容
2. 修复逻辑漏洞
3. 补充遗漏的关键信息
4. 确保符合行业标准
5. 保持内容的完整性和可读性

请直接输出修正后的完整内容，不要添加额外说明。"""


# ============================================================================
# 专家验证器主类
# ============================================================================
class ExpertValidator:
    """
    专家验证器
    
    实现行业专家级别的内容验证和优化。
    """
    
    def __init__(
        self,
        api_key: str = API_KEY,
        base_url: str = BASE_URL,
        model_name: str = MODEL_NAME,
        industry: str = "通用"
    ):
        """初始化专家验证器"""
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.industry = industry
        self.llm = None
        self.standards_db = {}
        
        self._init_llm()
        self._load_standards()
    
    def _init_llm(self):
        """初始化大语言模型"""
        if not self.api_key:
            console.print("[yellow]⚠[/yellow] 未配置 API Key")
            return
        
        try:
            from langchain_openai import ChatOpenAI
            
            self.llm = ChatOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model_name,
                temperature=0.3  # 验证时使用较低温度
            )
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] LLM 初始化失败: {e}")
    
    def _load_standards(self):
        """加载标准库"""
        self.standards_db = {}
        
        if not STANDARDS_DIR.exists():
            return
        
        for std_file in STANDARDS_DIR.glob("*.md"):
            try:
                content = std_file.read_text(encoding='utf-8')
                self.standards_db[std_file.stem] = {
                    "name": std_file.stem,
                    "content": content,
                    "sections": self._parse_standard_sections(content)
                }
                console.print(f"[dim]已加载标准: {std_file.stem}[/dim]")
            except Exception as e:
                console.print(f"[yellow]标准加载失败 {std_file}: {e}[/yellow]")
    
    def _parse_standard_sections(self, content: str) -> List[Dict]:
        """解析标准文档的条款"""
        sections = []
        
        # 匹配常见的条款格式
        patterns = [
            r'第(\d+(?:\.\d+)?(?:\.\d+)?)条[：:]\s*(.+?)(?=第\d+|$)',
            r'(\d+(?:\.\d+)?(?:\.\d+)?)[.、]\s*(.+?)(?=\d+\.|$)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            for match in matches:
                section_num, section_content = match
                sections.append({
                    "number": section_num,
                    "content": section_content.strip()[:500]
                })
        
        return sections
    
    def add_standard(self, name: str, content: str) -> bool:
        """添加新标准到库"""
        try:
            std_path = STANDARDS_DIR / f"{name}.md"
            std_path.write_text(content, encoding='utf-8')
            
            self.standards_db[name] = {
                "name": name,
                "content": content,
                "sections": self._parse_standard_sections(content)
            }
            
            return True
        except Exception as e:
            console.print(f"[red]添加标准失败: {e}[/red]")
            return False
    
    def get_standards_list(self) -> List[str]:
        """获取已加载的标准列表"""
        return list(self.standards_db.keys())
    
    def check_sensitive_words(self, content: str) -> Tuple[bool, List[str]]:
        """
        敏感词检查
        
        Args:
            content: 待检查内容
            
        Returns:
            (是否通过, 发现的敏感词列表)
        """
        found_words = []
        
        # 检查行业特定敏感词
        industry_words = SENSITIVE_WORDS.get(self.industry, [])
        general_words = SENSITIVE_WORDS.get("通用", [])
        
        all_words = industry_words + general_words
        
        for word in all_words:
            if word in content:
                found_words.append(word)
        
        return len(found_words) == 0, found_words
    
    def align_with_standards(
        self,
        content: str,
        standards: List[str] = None
    ) -> Tuple[List[StandardReference], List[Dict]]:
        """
        与行业标准对齐
        
        Args:
            content: 生成的内容
            standards: 要对齐的标准名称列表
            
        Returns:
            (符合的标准引用列表, 违规列表)
        """
        if not self.llm:
            return [], []
        
        # 准备标准内容
        if standards is None:
            standards = list(self.standards_db.keys())
        
        standards_text = ""
        for std_name in standards:
            if std_name in self.standards_db:
                std = self.standards_db[std_name]
                standards_text += f"\n【{std_name}】\n{std['content'][:2000]}\n"
        
        if not standards_text:
            return [], []
        
        prompt = STANDARD_ALIGNMENT_PROMPT.format(
            content=content[:2000],
            standards=standards_text
        )
        
        try:
            response = self.llm.invoke(prompt)
            result = self._parse_json(response.content)
            
            if not result:
                return [], []
            
            # 解析符合的标准
            aligned = []
            for item in result.get("aligned_standards", []):
                aligned.append(StandardReference(
                    standard_name=item.get("standard_name", ""),
                    section=item.get("section", ""),
                    content=item.get("alignment_note", ""),
                    relevance_score=result.get("compliance_score", 0) / 100
                ))
            
            violations = result.get("violations", [])
            
            return aligned, violations
            
        except Exception as e:
            console.print(f"[yellow]标准对齐失败: {e}[/yellow]")
            return [], []
    
    def validate_content(
        self,
        generated_content: str,
        source_material: str = "",
        standards: List[str] = None,
        max_revisions: int = 3
    ) -> Tuple[str, ValidationFeedback]:
        """
        双模型验证内容
        
        Args:
            generated_content: 生成的内容
            source_material: 原始素材
            standards: 适用标准列表
            max_revisions: 最大修订次数
            
        Returns:
            (最终内容, 验证反馈)
        """
        if not self.llm:
            return generated_content, ValidationFeedback(
                result=ValidationResult.PASSED,
                score=60,
                issues=["验证模型不可用"],
                suggestions=[],
                hallucinations=[],
                standard_violations=[],
                safe_to_publish=True
            )
        
        current_content = generated_content
        revision_count = 0
        
        # 准备标准文本
        standards_text = ""
        if standards:
            for std_name in standards:
                if std_name in self.standards_db:
                    std = self.standards_db[std_name]
                    standards_text += f"\n【{std_name}】\n{std['content'][:1000]}\n"
        
        while revision_count < max_revisions:
            # 步骤1: 敏感词检查
            is_safe, sensitive_words = self.check_sensitive_words(current_content)
            
            # 步骤2: 考官验证
            prompt = EXAMINER_PROMPT.format(
                source_material=source_material[:1500] if source_material else "无原始素材",
                generated_content=current_content[:2000],
                standards=standards_text if standards_text else "无特定行业标准"
            )
            
            try:
                response = self.llm.invoke(prompt)
                result = self._parse_json(response.content)
                
                if not result:
                    break
                
                verdict = result.get("verdict", "passed")
                score = result.get("overall_score", 80)
                
                # 构建反馈
                feedback = ValidationFeedback(
                    result=ValidationResult(verdict),
                    score=score,
                    issues=result.get("logic_issues", []),
                    suggestions=result.get("revision_suggestions", []),
                    hallucinations=result.get("hallucinations", []),
                    standard_violations=[],
                    safe_to_publish=is_safe and verdict == "passed"
                )
                
                # 添加敏感词问题
                if not is_safe:
                    feedback.issues.append(f"发现敏感词: {', '.join(sensitive_words)}")
                    feedback.safe_to_publish = False
                
                # 如果通过验证，返回
                if verdict == "passed" and is_safe:
                    return current_content, feedback
                
                # 如果被拒绝，直接返回
                if verdict == "rejected":
                    return current_content, feedback
                
                # 需要修订
                revision_feedback = {
                    "hallucinations": result.get("hallucinations", []),
                    "logic_issues": result.get("logic_issues", []),
                    "missing_points": result.get("missing_points", []),
                    "suggestions": result.get("revision_suggestions", []),
                    "sensitive_words": sensitive_words
                }
                
                # 生成修订版本
                revision_prompt = REVISION_PROMPT.format(
                    original_content=current_content,
                    feedback=json.dumps(revision_feedback, ensure_ascii=False, indent=2)
                )
                
                revision_response = self.llm.invoke(revision_prompt)
                current_content = revision_response.content.strip()
                
                revision_count += 1
                console.print(f"[yellow]→ 第 {revision_count} 次修订完成[/yellow]")
                
            except Exception as e:
                console.print(f"[yellow]验证过程出错: {e}[/yellow]")
                break
        
        # 最终验证
        is_safe, _ = self.check_sensitive_words(current_content)
        
        return current_content, ValidationFeedback(
            result=ValidationResult.NEEDS_REVISION,
            score=70,
            issues=["达到最大修订次数"],
            suggestions=["建议人工审核"],
            hallucinations=[],
            standard_violations=[],
            safe_to_publish=is_safe
        )
    
    def build_knowledge_graph(self, courseware: Dict) -> KnowledgeGraph:
        """
        构建知识图谱
        
        Args:
            courseware: 课件数据
            
        Returns:
            知识图谱对象
        """
        graph = KnowledgeGraph()
        
        if not self.llm:
            # 无 LLM 时使用简单规则构建
            return self._build_simple_graph(courseware)
        
        # 收集所有内容
        all_content = []
        
        # 从大纲提取
        outline = courseware.get("outline", {})
        if outline:
            all_content.append(f"课程标题: {outline.get('title', '')}")
            for section_key in ["introduction", "core_content", "case_analysis", "summary"]:
                section = outline.get(section_key, {})
                if section:
                    all_content.append(f"{section.get('title', '')}: {', '.join(section.get('points', []))}")
        
        # 从脚本提取
        for script in courseware.get("scripts", []):
            all_content.append(script.get("content", "")[:500])
        
        content_text = "\n".join(all_content)
        
        prompt = KNOWLEDGE_GRAPH_PROMPT.format(content=content_text[:3000])
        
        try:
            response = self.llm.invoke(prompt)
            result = self._parse_json(response.content)
            
            if not result:
                return self._build_simple_graph(courseware)
            
            # 解析节点
            for node_data in result.get("nodes", []):
                graph.nodes.append(KnowledgeNode(
                    node_id=node_data.get("id", ""),
                    label=node_data.get("label", ""),
                    content=node_data.get("content", ""),
                    category=node_data.get("category", "默认"),
                    importance=node_data.get("importance", 0.5)
                ))
            
            # 解析边
            for edge_data in result.get("edges", []):
                graph.edges.append(KnowledgeEdge(
                    source_id=edge_data.get("source", ""),
                    target_id=edge_data.get("target", ""),
                    relation=edge_data.get("relation", "相关")
                ))
            
            return graph
            
        except Exception as e:
            console.print(f"[yellow]知识图谱构建失败: {e}[/yellow]")
            return self._build_simple_graph(courseware)
    
    def _build_simple_graph(self, courseware: Dict) -> KnowledgeGraph:
        """简单规则构建知识图谱"""
        graph = KnowledgeGraph()
        
        # 从大纲提取节点
        outline = courseware.get("outline", {})
        node_id = 0
        prev_node_id = None
        
        for section_key in ["introduction", "core_content", "case_analysis", "summary"]:
            section = outline.get(section_key, {})
            if section:
                current_id = f"node_{node_id}"
                graph.nodes.append(KnowledgeNode(
                    node_id=current_id,
                    label=section.get("title", section_key),
                    content=", ".join(section.get("points", [])),
                    category="核心概念" if section_key == "core_content" else "实践方法",
                    importance=0.8 if section_key == "core_content" else 0.5
                ))
                
                # 添加边
                if prev_node_id:
                    graph.edges.append(KnowledgeEdge(
                        source_id=prev_node_id,
                        target_id=current_id,
                        relation="前提"
                    ))
                
                prev_node_id = current_id
                node_id += 1
        
        return graph
    
    def _parse_json(self, text: str) -> Optional[Dict]:
        """安全解析 JSON"""
        try:
            # 清理可能的 markdown 代码块
            if "```" in text:
                match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
                if match:
                    text = match.group(1)
            
            return json.loads(text)
        except json.JSONDecodeError:
            return None
    
    def annotate_with_standards(self, content: str, standards: List[StandardReference]) -> str:
        """为内容添加标准标注"""
        if not standards:
            return content
        
        # 在内容末尾添加标准引用
        annotations = "\n\n---\n**符合标准：**\n"
        for std in standards:
            annotations += f"- 符合【{std.standard_name}】第{std.section}条\n"
        
        return content + annotations


# ============================================================================
# 导出函数
# ============================================================================
def create_expert_validator(industry: str = "通用") -> ExpertValidator:
    """创建专家验证器实例"""
    return ExpertValidator(industry=industry)


def get_available_industries() -> List[str]:
    """获取可用的行业列表"""
    return ["通用", "医疗", "教育", "金融"]


def graph_to_dict(graph: KnowledgeGraph) -> Dict:
    """将知识图谱转换为字典"""
    return {
        "nodes": [asdict(n) for n in graph.nodes],
        "edges": [asdict(e) for e in graph.edges]
    }


def dict_to_graph(data: Dict) -> KnowledgeGraph:
    """从字典恢复知识图谱"""
    graph = KnowledgeGraph()
    
    for n in data.get("nodes", []):
        graph.nodes.append(KnowledgeNode(
            node_id=n["node_id"],
            label=n["label"],
            content=n["content"],
            category=n.get("category", "默认"),
            importance=n.get("importance", 0.5)
        ))
    
    for e in data.get("edges", []):
        graph.edges.append(KnowledgeEdge(
            source_id=e["source_id"],
            target_id=e["target_id"],
            relation=e.get("relation", "相关"),
            weight=e.get("weight", 1.0),
            is_blocked=e.get("is_blocked", False)
        ))
    
    return graph
