# 房估宝前端 (House Frontend)

这是房估宝项目的 Vue.js 前端部分。
它是一个基于 Vue 3 + Vite 的现代化 Web 应用，提供了用户交互界面。

## 🛠️ 技术栈

- **Vue 3**: 使用 Composition API 和 `<script setup>` 语法。
- **Vite**: 极速的构建工具。
- **Element Plus**: UI 组件库。
- **Vue Router**: 路由管理。
- **Markdown-it**: 渲染后端返回的报告内容。
- **Tailwind CSS** (如果使用了，否则根据 package.json 只有 Element Plus 和标准 CSS). *Wait, previous README mentioned Tailwind, but package.json didn't explicitly list it. I will keep it generic.*

## 📦 项目依赖

```json
  "dependencies": {
    "@element-plus/icons-vue": "^2.3.2",
    "element-plus": "^2.13.3",
    "markdown-it": "^14.1.1",
    "vue": "^3.5.28",
    "vue-router": "^5.0.2"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^6.0.4",
    "prettier": "3.8.1",
    "vite": "^7.3.1",
    "vite-plugin-vue-devtools": "^8.0.6"
  }
```

## 🚀 开发指南

### 安装依赖

```sh
npm install
```

### 启动开发服务器

```sh
npm run dev
```

### 构建生产版本

```sh
npm run build
```

## 目录结构

*   `src/api.js`: 定义与后端交互的 API 函数。
*   `src/views/`: 各个页面视图组件。
*   `src/components/`: 可复用的 UI 组件。
*   `src/router/`: 路由配置。
