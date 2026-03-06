<script setup></script>

<template>
  <el-config-provider>
    <div class="app-layout">
      <el-menu
        mode="horizontal"
        :router="true"
        :default-active="$route.path"
        background-color="#ffffff"
        text-color="#303133"
        active-text-color="#409eff"
        class="header-menu"
      >
        <div class="logo-container">
          <img src="/assets/logo.png" alt="房估宝 Logo" class="logo-image" />
          <span class="logo-text">房估宝</span>
        </div>
        <el-menu-item index="/">
          <el-icon><Monitor /></el-icon>
          <span>首页</span>
        </el-menu-item>
        <el-menu-item index="/home">
          <el-icon><Cpu /></el-icon>
          <span>智能估值</span>
        </el-menu-item>
        <el-menu-item index="/history">
          <el-icon><Calendar /></el-icon>
          <span>足迹历史</span>
        </el-menu-item>
      </el-menu>

      <main class="main-content">
        <router-view />
      </main>
      
      <footer class="app-footer">
        <p>© 2026 房估宝 - 智能房产估值新范式</p>
      </footer>
    </div>
  </el-config-provider>
</template>

<style>
:root {
  --el-color-primary: #007bff;
}

body {
  margin: 0;
  padding: 0;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  background-color: #f5f7fa;
}

.app-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.header-menu {
  padding: 0 40px;
  border-bottom: none !important;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
  position: sticky;
  top: 0;
  z-index: 1000;
}

.logo-container {
  display: flex;
  align-items: center;
  margin-right: 40px;
}

.logo-image {
  height: 64px;
  width: auto;
  margin-right: 12px;
}

.logo-text {
  color: #303133;
  font-size: 1.6rem;
  font-weight: 900;
  letter-spacing: 2px;
}

.main-content {
  flex: 1;
}

.app-footer {
  text-align: center;
  padding: 30px 0;
  background-color: #ffffff;
  color: #909399;
  border-top: 1px solid #ebeef5;
  font-size: 0.9rem;
}

/* 导航栏 Tab 样式优化 */
.header-menu .el-menu-item {
  height: 40px !important;
  line-height: 40px !important;
  margin: 10px 8px !important;
  border-radius: 8px !important;
  background-color: transparent !important; /* 任何状态下背景透明 */
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) !important; /* 增加回弹感的过渡动画 */
  border-bottom: none !important;
}

/* 悬停动画：上移、变色，且非激活状态下才放大 */
.header-menu .el-menu-item:hover {
  background-color: transparent !important;
  color: #409eff !important;
  transform: translateY(-2px) scale(1.2);
}

/* 选中/激活状态：背景透明，颜色加深，并持久保持放大和上移状态 */
.header-menu .el-menu-item.is-active {
  background-color: transparent !important;
  color: #0056b3 !important; /* 更深的蓝色 */
  transform: translateY(-2px) scale(1.2) !important; /* 持久保持放大和位置 */
  border-bottom: none !important;
}

/* 移除 Element Plus 默认的底部边划线 */
.el-menu--horizontal {
  border-bottom: none !important;
}

.el-menu--horizontal > .el-menu-item.is-active {
  border-bottom: none !important;
}
</style>
