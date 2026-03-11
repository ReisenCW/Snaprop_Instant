<script setup>
import { ref, onMounted, reactive } from 'vue'
import { houseStore } from '@/store'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, Download, User, Document, Upload } from '@element-plus/icons-vue'
import axios from 'axios'
import { API_BASE_URL } from '@/config'

const activeTab = ref('users')
const users = ref([])
const reports = ref([])
const uploadLoading = ref(false)
const manualEntryLoading = ref(false)

const citiesList = ref(['上海', '北京'])
const showAddCityDialog = ref(false)
const cityForm = reactive({
  city_name: '',
  table_name: '',
  introduction: '',
  detail: ''
})

const manualForm = reactive({
  city: '上海',
  house_type: '3室2厅',
  house_floor: '中楼层 (共20层)',
  house_direction: '南',
  house_area: 100,
  house_structure: '平层',
  house_decoration: '精装',
  transaction_type: '挂牌',
  transaction_time: new Date().toISOString().split('T')[0],
  is_elevator: '有',
  house_year: 2010,
  green_rate: '35%',
  house_loc: '',
  house_position: '',
  u_price: 50000,
  t_price: 500,
  detail_url: ''
})

// --- City Management ---
const fetchCities = async () => {
  try {
    const res = await axios.get(`${API_BASE_URL}/api/cities`)
    if (res.data.success) citiesList.value = res.data.cities
  } catch (err) {
    console.error('Fetch cities error:', err)
  }
}

const handleAddCity = async () => {
  try {
    const res = await axios.post(`${API_BASE_URL}/api/admin/add_city`, cityForm)
    if (res.data.success) {
      ElMessage.success('城市及数据表创建成功')
      showAddCityDialog.value = false
      fetchCities()
    }
  } catch (err) {
    ElMessage.error('创建失败')
  }
}

// --- User Management ---
const fetchUsers = async () => {
  try {
    const res = await axios.get(`${API_BASE_URL}/api/admin/users`)
    if (res.data.success) users.value = res.data.users
  } catch (err) {
    ElMessage.error('加载用户失败')
  }
}

const handleDeleteUser = (username) => {
  ElMessageBox.confirm(`确定要删除用户 ${username} 吗？其关联的所有报告也将被删除。`, '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    const res = await axios.delete(`${API_BASE_URL}/api/admin/users`, { params: { username } })
    if (res.data.success) {
      ElMessage.success('用户已删除')
      fetchUsers()
    }
  })
}

// --- Report Management ---
const fetchReports = async () => {
  try {
    const res = await axios.get(`${API_BASE_URL}/api/admin/reports`)
    if (res.data.success) reports.value = res.data.reports
  } catch (err) {
    ElMessage.error('加载报告失败')
  }
}

const handleDeleteReport = (reportId) => {
  ElMessageBox.confirm('确定要删除这条报告记录吗？', '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    const res = await axios.delete(`${API_BASE_URL}/api/admin/reports`, { params: { report_id: reportId } })
    if (res.data.success) {
      ElMessage.success('报告已删除')
      fetchReports()
    }
  })
}

// --- Data Management ---
const handleExcelUpload = (file) => {
  const formData = new FormData()
  formData.append('file', file.raw)
  formData.append('city', manualForm.city)

  uploadLoading.value = true
  axios.post(`${API_BASE_URL}/api/admin/upload_excel`, formData)
    .then(res => {
      if (res.data.success) ElMessage.success(res.data.message)
    })
    .catch(() => ElMessage.error('上传失败'))
    .finally(() => uploadLoading.value = false)
}

const submitManualEntry = async () => {
  manualEntryLoading.value = true
  try {
    const res = await axios.post(`${API_BASE_URL}/api/admin/manual_entry`, manualForm)
    if (res.data.success) {
      ElMessage.success('成交数据添加成功')
      // Reset some fields
      manualForm.house_loc = ''
      manualForm.house_position = ''
      manualForm.u_price = 0
      manualForm.t_price = 0
    }
  } catch (err) {
    ElMessage.error('添加失败')
  } finally {
    manualEntryLoading.value = false
  }
}

onMounted(() => {
  if (houseStore.user?.username !== 'admin') {
    ElMessage.error('权限不足')
    return
  }
  fetchUsers()
  fetchReports()
  fetchCities()
})
</script>

<template>
  <div class="admin-container">
    <div class="admin-header">
      <h1 class="admin-title">系统管理中心</h1>
      <p class="admin-subtitle">管理用户、审核报告并更新房产历史数据</p>
    </div>

    <el-card class="admin-card">
      <el-tabs v-model="activeTab" type="border-card">
        <!-- 用户管理 -->
        <el-tab-pane label="用户管理" name="users">
          <template #label>
            <el-icon><User /></el-icon> <span>用户管理</span>
          </template>
          <el-table :data="users" stripe style="width: 100%">
            <el-table-column prop="username" label="用户名" width="180" />
            <el-table-column prop="email" label="邮箱" width="220" />
            <el-table-column prop="created_at" label="注册时间" />
            <el-table-column label="操作" width="120" align="center">
              <template #default="scope">
                <el-button type="danger" :icon="Delete" circle @click="handleDeleteUser(scope.row.username)" />
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- 报告管理 -->
        <el-tab-pane label="报告管理" name="reports">
          <template #label>
            <el-icon><Document /></el-icon> <span>报告管理</span>
          </template>
          <el-table :data="reports" stripe style="width: 100%">
            <el-table-column prop="report_id" label="报告ID" width="150" show-overflow-tooltip />
            <el-table-column prop="username" label="关联用户" width="120" />
            <el-table-column prop="city" label="城市" width="80" />
            <el-table-column prop="address" label="房产地址" min-width="200" show-overflow-tooltip />
            <el-table-column prop="total_price" label="总价 (万)" width="120" align="center">
              <template #default="scope">
                <span class="price-val">{{ (scope.row.total_price / 10000).toFixed(2) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="generated_at" label="生成时间" width="180" />
            <el-table-column label="操作" width="150" align="center">
              <template #default="scope">
                <el-button type="primary" size="small" @click="window.open(`${API_BASE_URL}${scope.row.pdf_url}`, '_blank')" v-if="scope.row.pdf_url">查看PDF</el-button>
                <el-button type="danger" :icon="Delete" circle @click="handleDeleteReport(scope.row.report_id)" />
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- 数据管理 -->
        <el-tab-pane label="数据更新" name="data">
          <template #label>
            <el-icon><Plus /></el-icon> <span>数据更新</span>
          </template>
          
          <el-row :gutter="40">
            <!-- Excel Upload and City Add -->
            <el-col :span="10">
              <div class="data-section">
                <div class="section-header">
                  <h3>批量导入 (Excel)</h3>
                  <el-button type="success" size="small" @click="showAddCityDialog = true">添加城市</el-button>
                </div>
                <el-form label-position="top">
                  <el-form-item label="目标城市">
                    <el-select v-model="manualForm.city" placeholder="请选择城市" style="width: 100%">
                      <el-option v-for="c in citiesList" :key="c" :label="c" :value="c" />
                    </el-select>
                  </el-form-item>
                  <el-upload
                    class="excel-upload-box"
                    drag
                    action=""
                    :auto-upload="false"
                    :on-change="handleExcelUpload"
                    accept=".xlsx, .xls"
                  >
                    <el-icon class="el-icon--upload"><upload-filled /></el-icon>
                    <div class="el-upload__text">
                      将 Excel 文件拖到此处，或 <em>点击上传</em>
                    </div>
                  </el-upload>
                  <p class="upload-tip">请确保 Excel 列名与数据库字段一致</p>
                </el-form>
              </div>
            </el-col>

            <!-- Manual Entry -->
            <el-col :span="14">
              <div class="data-section">
                <h3>手动单条录入</h3>
                <el-form :model="manualForm" label-width="80px" size="small">
                  <el-row :gutter="20">
                    <el-col :span="12">
                      <el-form-item label="城市">
                        <el-select v-model="manualForm.city" style="width: 100%">
                          <el-option v-for="c in citiesList" :key="c" :label="c" :value="c" />
                        </el-select>
                      </el-form-item>
                    </el-col>
                    <el-col :span="12">
                      <el-form-item label="户型">
                        <el-input v-model="manualForm.house_type" placeholder="如: 3室2厅" />
                      </el-form-item>
                    </el-col>
                  </el-row>

                  <el-row :gutter="20">
                    <el-col :span="12">
                      <el-form-item label="楼层">
                        <el-input v-model="manualForm.house_floor" placeholder="如: 中楼层" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="12">
                      <el-form-item label="朝向">
                        <el-input v-model="manualForm.house_direction" placeholder="如: 南" />
                      </el-form-item>
                    </el-col>
                  </el-row>

                  <el-row :gutter="20">
                    <el-col :span="12">
                      <el-form-item label="面积 (㎡)">
                        <el-input-number v-model="manualForm.house_area" :precision="2" style="width: 100%" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="12">
                      <el-form-item label="结构">
                        <el-input v-model="manualForm.house_structure" placeholder="如: 平层" />
                      </el-form-item>
                    </el-col>
                  </el-row>

                  <el-row :gutter="20">
                    <el-col :span="12">
                      <el-form-item label="成交类型">
                        <el-select v-model="manualForm.transaction_type" style="width: 100%">
                          <el-option label="挂牌" value="挂牌" />
                          <el-option label="成交" value="成交" />
                        </el-select>
                      </el-form-item>
                    </el-col>
                    <el-col :span="12">
                      <el-form-item label="成交时间">
                        <el-date-picker v-model="manualForm.transaction_time" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
                      </el-form-item>
                    </el-col>
                  </el-row>

                  <el-row :gutter="20">
                    <el-col :span="12">
                      <el-form-item label="装修">
                        <el-input v-model="manualForm.house_decoration" placeholder="如: 精装" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="12">
                      <el-form-item label="电梯">
                        <el-radio-group v-model="manualForm.is_elevator">
                          <el-radio label="有">有</el-radio>
                          <el-radio label="无">无</el-radio>
                        </el-radio-group>
                      </el-form-item>
                    </el-col>
                  </el-row>

                  <el-row :gutter="20">
                    <el-col :span="12">
                      <el-form-item label="建成年份">
                        <el-input-number v-model="manualForm.house_year" :controls="false" style="width: 100%" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="12">
                      <el-form-item label="绿化率">
                        <el-input v-model="manualForm.green_rate" placeholder="如: 35%" />
                      </el-form-item>
                    </el-col>
                  </el-row>

                  <el-row :gutter="20">
                    <el-col :span="12">
                      <el-form-item label="单价 (元)">
                        <el-input-number v-model="manualForm.u_price" :controls="false" style="width: 100%" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="12">
                      <el-form-item label="总价 (万)">
                        <el-input-number v-model="manualForm.t_price" :controls="false" style="width: 100%" />
                      </el-form-item>
                    </el-col>
                  </el-row>

                  <el-form-item label="具体位置">
                    <el-input v-model="manualForm.house_loc" placeholder="小区名称, 如: 仁恒森兰雅苑(一期)" />
                  </el-form-item>
                  <el-form-item label="板块/商圈">
                    <el-input v-model="manualForm.house_position" placeholder="如: 浦东 高行 中环至外环" />
                  </el-form-item>
                  <el-form-item label="详情URL">
                    <el-input v-model="manualForm.detail_url" placeholder="如: https://sh.lianjia.com/..." />
                  </el-form-item>

                  <div style="text-align: right; margin-top: 10px;">
                    <el-button type="primary" @click="submitManualEntry" :loading="manualEntryLoading" style="width: 200px">提交数据记录</el-button>
                  </div>
                </el-form>
              </div>
            </el-col>
          </el-row>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- Add City Dialog -->
    <el-dialog v-model="showAddCityDialog" title="开设新城市" width="500px">
      <el-form :model="cityForm" label-width="100px">
        <el-form-item label="城市名称">
          <el-input v-model="cityForm.city_name" placeholder="如: 广州" />
        </el-form-item>
        <el-form-item label="数据表名">
          <el-input v-model="cityForm.table_name" placeholder="如: guangzhou" />
        </el-form-item>
        <el-form-item label="简短介绍">
          <el-input v-model="cityForm.introduction" type="textarea" placeholder="城市地理位置介绍" />
        </el-form-item>
        <el-form-item label="详细说明">
          <el-input v-model="cityForm.detail" type="textarea" :rows="4" placeholder="城市下辖区、面积等详细信息" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddCityDialog = false">取消</el-button>
        <el-button type="primary" @click="handleAddCity">确认创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
/* Keep existing styles, add some new ones */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.data-section h3 {
  margin-bottom: 0;
}
</style>

<style scoped>
.admin-container {
  padding: 40px;
  background-color: #f5f7fa;
  min-height: 100vh;
}

.admin-header {
  margin-bottom: 30px;
  text-align: center;
}

.admin-title {
  font-size: 2.2rem;
  font-weight: 700;
  color: #303133;
  margin-bottom: 10px;
}

.admin-subtitle {
  color: #909399;
  font-size: 1.1rem;
}

.admin-card {
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(0,0,0,0.05);
}

.price-val {
  color: #f56c6c;
  font-weight: 600;
}

.data-section {
  padding: 10px;
}

.data-section h3 {
  margin-bottom: 20px;
  color: #409eff;
  border-bottom: 2px solid #ecf5ff;
  padding-bottom: 10px;
}

.excel-upload-box {
  margin-bottom: 10px;
}

.upload-tip {
  font-size: 12px;
  color: #999;
  text-align: center;
}
</style>
