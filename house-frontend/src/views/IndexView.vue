<script setup>
import { useRouter } from 'vue-router'
import { Monitor, Cpu, TrendCharts, Promotion } from '@element-plus/icons-vue'

const router = useRouter()

const startValuation = () => {
  router.push('/home')
}

const features = [
  {
    title: '多模态视觉融合',
    desc: '集成 OCR 识别、多模态语义分析与地理空间数据，全方位还原房产价值。',
    icon: Monitor,
    color: '#409EFF'
  },
  {
    title: '专业评估方法',
    desc: '利用IMCA(智能化市场比较法)筛选海量相似成交案例，提供精准的市场价值评估。',
    icon: Cpu,
    color: '#67C23A'
  },
  {
    title: 'LLM驱动的市场趋势分析',
    desc: '利用尖端大语言模型实时分析市场趋势，微调评估价格，提供最具参考性的预测深度。',
    icon: TrendCharts,
    color: '#E6A23C'
  }
]
</script>

<template>
  <div class="index-container">
    <!-- Hero Section -->
    <header class="hero-section">
      <el-row justify="center" align="middle" class="hero-content">
        <el-col :xs="22" :sm="18" :md="14" :lg="12" class="text-center">
          <h1 class="brand-title">
            <div class="logo-wrapper">
              <img src="/assets/logo.png" alt="房估宝 Logo" class="hero-logo" />
            </div>
            AI智能房产估值
          </h1>
          <div class="brand-subtitle">
            <p>基于多模态融合与大语言模型的智能房产估值系统</p>
            <p>为您提供专业的房产估值服务，2分钟轻松生成评估报告</p>
          </div>
          <div class="action-buttons">
            <el-button type="primary" size="large" :icon="Promotion" @click="startValuation" round>
              立即开启智能估值
            </el-button>
          </div>
        </el-col>
      </el-row>
    </header>

    <!-- Features Section -->
    <section class="features-section">
      <div class="section-wrapper">
        <el-row :gutter="40">
          <el-col v-for="(item, index) in features" :key="index" :xs="24" :sm="8">
            <el-card shadow="hover" class="feature-card">
              <div class="card-header">
                <el-icon :size="48" :color="item.color">
                  <component :is="item.icon" />
                </el-icon>
                <h3 class="card-title">{{ item.title }}</h3>
              </div>
              <p class="card-desc">{{ item.desc }}</p>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </section>

    
  </div>
</template>

<style scoped>
.index-container {
  min-height: 100vh;
  background-color: #f5f7fa;
}

.hero-section {
  background: linear-gradient(135deg, #61abff 0%, #007bff 100%);
  color: white;
  padding: 120px 0;
  text-align: center;
}

.brand-title {
  font-size: 4.5rem;
  font-weight: 800;
  margin-bottom: 24px;
  letter-spacing: 4px;
  text-shadow: 0 4px 12px rgba(0,0,0,0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
}

.logo-wrapper {
  background-color: white;
  border-radius: 20px;
  padding: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 15px rgba(0,0,0,0.1);
  height: 4.5rem; /* 与文字对齐 */
  width: 4.5rem;
}

.hero-logo {
  height: 100%;
  width: auto;
  object-fit: contain;
}

.brand-subtitle {
  font-size: 1.6rem;
  opacity: 0.9;
  margin-bottom: 48px;
  line-height: 1.8;
  font-weight: 300;
}

.action-buttons .el-button {
  padding: 28px 60px;
  font-size: 1.3rem;
  transition: all 0.3s;
  box-shadow: 0 6px 20px rgba(0,0,0,0.15);
}

.action-buttons .el-button:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 25px rgba(0,0,0,0.2);
}

.features-section {
  padding: 100px 0;
}

.section-wrapper {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 30px;
}

.feature-card {
  border: none;
  border-radius: 16px;
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  height: 100%;
}

.feature-card:hover {
  transform: translateY(-12px);
  box-shadow: 0 12px 30px rgba(0,0,0,0.1) !important;
}

.card-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  margin-bottom: 20px;
}

.card-title {
  margin: 0;
  font-size: 1.4rem;
  color: #2c3e50;
  font-weight: 600;
}

.card-desc {
  color: #7f8c8d;
  line-height: 1.8;
  text-align: center;
  font-size: 1.05rem;
}

.stats-section {
  padding: 80px 0;
  background-color: white;
  border-top: 1px solid #ebeef5;
}

.stats-row {
  max-width: 1100px;
  margin: 0 auto;
}

@media (max-width: 768px) {
  .brand-title {
    font-size: 2.8rem;
  }
  .brand-subtitle {
    font-size: 1.2rem;
  }
  .hero-section {
    padding: 80px 0;
  }
}
</style>
