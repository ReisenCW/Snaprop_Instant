<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { CameraFilled, ArrowLeft, Promotion, ZoomIn, Delete, MagicStick, InfoFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { houseStore } from '@/store'
import { startValuation } from '@/api'
import { compressImageIfNeeded } from '@/utils/imageCompression'

const router = useRouter()
const fileList = ref([])
const isLoading = ref(false)

const houseInfo = houseStore

const dialogImageUrl = ref('')
const dialogVisible = ref(false)

const previewSrcList = computed(() => fileList.value.map(item => item.url))

const prevStep = () => {
  router.push('/home/step1')
}

const startAnalysis = async () => {
  // 组装数据调用后端（照片可选）
  const valuationData = {
    address: houseInfo.address,
    city: houseInfo.city,
    area: houseInfo.area,
    room: houseInfo.rooms,
    hall: houseInfo.halls,
    kitchen: houseInfo.kitchens,
    bathroom: houseInfo.bathrooms,
    structure: houseInfo.structure,
    fitment: houseInfo.decoration,
    year: houseInfo.year instanceof Date ? houseInfo.year.getFullYear() : houseInfo.year,
    enable_prediction: houseInfo.enablePrediction,
    cert_image: houseInfo.cert_image,
    // 传入上传后的 Base64 图片
    property_photos: fileList.value.map(item => item.url)
  }

  try {
    isLoading.value = true
    // 将数据存入 store 供 Step3 使用
    houseInfo.valuationData = valuationData
    // 立即跳转到结果页，由 Step3 负责发起请求
    router.push('/home/step3')
  } catch (error) {
    ElMessage.error('进入分析页面失败')
  } finally {
    isLoading.value = false
  }
}

const handleBeforeUpload = async (file) => {
  const isJPG = file.type === 'image/jpeg' || file.type === 'image/png'
  if (!isJPG) {
    ElMessage.error('仅支持上传 JPG 或 PNG 图片文件')
    return false
  }

  // Clear existing file (single file mode - replace instead of append)
  fileList.value = []

  let fileToProcess = file

  // Compress if larger than 18MB (to leave margin for base64 overhead)
  if (file.size > 18 * 1024 * 1024) {
    ElMessage.info('图片较大，正在压缩...')
    const compressed = await compressImageIfNeeded(file, 18432)
    if (!compressed) {
      ElMessage.error('图片压缩后仍超过20MB，请上传更小的图片')
      return false
    }
    fileToProcess = compressed
  }

  // Convert to Base64
  const reader = new FileReader()
  reader.readAsDataURL(fileToProcess)
  reader.onload = () => {
    fileList.value.push({
      name: file.name,
      url: reader.result,
      raw: fileToProcess,
      status: 'success',
      uid: Date.now() + Math.random()
    })
    ElMessage.success('图片读取成功')
  }
  reader.onerror = (error) => {
    console.error('Error: ', error)
    ElMessage.error('图片读取失败')
  }

  // 阻止默认上传动作
  return false
}

const handleRemove = (file) => {
  const index = fileList.value.findIndex(f => f.uid === file.uid || f === file)
  if (index !== -1) {
    fileList.value.splice(index, 1)
  }
}

const handlePictureCardPreview = (file) => {
  dialogImageUrl.value = file.url
  dialogVisible.value = true
}
</script>

<template>
  <div class="step-two-container">
    <!-- Header Section -->
    <div class="header-section">
      <h2 class="step-title">步骤 2: 上传房产外观环境照片</h2>
      <p class="step-description">提供房产的外观图片、周边配套或室内实拍图（可选）。丰富的视觉资料将通过多模态模型显著提高估值的准确度。</p>
    </div>

    <!-- Upload Card -->
    <el-card shadow="never" class="upload-container-card">
      <el-upload
        action="#"
        list-type="picture-card"
        v-model:file-list="fileList"
        :auto-upload="false"
        :on-remove="handleRemove"
        :on-change="(uploadFile) => { if (uploadFile && uploadFile.raw) handleBeforeUpload(uploadFile.raw) }"
        accept=".png,.jpg,.jpeg"
        class="multi-photo-uploader"
      >
        <template #default>
          <div class="upload-inner">
            <el-icon class="camera-icon"><camera-filled /></el-icon>
            <p class="upload-text">点击上传照片</p>
            <span class="upload-tip">支持 JPG / PNG</span>
          </div>
        </template>
        
        <template #file="{ file }">
          <div class="el-upload-list__item-thumbnail-wrapper">
            <img class="el-upload-list__item-thumbnail" :src="file.url" alt="" />
            <span class="el-upload-list__item-actions">
              <span
                class="el-upload-list__item-preview"
                @click="handlePictureCardPreview(file)"
              >
                <el-icon><zoom-in /></el-icon>
              </span>
              <span
                class="el-upload-list__item-delete"
                @click="handleRemove(file)"
              >
                <el-icon><delete /></el-icon>
              </span>
            </span>
          </div>
        </template>
      </el-upload>
      
      <div v-if="fileList.length > 0" class="uploaded-links-list">
        <div v-for="(file, index) in fileList" :key="file.uid" class="file-link-item">
          <el-link :href="file.url" target="_blank" type="primary">已提供图片 {{ index + 1 }}: {{ file.name }}</el-link>
        </div>
      </div>
      <p class="upload-hint-optional">* 照片为可选项，不上传也可直接开始估值</p>
    </el-card>

    <el-dialog v-model="dialogVisible">
      <img w-full :src="dialogImageUrl" alt="Preview Image" style="width: 100%" />
    </el-dialog>

    <!-- Footer Controls -->
    <div class="navigation-footer">
      <el-button size="large" @click="prevStep" :icon="ArrowLeft" plain round>
        返回上一步
      </el-button>

      <!-- LLM Prediction Toggle (Placed in middle) -->
      <div class="llm-toggle-footer">
        <el-icon class="magic-icon"><magic-stick /></el-icon>
        <span class="toggle-text">大模型预测微调</span>
        <el-switch
          v-model="houseInfo.enablePrediction"
          inline-prompt
          active-text="开"
          inactive-text="关"
        />
        <el-tooltip content="开启后将结合最新市场趋势数据通过大模型进行价格修正" placement="top">
          <el-icon class="info-icon"><info-filled /></el-icon>
        </el-tooltip>
      </div>

      <el-button type="success" size="large" @click="startAnalysis" :icon="Promotion" round shadow>
        开始估值分析
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.step-two-container {
  max-width: 900px;
  margin: 0 auto;
  animation: fadeSlideIn 0.5s ease-out;
}

@keyframes fadeSlideIn {
  from { opacity: 0; transform: translateY(18px); }
  to { opacity: 1; transform: translateY(0); }
}

.header-section {
  text-align: center;
  margin-bottom: 40px;
}

.step-title {
  font-size: 2rem;
  color: #2c3e50;
  margin-bottom: 12px;
  font-weight: 700;
}

.step-description {
  color: #7f8c8d;
  font-size: 1.1rem;
  max-width: 700px;
  margin: 0 auto;
  line-height: 1.7;
}

.upload-container-card {
  border-radius: 20px;
  padding: 50px 20px;
  text-align: center;
  border: 2px dashed #d0d7de;
  background: linear-gradient(135deg, #fafbfc 0%, #f0f4f8 100%);
  display: flex;
  justify-content: center;
  transition: all 0.3s ease;
}

.upload-container-card:hover {
  border-color: #409eff;
  background: linear-gradient(135deg, #f0f7ff 0%, #e8f4fd 100%);
  box-shadow: 0 4px 20px rgba(64,158,255,0.08);
}

.multi-photo-uploader :deep(.el-upload-list) {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
}

.uploaded-links-list {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  text-align: left;
}

.file-link-item {
  padding: 10px 16px;
  background: #fff;
  border-radius: 10px;
  border: 1px solid #ebeef5;
  transition: all 0.2s ease;
}

.file-link-item:hover {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64,158,255,0.1);
}

:deep(.el-upload-dragger) {
  padding: 40px 0;
  border: none;
  background: transparent;
}

:deep(.el-upload--picture-card) {
  width: 100%;
  height: 300px;
  border: none;
  background: transparent;
  border-radius: 16px;
  overflow: hidden;
}

:deep(.el-upload--picture-card .el-upload-list__item) {
  border-radius: 12px;
}

.camera-icon {
  font-size: 4.5rem;
  color: #409eff;
  margin-bottom: 20px;
  transition: transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.upload-container-card:hover .camera-icon {
  transform: scale(1.15) translateY(-4px);
}

.el-upload-list__item-thumbnail-wrapper {
  width: 100%;
  height: 100%;
  position: relative;
}

.el-upload-list__item-thumbnail {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.upload-text {
  font-size: 1.2rem;
  color: #606266;
  font-weight: 500;
  margin-bottom: 4px;
}

.upload-tip {
  color: #909399;
  font-size: 0.9rem;
}

/* Uploaded photo card styling */
:deep(.el-upload-list__item) {
  border-radius: 14px !important;
  overflow: hidden;
  border: 2px solid #e4e7ed !important;
  transition: all 0.3s ease;
}

:deep(.el-upload-list__item:hover) {
  border-color: #409eff !important;
  box-shadow: 0 4px 16px rgba(64, 158, 255, 0.15);
}

:deep(.el-upload-list__item-thumbnail) {
  object-fit: cover;
  border-radius: 12px;
}

:deep(.el-upload-list__item-actions) {
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(4px);
  opacity: 0;
  transition: opacity 0.3s ease;
}

:deep(.el-upload-list__item:hover .el-upload-list__item-actions) {
  opacity: 1;
}

:deep(.el-upload-list__item-actions span) {
  transition: transform 0.2s ease;
}

:deep(.el-upload-list__item-actions span:hover) {
  transform: scale(1.2);
}

.upload-hint-optional {
  color: #909399;
  font-size: 0.85rem;
  margin-top: 12px;
  font-style: italic;
}

.llm-toggle-footer {
  display: flex;
  align-items: center;
  gap: 12px;
  background: linear-gradient(135deg, #f0f7ff, #faf5ff);
  padding: 10px 24px;
  border-radius: 40px;
  border: 1px solid #d9ecff;
  box-shadow: 0 2px 8px rgba(64,158,255,0.06);
}

.toggle-text {
  font-size: 0.95rem;
  font-weight: 600;
  color: #606266;
}

.magic-icon {
  color: #409eff;
  font-size: 1.2rem;
}

.info-icon {
  color: #909399;
  cursor: help;
  font-size: 0.9rem;
  transition: color 0.2s;
}

.info-icon:hover {
  color: #409eff;
}

.navigation-footer {
  margin-top: 50px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.navigation-footer .el-button {
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.navigation-footer .el-button:hover {
  transform: translateY(-2px);
}

/* Responsive */
@media (max-width: 768px) {
  .step-title {
    font-size: 1.5rem;
  }
  .upload-container-card {
    padding: 30px 16px;
  }
  .navigation-footer {
    flex-direction: column;
    align-items: stretch;
  }
  .llm-toggle-footer {
    justify-content: center;
  }
  .camera-icon {
    font-size: 3rem;
  }
}
</style>
