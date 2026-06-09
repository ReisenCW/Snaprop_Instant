<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, TrendCharts, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  MarkLineComponent,
} from 'echarts/components'
import { getMarketTrends } from '@/api'

use([
  CanvasRenderer,
  LineChart,
  BarChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  MarkLineComponent,
])

const router = useRouter()
const loading = ref(true)
const trendData = ref(null)
const selectedDistricts = ref(['全市', '黄浦', '静安', '徐汇', '浦东'])

// 所有可用的区域列表
const allDistricts = ref([])
const months = ref([])

// 配色
const districtColors = {
  '全市': '#409eff',
  '黄浦': '#e74c3c',
  '静安': '#e67e22',
  '徐汇': '#9b59b6',
  '长宁': '#1abc9c',
  '浦东': '#3498db',
  '虹口': '#f39c12',
  '杨浦': '#2ecc71',
  '普陀': '#e91e63',
  '闵行': '#00bcd4',
  '宝山': '#795548',
  '嘉定': '#607d8b',
  '松江': '#8bc34a',
  '青浦': '#ff9800',
  '奉贤': '#03a9f4',
  '金山': '#ff5722',
  '崇明': '#009688',
}

const goBack = () => router.back()

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getMarketTrends()
    if (res.data.success) {
      trendData.value = res.data.data
      allDistricts.value = Object.keys(trendData.value.districts)
      months.value = trendData.value.months || []
    } else {
      ElMessage.error(res.data.error || '获取行情数据失败')
    }
  } catch (err) {
    ElMessage.error('获取行情数据失败，请检查后端连接')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchData()
})

// ── 折线图：月度均价走势 ──
const lineChartOption = computed(() => {
  if (!trendData.value) return {}
  const { districts: data, months: m } = trendData.value

  const series = selectedDistricts.value.map((d) => ({
    name: d,
    type: 'line',
    data: (data[d] || []).map((e) => e.avg_price),
    smooth: true,
    symbol: 'circle',
    symbolSize: 6,
    lineStyle: { width: 2.5 },
    itemStyle: { color: districtColors[d] || undefined },
  }))

  return {
    title: {
      text: '上海各区月度均价走势',
      left: 'center',
      textStyle: { fontSize: 16, fontWeight: 600, color: '#303133' },
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        let html = `<strong>${params[0].axisValue}</strong><br/>`
        params.forEach((p) => {
          html += `${p.marker} ${p.seriesName}: <strong>${p.value.toLocaleString()}</strong> 元/m²<br/>`
        })
        return html
      },
    },
    legend: {
      bottom: 0,
      textStyle: { fontSize: 12 },
    },
    grid: { left: '3%', right: '4%', bottom: '12%', top: '18%', containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: m,
      axisLabel: { rotate: 30, fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      name: '元/m²',
      axisLabel: {
        formatter: (v) => (v / 10000).toFixed(1) + '万',
      },
      splitLine: { lineStyle: { type: 'dashed', color: '#e8e8e8' } },
    },
    series,
  }
})

// ── 柱状图：最新月份各区均价对比 ──
const barChartOption = computed(() => {
  if (!trendData.value) return {}
  const { districts: data, months: m } = trendData.value
  const latestMonth = m[m.length - 1] || ''

  const entries = Object.entries(data)
    .filter(([d]) => d !== '全市')
    .map(([district, values]) => {
      const latest = values[values.length - 1]
      return {
        district,
        price: latest ? latest.avg_price : 0,
      }
    })
    .sort((a, b) => b.price - a.price)

  return {
    title: {
      text: `${latestMonth} 各区均价对比`,
      left: 'center',
      textStyle: { fontSize: 16, fontWeight: 600, color: '#303133' },
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const p = params[0]
        return `${p.name}<br/>均价: <strong>${p.value.toLocaleString()}</strong> 元/m²`
      },
    },
    grid: { left: '3%', right: '8%', bottom: '8%', top: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: entries.map((e) => e.district),
      axisLabel: { rotate: 45, fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      name: '元/m²',
      axisLabel: {
        formatter: (v) => (v / 10000).toFixed(0) + '万',
      },
      splitLine: { lineStyle: { type: 'dashed', color: '#e8e8e8' } },
    },
    series: [
      {
        type: 'bar',
        data: entries.map((e, i) => ({
          value: e.price,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: districtColors[e.district] || '#409eff' },
              { offset: 1, color: 'rgba(64,158,255,0.3)' },
            ]),
            borderRadius: [6, 6, 0, 0],
          },
        })),
        barWidth: '55%',
        emphasis: {
          itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.2)' },
        },
      },
    ],
  }
})

// ── 柱状图：各区年涨跌幅度 ──
const changeChartOption = computed(() => {
  if (!trendData.value) return {}
  const { districts: data } = trendData.value

  const entries = Object.entries(data)
    .filter(([d]) => d !== '全市')
    .map(([district, values]) => {
      const first = values[0]
      const last = values[values.length - 1]
      const change = first && last ? ((last.avg_price - first.avg_price) / first.avg_price * 100) : 0
      return { district, change: Math.round(change * 100) / 100 }
    })
    .sort((a, b) => b.change - a.change)

  return {
    title: {
      text: '近一年各区涨跌幅度',
      left: 'center',
      textStyle: { fontSize: 16, fontWeight: 600, color: '#303133' },
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const v = params[0].value
        const label = v >= 0 ? '↑ 涨幅' : '↓ 跌幅'
        return `${params[0].name}<br/>${label}: <strong>${Math.abs(v).toFixed(2)}%</strong>`
      },
    },
    grid: { left: '3%', right: '8%', bottom: '8%', top: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: entries.map((e) => e.district),
      axisLabel: { rotate: 45, fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      name: '涨跌幅 (%)',
      axisLabel: { formatter: '{value}%' },
      splitLine: { lineStyle: { type: 'dashed', color: '#e8e8e8' } },
    },
    series: [
      {
        type: 'bar',
        data: entries.map((e) => ({
          value: e.change,
          itemStyle: {
            color: e.change >= 0
              ? new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                  { offset: 0, color: '#67C23A' },
                  { offset: 1, color: 'rgba(103,194,58,0.3)' },
                ])
              : new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                  { offset: 0, color: '#F56C6C' },
                  { offset: 1, color: 'rgba(245,108,108,0.3)' },
                ]),
            borderRadius: [6, 6, 0, 0],
          },
        })),
        barWidth: '55%',
        markLine: {
          silent: true,
          data: [{ yAxis: 0, lineStyle: { color: '#909399', type: 'dashed' } }],
        },
      },
    ],
  }
})

// Import echarts for graphic gradients
import * as echarts from 'echarts'

const toggleDistrict = (d) => {
  const idx = selectedDistricts.value.indexOf(d)
  if (idx >= 0) {
    if (selectedDistricts.value.length > 1) {
      selectedDistricts.value.splice(idx, 1)
    }
  } else {
    selectedDistricts.value.push(d)
  }
}

const isSelected = (d) => selectedDistricts.value.includes(d)

const displayName = (d) => d === '全市' ? '📊 ' + d : d
</script>

<template>
  <div class="market-page">
    <!-- Top bar -->
    <div class="page-top">
      <el-button :icon="ArrowLeft" @click="goBack" round plain>返回</el-button>
      <h1 class="page-title">
        <el-icon :size="24"><TrendCharts /></el-icon>
        上海房价行情
      </h1>
      <span class="date-range">数据区间：2025.07 — 2026.06</span>
    </div>

    <div v-loading="loading" class="market-content">
      <template v-if="trendData">
        <!-- District tag selector -->
        <div class="district-filter">
          <span class="filter-label">对比区域：</span>
          <el-checkbox-group v-model="selectedDistricts" :min="1" size="small">
            <el-checkbox-button
              v-for="d in allDistricts"
              :key="d"
              :value="d"
              :checked="isSelected(d)"
              class="district-tag"
            >
              {{ displayName(d) }}
            </el-checkbox-button>
          </el-checkbox-group>
        </div>

        <!-- Line chart -->
        <el-card shadow="hover" class="chart-card">
          <VChart
            :option="lineChartOption"
            :autoresize="true"
            style="height: 420px"
          />
        </el-card>

        <!-- Dual bar charts -->
        <el-row :gutter="24">
          <el-col :md="12" :span="24">
            <el-card shadow="hover" class="chart-card">
              <VChart
                :option="barChartOption"
                :autoresize="true"
                style="height: 380px"
              />
            </el-card>
          </el-col>
          <el-col :md="12" :span="24">
            <el-card shadow="hover" class="chart-card">
              <VChart
                :option="changeChartOption"
                :autoresize="true"
                style="height: 380px"
              />
            </el-card>
          </el-col>
        </el-row>

        <!-- Quick stats cards -->
        <el-row :gutter="20" class="stats-row">
          <el-col :sm="8" :span="24">
            <el-card shadow="hover" class="stat-mini-card">
              <div class="stat-mini-label">全市均价</div>
              <div class="stat-mini-value">
                {{ (trendData.districts['全市']?.slice(-1)[0]?.avg_price || 0).toLocaleString() }}
                <small>元/m²</small>
              </div>
            </el-card>
          </el-col>
          <el-col :sm="8" :span="24">
            <el-card shadow="hover" class="stat-mini-card">
              <div class="stat-mini-label">最高区域（黄浦）</div>
              <div class="stat-mini-value highlight">
                {{ (trendData.districts['黄浦']?.slice(-1)[0]?.avg_price || 0).toLocaleString() }}
                <small>元/m²</small>
              </div>
            </el-card>
          </el-col>
          <el-col :sm="8" :span="24">
            <el-card shadow="hover" class="stat-mini-card">
              <div class="stat-mini-label">近一年全市涨跌</div>
              <div
                class="stat-mini-value"
                :class="(() => {
                  const d = trendData.districts['全市']
                  if (!d || d.length < 2) return ''
                  const ch = ((d[d.length-1].avg_price - d[0].avg_price) / d[0].avg_price * 100)
                  return ch >= 0 ? 'up' : 'down'
                })()"
              >
                {{ (() => {
                  const d = trendData.districts['全市']
                  if (!d || d.length < 2) return '--'
                  const ch = ((d[d.length-1].avg_price - d[0].avg_price) / d[0].avg_price * 100)
                  return (ch >= 0 ? '+' : '') + ch.toFixed(2) + '%'
                })() }}
              </div>
            </el-card>
          </el-col>
        </el-row>
      </template>

      <el-empty v-else-if="!loading" description="暂无行情数据" />
    </div>
  </div>
</template>

<style scoped>
.market-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 30px 40px;
  min-height: 80vh;
  animation: fadeSlideIn 0.45s ease-out;
}

@keyframes fadeSlideIn {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

.page-top {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 28px;
  flex-wrap: wrap;
}

.page-title {
  font-size: 1.8rem;
  font-weight: 700;
  color: #2c3e50;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.date-range {
  font-size: 0.9rem;
  color: #909399;
  margin-left: auto;
  background: #f0f2f5;
  padding: 6px 16px;
  border-radius: 20px;
}

/* District filter */
.district-filter {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 24px;
  padding: 14px 20px;
  background: white;
  border-radius: 14px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}

.filter-label {
  font-weight: 600;
  color: #303133;
  font-size: 0.95rem;
  white-space: nowrap;
}

.district-tag {
  margin: 0 !important;
}

.district-tag :deep(.el-checkbox-button__inner) {
  border-radius: 8px !important;
  border: 1px solid #e4e7ed !important;
  padding: 5px 14px !important;
  font-size: 0.88rem;
}

.district-tag :deep(.el-checkbox-button.is-checked .el-checkbox-button__inner) {
  background: #409eff !important;
  border-color: #409eff !important;
  color: white !important;
}

/* Chart cards */
.chart-card {
  margin-bottom: 24px;
  border-radius: 16px;
  border: 1px solid #ebeef5;
  box-shadow: 0 4px 16px rgba(0,0,0,0.04);
  transition: box-shadow 0.3s;
}

.chart-card:hover {
  box-shadow: 0 8px 28px rgba(0,0,0,0.08);
}

/* Stat mini cards */
.stats-row {
  margin-bottom: 32px;
}

.stat-mini-card {
  border-radius: 14px;
  border: 1px solid #ebeef5;
  text-align: center;
  padding: 8px 0;
}

.stat-mini-label {
  font-size: 0.88rem;
  color: #909399;
  margin-bottom: 8px;
}

.stat-mini-value {
  font-size: 1.8rem;
  font-weight: 800;
  color: #303133;
}

.stat-mini-value small {
  font-size: 0.85rem;
  font-weight: 400;
  color: #909399;
  margin-left: 4px;
}

.stat-mini-value.highlight {
  color: #e74c3c;
}

.stat-mini-value.up {
  color: #67C23A;
}

.stat-mini-value.down {
  color: #F56C6C;
}

/* Responsive */
@media (max-width: 768px) {
  .market-page {
    padding: 20px 14px;
  }
  .page-title {
    font-size: 1.4rem;
  }
  .date-range {
    margin-left: 0;
    margin-top: 4px;
    width: 100%;
    text-align: center;
  }
  .district-filter {
    padding: 10px 14px;
    gap: 4px;
  }
  .stat-mini-value {
    font-size: 1.4rem;
  }
}
</style>
