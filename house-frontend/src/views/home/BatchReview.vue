<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Edit, Check, Close } from '@element-plus/icons-vue'
import { startValuation } from '@/api'
import { houseStore } from '@/store'

const router = useRouter()

// Extraction records: { name, status, data: {address, city, area, room, hall, kitchen, bathroom, floor, fitment, structure, direction, year, green_rate}, cert_image }
const extractions = ref([])
const processing = ref(false)
const progress = ref(0)
const progressText = ref('')

// Edit dialog
const editVisible = ref(false)
const editingIndex = ref(-1)
const editForm = ref({})

const FIELD_META = [
  { key: 'address', label: '地址', type: 'text', placeholder: '小区或街道地址' },
  { key: 'city', label: '城市', type: 'text', placeholder: '如：上海' },
  { key: 'area', label: '面积 (㎡)', type: 'number', placeholder: '建筑面积' },
  { key: 'room', label: '室', type: 'number', placeholder: '卧室数量' },
  { key: 'hall', label: '厅', type: 'number', placeholder: '客厅数量' },
  { key: 'kitchen', label: '厨', type: 'number', placeholder: '厨房数量' },
  { key: 'bathroom', label: '卫', type: 'number', placeholder: '卫生间数量' },
  { key: 'floor', label: '楼层', type: 'select', options: ['低楼层', '中楼层', '高楼层'] },
  { key: 'fitment', label: '装修', type: 'select', options: ['精装', '简装', '毛坯'] },
  { key: 'structure', label: '结构', type: 'select', options: ['平层', '复式'] },
  { key: 'direction', label: '朝向', type: 'select', options: ['南', '东南', '西南', '东', '西', '北', '南北'] },
  { key: 'year', label: '建成年份', type: 'number', placeholder: '如：2015' },
  { key: 'green_rate', label: '绿化率 (%)', type: 'number', placeholder: '如：35' },
]

const successExtractions = computed(() => extractions.value.filter(e => e.status === 'success'))
const failedExtractions = computed(() => extractions.value.filter(e => e.status === 'failed'))

onMounted(() => {
  if (houseStore.batchExtractions && houseStore.batchExtractions.length > 0) {
    extractions.value = houseStore.batchExtractions
  } else {
    ElMessage.warning('未找到OCR识别结果，请先上传产证')
    router.replace('/home/batch')
  }
})

const openEdit = (index) => {
  editingIndex.value = index
  editForm.value = { ...extractions.value[index].data }
  editVisible.value = true
}

const saveEdit = () => {
  if (editingIndex.value >= 0) {
    extractions.value[editingIndex.value].data = { ...editForm.value }
    // Persist back to store
    houseStore.batchExtractions = [...extractions.value]
  }
  editVisible.value = false
}

const cancelEdit = () => {
  editVisible.value = false
}

const formatValue = (row, key) => {
  const val = row.data?.[key]
  if (val === undefined || val === null || val === '') return '-'
  if (key === 'area') return val + '㎡'
  if (key === 'room') return val + '室'
  if (key === 'hall') return val + '厅'
  if (key === 'year' && typeof val === 'string' && val.includes('年')) return val
  if (key === 'green_rate') return val + '%'
  return val
}

const houseTypeLabel = (row) => {
  const r = row.data?.room || '-'
  const h = row.data?.hall || '-'
  const k = row.data?.kitchen || 1
  const b = row.data?.bathroom || 1
  return `${r}室${h}厅${k}厨${b}卫`
}

const startBatchValuation = async () => {
  const list = successExtractions.value
  if (list.length === 0) {
    ElMessage.warning('没有可估值的房产数据')
    return
  }

  processing.value = true
  progress.value = 0
  const results = []

  for (let i = 0; i < list.length; i++) {
    const item = list[i]
    const d = item.data
    progressText.value = `正在估值第 ${i + 1}/${list.length} 套: ${d.address || item.name}`

    try {
      const valuationRes = await startValuation({
        address: d.address || '',
        city: d.city || '上海',
        area: d.area || 100,
        room: d.room || 3,
        hall: d.hall || 2,
        kitchen: d.kitchen || 1,
        bathroom: d.bathroom || 1,
        floor: d.floor || '中楼层',
        fitment: d.fitment || '精装',
        structure: d.structure || '平层',
        direction: d.direction || '南',
        year: d.year || 2015,
        green_rate: d.green_rate || 35,
        cert_image: item.cert_image || '',
        enable_prediction: false
      })

      if (valuationRes.data.success) {
        const valData = valuationRes.data.data
        results.push({
          name: item.name,
          status: 'success',
          address: valData.property_data?.address || d.address || '-',
          area: valData.property_data?.area || d.area || '-',
          houseType: valData.property_data?.house_type || houseTypeLabel(item),
          unitPrice: valData.estimation_result?.estimated_price || 0,
          totalPrice: valData.total_price || 0
        })
      } else {
        results.push({
          name: item.name,
          status: 'failed',
          error: valuationRes.data.error || '估值失败'
        })
      }
    } catch (err) {
      results.push({
        name: item.name,
        status: 'failed',
        error: err.message || '网络错误'
      })
    }

    progress.value = Math.round(((i + 1) / list.length) * 100)
  }

  // Also add failed OCR items to results
  for (const f of failedExtractions.value) {
    results.push({ name: f.name, status: 'failed', error: f.error || 'OCR识别失败' })
  }

  processing.value = false
  progressText.value = ''

  const successCount = results.filter(r => r.status === 'success').length
  if (successCount > 0) {
    ElMessage.success(`批量估值完成！成功 ${successCount}/${results.length}`)
    houseStore.batchResults = results
    setTimeout(() => router.push('/home/batch-results'), 800)
  } else {
    ElMessage.error('所有房产估值失败，请检查数据后重试')
  }
}

const goBack = () => {
  router.push('/home/batch')
}
</script>

<template>
  <div class="batch-review-container">
    <div class="page-header">
      <el-button :icon="ArrowLeft" @click="goBack" round plain>返回上传</el-button>
      <div class="header-text">
        <h1 class="page-title">确认房产信息</h1>
        <p class="page-desc">请核对并修改 OCR 识别的房产信息，确认无误后开始批量估值</p>
      </div>
    </div>

    <!-- Success extractions table -->
    <div v-if="successExtractions.length > 0" class="review-card">
      <div class="review-toolbar">
        <span class="review-count">
          识别成功 <strong>{{ successExtractions.length }}</strong> 份
          <template v-if="failedExtractions.length">，失败 <strong style="color:#f56c6c">{{ failedExtractions.length }}</strong> 份</template>
        </span>
      </div>

      <el-table :data="successExtractions" stripe border style="width: 100%">
        <el-table-column type="index" label="#" width="50" />
        <el-table-column label="文件名" min-width="140">
          <template #default="{ row }">{{ row.name }}</template>
        </el-table-column>
        <el-table-column label="地址" min-width="180">
          <template #default="{ row }">{{ formatValue(row, 'address') }}</template>
        </el-table-column>
        <el-table-column label="面积" width="90" align="center">
          <template #default="{ row }">{{ formatValue(row, 'area') }}</template>
        </el-table-column>
        <el-table-column label="户型" width="110" align="center">
          <template #default="{ row }">{{ houseTypeLabel(row) }}</template>
        </el-table-column>
        <el-table-column label="楼层" width="90" align="center">
          <template #default="{ row }">{{ formatValue(row, 'floor') }}</template>
        </el-table-column>
        <el-table-column label="装修" width="80" align="center">
          <template #default="{ row }">{{ formatValue(row, 'fitment') }}</template>
        </el-table-column>
        <el-table-column label="朝向" width="70" align="center">
          <template #default="{ row }">{{ formatValue(row, 'direction') }}</template>
        </el-table-column>
        <el-table-column label="操作" width="90" align="center" fixed="right">
          <template #default="{ row, $index }">
            <el-button type="primary" link :icon="Edit" @click="openEdit($index)">
              编辑
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- Action -->
      <div class="review-actions">
        <el-button size="large" round @click="goBack">返回重新上传</el-button>
        <el-button
          type="primary"
          size="large"
          round
          :loading="processing"
          @click="startBatchValuation"
        >
          {{ processing ? '估值中...' : `确认无误，开始批量估值 (${successExtractions.length} 套)` }}
        </el-button>
      </div>

      <!-- Valuation progress -->
      <div v-if="processing" class="valuation-progress">
        <el-progress :percentage="progress" :stroke-width="10" />
        <p class="progress-text">{{ progressText }}</p>
      </div>
    </div>

    <!-- Failed extractions -->
    <div v-if="failedExtractions.length > 0" class="failed-card">
      <h3>识别失败 ({{ failedExtractions.length }})</h3>
      <el-table :data="failedExtractions" size="small" stripe>
        <el-table-column prop="name" label="文件名" min-width="200" />
        <el-table-column prop="error" label="错误原因" min-width="200" />
      </el-table>
    </div>

    <!-- All failed -->
    <div v-if="extractions.length > 0 && successExtractions.length === 0" class="all-failed">
      <p>所有产证 OCR 识别均失败</p>
      <el-button type="primary" round @click="goBack">返回重新上传</el-button>
    </div>

    <!-- Edit Dialog -->
    <el-dialog v-model="editVisible" title="编辑房产信息" width="560px" :close-on-click-modal="false" align-center>
      <el-form label-position="top" class="edit-form">
        <el-row :gutter="16">
          <el-col :span="24">
            <el-form-item label="地址">
              <el-input v-model="editForm.address" placeholder="小区或街道地址" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="城市">
              <el-input v-model="editForm.city" placeholder="如：上海" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="面积 (㎡)">
              <el-input-number v-model="editForm.area" :min="10" :max="1000" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="6">
            <el-form-item label="室">
              <el-input-number v-model="editForm.room" :min="0" :max="10" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="厅">
              <el-input-number v-model="editForm.hall" :min="0" :max="10" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="厨">
              <el-input-number v-model="editForm.kitchen" :min="0" :max="5" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="卫">
              <el-input-number v-model="editForm.bathroom" :min="0" :max="5" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="楼层">
              <el-select v-model="editForm.floor" style="width:100%">
                <el-option v-for="o in ['低楼层','中楼层','高楼层']" :key="o" :value="o" :label="o" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="装修">
              <el-select v-model="editForm.fitment" style="width:100%">
                <el-option v-for="o in ['精装','简装','毛坯']" :key="o" :value="o" :label="o" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="结构">
              <el-select v-model="editForm.structure" style="width:100%">
                <el-option v-for="o in ['平层','复式']" :key="o" :value="o" :label="o" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="朝向">
              <el-select v-model="editForm.direction" style="width:100%">
                <el-option v-for="o in ['南','东南','西南','东','西','北','南北']" :key="o" :value="o" :label="o" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="建成年份">
              <el-input-number v-model="editForm.year" :min="1980" :max="2030" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="绿化率 (%)">
              <el-input-number v-model="editForm.green_rate" :min="0" :max="100" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button :icon="Close" @click="cancelEdit">取消</el-button>
        <el-button type="primary" :icon="Check" @click="saveEdit">确认修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.batch-review-container {
  max-width: 1000px;
  margin: 0 auto;
  padding: 30px 20px;
  animation: fadeSlideIn 0.5s ease-out;
}

@keyframes fadeSlideIn {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

.page-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 28px;
}

.header-text {
  flex: 1;
}

.page-title {
  font-size: 1.6rem;
  font-weight: 800;
  color: #2c3e50;
  margin: 0 0 4px;
}

.page-desc {
  font-size: 0.95rem;
  color: #909399;
  margin: 0;
}

.review-card {
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.05);
  margin-bottom: 24px;
}

.review-toolbar {
  margin-bottom: 16px;
}

.review-count {
  font-size: 1rem;
  color: #303133;
}

.review-actions {
  margin-top: 24px;
  display: flex;
  justify-content: center;
  gap: 16px;
}

.valuation-progress {
  margin-top: 24px;
  text-align: center;
}

.progress-text {
  margin-top: 10px;
  font-size: 0.9rem;
  color: #606266;
}

.failed-card {
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.05);
  margin-bottom: 24px;
}

.failed-card h3 {
  margin: 0 0 14px;
  font-size: 1rem;
  color: #e6a23c;
}

.all-failed {
  text-align: center;
  padding: 48px 20px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}

.all-failed p {
  font-size: 1.1rem;
  color: #909399;
  margin: 0 0 20px;
}

.edit-form {
  max-height: 60vh;
  overflow-y: auto;
}

/* Responsive */
@media (max-width: 768px) {
  .batch-review-container {
    padding: 20px 14px;
  }
  .page-header {
    flex-direction: column;
    gap: 10px;
  }
  .page-title {
    font-size: 1.4rem;
  }
  .review-card {
    padding: 16px 10px;
    border-radius: 14px;
    overflow-x: auto;
  }
  .review-actions {
    flex-direction: column;
    gap: 12px;
  }
}

@media (max-width: 480px) {
  .batch-review-container {
    padding: 12px 8px;
  }
  .page-title {
    font-size: 1.2rem;
  }
  .review-card {
    padding: 12px 6px;
  }
}
</style>
