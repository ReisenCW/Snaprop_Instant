<template>
  <div>
    <h1>导出</h1>

    <div class="card">
      <h2>导出测试用例</h2>
      <div class="form-group">
        <label>选择需求（可选，不选则导出全部）</label>
        <select v-model="selectedRequirementId">
          <option value="">全部</option>
          <option v-for="req in requirements" :key="req.id" :value="req.id">
            {{ req.id }} - {{ req.description.substring(0, 50) }}...
          </option>
        </select>
      </div>
      <div class="export-buttons">
        <button class="btn btn-primary" @click="exportJSON" :disabled="loading">
          {{ loading ? '导出中...' : '导出 JSON' }}
        </button>
        <button class="btn btn-success" @click="exportCSV" :disabled="loading">
          {{ loading ? '导出中...' : '导出 CSV' }}
        </button>
        <button class="btn btn-secondary" @click="exportExcel" :disabled="loading">
          {{ loading ? '导出中...' : '导出 Excel' }}
        </button>
      </div>
    </div>

    <div class="card">
      <h2>导出完整报告</h2>
      <div class="form-group">
        <label>选择需求</label>
        <select v-model="selectedRequirementIdForFull">
          <option value="">请选择需求</option>
          <option v-for="req in requirements" :key="req.id" :value="req.id">
            {{ req.id }} - {{ req.description.substring(0, 50) }}...
          </option>
        </select>
      </div>
      <button class="btn btn-primary" @click="exportFull" :disabled="loading || !selectedRequirementIdForFull">
        {{ loading ? '导出中...' : '导出完整报告（JSON）' }}
      </button>
    </div>

    <div class="card">
      <h2>导出风险评分</h2>
      <div class="export-buttons">
        <button class="btn btn-primary" @click="exportRisksJSON" :disabled="loading">
          {{ loading ? '导出中...' : '导出 JSON' }}
        </button>
        <button class="btn btn-success" @click="exportRisksCSV" :disabled="loading">
          {{ loading ? '导出中...' : '导出 CSV' }}
        </button>
        <button class="btn btn-secondary" @click="exportRisksExcel" :disabled="loading">
          {{ loading ? '导出中...' : '导出 Excel' }}
        </button>
      </div>
    </div>

    <div v-if="message" :class="messageType">{{ message }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { requirementsApi, exportApi } from '@/api'
import type { Requirement } from '@/types'

const requirements = ref<Requirement[]>([])
const selectedRequirementId = ref('')
const selectedRequirementIdForFull = ref('')
const loading = ref(false)
const message = ref('')
const messageType = ref('success')

const loadRequirements = async () => {
  try {
    const res = await requirementsApi.list()
    requirements.value = res.data
  } catch {
    message.value = '加载需求失败'
    messageType.value = 'error'
  }
}

const downloadFile = (data: Blob, filename: string) => {
  const url = window.URL.createObjectURL(data)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

const downloadJSON = (data: unknown, filename: string) => {
  const json = JSON.stringify(data, null, 2)
  const blob = new Blob([json], { type: 'application/json' })
  downloadFile(blob, filename)
}

const exportJSON = async () => {
  loading.value = true
  try {
    const res = await exportApi.json(selectedRequirementId.value || undefined)
    downloadJSON(res.data, 'testcases.json')
    message.value = '导出成功'
    messageType.value = 'success'
  } catch {
    message.value = '导出失败'
    messageType.value = 'error'
  } finally {
    loading.value = false
  }
}

const exportCSV = async () => {
  loading.value = true
  try {
    const res = await exportApi.csv(selectedRequirementId.value || undefined)
    downloadFile(res.data, 'testcases.csv')
    message.value = '导出成功'
    messageType.value = 'success'
  } catch {
    message.value = '导出失败'
    messageType.value = 'error'
  } finally {
    loading.value = false
  }
}

const exportExcel = async () => {
  loading.value = true
  try {
    const res = await exportApi.excel(selectedRequirementId.value || undefined)
    downloadFile(res.data, 'testcases.xlsx')
    message.value = '导出成功'
    messageType.value = 'success'
  } catch {
    message.value = '导出失败'
    messageType.value = 'error'
  } finally {
    loading.value = false
  }
}

const exportFull = async () => {
  if (!selectedRequirementIdForFull.value) return
  loading.value = true
  try {
    const res = await exportApi.full(selectedRequirementIdForFull.value)
    downloadJSON(res.data, `full_report_${selectedRequirementIdForFull.value}.json`)
    message.value = '导出成功'
    messageType.value = 'success'
  } catch {
    message.value = '导出失败'
    messageType.value = 'error'
  } finally {
    loading.value = false
  }
}

const exportRisksJSON = async () => {
  loading.value = true
  try {
    const res = await exportApi.risksJson()
    downloadJSON(res.data, 'risks.json')
    message.value = '导出成功'
    messageType.value = 'success'
  } catch {
    message.value = '导出失败'
    messageType.value = 'error'
  } finally {
    loading.value = false
  }
}

const exportRisksCSV = async () => {
  loading.value = true
  try {
    const res = await exportApi.risksCsv()
    downloadFile(res.data, 'risks.csv')
    message.value = '导出成功'
    messageType.value = 'success'
  } catch {
    message.value = '导出失败'
    messageType.value = 'error'
  } finally {
    loading.value = false
  }
}

const exportRisksExcel = async () => {
  loading.value = true
  try {
    const res = await exportApi.risksExcel()
    downloadFile(res.data, 'risks.xlsx')
    message.value = '导出成功'
    messageType.value = 'success'
  } catch {
    message.value = '导出失败'
    messageType.value = 'error'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadRequirements()
})
</script>

<style scoped>
.export-buttons {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}
</style>
