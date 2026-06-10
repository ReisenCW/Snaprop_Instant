<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Download } from '@element-plus/icons-vue'
import { houseStore } from '@/store'
import { exportExcel } from '@/api'
import * as echarts from 'echarts'

const router = useRouter()

const results = ref([])
const chartRef = ref(null)

const successResults = computed(() => results.value.filter(r => r.status === 'success'))
const failedResults = computed(() => results.value.filter(r => r.status === 'failed'))
const avgUnitPrice = computed(() => {
  const list = successResults.value
  if (list.length === 0) return 0
  return Math.round(list.reduce((s, r) => s + r.unitPrice, 0) / list.length)
})

onMounted(() => {
  // Load from store
  if (houseStore.batchResults && houseStore.batchResults.length > 0) {
    results.value = houseStore.batchResults
  } else {
    ElMessage.warning('未找到批量估值结果，请先上传')
    router.replace('/home/batch')
    return
  }

  // Render chart
  if (successResults.value.length > 0) {
    setTimeout(() => renderChart(), 100)
  }
})

const renderChart = () => {
  if (!chartRef.value) return
  const chart = echarts.init(chartRef.value)

  const addresses = successResults.value.map(r => {
    const addr = r.address || r.name || '-'
    return addr.length > 10 ? addr.slice(0, 10) + '...' : addr
  })
  const totalPrices = successResults.value.map(r => {
    return (r.totalPrice / 10000).toFixed(1)
  })
  const unitPrices = successResults.value.map(r => Math.round(r.unitPrice))

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    legend: {
      data: ['总价(万元)', '单价(元/㎡)'],
      bottom: 0
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '12%',
      top: '8%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: addresses,
      axisLabel: { rotate: 30, fontSize: 11 }
    },
    yAxis: [
      {
        type: 'value',
        name: '万元',
        splitLine: { lineStyle: { type: 'dashed' } }
      },
      {
        type: 'value',
        name: '元/㎡',
        splitLine: { show: false }
      }
    ],
    series: [
      {
        name: '总价(万元)',
        type: 'bar',
        data: totalPrices,
        itemStyle: {
          borderRadius: [6, 6, 0, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#409eff' },
            { offset: 1, color: '#6610f2' }
          ])
        },
        barWidth: '40%'
      },
      {
        name: '单价(元/㎡)',
        type: 'line',
        yAxisIndex: 1,
        data: unitPrices,
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: { color: '#67c23a', width: 3 },
        itemStyle: { color: '#67c23a' }
      }
    ]
  })

  window.addEventListener('resize', () => chart?.resize(), { once: false })
}

const formatPrice = (p) => {
  if (!p || p <= 0) return '-'
  return Number(p).toLocaleString('zh-CN')
}

const formatTotal = (p) => {
  if (!p || p <= 0) return '-'
  const wan = (p / 10000).toFixed(0)
  return `${wan}万`
}

const handleExportExcel = async () => {
  if (successResults.value.length === 0) {
    ElMessage.warning('没有可导出的数据')
    return
  }
  const tableData = successResults.value.map((r, i) => ([
    i + 1,
    r.address,
    r.area,
    r.houseType,
    r.unitPrice,
    r.totalPrice
  ]))
  try {
    await exportExcel(tableData)
    ElMessage.success('Excel 导出成功')
  } catch {
    ElMessage.error('导出失败')
  }
}

const goBack = () => {
  router.push('/home/mode')
}

const goBatchAgain = () => {
  houseStore.batchResults = null
  router.push('/home/batch')
}
</script>

<template>
  <div class="batch-results-container">
    <div class="page-header">
      <el-button :icon="ArrowLeft" @click="goBack" round plain>返回模式选择</el-button>
      <h1 class="page-title">批量估值结果</h1>
      <el-button type="primary" :icon="Download" @click="handleExportExcel" round>
        导出 Excel
      </el-button>
    </div>

    <!-- Summary cards -->
    <div v-if="successResults.length > 0" class="summary-cards">
      <div class="summary-card">
        <span class="summary-num">{{ successResults.length }}</span>
        <span class="summary-label">成功估值</span>
      </div>
      <div class="summary-card">
        <span class="summary-num">{{ failedResults.length }}</span>
        <span class="summary-label">处理失败</span>
      </div>
      <div class="summary-card">
        <span class="summary-num">{{ formatPrice(avgUnitPrice) }}</span>
        <span class="summary-label">均价 (元/㎡)</span>
      </div>
    </div>

    <!-- Chart -->
    <div v-if="successResults.length > 1" class="chart-card">
      <div ref="chartRef" style="height: 360px; width: 100%;"></div>
    </div>

    <!-- Results table -->
    <div class="table-card">
      <h3 v-if="successResults.length > 0">房源对比表</h3>
      <el-table v-if="successResults.length > 0" :data="successResults" stripe border style="width: 100%">
        <el-table-column type="index" label="#" width="50" />
        <el-table-column prop="address" label="地址" min-width="220" />
        <el-table-column prop="area" label="面积(㎡)" width="100" align="center" />
        <el-table-column prop="houseType" label="户型" width="120" align="center" />
        <el-table-column label="估价单价(元/㎡)" width="140" align="right">
          <template #default="{ row }">{{ formatPrice(row.unitPrice) }}</template>
        </el-table-column>
        <el-table-column label="估价总价" width="130" align="right">
          <template #default="{ row }">{{ formatTotal(row.totalPrice) }}</template>
        </el-table-column>
      </el-table>

      <!-- Failed items -->
      <div v-if="failedResults.length > 0" class="failed-section">
        <h4>处理失败</h4>
        <el-table :data="failedResults" size="small" stripe>
          <el-table-column prop="name" label="文件名" min-width="200" />
          <el-table-column prop="error" label="错误原因" min-width="200" />
        </el-table>
      </div>

      <div v-if="successResults.length === 0 && failedResults.length > 0" class="all-failed">
        <p>所有产证处理均失败</p>
        <el-button type="primary" round @click="goBatchAgain">重新上传</el-button>
      </div>
    </div>

    <!-- Actions -->
    <div v-if="successResults.length > 0" class="footer-actions">
      <el-button size="large" round @click="goBatchAgain">重新批量估值</el-button>
      <el-button size="large" type="primary" round :icon="Download" @click="handleExportExcel">
        导出 Excel 对比表
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.batch-results-container {
  max-width: 960px;
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
  align-items: center;
  gap: 16px;
  margin-bottom: 28px;
  flex-wrap: wrap;
}

.page-title {
  flex: 1;
  font-size: 1.6rem;
  font-weight: 800;
  color: #2c3e50;
  margin: 0;
}

.summary-cards {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
}

.summary-card {
  flex: 1;
  background: white;
  border-radius: 14px;
  padding: 20px;
  text-align: center;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}

.summary-num {
  display: block;
  font-size: 1.8rem;
  font-weight: 800;
  color: #409eff;
}

.summary-label {
  font-size: 0.85rem;
  color: #909399;
  margin-top: 4px;
}

.chart-card {
  background: white;
  border-radius: 16px;
  padding: 24px 20px 32px;
  margin-bottom: 24px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}

.table-card {
  background: white;
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}

.table-card h3 {
  margin: 0 0 16px;
  font-size: 1.1rem;
  color: #303133;
}

.failed-section {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
}

.failed-section h4 {
  margin: 0 0 12px;
  color: #e6a23c;
  font-size: 0.95rem;
}

.all-failed {
  text-align: center;
  padding: 40px 20px;
}

.all-failed p {
  font-size: 1.1rem;
  color: #909399;
  margin: 0 0 20px;
}

.footer-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
}

/* Responsive */
@media (max-width: 768px) {
  .batch-results-container {
    padding: 20px 14px;
  }
  .page-header {
    gap: 10px;
  }
  .page-title {
    font-size: 1.3rem;
  }
  .summary-cards {
    gap: 10px;
  }
  .summary-card {
    padding: 14px 10px;
  }
  .summary-num {
    font-size: 1.3rem;
  }
  .chart-card {
    padding: 16px 8px 24px;
  }
  .table-card {
    padding: 16px 10px;
    overflow-x: auto;
  }
  .footer-actions {
    flex-direction: column;
    gap: 12px;
  }
}

@media (max-width: 480px) {
  .batch-results-container {
    padding: 12px 8px;
  }
  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }
  .summary-num {
    font-size: 1.1rem;
  }
  .summary-label {
    font-size: 0.75rem;
  }
  .chart-card :deep(canvas) {
    max-height: 260px;
  }
}
</style>
