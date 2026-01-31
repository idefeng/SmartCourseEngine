#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SmartCourseEngine - 可视化管理后台
===================================

整合素材解析、知识管理、内容生成的一站式教学资源管理平台。

使用方法: streamlit run app.py

作者: SmartCourseEngine Team
日期: 2026-01-31
"""

import os
import sys
import tempfile
import time
import json
from pathlib import Path
from datetime import datetime

import streamlit as st


# ============================================================================
# 配置文件管理
# ============================================================================
CONFIG_FILE = Path(__file__).parent / "config.json"


def load_config() -> dict:
    """加载配置文件"""
    default_config = {
        "deepseek_api_key": "",
        "heygen_api_key": "",
        "model_name": "deepseek-chat"
    }
    
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved_config = json.load(f)
                # 合并默认配置和保存的配置
                default_config.update(saved_config)
        except Exception:
            pass
    
    return default_config


def save_config(config: dict) -> bool:
    """保存配置到文件"""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False

# 设置页面配置（必须是第一个 Streamlit 命令）
st.set_page_config(
    page_title="SmartCourseEngine",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# 自定义样式
# ============================================================================
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 1rem;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .stat-number {
        font-size: 2.5rem;
        font-weight: bold;
    }
    .stat-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    .knowledge-card {
        background: #f8f9fa;
        border-left: 4px solid #667eea;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0 0.5rem 0.5rem 0;
    }
    .file-list-item {
        background: #fff;
        border: 1px solid #e9ecef;
        padding: 0.75rem 1rem;
        margin: 0.25rem 0;
        border-radius: 0.5rem;
        display: flex;
        align-items: center;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# 初始化模块
# ============================================================================
@st.cache_resource
def init_knowledge_manager():
    """初始化知识管理器"""
    try:
        from knowledge_manager import KnowledgeManager
        base_dir = Path(__file__).parent
        return KnowledgeManager(db_path=str(base_dir / "chroma_db"))
    except Exception as e:
        st.error(f"知识管理器初始化失败: {e}")
        return None


@st.cache_resource
def init_content_generator():
    """初始化内容生成器"""
    try:
        from content_generator import ContentGenerator
        return ContentGenerator()
    except Exception as e:
        st.error(f"内容生成器初始化失败: {e}")
        return None


def get_db_stats():
    """获取数据库统计"""
    km = init_knowledge_manager()
    if km and km.collection:
        return km.collection.count()
    return 0


def get_file_list():
    """获取已解析的文件列表"""
    base_dir = Path(__file__).parent
    output_dir = base_dir / "output_markdown"
    if output_dir.exists():
        return list(output_dir.glob("*.md"))
    return []


# ============================================================================
# 侧边栏
# ============================================================================
def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.markdown("## 🎓 SmartCourseEngine")
        st.markdown("---")
        
        # 系统状态
        st.markdown("### 📊 系统状态")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("知识点总数", get_db_stats())
        with col2:
            st.metric("已解析文件", len(get_file_list()))
        
        st.markdown("---")
        
        # API 配置
        st.markdown("### ⚙️ API 配置")
        
        # 加载配置
        config = load_config()
        
        # DeepSeek API Key
        api_key = st.text_input(
            "DeepSeek API Key",
            value=config.get("deepseek_api_key", ""),
            type="password",
            help="用于知识点提取和内容生成",
            key="deepseek_api_key_input"
        )
        
        # HeyGen API Key
        heygen_key = st.text_input(
            "HeyGen API Key",
            value=config.get("heygen_api_key", ""),
            type="password",
            help="用于生成数字人视频",
            key="heygen_api_key_input"
        )
        
        # 模型选择
        model_options = ["deepseek-chat", "deepseek-coder", "qwen-turbo", "gpt-4o-mini"]
        saved_model = config.get("model_name", "deepseek-chat")
        default_index = model_options.index(saved_model) if saved_model in model_options else 0
        model = st.selectbox("选择模型", model_options, index=default_index, key="model_select")
        
        # 检测配置变更并保存
        config_changed = False
        if api_key != config.get("deepseek_api_key", ""):
            config["deepseek_api_key"] = api_key
            config_changed = True
        if heygen_key != config.get("heygen_api_key", ""):
            config["heygen_api_key"] = heygen_key
            config_changed = True
        if model != config.get("model_name", "deepseek-chat"):
            config["model_name"] = model
            config_changed = True
        
        # 保存配置到文件
        if config_changed:
            if save_config(config):
                st.toast("✓ 配置已保存", icon="💾")
        
        # 设置环境变量
        if api_key:
            os.environ["DEEPSEEK_API_KEY"] = api_key
            st.success("✓ DeepSeek API Key 已配置")
        
        if heygen_key:
            os.environ["HEYGEN_API_KEY"] = heygen_key
            st.success("✓ HeyGen API Key 已配置")
        
        os.environ["MODEL_NAME"] = model
        
        st.markdown("---")
        
        # 关于
        st.markdown("### 💡 关于")
        st.markdown("""
        **SmartCourseEngine** 是一套完整的教学资源智能处理系统：
        
        - 📁 **素材入库**: 解析各类教学素材
        - 🧠 **知识大脑**: 智能检索知识点
        - ✨ **课件生成**: 自动生成课件包
        """)


# ============================================================================
# 素材入库标签页
# ============================================================================
def render_material_tab():
    """渲染素材入库标签页"""
    st.markdown("## 📁 素材入库")
    st.markdown("上传教学素材，系统将自动解析并存入知识库。")
    
    st.markdown("---")
    
    # 文件上传
    uploaded_files = st.file_uploader(
        "上传教学素材",
        type=["pdf", "docx", "doc", "mp4", "mp3", "wav", "jpg", "jpeg", "png"],
        accept_multiple_files=True,
        help="支持 PDF、Word、音视频、图片等格式"
    )
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        process_btn = st.button("🚀 开始解析", type="primary", use_container_width=True)
    
    if uploaded_files and process_btn:
        base_dir = Path(__file__).parent
        input_dir = base_dir / "input_materials"
        input_dir.mkdir(exist_ok=True)
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 保存上传的文件
        for i, uploaded_file in enumerate(uploaded_files):
            progress = (i + 1) / len(uploaded_files)
            progress_bar.progress(progress)
            status_text.text(f"正在处理: {uploaded_file.name}")
            
            # 保存文件
            file_path = input_dir / uploaded_file.name
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            time.sleep(0.5)  # 模拟处理时间
        
        progress_bar.progress(1.0)
        status_text.text("正在解析文件...")
        
        # 调用解析模块
        try:
            # 导入并使用解析器
            from main_parser import DocumentParser, MediaTranscriber, ImageOCR
            import logging
            
            logger = logging.getLogger("SmartParser")
            logger.setLevel(logging.INFO)
            
            output_dir = base_dir / "output_markdown"
            output_dir.mkdir(exist_ok=True)
            
            doc_parser = DocumentParser(logger)
            media_transcriber = MediaTranscriber(logger)
            image_ocr = ImageOCR(logger)
            
            success_count = 0
            
            for uploaded_file in uploaded_files:
                file_path = input_dir / uploaded_file.name
                
                # 根据文件类型选择解析器
                suffix = file_path.suffix.lower()
                content = None
                
                if suffix in ['.pdf', '.docx', '.doc']:
                    content = doc_parser.parse(file_path)
                elif suffix in ['.mp4', '.avi', '.mkv', '.mp3', '.wav', '.m4a']:
                    content = media_transcriber.transcribe(file_path)
                elif suffix in ['.jpg', '.jpeg', '.png', '.bmp']:
                    content = image_ocr.recognize(file_path)
                
                if content:
                    output_path = output_dir / f"{file_path.stem}.md"
                    output_path.write_text(content, encoding='utf-8')
                    success_count += 1
            
            st.success(f"✓ 成功解析 {len(uploaded_files)} 个文件！")
            
            # 自动入库
            km = init_knowledge_manager()
            if km:
                status_text.text("正在存入知识库...")
                km.process_documents(str(output_dir), extract_knowledge=False)
                st.success("✓ 已存入知识库！")
            
        except Exception as e:
            st.error(f"解析失败: {e}")
        
        status_text.empty()
    
    st.markdown("---")
    
    # 已解析文件列表
    st.markdown("### 📄 已解析文件")
    
    files = get_file_list()
    
    if files:
        for f in files:
            col1, col2, col3 = st.columns([5, 2, 1])
            with col1:
                st.markdown(f"📄 **{f.name}**")
            with col2:
                st.caption(f"{f.stat().st_size / 1024:.1f} KB")
            with col3:
                if st.button("👁️", key=f"view_{f.name}", help="预览"):
                    st.session_state.preview_file = f
        
        # 预览文件内容
        if "preview_file" in st.session_state:
            st.markdown("---")
            st.markdown(f"### 预览: {st.session_state.preview_file.name}")
            content = st.session_state.preview_file.read_text(encoding='utf-8')
            st.markdown(content[:2000] + ("..." if len(content) > 2000 else ""))
    else:
        st.info("暂无已解析的文件")


# ============================================================================
# 知识大脑标签页
# ============================================================================
def render_knowledge_tab():
    """渲染知识大脑标签页"""
    st.markdown("## 🧠 知识大脑")
    st.markdown("搜索和浏览知识库中的内容。")
    
    st.markdown("---")
    
    # 搜索框
    query = st.text_input(
        "🔍 搜索知识点",
        placeholder="输入关键词或问题，如：托育培训项目的实施流程",
        help="基于语义检索，支持自然语言查询"
    )
    
    col1, col2 = st.columns([1, 5])
    with col1:
        top_k = st.selectbox("返回数量", [3, 5, 10], index=0)
    
    if query:
        km = init_knowledge_manager()
        
        if km:
            with st.spinner("正在检索..."):
                results = km.query_knowledge(query, top_k=top_k)
            
            if results:
                st.success(f"找到 {len(results)} 个相关知识点")
                
                for r in results:
                    with st.expander(
                        f"#{r['rank']} {r.get('knowledge_name', '未命名')} "
                        f"(相关度: {r.get('relevance_score', 0):.1%})",
                        expanded=r['rank'] == 1
                    ):
                        st.markdown(f"**来源:** {r.get('source', '未知')}")
                        st.markdown(f"**类别:** {r.get('category', '未分类')}")
                        st.markdown("---")
                        st.markdown(r.get('content', ''))
            else:
                st.warning("未找到相关知识点")
        else:
            st.error("知识库未初始化")
    
    st.markdown("---")
    
    # 知识图谱预览
    st.markdown("### 📚 已入库文件")
    
    files = get_file_list()
    
    if files:
        cols = st.columns(3)
        for i, f in enumerate(files):
            with cols[i % 3]:
                st.markdown(f"""
                <div class="knowledge-card">
                    <strong>📄 {f.stem}</strong><br>
                    <small style="color: #6c757d;">{f.stat().st_size / 1024:.1f} KB</small>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("知识库为空，请先上传素材")


# ============================================================================
# 课件生成标签页
# ============================================================================
def render_generate_tab():
    """渲染课件生成标签页"""
    st.markdown("## ✨ 课件生成")
    st.markdown("输入主题，自动生成完整的教学课件包。")
    
    st.markdown("---")
    
    # 检查 API Key
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key or api_key == "your-deepseek-api-key-here":
        st.warning("⚠️ 请先在侧边栏配置 API Key")
        return
    
    # 主题输入
    topic = st.text_input(
        "📝 课程主题",
        placeholder="例如：托育项目风险管理",
        help="输入您想要生成课件的主题"
    )
    
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        generate_btn = st.button("🚀 生成课件", type="primary", use_container_width=True)
    
    if topic and generate_btn:
        try:
            # 清除缓存，重新初始化（使用新的 API Key）
            st.cache_resource.clear()
            
            generator = init_content_generator()
            
            if not generator:
                st.error("内容生成器初始化失败")
                return
            
            # 生成课件
            with st.spinner("正在生成课件，请稍候..."):
                progress_text = st.empty()
                
                progress_text.text("检索相关知识点...")
                courseware = generator.generate_courseware(topic)
            
            progress_text.empty()
            
            if not courseware.get("outline"):
                st.error("课件生成失败，请检查 API 配置")
                return
            
            st.success("✓ 课件生成完成！")
            
            # 预览大纲
            st.markdown("### 📋 课程大纲")
            
            outline = courseware.get("outline", {})
            
            if outline:
                st.markdown(f"**{outline.get('title', topic)}**")
                
                sections = [
                    outline.get("introduction", {}),
                    outline.get("core_content", {}),
                    outline.get("case_analysis", {}),
                    outline.get("summary", {})
                ]
                
                for section in sections:
                    if section:
                        st.markdown(f"**{section.get('title', '')}**")
                        for point in section.get("points", []):
                            st.markdown(f"  - {point}")
            
            # 预览题库
            st.markdown("### 📝 练习题库预览")
            
            quizzes = courseware.get("quizzes", [])
            
            if quizzes:
                for i, quiz in enumerate(quizzes, 1):
                    with st.expander(f"第{i}组题目"):
                        # 单选题
                        sc = quiz.get("single_choice", {})
                        if sc:
                            st.markdown("**【单选题】**")
                            st.markdown(sc.get("question", ""))
                            for key, val in sc.get("options", {}).items():
                                st.markdown(f"  {key}. {val}")
                            st.info(f"答案: {sc.get('answer', '')}")
                        
                        # 判断题
                        tf = quiz.get("true_false", {})
                        if tf:
                            st.markdown("**【判断题】**")
                            st.markdown(tf.get("question", ""))
                            st.info(f"答案: {'正确' if tf.get('answer') else '错误'}")
            
            # 导出 Word
            st.markdown("### 📥 下载课件")
            
            base_dir = Path(__file__).parent
            output_dir = base_dir / "generated_courseware"
            output_dir.mkdir(exist_ok=True)
            
            docx_path = generator.export_to_word(courseware, str(output_dir))
            
            col_dl1, col_dl2 = st.columns(2)
            
            with col_dl1:
                with open(docx_path, "rb") as f:
                    st.download_button(
                        label="📄 下载 Word 文档",
                        data=f.read(),
                        file_name=Path(docx_path).name,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True
                    )
            
            # 保存课件数据用于视频生成
            st.session_state.last_courseware = courseware
            
            st.success(f"文件已保存: {docx_path}")
            
        except Exception as e:
            st.error(f"生成失败: {e}")
            import traceback
            st.code(traceback.format_exc())
    
    # 视频生成区域
    st.markdown("---")
    st.markdown("### 🎬 生成数字人视频")
    
    # 检查 HeyGen API Key
    heygen_key = os.getenv("HEYGEN_API_KEY", "")
    
    if not heygen_key or heygen_key == "your-heygen-api-key-here":
        st.warning("⚠️ 请先配置 HeyGen API Key 才能生成视频")
        st.code("$env:HEYGEN_API_KEY = 'your-heygen-api-key'")
    else:
        st.success("✓ HeyGen API Key 已配置")
        
        # 视频配置选项
        with st.expander("⚙️ 视频生成配置", expanded=False):
            st.markdown("#### 数字人形象")
            
            # 获取形象列表（带缓存）
            if "heygen_avatars" not in st.session_state:
                try:
                    from video_creator import get_heygen_avatars
                    st.session_state.heygen_avatars = get_heygen_avatars(heygen_key)
                except Exception as e:
                    st.session_state.heygen_avatars = []
                    st.warning(f"获取形象列表失败: {e}")
            
            avatars = st.session_state.heygen_avatars
            if avatars:
                avatar_names = [f"{a['name']} ({a['gender']})" for a in avatars]
                avatar_ids = [a['avatar_id'] for a in avatars]
                
                # 默认选择第一个
                default_idx = 0
                for i, aid in enumerate(avatar_ids):
                    if "Kristin" in aid:  # 优先选择 Kristin
                        default_idx = i
                        break
                
                selected_avatar_idx = st.selectbox(
                    "选择数字人形象",
                    range(len(avatar_names)),
                    index=default_idx,
                    format_func=lambda i: avatar_names[i],
                    help="选择视频中出现的数字人形象"
                )
                selected_avatar_id = avatar_ids[selected_avatar_idx]
                
                # 显示预览图
                if avatars[selected_avatar_idx].get("preview_url"):
                    st.image(avatars[selected_avatar_idx]["preview_url"], width=200)
            else:
                selected_avatar_id = "Kristin_public_2_20240108"
                st.info("使用默认形象: Kristin")
            
            st.markdown("#### 语音设置")
            
            # 获取语音列表（带缓存）
            if "heygen_voices" not in st.session_state:
                try:
                    from video_creator import get_heygen_voices
                    st.session_state.heygen_voices = get_heygen_voices(heygen_key, "chinese")
                except Exception as e:
                    st.session_state.heygen_voices = []
                    st.warning(f"获取语音列表失败: {e}")
            
            voices = st.session_state.heygen_voices
            if voices:
                voice_names = [f"{v['name']} ({v['gender']})" for v in voices]
                voice_ids = [v['voice_id'] for v in voices]
                
                selected_voice_idx = st.selectbox(
                    "选择语音",
                    range(len(voice_names)),
                    index=0,
                    format_func=lambda i: voice_names[i],
                    help="选择视频旁白的语音"
                )
                selected_voice_id = voice_ids[selected_voice_idx]
            else:
                selected_voice_id = "auto"
                st.info("将自动选择中文语音")
            
            st.markdown("#### 视频分辨率")
            
            resolution_options = ["720p", "1080p", "方形 (1:1)", "竖屏 (9:16)"]
            selected_resolution = st.selectbox(
                "选择分辨率",
                resolution_options,
                index=0,
                help="720p 适合网页播放，1080p 适合高清展示，方形适合社交媒体，竖屏适合手机观看"
            )
            
            # 刷新按钮
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 刷新形象列表"):
                    if "heygen_avatars" in st.session_state:
                        del st.session_state.heygen_avatars
                    st.rerun()
            with col2:
                if st.button("🔄 刷新语音列表"):
                    if "heygen_voices" in st.session_state:
                        del st.session_state.heygen_voices
                    st.rerun()
        
        # 保存配置到 session_state
        if "heygen_avatars" in st.session_state and st.session_state.heygen_avatars:
            st.session_state.video_config = {
                "avatar_id": selected_avatar_id,
                "voice_id": selected_voice_id,
                "dimension": selected_resolution
            }
        else:
            st.session_state.video_config = {
                "avatar_id": "Kristin_public_2_20240108",
                "voice_id": "auto",
                "dimension": "720p"
            }
    
    # 检查是否有课件数据
    if "last_courseware" in st.session_state:
        courseware = st.session_state.last_courseware
        
        # 显示课件信息卡片
        scripts = courseware.get("audio_scripts", []) or courseware.get("scripts", [])
        script_count = len(scripts)
        
        # 课件信息
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1rem; border-radius: 0.5rem; color: white; margin-bottom: 1rem;">
            <strong>📄 当前课件:</strong> {courseware.get('topic', '未命名')}<br>
            <strong>📝 脚本章节:</strong> {script_count} 个
            {f"<br><small>章节: {', '.join([s.get('section', '未命名') for s in scripts[:5]])}{' ...' if len(scripts) > 5 else ''}</small>" if scripts else ""}
        </div>
        """, unsafe_allow_html=True)
        
        # 生成模式选择
        col1, col2 = st.columns([1, 1])
        with col1:
            batch_mode = st.toggle(
                "📦 批量模式",
                value=False,
                help="开启后每个章节生成独立视频，关闭则合并为一个视频"
            )
        with col2:
            if batch_mode:
                st.caption(f"将生成 {script_count} 个独立视频")
            else:
                st.caption("将合并为 1 个完整视频")
        
        # 生成按钮
        if st.button("🎬 开始生成数字人视频", type="primary", use_container_width=True):
            if not heygen_key or heygen_key == "your-heygen-api-key-here":
                st.error("请先配置 HeyGen API Key")
                return
            
            try:
                from video_creator import VideoCreator
                import time as time_module
                
                # 获取视频配置
                video_config = st.session_state.get("video_config", {})
                
                # 显式传入 API 密钥和配置
                video_creator = VideoCreator(
                    provider="heygen", 
                    api_key=heygen_key,
                    avatar_id=video_config.get("avatar_id"),
                    voice_id=video_config.get("voice_id"),
                    dimension=video_config.get("dimension", "720p")
                )
                
                # 创建进度显示容器
                progress_container = st.container()
                with progress_container:
                    st.markdown("### 🎬 视频生成进度")
                    progress_bar = st.progress(0)
                    
                    # 状态信息显示
                    col_status1, col_status2, col_status3 = st.columns(3)
                    with col_status1:
                        current_section = st.empty()
                        current_section.metric("当前章节", "准备中...")
                    with col_status2:
                        current_status = st.empty()
                        current_status.metric("状态", "初始化")
                    with col_status3:
                        elapsed_time = st.empty()
                        elapsed_time.metric("已用时间", "0s")
                    
                    log_area = st.empty()
                
                start_time = time_module.time()
                logs = []
                
                def update_progress(status, elapsed, part=1, total=1, section_name=""):
                    # 更新进度条
                    progress = part / total if total > 0 else 0
                    progress_bar.progress(progress, text=f"进度: {part}/{total}")
                    
                    # 更新状态指标
                    current_section.metric("当前章节", section_name or f"片段 {part}")
                    current_status.metric("状态", status)
                    
                    total_elapsed = int(time_module.time() - start_time)
                    elapsed_time.metric("已用时间", f"{total_elapsed}s")
                    
                    # 记录日志
                    log_entry = f"[{total_elapsed}s] 章节 {part}/{total} ({section_name}): {status}"
                    logs.append(log_entry)
                    # 只显示最近5条日志
                    log_area.code("\n".join(logs[-5:]), language=None)
                
                with st.spinner("正在生成数字人视频，请稍候（可能需要几分钟）..."):
                    videos = video_creator.create_from_courseware(
                        courseware,
                        progress_callback=update_progress,
                        batch_mode=batch_mode
                    )
                
                # 计算总耗时
                total_time = int(time_module.time() - start_time)
                
                # 清除进度显示
                progress_container.empty()
                
                if videos:
                    # 成功消息
                    st.success(f"✅ 成功生成 {len(videos)} 个视频！总耗时: {total_time}s")
                    
                    # 视频展示区
                    st.markdown("### 📹 生成的视频")
                    
                    for idx, video_path in enumerate(videos):
                        with st.expander(f"🎬 {Path(video_path).name}", expanded=(idx == 0)):
                            # 视频预览
                            st.video(video_path)
                            
                            # 视频信息
                            file_size = Path(video_path).stat().st_size / (1024 * 1024)  # MB
                            st.caption(f"文件大小: {file_size:.2f} MB")
                            
                            # 下载按钮
                            with open(video_path, "rb") as vf:
                                st.download_button(
                                    label=f"📥 下载视频",
                                    data=vf.read(),
                                    file_name=Path(video_path).name,
                                    mime="video/mp4",
                                    use_container_width=True,
                                    key=f"download_{idx}"
                                )
                    
                    # 批量下载提示
                    if len(videos) > 1:
                        st.info(f"💡 所有视频已保存到: output_videos 文件夹")
                else:
                    st.warning("⚠️ 未生成任何视频，请检查 API 配置和网络连接")
                    
            except Exception as e:
                st.error(f"❌ 视频生成失败: {e}")
                import traceback
                with st.expander("查看错误详情"):
                    st.code(traceback.format_exc())
    else:
        st.info("📝 请先生成课件，然后才能一键生成视频")
    
    # 质量评估区域
    st.markdown("---")
    st.markdown("### 📊 课件质量评估")
    
    if "last_courseware" in st.session_state:
        courseware = st.session_state.last_courseware
        
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); 
                    padding: 1rem; border-radius: 0.5rem; color: white; margin-bottom: 1rem;">
            <strong>📄 待评估课件:</strong> {courseware.get('topic', '未命名')}
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🔍 开始质量评估", type="secondary", use_container_width=True):
            try:
                from quality_evaluator import CoursewareEvaluator
                
                evaluator = CoursewareEvaluator()
                
                with st.spinner("正在评估课件质量..."):
                    report = evaluator.evaluate(courseware)
                
                # 保存报告到 session_state
                st.session_state.quality_report = report
                
                # 显示评估结果
                # 总分和等级
                grade_colors = {"A": "green", "B": "blue", "C": "orange", "D": "red", "F": "red"}
                grade_color = grade_colors.get(report.grade, "gray")
                
                col_score, col_grade = st.columns([2, 1])
                with col_score:
                    st.metric(
                        label="综合评分",
                        value=f"{report.overall_score:.1f} / 100",
                        delta=f"{'优秀' if report.overall_score >= 80 else '良好' if report.overall_score >= 70 else '待提升'}"
                    )
                with col_grade:
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, {'#27ae60' if report.grade in ['A', 'B'] else '#f39c12' if report.grade == 'C' else '#e74c3c'} 0%, 
                                {'#2ecc71' if report.grade in ['A', 'B'] else '#f1c40f' if report.grade == 'C' else '#c0392b'} 100%); 
                                padding: 1.5rem; border-radius: 0.5rem; text-align: center; color: white;">
                        <div style="font-size: 2rem; font-weight: bold;">{report.grade}</div>
                        <div>等级</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown(f"**📝 评估总结:** {report.summary}")
                
                # 详细评分
                with st.expander("📊 详细评分", expanded=True):
                    for s in report.scores:
                        score_pct = s.score / 100
                        bar_color = "green" if s.score >= 80 else "orange" if s.score >= 60 else "red"
                        
                        col1, col2, col3 = st.columns([3, 1, 4])
                        with col1:
                            st.markdown(f"**{s.criterion}** ({s.weight*100:.0f}%)")
                        with col2:
                            st.markdown(f"**{s.score:.0f}**")
                        with col3:
                            st.progress(score_pct, text=s.details)
                
                # 优势与建议
                col_strength, col_weakness = st.columns(2)
                
                with col_strength:
                    if report.strengths:
                        st.markdown("#### ✅ 优势")
                        for s in report.strengths:
                            st.markdown(f"- {s}")
                
                with col_weakness:
                    if report.weaknesses:
                        st.markdown("#### ⚠️ 待改进")
                        for w in report.weaknesses:
                            st.markdown(f"- {w}")
                
                # 改进建议
                if report.recommendations:
                    with st.expander("💡 改进建议"):
                        for r in report.recommendations:
                            st.markdown(f"- {r}")
                
                # 导出报告
                st.markdown("---")
                if st.button("📥 导出评估报告", use_container_width=True):
                    base_dir = Path(__file__).parent
                    output_dir = base_dir / "generated_courseware"
                    output_dir.mkdir(exist_ok=True)
                    
                    safe_topic = report.topic.replace("/", "_").replace("\\", "_")
                    report_path = output_dir / f"质量评估_{safe_topic}.md"
                    
                    report_content = evaluator.export_report(report, str(report_path))
                    st.success(f"✅ 报告已导出: {report_path.name}")
                    
                    with open(report_path, "r", encoding="utf-8") as f:
                        st.download_button(
                            label="📄 下载评估报告",
                            data=f.read(),
                            file_name=report_path.name,
                            mime="text/markdown",
                            use_container_width=True
                        )
                
            except Exception as e:
                st.error(f"❌ 评估失败: {e}")
                import traceback
                with st.expander("查看错误详情"):
                    st.code(traceback.format_exc())
    else:
        st.info("📝 请先生成课件，然后才能进行质量评估")


# ============================================================================
# 互动学习标签页
# ============================================================================
def render_interactive_learning_tab():
    """渲染互动学习标签页"""
    st.markdown("### 🎮 互动学习模式")
    st.markdown("体验\"学-测-补\"自适应学习闭环：视频学习 → 知识检测 → 智能补漏")
    
    # 初始化交互引擎
    try:
        from interaction_engine import (
            InteractionEngine, 
            LearningSession, 
            session_to_dict, 
            dict_to_session,
            AnswerResult
        )
        engine = InteractionEngine()
    except Exception as e:
        st.error(f"交互引擎初始化失败: {e}")
        return
    
    # 检查是否有课件
    if "last_courseware" not in st.session_state:
        st.warning("⚠️ 请先在「课件生成」标签页生成课件")
        return
    
    courseware = st.session_state.last_courseware
    topic = courseware.get("topic", "未命名课程")
    
    # 初始化学习会话
    if "learning_session" not in st.session_state:
        session = engine.create_session(topic)
        st.session_state.learning_session = session_to_dict(session)
    
    session = dict_to_session(st.session_state.learning_session)
    
    # 课程信息卡
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 1.5rem; border-radius: 1rem; color: white; margin-bottom: 1rem;">
        <h3 style="margin: 0;">📚 {topic}</h3>
        <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">
            进度: 第 {session.current_section_index + 1} 节 / 共 {len(courseware.get('scripts', []))} 节
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # 章节选择
    scripts = courseware.get("scripts", [])
    section_names = [s.get("section", f"第{i+1}节") for i, s in enumerate(scripts)]
    
    # 检查是否有章节
    if not section_names:
        st.warning("⚠️ 当前课件没有章节内容，请先生成完整的课件")
        return
    
    col1, col2 = st.columns([3, 1])
    with col1:
        # 确保 index 在有效范围内
        default_index = min(session.current_section_index, len(section_names) - 1)
        selected_section = st.selectbox(
            "选择章节",
            range(len(section_names)),
            format_func=lambda x: f"{'🔓' if x in session.unlocked_sections else '🔒'} {section_names[x]}",
            index=default_index
        )
    
    with col2:
        if selected_section not in session.unlocked_sections:
            st.warning("🔒 未解锁")
        else:
            st.success("🔓 已解锁")
    
    if selected_section not in session.unlocked_sections:
        st.info("💡 完成前面章节的练习题才能解锁此章节")
        return
    
    # 视频/内容区域
    st.markdown("---")
    st.markdown(f"### 📖 {section_names[selected_section]}")
    
    # 显示讲解内容
    if selected_section < len(scripts):
        script_content = scripts[selected_section].get("content", "")
        
        with st.expander("📝 讲解内容", expanded=True):
            st.markdown(script_content)
        
        # 检查视频
        if "generated_videos" in st.session_state:
            videos = st.session_state.generated_videos
            if selected_section < len(videos) and videos[selected_section]:
                st.video(videos[selected_section])
    
    # 练习题区域
    st.markdown("---")
    st.markdown("### ✍️ 知识检测")
    
    quiz = engine.get_quiz_for_section(courseware, selected_section)
    
    if not quiz:
        st.info("本节暂无练习题")
        # 自动解锁下一节
        if selected_section + 1 not in session.unlocked_sections:
            session.unlocked_sections.append(selected_section + 1)
            st.session_state.learning_session = session_to_dict(session)
        return
    
    knowledge_point = quiz.get("knowledge_point", "")
    st.markdown(f"**知识点**: {knowledge_point}")
    
    # 答题状态键
    quiz_key = f"quiz_{selected_section}"
    
    # 检查是否已答过（本会话内）
    answered_key = f"answered_{quiz_key}"
    
    if answered_key not in st.session_state:
        st.session_state[answered_key] = False
        st.session_state[f"result_{quiz_key}"] = None
    
    # 单选题
    single_choice = quiz.get("single_choice", {})
    if single_choice:
        st.markdown("#### 📋 单选题")
        st.markdown(single_choice.get("question", ""))
        
        options = single_choice.get("options", {})
        option_list = [f"{k}. {v}" for k, v in options.items()]
        
        if not st.session_state[answered_key]:
            user_answer = st.radio(
                "请选择答案:",
                list(options.keys()),
                format_func=lambda x: f"{x}. {options[x]}",
                key=f"radio_{quiz_key}"
            )
            
            if st.button("✅ 提交答案", key=f"submit_{quiz_key}", type="primary"):
                is_correct, attempt = engine.check_answer(
                    session, quiz, user_answer, "single_choice"
                )
                
                st.session_state[answered_key] = True
                st.session_state[f"result_{quiz_key}"] = {
                    "is_correct": is_correct,
                    "user_answer": user_answer,
                    "correct_answer": single_choice.get("answer"),
                    "explanation": single_choice.get("explanation", "")
                }
                
                # 如果答错，生成错因分析
                if not is_correct:
                    error_analysis = engine.analyze_error(quiz, user_answer, "single_choice")
                    st.session_state[f"result_{quiz_key}"]["error_analysis"] = error_analysis
                
                # 更新会话
                st.session_state.learning_session = session_to_dict(session)
                st.rerun()
        
        else:
            # 显示结果
            result = st.session_state[f"result_{quiz_key}"]
            
            if result["is_correct"]:
                st.success("🎉 回答正确！")
                st.markdown(f"**解析**: {result['explanation']}")
                
                # 解锁下一节
                if selected_section + 1 not in session.unlocked_sections:
                    session.unlocked_sections.append(selected_section + 1)
                    st.session_state.learning_session = session_to_dict(session)
                    st.balloons()
                    st.success(f"🔓 已解锁下一节: {section_names[selected_section + 1] if selected_section + 1 < len(section_names) else '课程完成！'}")
            else:
                st.error(f"❌ 回答错误 (正确答案: {result['correct_answer']})")
                
                # 显示错因分析
                if "error_analysis" in result:
                    st.markdown("#### 🔍 智能错因分析")
                    st.info(result["error_analysis"])
                
                # 检查是否需要补漏
                if engine.needs_remediation(session, knowledge_point):
                    st.markdown("#### 📚 个性化补漏")
                    st.warning("检测到您在此知识点连续答错，为您推荐补充学习材料：")
                    
                    # 获取补漏内容
                    error_attempts = [
                        a for a in session.quiz_attempts 
                        if a.knowledge_point == knowledge_point and a.result == AnswerResult.INCORRECT
                    ]
                    remediation = engine.get_remediation_content(knowledge_point, error_attempts)
                    
                    with st.expander("📖 补充学习材料", expanded=True):
                        st.markdown(remediation.content)
                        st.caption(f"来源: {remediation.source}")
                    
                    # 标记已展示补漏
                    if knowledge_point in session.knowledge_progress:
                        session.knowledge_progress[knowledge_point].remediation_shown = True
                        st.session_state.learning_session = session_to_dict(session)
            
            # 重试按钮
            if st.button("🔄 重新作答", key=f"retry_{quiz_key}"):
                st.session_state[answered_key] = False
                st.session_state[f"result_{quiz_key}"] = None
                st.rerun()
    
    # 学习进度概览
    st.markdown("---")
    st.markdown("### 📈 本次学习进度")
    
    progress_cols = st.columns(4)
    with progress_cols[0]:
        total_attempts = len(session.quiz_attempts)
        st.metric("答题次数", total_attempts)
    
    with progress_cols[1]:
        correct_count = sum(1 for a in session.quiz_attempts if a.result == AnswerResult.CORRECT)
        st.metric("正确数", correct_count)
    
    with progress_cols[2]:
        accuracy = correct_count / total_attempts * 100 if total_attempts > 0 else 0
        st.metric("正确率", f"{accuracy:.0f}%")
    
    with progress_cols[3]:
        unlocked = len(session.unlocked_sections)
        total = len(scripts)
        st.metric("解锁进度", f"{unlocked}/{total}")


# ============================================================================
# 学习报告标签页
# ============================================================================
def render_learning_report_tab():
    """渲染学习报告标签页"""
    st.markdown("### 📊 学习数据看板")
    st.markdown("查看学习表现分析、知识点掌握情况，生成个性化学习诊断书")
    
    # 检查是否有学习会话
    if "learning_session" not in st.session_state:
        st.info("📝 暂无学习记录，请先在「互动学习」标签页进行学习")
        return
    
    try:
        from interaction_engine import (
            InteractionEngine, 
            dict_to_session, 
            LearningReportPDF,
            AnswerResult
        )
        engine = InteractionEngine()
        session = dict_to_session(st.session_state.learning_session)
    except Exception as e:
        st.error(f"加载学习数据失败: {e}")
        return
    
    # 生成报告
    report = engine.generate_learning_report(session)
    summary = report.get("summary", {})
    
    # 总体统计卡片
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); 
                padding: 1.5rem; border-radius: 1rem; color: white; margin-bottom: 1rem;">
        <h3 style="margin: 0;">📚 {report.get('course_topic', '课程学习')}</h3>
        <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">
            学习时长: {summary.get('total_duration_minutes', 0):.1f} 分钟 | 
            完成章节: {summary.get('sections_completed', 0)} 节
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # 核心指标
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "总答题数",
            summary.get("total_questions", 0),
            help="本次学习回答的题目总数"
        )
    
    with col2:
        st.metric(
            "正确数",
            summary.get("correct_answers", 0),
            delta=f"+{summary.get('correct_answers', 0)}" if summary.get('correct_answers', 0) > 0 else None
        )
    
    with col3:
        accuracy = summary.get("overall_accuracy", 0) * 100
        st.metric(
            "正确率",
            f"{accuracy:.0f}%",
            delta="优秀" if accuracy >= 80 else "良好" if accuracy >= 60 else "待提升"
        )
    
    with col4:
        st.metric(
            "学习时长",
            f"{summary.get('total_duration_minutes', 0):.0f}min"
        )
    
    st.markdown("---")
    
    # 知识点掌握情况
    st.markdown("### 📖 知识点掌握情况")
    
    knowledge_breakdown = report.get("knowledge_breakdown", [])
    
    if knowledge_breakdown:
        for ks in knowledge_breakdown:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                accuracy = ks.get("accuracy_rate", 0)
                mastery = ks.get("mastery_level", 0)
                
                # 进度条颜色
                if mastery >= 0.8:
                    bar_text = "掌握良好 ✅"
                elif mastery >= 0.6:
                    bar_text = "基本掌握 📖"
                else:
                    bar_text = "需要加强 ⚠️"
                
                st.markdown(f"**{ks.get('knowledge_point', '未知')}**")
                st.progress(mastery, text=bar_text)
            
            with col2:
                st.markdown(f"正确率: **{accuracy * 100:.0f}%**")
                st.caption(f"练习 {ks.get('total_attempts', 0)} 次")
    else:
        st.info("暂无知识点数据")
    
    st.markdown("---")
    
    # 薄弱点和建议
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### ⚠️ 薄弱知识点")
        weak_points = report.get("weak_points", [])
        if weak_points:
            for wp in weak_points:
                st.markdown(f"- 📌 {wp}")
        else:
            st.success("🎉 没有明显薄弱点，继续保持！")
    
    with col2:
        st.markdown("### ✅ 优势知识点")
        strong_points = report.get("strong_points", [])
        if strong_points:
            for sp in strong_points:
                st.markdown(f"- ⭐ {sp}")
        else:
            st.info("继续学习，积累更多优势知识点")
    
    st.markdown("---")
    
    # 学习建议
    st.markdown("### 💡 个性化学习建议")
    recommendations = report.get("recommendations", [])
    for rec in recommendations:
        st.info(rec)
    
    st.markdown("---")
    
    # 导出报告
    st.markdown("### 📥 导出学习诊断书")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📄 生成 PDF 报告", type="primary", use_container_width=True):
            try:
                pdf_generator = LearningReportPDF()
                
                base_dir = Path(__file__).parent
                output_dir = base_dir / "generated_courseware"
                output_dir.mkdir(exist_ok=True)
                
                safe_topic = report.get("course_topic", "学习报告").replace("/", "_").replace("\\", "_")
                pdf_path = output_dir / f"学习诊断书_{safe_topic}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
                
                result = pdf_generator.generate(report, str(pdf_path))
                
                if result:
                    st.success(f"✅ PDF 报告已生成!")
                    
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            label="📥 下载 PDF 报告",
                            data=f.read(),
                            file_name=pdf_path.name,
                            mime="application/pdf",
                            use_container_width=True
                        )
                else:
                    st.warning("PDF 生成功能需要安装 reportlab 库")
                    st.code("pip install reportlab")
            except Exception as e:
                st.error(f"PDF 生成失败: {e}")
    
    with col2:
        # JSON 导出
        if st.button("📋 导出 JSON 数据", use_container_width=True):
            json_str = json.dumps(report, ensure_ascii=False, indent=2)
            st.download_button(
                label="📥 下载 JSON",
                data=json_str,
                file_name=f"学习报告_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json",
                use_container_width=True
            )


# ============================================================================
# 知识图谱标签页
# ============================================================================
def render_knowledge_graph_tab():
    """渲染知识图谱标签页"""
    st.markdown("### 🗺️ 知识图谱可视化")
    st.markdown("以图形方式展示知识点之间的逻辑关联，支持交互编辑")
    
    # 检查是否有课件
    if "last_courseware" not in st.session_state:
        st.warning("⚠️ 请先在「课件生成」标签页生成课件")
        return
    
    # 初始化专家验证器
    try:
        from expert_validator import (
            ExpertValidator,
            KnowledgeGraph,
            graph_to_dict,
            dict_to_graph
        )
        validator = ExpertValidator()
    except Exception as e:
        st.error(f"专家验证器初始化失败: {e}")
        return
    
    courseware = st.session_state.last_courseware
    topic = courseware.get("topic", "知识图谱")
    
    # 构建或获取知识图谱
    if "knowledge_graph" not in st.session_state:
        with st.spinner("🔄 正在构建知识图谱..."):
            graph = validator.build_knowledge_graph(courseware)
            st.session_state.knowledge_graph = graph_to_dict(graph)
    
    graph = dict_to_graph(st.session_state.knowledge_graph)
    
    # 图谱信息卡
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); 
                padding: 1.5rem; border-radius: 1rem; color: #333; margin-bottom: 1rem;">
        <h3 style="margin: 0;">📚 {topic}</h3>
        <p style="margin: 0.5rem 0 0 0;">
            节点数: {len(graph.nodes)} | 关联数: {len(graph.edges)}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # 尝试使用 streamlit-agraph
    try:
        from streamlit_agraph import agraph, Node, Edge, Config
        
        # 转换为 agraph 格式
        nodes_data, edges_data = graph.to_agraph_data()
        
        nodes = [
            Node(
                id=n["id"],
                label=n["label"],
                title=n.get("title", ""),
                color=n.get("color", "#97C2FC"),
                size=n.get("size", 25)
            )
            for n in nodes_data
        ]
        
        edges = [
            Edge(
                source=e["source"],
                target=e["target"],
                label=e.get("label", ""),
                width=e.get("width", 2),
                color=e.get("color", "#888888")
            )
            for e in edges_data
        ]
        
        config = Config(
            width=800,
            height=500,
            directed=True,
            physics=True,
            hierarchical=False,
            nodeHighlightBehavior=True,
            highlightColor="#F7A7A6",
            collapsible=True
        )
        
        # 渲染图谱
        selected_node = agraph(nodes=nodes, edges=edges, config=config)
        
        # 显示选中节点信息
        if selected_node:
            st.markdown("---")
            st.markdown(f"**选中节点**: {selected_node}")
            
            # 查找节点详情
            for node in graph.nodes:
                if node.node_id == selected_node:
                    st.markdown(f"**类别**: {node.category}")
                    st.markdown(f"**内容**: {node.content}")
                    st.markdown(f"**重要度**: {node.importance:.0%}")
                    break
        
    except ImportError:
        st.warning("⚠️ streamlit-agraph 未安装，显示简化版本")
        st.code("pip install streamlit-agraph")
        
        # 简化显示
        st.markdown("#### 📊 知识节点列表")
        for node in graph.nodes:
            with st.expander(f"{'⭐' if node.importance > 0.7 else '📌'} {node.label}"):
                st.markdown(f"**类别**: {node.category}")
                st.markdown(f"**内容**: {node.content}")
                st.markdown(f"**重要度**: {node.importance:.0%}")
        
        st.markdown("#### 🔗 知识关联")
        for edge in graph.edges:
            if not edge.is_blocked:
                st.markdown(f"- {edge.source_id} → *{edge.relation}* → {edge.target_id}")
    
    st.markdown("---")
    
    # 边管理
    st.markdown("### ⚙️ 关联管理")
    st.markdown("您可以禁用或调整知识点之间的关联权重")
    
    if graph.edges:
        edge_options = [
            f"{e.source_id} → {e.target_id} ({e.relation})"
            for e in graph.edges
        ]
        
        selected_edge_idx = st.selectbox(
            "选择关联",
            range(len(edge_options)),
            format_func=lambda x: edge_options[x]
        )
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            new_weight = st.slider(
                "权重",
                0.0, 2.0,
                value=graph.edges[selected_edge_idx].weight,
                step=0.1
            )
        
        with col2:
            if st.button("✅ 更新权重"):
                graph.edges[selected_edge_idx].weight = new_weight
                st.session_state.knowledge_graph = graph_to_dict(graph)
                st.success("权重已更新")
                st.rerun()
        
        with col3:
            is_blocked = graph.edges[selected_edge_idx].is_blocked
            if st.button("🚫 禁用" if not is_blocked else "✅ 启用"):
                graph.edges[selected_edge_idx].is_blocked = not is_blocked
                st.session_state.knowledge_graph = graph_to_dict(graph)
                st.success("状态已更新")
                st.rerun()
    
    # 重建图谱
    st.markdown("---")
    if st.button("🔄 重新构建知识图谱", type="secondary"):
        with st.spinner("正在重建..."):
            graph = validator.build_knowledge_graph(courseware)
            st.session_state.knowledge_graph = graph_to_dict(graph)
            st.success("知识图谱已重建")
            st.rerun()


# ============================================================================
# 标准库管理标签页
# ============================================================================
def render_standards_library_tab():
    """渲染标准库管理标签页"""
    st.markdown("### 📋 行业标准库管理")
    st.markdown("上传和管理行业标准文档，用于课件生成时的合规性校验")
    
    # 初始化专家验证器
    try:
        from expert_validator import (
            ExpertValidator,
            get_available_industries,
            STANDARDS_DIR
        )
        validator = ExpertValidator()
    except Exception as e:
        st.error(f"专家验证器初始化失败: {e}")
        return
    
    # 行业选择
    col1, col2 = st.columns([2, 1])
    with col1:
        industries = get_available_industries()
        selected_industry = st.selectbox(
            "选择行业",
            industries,
            help="选择行业以加载对应的敏感词库"
        )
    
    with col2:
        st.metric("已加载标准", len(validator.get_standards_list()))
    
    st.markdown("---")
    
    # 已有标准列表
    st.markdown("#### 📚 已加载的标准文档")
    
    standards_list = validator.get_standards_list()
    
    if standards_list:
        for std_name in standards_list:
            with st.expander(f"📄 {std_name}"):
                std_path = STANDARDS_DIR / f"{std_name}.md"
                if std_path.exists():
                    content = std_path.read_text(encoding='utf-8')
                    st.markdown(content[:2000] + ("..." if len(content) > 2000 else ""))
                    
                    if st.button(f"🗑️ 删除", key=f"del_{std_name}"):
                        std_path.unlink()
                        st.success(f"已删除: {std_name}")
                        st.rerun()
    else:
        st.info("📭 暂无标准文档，请上传行业标准")
    
    st.markdown("---")
    
    # 上传新标准
    st.markdown("#### ➕ 添加新标准")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        std_name = st.text_input(
            "标准名称",
            placeholder="如：国家托育服务标准、医疗机构管理条例"
        )
    
    with col2:
        upload_method = st.radio("上传方式", ["文件上传", "手动输入"], horizontal=True)
    
    if upload_method == "文件上传":
        uploaded_file = st.file_uploader(
            "上传标准文档",
            type=["txt", "md"],
            help="支持 TXT 或 Markdown 格式"
        )
        
        if uploaded_file and std_name:
            if st.button("📤 上传标准", type="primary"):
                content = uploaded_file.read().decode('utf-8')
                if validator.add_standard(std_name, content):
                    st.success(f"✅ 标准 '{std_name}' 已添加")
                    st.rerun()
                else:
                    st.error("添加失败")
    else:
        std_content = st.text_area(
            "标准内容",
            height=200,
            placeholder="请输入标准文档内容...\n\n格式建议：\n第1条：...\n第2条：..."
        )
        
        if std_name and std_content:
            if st.button("💾 保存标准", type="primary"):
                if validator.add_standard(std_name, std_content):
                    st.success(f"✅ 标准 '{std_name}' 已添加")
                    st.rerun()
                else:
                    st.error("添加失败")
    
    st.markdown("---")
    
    # 敏感词测试
    st.markdown("#### 🔍 敏感词检测测试")
    
    test_text = st.text_area(
        "输入测试文本",
        height=100,
        placeholder="输入文本以检测其中的敏感词..."
    )
    
    if test_text:
        # 创建对应行业的验证器
        industry_validator = ExpertValidator(industry=selected_industry)
        is_safe, found_words = industry_validator.check_sensitive_words(test_text)
        
        if is_safe:
            st.success("✅ 未检测到敏感词")
        else:
            st.error(f"⚠️ 检测到敏感词: {', '.join(found_words)}")
    
    st.markdown("---")
    
    # 内容验证测试
    st.markdown("#### 🧪 双模型验证测试")
    st.markdown("测试生成内容的专家级验证流程")
    
    with st.expander("展开验证测试"):
        test_content = st.text_area(
            "待验证内容",
            height=150,
            placeholder="输入需要验证的课件内容..."
        )
        
        source_material = st.text_area(
            "原始素材 (可选)",
            height=100,
            placeholder="用于对比验证的原始知识来源..."
        )
        
        selected_standards = st.multiselect(
            "选择适用标准",
            standards_list
        )
        
        if test_content:
            if st.button("🔬 开始验证", type="primary"):
                with st.spinner("🔄 正在进行双模型验证..."):
                    industry_validator = ExpertValidator(industry=selected_industry)
                    
                    validated_content, feedback = industry_validator.validate_content(
                        test_content,
                        source_material,
                        selected_standards,
                        max_revisions=2
                    )
                    
                    # 显示验证结果
                    result_color = {
                        "passed": "green",
                        "needs_revision": "orange",
                        "rejected": "red"
                    }
                    
                    st.markdown(f"""
                    <div style="background: {'#d4edda' if feedback.result.value == 'passed' else '#fff3cd' if feedback.result.value == 'needs_revision' else '#f8d7da'}; 
                                padding: 1rem; border-radius: 0.5rem; margin: 1rem 0;">
                        <h4 style="margin: 0;">验证结果: {feedback.result.value.upper()}</h4>
                        <p>评分: {feedback.score:.0f} / 100</p>
                        <p>可发布: {'✅ 是' if feedback.safe_to_publish else '❌ 否'}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if feedback.hallucinations:
                        st.warning(f"🎭 发现幻觉: {', '.join(feedback.hallucinations)}")
                    
                    if feedback.issues:
                        st.info(f"💡 问题: {', '.join(feedback.issues)}")
                    
                    if feedback.suggestions:
                        st.markdown("**修改建议:**")
                        for sug in feedback.suggestions:
                            st.markdown(f"- {sug}")
                    
                    if validated_content != test_content:
                        st.markdown("**修正后内容:**")
                        st.text_area("", validated_content, height=200, disabled=True)


# ============================================================================
# 主程序
# ============================================================================
def main():
    """主程序入口"""
    # 渲染侧边栏
    render_sidebar()
    
    # 主标题
    st.markdown('<h1 class="main-header">🎓 SmartCourseEngine</h1>', unsafe_allow_html=True)
    st.markdown("**智能教学资源管理平台** - 一站式素材解析、知识管理、课件生成、自适应学习")
    
    st.markdown("---")
    
    # 标签页
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📁 素材入库", 
        "🧠 知识大脑", 
        "✨ 课件生成",
        "🎮 互动学习",
        "📊 学习报告",
        "🗺️ 知识图谱",
        "📋 标准库"
    ])
    
    with tab1:
        render_material_tab()
    
    with tab2:
        render_knowledge_tab()
    
    with tab3:
        render_generate_tab()
    
    with tab4:
        render_interactive_learning_tab()
    
    with tab5:
        render_learning_report_tab()
    
    with tab6:
        render_knowledge_graph_tab()
    
    with tab7:
        render_standards_library_tab()


if __name__ == "__main__":
    main()
