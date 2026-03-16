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
const loadingProgress = ref(0)
const loadingStage = ref(0)
const baseLoadingStages = [
  '正在通过地理编码精确定位房产位置...',
  '正在分析房产证 OCR 提取的结构化数据...',
  '正在多维检索周边成交案例与市场行情...',
  '正在调用多模态 LLM 进行趋势预测与微调...',
  '正在综合所有因素生成最终估值报告...'
]

// 根据是否开启 LLM 预测动态返回加载阶段
const loadingStages = computed(() => {
  const hasLLM = houseInfo.enablePrediction !== false
  return hasLLM ? baseLoadingStages : baseLoadingStages.filter((_, i) => i !== 3)
})

let progressInterval = null

// 根据是否开启 LLM 预测调整进度映射
const getStageByProgress = (p, hasLLM = true) => {
  if (p < 15) return 0
  if (p < 38) return 1
  if (p < 55) return 2
  if (hasLLM) {
    if (p < 92) return 3
    return 4
  } else {
    // 无 LLM 时，跳过阶段 3，直接到阶段 4
    if (p < 75) return 3 // 对应原来的阶段 4
    return 4
  }
}

// 各阶段进度速度，参考实际耗时（每 500ms 一次 tick）：
//   0→15%  : 前置解析/定位    ~1s   → 快速
//   15→38% : 联网搜索+精简    ~11s  → 中速
//   38→55% : 案例检索/Memory  ~3s   → 较快
//   55→92% : LLM 趋势预测     ~37s  → 极慢（避免卡在95%等待）
//   92→95% : 最终整合         ~2s
const getIncrement = (p) => {
  if (p < 15)  return Math.random() * 5   + 3    // 快：0→15 约1s
  if (p < 38)  return Math.random() * 0.8 + 0.7  // 中：15→38 约11s
  if (p < 55)  return Math.random() * 1.5 + 1.5  // 较快：38→55 约4s
  if (p < 92)  return Math.random() * 0.3 + 0.25 // 极慢：55→92 约46s（覆盖37s LLM）
  if (p < 95)  return Math.random() * 0.5 + 0.5  // 收尾：92→95 约2s
  return 0
}



const startProgress = () => {
  loadingProgress.value = 0
  loadingStage.value = 0
  const hasLLM = houseInfo.enablePrediction !== false
  progressInterval = setInterval(() => {
    const p = loadingProgress.value
    if (p < 95) {
      loadingProgress.value = Math.min(p + getIncrement(p), 95)
      const stage = getStageByProgress(loadingProgress.value, hasLLM)
      if (stage > loadingStage.value) {
        loadingStage.value = stage
      }
    }
  }, 500)
}

const clearProgress = () => {
  if (progressInterval) {
    clearInterval(progressInterval)
    progressInterval = null
  }
  loadingProgress.value = 100
}

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
    isLoading.value = false
    ElMessage.warning('缺少评估数据，请重新填写信息')
    router.push('/home/step1')
    return
  }

  try {
    isLoading.value = true
    startProgress()
    const payload = {
      ...houseInfo.valuationData,
      username: houseStore.user?.username || 'admin'
    }
    const response = await startValuation(payload)
    if (response && response.data && response.data.success) {
      clearProgress()
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
    clearProgress()
  }
}

onMounted(() => {
  fetchValuation()
})

const restartProcess = () => {
  // 清除上次估值数据，确保重新评估时走完整流程
  houseInfo.valuationData = null
  // 清空表单数据，让用户重新填写
  houseStore.reset()
  router.push('/home/step1')
}

const goToHistory = () => {
  router.push('/history')
}

const generateFullReport = () => {
  if (valuationResult.value) {
    const report_id = valuationResult.value.report_id
    const routeData = router.resolve({ name: 'report-detail', params: { id: report_id } })
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
      <div class="loading-card">
        <div class="loading-animation">
          <el-icon class="is-loading main-loading-icon"><refresh /></el-icon>
        </div>
        
        <h2 class="loading-title">智能评估正在生成中</h2>
        <p class="loading-desc">系统正在调用多模态大模型为您进行深度价值分析...</p>
        
        <div class="progress-wrapper">
          <el-progress 
            :percentage="Math.floor(loadingProgress)" 
            :stroke-width="12" 
            striped 
            striped-flow 
            :duration="10"
            class="custom-progress"
          />
        </div>

        <div class="loading-stages">
          <div 
            v-for="(stage, index) in loadingStages" 
            :key="index"
            class="stage-item"
            :class="{ 
              'active': loadingStage === index, 
              'completed': loadingStage > index 
            }"
          >
            <el-icon v-if="loadingStage > index" class="stage-icon success"><Check /></el-icon>
            <el-icon v-else-if="loadingStage === index" class="stage-icon processing is-loading"><Refresh /></el-icon>
            <el-icon v-else class="stage-icon pending"><Document /></el-icon>
            <span class="stage-text">{{ stage }}</span>
          </div>
        </div>
      </div>
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
              <el-button type="warning" plain :icon="Document" @click="generateFullReport" block size="large" round>
                查看估值详情预览
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
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 60px 0;
}

.loading-card {
  background: white;
  padding: 50px;
  border-radius: 20px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.05);
  width: 100%;
  max-width: 600px;
  text-align: center;
}

.loading-title {
  font-size: 1.6rem;
  font-weight: 700;
  color: #303133;
  margin: 20px 0 10px;
}

.loading-desc {
  color: #909399;
  margin-bottom: 30px;
}

.progress-wrapper {
  margin-bottom: 40px;
}

.custom-progress :deep(.el-progress-bar__outer) {
  background-color: #f0f2f5;
}

.loading-stages {
  text-align: left;
  background: #f8fafc;
  padding: 25px;
  border-radius: 12px;
  border: 1px solid #edf2f7;
}

.stage-item {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 15px;
  opacity: 0.5;
  transition: all 0.3s ease;
}

.stage-item:last-child {
  margin-bottom: 0;
}

.stage-item.active {
  opacity: 1;
  transform: translateX(5px);
  color: #409eff;
  font-weight: 500;
}

.stage-item.completed {
  opacity: 1;
  color: #67c23a;
}

.stage-icon {
  font-size: 1.2rem;
}

.stage-icon.success {
  color: #67c23a;
}

.stage-icon.processing {
  color: #409eff;
}

.stage-icon.pending {
  color: #c0c4cc;
}

.stage-text {
  font-size: 0.95rem;
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
