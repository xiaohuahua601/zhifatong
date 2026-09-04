<!-- ============================================================
 * 智法通 - 置信度进度条组件
 * 功能：渐变色条、百分比显示、低置信度警告
 * ============================================================ -->
<script setup lang="ts">
import { computed } from 'vue'
import { WarningFilled } from '@element-plus/icons-vue'

/* ----------------------------------------------------------
 * Props 定义
 * ---------------------------------------------------------- */
const props = withDefaults(defineProps<{
  /** 置信度值（0-100） */
  value: number
  /** 低置信度阈值（低于此值显示警告） */
  warningThreshold?: number
  /** 是否显示百分比文字 */
  showPercent?: boolean
  /** 进度条高度（像素） */
  barHeight?: number
  /** 标签文字 */
  label?: string
}>(), {
  warningThreshold: 50,
  showPercent: true,
  barHeight: 6,
  label: '置信度',
})

/* ----------------------------------------------------------
 * 计算属性
 * ---------------------------------------------------------- */
/** 是否为低置信度 */
const isLowConfidence = computed(() => props.value < props.warningThreshold)

/** 进度条渐变色：根据置信度值从红到绿渐变 */
const barGradient = computed(() => {
  if (props.value >= 80) {
    return 'linear-gradient(90deg, #7ca586, #8fb398)'
  } else if (props.value >= 60) {
    return 'linear-gradient(90deg, #c9973f, #d3a75c)'
  } else if (props.value >= 40) {
    return 'linear-gradient(90deg, #c05b52, #cb736b)'
  } else {
    return 'linear-gradient(90deg, #a04a43, #c05b52)'
  }
})

/** 置信度文字颜色 */
const textColor = computed(() => {
  if (props.value >= 80) return '#7ca586'
  if (props.value >= 60) return '#c9973f'
  if (props.value >= 40) return '#c05b52'
  return '#a04a43'
})

/** 置信度等级描述 */
const confidenceLevel = computed(() => {
  if (props.value >= 90) return '高'
  if (props.value >= 70) return '较高'
  if (props.value >= 50) return '中等'
  if (props.value >= 30) return '较低'
  return '低'
})
</script>

<template>
  <div class="confidence-bar" :class="{ 'is-low': isLowConfidence }">
    <!-- 标签行 -->
    <div class="bar-header">
      <div class="bar-label">
        <span class="label-text">{{ label }}</span>
        <!-- 低置信度警告图标 -->
        <el-tooltip
          v-if="isLowConfidence"
          content="置信度较低，建议核实AI回答的准确性"
          placement="top"
        >
          <el-icon :size="14" class="warning-icon"><WarningFilled /></el-icon>
        </el-tooltip>
      </div>
      <div class="bar-value" :style="{ color: textColor }">
        <span v-if="showPercent" class="value-percent">{{ value }}%</span>
        <span class="value-level">{{ confidenceLevel }}</span>
      </div>
    </div>

    <!-- 进度条轨道 -->
    <div class="bar-track" :style="{ height: barHeight + 'px' }">
      <div
        class="bar-fill"
        :style="{
          width: value + '%',
          background: barGradient,
          height: barHeight + 'px',
        }"
      />
    </div>
  </div>
</template>

<style scoped>
/* 置信度进度条容器 */
.confidence-bar {
  width: 100%;
}

/* 低置信度样式 */
.confidence-bar.is-low .bar-track {
  background: rgba(192, 91, 82, 0.08);
}

/* 头部标签行 */
.bar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.bar-label {
  display: flex;
  align-items: center;
  gap: 4px;
}

.label-text {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-weight: var(--font-weight-medium);
}

/* 警告图标 */
.warning-icon {
  color: var(--color-warning);
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* 数值显示 */
.bar-value {
  display: flex;
  align-items: center;
  gap: 6px;
}

.value-percent {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  font-variant-numeric: tabular-nums;
}

.value-level {
  font-size: var(--font-size-xs);
  opacity: 0.7;
}

/* 进度条轨道 */
.bar-track {
  width: 100%;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-circle);
  overflow: hidden;
}

/* 进度条填充 */
.bar-fill {
  border-radius: var(--radius-circle);
  transition: width 0.6s ease, background 0.3s ease;
  position: relative;
}

/* 进度条光泽效果 */
.bar-fill::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 50%;
  background: linear-gradient(180deg, rgba(236, 231, 218, 0.16), transparent);
  border-radius: var(--radius-circle) var(--radius-circle) 0 0;
}
</style>
