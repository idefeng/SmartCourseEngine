# SmartCourseEngine - 智能课件生成引擎

> 🎓 将教学素材自动转化为结构化课件和数字人讲解视频

## ✨ 功能特性

### 📄 素材解析
- **文档解析**: PDF、Word、PPT 自动转 Markdown (IBM Docling)
- **语音转写**: 音频/视频自动转文字 (Faster Whisper)
- **图片 OCR**: 图片文字识别 (PaddleOCR)

### 📚 知识库管理
- 基于 ChromaDB 的向量知识库
- 支持语义搜索和知识问答
- LangChain 驱动的 RAG 功能

### 🎬 智能生成
- **课件生成**: 自动生成结构化教学大纲和 Word 文档
- **数字人视频**: 一键生成 AI 讲师讲解视频 (HeyGen API)
- **自动练习题**: 基于知识点自动出题

## 🚀 快速开始

### 环境要求
- Python 3.10+
- Windows 10/11

### 安装步骤

```powershell
# 1. 进入项目目录
cd SmartParser

# 2. 运行安装脚本
.\setup_and_run.ps1
```

### 配置 API

首次运行后，在侧边栏配置 API Key：
- **DeepSeek API Key**: 用于 AI 对话和内容生成
- **HeyGen API Key**: 用于数字人视频生成

配置会自动保存到 `config.json`。

## 📁 项目结构

```
SmartParser/
├── app.py                 # Streamlit 主应用
├── main_parser.py         # 文档解析器
├── knowledge_manager.py   # 知识库管理
├── content_generator.py   # 内容生成器
├── video_creator.py       # 视频生成器
├── config.json            # API 配置 (git ignored)
├── requirements.txt       # Python 依赖
├── chroma_db/             # 向量数据库
├── input_materials/       # 输入素材
├── output_markdown/       # 解析输出
├── generated_courseware/  # 生成的课件
├── output_videos/         # 生成的视频
└── docs/                  # 文档
    └── 工作计划.md        # 开发计划
```

## 🎬 视频生成功能

支持以下配置选项：

| 功能 | 描述 |
|------|------|
| 🎭 数字人形象 | 1000+ 可选形象 |
| 🗣️ 语音选择 | 多种中文语音 |
| 📐 分辨率 | 720p / 1080p / 方形 / 竖屏 |
| 📦 批量模式 | 按章节生成独立视频 |

## 📋 开发计划

查看 [工作计划.md](docs/工作计划.md) 了解开发进度和待办任务。

## 📄 许可证

MIT License
