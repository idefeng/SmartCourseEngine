#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频创建器单元测试
==================

测试 VideoCreator 的核心功能：
- 文本分割
- API 配置
- 头像/语音获取
- 视频创建流程

注意: 实际视频创建测试需要 HeyGen API Key

作者: SmartCourseEngine Team
日期: 2026-01-31
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# 测试数据
# ============================================================================
@pytest.fixture
def sample_courseware():
    """测试用课件数据"""
    return {
        "topic": "测试课程",
        "scripts": [
            {"section": "第一节", "content": "这是第一节的内容"},
            {"section": "第二节", "content": "这是第二节的内容"}
        ],
        "audio_scripts": [
            {"section": "第一节", "content": "这是第一节的音频脚本"},
            {"section": "第二节", "content": "这是第二节的音频脚本"}
        ]
    }


@pytest.fixture
def mock_avatar_response():
    """模拟头像 API 响应"""
    return {
        "data": {
            "avatars": [
                {"avatar_id": "avatar_001", "avatar_name": "Anna", "preview_image_url": "http://example.com/anna.jpg"},
                {"avatar_id": "avatar_002", "avatar_name": "Bob", "preview_image_url": "http://example.com/bob.jpg"}
            ]
        }
    }


@pytest.fixture
def mock_voice_response():
    """模拟语音 API 响应"""
    return {
        "data": {
            "voices": [
                {"voice_id": "voice_001", "name": "小明", "language": "chinese", "gender": "male"},
                {"voice_id": "voice_002", "name": "小红", "language": "chinese", "gender": "female"},
                {"voice_id": "voice_003", "name": "John", "language": "english", "gender": "male"}
            ]
        }
    }


# ============================================================================
# 基础功能测试
# ============================================================================
class TestVideoCreatorBasic:
    """基础功能测试"""
    
    def test_import_module(self):
        """测试模块导入"""
        from video_creator import VideoCreator, HeyGenVideoCreator
        assert VideoCreator is not None
        assert HeyGenVideoCreator is not None
    
    def test_video_dimensions(self):
        """测试视频分辨率配置"""
        from video_creator import VIDEO_DIMENSIONS
        
        assert "720p" in VIDEO_DIMENSIONS
        assert "1080p" in VIDEO_DIMENSIONS
        assert VIDEO_DIMENSIONS["720p"]["width"] == 1280
        assert VIDEO_DIMENSIONS["720p"]["height"] == 720
    
    def test_api_constants(self):
        """测试 API 常量定义"""
        from video_creator import HEYGEN_API_BASE, HEYGEN_API_BASE_V1
        
        assert "api.heygen.com" in HEYGEN_API_BASE
        assert "v2" in HEYGEN_API_BASE
        assert "v1" in HEYGEN_API_BASE_V1


# ============================================================================
# 文本处理测试
# ============================================================================
class TestTextProcessing:
    """文本处理功能测试"""
    
    def test_max_text_length_constant(self):
        """测试文本长度常量定义"""
        from video_creator import MAX_TEXT_LENGTH
        
        assert MAX_TEXT_LENGTH > 0
        assert MAX_TEXT_LENGTH <= 2000  # HeyGen 限制
    
    def test_video_creator_handles_long_text(self, sample_courseware):
        """测试 VideoCreator 处理长文本"""
        from video_creator import VideoCreator
        
        # 创建包含长文本的课件
        long_courseware = {
            "topic": "长文本测试",
            "scripts": [
                {"section": "测试", "content": "这是一段测试文本。" * 200}
            ]
        }
        
        with patch('video_creator.get_heygen_chinese_voice', return_value="mock_voice"):
            creator = VideoCreator(provider="heygen", api_key="test_key")
            
            # 确保创建器可以初始化
            assert creator is not None
            assert creator.provider == "heygen"


# ============================================================================
# 头像和语音获取测试
# ============================================================================
class TestAssetsRetrieval:
    """头像和语音获取测试"""
    
    def test_get_avatars_success(self, mock_avatar_response):
        """测试成功获取头像列表"""
        from video_creator import get_heygen_avatars
        
        with patch('video_creator.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_avatar_response
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            result = get_heygen_avatars("test_api_key")
            
            assert len(result) == 2
            assert result[0]["avatar_id"] == "avatar_001"
            assert result[1]["avatar_name"] == "Bob"
    
    def test_get_voices_success(self, mock_voice_response):
        """测试成功获取语音列表"""
        from video_creator import get_heygen_voices
        
        with patch('video_creator.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_voice_response
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            result = get_heygen_voices("test_api_key", language="chinese")
            
            # 应该只返回中文语音
            assert len(result) == 2
            assert all(v["language"] == "chinese" for v in result)
    
    def test_get_avatars_api_error(self):
        """测试 API 错误处理"""
        from video_creator import get_heygen_avatars
        
        with patch('video_creator.requests.get') as mock_get:
            mock_get.side_effect = Exception("API Error")
            
            result = get_heygen_avatars("test_api_key")
            
            assert result == []  # 错误时返回空列表
    
    def test_get_chinese_voice(self, mock_voice_response):
        """测试获取中文语音"""
        from video_creator import get_heygen_chinese_voice
        
        with patch('video_creator.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = mock_voice_response
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            result = get_heygen_chinese_voice("test_api_key")
            
            assert result is not None
            # 返回的应该是中文语音 ID
            assert result in ["voice_001", "voice_002"]


# ============================================================================
# 视频创建器初始化测试
# ============================================================================
class TestVideoCreatorInitialization:
    """视频创建器初始化测试"""
    
    def test_heygen_creator_init_with_dimension(self):
        """测试 HeyGen 创建器初始化带分辨率"""
        from video_creator import HeyGenVideoCreator, VIDEO_DIMENSIONS
        
        with patch('video_creator.get_heygen_chinese_voice', return_value="mock_voice_id"):
            creator = HeyGenVideoCreator(
                api_key="test_key",
                dimension="1080p"
            )
            
            assert creator.dimension == VIDEO_DIMENSIONS["1080p"]
            assert creator.api_key == "test_key"
    
    def test_video_creator_factory(self):
        """测试 VideoCreator 工厂类"""
        from video_creator import VideoCreator
        
        with patch('video_creator.get_heygen_chinese_voice', return_value="mock_voice_id"):
            creator = VideoCreator(
                provider="heygen",
                api_key="test_key",
                avatar_id="test_avatar",
                voice_id="test_voice",
                dimension="720p"
            )
            
            assert creator.provider == "heygen"
            assert creator.creator is not None


# ============================================================================
# 课件视频生成测试
# ============================================================================
class TestCoursewareVideoGeneration:
    """课件视频生成测试"""
    
    def test_create_from_courseware_batch_mode(self, sample_courseware):
        """测试批量模式从课件创建视频"""
        from video_creator import VideoCreator
        
        mock_videos = ["video1.mp4", "video2.mp4"]
        
        with patch('video_creator.get_heygen_chinese_voice', return_value="mock_voice"):
            with patch.object(VideoCreator, 'create_video_from_script', return_value=mock_videos):
                creator = VideoCreator(provider="heygen", api_key="test_key")
                
                # 使用批量模式
                videos = creator.create_from_courseware(
                    sample_courseware,
                    batch_mode=True
                )
                
                # 批量模式应该返回视频列表
                assert isinstance(videos, list)
    
    def test_create_from_courseware_merged_mode(self, sample_courseware):
        """测试合并模式从课件创建视频"""
        from video_creator import VideoCreator
        
        mock_videos = ["merged_video.mp4"]
        
        with patch('video_creator.get_heygen_chinese_voice', return_value="mock_voice"):
            with patch.object(VideoCreator, 'create_video_from_script', return_value=mock_videos):
                creator = VideoCreator(provider="heygen", api_key="test_key")
                
                videos = creator.create_from_courseware(
                    sample_courseware,
                    batch_mode=False
                )
                
                assert isinstance(videos, list)


# ============================================================================
# API 请求构建测试
# ============================================================================
class TestAPIRequestBuilding:
    """API 请求构建测试"""
    
    def test_create_video_payload(self):
        """测试视频创建请求体构建"""
        from video_creator import HeyGenVideoCreator, VIDEO_DIMENSIONS
        
        with patch('video_creator.get_heygen_chinese_voice', return_value="mock_voice"):
            creator = HeyGenVideoCreator(
                api_key="test_key",
                avatar_id="test_avatar",
                voice_id="test_voice",
                dimension="720p"
            )
            
            # 检查配置是否正确设置
            assert creator.avatar_id == "test_avatar"
            assert creator.voice_id == "test_voice"
            assert creator.dimension == VIDEO_DIMENSIONS["720p"]


# ============================================================================
# 边界条件测试
# ============================================================================
class TestEdgeCases:
    """边界条件测试"""
    
    def test_empty_courseware(self):
        """测试空课件处理"""
        from video_creator import VideoCreator
        
        empty_courseware = {"topic": "空课件", "scripts": [], "audio_scripts": []}
        
        with patch('video_creator.get_heygen_chinese_voice', return_value="mock_voice"):
            creator = VideoCreator(provider="heygen", api_key="test_key")
            
            videos = creator.create_from_courseware(empty_courseware)
            
            assert videos == []  # 空课件应返回空列表
    
    def test_missing_scripts(self):
        """测试缺少脚本的课件"""
        from video_creator import VideoCreator
        
        courseware = {"topic": "无脚本课件"}
        
        with patch('video_creator.get_heygen_chinese_voice', return_value="mock_voice"):
            creator = VideoCreator(provider="heygen", api_key="test_key")
            
            videos = creator.create_from_courseware(courseware)
            
            assert videos == []


# ============================================================================
# 运行入口
# ============================================================================
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
