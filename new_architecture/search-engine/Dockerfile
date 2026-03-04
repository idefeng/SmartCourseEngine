# 搜索服务 Dockerfile
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY search-engine/requirements.txt /app/requirements.txt
COPY shared/requirements.txt /app/shared-requirements.txt

# 安装Python依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r shared-requirements.txt && \
    pip install --no-cache-dir -r requirements.txt

# 复制共享模块与服务代码
COPY shared /app/shared
COPY search-engine /app

# 创建必要的目录
RUN mkdir -p /app/data/index /app/data/cache

# 暴露端口
EXPOSE 8004

# 启动命令
CMD ["python", "main.py"]
