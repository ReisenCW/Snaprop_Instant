import { reactive } from 'vue'

const stored = JSON.parse(localStorage.getItem('user')) || {}

export const houseStore = reactive({
  // Step 1: Basic Info
  address: '',
  city: '',
  area: 100,
  rooms: 3,
  halls: 2,
  kitchens: 1,
  bathrooms: 1,
  structure: '平层',
  green_rate: 35,
  decoration: '精装',
  floor: '中',
  direction: '南',
  year: null,
  enablePrediction: false, // 是否开启大语言模型预测微调
  selectionWeights: null, // 专家权重
  valuationData: null,
  cert_image: '',
  batchResults: null,  // 批量估值结果
  batchExtractions: null,  // 批量OCR识别结果（待确认编辑）

  // Auth state
  user: stored.username ? {
    id: stored.id || null,
    username: stored.username || null,
    email: stored.email || '',
    avatar: stored.avatar || '',
    nickname: stored.nickname || '',
    signature: stored.signature || '',
    phone: stored.phone || ''
  } : null,
  isAuthenticated: !!stored.username,

  // Login action
  login(userData) {
    this.user = {
      id: userData.id || null,
      username: userData.username,
      email: userData.email || '',
      avatar: userData.avatar || '',
      nickname: userData.nickname || '',
      signature: userData.signature || '',
      phone: userData.phone || ''
    }
    this.isAuthenticated = true
    localStorage.setItem('user', JSON.stringify(this.user))
  },

  // Update profile (partial)
  updateProfile(data) {
    if (this.user) {
      Object.assign(this.user, data)
      localStorage.setItem('user', JSON.stringify(this.user))
    }
  },

  // Logout action
  logout() {
    this.user = null
    this.isAuthenticated = false
    localStorage.removeItem('user')
  },

  // Reset function
  reset() {
    this.address = ''
    this.city = ''
    this.area = 100
    this.rooms = 3
    this.halls = 2
    this.kitchens = 1
    this.bathrooms = 1
    this.structure = '平层'
    this.green_rate = 35
    this.decoration = '精装'
    this.floor = '中'
    this.direction = '南'
    this.year = null
    this.enablePrediction = false
    this.selectionWeights = null
    this.valuationData = null
    this.cert_image = ''
    this.batchResults = null
    this.batchExtractions = null
  }
})
