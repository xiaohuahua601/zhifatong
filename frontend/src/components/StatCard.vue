<!-- ============================================================
 * 智法通 - 统计卡片组件
 * 功能：图标、数值（带动画计数）、标题、趋势指示、毛玻璃效果
 * ============================================================ -->
<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue'
import { TrendCharts, TopRight, BottomLeft } from '@element-plus/icons-vue'

/* ----------------------------------------------------------
 * Props 定义
 * ---------------------------------------------------------- */
const props = withDefaults(defineProps<{
  /** 卡片标题 */
  title: string
  /** 目标数值 */
  value: number
  /** 数值前缀（如 ¥、$） */
  prefix?: string
  /** 数值后缀（如 %、份） */
  suffix?: string
  /** 图标组件 */
  icon?: any
  /** 趋势方向：up上升 / down下降 / none无趋势 */
  trend?: 'up' | 'down' | 'none'
  /** 趋势百分比数值 */
  trendValue?: number
  /** 数值动画持续时间（毫秒） */
  duration?: number
  /** 图标背景色（CSS颜色值） */
  iconBgColor?: string
}>(), {
  prefix: '',
  suffix: '',
  icon: TrendCharts,
  trend: 'none',
  trendValue: 0,
  duration: 1500,
  iconBgColor: 'rgba(201, 169, 98, 0.15)',
})

/* ----------------------------------------------------------
 * 动画计数逻辑
 * 使用 requestAnimationFrame 实现数值从 0 递增到目标值
 * ---------------------------------------------------------- */
const displayValue = ref(0)

/** 缓动函数：easeOutExpo，让动画先快后慢更自然 */
const easeOutExpo = (t: number): number => {
  return t === 1 ? 1 : 1 - Math.pow(2, -10 * t)
}

/** 启动数值动画 */
const startAnimation = () => {
  const startTime = performance.now()
  const targetValue = props.value

  const animate = (currentTime: number) => {
    const elapsed = currentTime - startTime
    const progress = Math.min(elapsed / props.duration, 1)
    const easedProgress = easeOutExpo(progress)

    displayValue.value = Math.round(targetValue * easedProgress)

    if (progress < 1) {
      requestAnimationFrame(animate)
    }
  }

  requestAnimationFrame(animate)
}

/* ----------------------------------------------------------
 * 趋势相关计算
 * ---------------------------------------------------------- */
/** 趋势颜色 */
const trendColor = computed(() => {
  if (props.trend === 'up') return 'var(--color-success)'
  if (props.trend === 'down') return 'var(--color-danger)'
  return 'var(--color-text-tertiary)'
})

/** 趋势图标 */
const trendIcon = computed(() => {
  return props.trend === 'up' ? TopRight : BottomLeft
})

/** 格式化显示数值 */
const formattedValue = computed(() => {
  return displayValue.value.toLocaleString()
})

/* ----------------------------------------------------------
 * 生命周期
 * ---------------------------------------------------------- */
onMounted(() => {
  startAnimation()
})

/** 当目标值变化时重新启动动画 */
watch(() => props.value, () => {
  startAnimation()
})
</script>

<template>
  <div class="stat-card">
    <!-- 顶部：图标 + 趋势 -->
    <div class="stat-card-header">
      <div class="stat-icon" :style="{ background: iconBgColor }">
        <el-icon :size="22"><component :is="icon" /></el-icon>
      </div>
      <div
        v-if="trend !== 'none'"
        class="stat-trend"
        :style="{ color: trendColor }"
      >
        <el-icon :size="12"><component :is="trendIcon" /></el-icon>
        <span>{{ trendValue }}%</span>
      </div>
    </div>

    <!-- 数值区域 -->
    <div class="stat-value">
      <span class="stat-prefix" v-if="prefix">{{ prefix }}</span>
      <span class="stat-number">{{ formattedValue }}</span>
      <span class="stat-suffix" v-if="suffix">{{ suffix }}</span>
    </div>

    <!-- 标题 -->
    <div class="stat-title">{{ title }}</div>
  </div>
</template>

<style scoped>
/* 统计卡片 */
.stat-card {
  background: rgba(28, 35, 52, 0.8);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(148, 158, 178, 0.14);
  border-radius: 6px;
  padding: var(--spacing-xl);
  transition: all var(--transition-base);
  cursor: default;
  position: relative;
  overflow: hidden;
}

/* 悬浮效果：边框发光 + 阴影增强 */
.stat-card:hover {
  border-color: rgba(201, 169, 98, 0.3);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3), 0 0 20px rgba(201, 169, 98, 0.1);
  transform: translateY(-2px);
}

/* 卡片顶部光晕装饰 */
.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--color-brand-gold), transparent);
  opacity: 0;
  transition: opacity var(--transition-base);
}

.stat-card:hover::before {
  opacity: 0.6;
}

/* 顶部区域 */
.stat-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-base);
}

/* 图标容器 */
.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-brand-gold);
  transition: all var(--transition-base);
}

.stat-card:hover .stat-icon {
  transform: scale(1.05);
}

/* 趋势指示 */
.stat-trend {
  display: flex;
  align-items: center;
  gap: 2px;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  padding: 2px 8px;
  border-radius: var(--radius-circle);
  background: rgba(148, 158, 178, 0.08);
}

/* 数值区域 */
.stat-value {
  display: flex;
  align-items: baseline;
  gap: 2px;
  margin-bottom: var(--spacing-sm);
}

.stat-prefix {
  font-size: var(--font-size-lg);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
}

.stat-number {
  font-size: var(--font-size-4xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  line-height: 1;
  letter-spacing: -0.5px;
}

.stat-suffix {
  font-size: var(--font-size-md);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
  margin-left: 2px;
}

/* 标题 */
.stat-title {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  font-weight: var(--font-weight-medium);
}
</style>
