<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Check, Download, Share, Refresh, Printer, Document, Clock, CircleCloseFilled, ArrowLeft, TrendCharts } from '@element-plus/icons-vue'
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
const hasError = ref(false)
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
const estimatedPrice = computed(() => {
  if (!valuationResult.value) return 0
  return valuationResult.value.estimation_result?.estimated_price || valuationResult.value.estimated_price || 0
})

const totalPrice = computed(() => {
  if (!valuationResult.value) return 0
  const area = houseInfo.area || 100
  const tp = valuationResult.value.total_price || (estimatedPrice.value * area)
  return tp / 10000
})

// Count-up animation values
const displayTotalPrice = ref(0)
const displayEstimatedPrice = ref(0)

// Animate value from start to end
const animateValue = (targetRef, endValue, duration = 1500) => {
  const startValue = 0
  const range = endValue - startValue
  const startTime = performance.now()

  const animate = (currentTime) => {
    const elapsed = currentTime - startTime
    const progress = Math.min(elapsed / duration, 1)
    // cubic ease-out
    const easeOut = 1 - Math.pow(1 - progress, 3)
    targetRef.value = startValue + range * easeOut
    if (progress < 1) {
      requestAnimationFrame(animate)
    }
  }
  requestAnimationFrame(animate)
}

// Watch for valuation result to trigger count-up animation
watch(valuationResult, (newVal) => {
  if (newVal) {
    // Small delay to let the UI render first
    setTimeout(() => {
      animateValue(displayTotalPrice, totalPrice.value)
      animateValue(displayEstimatedPrice, estimatedPrice.value)
    }, 300)
  }
}, { immediate: false })

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
      username: houseStore.user?.username || 'admin',
      selection_weights: houseStore.selectionWeights
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
    hasError.value = true
    ElMessage.error(`智能评估分析失败: ${error.message || '请检查后端连接'}`)
  } finally {
    isLoading.value = false
    clearProgress()
  }
}

onMounted(() => {
  fetchValuation()
})

onUnmounted(() => {
  clearProgress()
})

const restartProcess = () => {
  // 清除上次估值数据，确保重新评估时走完整流程
  houseInfo.valuationData = null
  // 清空表单数据，让用户重新填写
  houseStore.reset()
  // Navigate to step 1 via router (avoids full page reload)
  router.push('/home/step1')
}

const goBack = () => {
  router.push('/home/step2')
}

const goToHistory = () => {
  router.push('/history')
}

const generateFullReport = () => {
  if (valuationResult.value) {
    const rid = valuationResult.value.report_id || reportId.value
    if (!rid) {
      ElMessage.warning('报告 ID 缺失，无法生成详情预览')
      return
    }
    const routeData = router.resolve({ name: 'report-detail', params: { id: rid } })
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

    <div v-else-if="hasError" class="error-state">
      <div class="error-card">
        <el-icon class="error-icon"><CircleCloseFilled /></el-icon>
        <h2 class="error-title">评估失败</h2>
        <p class="error-desc">智能评估分析未能完成，请检查后端服务状态或网络连接</p>
        <div class="error-actions">
          <el-button type="primary" :icon="Refresh" @click="restartProcess" size="large" round>
            重新开始评估
          </el-button>
          <el-button type="info" plain :icon="ArrowLeft" @click="goBack" size="large" round>
            返回上一步
          </el-button>
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
              <el-statistic title="估值总价 (万元)" :value="displayTotalPrice" :precision="2">
                <template #suffix>
                  <span class="unit-label">万</span>
                </template>
              </el-statistic>
              <el-divider direction="vertical" class="stat-divider" />
              <el-statistic title="预估单价 (元/m²)" :value="displayEstimatedPrice" :precision="0">
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

          <!-- Market trends link -->
          <div class="market-link-card no-print">
            <div class="market-link-content">
              <el-icon :size="28" color="#409eff"><TrendCharts /></el-icon>
              <span class="market-link-text">了解上海各区域房价走势，辅助判断估值合理性</span>
              <el-button type="primary" plain round @click="router.push('/market')">
                查看市场行情 →
              </el-button>
            </div>
          </div>
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
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.valuation-footer-actions .el-button:hover {
  transform: translateY(-2px);
}

.step-three-container {
  max-width: 1200px;
  margin: 0 auto;
  animation: fadeSlideIn 0.45s ease-out;
  padding: 20px;
}

@keyframes fadeSlideIn {
  from { opacity: 0; transform: translateY(18px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ── Loading State ── */
.loading-state {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 60px 0;
}

.loading-card {
  background: white;
  padding: 56px 48px;
  border-radius: 24px;
  box-shadow: 0 12px 40px rgba(0,0,0,0.06);
  width: 100%;
  max-width: 620px;
  text-align: center;
}

.loading-animation {
  margin-bottom: 16px;
}

.main-loading-icon {
  font-size: 3.5rem;
  color: #409eff;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(0.95); }
}

.loading-title {
  font-size: 1.7rem;
  font-weight: 700;
  color: #303133;
  margin: 20px 0 10px;
}

.loading-desc {
  color: #909399;
  margin-bottom: 36px;
  font-size: 0.98rem;
}

.progress-wrapper {
  margin-bottom: 44px;
}

.custom-progress :deep(.el-progress-bar__outer) {
  background-color: #f0f2f5;
  border-radius: 20px;
}

.custom-progress :deep(.el-progress-bar__inner) {
  border-radius: 20px;
}

.loading-stages {
  text-align: left;
  background: linear-gradient(135deg, #f8fafc, #f0f4f8);
  padding: 28px;
  border-radius: 16px;
  border: 1px solid #edf2f7;
}

.stage-item {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 15px;
  padding: 6px 8px;
  border-radius: 8px;
  opacity: 0.45;
  transition: all 0.35s ease;
}

.stage-item:last-child {
  margin-bottom: 0;
}

.stage-item.active {
  opacity: 1;
  transform: translateX(8px);
  color: #409eff;
  font-weight: 500;
  background: rgba(64,158,255,0.04);
}

.stage-item.completed {
  opacity: 1;
  color: #67c23a;
}

.stage-icon {
  font-size: 1.3rem;
  flex-shrink: 0;
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

/* ── Error State ── */
.error-state {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 60px 0;
}

.error-card {
  background: white;
  padding: 56px;
  border-radius: 24px;
  box-shadow: 0 12px 40px rgba(0,0,0,0.06);
  width: 100%;
  max-width: 600px;
  text-align: center;
}

.error-icon {
  font-size: 4.5rem;
  color: #F56C6C;
  margin-bottom: 20px;
  animation: shake 0.6s ease-in-out;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-8px); }
  75% { transform: translateX(8px); }
}

.error-title {
  font-size: 1.7rem;
  font-weight: 700;
  color: #303133;
  margin: 20px 0 10px;
}

.error-desc {
  color: #909399;
  margin-bottom: 32px;
}

.error-actions {
  display: flex;
  gap: 15px;
  justify-content: center;
  flex-wrap: wrap;
}

/* ── Result Content ── */
.report-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 2px solid #f0f2f5;
}

.report-title {
  font-size: 2rem;
  font-weight: 700;
  color: #303133;
  margin-bottom: 8px;
}

/* Valuation Card */
.main-valuation-card {
  margin-bottom: 24px;
  border-radius: 20px;
  overflow: hidden;
}

.main-valuation-card :deep(.el-card__header) {
  background: linear-gradient(135deg, #f8fafc, #f0f4f8);
  border-bottom: 1px solid #ebeef5;
}

.house-info-card {
  border-radius: 16px;
  overflow: hidden;
}

.explanation-card {
  margin-bottom: 24px;
  border-radius: 16px;
  overflow: hidden;
}

.explanation-text {
  line-height: 1.8;
  color: #303133;
}

.market-link-card {
  margin-bottom: 24px;
  padding: 20px 28px;
  background: linear-gradient(135deg, #f0f7ff 0%, #f8faff 100%);
  border: 1px solid #d9ecff;
  border-radius: 14px;
}

.market-link-content {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.market-link-text {
  flex: 1;
  font-size: 0.95rem;
  color: #606266;
  min-width: 0;
}

/* Valuation Showcase */
.valuation-showcase {
  display: flex;
  justify-content: space-around;
  align-items: center;
  padding: 32px 16px;
  background: linear-gradient(135deg, #fafbff 0%, #f5f7ff 100%);
  border-radius: 16px;
  margin: 8px 0;
}

.valuation-showcase :deep(.el-statistic__head) {
  font-size: 0.9rem;
  color: #909399;
  font-weight: 500;
}

.valuation-showcase :deep(.el-statistic__number) {
  font-size: 2.4rem;
  font-weight: 800;
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

/* Markdown Rendering Styles */
:deep(.markdown-body) {
  font-size: 15px;
  line-height: 1.8;
}

:deep(.markdown-body h3) {
  margin-top: 1.5em;
  margin-bottom: 0.8em;
  color: #303133;
  border-left: 4px solid #409eff;
  padding-left: 12px;
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
  display: table;
  border-radius: 8px;
  overflow: hidden;
}

:deep(.markdown-body th), :deep(.markdown-body td) {
  border: 1px solid #ebeef5;
  padding: 10px 14px;
  text-align: left;
}

:deep(.markdown-body th) {
  background-color: #f5f7fa;
  color: #606266;
  font-weight: 600;
}

:deep(.markdown-body tbody tr:hover) {
  background-color: #fafbfc;
}

:deep(.markdown-body blockquote) {
  margin: 1em 0;
  padding: 12px 18px;
  color: #606266;
  background-color: #f8f9fb;
  border-left: 4px solid #409eff;
  border-radius: 0 8px 8px 0;
}

:deep(.markdown-body ul), :deep(.markdown-body ol) {
  padding-left: 24px;
  margin-bottom: 1em;
}

:deep(.markdown-body li) {
  margin-bottom: 4px;
}

/* Print */
@media print {
  .no-print { display: none !important; }
  .step-three-container {
    padding: 0;
    max-width: 100%;
  }
}

/* Responsive */
@media (max-width: 768px) {
  .valuation-showcase {
    flex-direction: column;
    gap: 20px;
    padding: 20px;
  }
  .stat-divider {
    height: 1px;
    width: 80%;
    margin: 0;
  }
  .valuation-showcase :deep(.el-statistic__number) {
    font-size: 1.8rem;
  }
  .report-title {
    font-size: 1.6rem;
  }
  .loading-card, .error-card {
    padding: 36px 24px;
  }
}
</style>
