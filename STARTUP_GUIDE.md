# 房估宝 - 启动指南

## 📋 前提条件

请确保已安装以下软件：

- **Python 3.8+**：用于运行 Flask 后端
- **Node.js 20+**：用于运行 Vue 前端
- **Git**（可选）：用于版本控制

## 🚀 快速启动

### 方法一：使用批处理文件（推荐）

1. **双击运行** `start_all.bat`
2. 系统会自动检查 Python 和 Node.js
3. 自动打开两个新窗口：
   - **Flask 后端** 窗口
   - **Vue 前端** 窗口

### 方法二：使用 PowerShell 脚本

1. 右键点击 `start_all.ps1`
2. 选择 **"使用 PowerShell 运行"**
3. 如果提示权限问题，以管理员身份运行 PowerShell，执行：
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

## 🌐 访问地址

启动成功后，在浏览器中访问：

- **前端界面**：http://localhost:5173
- **后端 API**：http://127.0.0.1:5000

> 注意：前端端口可能因配置而异，请以实际输出为准

## ⏹️ 停止服务

### 方法一：使用停止脚本

双击运行 `stop_all.bat`，会自动关闭所有服务窗口。

### 方法二：手动关闭

直接关闭两个服务窗口即可。

## 🔧 故障排查

### 1. Python 未找到

**错误信息**：`未检测到 Python`

**解决方案**：
- 下载并安装 Python：https://www.python.org/downloads/
- 安装时勾选 "Add Python to PATH"

### 2. Node.js 未找到

**错误信息**：`未检测到 Node.js`

**解决方案**：
- 下载并安装 Node.js：https://nodejs.org/
- 推荐安装 LTS（长期支持）版本

### 3. 端口占用

**错误信息**：`Address already in use` 或 `端口被占用`

**解决方案**：

**Windows**：
```cmd
# 查找占用端口的进程
netstat -ano | findstr :5000
netstat -ano | findstr :5173

# 杀死进程（将 PID 替换为实际进程 ID）
taskkill /F /PID <PID>
```

**或者**直接运行 `stop_all.bat` 停止所有服务后重新启动。

### 4. npm 依赖缺失

**错误信息**：`Cannot find module 'xxx'`

**解决方案**：
```cmd
cd house-frontend
npm install
```

### 5. Python 依赖缺失

**错误信息**：`ModuleNotFoundError`

**解决方案**：
```cmd
cd Snaprop_Instant
pip install -r requirements.txt
```

## 📝 手动启动（备用方案）

如果自动脚本无法使用，可以手动启动：

### 启动后端

```cmd
cd Snaprop_Instant
python app.py
```

### 启动前端

打开新的命令提示符窗口：

```cmd
cd house-frontend
npm run dev
```

## 💡 使用提示

1. **首次启动**：建议先手动运行一次，观察输出信息，了解正常启动流程
2. **开发环境**：两个服务都支持热重载，修改代码后会自动刷新
3. **日志查看**：每个服务窗口会显示详细的运行日志，便于调试
4. **网络访问**：默认只允许本地访问，如需局域网访问需修改配置

## 🆘 常见问题

**Q: 启动后浏览器无法访问？**
A: 等待 5-10 秒，服务需要启动时间。检查服务窗口是否有错误信息。

**Q: 前端页面显示空白？**
A: 打开浏览器开发者工具（F12），查看 Console 和 Network 标签页的错误信息。

**Q: 后端 API 请求失败？**
A: 确认后端服务正常运行，检查浏览器 Console 中 API 地址是否正确。

**Q: 脚本运行时闪退？**
A: 可能是 Python 或 Node.js 未正确安装。尝试手动启动查看详细错误信息。

## 📞 技术支持

如遇到其他问题，请查看项目文档或联系开发团队。