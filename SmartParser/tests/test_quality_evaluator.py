#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SmartCourseEngine 单元测试
==========================

测试核心功能模块的可靠性：
- 质量评估器
- 内容生成器
- 视频创建器

运行测试:
    pytest tests/ -v
    
或运行单个测试文件:
    pytest tests/test_quality_evaluator.py -v
    
作者: SmartCourseEngine Team
日期: 2026-01-31
"""

import pytest
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from quality_evaluator import (
    CoursewareEvaluator,
    QualityScore,
    QualityReport,
    REQUIRED_SECTIONS,
    QUALITY_CRITERIA
)


# ============================================================================
# 测试数据
# ============================================================================
@pytest.fixture
def sample_courseware():
    """标准课件样例数据"""
    return {
        "topic": "人工智能基础",
        "generated_at": "2026-01-31T10:00:00",
        "outline": {
            "title": "人工智能基础课程",
            "introduction": {
                "title": "导入部分",
                "points": ["什么是人工智能", "AI的发展历程", "AI的应用场景"]
            },
            "core_content": {
                "title": "核心讲解",
                "points": ["机器学习基础", "深度学习原理", "神经网络结构"]
            },
            "case_analysis": {
                "title": "案例分析",
                "points": ["图像识别案例", "自然语言处理案例"]
            },
            "summary": {
                "title": "总结回顾",
                "points": ["关键知识点", "后续学习路径"]
            }
        },
        "scripts": [
            {
                "section": "导入部分",
                "content": "欢迎来到人工智能基础课程。首先，让我们了解什么是人工智能。人工智能是计算机科学的一个分支，致力于创建能够执行通常需要人类智能的任务的系统。接下来，我们将探讨AI的发展历程，从1950年代的起源到今天的突破性进展。最后，我们将介绍AI在医疗、金融、教育等领域的广泛应用场景。"
            },
            {
                "section": "核心讲解",
                "content": "机器学习是人工智能的核心技术之一。它使计算机能够从数据中学习，而无需显式编程。深度学习是机器学习的一个子集，使用多层神经网络来处理复杂的数据模式。神经网络的结构包括输入层、隐藏层和输出层，每一层都包含多个神经元，通过权重连接并进行信息传递。因此，理解这些基础概念对于掌握人工智能至关重要。"
            },
            {
                "section": "案例分析",
                "content": "让我们通过具体案例来理解AI的实际应用。例如，在图像识别领域，卷积神经网络可以识别图片中的物体、人脸和场景。在自然语言处理方面，Transformer模型实现了机器翻译、文本生成等功能。这些案例展示了AI技术的强大能力。"
            },
            {
                "section": "总结回顾",
                "content": "总之，今天我们学习了人工智能的基础知识，包括机器学习、深度学习和神经网络。这些知识为后续的深入学习奠定了坚实的基础。建议大家继续探索更多的AI应用和技术细节。"
            }
        ],
        "audio_scripts": [
            {"section": "导入部分", "content": "欢迎来到人工智能基础课程..."},
            {"section": "核心讲解", "content": "机器学习是人工智能的核心..."},
            {"section": "案例分析", "content": "让我们通过具体案例..."},
            {"section": "总结回顾", "content": "总之，今天我们学习了..."}
        ],
        "quizzes": [
            {
                "knowledge_point": "机器学习基础",
                "choice": {
                    "question": "机器学习属于哪个领域？",
                    "options": {"A": "计算机科学", "B": "生物学", "C": "物理学", "D": "化学"},
                    "answer": "A",
                    "explanation": "机器学习是人工智能的一个分支，属于计算机科学领域。"
                },
                "judgment": {
                    "question": "深度学习是机器学习的一个子集。",
                    "answer": True,
                    "explanation": "深度学习确实是机器学习的一个子集，专注于使用深层神经网络。"
                },
                "case": {
                    "question": "描述一个图像识别的应用场景。",
                    "answer": "自动驾驶汽车使用图像识别来检测道路上的障碍物。",
                    "explanation": "图像识别在自动驾驶中用于实时检测行人、车辆和交通标志。"
                }
            }
        ]
    }


@pytest.fixture
def minimal_courseware():
    """最小化课件数据"""
    return {
        "topic": "测试课件",
        "outline": {},
        "scripts": [],
        "quizzes": []
    }


@pytest.fixture
def incomplete_courseware():
    """不完整课件数据"""
    return {
        "topic": "不完整课件",
        "outline": {
            "introduction": {"title": "导入", "points": ["要点1"]},
            "core_content": {"title": "核心", "points": ["要点2"]}
            # 缺少 case_analysis 和 summary
        },
        "scripts": [
            {"section": "导入", "content": "简短的内容"}
        ],
        "quizzes": []
    }


@pytest.fixture
def evaluator():
    """评估器实例"""
    return CoursewareEvaluator()


# ============================================================================
# 评估器基础测试
# ============================================================================
class TestCoursewareEvaluatorBasic:
    """评估器基础功能测试"""
    
    def test_evaluator_initialization(self, evaluator):
        """测试评估器初始化"""
        assert evaluator is not None
        assert evaluator.criteria == QUALITY_CRITERIA
    
    def test_evaluate_returns_report(self, evaluator, sample_courseware):
        """测试评估返回报告对象"""
        report = evaluator.evaluate(sample_courseware)
        
        assert isinstance(report, QualityReport)
        assert report.topic == "人工智能基础"
        assert report.overall_score >= 0
        assert report.overall_score <= 100
        assert report.grade in ["A", "B", "C", "D", "F"]
    
    def test_grade_calculation(self, evaluator):
        """测试等级计算"""
        assert evaluator._calculate_grade(95) == "A"
        assert evaluator._calculate_grade(85) == "B"
        assert evaluator._calculate_grade(75) == "C"
        assert evaluator._calculate_grade(65) == "D"
        assert evaluator._calculate_grade(50) == "F"


# ============================================================================
# 结构完整性测试
# ============================================================================
class TestStructureEvaluation:
    """结构完整性评估测试"""
    
    def test_complete_structure_high_score(self, evaluator, sample_courseware):
        """完整结构应获得高分"""
        score = evaluator._evaluate_structure(sample_courseware)
        
        assert score.criterion == "结构完整性"
        assert score.score >= 80  # 完整结构应该得高分
        assert score.weight == 0.25
    
    def test_incomplete_structure_low_score(self, evaluator, incomplete_courseware):
        """不完整结构应获得较低分数"""
        score = evaluator._evaluate_structure(incomplete_courseware)
        
        assert score.score < 80
        assert len(score.suggestions) > 0  # 应有改进建议
    
    def test_empty_outline_zero_score(self, evaluator, minimal_courseware):
        """空大纲应获得零分"""
        score = evaluator._evaluate_structure(minimal_courseware)
        
        assert score.score == 0
        assert "缺少课程大纲" in score.details


# ============================================================================
# 内容丰富度测试
# ============================================================================
class TestContentRichnessEvaluation:
    """内容丰富度评估测试"""
    
    def test_rich_content_high_score(self, evaluator, sample_courseware):
        """丰富内容应获得高分"""
        score = evaluator._evaluate_content_richness(sample_courseware)
        
        assert score.criterion == "内容丰富度"
        assert score.score >= 60  # 有一定内容应该有分数
    
    def test_empty_content_low_score(self, evaluator, minimal_courseware):
        """空内容应获得低分"""
        score = evaluator._evaluate_content_richness(minimal_courseware)
        
        assert score.score == 0
        assert "没有任何脚本内容" in score.details
    
    def test_content_word_count(self, evaluator, sample_courseware):
        """测试内容字数统计"""
        score = evaluator._evaluate_content_richness(sample_courseware)
        
        assert "字" in score.details  # 应包含字数信息


# ============================================================================
# 知识点覆盖测试
# ============================================================================
class TestKnowledgeCoverageEvaluation:
    """知识点覆盖评估测试"""
    
    def test_good_coverage(self, evaluator, sample_courseware):
        """良好覆盖应获得高分"""
        score = evaluator._evaluate_knowledge_coverage(sample_courseware)
        
        assert score.criterion == "知识点覆盖"
        # 脚本内容与大纲知识点相关，应有一定覆盖率
        assert score.score >= 30
    
    def test_no_knowledge_points(self, evaluator, minimal_courseware):
        """无知识点定义应给予基础评估"""
        score = evaluator._evaluate_knowledge_coverage(minimal_courseware)
        
        # 没有知识点时基于内容量评估
        assert score.score >= 0


# ============================================================================
# 练习题质量测试
# ============================================================================
class TestQuizQualityEvaluation:
    """练习题质量评估测试"""
    
    def test_with_quizzes(self, evaluator, sample_courseware):
        """有练习题应获得相应分数"""
        score = evaluator._evaluate_quiz_quality(sample_courseware)
        
        assert score.criterion == "练习题质量"
        assert score.score > 30  # 有完整题目应该有高分
    
    def test_without_quizzes(self, evaluator, minimal_courseware):
        """无练习题应获得基础分"""
        score = evaluator._evaluate_quiz_quality(minimal_courseware)
        
        assert score.score == 30  # 基础分
        assert "未包含练习题" in score.details


# ============================================================================
# 可读性测试
# ============================================================================
class TestReadabilityEvaluation:
    """可读性评估测试"""
    
    def test_readable_content(self, evaluator, sample_courseware):
        """可读性良好的内容应获得分数"""
        score = evaluator._evaluate_readability(sample_courseware)
        
        assert score.criterion == "可读性"
        assert score.score > 0
    
    def test_empty_content_readability(self, evaluator, minimal_courseware):
        """空内容可读性应为零"""
        score = evaluator._evaluate_readability(minimal_courseware)
        
        assert score.score == 0


# ============================================================================
# 报告生成测试
# ============================================================================
class TestReportGeneration:
    """报告生成测试"""
    
    def test_report_structure(self, evaluator, sample_courseware):
        """测试报告结构完整性"""
        report = evaluator.evaluate(sample_courseware)
        
        assert report.topic is not None
        assert report.generated_at is not None
        assert report.overall_score is not None
        assert report.grade is not None
        assert len(report.scores) == 5  # 五个评估维度
        assert report.summary is not None
        assert isinstance(report.strengths, list)
        assert isinstance(report.weaknesses, list)
        assert isinstance(report.recommendations, list)
    
    def test_export_report(self, evaluator, sample_courseware, tmp_path):
        """测试报告导出"""
        report = evaluator.evaluate(sample_courseware)
        
        output_path = tmp_path / "test_report.md"
        result_path = evaluator.export_report(report, str(output_path))
        
        assert Path(result_path).exists()
        
        content = Path(result_path).read_text(encoding="utf-8")
        assert "课件质量评估报告" in content
        assert report.topic in content
        assert report.grade in content


# ============================================================================
# 边界条件测试
# ============================================================================
class TestEdgeCases:
    """边界条件测试"""
    
    def test_none_courseware(self, evaluator):
        """测试空课件处理"""
        empty_courseware = {}
        report = evaluator.evaluate(empty_courseware)
        
        assert report is not None
        assert report.grade == "F"  # 应该是最低等级
    
    def test_special_characters_in_topic(self, evaluator):
        """测试主题包含特殊字符"""
        courseware = {
            "topic": "AI/ML: 入门指南 (2026)",
            "outline": {},
            "scripts": []
        }
        report = evaluator.evaluate(courseware)
        
        assert report.topic == "AI/ML: 入门指南 (2026)"
    
    def test_very_long_content(self, evaluator):
        """测试超长内容"""
        long_content = "这是一段测试内容。" * 1000
        courseware = {
            "topic": "长内容测试",
            "outline": {},
            "scripts": [{"section": "测试", "content": long_content}]
        }
        report = evaluator.evaluate(courseware)
        
        # 超长内容应该得到高的内容丰富度分数
        content_score = next(s for s in report.scores if s.criterion == "内容丰富度")
        assert content_score.score >= 80


# ============================================================================
# 运行入口
# ============================================================================
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
