# ============================================
#  房估宝 - 前端自动构建 & 部署脚本
#  用法: .\deploy_frontend.ps1（中途输入 2 次服务器密码）
#  免密: ssh-copy-id root@47.101.213.225
# ============================================

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# ---------- 配置 ----------
$SERVER_IP   = "47.101.213.225"
$SERVER_PORT = 22
$SERVER_USER = "root"
$REMOTE_HTML_DIR = "/usr/share/nginx/html"
$REMOTE_NGINX_CONF = "/etc/nginx/conf.d/fangubao.conf"
$ARCHIVE_NAME = "dist.zip"

# ---------- 输出 ----------
function info  { Write-Host "[信息] $args" -ForegroundColor Cyan }
function ok    { Write-Host "[ ✓ ] $args" -ForegroundColor Green }
function err   { Write-Host "[ ✗ ] $args" -ForegroundColor Red; exit 1 }
function step  { Write-Host "`n>>> $args <<<" -ForegroundColor Yellow }

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir
$FrontendDir = Join-Path $ScriptDir "house-frontend"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "   房估宝 - 前端部署" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# ============ Step 1: 构建前端 ============
step "Step 1/4: 构建前端"
Set-Location $FrontendDir
info "安装依赖..."
npm install 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { err "npm install 失败" }

info "执行构建 (npm run build)..."
npm run build 2>&1
if ($LASTEXITCODE -ne 0) { err "构建失败" }
if (-not (Test-Path "dist")) { err "dist 目录未生成" }
ok "构建完成"

# ============ Step 2: 打包 & 上传 ============
step "Step 2/4: 打包 & 上传"
Set-Location $FrontendDir
if (Test-Path $ARCHIVE_NAME) { Remove-Item $ARCHIVE_NAME -Force }

# tar -a 自动检测格式输出 zip，-C 先切到 dist 目录再打包 .
info "打包 dist/ → $ARCHIVE_NAME"
tar -a -cf $ARCHIVE_NAME -C dist .
if ($LASTEXITCODE -ne 0) { err "打包失败" }
ok "打包完成 ($([math]::Round((Get-Item $ARCHIVE_NAME).Length / 1KB, 1)) KB)"

info "上传到服务器（需要输入密码）..."
scp -P $SERVER_PORT $ARCHIVE_NAME "${SERVER_USER}@${SERVER_IP}:/tmp/"
if ($LASTEXITCODE -ne 0) { err "上传失败" }
ok "上传完成"

# ============ Step 3: 服务器端部署 ============
step "Step 3/4: 服务端部署（需要输入密码）"

$DeployCmd = @"
set -e
# 备份旧文件
if [ -d ${REMOTE_HTML_DIR} ] && [ "`$(ls -A ${REMOTE_HTML_DIR} 2`>/dev/null)" ]; then
    mkdir -p /tmp/html_backup
    cp -r ${REMOTE_HTML_DIR}/* /tmp/html_backup/ 2`>/dev/null || true
    echo '[信息] 已备份旧文件到 /tmp/html_backup/'
fi
# 解压新文件
cd ${REMOTE_HTML_DIR} && rm -rf * && unzip -o /tmp/${ARCHIVE_NAME} && rm -f /tmp/${ARCHIVE_NAME}
echo '[ ✓ ] 前端文件已部署到 ${REMOTE_HTML_DIR}'
"@

info "解压部署中..."
ssh -p $SERVER_PORT "${SERVER_USER}@${SERVER_IP}" $DeployCmd
if ($LASTEXITCODE -ne 0) { err "远程部署失败" }

# 上传并更新 nginx 配置
$NginxConf = Join-Path $ScriptDir "nginx.conf"
if (Test-Path $NginxConf) {
    $ngContent = Get-Content $NginxConf -Raw
    if ($ngContent -match 'backend:\d+') {
        Write-Host "?" -ForegroundColor Yellow -NoNewline
        $choice = Read-Host " nginx.conf 含 Docker 主机名，替换为 127.0.0.1？[Y/n]"
        if ($choice -eq '' -or $choice -eq 'y' -or $choice -eq 'Y') {
            $ngContent = $ngContent -replace 'http://backend:\d+/', 'http://127.0.0.1:5000/'
            $ngContent | Set-Content -Path $NginxConf -NoNewline
            ok "已自动适配 nginx.conf"
        }
    }
    info "上传 nginx 配置..."
    scp -P $SERVER_PORT $NginxConf "${SERVER_USER}@${SERVER_IP}:/tmp/fangubao.conf"
    $NginxCmd = "cp /tmp/fangubao.conf ${REMOTE_NGINX_CONF} && rm /tmp/fangubao.conf && nginx -t && nginx -s reload && echo '[ ✓ ] nginx 重载成功'"
    ssh -p $SERVER_PORT "${SERVER_USER}@${SERVER_IP}" $NginxCmd
    if ($LASTEXITCODE -ne 0) { err "nginx 配置更新失败" }
}

# ============ Step 4: 清理 ============
step "Step 4/4: 清理"
Set-Location $FrontendDir
if (Test-Path $ARCHIVE_NAME) { Remove-Item $ARCHIVE_NAME -Force }
ok "清理完成"

Set-Location $ScriptDir
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "   前端部署完成！" -ForegroundColor Green
Write-Host "   访问: http://${SERVER_IP}" -ForegroundColor Yellow
Write-Host "========================================`n" -ForegroundColor Cyan
