<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { UploadFilled, Edit, ArrowRight, Crop, Plus, Delete, Download, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import 'vue-cropper/dist/index.css'
import { VueCropper } from 'vue-cropper'
import { houseStore } from '@/store'
import * as XLSX from 'xlsx'
import { uploadCert, exportExcel as exportExcelApi } from '@/api'
import { API_BASE_URL } from '@/config'

const router = useRouter()
const isLoading = ref(false)
const cropperVisible = ref(false)
const cropperImg = ref('')
const cropperRef = ref(null)
const uploadedImageUrl = ref('')
const currentFile = ref(null)

// OCR Table data
const ocrTableData = ref([])

const houseInfo = houseStore

// 专家权重
const weights = reactive({
  area: 0.20,
  type: 0.15,
  direction: 0.15,
  structure: 0.15,
  floor: 0.10,
  decoration: 0.10,
  year: 0.10,
  time: 0.05
})

const defaultWeights = { ...weights }

const resetWeights = () => {
  Object.assign(weights, defaultWeights)
}

const nextStep = () => {
  // 校验逻辑
  // 确保 houseInfo 的属性是定义的，避免 undefined
  const address = houseInfo.address ? houseInfo.address.trim() : ''
  const city = houseInfo.city ? houseInfo.city.trim() : ''
  const area = parseFloat(houseInfo.area)

  if (!address) {
    ElMessage.warning('请输入房产地址')
    return
  }
  // 简单的地址长度校验
  if (address.length < 2) {
     ElMessage.warning('房产地址似乎过短，请输入完整地址')
     return
  }

  if (!city) {
    ElMessage.warning('请输入所在城市')
    return
  }
  if (isNaN(area) || area <= 0) {
    ElMessage.warning('请输入有效的建筑面积')
    return
  }
  // 修正年份校验逻辑：houseInfo.year 应该是一个有效对象或值
  if (!houseInfo.year) {
    ElMessage.warning('请选择建成年份')
    return
  }
  
  // 户型校验（至少有一室或一厅等）
  const totalRooms = (houseInfo.rooms || 0) + (houseInfo.halls || 0) + (houseInfo.kitchens || 0) + (houseInfo.bathrooms || 0)
  if (totalRooms === 0) {
    ElMessage.warning('请填写完整的户型信息')
    return
  }
  
  // 保存专家权重到 store
  houseStore.selectionWeights = { ...weights }
  
  // 将 houseInfo 中的数据正确传递到 step2 (假设通过 store 持久化或路由传递)
  // 这里我们已经使用了 pinia store，可以直接跳转
  router.push('/home/step2')
}

const handleBeforeUpload = (file) => {
  const isImage = file.type.startsWith('image/')
  if (!isImage) {
    ElMessage.error('请上传图片文件 (JPG, PNG)')
    return false
  }
  // 限制文件大小，例如 10MB
  const isLt10M = file.size / 1024 / 1024 < 10
  if (!isLt10M) {
    ElMessage.error('上传图片大小不能超过 10MB!')
    return false
  }

  currentFile.value = file
  const reader = new FileReader()
  reader.onload = (e) => {
    cropperImg.value = e.target.result
    cropperVisible.value = true
  }
  // 错误处理
  reader.onerror = () => {
    ElMessage.error('读取文件失败，请重试')
  }
  reader.readAsDataURL(file)
  return false // Prevent auto upload by el-upload default action
}

const confirmCrop = () => {
  if (!cropperRef.value) return
  
  cropperRef.value.getCropBlob(async (blob) => {
    isLoading.value = true
    try {
      // Create file from blob, ensuring explicit types
      const file = new File([blob], currentFile.value.name, { type: 'image/jpeg' })
      
      // Call backend OCR API
      const response = await uploadCert(file)
      
      if (response && response.data && response.data.success) {
        // 使用 API_BASE_URL 构建完整 URL，假设后端返回相对路径
        const _url = response.data.url
        uploadedImageUrl.value = _url.startsWith('http') ? _url : `${API_BASE_URL}${_url}`
        
        // 存入全局 store
        houseInfo.cert_image = _url
        
        // 关键修复：后端现在直接返回 [{field, value}] 数组对象，直接赋值即可
        ocrTableData.value = response.data.table_data || []
        
        ElMessage.success('识别成功')
        cropperVisible.value = false
      } else {
        const errorMsg = response?.data?.error || '识别失败，请检查图片清晰度'
        ElMessage.error(errorMsg)
      }
    } catch (error) {
      console.error('OCR Error:', error)
      ElMessage.error('无法连接到后端接口，请检查网络或服务状态')
    } finally {
      isLoading.value = false
    }
  })
}

const addRow = () => {
  ocrTableData.value.push({ field: '', value: '' })
}

const removeRow = (index) => {
  ocrTableData.value.splice(index, 1)
}

const syncToBasicInfo = () => {
  if (ocrTableData.value.length === 0) {
    ElMessage.warning('表格无数据可同步')
    return
  }

  let syncCount = 0
  
  // Logic to parse table data back to houseStore
  // 使用更健壮的正则匹配，不仅仅是 includes
  ocrTableData.value.forEach(row => {
    const field = row.field ? row.field.trim() : ''
    const value = row.value ? row.value.trim() : ''
    
    if (!field || !value) return

    // 地址匹配
    if (field.includes('地址') || field.includes('座落') || field.includes('位置')) {
      houseStore.address = value
      syncCount++
    }
    // 城市匹配：需要排除仅仅包含“城市”字样但不是城市名字的情况，这里简单赋值
    if (field === '城市' || field.includes('所在城市')) {
      houseStore.city = value
      syncCount++
    }
    // 面积匹配：提取数字
    if (field.includes('面积')) {
      const areaMatch = value.match(/[\d.]+/)
      if (areaMatch) {
         const parsedArea = parseFloat(areaMatch[0])
         if (!isNaN(parsedArea)) {
            houseStore.area = parsedArea
            syncCount++
         }
      }
    }
    // 户型匹配：X室X厅X卫
    if (field.includes('户型') || field.includes('房型')) {
      const r = value.match(/(\d+)\s*[室房]/)
      const h = value.match(/(\d+)\s*厅/)
      const b = value.match(/(\d+)\s*卫/)
      const k = value.match(/(\d+)\s*厨/)
      
      if (r) houseStore.rooms = parseInt(r[1])
      if (h) houseStore.halls = parseInt(h[1])
      if (b) houseStore.bathrooms = parseInt(b[1])
      if (k) houseStore.kitchens = parseInt(k[1])
      if (r || h || b || k) syncCount++
    }
    // 年份匹配：提取4位年份
    if (field.includes('年份') || field.includes('建成') || field.includes('年代')) {
      const yearStr = value.match(/(19|20)\d{2}/)
      if (yearStr) {
        // 设置为该年 1月1日
        houseStore.year = new Date(parseInt(yearStr[0]), 0, 1)
        syncCount++
      }
    }
  })
  
  if (syncCount > 0) {
      ElMessage.success(`已同步 ${syncCount} 项信息至下方表单`)
  } else {
      ElMessage.info('未能自动匹配到相关字段，请手动填写')
  }
}

const downloadExcel = () => {
  if (ocrTableData.value.length === 0) {
    ElMessage.warning('表格无数据可导出')
    return
  }
  try {
      const worksheet = XLSX.utils.json_to_sheet(ocrTableData.value)
      const workbook = XLSX.utils.book_new()
      XLSX.utils.book_append_sheet(workbook, worksheet, "OCR_Result")
      XLSX.writeFile(workbook, "house_ocr_result.xlsx")
      ElMessage.success('导出成功')
  } catch (e) {
      console.error(e)
      ElMessage.error('导出失败')
  }
}

const handleUploadSuccess = (response) => {
  // Logic to handle OCR result from backend
  console.log('OCR Result:', response)
}

const reUpload = () => {
  uploadedImageUrl.value = ''
  currentFile.value = null
  // 清空表格数据，或者询问用户是否保留
  // ocrTableData.value = [] 
}

const openOriginalImage = () => {
  if (uploadedImageUrl.value) {
    window.open(uploadedImageUrl.value, '_blank')
  }
}
</script>

<template>
  <div class="step-one-container">
    <!-- Title Section -->
    <div class="header-section">
      <div class="title-row">
        <h2 class="step-title">步骤 1: 提取房产基本信息</h2>
      </div>
      <p class="step-description">上传房产证或不动产登记证照片，AI 将自动识别并提取关键信息。您也可以手动完善以下表单。</p>
    </div>

    <!-- Content Layout -->
    <div class="main-content">
      <!-- Top: Upload & OCR Table Section -->
      <div v-if="!uploadedImageUrl">
        <el-card shadow="never" class="upload-card">
          <el-upload
            class="drag-upload"
            drag
            action="#"
            :show-file-list="false"
            :before-upload="handleBeforeUpload"
            accept=".png,.jpg,.jpeg"
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">
              将房产证图片拖到此处，或 <em>点击上传</em> 进行 AI 识别
            </div>
          </el-upload>
        </el-card>
      </div>
      
      <div v-else class="upload-ocr-row">
        <!-- Left: Image Display -->
        <el-card shadow="hover" class="image-display-card">
          <div class="uploaded-container">
            <div class="image-preview-wrapper-large">
              <el-image 
                :src="uploadedImageUrl" 
                :preview-src-list="[uploadedImageUrl]"
                fit="contain"
                class="preview-img-large"
              />
              <div class="image-actions-overlay">
                <el-button type="info" size="small" :icon="Refresh" @click="reUpload" plain>
                  重新上传
                </el-button>
                <el-button type="primary" size="small" :icon="Plus" @click="openOriginalImage">
                  查看原图
                </el-button>
              </div>
            </div>
          </div>
        </el-card>

        <!-- Right: OCR Editable Table -->
        <el-card shadow="hover" class="ocr-table-card">
          <template #header>
            <div class="ocr-header">
              <span class="ocr-title">AI 识别结果 (可编辑)</span>
              <el-button type="success" link :icon="Plus" @click="addRow">添加行</el-button>
            </div>
          </template>
          
          <el-table :data="ocrTableData" border stripe height="250">
            <el-table-column label="字段名称">
              <template #default="scope">
                <el-input v-model="scope.row.field" placeholder="字段名" />
              </template>
            </el-table-column>
            <el-table-column label="识别内容">
              <template #default="scope">
                <el-input v-model="scope.row.value" placeholder="识别内容" />
              </template>
            </el-table-column>
            <el-table-column width="60">
              <template #default="scope">
                <el-button type="danger" circle :icon="Delete" @click="removeRow(scope.$index)" size="small" />
              </template>
            </el-table-column>
          </el-table>

          <div class="ocr-footer-actions">
            <el-button type="primary" :icon="Refresh" @click="syncToBasicInfo" plain>同步至下方表单</el-button>
            <el-button type="info" :icon="Download" @click="downloadExcel" plain>导出 Excel</el-button>
          </div>
        </el-card>
      </div>

      <!-- Bottom: Form Section -->
      <el-card shadow="never" class="form-card mt-20">
        <template #header>
          <div class="card-header">
            <span><el-icon><edit /></el-icon> 基本信息确认</span>
          </div>
        </template>
        
        <el-form :model="houseInfo" label-position="top">
          <!-- Form rows... -->
          <el-row :gutter="20">
            <el-col :span="16">
              <el-form-item label="房产地址">
                <el-input v-model="houseInfo.address" placeholder="请输入完整房产地址" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="所在城市">
                <el-input v-model="houseInfo.city" placeholder="请输入所在城市" />
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item label="建筑面积 (㎡)">
                <el-input-number v-model="houseInfo.area" :precision="2" :step="0.1" controls-position="right" style="width: 100%" />
              </el-form-item>
            </el-col>
            <el-col :span="16">
              <el-form-item label="户型">
                <div class="layout-group">
                  <el-input-number v-model="houseInfo.rooms" :min="0" :max="10" controls-position="right" style="width: 22%" />
                  <span class="unit">室</span>
                  <el-input-number v-model="houseInfo.halls" :min="0" :max="10" controls-position="right" style="width: 22%" />
                  <span class="unit">厅</span>
                  <el-input-number v-model="houseInfo.kitchens" :min="0" :max="10" controls-position="right" style="width: 22%" />
                  <span class="unit">厨</span>
                  <el-input-number v-model="houseInfo.bathrooms" :min="0" :max="10" controls-position="right" style="width: 22%" />
                  <span class="unit">卫</span>
                </div>
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item label="房屋结构">
                <el-select v-model="houseInfo.structure" placeholder="请选择" style="width: 100%">
                  <el-option label="平层" value="平层" />
                  <el-option label="复式" value="复式" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="装修情况">
                <el-select v-model="houseInfo.decoration" placeholder="请选择" style="width: 100%">
                  <el-option label="毛坯" value="毛坯" />
                  <el-option label="简装" value="简装" />
                  <el-option label="精装" value="精装" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="绿化率 (%)">
                <el-input-number v-model="houseInfo.green_rate" :min="0" :max="100" controls-position="right" style="width: 100%" />
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item label="所在楼层">
                <el-select v-model="houseInfo.floor" placeholder="请选择" style="width: 100%">
                  <el-option label="低楼层" value="低" />
                  <el-option label="中楼层" value="中" />
                  <el-option label="高楼层" value="高" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="朝向">
                <el-select v-model="houseInfo.direction" placeholder="请选择" style="width: 100%">
                  <el-option label="东" value="东" />
                  <el-option label="南" value="南" />
                  <el-option label="西" value="西" />
                  <el-option label="北" value="北" />
                  <el-option label="东南" value="东南" />
                  <el-option label="西南" value="西南" />
                  <el-option label="东北" value="东北" />
                  <el-option label="西北" value="西北" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="建成年份">
                <el-date-picker v-model="houseInfo.year" type="year" placeholder="年份" style="width: 100%" />
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>

        <!-- 专家权重调整区域 -->
        <el-collapse style="margin-top: 20px">
          <el-collapse-item title="⚙️ 专家参数调整（可选）" name="expert">
            <div style="color: #909399; font-size: 12px; margin-bottom: 10px;">
              以下参数用于调整相似案例检索权重，仅供专家使用
            </div>
            <el-row :gutter="15">
              <el-col :span="6">
                <div class="weight-item">
                  <span>面积权重</span>
                  <el-slider v-model="weights.area" :min="0" :max="1" :step="0.05" show-stops />
                  <span class="weight-value">{{ weights.area }}</span>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="weight-item">
                  <span>户型权重</span>
                  <el-slider v-model="weights.type" :min="0" :max="1" :step="0.05" show-stops />
                  <span class="weight-value">{{ weights.type }}</span>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="weight-item">
                  <span>朝向权重</span>
                  <el-slider v-model="weights.direction" :min="0" :max="1" :step="0.05" show-stops />
                  <span class="weight-value">{{ weights.direction }}</span>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="weight-item">
                  <span>结构权重</span>
                  <el-slider v-model="weights.structure" :min="0" :max="1" :step="0.05" show-stops />
                  <span class="weight-value">{{ weights.structure }}</span>
                </div>
              </el-col>
            </el-row>
            <el-row :gutter="15" style="margin-top: 10px">
              <el-col :span="6">
                <div class="weight-item">
                  <span>楼层权重</span>
                  <el-slider v-model="weights.floor" :min="0" :max="1" :step="0.05" show-stops />
                  <span class="weight-value">{{ weights.floor }}</span>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="weight-item">
                  <span>装修权重</span>
                  <el-slider v-model="weights.decoration" :min="0" :max="1" :step="0.05" show-stops />
                  <span class="weight-value">{{ weights.decoration }}</span>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="weight-item">
                  <span>年份权重</span>
                  <el-slider v-model="weights.year" :min="0" :max="1" :step="0.05" show-stops />
                  <span class="weight-value">{{ weights.year }}</span>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="weight-item">
                  <span>时间权重</span>
                  <el-slider v-model="weights.time" :min="0" :max="1" :step="0.05" show-stops />
                  <span class="weight-value">{{ weights.time }}</span>
                </div>
              </el-col>
            </el-row>
            <div style="margin-top: 10px; text-align: right;">
              <el-button size="small" @click="resetWeights">恢复默认</el-button>
            </div>
          </el-collapse-item>
        </el-collapse>

        <div class="action-footer">
          <el-button type="primary" size="large" @click="nextStep" round>
            下一步：上传环境照片 <el-icon class="el-icon--right"><arrow-right /></el-icon>
          </el-button>
        </div>
      </el-card>

      <!-- Cropper Dialog -->
      <el-dialog v-model="cropperVisible" title="剪裁房产证照片" width="600px" align-center>
        <div class="cropper-wrapper">
          <vue-cropper
            ref="cropperRef"
            :img="cropperImg"
            :autoCrop="true"
            :autoCropWidth="400"
            :autoCropHeight="300"
            :fixed="false"
            :centerBox="true"
            :info="true"
            style="height: 400px"
          />
        </div>
        <template #footer>
          <el-button @click="cropperVisible = false">取消</el-button>
          <el-button type="primary" :loading="isLoading" @click="confirmCrop">确认剪裁并上传</el-button>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<style scoped>
.step-one-container {
  animation: fadeIn 0.5s ease-in-out;
}

.header-section {
  margin-bottom: 30px;
}

.step-title {
  color: #2c3e50;
  font-size: 1.8rem;
  margin-bottom: 10px;
}

.step-description {
  color: #7f8c8d;
  font-size: 1rem;
  line-height: 1.6;
}

.upload-card, .form-card, .image-display-card, .ocr-table-card {
  border-radius: 12px;
}

.upload-ocr-row {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
}

.image-display-card {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.ocr-table-card {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.ocr-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.ocr-title {
  font-weight: 600;
  color: #409eff;
}

.ocr-footer-actions {
  margin-top: 15px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.mt-20 {
  margin-top: 20px;
}

.drag-upload {
  width: 100%;
}

:deep(.el-upload-dragger) {
  padding: 60px 20px;
  background-color: #fafafa;
  border: 2px dashed #dcdfe6;
}

.uploaded-container {
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}

.image-preview-wrapper-large {
  width: 100%;
  max-width: 600px;
  height: 300px;
  position: relative;
  background-color: #f5f7fa;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #e4e7ed;
}

.preview-img-large {
  width: 100%;
  height: 100%;
}

.image-actions-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(0, 0, 0, 0.5);
  padding: 10px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 15px;
}

.card-header {
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.floor-group, .layout-group {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.unit {
  margin: 0 4px;
  color: #606266;
  font-size: 14px;
}

:deep(.el-input-number.is-controls-right .el-input-number__decrease),
:deep(.el-input-number.is-controls-right .el-input-number__increase) {
  width: 20px;
}

.action-footer {
  margin-top: 30px;
  text-align: right;
}

.cropper-wrapper {
  height: 400px;
}

.ml-10 {
  margin-left: 10px;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
.weight-item {
  text-align: center;
  padding: 5px;
}
.weight-item span {
  display: block;
  font-size: 12px;
  color: #606266;
  margin-bottom: 5px;
}
.weight-value {
  display: inline-block;
  margin-top: 5px;
  font-size: 12px;
  color: #409EFF;
  font-weight: bold;
}
</style>
