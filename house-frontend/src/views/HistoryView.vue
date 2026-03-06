<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { View, Search, Calendar, House, Download, Refresh, ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import ReportInfoDialog from '@/components/ReportInfoDialog.vue'
import { getHistory } from '@/api'
import { API_BASE_URL } from '@/config'

const reports = ref([])
const isLoading = ref(true)
const isGeneratingPdf = ref(false)
const searchKeyword = ref('')
const router = useRouter()
const showReportDialog = ref(false)
const currentReportForPdf = ref(null)

const fetchReports = async () => {
  isLoading.value = true
  try {
    const response = await getHistory()
    if (response.data && response.data.success) {
      reports.value = response.data.list
    } else {
        // Fallback for empty or different structure
        reports.value = []
    }
  } catch (error) {
    console.error('Fetch reports error:', error)
    ElMessage.error('无法连接到后端服务器')
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  fetchReports()
})

const formatPriceDetail = (row) => {
  const price = row.estimated_price
  if (!price) return '0'
  return parseFloat(price).toLocaleString(undefined, { minimumFractionDigits: 0 })
}

const handleView = (row) => {
  const reportId = row.id
  const routeData = router.resolve({
    name: 'report-detail',
    params: { id: reportId }
  });
  router.push({ name: 'report-detail', params: { id: reportId } })
}

const handleDownloadPdf = (pdf_url) => {
  if (pdf_url) {
    const url = pdf_url.startsWith('http') ? pdf_url : `${API_BASE_URL}${pdf_url}`
    window.open(url, '_blank')
  }
}

const generatePdf = (row) => {
  currentReportForPdf.value = {
    report_id: row.report_id || row.id.replace('.json', ''),
    address: row.address,
    city: row.city || '上海',
    area: row.area,
    house_type: row.house_type
  }
  showReportDialog.value = true
}

const handleReportConfirm = async (formData) => {
  showReportDialog.value = false
  if (!currentReportForPdf.value) return

  if (isGeneratingPdf.value) return
  
  try {
    isGeneratingPdf.value = true
    ElMessage.info('正在请求后端生成 PDF 报告，请稍候...')
    
    // row.id typically comes from filename which matches report_id
    const report_id = currentReportForPdf.value.report_id
    
    const res = await axios.post(`${API_BASE_URL}/api/generate_pdf`, {
      report_id: report_id,
      client_name: formData.clientName,
      report_logo: formData.reportLogo,
      surrounding: formData.surrounding,
      traffic: formData.traffic,
      property_overview: formData.propertyOverview,
      occupancy: formData.occupancy
    })
    
    if (res.data && res.data.success) {
      ElMessage.success('PDF 报告成功生成，开始下载')
      // Refresh history to update pdf_url in list
      await fetchReports()
      // Trigger download
      handleDownloadPdf(res.data.pdf_url)
    } else {
      throw new Error(res.data?.error || 'PDF 生成失败')
    }
  } catch (error) {
    console.error('Generate PDF error:', error)
    ElMessage.error(`PDF 生成失败: ${error.message}`)
  } finally {
    isGeneratingPdf.value = false
  }
}

const filteredReports = computed(() => {
  if (!searchKeyword.value) return reports.value
  return reports.value.filter(r =>
    r.address.toLowerCase().includes(searchKeyword.value.toLowerCase())
  )
})
</script>

<template>
  <div class="history-container">
    <ReportInfoDialog
      v-model:visible="showReportDialog"
      :initial-data="currentReportForPdf"
      @confirm="handleReportConfirm"
    />
    <div class="page-meta">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item @click="router.push('/')" style="cursor: pointer;">
          <div style="display: flex; align-items: center; gap: 4px;">
            <el-icon><ArrowLeft /></el-icon> 首页
          </div>
        </el-breadcrumb-item>
        <el-breadcrumb-item>历史记录</el-breadcrumb-item>
      </el-breadcrumb>
      <h1 class="page-title">
        <el-icon><Calendar /></el-icon> 估值历史记录
      </h1>
    </div>

    <el-card v-if="reports.length || isLoading" class="content-card" shadow="never">
      <template #header>
        <div class="toolbar">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索房产地址..."
            class="search-bar"
            :prefix-icon="Search"
            clearable
          />
          <el-button type="primary" :icon="House" @click="$router.push('/home')" round>
            发起新估值
          </el-button>
        </div>
      </template>

      <el-table
        v-loading="isLoading"
        :data="filteredReports"
        style="width: 100%"
        empty-text="没有找到匹配的记录"
      >
        <el-table-column prop="address" label="房产地址" min-width="280">
          <template #default="scope">
            <div class="address-box">
              <span class="city-tag">[{{ scope.row.city }}]</span>
              <span class="address-text">{{ scope.row.address }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="估价单价 (元/㎡)" width="180" align="center">
          <template #default="scope">
            <el-tag type="success" effect="dark" class="price-tag">
              ¥ {{ formatPriceDetail(scope.row) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="总价 (万元)" width="150" align="center">
          <template #default="scope">
            <span class="total-price">{{ (scope.row.total_price / 10000).toFixed(2) }} 万</span>
          </template>
        </el-table-column>

        <el-table-column prop="generated_at" label="生成时间" width="180" align="center" sortable />

        <el-table-column label="操作" width="280" fixed="right" align="center">
          <template #default="scope">
            <div class="action-cell">
              <el-button size="small" :icon="View" @click="handleView(scope.row)" link type="primary">
                查看详情
              </el-button>
              <el-divider direction="vertical" />
              <el-button
                v-if="!scope.row.pdf_url"
                size="small"
                :icon="Refresh"
                @click="generatePdf(scope.row)"
                link
                type="warning"
                :loading="isGeneratingPdf"
              >
                生成报告
              </el-button>
              <el-button
                v-else
                size="small"
                :icon="Download"
                @click="handleDownloadPdf(scope.row.pdf_url)"
                link
                type="success"
              >
                下载 PDF
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <div v-if="!isLoading && !reports.length" class="empty-layout">
      <el-empty description="暂时没有发现您的估值记录">
        <el-button type="primary" @click="router.push('/home')" round>开启您的首次估值</el-button>
      </el-empty>
    </div>
  </div>
</template>

<style scoped>
.history-container {
  padding: 40px;
  max-width: 1200px;
  margin: 0 auto;
  min-height: 80vh;
  animation: fadeIn 0.4s ease-out;
}

.page-meta {
  margin-bottom: 30px;
}

.page-title {
  margin: 15px 0 0;
  font-size: 2rem;
  font-weight: 700;
  color: #2c3e50;
  display: flex;
  align-items: center;
  gap: 12px;
}

.content-card {
  border-radius: 12px;
  border: 1px solid #ebeef5;
  box-shadow: 0 4px 12px rgba(0,0,0,0.03);
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-bar {
  width: 350px;
}

.address-box {
  display: flex;
  align-items: center;
}

.city-tag {
  color: #909399;
  margin-right: 8px;
  font-size: 0.9em;
  white-space: nowrap;
}

.address-text {
  color: #303133;
  font-weight: 500;
}

.price-tag {
  font-weight: 600;
  font-family: 'Helvetica Neue', Arial, sans-serif;
  min-width: 100px;
}

.total-price {
  color: #f56c6c;
  font-weight: 600;
  font-size: 1.05rem;
}

.action-cell {
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-layout {
  padding: 100px 0;
  background: white;
  border-radius: 12px;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
