# 房估宝 - 一键启动服务 (PowerShell 版本)
# 使用方法：右键 -> "使用 PowerShell 运行" 或在 PowerShell 中执行 .\start_all.ps1

# 设置控制台编码为 UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    房估宝 - 一键启动服务" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 获取脚本所在目录
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# 检查 Python 是否安装
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[✓] Python 已安装：$pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[✗] 未检测到 Python，请先安装 Python" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}

# 检查 Node.js 是否安装
try {
    $nodeVersion = node --version 2>&1
    Write-Host "[✓] Node.js 已安装：$nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "[✗] 未检测到 Node.js，请先安装 Node.js" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}

Write-Host ""
Write-Host "[信息] 系统检查通过，开始启动服务..." -ForegroundColor Yellow
Write-Host ""

# 启动 Flask 后端
Write-Host "[1/2] 正在启动 Flask 后端..." -ForegroundColor Cyan
$backendPath = Join-Path $scriptDir "Snaprop_Instant"
$backendScript = Join-Path $backendPath "app.py"

Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
    Set-Location '$backendPath'
    Write-Host '后端服务启动中...' -ForegroundColor Green
    python app.py
"@ -WindowStyle Normal

Write-Host "[✓] Flask 后端已启动（新窗口）" -ForegroundColor Green
Start-Sleep -Seconds 3

# 启动 Vue 前端
Write-Host ""
Write-Host "[2/2] 正在启动 Vue 前端..." -ForegroundColor Cyan
$frontendPath = Join-Path $scriptDir "house-frontend"

Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
    Set-Location '$frontendPath'
    Write-Host '前端服务启动中...' -ForegroundColor Green
    npm run dev
"@ -WindowStyle Normal

Write-Host "[✓] Vue 前端已启动（新窗口）" -ForegroundColor Green
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    服务启动完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "后端地址：http://127.0.0.1:5000" -ForegroundColor Yellow
Write-Host "前端地址：http://localhost:5173（以实际输出为准）" -ForegroundColor Yellow
Write-Host ""
Write-Host "提示：" -ForegroundColor Yellow
Write-Host "- 两个服务将在独立窗口运行" -ForegroundColor Gray
Write-Host "- 关闭窗口可停止对应服务" -ForegroundColor Gray
Write-Host "- 如遇端口占用，请先关闭占用进程" -ForegroundColor Gray
Write-Host ""
Read-Host "按回车键退出此窗口"# 房估宝 - 一键启动服务 (PowerShell 版本)
# 使用方法：右键 -> "使用 PowerShell 运行" 或在 PowerShell 中执行 .\start_all.ps1

# 设置控制台编码为 UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    房估宝 - 一键启动服务" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 获取脚本所在目录
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# 检查 Python 是否安装
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[✓] Python 已安装：$pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[✗] 未检测到 Python，请先安装 Python" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}

# 检查 Node.js 是否安装
try {
    $nodeVersion = node --version 2>&1
    Write-Host "[✓] Node.js 已安装：$nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "[✗] 未检测到 Node.js，请先安装 Node.js" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}

Write-Host ""
Write-Host "[信息] 系统检查通过，开始启动服务..." -ForegroundColor Yellow
Write-Host ""

# 启动 Flask 后端
Write-Host "[1/2] 正在启动 Flask 后端..." -ForegroundColor Cyan
$backendPath = Join-Path $scriptDir "Snaprop_Instant"
$backendScript = Join-Path $backendPath "app.py"

Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
    Set-Location '$backendPath'
    Write-Host '后端服务启动中...' -ForegroundColor Green
    python app.py
"@ -WindowStyle Normal

Write-Host "[✓] Flask 后端已启动（新窗口）" -ForegroundColor Green
Start-Sleep -Seconds 3

# 启动 Vue 前端
Write-Host ""
Write-Host "[2/2] 正在启动 Vue 前端..." -ForegroundColor Cyan
$frontendPath = Join-Path $scriptDir "house-frontend"

Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
    Set-Location '$frontendPath'
    Write-Host '前端服务启动中...' -ForegroundColor Green
    npm run dev
"@ -WindowStyle Normal

Write-Host "[✓] Vue 前端已启动（新窗口）" -ForegroundColor Green
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    服务启动完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "后端地址：http://127.0.0.1:5000" -ForegroundColor Yellow
Write-Host "前端地址：http://localhost:5173（以实际输出为准）" -ForegroundColor Yellow
Write-Host ""
Write-Host "提示：" -ForegroundColor Yellow
Write-Host "- 两个服务将在独立窗口运行" -ForegroundColor Gray
Write-Host "- 关闭窗口可停止对应服务" -ForegroundColor Gray
Write-Host "- 如遇端口占用，请先关闭占用进程" -ForegroundColor Gray
Write-Host ""
Read-Host "按回车键退出此窗口"