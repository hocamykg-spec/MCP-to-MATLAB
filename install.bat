@echo off
chcp 65001 >nul
echo ========================================
echo   MCP-MATLAB 自动安装脚本
echo ========================================
echo.

echo [1/5] 检查Python安装...
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误：未找到Python
    echo 请先安装Python 3.9或更高版本
    echo 下载地址：https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do echo %%i
echo Python检查通过！

echo.
echo [2/5] 检查pip安装...
pip --version >nul 2>&1
if errorlevel 1 (
    echo 错误：未找到pip
    echo 请确保pip已正确安装
    pause
    exit /b 1
)
echo pip检查通过！

echo.
echo [3/5] 安装Python依赖...
echo 正在安装mcp、numpy、pydantic等依赖...
pip install -e .
if errorlevel 1 (
    echo 错误：安装Python依赖失败
    echo 请检查网络连接或使用管理员权限运行
    pause
    exit /b 1
)
echo Python依赖安装完成！

echo.
echo [4/5] 检查MATLAB安装...
set MATLAB_FOUND=0
if exist "D:\MATLAB\bin\matlab.exe" (
    echo MATLAB已找到：D:\MATLAB
    set MATLAB_FOUND=1
    set MATLAB_PATH=D:\MATLAB
)
if exist "C:\Program Files\MATLAB\R2024b\bin\matlab.exe" (
    echo MATLAB已找到：C:\Program Files\MATLAB\R2024b
    set MATLAB_FOUND=1
    set MATLAB_PATH=C:\Program Files\MATLAB\R2024b
)
if exist "C:\Program Files\MATLAB\R2024a\bin\matlab.exe" (
    echo MATLAB已找到：C:\Program Files\MATLAB\R2024a
    set MATLAB_FOUND=1
    set MATLAB_PATH=C:\Program Files\MATLAB\R2024a
)

if %MATLAB_FOUND%==0 (
    echo 警告：未自动找到MATLAB
    echo 请手动输入MATLAB安装路径
    set /p MATLAB_PATH="MATLAB安装路径："
)

echo.
echo [5/5] 安装MATLAB Engine API...
if exist "%MATLAB_PATH%\extern\engines\python\setup.py" (
    echo 正在安装MATLAB Engine API...
    cd /d "%MATLAB_PATH%\extern\engines\python"
    python setup.py install
    if errorlevel 1 (
        echo 错误：MATLAB Engine API安装失败
        echo 请以管理员身份运行此脚本
        cd /d "%~dp0"
        pause
        exit /b 1
    )
    cd /d "%~dp0"
    echo MATLAB Engine API安装完成！
) else (
    echo 错误：未找到MATLAB Engine API安装文件
    echo 请检查MATLAB路径是否正确
    pause
    exit /b 1
)

echo.
echo ========================================
echo   安装完成！
echo ========================================
echo.
echo 已安装内容：
echo 1. Python依赖包（mcp, numpy, pydantic等）
echo 2. MATLAB Engine API
echo.
echo 使用方法：
echo 1. 双击 start.bat 启动MATLAB和MCP服务器
echo 2. 或分别使用：
echo    - start_matlab.py 启动MATLAB
echo    - start_mcp.bat 启动MCP服务器
echo.
echo 配置MCP客户端（如Claude Desktop）：
echo 参考 README.md 或 部署指南.md
echo.
echo 测试安装：
echo python test_server.py
echo.
pause