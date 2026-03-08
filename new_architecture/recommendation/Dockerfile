# 使用Python 3.9作为基础镜像
FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制共享模块与服务代码
COPY shared/requirements.txt /app/shared-requirements.txt
COPY shared /app/shared
COPY recommendation/requirements.txt /app/requirements.txt
COPY recommendation /app

# 安装Python依赖
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r shared-requirements.txt && \
    pip install --no-cache-dir -r requirements.txt

# 暴露端口
EXPOSE 8005

# 启动命令
CMD ["python", "main.py"]