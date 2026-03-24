<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const activeStep = computed(() => {
  if (route.path.includes('step1')) return 0
  if (route.path.includes('step2')) return 1
  if (route.path.includes('step3')) return 2
  return 0
})
</script>

<template>
  <div class="home-layout">
    <!-- Progress Header -->
    <div class="stepper-card">
      <el-steps :active="activeStep" finish-status="success" align-center>
        <el-step title="步骤 1" description="房产基本信息" />
        <el-step title="步骤 2" description="房产外观环境" />
        <el-step title="步骤 3" description="智能估值报告" />
      </el-steps>
    </div>

    <!-- Main Step Content -->
    <div class="step-view-container">
      <router-view :key="$route.fullPath" />
    </div>
  </div>
</template>

<style scoped>
.home-layout {
  padding: 30px 40px;
  max-width: 1200px;
  margin: 0 auto;
  background-color: #f5f7fa;
  min-height: calc(100vh - 120px);
}

.stepper-card {
  background: white;
  padding: 30px;
  border-radius: 16px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.05);
  margin-bottom: 40px;
}

.step-view-container {
  position: relative;
}

/* Page Transition */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.3s ease;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

:deep(.el-step__title) {
  font-weight: 600;
}
</style>