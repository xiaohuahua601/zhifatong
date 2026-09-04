<!-- ============================================================
 * 智法通 - 风险条款卡片组件
 * 功能：条款原文、风险等级标签（高/中/低）、风险描述、
 *       修改建议、法律依据
 * ============================================================ -->
<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  Warning,
  Document,
  EditPen,
  Reading,
  ArrowDown,
  ArrowUp
} from '@element-plus/icons-vue'
import CitationTag from './CitationTag.vue'

/* ----------------------------------------------------------
 * Props 定义
 * ---------------------------------------------------------- */
interface LegalBasis {
  /** 法条名称 */
  name: string
  /** 条款编号 */
  article: string
  /** 效力状态 */
  status: 'valid' | 'revised' | 'abolished'
}

const props = withDefaults(defineProps<{
  /** 条款原文 */
  clauseText: string
  /** 条款编号/序号 */
  clauseIndex?: number
  /** 风险等级：high高 / medium中 / low低 */
  riskLevel: 'high' | 'medium' | 'low'
  /** 风险描述 */
  riskDescription: string
  /** 修改建议 */
  suggestion?: string
  /** 法律依据列表 */
  legalBasis?: LegalBasis[]
}>(), {
  clauseIndex: 1,
  suggestion: '',
  legalBasis: () => [],
})

/* ----------------------------------------------------------
 * 事件
 * ---------------------------------------------------------- */
const emit = defineEmits<{
  /** 点击法条引用 */
  (e: 'citation-click', basis: LegalBasis): void
}>()

/* ----------------------------------------------------------
 * 风险等级相关计算
 * ---------------------------------------------------------- */
/** 风险等级配置映射 */
const riskLevelConfig = computed(() => {
  const configs = {
    high: {
      label: '高风险',
      color: '#c05b52',
      bgColor: 'rgba(192, 91, 82, 0.12)',
      borderColor: 'rgba(192, 91, 82, 0.3)',
      tagType: 'danger' as const,
    },
    medium: {
      label: '中风险',
      color: '#c9973f',
      bgColor: 'rgba(201, 151, 63, 0.12)',
      borderColor: 'rgba(201, 151, 63, 0.3)',
      tagType: 'warning' as const,
    },
    low: {
      label: '低风险',
      color: '#7ca586',
      bgColor: 'rgba(124, 165, 134, 0.12)',
      borderColor: 'rgba(124, 165, 134, 0.3)',
      tagType: 'success' as const,
    },
  }
  return configs[props.riskLevel]
})

/* ----------------------------------------------------------
 * 展开/折叠详情
 * ---------------------------------------------------------- */
const isExpanded = ref(false)

const toggleExpand = () => {
  isExpanded.value = !isExpanded.value
}
</script>

<template>
  <div
    class="risk-clause-card"
    :class="[`risk-${riskLevel}`, { 'is-expanded': isExpanded }]"
    :style="{
      borderLeftColor: riskLevelConfig.color,
    }"
  >
    <!-- 卡片头部：条款编号 + 风险标签 + 展开按钮 -->
    <div class="clause-header" @click="toggleExpand">
      <div class="clause-header-left">
        <span class="clause-index">条款 {{ clauseIndex }}</span>
        <el-tag
          :type="riskLevelConfig.tagType"
          size="small"
          effect="dark"
          class="risk-tag"
          round
        >
          {{ riskLevelConfig.label }}
        </el-tag>
      </div>
      <el-icon class="expand-icon" :size="14">
        <ArrowDown v-if="!isExpanded" />
        <ArrowUp v-else />
      </el-icon>
    </div>

    <!-- 条款原文 -->
    <div class="clause-text">
      <div class="section-label">
        <el-icon :size="14"><Document /></el-icon>
        <span>条款原文</span>
      </div>
      <div class="clause-text-content">{{ clauseText }}</div>
    </div>

    <!-- 展开详情区域 -->
    <transition name="expand">
      <div v-if="isExpanded" class="clause-details">
        <!-- 风险描述 -->
        <div class="detail-section">
          <div class="section-label">
            <el-icon :size="14"><Warning /></el-icon>
            <span>风险描述</span>
          </div>
          <div class="detail-content risk-desc" :style="{ color: riskLevelConfig.color }">
            {{ riskDescription }}
          </div>
        </div>

        <!-- 修改建议 -->
        <div v-if="suggestion" class="detail-section">
          <div class="section-label">
            <el-icon :size="14"><EditPen /></el-icon>
            <span>修改建议</span>
          </div>
          <div class="detail-content suggestion-text">{{ suggestion }}</div>
        </div>

        <!-- 法律依据 -->
        <div v-if="legalBasis.length > 0" class="detail-section">
          <div class="section-label">
            <el-icon :size="14"><Reading /></el-icon>
            <span>法律依据</span>
          </div>
          <div class="detail-content legal-basis-list">
            <CitationTag
              v-for="(basis, index) in legalBasis"
              :key="index"
              :name="basis.name"
              :article="basis.article"
              :status="basis.status"
              class="basis-item"
              @click="emit('citation-click', basis)"
            />
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
/* 风险条款卡片 */
.risk-clause-card {
  background: rgba(28, 35, 52, 0.8);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(148, 158, 178, 0.14);
  border-left: 3px solid var(--color-border-primary);
  border-radius: 6px;
  padding: var(--spacing-base);
  transition: all var(--transition-base);
  cursor: default;
}

.risk-clause-card:hover {
  border-color: rgba(148, 158, 178, 0.24);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3);
}

/* 风险等级左边框色 */
.risk-high {
  border-left-color: #c05b52;
}

.risk-medium {
  border-left-color: #c9973f;
}

.risk-low {
  border-left-color: #7ca586;
}

/* 卡片头部 */
.clause-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  padding-bottom: var(--spacing-sm);
}

.clause-header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.clause-index {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.risk-tag {
  font-size: 11px;
}

.expand-icon {
  color: var(--color-text-tertiary);
  transition: transform var(--transition-fast);
}

/* 条款原文 */
.clause-text {
  margin-top: var(--spacing-sm);
}

.section-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-weight: var(--font-weight-medium);
  margin-bottom: var(--spacing-xs);
}

.clause-text-content {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: var(--line-height-relaxed);
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-base);
  border-left: 2px solid var(--color-border-primary);
}

/* 展开详情 */
.clause-details {
  margin-top: var(--spacing-md);
  padding-top: var(--spacing-md);
  border-top: 1px solid var(--color-border-secondary);
}

.detail-section {
  margin-bottom: var(--spacing-md);
}

.detail-section:last-child {
  margin-bottom: 0;
}

.detail-content {
  font-size: var(--font-size-sm);
  line-height: var(--line-height-relaxed);
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-base);
}

.risk-desc {
  font-weight: var(--font-weight-medium);
}

.suggestion-text {
  color: var(--color-text-primary);
}

.legal-basis-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm);
}

.basis-item {
  cursor: pointer;
}

/* 展开过渡动画 */
.expand-enter-active,
.expand-leave-active {
  transition: all var(--transition-base);
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
  margin-top: 0;
  padding-top: 0;
}

.expand-enter-to,
.expand-leave-from {
  max-height: 500px;
}
</style>
