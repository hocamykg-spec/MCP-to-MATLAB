@echo off
echo ========================================
echo   MCP-MATLAB 启动脚本
echo ========================================
echo.

echo [1/2] 正在启动MATLAB桌面应用程序...
start matlab
timeout /t 3 /nobreak >nul
echo MATLAB桌面应用程序已启动！

echo.
echo [2/2] 正在启动MCP服务器...
echo.
echo MCP服务器启动中...
echo 按 Ctrl+C 可停止服务器
echo.

cd /d "%~dp0"
python server.py