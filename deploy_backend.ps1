# ============================================
#  房估宝 - 后端自动部署脚本
#  用法: .\deploy_backend.ps1（中途输入多次服务器密码）
#  免密: ssh-copy-id root@47.101.213.225 后无需输入密码
# ============================================

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# ---------- 配置 ----------
$SERVER_IP   = "47.101.213.225"
$SERVER_PORT = 22
$SERVER_USER = "root"
$REMOTE_APP_DIR = "/opt/fangubao"
$GUNICORN_WORKERS = 2
$GUNICORN_PORT = 5000
$SERVICE_NAME = "fangubao"
$ARCHIVE_NAME = "backend_deploy.zip"

# ---------- 输出 ----------
function info  { Write-Host "[信息] $args" -ForegroundColor Cyan }
function ok    { Write-Host "[ ✓ ] $args" -ForegroundColor Green }
function err   { Write-Host "[ ✗ ] $args" -ForegroundColor Red; exit 1 }
function step  { Write-Host "`n>>> $args <<<" -ForegroundColor Yellow }

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "   房估宝 - 后端部署" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# ============ Step 1: 打包 ============
step "Step 1/4: 打包后端文件"
Set-Location $ScriptDir
if (Test-Path $ARCHIVE_NAME) { Remove-Item $ARCHIVE_NAME -Force }

info "打包 Snaprop_Instant/（排除 .venv, __pycache__, uploads 等）..."
tar -a -cf $ARCHIVE_NAME `
    -C Snaprop_Instant `
    --exclude=.venv `
    --exclude=__pycache__ `
    --exclude='*.pyc' `
    --exclude=.pytest_cache `
    --exclude=static/uploads `
    --exclude=static/reports `
    --exclude='*.db' `
    --exclude=.env `
    --exclude=chroma_db `
    .

if ($LASTEXITCODE -ne 0) { err "打包失败" }
ok "打包完成 ($([math]::Round((Get-Item $ARCHIVE_NAME).Length / 1MB, 1)) MB)"

# ============ Step 2: 上传 ============
step "Step 2/4: 上传到服务器"
$zipSize = [math]::Round((Get-Item $ARCHIVE_NAME).Length / 1MB, 1)
info "上传 $ARCHIVE_NAME ($zipSize MB) → /tmp/，请耐心等待..."
scp -P $SERVER_PORT $ARCHIVE_NAME "${SERVER_USER}@${SERVER_IP}:/tmp/"
if ($LASTEXITCODE -ne 0) { err "上传失败" }
ok "上传完成"

# ============ Step 3: 服务端部署 ============
step "Step 3/4: 服务端部署"

$DeployCmd = @"
set -e
if [ -d ${REMOTE_APP_DIR} ]; then
    BACKUP_DIR="/tmp/fangubao_backup_`$(date +%Y%m%d_%H%M%S)"
    mkdir -p "`$BACKUP_DIR"
    cp -r ${REMOTE_APP_DIR}/* "`$BACKUP_DIR/" 2`>/dev/null || true
    echo "[信息] 已备份到 `$BACKUP_DIR"
fi
mkdir -p ${REMOTE_APP_DIR}
rm -rf ${REMOTE_APP_DIR}/*
cd ${REMOTE_APP_DIR} && unzip -o /tmp/${ARCHIVE_NAME} && rm -f /tmp/${ARCHIVE_NAME}
echo "[ ✓ ] 后端文件已部署到 ${REMOTE_APP_DIR}"
cd ${REMOTE_APP_DIR}
# 首次部署时创建虚拟环境
if [ ! -d .venv ]; then
    echo "--- 创建虚拟环境 ---"
    python3 -m venv .venv
fi
# 安装/更新依赖（有缓存则很快）
if [ -f requirements.txt ]; then
    REQ_HASH=`$(md5sum requirements.txt | cut -d' ' -f1 2`>/dev/null || echo '')
    if [ -f /tmp/requirements_md5.txt ] && [ "`$(cat /tmp/requirements_md5.txt)" = "`$REQ_HASH" ]; then
        echo "--- 依赖无变化，跳过 pip install ---"
    else
        echo "--- pip install 开始（阿里云镜像） ---"
        .venv/bin/pip install --upgrade pip gunicorn -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com -q
        # 去哈希（老pip不支持--no-hashes）并转UTF-8
        iconv -f UTF-16LE -t UTF-8 requirements.txt 2>/dev/null | grep -v '\\--hash' > /tmp/req_clean.txt || cat requirements.txt | grep -v '\\--hash' > /tmp/req_clean.txt
        .venv/bin/pip install -r /tmp/req_clean.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com --default-timeout 120
        rm -f /tmp/req_clean.txt
        echo "`$REQ_HASH" > /tmp/requirements_md5.txt
        echo "--- pip install 完成 ---"
    fi
fi
"@

info "解压部署 & 安装依赖..."
ssh -p $SERVER_PORT "${SERVER_USER}@${SERVER_IP}" $DeployCmd
if ($LASTEXITCODE -ne 0) { err "远程部署失败" }

# 上传 .env 到 /opt/.env（app.py 从这里加载环境变量）
if (Test-Path ".env") {
    info "上传 .env → /opt/.env（API密钥配置）..."
    scp -P $SERVER_PORT ".env" "${SERVER_USER}@${SERVER_IP}:/opt/.env"
    if ($LASTEXITCODE -ne 0) { err ".env 上传失败" }
    ok ".env 已部署"
} else {
    info "本地无 .env 文件，跳过（服务器上已有或使用其他方式配置）"
}

# 配置/更新 systemd 服务
$SystemdUnit = @"
[Unit]
Description=FangGuBao Backend Service
After=network.target
StartLimitBurst=10
StartLimitIntervalSec=30

[Service]
Type=simple
User=root
WorkingDirectory=${REMOTE_APP_DIR}
EnvironmentFile=/opt/.env
ExecStart=${REMOTE_APP_DIR}/.venv/bin/gunicorn -w ${GUNICORN_WORKERS} -b 0.0.0.0:${GUNICORN_PORT} app:app
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"@

$B64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($SystemdUnit))
$SystemdCmd = "echo '$B64' | base64 -d > /etc/systemd/system/${SERVICE_NAME}.service && systemctl daemon-reload && echo '[ ✓ ] systemd 配置已更新'"
ssh -p $SERVER_PORT "${SERVER_USER}@${SERVER_IP}" $SystemdCmd
if ($LASTEXITCODE -ne 0) { err "systemd 配置更新失败" }

# ============ Step 4: 重启服务 ============
step "Step 4/4: 重启后端服务"

$RestartCmd = @"
# 停止旧 sitp 服务（如果还存在）
systemctl stop sitp 2`>/dev/null && systemctl disable sitp 2`>/dev/null || true
# 杀掉所有旧 gunicorn 进程
pkill -9 -f 'gunicorn.*app:app' 2`>/dev/null || true
sleep 2
# 重置 systemd 限流计数器
systemctl reset-failed ${SERVICE_NAME} 2`>/dev/null || true
# 启用并启动服务
systemctl enable ${SERVICE_NAME} 2`>/dev/null || true
echo ">>> 启动 ${SERVICE_NAME} 服务..."
systemctl start ${SERVICE_NAME} 2`>&1 && echo "systemctl start: OK" || echo "systemctl start: FAIL (exit=`$?)"
sleep 3
echo ""
echo "======== 服务状态 ========"
systemctl is-active ${SERVICE_NAME} 2`>&1 || true
echo ""
echo "======== 端口监听 (port ${GUNICORN_PORT}) ========"
ss -tlnp 2`>/dev/null | grep ${GUNICORN_PORT} || echo "端口 ${GUNICORN_PORT} 未监听"
echo ""
echo "======== 最近日志 (journalctl -n 20) ========"
journalctl -u ${SERVICE_NAME} --no-pager -n 20 2`>&1 || true
echo ""
echo "======== 进程列表 (gunicorn) ========"
ps aux 2`>/dev/null | grep gunicorn | grep -v grep || echo "无 gunicorn 进程"
echo ""
echo ">>> DIAGNOSTICS_DONE <<<"
exit 0
"@

info "连接服务器 & 执行重启..."
$RestartOutput = ssh -p $SERVER_PORT "${SERVER_USER}@${SERVER_IP}" $RestartCmd 2>&1

# 始终输出诊断结果
Write-Host $RestartOutput

# 判断结果
if ($LASTEXITCODE -eq 0 -and $RestartOutput -match "端口.*未监听") {
    Write-Host "[ ✗ ] 服务可能未正常启动，请检查上方日志" -ForegroundColor Red
} elseif ($LASTEXITCODE -ne 0) {
    Write-Host "[ ✗ ] SSH 连接或远程命令失败 (exit=$LASTEXITCODE)" -ForegroundColor Red
} elseif ($RestartOutput -match "active") {
    ok "服务运行中，端口已监听"
} else {
    Write-Host "[!] 无法确定服务状态，请检查上方输出" -ForegroundColor Yellow
}

# 快速验证：测试模块能否导入
Write-Host ""
info "验证 Python 模块导入..."
$VerifyCmd = "cd ${REMOTE_APP_DIR} && .venv/bin/python -c 'from app import app; print(`"[ ✓ ] 模块导入成功`")'"
$VerifyOutput = ssh -p $SERVER_PORT "${SERVER_USER}@${SERVER_IP}" $VerifyCmd 2>&1
Write-Host $VerifyOutput
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ ✗ ] 模块导入失败，请检查服务器日志: journalctl -u ${SERVICE_NAME} -n 50" -ForegroundColor Red
} else {
    ok "模块导入验证通过"
}

# ============ 清理 ============
Set-Location $ScriptDir
if (Test-Path $ARCHIVE_NAME) { Remove-Item $ARCHIVE_NAME -Force }
ok "本地临时文件已清理"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "   后端部署完成！" -ForegroundColor Green
Write-Host "   验证: curl http://${SERVER_IP}:${GUNICORN_PORT}/" -ForegroundColor Yellow
Write-Host "========================================`n" -ForegroundColor Cyan
