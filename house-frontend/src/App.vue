<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { houseStore } from './store'
import { useRouter } from 'vue-router'
import { ArrowUp } from '@element-plus/icons-vue'
import { API_BASE_URL } from './config'

const router = useRouter()

const showBackToTop = ref(false)

const handleScroll = () => {
  showBackToTop.value = window.scrollY > 400
}

const scrollToTop = () => {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

onMounted(() => {
  window.addEventListener('scroll', handleScroll)
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
})

const handleLogout = () => {
  houseStore.logout()
  router.push('/')
}

const userAvatarSrc = computed(() => {
  const av = houseStore.user?.avatar
  if (!av) return ''
  return av.startsWith('http') ? av : `${API_BASE_URL}${av}`
})
</script>

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
        :ellipsis="false"
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

        <div class="header-right">
          <template v-if="houseStore.isAuthenticated">
            <el-dropdown trigger="hover">
              <span class="user-info">
                <el-avatar :size="34" :src="userAvatarSrc" class="nav-avatar">
                  <el-icon :size="20"><User /></el-icon>
                </el-avatar>
                <span class="username">{{ houseStore.user?.nickname || houseStore.user?.username }}</span>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item v-if="houseStore.user?.username === 'admin'" @click="$router.push('/admin')">
                    <el-icon><Setting /></el-icon> 系统管理
                  </el-dropdown-item>
                  <el-dropdown-item @click="$router.push('/profile')">
                    <el-icon><User /></el-icon> 个人中心
                  </el-dropdown-item>
                  <el-dropdown-item divided @click="handleLogout">
                    <el-icon><SwitchButton /></el-icon> 退出登录
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
          <el-button v-else type="primary" round @click="$router.push('/login')" class="login-nav-btn">
            登录 / 注册
          </el-button>
        </div>
      </el-menu>

      <main class="main-content">
        <router-view v-slot="{ Component, route }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" :key="route.fullPath" />
          </transition>
        </router-view>
      </main>

      <!-- Back to Top Button -->
      <transition name="fade">
        <div v-show="showBackToTop" class="back-to-top" @click="scrollToTop">
          <el-icon :size="22"><ArrowUp /></el-icon>
        </div>
      </transition>

      <footer class="app-footer">
        <div class="footer-content">
          <div class="footer-brand">
            <span class="footer-logo-text">房估宝</span>
            <span class="footer-divider">|</span>
            <span class="footer-desc">智能房产估值新范式</span>
          </div>
          <p class="footer-copy">© 2026 房估宝 - 基于多模态融合与大语言模型的智能房产估值系统</p>
        </div>
      </footer>
    </div>
  </el-config-provider>
</template>

<style>
:root {
  --el-color-primary: #007bff;
  --app-gradient: linear-gradient(135deg, #007bff 0%, #6610f2 100%);
}

body {
  margin: 0;
  padding: 0;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background-color: #f0f2f5;
}

/* Scrollbar styling */
::-webkit-scrollbar {
  width: 8px;
}
::-webkit-scrollbar-track {
  background: #f1f1f1;
}
::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
  background: #a1a1a1;
}

.app-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.header-menu {
  padding: 0 40px;
  border-bottom: none !important;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
  position: sticky;
  top: 0;
  z-index: 1000;
  background: linear-gradient(to bottom, #ffffff, #fefefe) !important;
  display: flex !important;
  align-items: center !important;
}

/* Subtle gradient accent line at header bottom */
.header-menu::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #007bff, #6610f2, #e83e8c);
  opacity: 0.6;
}

.logo-container {
  display: flex;
  align-items: center;
  margin-right: 40px;
  margin-top: 5px;
  flex-shrink: 0;
}

.logo-image {
  height: 54px;
  width: auto;
  margin-right: 12px;
  transition: transform 0.3s ease;
}

.logo-image:hover {
  transform: rotate(-5deg) scale(1.05);
}

.logo-text {
  background: linear-gradient(135deg, #007bff, #6610f2);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-size: 1.5rem;
  font-weight: 900;
  letter-spacing: 2px;
}

.header-right {
  margin-left: auto !important;
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  outline: none;
}

.nav-avatar {
  flex-shrink: 0;
  border: 2px solid #e4e7ed;
  transition: border-color 0.3s ease;
}

.user-info:hover .nav-avatar {
  border-color: #409eff;
}

.username {
  font-weight: 500;
  color: #303133;
}

.login-nav-btn {
  padding: 8px 20px;
  font-weight: 600;
}

.main-content {
  flex: 1;
  min-height: calc(100vh - 140px);
}

/* Page Transition */
.page-fade-enter-active,
.page-fade-leave-active {
  transition: all 0.3s ease;
}
.page-fade-enter-from {
  opacity: 0;
  transform: translateY(12px);
}
.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-12px);
}

/* Back to Top Button */
.back-to-top {
  position: fixed;
  bottom: 40px;
  right: 40px;
  width: 48px;
  height: 48px;
  background: var(--app-gradient);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 999;
  box-shadow: 0 4px 16px rgba(0, 123, 255, 0.35);
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.back-to-top:hover {
  transform: translateY(-4px) scale(1.08);
  box-shadow: 0 6px 24px rgba(0, 123, 255, 0.5);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

/* Footer */
.app-footer {
  background: linear-gradient(180deg, #ffffff 0%, #f8f9fb 100%);
  border-top: 1px solid #ebeef5;
  padding: 36px 0;
}

.footer-content {
  max-width: 1200px;
  margin: 0 auto;
  text-align: center;
  padding: 0 20px;
}

.footer-brand {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-bottom: 10px;
}

.footer-logo-text {
  font-size: 1.2rem;
  font-weight: 800;
  background: linear-gradient(135deg, #007bff, #6610f2);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.footer-divider {
  color: #dcdfe6;
}

.footer-desc {
  color: #606266;
  font-size: 0.95rem;
}

.footer-copy {
  color: #909399;
  font-size: 0.82rem;
  margin: 0;
}

/* 导航栏 Tab 样式优化 */
.header-menu .el-menu-item {
  height: 40px !important;
  line-height: 40px !important;
  margin: 10px 8px !important;
  border-radius: 8px !important;
  background-color: transparent !important;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
  border-bottom: none !important;
  font-weight: 500;
  flex-grow: 0 !important;
}

/* 悬停动画 */
.header-menu .el-menu-item:hover {
  background-color: transparent !important;
  color: #409eff !important;
  transform: translateY(-2px) scale(1.2);
}

/* 选中/激活状态 */
.header-menu .el-menu-item.is-active {
  background-color: transparent !important;
  color: #0056b3 !important;
  transform: translateY(-2px) scale(1.2) !important;
  border-bottom: none !important;
}

/* 移除 Element Plus 默认的底部边划线 */
.el-menu--horizontal {
  border-bottom: none !important;
}

.el-menu--horizontal > .el-menu-item.is-active {
  border-bottom: none !important;
}

/* Override Element Plus internal flex so items stay compact */
.header-menu > li {
  flex-grow: 0 !important;
}

/* Responsive */
@media (max-width: 768px) {
  .header-menu {
    padding: 0 16px;
  }
  .logo-text {
    display: none;
  }
  .back-to-top {
    bottom: 20px;
    right: 20px;
    width: 40px;
    height: 40px;
  }
}
</style>
