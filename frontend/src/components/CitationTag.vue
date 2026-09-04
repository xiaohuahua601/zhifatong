<!-- ============================================================
 * 智法通 - 法条引用标签组件
 * 功能：法条名称、条款编号、点击查看详情、效力状态标识
 * ============================================================ -->
<script setup lang="ts">
import { computed } from 'vue'
import { TopRight } from '@element-plus/icons-vue'

/* ----------------------------------------------------------
 * Props 定义
 * ---------------------------------------------------------- */
const props = withDefaults(defineProps<{
  /** 法条名称（如"中华人民共和国民法典"） */
  name: string
  /** 条款编号（如"第580条"） */
  article: string
  /** 效力状态：valid有效 / revised已修订 / abolished已废止 */
  status?: 'valid' | 'revised' | 'abolished'
  /** 是否显示跳转图标 */
  showLink?: boolean
}>(), {
  status: 'valid',
  showLink: true,
})

/* ----------------------------------------------------------
 * 事件
 * ---------------------------------------------------------- */
const emit = defineEmits<{
  /** 点击标签事件 */
  (e: 'click', data: { name: string; article: string; status: string }): void
}>()

/* ----------------------------------------------------------
 * 效力状态配置
 * ---------------------------------------------------------- */
const statusConfig = computed(() => {
  const configs = {
    valid: {
      label: '有效',
      color: '#7ca586',
      bgColor: 'rgba(124, 165, 134, 0.12)',
    },
    revised: {
      label: '已修订',
      color: '#c9973f',
      bgColor: 'rgba(201, 151, 63, 0.12)',
    },
    abolished: {
      label: '已废止',
      color: '#c05b52',
      bgColor: 'rgba(192, 91, 82, 0.12)',
    },
  }
  return configs[props.status]
})

/* ----------------------------------------------------------
 * 点击处理
 * ---------------------------------------------------------- */
const handleClick = () => {
  emit('click', {
    name: props.name,
    article: props.article,
    status: props.status,
  })
}
</script>

<template>
  <div class="citation-tag" @click="handleClick">
    <!-- 法条名称 -->
    <span class="citation-name">《{{ name }}》</span>

    <!-- 条款编号 -->
    <span class="citation-article">{{ article }}</span>

    <!-- 效力状态标识 -->
    <span
      class="citation-status"
      :style="{
        color: statusConfig.color,
        backgroundColor: statusConfig.bgColor,
      }"
    >
      {{ statusConfig.label }}
    </span>

    <!-- 跳转图标 -->
    <el-icon v-if="showLink" :size="10" class="citation-link-icon">
      <TopRight />
    </el-icon>
  </div>
</template>

<style scoped>
/* 法条引用标签 */
.citation-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: rgba(201, 169, 98, 0.1);
  border: 1px solid rgba(201, 169, 98, 0.3);
  border-radius: 6px;
  color: var(--color-brand-gold);
  font-size: var(--font-size-xs);
  cursor: pointer;
  transition: all var(--transition-fast);
  white-space: nowrap;
  user-select: none;
}

.citation-tag:hover {
  background: rgba(201, 169, 98, 0.2);
  border-color: var(--color-brand-gold);
  box-shadow: 0 0 8px rgba(201, 169, 98, 0.15);
  transform: translateY(-1px);
}

.citation-tag:active {
  transform: translateY(0);
}

/* 法条名称 */
.citation-name {
  font-weight: var(--font-weight-medium);
}

/* 条款编号 */
.citation-article {
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-normal);
}

/* 效力状态标识 */
.citation-status {
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 3px;
  font-weight: var(--font-weight-medium);
  line-height: 1.4;
}

/* 跳转图标 */
.citation-link-icon {
  opacity: 0.5;
  transition: opacity var(--transition-fast);
}

.citation-tag:hover .citation-link-icon {
  opacity: 1;
}
</style>
