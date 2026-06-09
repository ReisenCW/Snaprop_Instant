<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft, User, EditPen, Camera, Check, Lock, House,
  DataAnalysis
} from '@element-plus/icons-vue'
import 'vue-cropper/dist/index.css'
import { VueCropper } from 'vue-cropper'
import { houseStore } from '@/store'
import { getProfile, updateProfile, uploadAvatar } from '@/api'
import { API_BASE_URL } from '@/config'

const router = useRouter()
const activeTab = ref('info')
const profileLoading = ref(true)
const avatarUploading = ref(false)
const saving = ref(false)

// Cropper state
const cropperVisible = ref(false)
const cropperImg = ref('')
const cropperRef = ref(null)
const pendingAvatarFile = ref(null)

// Stats
const stats = ref({ report_count: 0 })

// Profile form
const form = reactive({
  nickname: '',
  signature: '',
  phone: '',
  email: ''
})

// Password form
const pwdForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})
const changingPwd = ref(false)

// Load profile
const fetchProfile = async () => {
  if (!houseStore.user?.username) {
    router.push('/login')
    return
  }
  profileLoading.value = true
  try {
    const res = await getProfile(houseStore.user.username)
    if (res.data.success) {
      const p = res.data.profile
      form.nickname = p.nickname || ''
      form.signature = p.signature || ''
      form.phone = p.phone || ''
      form.email = p.email || ''
      stats.value = p.stats || { report_count: 0 }
      // Sync to store
      houseStore.updateProfile({
        avatar: p.avatar || '',
        nickname: p.nickname || '',
        signature: p.signature || '',
        phone: p.phone || ''
      })
    }
  } catch (err) {
    ElMessage.error('加载个人资料失败')
  } finally {
    profileLoading.value = false
  }
}

onMounted(() => {
  fetchProfile()
})

const goBack = () => router.back()

const handleSaveProfile = async () => {
  saving.value = true
  try {
    const res = await updateProfile({
      username: houseStore.user.username,
      nickname: form.nickname,
      signature: form.signature,
      phone: form.phone,
      email: form.email
    })
    if (res.data.success) {
      houseStore.updateProfile({
        nickname: form.nickname,
        signature: form.signature,
        phone: form.phone,
        email: form.email
      })
      ElMessage.success('个人资料已保存')
    } else {
      ElMessage.error(res.data.error || '保存失败')
    }
  } catch (err) {
    ElMessage.error('保存失败，请稍后重试')
  } finally {
    saving.value = false
  }
}

const handleAvatarPick = (e) => {
  const file = e.target.files?.[0]
  if (!file) return
  const isImage = file.type.startsWith('image/')
  if (!isImage) {
    ElMessage.error('请上传图片文件 (JPG, PNG)')
    e.target.value = ''
    return
  }
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.error('头像图片不能超过 5MB')
    e.target.value = ''
    return
  }

  pendingAvatarFile.value = file
  const reader = new FileReader()
  reader.onload = (ev) => {
    cropperImg.value = ev.target.result
    cropperVisible.value = true
  }
  reader.readAsDataURL(file)
  e.target.value = ''
}

const confirmCrop = () => {
  if (!cropperRef.value) return
  cropperRef.value.getCropBlob(async (blob) => {
    avatarUploading.value = true
    cropperVisible.value = false
    try {
      const croppedFile = new File([blob], pendingAvatarFile.value.name, { type: 'image/jpeg' })
      const res = await uploadAvatar(croppedFile, houseStore.user.username)
      if (res.data.success) {
        const avatarUrl = res.data.url.startsWith('http')
          ? res.data.url
          : `${API_BASE_URL}${res.data.url}`
        houseStore.updateProfile({ avatar: res.data.url })
        ElMessage.success('头像已更新')
      } else {
        ElMessage.error(res.data.error || '上传失败')
      }
    } catch (err) {
      ElMessage.error('头像上传失败')
    } finally {
      avatarUploading.value = false
      pendingAvatarFile.value = null
    }
  })
}

const handleChangePassword = async () => {
  if (pwdForm.newPassword !== pwdForm.confirmPassword) {
    ElMessage.error('两次输入的新密码不一致')
    return
  }
  if (pwdForm.newPassword.length < 6) {
    ElMessage.error('新密码不能少于6位')
    return
  }
  changingPwd.value = true
  try {
    const axios = (await import('axios')).default
    const res = await axios.post(`${API_BASE_URL}/api/change_password`, {
      username: houseStore.user.username,
      old_password: pwdForm.oldPassword,
      new_password: pwdForm.newPassword
    })
    if (res.data.success) {
      ElMessage.success('密码修改成功，请重新登录')
      pwdForm.oldPassword = ''
      pwdForm.newPassword = ''
      pwdForm.confirmPassword = ''
      setTimeout(() => {
        houseStore.logout()
        router.push('/login')
      }, 1500)
    } else {
      ElMessage.error(res.data.error || '修改密码失败')
    }
  } catch (err) {
    ElMessage.error('请求失败，请稍后重试')
  } finally {
    changingPwd.value = false
  }
}

const userAvatar = () => {
  const av = houseStore.user?.avatar
  if (!av) return ''
  return av.startsWith('http') ? av : `${API_BASE_URL}${av}`
}

const displayName = () => {
  return houseStore.user?.nickname || houseStore.user?.username || '用户'
}
</script>

<template>
  <div class="profile-page">
    <!-- Back nav -->
    <div class="page-top">
      <el-button :icon="ArrowLeft" @click="goBack" round plain>返回</el-button>
      <h1 class="page-title">个人中心</h1>
    </div>

    <div v-loading="profileLoading" class="profile-layout">
      <!-- Left sidebar -->
      <aside class="profile-sidebar">
        <div class="sidebar-card">
          <!-- Avatar -->
          <div class="avatar-section">
            <label class="avatar-wrap" title="点击更换头像">
              <el-avatar :size="100" :src="userAvatar()" class="avatar-img">
                <el-icon :size="48"><User /></el-icon>
              </el-avatar>
              <div class="avatar-overlay">
                <el-icon :size="24"><Camera /></el-icon>
                <span>更换头像</span>
              </div>
              <input
                type="file"
                accept="image/*"
                class="avatar-input"
                @change="handleAvatarPick"
                :disabled="avatarUploading"
              />
            </label>
            <div v-if="avatarUploading" class="uploading-hint">上传中...</div>
          </div>

          <!-- Name & signature -->
          <div class="user-meta">
            <h3 class="user-display-name">{{ displayName() }}</h3>
            <p class="user-username">@{{ houseStore.user?.username }}</p>
            <p class="user-sig">{{ houseStore.user?.signature || '还没有设置个性签名' }}</p>
          </div>

          <!-- Stats -->
          <div class="stats-row">
            <div class="stat-item">
              <el-icon :size="22"><DataAnalysis /></el-icon>
              <span class="stat-num">{{ stats.report_count }}</span>
              <span class="stat-lbl">累计估值</span>
            </div>
            <div class="stat-item">
              <el-icon :size="22"><House /></el-icon>
              <span class="stat-num">{{ stats.report_count }}</span>
              <span class="stat-lbl">生成报告</span>
            </div>
          </div>
        </div>
      </aside>

      <!-- Right content -->
      <main class="profile-main">
        <el-card shadow="never" class="main-card">
          <el-tabs v-model="activeTab" class="profile-tabs">
            <!-- Tab 1: Basic Info -->
            <el-tab-pane label="基本信息" name="info">
              <template #label>
                <span class="tab-label">
                  <el-icon><EditPen /></el-icon> 基本信息
                </span>
              </template>

              <el-form label-position="top" class="profile-form">
                <el-row :gutter="24">
                  <el-col :sm="12" :span="24">
                    <el-form-item label="昵称">
                      <el-input
                        v-model="form.nickname"
                        placeholder="设置一个昵称，让大家认识你"
                        maxlength="30"
                        show-word-limit
                      />
                    </el-form-item>
                  </el-col>
                  <el-col :sm="12" :span="24">
                    <el-form-item label="手机号">
                      <el-input v-model="form.phone" placeholder="输入手机号" maxlength="20" />
                    </el-form-item>
                  </el-col>
                </el-row>

                <el-form-item label="个性签名">
                  <el-input
                    v-model="form.signature"
                    type="textarea"
                    :rows="3"
                    placeholder="写一句话介绍自己..."
                    maxlength="100"
                    show-word-limit
                  />
                </el-form-item>

                <el-form-item label="邮箱">
                  <el-input v-model="form.email" placeholder="your@email.com" />
                </el-form-item>

                <div class="form-actions">
                  <el-button type="primary" :icon="Check" :loading="saving" @click="handleSaveProfile" round>
                    保存修改
                  </el-button>
                </div>
              </el-form>
            </el-tab-pane>

            <!-- Tab 2: Security -->
            <el-tab-pane label="账户安全" name="security">
              <template #label>
                <span class="tab-label">
                  <el-icon><Lock /></el-icon> 账户安全
                </span>
              </template>

              <el-form label-position="top" class="profile-form">
                <el-form-item label="当前密码">
                  <el-input v-model="pwdForm.oldPassword" type="password" show-password placeholder="请输入当前密码" />
                </el-form-item>
                <el-form-item label="新密码">
                  <el-input v-model="pwdForm.newPassword" type="password" show-password placeholder="请输入新密码（至少6位）" />
                </el-form-item>
                <el-form-item label="确认新密码">
                  <el-input v-model="pwdForm.confirmPassword" type="password" show-password placeholder="请再次输入新密码" />
                </el-form-item>

                <div class="form-actions">
                  <el-button type="warning" :icon="Lock" :loading="changingPwd" @click="handleChangePassword" round>
                    修改密码
                  </el-button>
                </div>
              </el-form>
            </el-tab-pane>
          </el-tabs>
        </el-card>
      </main>
    </div>

    <!-- Cropper Dialog -->
    <el-dialog v-model="cropperVisible" title="裁剪头像" width="520px" align-center :close-on-click-modal="false">
      <div class="cropper-wrapper">
        <vue-cropper
          ref="cropperRef"
          :img="cropperImg"
          :autoCrop="true"
          :autoCropWidth="200"
          :autoCropHeight="200"
          :fixed="true"
          :fixedNumber="[1, 1]"
          :centerBox="true"
          :info="true"
          outputType="jpeg"
          style="height: 360px"
        />
      </div>
      <template #footer>
        <el-button @click="cropperVisible = false">取消</el-button>
        <el-button type="primary" :loading="avatarUploading" @click="confirmCrop">确认裁剪并上传</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.profile-page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 30px 40px;
  min-height: 80vh;
  animation: fadeSlideIn 0.45s ease-out;
}

@keyframes fadeSlideIn {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

.page-top {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 32px;
}

.page-title {
  font-size: 1.8rem;
  font-weight: 700;
  color: #2c3e50;
  margin: 0;
}

/* Layout */
.profile-layout {
  display: flex;
  gap: 28px;
  align-items: flex-start;
}

/* Sidebar */
.profile-sidebar {
  width: 280px;
  flex-shrink: 0;
}

.sidebar-card {
  background: white;
  border-radius: 20px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.05);
  padding: 36px 24px;
  text-align: center;
}

/* Avatar */
.avatar-section {
  margin-bottom: 20px;
}

.avatar-wrap {
  position: relative;
  display: inline-block;
  cursor: pointer;
  border-radius: 50%;
  overflow: hidden;
}

.avatar-img {
  transition: filter 0.3s ease;
}

.avatar-wrap:hover .avatar-img {
  filter: brightness(0.75);
}

.avatar-overlay {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  background: rgba(0,0,0,0.45);
  color: white;
  font-size: 13px;
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
}

.avatar-wrap:hover .avatar-overlay {
  opacity: 1;
}

.avatar-input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.uploading-hint {
  margin-top: 8px;
  font-size: 12px;
  color: #409eff;
}

/* User meta */
.user-meta {
  margin-bottom: 24px;
}

.user-display-name {
  font-size: 1.2rem;
  font-weight: 700;
  color: #303133;
  margin: 0 0 4px;
}

.user-username {
  font-size: 0.9rem;
  color: #909399;
  margin: 0 0 8px;
}

.user-sig {
  font-size: 0.9rem;
  color: #606266;
  line-height: 1.5;
  margin: 0;
  font-style: italic;
}

/* Stats */
.stats-row {
  display: flex;
  border-top: 1px solid #ebeef5;
  padding-top: 20px;
  gap: 12px;
}

.stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 10px 0;
  background: #f8fafc;
  border-radius: 12px;
}

.stat-num {
  font-size: 1.6rem;
  font-weight: 800;
  color: #409eff;
}

.stat-lbl {
  font-size: 0.8rem;
  color: #909399;
}

/* Main */
.profile-main {
  flex: 1;
  min-width: 0;
}

.main-card {
  border-radius: 20px;
  border: 1px solid #ebeef5;
  box-shadow: 0 4px 16px rgba(0,0,0,0.04);
}

.profile-tabs :deep(.el-tabs__header) {
  margin-bottom: 8px;
  padding: 0 12px;
}

.tab-label {
  display: flex;
  align-items: center;
  gap: 6px;
}

.profile-form {
  padding: 8px 8px 0;
}

.form-actions {
  padding-top: 12px;
  border-top: 1px solid #f0f2f5;
  text-align: right;
}

/* Cropper */
.cropper-wrapper {
  height: 360px;
  border-radius: 12px;
  overflow: hidden;
}

/* Responsive */
@media (max-width: 768px) {
  .profile-page {
    padding: 20px 14px;
  }
  .profile-layout {
    flex-direction: column;
  }
  .profile-sidebar {
    width: 100%;
  }
  .sidebar-card {
    padding: 24px 18px;
  }
  .stats-row {
    flex-direction: row;
  }
  .page-title {
    font-size: 1.4rem;
  }
}
</style>
