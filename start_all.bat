@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo     房估宝 - 一键启动服务
echo ========================================
echo.

REM 设置项目根目录
cd /d "%~dp0"

REM 检查 Python 是否安装
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python
    pause
    exit /b 1
)

REM 检查 Node.js 是否安装
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Node.js，请先安装 Node.js
    pause
    exit /b 1
)

echo [信息] 系统检查通过
echo.

REM 启动 Flask 后端
echo [信息] 正在启动 Flask 后端...
cd /d "Snaprop_Instant"
start "Flask 后端" cmd /k "echo 后端服务启动中... && python app.py"
echo [信息] Flask 后端已启动（新窗口）
echo.

REM 等待后端启动
timeout /t 3 /nobreak >nul

REM 启动 Vue 前端
echo [信息] 正在启动 Vue 前端...
cd /d "..\house-frontend"
start "Vue 前端" cmd /k "echo 前端服务启动中... && npm run dev"
echo [信息] Vue 前端已启动（新窗口）
echo.

echo ========================================
echo     服务启动完成！
echo ========================================
echo.
echo 后端地址：http://127.0.0.1:5000
echo 前端地址：http://localhost:5173（以实际输出为准）
echo.
echo 提示：
echo - 两个服务将在独立窗口运行
echo - 关闭窗口可停止对应服务
echo - 如遇端口占用，请先关闭占用进程
echo.
pause