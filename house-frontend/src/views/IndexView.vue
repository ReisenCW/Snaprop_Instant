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
    desc: '利用 IMCA（智能化市场比较法）筛选海量相似成交案例，提供精准的市场价值评估。',
    icon: Cpu,
    color: '#67C23A'
  },
  {
    title: 'LLM 驱动的市场趋势分析',
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
      <div class="hero-bg-shapes">
        <div class="shape shape-1"></div>
        <div class="shape shape-2"></div>
        <div class="shape shape-3"></div>
      </div>
      <el-row justify="center" align="middle" class="hero-content">
        <el-col :xs="22" :sm="18" :md="14" :lg="12" class="text-center">
          <h1 class="brand-title">
            <div class="logo-wrapper">
              <img src="/assets/logo.png" alt="房估宝 Logo" class="hero-logo" />
            </div>
            AI 智能房产估值
          </h1>
          <div class="brand-subtitle">
            <p>基于多模态融合与大语言模型的智能房产估值系统</p>
            <p>为您提供专业的房产估值服务，2 分钟轻松生成评估报告</p>
          </div>
          <div class="action-buttons">
            <el-button type="primary" size="large" :icon="Promotion" @click="startValuation" round class="cta-btn">
              立即开启智能估值
            </el-button>
          </div>
          <div class="hero-hint">
            <span>无需下载 · 即开即用 · 完全免费</span>
          </div>
        </el-col>
      </el-row>
      <div class="hero-wave">
        <svg viewBox="0 0 1440 100" preserveAspectRatio="none">
          <path fill="#f0f2f5" d="M0,30 C240,80 480,0 720,30 C960,60 1200,10 1440,40 L1440,100 L0,100 Z" />
        </svg>
      </div>
    </header>

    <!-- Features Section -->
    <section class="features-section">
      <div class="section-wrapper">
        <div class="section-header">
          <h2 class="section-main-title">为什么选择房估宝？</h2>
          <p class="section-sub-title">三大核心技术，打造最精准的房产估值体验</p>
        </div>
        <el-row :gutter="32">
          <el-col v-for="(item, index) in features" :key="index" :xs="24" :sm="8">
            <el-card shadow="hover" class="feature-card" :style="{ '--card-delay': `${index * 0.15}s` }">
              <div class="card-header">
                <div class="icon-ring" :style="{ '--icon-color': item.color }">
                  <el-icon :size="36" :color="item.color">
                    <component :is="item.icon" />
                  </el-icon>
                </div>
                <span class="card-number">{{ String(index + 1).padStart(2, '0') }}</span>
                <h3 class="card-title">{{ item.title }}</h3>
              </div>
              <p class="card-desc">{{ item.desc }}</p>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </section>

    <!-- Bottom CTA Section -->
    <section class="cta-section">
      <div class="section-wrapper">
        <div class="cta-card">
          <h2 class="cta-title">准备好开始您的房产估值了吗？</h2>
          <p class="cta-desc">上传房产证照片，AI 自动识别信息，2 分钟内获取专业估值报告</p>
          <el-button type="primary" size="large" :icon="Promotion" @click="startValuation" round class="cta-bottom-btn">
            免费开始估值
          </el-button>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.index-container {
  min-height: 100vh;
  background-color: #f0f2f5;
  overflow: hidden;
}

/* ── Hero ── */
.hero-section {
  background: linear-gradient(135deg, #007bff 0%, #4b6cb7 50%, #6610f2 100%);
  color: white;
  padding: 110px 0 120px;
  text-align: center;
  position: relative;
  overflow: hidden;
}

.hero-bg-shapes {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.shape {
  position: absolute;
  border-radius: 50%;
  opacity: 0.08;
  background: white;
}

.shape-1 {
  width: 400px;
  height: 400px;
  top: -100px;
  right: -100px;
  animation: float 8s ease-in-out infinite;
}

.shape-2 {
  width: 200px;
  height: 200px;
  bottom: 60px;
  left: 10%;
  animation: float 6s ease-in-out infinite reverse;
}

.shape-3 {
  width: 300px;
  height: 300px;
  top: 50%;
  left: 50%;
  animation: float 10s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) rotate(0deg); }
  50% { transform: translate(30px, -20px) rotate(10deg); }
}

.hero-content {
  position: relative;
  z-index: 2;
}

.hero-badge {
  display: flex;
  gap: 10px;
  justify-content: center;
  margin-bottom: 28px;
}

.brand-title {
  font-size: 4.2rem;
  font-weight: 800;
  margin-bottom: 24px;
  letter-spacing: 3px;
  text-shadow: 0 4px 16px rgba(0,0,0,0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  animation: fadeInDown 0.8s ease-out;
}

.logo-wrapper {
  background-color: white;
  border-radius: 20px;
  padding: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 20px rgba(0,0,0,0.15);
  height: 4.5rem;
  width: 4.5rem;
  transition: transform 0.3s ease;
}

.logo-wrapper:hover {
  transform: scale(1.08) rotate(-3deg);
}

.hero-logo {
  height: 100%;
  width: auto;
  object-fit: contain;
}

.brand-subtitle {
  font-size: 1.5rem;
  opacity: 0.92;
  margin-bottom: 40px;
  line-height: 1.8;
  font-weight: 300;
  animation: fadeInDown 0.8s ease-out 0.15s both;
}

.brand-subtitle p {
  margin: 4px 0;
}

.action-buttons {
  animation: fadeInDown 0.8s ease-out 0.3s both;
}

.cta-btn {
  padding: 28px 60px !important;
  font-size: 1.3rem !important;
  transition: all 0.3s;
  box-shadow: 0 6px 24px rgba(0,0,0,0.18);
}

.cta-btn:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 32px rgba(0,0,0,0.25);
}

.hero-hint {
  margin-top: 24px;
  font-size: 0.95rem;
  animation: fadeInDown 0.8s ease-out 0.45s both;
}

.hero-hint span {
  display: inline-block;
  background: rgba(0, 0, 0, 0.2);
  backdrop-filter: blur(8px);
  padding: 8px 28px;
  border-radius: 20px;
  color: #fff;
  font-weight: 500;
  letter-spacing: 1px;
}

.hero-wave {
  position: absolute;
  bottom: -1px;
  left: 0;
  right: 0;
  height: 80px;
  overflow: hidden;
  z-index: 1;
}

.hero-wave svg {
  width: 100%;
  height: 100%;
}

@keyframes fadeInDown {
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ── Features ── */
.features-section {
  padding: 100px 0 60px;
}

.section-wrapper {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 30px;
}

.section-header {
  text-align: center;
  margin-bottom: 56px;
}

.section-main-title {
  font-size: 2.2rem;
  font-weight: 700;
  color: #2c3e50;
  margin: 0 0 12px;
}

.section-sub-title {
  color: #909399;
  font-size: 1.1rem;
  margin: 0;
}

.feature-card {
  border: none;
  border-radius: 20px;
  transition: all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  height: 100%;
  animation: cardReveal 0.6s ease-out var(--card-delay, 0s) both;
  overflow: hidden;
}

.feature-card:hover {
  transform: translateY(-14px);
  box-shadow: 0 16px 40px rgba(0,0,0,0.1) !important;
}

.feature-card:hover .icon-ring {
  transform: scale(1.12);
  box-shadow: 0 0 0 8px rgba(64, 158, 255, 0.15);
  box-shadow: 0 0 0 8px color-mix(in srgb, var(--icon-color) 15%, transparent);
}

@keyframes cardReveal {
  from { opacity: 0; transform: translateY(40px); }
  to { opacity: 1; transform: translateY(0); }
}

.card-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.icon-ring {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: rgba(64, 158, 255, 0.08);
  background: color-mix(in srgb, var(--icon-color) 8%, transparent);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.4s ease;
  box-shadow: 0 0 0 4px rgba(64, 158, 255, 0.08);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--icon-color) 8%, transparent);
}

.card-number {
  position: absolute;
  top: 16px;
  right: 20px;
  font-size: 2.5rem;
  font-weight: 900;
  color: #f0f2f5;
  pointer-events: none;
}

.card-title {
  margin: 0;
  font-size: 1.35rem;
  color: #2c3e50;
  font-weight: 600;
}

.card-desc {
  color: #7f8c8d;
  line-height: 1.8;
  text-align: center;
  font-size: 1.02rem;
}

/* ── CTA ── */
.cta-section {
  padding: 80px 0 100px;
}

.cta-card {
  background: linear-gradient(135deg, #007bff 0%, #6610f2 100%);
  color: white;
  text-align: center;
  padding: 60px 40px;
  border-radius: 24px;
  box-shadow: 0 12px 40px rgba(0, 123, 255, 0.3);
  position: relative;
  overflow: hidden;
}

.cta-card::before {
  content: '';
  position: absolute;
  width: 300px;
  height: 300px;
  background: rgba(255,255,255,0.05);
  border-radius: 50%;
  top: -80px;
  right: -60px;
}

.cta-card::after {
  content: '';
  position: absolute;
  width: 200px;
  height: 200px;
  background: rgba(255,255,255,0.05);
  border-radius: 50%;
  bottom: -50px;
  left: -40px;
}

.cta-title {
  font-size: 2rem;
  font-weight: 700;
  margin: 0 0 16px;
  position: relative;
  z-index: 1;
}

.cta-desc {
  font-size: 1.15rem;
  opacity: 0.9;
  margin: 0 0 32px;
  position: relative;
  z-index: 1;
}

.cta-bottom-btn {
  padding: 18px 48px !important;
  font-size: 1.2rem !important;
  position: relative;
  z-index: 1;
  background: white !important;
  color: #007bff !important;
  border: none !important;
  box-shadow: 0 4px 16px rgba(0,0,0,0.15);
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.cta-bottom-btn:hover {
  transform: translateY(-4px) scale(1.04);
  box-shadow: 0 8px 24px rgba(0,0,0,0.2);
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .brand-title {
    font-size: 2.4rem;
    flex-direction: column;
    gap: 12px;
  }
  .brand-subtitle {
    font-size: 1.15rem;
  }
  .hero-section {
    padding: 80px 0 90px;
  }
  .cta-btn {
    padding: 20px 40px !important;
    font-size: 1.1rem !important;
  }
  .section-main-title {
    font-size: 1.7rem;
  }
  .stat-number {
    font-size: 2.2rem;
  }
  .feature-card {
    margin-bottom: 16px;
  }
  .cta-title {
    font-size: 1.5rem;
  }
}
</style>
