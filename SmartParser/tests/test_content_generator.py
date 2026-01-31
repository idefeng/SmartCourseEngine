#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内容生成器单元测试
==================

测试 ContentGenerator 的核心功能：
- 知识检索
- 大纲生成
- 脚本生成
- 练习题生成
- 课件导出

注意: 部分测试需要有效的 API Key 和网络连接

作者: SmartCourseEngine Team
日期: 2026-01-31
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# 测试配置
# ============================================================================
@pytest.fixture
def mock_llm_response():
    """模拟 LLM 响应"""
    return {
        "title": "测试课程大纲",
        "introduction": {
            "title": "导入部分",
            "points": ["要点1", "要点2"]
        },
        "core_content": {
            "title": "核心内容",
            "points": ["核心要点1", "核心要点2"]
        },
        "case_analysis": {
            "title": "案例分析",
            "points": ["案例1"]
        },
        "summary": {
            "title": "总结",
            "points": ["总结要点"]
        }
    }


@pytest.fixture
def mock_knowledge_points():
    """模拟知识点数据"""
    return [
        {"content": "人工智能是计算机科学的一个分支", "source": "教材第一章"},
        {"content": "机器学习是AI的核心技术", "source": "教材第二章"},
        {"content": "深度学习使用神经网络", "source": "教材第三章"}
    ]


# ============================================================================
# 基础功能测试 (不需要 API)
# ============================================================================
class TestContentGeneratorBasic:
    """基础功能测试（不需要网络）"""
    
    def test_import_module(self):
        """测试模块导入"""
        from content_generator import ContentGenerator
        assert ContentGenerator is not None
    
    def test_prompts_exist(self):
        """测试提示词模板存在"""
        from content_generator import OUTLINE_PROMPT, SCRIPT_PROMPT, QUIZ_PROMPT
        
        assert OUTLINE_PROMPT is not None
        assert "{topic}" in OUTLINE_PROMPT
        assert SCRIPT_PROMPT is not None
        assert QUIZ_PROMPT is not None
    
    def test_json_parsing(self):
        """测试 JSON 解析功能"""
        from content_generator import ContentGenerator
        
        # 创建一个不连接 LLM 的实例进行测试
        with patch.object(ContentGenerator, '_init_llm'):
            with patch.object(ContentGenerator, '_init_knowledge_manager'):
                generator = ContentGenerator.__new__(ContentGenerator)
                generator.llm = None
                generator.knowledge_manager = None
        
                # 测试正常 JSON
                result = generator._parse_json('{"key": "value"}')
                assert result == {"key": "value"}
                
                # 测试带 markdown 代码块的 JSON
                result = generator._parse_json('```json\n{"key": "value"}\n```')
                assert result == {"key": "value"}
                
                # 测试无效 JSON
                result = generator._parse_json('not json')
                assert result is None


# ============================================================================
# 知识检索测试 (需要知识库)
# ============================================================================
class TestKnowledgeRetrieval:
    """知识检索测试"""
    
    def test_retrieve_with_mock(self, mock_knowledge_points):
        """使用 Mock 测试知识检索"""
        from content_generator import ContentGenerator
        
        with patch.object(ContentGenerator, '_init_llm'):
            with patch.object(ContentGenerator, '_init_knowledge_manager'):
                generator = ContentGenerator.__new__(ContentGenerator)
                generator.llm = None
                generator.knowledge_manager = Mock()
                generator.knowledge_manager.search.return_value = mock_knowledge_points
                
                result = generator.retrieve_knowledge("人工智能")
                
                assert len(result) == 3
                assert result[0]["content"] == "人工智能是计算机科学的一个分支"


# ============================================================================
# 大纲生成测试
# ============================================================================
class TestOutlineGeneration:
    """大纲生成测试"""
    
    def test_generate_outline_with_mock(self, mock_llm_response, mock_knowledge_points):
        """使用 Mock 测试大纲生成"""
        from content_generator import ContentGenerator
        import json
        
        with patch.object(ContentGenerator, '_init_llm'):
            with patch.object(ContentGenerator, '_init_knowledge_manager'):
                generator = ContentGenerator.__new__(ContentGenerator)
                generator.llm = Mock()
                generator.llm.invoke.return_value.content = json.dumps(mock_llm_response)
                generator.knowledge_manager = None
                
                result = generator.generate_outline("测试主题", mock_knowledge_points)
                
                assert result is not None
                assert result.get("title") == "测试课程大纲"
                assert "introduction" in result
                assert "core_content" in result


# ============================================================================
# 脚本生成测试
# ============================================================================
class TestScriptGeneration:
    """脚本生成测试"""
    
    def test_generate_script_with_mock(self):
        """使用 Mock 测试脚本生成"""
        from content_generator import ContentGenerator
        
        mock_script = "这是一段测试脚本，讲解了相关知识点。"
        
        with patch.object(ContentGenerator, '_init_llm'):
            with patch.object(ContentGenerator, '_init_knowledge_manager'):
                generator = ContentGenerator.__new__(ContentGenerator)
                generator.llm = Mock()
                generator.llm.invoke.return_value.content = mock_script
                generator.knowledge_manager = None
                
                result = generator.generate_script(
                    topic="测试主题",
                    section_title="导入部分",
                    points=["要点1", "要点2"],
                    knowledge_context="相关知识内容"
                )
                
                assert result == mock_script


# ============================================================================
# 练习题生成测试
# ============================================================================
class TestQuizGeneration:
    """练习题生成测试"""
    
    def test_generate_quiz_with_mock(self):
        """使用 Mock 测试练习题生成"""
        from content_generator import ContentGenerator
        import json
        
        mock_quiz = {
            "single_choice": {
                "question": "测试问题?",
                "options": {"A": "选项A", "B": "选项B", "C": "选项C", "D": "选项D"},
                "answer": "A",
                "explanation": "解析内容"
            }
        }
        
        with patch.object(ContentGenerator, '_init_llm'):
            with patch.object(ContentGenerator, '_init_knowledge_manager'):
                generator = ContentGenerator.__new__(ContentGenerator)
                generator.llm = Mock()
                generator.llm.invoke.return_value.content = json.dumps(mock_quiz)
                generator.knowledge_manager = None
                
                result = generator.generate_quiz("测试主题", "知识点内容")
                
                assert result is not None
                assert "single_choice" in result


# ============================================================================
# 课件导出测试
# ============================================================================
class TestCoursewareExport:
    """课件导出测试"""
    
    def test_export_to_word(self, tmp_path):
        """测试 Word 导出功能"""
        from content_generator import ContentGenerator
        
        courseware = {
            "topic": "测试课件",
            "outline": {
                "title": "测试大纲",
                "introduction": {"title": "导入", "points": ["点1"]},
                "core_content": {"title": "核心", "points": ["点2"]},
                "case_analysis": {"title": "案例", "points": []},
                "summary": {"title": "总结", "points": []}
            },
            "scripts": [
                {"section": "导入", "content": "导入内容"},
                {"section": "核心", "content": "核心内容"}
            ],
            "quizzes": [
                {
                    "single_choice": {
                        "question": "问题",
                        "options": {"A": "选项A", "B": "选项B"},
                        "answer": "A",
                        "explanation": "解析"
                    }
                }
            ]
        }
        
        with patch.object(ContentGenerator, '_init_llm'):
            with patch.object(ContentGenerator, '_init_knowledge_manager'):
                generator = ContentGenerator.__new__(ContentGenerator)
                generator.llm = None
                generator.knowledge_manager = None
                
                output_path = generator.export_to_word(courseware, str(tmp_path))
                
                assert Path(output_path).exists()
                assert output_path.endswith(".docx")


# ============================================================================
# 完整课件生成测试 (集成测试，需要 API)
# ============================================================================
class TestFullCoursewareGeneration:
    """完整课件生成测试 - 需要 API Key"""
    
    @pytest.mark.skipif(
        not os.getenv("DEEPSEEK_API_KEY"),
        reason="需要 DEEPSEEK_API_KEY 环境变量"
    )
    def test_generate_courseware_integration(self):
        """集成测试：生成完整课件"""
        from content_generator import ContentGenerator
        
        generator = ContentGenerator()
        courseware = generator.generate_courseware("Python 基础入门")
        
        assert courseware is not None
        assert courseware.get("topic") == "Python 基础入门"
        assert courseware.get("outline") is not None
        assert len(courseware.get("scripts", [])) > 0


# ============================================================================
# 运行入口
# ============================================================================
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
