<!-- ============================================================
 * 智法通 - 聊天消息组件
 * 功能：用户/助手消息区分、Markdown渲染、法条引用高亮、
 *       置信度指示、反馈按钮、复制按钮
 * ============================================================ -->
<script setup lang="ts">
import { ref, computed } from 'vue'
import {
  CopyDocument,
  Check,
  Select,
  Close,
  TopRight
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import CitationTag from './CitationTag.vue'
import ConfidenceBar from './ConfidenceBar.vue'

/* ----------------------------------------------------------
 * Props 定义
 * ---------------------------------------------------------- */
interface Citation {
  /** 法条名称 */
  name: string
  /** 条款编号 */
  article: string
  /** 效力状态：有效/已修订/已废止 */
  status: 'valid' | 'revised' | 'abolished'
}

const props = withDefaults(defineProps<{
  /** 消息角色：user用户 / assistant助手 */
  role: 'user' | 'assistant'
  /** 消息文本内容（支持Markdown） */
  content: string
  /** 消息发送时间 */
  timestamp?: string
  /** AI回答的置信度（0-100），仅助手消息有效 */
  confidence?: number
  /** 法条引用列表，仅助手消息有效 */
  citations?: Citation[]
  /** 是否正在生成中（流式输出状态） */
  streaming?: boolean
}>(), {
  timestamp: '',
  confidence: 0,
  citations: () => [],
  streaming: false,
})

/* ----------------------------------------------------------
 * 事件
 * ---------------------------------------------------------- */
const emit = defineEmits<{
  /** 点击法条引用 */
  (e: 'citation-click', citation: Citation): void
  /** 反馈：点赞/踩 */
  (e: 'feedback', type: 'like' | 'dislike'): void
}>()

/* ----------------------------------------------------------
 * 复制功能
 * ---------------------------------------------------------- */
const copied = ref(false)

/** 复制消息内容到剪贴板 */
const copyContent = async () => {
  try {
    await navigator.clipboard.writeText(props.content)
    copied.value = true
    ElMessage.success('已复制到剪贴板')
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch {
    ElMessage.error('复制失败')
  }
}

/* ----------------------------------------------------------
 * 反馈功能
 * ---------------------------------------------------------- */
const feedbackType = ref<'like' | 'dislike' | null>(null)

/** 提交反馈 */
const handleFeedback = (type: 'like' | 'dislike') => {
  feedbackType.value = feedbackType.value === type ? null : type
  emit('feedback', type)
}

/* ----------------------------------------------------------
 * 简易Markdown渲染
 * 将Markdown文本转为HTML（生产环境应使用marked等库）
 * ---------------------------------------------------------- */
const renderedContent = computed(() => {
  let html = props.content

  // 代码块处理
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code class="lang-$1">$2</code></pre>')
  // 行内代码
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>')
  // 加粗
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  // 斜体
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>')
  // 标题
  html = html.replace(/^### (.+)$/gm, '<h4>$1</h4>')
  html = html.replace(/^## (.+)$/gm, '<h3>$1</h3>')
  html = html.replace(/^# (.+)$/gm, '<h2>$1</h2>')
  // 无序列表
  html = html.replace(/^- (.+)$/gm, '<li>$1</li>')
  html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>')
  // 有序列表
  html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
  // 引用
  html = html.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
  // 法条引用高亮：匹配《xxx》第x条 格式
  html = html.replace(/《([^》]+)》第([一二三四五六七八九十百千\d]+)条/g,
    '<span class="law-citation">《$1》第$2条</span>')
  // 换行
  html = html.replace(/\n/g, '<br>')

  return html
})

/** 是否为助手消息 */
const isAssistant = computed(() => props.role === 'assistant')
</script>

<template>
  <div
    class="chat-message"
    :class="[`chat-message-${role}`, { 'is-streaming': streaming }]"
  >
    <!-- 头像 -->
    <div class="message-avatar">
      <div v-if="isAssistant" class="avatar-assistant">
        <svg viewBox="0 0 24 24" fill="none" width="20" height="20">
          <path d="M12 2L4 6V12C4 16.4 7.4 20.5 12 22C16.6 20.5 20 16.4 20 12V6L12 2Z"
            fill="#b7791f" opacity="0.2" stroke="#b7791f" stroke-width="1.5"/>
          <path d="M9 12L11 14L15 10" stroke="#b7791f" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
      </div>
      <div v-else class="avatar-user">
        <el-icon :size="16"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg></el-icon>
      </div>
    </div>

    <!-- 消息主体 -->
    <div class="message-body">
      <!-- 消息内容区域 -->
      <div class="message-content" v-html="renderedContent" />

      <!-- 流式输出光标 -->
      <span v-if="streaming" class="streaming-cursor">▊</span>

      <!-- 法条引用标签列表 -->
      <div v-if="isAssistant && citations.length > 0" class="message-citations">
        <span class="citations-label">引用法条：</span>
        <CitationTag
          v-for="(citation, index) in citations"
          :key="index"
          :name="citation.name"
          :article="citation.article"
          :status="citation.status"
          class="citation-item"
          @click="emit('citation-click', citation)"
        />
      </div>

      <!-- 置信度指示（仅助手消息且置信度>0时显示） -->
      <ConfidenceBar
        v-if="isAssistant && confidence > 0"
        :value="confidence"
        class="message-confidence"
      />

      <!-- 底部操作栏 -->
      <div class="message-footer" v-if="isAssistant && !streaming">
        <span class="message-time" v-if="timestamp">{{ timestamp }}</span>
        <div class="message-actions">
          <!-- 复制按钮 -->
          <el-tooltip :content="copied ? '已复制' : '复制'" placement="top">
            <div class="action-btn" @click="copyContent">
              <el-icon :size="14">
                <Check v-if="copied" />
                <CopyDocument v-else />
              </el-icon>
            </div>
          </el-tooltip>
          <!-- 点赞 -->
          <el-tooltip content="有帮助" placement="top">
            <div
              class="action-btn"
              :class="{ 'is-active': feedbackType === 'like' }"
              @click="handleFeedback('like')"
            >
              <el-icon :size="14"><Select /></el-icon>
            </div>
          </el-tooltip>
          <!-- 踩 -->
          <el-tooltip content="需改进" placement="top">
            <div
              class="action-btn"
              :class="{ 'is-active': feedbackType === 'dislike' }"
              @click="handleFeedback('dislike')"
            >
              <el-icon :size="14"><Close /></el-icon>
            </div>
          </el-tooltip>
        </div>
      </div>

      <!-- AI生成内容标识（合规要求） -->
      <div v-if="isAssistant && !streaming" class="ai-content-label">
        AI生成内容，仅供参考
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 消息容器 */
.chat-message {
  display: flex;
  gap: var(--spacing-md);
  padding: var(--spacing-base) var(--spacing-xl);
  animation: fadeInUp 0.3s ease both;
}

/* 用户消息靠右 */
.chat-message-user {
  flex-direction: row-reverse;
}

/* 头像 */
.message-avatar {
  flex-shrink: 0;
  margin-top: 2px;
}

.avatar-assistant {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-lg);
  background: rgba(201, 169, 98, 0.1);
  border: 1px solid rgba(201, 169, 98, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-user {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, var(--color-brand-blue), var(--color-brand-blue-light));
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-brand-gold);
}

/* 消息主体 */
.message-body {
  max-width: 70%;
  min-width: 0;
}

/* 用户消息气泡 */
.chat-message-user .message-body {
  background: linear-gradient(135deg, rgba(60, 74, 104, 0.6), rgba(60, 74, 104, 0.3));
  border: 1px solid rgba(60, 74, 104, 0.5);
  border-radius: 8px 8px 2px 8px;
  padding: var(--spacing-md) var(--spacing-base);
}

/* 助手消息气泡 */
.chat-message-assistant .message-body {
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(148, 158, 178, 0.14);
  border-radius: 8px 8px 8px 2px;
  padding: var(--spacing-md) var(--spacing-base);
}

/* 消息内容排版 */
.message-content {
  font-size: var(--font-size-base);
  line-height: var(--line-height-relaxed);
  color: var(--color-text-primary);
  word-break: break-word;
}

/* Markdown渲染样式 */
.message-content :deep(h2),
.message-content :deep(h3),
.message-content :deep(h4) {
  margin: var(--spacing-base) 0 var(--spacing-sm);
  color: var(--color-text-primary);
}

.message-content :deep(strong) {
  color: var(--color-brand-gold);
  font-weight: var(--font-weight-semibold);
}

.message-content :deep(code) {
  font-family: var(--font-family-mono);
  font-size: 0.9em;
  padding: 2px 6px;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-sm);
  color: var(--color-brand-gold);
}

.message-content :deep(pre) {
  margin: var(--spacing-sm) 0;
  padding: var(--spacing-base);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-base);
  overflow-x: auto;
}

.message-content :deep(blockquote) {
  margin: var(--spacing-sm) 0;
  padding: var(--spacing-sm) var(--spacing-base);
  border-left: 3px solid var(--color-brand-gold);
  background: var(--color-bg-tertiary);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  color: var(--color-text-secondary);
}

/* 法条引用高亮 */
.message-content :deep(.law-citation) {
  color: var(--color-brand-gold);
  background: rgba(201, 169, 98, 0.1);
  padding: 1px 4px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.message-content :deep(.law-citation:hover) {
  background: rgba(201, 169, 98, 0.2);
}

/* 流式输出光标 */
.streaming-cursor {
  color: var(--color-brand-gold);
  animation: blink 1s step-end infinite;
  font-size: var(--font-size-base);
  margin-left: 2px;
}

/* 法条引用标签区域 */
.message-citations {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-md);
  padding-top: var(--spacing-md);
  border-top: 1px solid var(--color-border-secondary);
}

.citations-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  white-space: nowrap;
}

.citation-item {
  cursor: pointer;
}

/* 置信度条 */
.message-confidence {
  margin-top: var(--spacing-md);
}

/* 底部操作栏 */
.message-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: var(--spacing-md);
  padding-top: var(--spacing-sm);
  border-top: 1px solid var(--color-border-secondary);
}

.message-time {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

/* AI生成内容标识（合规要求） */
.ai-content-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  opacity: 0.7;
  margin-top: var(--spacing-sm);
  user-select: none;
}

.message-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.chat-message:hover .message-actions {
  opacity: 1;
}

/* 操作按钮 */
.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-base);
  cursor: pointer;
  color: var(--color-text-tertiary);
  transition: all var(--transition-fast);
}

.action-btn:hover {
  color: var(--color-brand-gold);
  background: rgba(201, 169, 98, 0.08);
}

.action-btn.is-active {
  color: var(--color-brand-gold);
  background: rgba(201, 169, 98, 0.12);
}

/* 动画 */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
</style>
