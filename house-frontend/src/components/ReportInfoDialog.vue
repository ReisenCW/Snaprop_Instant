<script setup>
import { ref, reactive } from 'vue'
import { Plus, MagicStick } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import { API_BASE_URL } from '@/config'

const props = defineProps({
  visible: Boolean,
  initialData: Object
})

const emit = defineEmits(['update:visible', 'confirm'])

const formData = reactive({
  clientName: '敬启者',
  reportLogo: '',
  surrounding: '',
  traffic: '',
  propertyOverview: '',
  occupancy: ''
})

const isAutoFilling = ref(false)
const reportCache = new Map() // Cache for storing form data by report_id

// Initialize with any provided data
const init = () => {
  if (props.initialData) {
    const { report_id, city = '上海', address = '', house_type = '', area = '' } = props.initialData
    
    // Save current form data before switching if we have a previous report_id
    if (report_id) {
       if (reportCache.has(report_id)) {
           // Load from cache
           const cached = reportCache.get(report_id)
           Object.assign(formData, cached)
       } else {
           // Reset and init default
           formData.clientName = '敬启者'
           formData.reportLogo = ''
           formData.surrounding = ''
           formData.traffic = ''
           formData.propertyOverview = `该物业坐落于${city}${address}，房屋类型为${house_type}，建筑面积${area}平方米。房屋维护状况良好，配套设施完善。`
           formData.occupancy = '目前该物业处于自用状态，空置时间较短，室内维护保养较好。'
       }
    }
  }
}

const handleClose = () => {
  // Save to cache on close
  if (props.initialData && props.initialData.report_id) {
      reportCache.set(props.initialData.report_id, { ...formData })
  }
  emit('update:visible', false)
}

const handleConfirm = () => {
  if (!formData.clientName || !formData.surrounding || !formData.traffic || !formData.propertyOverview || !formData.occupancy) {
    ElMessage.warning('请填写所有带星号的必填项')
    return
  }
  // Save to cache on confirm
  if (props.initialData && props.initialData.report_id) {
      reportCache.set(props.initialData.report_id, { ...formData })
  }
  emit('confirm', { ...formData })
}

const autoFill = async () => {
  if (!props.initialData?.address) {
    ElMessage.error('缺少房产地址信息，无法自动生成')
    return
  }
  
  try {
    isAutoFilling.value = true
    const res = await axios.post(`${API_BASE_URL}/api/generate_report_content`, {
      city: props.initialData.city || '上海',
      address: props.initialData.address,
      house_type: props.initialData.house_type,
      area: props.initialData.area
    })
    
    if (res.data && res.data.success) {
      formData.surrounding = res.data.data.surrounding || formData.surrounding
      formData.traffic = res.data.data.traffic || formData.traffic
      
      const { city = '上海', address = '', house_type = '', area = '' } = props.initialData
      const overviewTpl = `该物业坐落于${city}${address}，房屋类型为${house_type}，建筑面积${area}平方米。房屋维护状况良好，配套设施完善。`
      const occupancyTpl = '目前该物业处于自用状态，空置时间较短，室内维护保养较好。'
      
      formData.propertyOverview = overviewTpl
      formData.occupancy = occupancyTpl
      
      ElMessage.success('已应用 AI 自动生成的内容')
    } else {
      throw new Error(res.data?.error || '生成失败')
    }
  } catch (error) {
    ElMessage.error(`自动生成失败: ${error.message}`)
  } finally {
    isAutoFilling.value = false
  }
}

const handleAvatarSuccess = (response) => {
  // 假设后端返回 { success: true, url: '/static/uploads/...' }
  if (response.success || response.url) {
    formData.reportLogo = response.url // 修复：后端可能直接返回 {url: ...} 或者 {success:true, url: ...}
    ElMessage.success('Logo 上传成功')
  } else {
    ElMessage.error(response.error || '上传失败')
  }
}

const beforeAvatarUpload = (rawFile) => {
  if (rawFile.type !== 'image/jpeg' && rawFile.type !== 'image/png') {
    ElMessage.error('Logo 必须是 JPG 或 PNG 格式!')
    return false
  } else if (rawFile.size / 1024 / 1024 > 20) {
    ElMessage.error('Logo 大小不能超过 20MB!')
    return false
  }
  return true
}
</script>

<template>
  <el-dialog
    :model-value="visible"
    title="完善报告信息"
    width="600px"
    @close="handleClose"
    @open="init"
    class="report-info-dialog"
  >
    <el-form :model="formData" label-position="top">
      <el-form-item label="敬启者（委托人） *" required>
        <el-input v-model="formData.clientName" placeholder="请输入委托人姓名" />
      </el-form-item>
      
      <el-form-item label="报告 Logo (可选)">
        <div class="logo-upload-container">
          <el-input v-model="formData.reportLogo" placeholder="请输入 Logo 图片 URL" />
          <el-upload
            class="avatar-uploader"
            :action="`${API_BASE_URL}/api/upload/logo`"
            :show-file-list="false"
            :on-success="handleAvatarSuccess"
            :before-upload="beforeAvatarUpload"
            name="file"
          >
            <el-button type="primary" :icon="Plus" plain>上传图片</el-button>
          </el-upload>
        </div>
        <div v-if="formData.reportLogo" class="logo-preview">
           <img :src="formData.reportLogo.startsWith('http') ? formData.reportLogo : `${API_BASE_URL}${formData.reportLogo}`" />
        </div>
      </el-form-item>

      <div class="divider">
        <span>报告正文内容</span>
        <el-button 
          type="primary" 
          link 
          :icon="MagicStick" 
          :loading="isAutoFilling"
          @click="autoFill"
        >
          一键 AI 生成默认内容
        </el-button>
      </div>

      <el-form-item label="临近环境及建筑物 *" required>
        <el-input 
          v-model="formData.surrounding" 
          type="textarea" 
          :rows="3" 
          placeholder="例如：位于XX商圈，周边有XX学校、医院..." 
        />
      </el-form-item>

      <el-form-item label="交通条件 *" required>
        <el-input 
          v-model="formData.traffic" 
          type="textarea" 
          :rows="3" 
          placeholder="例如：距离地铁X号线XX站约500米，公交线路众多..." 
        />
      </el-form-item>

      <el-form-item label="物业概况 *" required>
        <el-input 
          v-model="formData.propertyOverview" 
          type="textarea" 
          :rows="3" 
          placeholder="例如：建筑面积XX平米，XX室XX厅，南北通透..." 
        />
      </el-form-item>
      
      <el-form-item label="占用概况 *" required>
        <el-input 
          v-model="formData.occupancy" 
          type="textarea" 
          :rows="2" 
          placeholder="例如：目前由业主自住，保养状况良好。" 
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" @click="handleConfirm">
          生成 PDF 报告
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<style scoped>
.divider {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 20px 0 10px;
  border-bottom: 1px solid #ebeef5;
  padding-bottom: 5px;
}
.divider span {
  font-weight: bold;
  font-size: 14px;
  color: #606266;
}

.logo-upload-container {
  display: flex;
  gap: 10px;
}

.logo-preview {
  margin-top: 10px;
  border: 1px solid #dcdfe6;
  padding: 4px;
  border-radius: 4px;
  display: inline-block;
}
.logo-preview img {
  max-height: 60px;
  max-width: 200px;
  object-fit: contain;
}
</style>