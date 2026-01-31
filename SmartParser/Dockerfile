# =============================================================================
# SmartCourseEngine Dockerfile
# =============================================================================
# 多阶段构建，支持 GPU 加速和视频处理
# 
# 使用方法:
#   docker build -t smartcourseengine:latest .
#   docker run -p 8501:8501 smartcourseengine:latest
#
# GPU 支持:
#   docker run --gpus all -p 8501:8501 smartcourseengine:latest
# =============================================================================

# -----------------------------------------------------------------------------
# 阶段1: 基础镜像 (NVIDIA CUDA + Python)
# -----------------------------------------------------------------------------
FROM nvidia/cuda:12.1-runtime-ubuntu22.04 AS base

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Shanghai

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    # FFmpeg 视频处理
    ffmpeg \
    libavcodec-extra \
    # 音频处理
    libsndfile1 \
    portaudio19-dev \
    # PDF 处理
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    # 其他工具
    git \
    curl \
    wget \
    vim \
    # 清理缓存
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 设置 Python 别名
RUN ln -sf /usr/bin/python3.11 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

# 创建非 root 用户
RUN useradd -m -u 1000 appuser

# -----------------------------------------------------------------------------
# 阶段2: 依赖安装
# -----------------------------------------------------------------------------
FROM base AS dependencies

WORKDIR /app

# 复制依赖文件
COPY requirements.txt requirements-docker.txt* ./

# 安装 Python 依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    # Celery 和 Redis
    pip install --no-cache-dir celery[redis] redis flower && \
    # 可选: 本地 LLM 支持
    pip install --no-cache-dir ollama

# -----------------------------------------------------------------------------
# 阶段3: 生产镜像
# -----------------------------------------------------------------------------
FROM dependencies AS production

WORKDIR /app

# 复制应用代码
COPY --chown=appuser:appuser . .

# 创建必要目录
RUN mkdir -p /app/data/chroma_db \
             /app/data/output_markdown \
             /app/data/generated_courseware \
             /app/data/standards_library \
             /app/data/backups \
             /app/logs \
    && chown -R appuser:appuser /app

# 切换到非 root 用户
USER appuser

# 暴露端口
EXPOSE 8501 5555

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# 默认启动命令
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]

# -----------------------------------------------------------------------------
# 阶段4: 开发镜像 (可选)
# -----------------------------------------------------------------------------
FROM production AS development

USER root

# 安装开发工具
RUN pip install --no-cache-dir \
    pytest \
    pytest-cov \
    black \
    flake8 \
    ipython

USER appuser

# 开发模式启动
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.runOnSave=true"]
