@echo off
chcp 65001 > nul
echo ============================================================
echo          SmartCourseEngine - Start Application
echo ============================================================
echo.

cd /d "%~dp0"

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo [Error] Virtual environment not found!
    echo Please run setup_and_run.ps1 first.
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

echo [OK] Virtual environment activated
echo [OK] Starting Streamlit application...
echo.
echo ============================================================
echo   Access the application at: http://localhost:8501
echo   Press Ctrl+C to stop the server
echo ============================================================
echo.

REM Start Streamlit
streamlit run app.py --server.headless true

pause
