<script setup>
import { ref, reactive } from 'vue'
import { houseStore } from './store'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const router = useRouter()

const changePasswordDialogVisible = ref(false)
const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const handleLogout = () => {
  houseStore.logout()
  router.push('/')
}

const showChangePassword = () => {
  changePasswordDialogVisible.value = true
}

const handleChangePassword = async () => {
  if (passwordForm.newPassword !== passwordForm.confirmPassword) {
    ElMessage.error('两次输入的新密码不一致')
    return
  }
  
  try {
    const response = await axios.post('http://localhost:5000/api/change_password', {
      username: houseStore.user.username,
      old_password: passwordForm.oldPassword,
      new_password: passwordForm.newPassword
    })
    
    if (response.data.success) {
      ElMessage.success('密码修改成功')
      changePasswordDialogVisible.value = false
      // 重置表单
      passwordForm.oldPassword = ''
      passwordForm.newPassword = ''
      passwordForm.confirmPassword = ''
    } else {
      ElMessage.error(response.data.error || '修改密码失败')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '请求失败')
  }
}
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
                <el-avatar :size="32" icon="User" />
                <span class="username">{{ houseStore.user?.username }}</span>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item v-if="houseStore.user?.username === 'admin'" @click="$router.push('/admin')">系统管理</el-dropdown-item>
                  <el-dropdown-item @click="showChangePassword">修改密码</el-dropdown-item>
                  <el-dropdown-item divided @click="handleLogout">退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
          <el-button v-else type="primary" round @click="$router.push('/login')" class="login-nav-btn">
            登录 / 注册
          </el-button>
        </div>
      </el-menu>

      <!-- 修改密码对话框 -->
      <el-dialog
        v-model="changePasswordDialogVisible"
        title="修改密码"
        width="400px"
        center
        destroy-on-close
      >
        <el-form label-position="top">
          <el-form-item label="当前密码">
            <el-input v-model="passwordForm.oldPassword" type="password" show-password />
          </el-form-item>
          <el-form-item label="新密码">
            <el-input v-model="passwordForm.newPassword" type="password" show-password />
          </el-form-item>
          <el-form-item label="确认新密码">
            <el-input v-model="passwordForm.confirmPassword" type="password" show-password />
          </el-form-item>
        </el-form>
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="changePasswordDialogVisible = false">取消</el-button>
            <el-button type="primary" @click="handleChangePassword">确定</el-button>
          </span>
        </template>
      </el-dialog>

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
  margin-top: 5px; /* 下移一点 */
}

.logo-image {
  height: 54px; /* 稍微缩小一点防止撑开 header */
  width: auto;
  margin-right: 12px;
}

.logo-text {
  color: #303133;
  font-size: 1.5rem;
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

.header-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  padding-right: 20px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  outline: none;
}

.username {
  font-weight: 500;
  color: #303133;
}

.login-nav-btn {
  padding: 8px 20px;
  font-weight: 600;
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
