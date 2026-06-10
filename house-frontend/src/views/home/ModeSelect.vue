<script setup>
import { useRouter } from 'vue-router'
import { House, Collection } from '@element-plus/icons-vue'

const router = useRouter()

const goSingle = () => {
  router.push('/home/step1')
}

const goBatch = () => {
  router.push('/home/batch')
}
</script>

<template>
  <div class="mode-select-container">
    <h1 class="mode-title">选择估值模式</h1>
    <p class="mode-subtitle">根据您的需求选择合适的估值方式</p>

    <div class="mode-cards">
      <!-- Single Property -->
      <div class="mode-card single-card" @click="goSingle">
        <div class="card-icon-wrap single-icon">
          <el-icon :size="48"><House /></el-icon>
        </div>
        <h2 class="card-title">单房产估值</h2>
        <p class="card-desc">
          上传一份房产证，系统自动识别关键信息，结合市场数据与AI分析，
          生成专业的房产估值报告。适合个人房东、购房者快速了解房产价值。
        </p>
        <ul class="card-features">
          <li>OCR 智能识别产证信息</li>
          <li>IMCA 市场比较法精准估值</li>
          <li>AI 大模型趋势预测微调</li>
          <li>专业 PDF 报告一键导出</li>
        </ul>
        <el-button type="primary" size="large" round class="card-btn">
          开始单房产估值
        </el-button>
      </div>

      <!-- Batch Property -->
      <div class="mode-card batch-card" @click="goBatch">
        <div class="card-icon-wrap batch-icon">
          <el-icon :size="48"><Collection /></el-icon>
        </div>
        <h2 class="card-title">批量估值</h2>
        <p class="card-desc">
          一次上传多份房产证，系统自动批量处理，快速生成多房源对比分析。
          适合中介机构、房产平台批量评估多套房源价值。
        </p>
        <ul class="card-features">
          <li>支持最多 10 张产证同时上传</li>
          <li>自动逐套识别与估值</li>
          <li>多房源横向对比分析</li>
          <li>对比结果导出 Excel</li>
        </ul>
        <el-button type="success" size="large" round class="card-btn">
          开始批量估值
        </el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.mode-select-container {
  max-width: 960px;
  margin: 0 auto;
  padding: 40px 20px;
  text-align: center;
  animation: fadeSlideIn 0.5s ease-out;
}

@keyframes fadeSlideIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.mode-title {
  font-size: 2rem;
  font-weight: 800;
  color: #2c3e50;
  margin: 0 0 8px;
}

.mode-subtitle {
  font-size: 1.05rem;
  color: #909399;
  margin: 0 0 40px;
}

.mode-cards {
  display: flex;
  gap: 32px;
  justify-content: center;
}

.mode-card {
  flex: 1;
  max-width: 440px;
  background: white;
  border-radius: 20px;
  padding: 40px 32px 32px;
  text-align: center;
  cursor: pointer;
  transition: all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
  box-shadow: 0 4px 24px rgba(0,0,0,0.06);
  border: 2px solid transparent;
  position: relative;
  overflow: hidden;
}

.mode-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  transition: height 0.3s ease;
}

.single-card::before {
  background: linear-gradient(90deg, #409eff, #6610f2);
}

.batch-card::before {
  background: linear-gradient(90deg, #67c23a, #409eff);
}

.mode-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 12px 40px rgba(0,0,0,0.12);
}

.single-card:hover {
  border-color: #409eff;
}

.batch-card:hover {
  border-color: #67c23a;
}

.card-icon-wrap {
  width: 96px;
  height: 96px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px;
  transition: transform 0.3s ease;
}

.mode-card:hover .card-icon-wrap {
  transform: scale(1.1);
}

.single-icon {
  background: linear-gradient(135deg, #e8f4fd, #f0e6ff);
  color: #409eff;
}

.batch-icon {
  background: linear-gradient(135deg, #e8f8e0, #e8f4fd);
  color: #67c23a;
}

.card-title {
  font-size: 1.4rem;
  font-weight: 700;
  color: #303133;
  margin: 0 0 12px;
}

.card-desc {
  font-size: 0.95rem;
  color: #606266;
  line-height: 1.7;
  margin: 0 0 20px;
  text-align: left;
}

.card-features {
  list-style: none;
  padding: 0;
  margin: 0 0 28px;
  text-align: left;
}

.card-features li {
  position: relative;
  padding: 6px 0 6px 24px;
  font-size: 0.9rem;
  color: #606266;
}

.card-features li::before {
  content: '✓';
  position: absolute;
  left: 0;
  color: #67c23a;
  font-weight: 700;
}

.single-card .card-features li::before {
  color: #409eff;
}

.batch-card .card-features li::before {
  color: #67c23a;
}

.card-btn {
  width: 100%;
  font-weight: 600;
}

/* Responsive */
@media (max-width: 768px) {
  .mode-cards {
    flex-direction: column;
    align-items: center;
    gap: 24px;
  }
  .mode-card {
    max-width: 100%;
    padding: 32px 24px 24px;
  }
  .mode-title {
    font-size: 1.6rem;
  }
  .mode-select-container {
    padding: 24px 16px;
  }
}

@media (max-width: 480px) {
  .mode-select-container {
    padding: 16px 10px;
  }
  .mode-title {
    font-size: 1.4rem;
  }
  .mode-subtitle {
    font-size: 0.9rem;
    margin-bottom: 24px;
  }
  .mode-card {
    padding: 24px 16px 20px;
    border-radius: 16px;
  }
  .card-icon-wrap {
    width: 72px;
    height: 72px;
  }
  .card-title {
    font-size: 1.2rem;
  }
  .card-desc {
    font-size: 0.85rem;
  }
  .card-features li {
    font-size: 0.82rem;
  }
}
</style>
