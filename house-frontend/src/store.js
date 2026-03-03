import { reactive } from 'vue'

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
  green_rate: 25,
  decoration: '精装',
  floor: '中',
  direction: '南',
  year: '',
  enablePrediction: false, // 是否开启大语言模型预测微调

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
    this.green_rate = 25
    this.decoration = '精装'
    this.floor = '中'
    this.direction = '南'
    this.year = ''
    this.enablePrediction = false
  }
})
