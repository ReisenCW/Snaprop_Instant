<template>
  <div class="login-container">
    <div class="login-box">
      <div class="login-header">
        <h2>{{ isLogin ? '用户登录' : '用户注册' }}</h2>
        <p>{{ isLogin ? '欢迎回来，请登录您的账号' : '加入我们，开启便捷房产估值' }}</p>
      </div>

      <el-form :model="form" :rules="rules" ref="formRef" label-position="top" class="login-form">
        <!-- 注册需要邮箱 -->
        <el-form-item v-if="!isLogin" label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" prefix-icon="Message" />
        </el-form-item>

        <!-- 登录/注册都需要用户名 -->
        <el-form-item :label="isLogin ? '用户名 / 邮箱' : '用户名'" prop="account">
          <el-input v-model="form.account" :placeholder="isLogin ? '请输入用户名或邮箱' : '请输入用户名'" prefix-icon="User" />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" prefix-icon="Lock" show-password />
        </el-form-item>

        <!-- 注册需要确认密码 -->
        <el-form-item v-if="!isLogin" label="确认密码" prop="confirm_password">
          <el-input v-model="form.confirm_password" type="password" placeholder="请再次输入密码" prefix-icon="CircleCheck" show-password />
        </el-form-item>

        <div class="form-actions">
          <el-button type="primary" :loading="loading" @click="handleSubmit" class="submit-btn">
            {{ isLogin ? '立即登录' : '立即注册' }}
          </el-button>
        </div>

        <div class="login-footer">
          <span>{{ isLogin ? '还没有账号？' : '已有账号？' }}</span>
          <el-button link type="primary" @click="toggleMode">
            {{ isLogin ? '去注册' : '去登录' }}
          </el-button>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import { houseStore } from '../store'

const router = useRouter()
const isLogin = ref(true)
const loading = ref(false)
const formRef = ref(null)

const form = reactive({
  account: '',
  email: '',
  password: '',
  confirm_password: ''
})

const rules = computed(() => {
  const baseRules = {
    account: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
    password: [{ required: true, message: '请输入密码', trigger: 'blur' }, { min: 6, message: '密码不能少于6位', trigger: 'blur' }]
  }
  
  if (!isLogin.value) {
    return {
      ...baseRules,
      email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }, { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }],
      confirm_password: [
        { required: true, message: '请确认密码', trigger: 'blur' },
        {
          validator: (rule, value, callback) => {
            if (value !== form.password) {
              callback(new Error('两次输入的密码不一致'))
            } else {
              callback()
            }
          },
          trigger: 'blur'
        }
      ]
    }
  }
  return baseRules
})

const toggleMode = () => {
  isLogin.value = !isLogin.value
  formRef.value.resetFields()
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return

    loading.value = true
    try {
      const url = isLogin.value ? 'http://localhost:5000/api/login' : 'http://localhost:5000/api/register'
      const payload = isLogin.value 
        ? { account: form.account, password: form.password }
        : { username: form.account, email: form.email, password: form.password, confirm_password: form.confirm_password }

      const response = await axios.post(url, payload)
      const data = response.data

      if (data.success) {
        if (isLogin.value) {
          ElMessage.success('登录成功')
          houseStore.login(data.user)
          router.push('/')
        } else {
          ElMessage.success('注册成功，请登录')
          isLogin.value = true
        }
      } else {
        ElMessage.error(data.error || (isLogin.value ? '登录失败' : '注册失败'))
      }
    } catch (error) {
      console.error(error)
      const errorMsg = error.response?.data?.error || '请求失败，请稍后重试'
      ElMessage.error(errorMsg)
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  padding: 20px;
}

.login-box {
  width: 100%;
  max-width: 440px;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  padding: 40px;
  border-radius: 16px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.login-header {
  text-align: center;
  margin-bottom: 30px;
}

.login-header h2 {
  font-size: 28px;
  color: #2c3e50;
  margin-bottom: 10px;
  font-weight: 700;
}

.login-header p {
  color: #7f8c8d;
  font-size: 14px;
}

.login-form {
  margin-top: 20px;
}

.submit-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 8px;
  margin-top: 20px;
  transition: transform 0.2s;
}

.submit-btn:active {
  transform: scale(0.98);
}

.login-footer {
  margin-top: 24px;
  text-align: center;
  color: #7f8c8d;
  font-size: 14px;
}

:deep(.el-input__wrapper) {
  padding: 10px 15px;
  border-radius: 8px;
  box-shadow: 0 0 0 1px #dcdfe6 inset;
}

:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #409eff inset;
}

:deep(.el-form-item__label) {
  font-weight: 500;
  color: #34495e;
}
</style>
