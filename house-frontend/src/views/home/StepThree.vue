<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Check, Download, Share, Refresh, Printer, Document, Clock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import MarkdownIt from 'markdown-it'
import { houseStore } from '@/store'
import { startValuation } from '@/api'
import { API_BASE_URL } from '@/config'
import ReportInfoDialog from '@/components/ReportInfoDialog.vue'

const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true
})

const router = useRouter()
const isLoading = ref(true)
const reportTitle = ref('智能房产估值分析')
const reportId = ref('')
const houseInfo = houseStore

// Results from backend
const valuationResult = ref(null)
const pdfUrl = ref('')
const isGeneratingPdf = ref(false)
const showReportDialog = ref(false)

// Computed properties for safe data access
const totalPrice = computed(() => {
  if (!valuationResult.value) return 0
  const tp = valuationResult.value.total_price || (estimatedPrice.value * (houseInfo.area || 100))
  return tp / 10000
})

const estimatedPrice = computed(() => {
  if (!valuationResult.value) return 0
  return valuationResult.value.estimation_result?.estimated_price || valuationResult.value.estimated_price || 0
})

const confidence = computed(() => {
  if (!valuationResult.value) return 0
  const res = valuationResult.value.estimation_result || valuationResult.value
  const c = res.confidence || 0
  return c > 1 ? c : c * 100
})

const renderedExplanation = computed(() => {
  const text = valuationResult.value?.explanation || valuationResult.value?.estimation_result?.explanation || ''
  return md.render(text)
})

const fetchValuation = async () => {
  if (!houseInfo.valuationData) {
    ElMessage.error('缺少评估数据，请重新开始')
    router.push('/home/step1')
    return
  }

  try {
    isLoading.value = true
    const payload = {
      ...houseInfo.valuationData,
      username: houseStore.user?.username || 'admin'
    }
    const response = await startValuation(payload)
    if (response && response.data && response.data.success) {
      valuationResult.value = response.data.data
      reportId.value = response.data.data.report_id || 'RE-' + Date.now().toString().slice(-6)
      pdfUrl.value = response.data.data.pdf_url
      ElMessage.success('智能评估分析生成成功！')
    } else {
      const msg = response?.data?.error || '后端返回异常'
      throw new Error(msg)
    }
  } catch (error) {
    console.error('Valuation Error:', error)
    ElMessage.error(`智能评估分析失败: ${error.message || '请检查后端连接'}`)
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  fetchValuation()
})

const restartProcess = () => {
  router.push('/home/step1')
}

const goToHistory = () => {
  router.push('/history')
}

const generateFullReport = () => {
  if (valuationResult.value) {
    const reportFilename = valuationResult.value.report_id || 'RE-' + Date.now().toString().slice(-6)
    const id = reportFilename.replace('REPORT_', '')
    const routeData = router.resolve({ name: 'report-detail', params: { id: id } })
    window.open(routeData.href, '_blank')
  } else {
    ElMessage.warning('详情预览尚未生成')
  }
}

const downloadReport = async () => {
  if (pdfUrl.value) {
    const link = document.createElement('a')
    const _url = pdfUrl.value.startsWith('http') ? pdfUrl.value : `${API_BASE_URL}${pdfUrl.value}`
    link.href = _url
    link.download = `房产评估报告_${reportId.value}.pdf`
    link.target = '_blank'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  } else {
    showReportDialog.value = true
  }
}

const handleReportConfirm = async (formData) => {
  showReportDialog.value = false
  try {
    isGeneratingPdf.value = true
    ElMessage.info('正在请求后端生成 PDF 报告，请稍候...')
    const res = await axios.post(`${API_BASE_URL}/api/generate_pdf`, {
      report_id: valuationResult.value.report_id,
      client_name: formData.clientName,
      report_logo: formData.reportLogo,
      surrounding: formData.surrounding,
      traffic: formData.traffic,
      property_overview: formData.propertyOverview,
      occupancy: formData.occupancy
    })
    if (res.data && res.data.success) {
      pdfUrl.value = res.data.pdf_url
      ElMessage.success('PDF 报告成功生成，开始下载')
      downloadReport()
    } else {
      throw new Error(res.data?.error || 'PDF 生成失败')
    }
  } catch (error) {
    ElMessage.error(`PDF 生成失败: ${error.message}`)
  } finally {
    isGeneratingPdf.value = false
  }
}

const formatYear = (val) => {
  if (!val) return '未知'
  try {
    const date = new Date(val)
    if (!isNaN(date.getTime())) {
      return date.getFullYear()
    }
  } catch (e) {
    console.error('Date parsing error', e)
  }
  return val
}
</script>

<template>
  <ReportInfoDialog
    v-model:visible="showReportDialog"
    :initial-data="{ 
      ...houseInfo.valuationData, 
      report_id: reportId,
      house_type: `${houseInfo.rooms}室${houseInfo.halls}厅`
    }"
    @confirm="handleReportConfirm"
  />
  <div class="step-three-container">
    <div v-if="isLoading" class="loading-state">
      <div class="loading-animation">
        <el-icon class="is-loading main-loading-icon"><refresh /></el-icon>
      </div>
      <div class="analysis-badge">
        <span>AI 正在综合地理位置、OCR 识别与外观特征进行精确估值...</span>
      </div>
      <el-skeleton :rows="10" animated />
    </div>

<div v-else-if="valuationResult" class="report-content">
      <!-- Result Summary Card -->
      <div class="report-header no-print">
        <div class="title-meta">
          <h1 class="report-title">{{ reportTitle }}</h1>
          <el-tag type="info" effect="plain">报告编号: {{ reportId }}</el-tag>
        </div>
      </div>

      <el-row :gutter="24">
        <!-- Main Valuation Card -->
        <el-col :span="24">
          <!-- House Info Card -->
          <el-card shadow="hover" class="house-info-card" style="margin-bottom: 24px;">
            <template #header>
              <div class="card-header">
                <strong>被估物业信息</strong>
              </div>
            </template>
            <el-descriptions :column="3" border>
              <el-descriptions-item label="房屋地址">{{ houseInfo.address || '未填写' }}</el-descriptions-item>
              <el-descriptions-item label="所在城市">{{ houseInfo.city || '未填写' }}</el-descriptions-item>
              <el-descriptions-item label="建筑面积">{{ houseInfo.area }} m²</el-descriptions-item>
              <el-descriptions-item label="户型结构">
                {{ houseInfo.rooms }}室{{ houseInfo.halls }}厅{{ houseInfo.kitchens }}厨{{ houseInfo.bathrooms }}卫
              </el-descriptions-item>
              <el-descriptions-item label="建成年代">{{ formatYear(houseInfo.year) }}</el-descriptions-item>
              <el-descriptions-item label="所在楼层">{{ houseInfo.floor }}</el-descriptions-item>
              <el-descriptions-item label="房屋朝向">{{ houseInfo.direction }}</el-descriptions-item>
              <el-descriptions-item label="装修情况">{{ houseInfo.decoration }}</el-descriptions-item>
              <el-descriptions-item label="建筑结构">{{ houseInfo.structure }}</el-descriptions-item>
            </el-descriptions>
          </el-card>

          <el-card shadow="hover" class="main-valuation-card">
            <template #header>
              <div class="card-header">
                <strong>估值评估摘要</strong>
              </div>
            </template>
            <div class="valuation-showcase">
              <el-statistic title="估值总价 (万元)" :value="totalPrice" :precision="2">
                <template #suffix>
                  <span class="unit-label">万</span>
                </template>
              </el-statistic>
              <el-divider direction="vertical" class="stat-divider" />
              <el-statistic title="预估单价 (元/m²)" :value="estimatedPrice" :precision="0">
                <template #prefix>
                  <span class="currency-label">¥</span>
                </template>
              </el-statistic>
              <el-divider direction="vertical" class="stat-divider" />
              <el-statistic title="AI 置信度" :value="confidence" :precision="1">
                <template #suffix>
                  <span class="percent-label">%</span>
                </template>
              </el-statistic>
            </div>
            
            <!-- Bottom Action Buttons moved from sidebar to main card footer/bottom -->
            <div class="valuation-footer-actions no-print">
              <el-button type="primary" :icon="Refresh" @click="restartProcess" block size="large" round>
                开始新的评估
              </el-button>
              <el-button type="info" plain :icon="Clock" @click="goToHistory" block size="large" round>
                查看估值历史记录
              </el-button>
              <el-button 
                type="success" 
                :icon="Download" 
                @click="downloadReport" 
                :loading="isGeneratingPdf"
                round
                size="large"
              >
                {{ pdfUrl ? '保存/下载正式评估报告' : '生成房产评估报告 (PDF)' }}
              </el-button>
            </div>
          </el-card>

          <!-- Explanation Card -->
          <el-card shadow="hover" class="explanation-card">
            <template #header><strong>评估建议与分析</strong></template>
            <div 
              class="explanation-text markdown-body" 
              v-html="renderedExplanation"
            ></div>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<style scoped>
.valuation-footer-actions {
  display: flex;
  gap: 15px;
  justify-content: center;
  padding: 30px 20px 10px;
  border-top: 1px solid #ebeef5;
  margin-top: 20px;
  flex-wrap: wrap;
}

.valuation-footer-actions .el-button {
  margin: 0;
  min-width: 180px;
}

.step-three-container {
  max-width: 1200px;
  margin: 0 auto;
  animation: fadeIn 0.4s ease-out;
  padding: 20px;
}

.loading-state {
  padding: 80px 0;
  text-align: center;
}

.main-loading-icon {
  font-size: 3rem;
  color: #409eff;
  margin-bottom: 20px;
}

.analysis-badge {
  margin-top: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 15px;
  color: #409eff;
  font-size: 1.15rem;
  font-weight: 500;
}

.report-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 1px solid #ebeef5;
}

.report-title {
  font-size: 2rem;
  font-weight: 700;
  color: #303133;
  margin-bottom: 8px;
}

.main-valuation-card {
  margin-bottom: 24px;
}

.explanation-card {
  margin-bottom: 24px;
}

.explanation-text {
  line-height: 1.6;
  color: #303133;
}

/* Markdown Rendering Styles */
:deep(.markdown-body) {
  font-size: 15px;
}

:deep(.markdown-body h3) {
  margin-top: 1.5em;
  margin-bottom: 0.8em;
  color: #303133;
  border-left: 4px solid #409eff;
  padding-left: 10px;
}

:deep(.markdown-body h4) {
  margin-top: 1.2em;
  margin-bottom: 0.6em;
  color: #409eff;
}

:deep(.markdown-body table) {
  width: 100%;
  border-collapse: collapse;
  margin: 1em 0;
  font-size: 13px;
  /* overflow-x: auto; */
  /* display: block; */
  display: table;
}

:deep(.markdown-body th), :deep(.markdown-body td) {
  border: 1px solid #ebeef5;
  padding: 8px 12px;
  text-align: left;
}

:deep(.markdown-body th) {
  background-color: #f5f7fa;
  color: #909399;
}

:deep(.markdown-body blockquote) {
  margin: 1em 0;
  padding: 10px 15px;
  color: #606266;
  background-color: #fcfcfc;
  border-left: 5px solid #E4E7ED;
}

:deep(.markdown-body ul), :deep(.markdown-body ol) {
  padding-left: 20px;
  margin-bottom: 1em;
}

.valuation-showcase {
  display: flex;
  justify-content: space-around;
  align-items: center;
  padding: 20px 0;
}

.stat-divider {
  height: 60px;
  margin: 0 40px;
}

.unit-label, .currency-label, .percent-label {
  font-size: 16px;
  color: #909399;
  margin-left: 5px;
}

.analysis-status-card {
  margin-bottom: 24px;
}

.restart-container {
  margin-top: 20px;
}

.restart-container :deep(.el-button) {
  width: 100%;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
