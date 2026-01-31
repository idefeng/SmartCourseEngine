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
from pathlib import Path
from datetime import datetime

import streamlit as st

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
        
        api_key = st.text_input(
            "DeepSeek API Key",
            value=os.getenv("DEEPSEEK_API_KEY", ""),
            type="password",
            help="用于知识点提取和内容生成"
        )
        
        if api_key:
            os.environ["DEEPSEEK_API_KEY"] = api_key
            st.success("✓ API Key 已配置")
        
        model_options = ["deepseek-chat", "deepseek-coder", "qwen-turbo", "gpt-4o-mini"]
        model = st.selectbox("选择模型", model_options, index=0)
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
            
            with open(docx_path, "rb") as f:
                st.download_button(
                    label="📄 下载 Word 文档",
                    data=f.read(),
                    file_name=Path(docx_path).name,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    type="primary"
                )
            
            st.success(f"文件已保存: {docx_path}")
            
        except Exception as e:
            st.error(f"生成失败: {e}")
            import traceback
            st.code(traceback.format_exc())


# ============================================================================
# 主程序
# ============================================================================
def main():
    """主程序入口"""
    # 渲染侧边栏
    render_sidebar()
    
    # 主标题
    st.markdown('<h1 class="main-header">🎓 SmartCourseEngine</h1>', unsafe_allow_html=True)
    st.markdown("**智能教学资源管理平台** - 一站式素材解析、知识管理、课件生成")
    
    st.markdown("---")
    
    # 标签页
    tab1, tab2, tab3 = st.tabs(["📁 素材入库", "🧠 知识大脑", "✨ 课件生成"])
    
    with tab1:
        render_material_tab()
    
    with tab2:
        render_knowledge_tab()
    
    with tab3:
        render_generate_tab()


if __name__ == "__main__":
    main()
