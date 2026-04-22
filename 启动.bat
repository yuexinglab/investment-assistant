@echo off
chcp 65001 >nul
echo ============================================
echo   AI 项目判断工作台 - 启动中...
echo ============================================

:: 检查是否安装了依赖
python -c "import flask" 2>nul
if errorlevel 1 (
    echo [安装依赖中，首次启动需要等待约1分钟...]
    python -m pip install -r requirements.txt
)

echo.
echo [启动服务器]
echo 浏览器打开：http://localhost:5000
echo 按 Ctrl+C 关闭
echo.

python app.py
pause
