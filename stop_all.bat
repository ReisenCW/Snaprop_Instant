@echo off
chcp 65001 >nul
echo ========================================
echo     房估宝 - 停止所有服务
echo ========================================
echo.

echo [信息] 正在停止 Flask 后端...
taskkill /F /FI "WindowTitle eq Flask 后端*" 2>nul
if %errorlevel% equ 0 (
    echo [✓] Flask 后端已停止
) else (
    echo [信息] Flask 后端未运行
)

echo.
echo [信息] 正在停止 Vue 前端...
taskkill /F /FI "WindowTitle eq Vue 前端*" 2>nul
if %errorlevel% equ 0 (
    echo [✓] Vue 前端已停止
) else (
    echo [信息] Vue 前端未运行
)

echo.
echo ========================================
echo     所有服务已停止
echo ========================================
echo.
pause