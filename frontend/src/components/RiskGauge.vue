<!-- ============================================================
 * 智法通 - 风险评分仪表盘组件
 * 功能：半圆形仪表盘（SVG绘制）、颜色渐变（绿→黄→红）、
 *       分数显示、风险等级文字
 * ============================================================ -->
<script setup lang="ts">
import { computed, ref, watch, onMounted } from 'vue'

/* ----------------------------------------------------------
 * Props 定义
 * ---------------------------------------------------------- */
const props = withDefaults(defineProps<{
  /** 风险分数（0-100） */
  score: number
  /** 仪表盘尺寸（像素） */
  size?: number
  /** 是否显示动画 */
  animated?: boolean
  /** 标题文字 */
  title?: string
}>(), {
  size: 200,
  animated: true,
  title: '风险评分',
})

/* ----------------------------------------------------------
 * 仪表盘参数
 * ---------------------------------------------------------- */
/** 圆弧半径 */
const radius = computed(() => props.size * 0.38)
/** 圆弧中心坐标 */
const cx = computed(() => props.size / 2)
const cy = computed(() => props.size / 2 + 10)
/** 线宽 */
const strokeWidth = computed(() => props.size * 0.08)
/** 半圆弧周长（180度） */
const semiCircumference = computed(() => Math.PI * radius.value)

/* ----------------------------------------------------------
 * 动画逻辑
 * ---------------------------------------------------------- */
const animatedScore = ref(0)
const animationDuration = 1200

/** 缓动函数 */
const easeOutCubic = (t: number): number => 1 - Math.pow(1 - t, 3)

/** 启动动画 */
const startAnimation = () => {
  if (!props.animated) {
    animatedScore.value = props.score
    return
  }
  const startTime = performance.now()
  const startValue = animatedScore.value
  const targetValue = props.score

  const animate = (currentTime: number) => {
    const elapsed = currentTime - startTime
    const progress = Math.min(elapsed / animationDuration, 1)
    const easedProgress = easeOutCubic(progress)
    animatedScore.value = Math.round(startValue + (targetValue - startValue) * easedProgress)

    if (progress < 1) {
      requestAnimationFrame(animate)
    }
  }

  requestAnimationFrame(animate)
}

/* ----------------------------------------------------------
 * 风险等级计算
 * ---------------------------------------------------------- */
/** 风险等级文字 */
const riskLevel = computed(() => {
  if (animatedScore.value <= 30) return '低风险'
  if (animatedScore.value <= 60) return '中风险'
  if (animatedScore.value <= 80) return '较高风险'
  return '高风险'
})

/** 风险等级颜色 */
const riskColor = computed(() => {
  if (animatedScore.value <= 30) return '#7ca586'
  if (animatedScore.value <= 60) return '#c9973f'
  if (animatedScore.value <= 80) return '#c05b52'
  return '#a04a43'
})

/** 风险等级CSS类名 */
const riskClass = computed(() => {
  if (animatedScore.value <= 30) return 'risk-low'
  if (animatedScore.value <= 60) return 'risk-medium'
  if (animatedScore.value <= 80) return 'risk-high'
  return 'risk-critical'
})

/* ----------------------------------------------------------
 * SVG 路径计算
 * ---------------------------------------------------------- */
/** 背景弧线（灰色半圆） */
const backgroundArc = computed(() => {
  const r = radius.value
  const x = cx.value
  const y = cy.value
  return `M ${x - r} ${y} A ${r} ${r} 0 0 1 ${x + r} ${y}`
})

/** 前景弧线（渐变色，根据分数显示） */
const foregroundArc = computed(() => {
  const r = radius.value
  const x = cx.value
  const y = cy.value
  // 根据分数计算弧线终点角度
  const angle = (animatedScore.value / 100) * Math.PI
  const endX = x + r * Math.cos(Math.PI - angle)
  const endY = y - r * Math.sin(angle)

  // 当分数为0时不绘制
  if (animatedScore.value === 0) return ''

  // 当分数为100时绘制完整半圆
  if (animatedScore.value >= 100) {
    return `M ${x - r} ${y} A ${r} ${r} 0 0 1 ${x + r} ${y}`
  }

  return `M ${x - r} ${y} A ${r} ${r} 0 ${animatedScore.value > 50 ? 1 : 0} 1 ${endX} ${endY}`
})

/** 渐变色ID（避免多实例冲突） */
const gradientId = computed(() => `riskGradient-${Math.random().toString(36).slice(2, 8)}`)

/* ----------------------------------------------------------
 * 生命周期
 * ---------------------------------------------------------- */
onMounted(() => {
  startAnimation()
})

watch(() => props.score, () => {
  startAnimation()
})
</script>

<template>
  <div class="risk-gauge-container" :class="riskClass">
    <!-- 标题 -->
    <div class="gauge-title" v-if="title">{{ title }}</div>

    <!-- SVG 仪表盘 -->
    <svg
      :width="size"
      :height="size * 0.6"
      :viewBox="`0 0 ${size} ${size * 0.6}`"
      class="gauge-svg"
    >
      <defs>
        <!-- 渐变色定义：绿→黄→红 -->
        <linearGradient :id="gradientId" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="#7ca586" />
          <stop offset="40%" stop-color="#c9973f" />
          <stop offset="70%" stop-color="#c05b52" />
          <stop offset="100%" stop-color="#a04a43" />
        </linearGradient>
      </defs>

      <!-- 背景弧线 -->
      <path
        :d="backgroundArc"
        fill="none"
        stroke="rgba(148, 158, 178, 0.14)"
        :stroke-width="strokeWidth"
        stroke-linecap="round"
      />

      <!-- 前景弧线（渐变色） -->
      <path
        :d="foregroundArc"
        fill="none"
        :stroke="`url(#${gradientId})`"
        :stroke-width="strokeWidth"
        stroke-linecap="round"
        class="gauge-arc"
      />

      <!-- 分数文字 -->
      <text
        :x="cx"
        :y="cy - 8"
        text-anchor="middle"
        dominant-baseline="middle"
        class="gauge-score"
        :fill="riskColor"
      >
        {{ animatedScore }}
      </text>

      <!-- 风险等级文字 -->
      <text
        :x="cx"
        :y="cy + 16"
        text-anchor="middle"
        dominant-baseline="middle"
        class="gauge-level"
        :fill="riskColor"
      >
        {{ riskLevel }}
      </text>
    </svg>

    <!-- 底部刻度标注 -->
    <div class="gauge-scale">
      <span class="scale-label scale-low">0</span>
      <span class="scale-label scale-mid">50</span>
      <span class="scale-label scale-high">100</span>
    </div>
  </div>
</template>

<style scoped>
/* 仪表盘容器 */
.risk-gauge-container {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(148, 158, 178, 0.14);
  border-radius: 6px;
  padding: var(--spacing-xl);
  display: flex;
  flex-direction: column;
  align-items: center;
  transition: all var(--transition-base);
}

.risk-gauge-container:hover {
  border-color: rgba(148, 158, 178, 0.24);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3);
}

/* 标题 */
.gauge-title {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
  margin-bottom: var(--spacing-md);
}

/* SVG */
.gauge-svg {
  display: block;
  overflow: visible;
}

/* 弧线动画 */
.gauge-arc {
  transition: d 0.8s ease;
}

/* 分数文字 */
.gauge-score {
  font-size: 36px;
  font-weight: 700;
  font-family: var(--font-family);
}

/* 风险等级文字 */
.gauge-level {
  font-size: 14px;
  font-weight: 500;
  font-family: var(--font-family);
}

/* 底部刻度 */
.gauge-scale {
  display: flex;
  justify-content: space-between;
  width: 80%;
  margin-top: var(--spacing-xs);
}

.scale-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.scale-low { color: #7ca586; }
.scale-mid { color: #c9973f; }
.scale-high { color: #c05b52; }

/* 风险等级边框高亮 */
.risk-critical {
  border-color: rgba(160, 74, 67, 0.32) !important;
}

.risk-high {
  border-color: rgba(192, 91, 82, 0.25) !important;
}

.risk-medium {
  border-color: rgba(201, 151, 63, 0.25) !important;
}

.risk-low {
  border-color: rgba(124, 165, 134, 0.25) !important;
}
</style>
