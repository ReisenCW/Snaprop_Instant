<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { uploadCert, batchExtractFields } from '@/api'
import { houseStore } from '@/store'

const router = useRouter()
const fileList = ref([])
const processing = ref(false)
const progress = ref(0)
const progressText = ref('')
const results = ref([])

const canStart = computed(() => fileList.value.length > 0 && !processing.value)

const handleFileChange = (file, fileListNew) => {
  fileList.value = fileListNew
}

const handleRemove = () => {
  // Just let the upload component handle it
}

const processBatch = async () => {
  if (fileList.value.length === 0) {
    ElMessage.warning('请先上传房产证图片')
    return
  }

  processing.value = true
  progress.value = 0
  progressText.value = '准备开始...'
  results.value = []

  const total = fileList.value.length

  for (let i = 0; i < total; i++) {
    const fileItem = fileList.value[i]
    const rawFile = fileItem.raw || fileItem
    progressText.value = `正在识别第 ${i + 1}/${total} 份产证...`

    try {
      const ocrRes = await uploadCert(rawFile)
      if (!ocrRes.data.success) {
        results.value.push({
          name: rawFile.name,
          status: 'failed',
          error: ocrRes.data.error || 'OCR识别失败'
        })
      } else {
        progressText.value = `正在AI解析第 ${i + 1}/${total} 份产证...`

        // Use LLM to extract all fields from OCR table data
        const tableData = ocrRes.data.table_data || []
        let fields = null
        try {
          const extractRes = await batchExtractFields(tableData)
          if (extractRes.data?.success) {
            fields = extractRes.data.fields
          }
        } catch (extractErr) {
          console.warn('LLM extraction failed, using regex fallback:', extractErr)
        }

        // Fallback to regex-extracted data if LLM fails
        if (!fields) {
          const ex = ocrRes.data.extracted_data || {}
          fields = {
            address: ex.address || '',
            city: ex.city || houseStore.city || '上海',
            area: ex.area || 100,
            room: ex.room || 3,
            hall: ex.hall || 2,
            kitchen: ex.kitchen || 1,
            bathroom: ex.bathroom || 1,
            floor: ex.floor || '中楼层',
            fitment: ex.fitment || ex.decoration || '精装',
            structure: ex.structure || '平层',
            direction: ex.direction || '南',
            year: ex.year || 2015,
            green_rate: ex.green_rate || 35,
          }
        }

        results.value.push({
          name: rawFile.name,
          status: 'success',
          cert_image: ocrRes.data.extracted_data?.cert_image || '',
          data: fields
        })
      }
    } catch (err) {
      results.value.push({
        name: rawFile.name,
        status: 'failed',
        error: err.message || '网络错误'
      })
    }

    progress.value = Math.round(((i + 1) / total) * 100)
  }

  processing.value = false
  progressText.value = ''

  const successCount = results.value.filter(r => r.status === 'success').length
  if (successCount > 0) {
    ElMessage.success(`OCR 识别完成！成功 ${successCount}/${total}，请核对信息`)
    houseStore.batchExtractions = results.value
    setTimeout(() => {
      router.push('/home/batch-review')
    }, 600)
  } else {
    ElMessage.error('所有产证识别失败，请检查后重试')
  }
}

const goBack = () => {
  router.push('/home/mode')
}
</script>

<template>
  <div class="batch-upload-container">
    <div class="page-header">
      <h1 class="page-title">批量估值</h1>
      <p class="page-desc">上传多份房产证图片，系统将自动识别关键信息，您可在确认修改后再进行批量估值</p>
    </div>

    <!-- Upload area -->
    <div class="upload-section" v-if="results.length === 0">
      <el-upload
        v-model:file-list="fileList"
        drag
        multiple
        :limit="10"
        :auto-upload="false"
        accept="image/*"
        :on-change="handleFileChange"
        :on-remove="handleRemove"
        class="batch-uploader"
      >
        <el-icon class="el-icon--upload" :size="64"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          将房产证图片拖到此处，或 <em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            支持 JPG/PNG 格式，最多上传 10 张，每份产证将单独处理
          </div>
        </template>
      </el-upload>

      <!-- File list preview -->
      <div v-if="fileList.length > 0" class="file-preview-list">
        <div class="file-count">
          已选择 <strong>{{ fileList.length }}</strong> 份产证
        </div>
        <div class="file-names">
          <el-tag
            v-for="(f, idx) in fileList"
            :key="idx"
            closable
            @close="fileList.splice(idx, 1)"
            class="file-tag"
          >
            {{ f.name }}
          </el-tag>
        </div>
      </div>

      <!-- Action -->
      <div v-if="fileList.length > 0" class="upload-actions">
        <el-button round @click="goBack">返回选择</el-button>
        <el-button
          type="primary"
          size="large"
          round
          :loading="processing"
          :disabled="!canStart"
          @click="processBatch"
        >
          {{ processing ? '识别中...' : `开始 OCR 识别 (${fileList.length} 份)` }}
        </el-button>
      </div>

      <!-- Progress -->
      <div v-if="processing" class="batch-progress">
        <el-progress :percentage="progress" :stroke-width="12" :color="progress < 100 ? '#409eff' : '#67c23a'" />
        <p class="progress-text">{{ progressText }}</p>
      </div>
    </div>

    <!-- Quick result summary (shown during processing) -->
    <div v-if="results.length > 0 && processing" class="interim-results">
      <h3>处理进度</h3>
      <el-table :data="results" size="small" stripe>
        <el-table-column prop="name" label="文件名" min-width="160" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
              {{ row.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="识别地址" min-width="200">
          <template #default="{ row }">{{ row.data?.address || '-' }}</template>
        </el-table-column>
        <el-table-column prop="error" label="错误信息" min-width="140" />
      </el-table>
    </div>
  </div>
</template>

<style scoped>
.batch-upload-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 30px 20px;
  animation: fadeSlideIn 0.5s ease-out;
}

@keyframes fadeSlideIn {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

.page-header {
  text-align: center;
  margin-bottom: 32px;
}

.page-title {
  font-size: 1.8rem;
  font-weight: 800;
  color: #2c3e50;
  margin: 0 0 6px;
}

.page-desc {
  font-size: 1rem;
  color: #909399;
  margin: 0;
}

.upload-section {
  background: white;
  border-radius: 20px;
  padding: 36px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.05);
}

.batch-uploader :deep(.el-upload-dragger) {
  border-radius: 16px;
  border: 2px dashed #dcdfe6;
  padding: 48px 20px;
  transition: all 0.3s ease;
}

.batch-uploader :deep(.el-upload-dragger:hover) {
  border-color: #409eff;
  background: #f5f8ff;
}

.file-preview-list {
  margin-top: 24px;
  padding: 20px;
  background: #f8fafc;
  border-radius: 12px;
}

.file-count {
  font-size: 1rem;
  color: #303133;
  margin-bottom: 12px;
}

.file-names {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.file-tag {
  margin: 0;
}

.upload-actions {
  margin-top: 24px;
  display: flex;
  justify-content: center;
  gap: 16px;
}

.batch-progress {
  margin-top: 28px;
  text-align: center;
}

.progress-text {
  margin-top: 12px;
  font-size: 0.95rem;
  color: #606266;
}

.interim-results {
  margin-top: 28px;
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}

.interim-results h3 {
  margin: 0 0 16px;
  font-size: 1.1rem;
  color: #303133;
}

/* Responsive */
@media (max-width: 768px) {
  .batch-upload-container {
    padding: 20px 14px;
  }
  .upload-section {
    padding: 24px 16px;
    border-radius: 16px;
  }
  .batch-uploader :deep(.el-upload-dragger) {
    padding: 32px 12px;
  }
  .page-title {
    font-size: 1.5rem;
  }
  .upload-actions {
    flex-direction: column;
  }
}

@media (max-width: 480px) {
  .batch-upload-container {
    padding: 12px 8px;
  }
  .upload-section {
    padding: 16px 10px;
    border-radius: 14px;
  }
  .page-title {
    font-size: 1.3rem;
  }
  .page-desc {
    font-size: 0.85rem;
  }
  .file-preview-list {
    padding: 14px;
  }
}
</style>
