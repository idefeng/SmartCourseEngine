@echo off
REM SmartCourseEngine 开发环境启动脚本 (Windows)

echo 🚀 启动 SmartCourseEngine 开发环境
echo ======================================

REM 检查Python版本
echo 检查Python版本...
python --version
if errorlevel 1 (
    echo 错误: Python未安装或不在PATH中
    pause
    exit /b 1
)

REM 创建虚拟环境
if not exist "venv" (
    echo 创建虚拟环境...
    python -m venv venv
)

REM 激活虚拟环境
echo 激活虚拟环境...
call venv\Scripts\activate.bat

REM 安装依赖
echo 安装依赖...
pip install --upgrade pip
pip install -r shared\requirements.txt
pip install -r api-gateway\requirements.txt

REM 创建必要的目录
echo 创建数据目录...
if not exist "data" mkdir data
if not exist "logs" mkdir logs
if not exist "cache" mkdir cache

REM 初始化数据库
echo 初始化数据库...
if exist "init_database.py" (
    python init_database.py
) else (
    echo 警告: init_database.py 不存在，跳过数据库初始化
)

REM 启动API网关
echo 启动API网关服务...
cd api-gateway
start /B python main.py

REM 等待服务启动
echo 等待服务启动...
timeout /t 3 /nobreak >nul

REM 检查服务状态
echo 检查服务状态...
curl -f http://localhost:8000/health || echo 服务启动失败

echo.
echo ✅ 开发环境启动完成!
echo.
echo 访问以下地址:
echo   API文档: http://localhost:8000/docs
echo   健康检查: http://localhost:8000/health
echo.
echo 按 Ctrl+C 停止服务

REM 保持窗口打开
pause