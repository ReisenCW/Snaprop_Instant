<script setup>
import { ref, onMounted, computed, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Printer, Document, House, Download, Check } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { API_BASE_URL } from '@/config'
import axios from 'axios'
import MarkdownIt from 'markdown-it'

const route = useRoute()
const router = useRouter()
const md = new MarkdownIt({
  html: true,
  breaks: true,
  linkify: true
})

const reportId = route.params.id
const reportData = ref(null)
const isLoading = ref(true)

const fetchReportData = async () => {
  isLoading.value = true
  try {
    const response = await axios.get(`${API_BASE_URL}/api/reports/${reportId}.json`)
    reportData.value = response.data
  } catch (error) {
    console.error('Fetch report detail error:', error)
    ElMessage.error('无法加载报告详情')
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  fetchReportData()
})

const goBack = () => {
  router.back()
}

const printReport = () => {
  window.print()
}

const formattedExplanation = computed(() => {
  if (!reportData.value?.estimation_result?.explanation) return ''
  return md.render(reportData.value.estimation_result.explanation)
})

const getImageUrl = (path) => {
  if (!path) return ''
  if (path.startsWith('http') || path.startsWith('data:')) return path
  // Handle relative paths from backend, assuming they start with /static or just static
  const cleanPath = path.replace(/^\//, '')
  return `${API_BASE_URL}/${cleanPath}`
}

const totalPrice = computed(() => {
  if (!reportData.value?.estimation_result) return 0
  const er = reportData.value.estimation_result
  const price = er.estimated_price || 0
  const area = reportData.value.property_data?.area || 100
  const tp = er.total_price || (price * area)
  return (tp / 10000).toFixed(2)
})
</script>

<template>
  <div class="report-detail-container">
    <div class="no-print actions-bar">
      <el-button :icon="ArrowLeft" @click="goBack" round>返回</el-button>
      <div class="right-actions">
        <el-button type="primary" :icon="Printer" @click="printReport" round>打印估值分析</el-button>
      </div>
    </div>

    <div v-if="isLoading" class="loading-box">
      <el-skeleton :rows="15" animated />
    </div>

    <div v-else-if="reportData" class="report-paper">
      <div class="report-header-section">
        <div class="header-top">
          <div class="brand-info">
            <h1 class="main-title">智能房产估值分析</h1>
            <p class="subtitle">Intelligent Property Valuation Analysis</p>
          </div>
          <div class="report-meta">
            <p><strong>报告编号：</strong>{{ reportData.report_id || reportId }}</p>
            <p><strong>生成日期：</strong>{{ reportData.generated_at }}</p>
          </div>
        </div>
        <el-divider />
      </div>

      <!-- Core Result Section -->
      <div class="section-container core-result">
        <h2 class="section-title"><el-icon><House /></el-icon> 评估核心结论</h2>
        <div class="valuation-cards">
          <div class="v-card highlight">
            <span class="v-label">评估总价</span>
            <span class="v-value">{{ totalPrice }} <small>万元</small></span>
          </div>
          <div class="v-card">
            <span class="v-label">评估单价</span>
            <span class="v-value">{{ Math.round(reportData.estimation_result.estimated_price).toLocaleString() }} <small>元/㎡</small></span>
          </div>
          <div class="v-card">
            <span class="v-label">置信度</span>
            <span class="v-value">{{ (reportData.estimation_result.confidence * 100).toFixed(1) }}<small>%</small></span>
          </div>
        </div>
      </div>

      <!-- Property Info Section -->
      <div class="section-container property-info">
        <h2 class="section-title"><el-icon><Document /></el-icon> 目标房产信息</h2>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="房产地址" :span="2">{{ reportData.property_data.address }}</el-descriptions-item>
          <el-descriptions-item label="所在城市">{{ reportData.property_data.city }}</el-descriptions-item>
          <el-descriptions-item label="建筑面积">{{ reportData.property_data.area }} ㎡</el-descriptions-item>
          <el-descriptions-item label="户型结构">{{ reportData.property_data.house_type }} / {{ reportData.target_property.structure }}</el-descriptions-item>
          <el-descriptions-item label="装修情况">{{ reportData.target_property.fitment }}</el-descriptions-item>
          <el-descriptions-item label="建成年份">{{ reportData.target_property.built_time }} 年</el-descriptions-item>
          <el-descriptions-item label="所在楼层">{{ reportData.target_property.floor || '中楼层' }}</el-descriptions-item>
        </el-descriptions>
      </div>

      <!-- Detailed Analysis Section -->
      <div class="section-container detailed-analysis">
        <h2 class="section-title"><el-icon><Check /></el-icon> 估值逻辑说明</h2>
        <div class="markdown-body" v-html="formattedExplanation"></div>
      </div>

      <!-- Photos Section -->
      <div class="section-container photos-section">
        <h2 class="section-title"><el-icon><Picture /></el-icon> 现场及凭据照片</h2>
        <div class="photo-flex-container">
          <!-- Property Photos (Multiple) -->
          <template v-if="reportData.embedded_images?.property_photos && reportData.embedded_images.property_photos.length > 0">
             <div class="photo-item" v-for="(photo, index) in reportData.embedded_images.property_photos" :key="index">
                <el-card shadow="never" class="photo-card">
                  <template #header><div class="photo-card-header">房屋外观/详情 {{ index + 1 }}</div></template>
                  <el-image 
                    :src="getImageUrl(photo)" 
                    fit="contain"
                    class="report-image"
                    :preview-src-list="[getImageUrl(photo)]"
                  />
                </el-card>
             </div>
          </template>
          <!-- Fallback for legacy single photo -->
          <template v-else-if="reportData.property_data.property_photo || reportData.embedded_images?.photo_image">
              <div class="photo-item">
                <el-card shadow="never" class="photo-card">
                  <template #header><div class="photo-card-header">房屋外观/详情</div></template>
                  <el-image 
                    :src="getImageUrl(reportData.embedded_images?.photo_image || reportData.property_data.property_photo)" 
                    fit="contain"
                    class="report-image"
                    :preview-src-list="[getImageUrl(reportData.embedded_images?.photo_image || reportData.property_data.property_photo)]"
                  />
                </el-card>
              </div>
          </template>

          <!-- Step 2 User Photo (if provided separately in data) -->
          <div class="photo-item" v-if="reportData.property_data.property_image && reportData.property_data.property_image !== reportData.property_data.property_photo">
             <el-card shadow="never" class="photo-card">
              <template #header><div class="photo-card-header">现场实勘照片</div></template>
              <el-image 
                :src="getImageUrl(reportData.property_data.property_image)" 
                fit="contain"
                class="report-image"
                :preview-src-list="[getImageUrl(reportData.property_data.property_image)]"
              />
            </el-card>
          </div>

          <!-- Certificate Photo -->
          <div class="photo-item" v-if="reportData.property_data.property_cert_image || reportData.embedded_images?.cert_image">
            <el-card shadow="never" class="photo-card">
              <template #header><div class="photo-card-header">权属凭证</div></template>
              <el-image 
                :src="getImageUrl(reportData.embedded_images?.cert_image || reportData.property_data.property_cert_image)" 
                fit="contain"
                class="report-image"
                :preview-src-list="[getImageUrl(reportData.embedded_images?.cert_image || reportData.property_data.property_cert_image)]"
              />
            </el-card>
          </div>

          <!-- Map Image -->
          <div class="photo-item" v-if="reportData.embedded_images?.map_image">
            <el-card shadow="never" class="photo-card">
              <template #header><div class="photo-card-header">位置示意图</div></template>
              <el-image 
                :src="getImageUrl(reportData.embedded_images.map_image)" 
                fit="contain"
                class="report-image"
                :preview-src-list="[getImageUrl(reportData.embedded_images.map_image)]"
              />
            </el-card>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.report-detail-container {
  padding: 40px;
  background: #f5f7fa;
  min-height: 100vh;
}

.actions-bar {
  max-width: 900px;
  margin: 0 auto 20px;
  display: flex;
  justify-content: space-between;
}

.report-paper {
  max-width: 900px;
  margin: 0 auto;
  background: white;
  padding: 60px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
  border-radius: 4px;
}

.header-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.main-title {
  font-size: 2.2rem;
  color: #2c3e50;
  margin: 0;
  letter-spacing: 2px;
}

.subtitle {
  color: #909399;
  font-size: 0.9rem;
  margin-top: 5px;
}

.report-meta {
  text-align: right;
  font-size: 0.9rem;
  color: #606266;
}

.report-meta p { margin: 4px 0; }

.section-container {
  margin-bottom: 40px;
}

.section-title {
  font-size: 1.3rem;
  color: #409eff;
  border-left: 4px solid #409eff;
  padding-left: 12px;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.valuation-cards {
  display: flex;
  gap: 20px;
}

.v-card {
  flex: 1;
  background: #f8f9fb;
  padding: 20px;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.v-card.highlight {
  background: #ecf5ff;
}

.v-label {
  color: #909399;
  font-size: 0.9rem;
  margin-bottom: 10px;
}

.v-value {
  font-size: 1.8rem;
  font-weight: 700;
  color: #303133;
}

.v-value small {
  font-size: 0.9rem;
  font-weight: normal;
  margin-left: 4px;
}

.v-card.highlight .v-value {
  color: #409eff;
}

.markdown-body {
  line-height: 1.6;
  color: #444;
  background: #fafafa;
  padding: 20px;
  border-radius: 8px;
  font-size: 15px; 
}

.markdown-body :deep(h3) {
  margin-top: 1.5em;
  margin-bottom: 0.8em;
  color: #303133;
  border-left: 4px solid #409eff;
  padding-left: 10px;
}

.markdown-body :deep(h4) {
  margin-top: 1.2em;
  margin-bottom: 0.6em;
  color: #409eff;
}

.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 1em 0;
  font-size: 13px;
  overflow-x: auto;
  display: block;
}

.markdown-body :deep(th), .markdown-body :deep(td) {
  border: 1px solid #ebeef5;
  padding: 8px 12px;
  text-align: left;
}

.markdown-body :deep(th) {
  background-color: #f5f7fa;
  color: #909399;
}

.markdown-body :deep(blockquote) {
  margin: 1em 0;
  padding: 10px 15px;
  color: #606266;
  background-color: #fcfcfc;
  border-left: 5px solid #E4E7ED;
}

.markdown-body :deep(ul), .markdown-body :deep(ol) {
  padding-left: 20px;
  margin-bottom: 1em;
}

.photo-flex-container {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  justify-content: center;
}

.photo-item {
  flex: 1;
  min-width: 300px;
  max-width: 48%; /* Allows 2 items per row if space permits */
}

@media (max-width: 768px) {
  .photo-item {
    max-width: 100%;
    flex: 0 0 100%;
  }
}

.photo-card {
  height: 100%;
  margin-top: 10px;
}

.photo-card-header {
  text-align: center;
  font-weight: 500;
  font-size: 0.95rem;
  color: #606266;
}

.report-image {
  width: 100%;
  height: 220px;
  display: block;
}

.report-footer {
  margin-top: 60px;
  text-align: center;
  color: #909399;
  font-size: 0.85rem;
  border-top: 1px dashed #ebeef5;
  padding-top: 30px;
}

@media print {
  .no-print { display: none !important; }
  .report-detail-container { padding: 0; background: white; }
  .report-paper { box-shadow: none; padding: 0; max-width: 100%; }
}
</style>
