<!-- ============================================================
 * 智法通 - 聊天输入组件
 * 功能：多行文本输入、发送按钮、快捷键支持（Ctrl+Enter发送）、
 *       输入中状态
 * ============================================================ -->
<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import { Promotion } from '@element-plus/icons-vue'

/* ----------------------------------------------------------
 * Props & Emits
 * ---------------------------------------------------------- */
const props = withDefaults(defineProps<{
  /** 是否禁用输入（AI正在生成时禁用） */
  disabled?: boolean
  /** 输入框占位文本 */
  placeholder?: string
  /** 最大输入字符数 */
  maxLength?: number
}>(), {
  disabled: false,
  placeholder: '输入法律问题，按 Ctrl+Enter 发送...',
  maxLength: 2000,
})

const emit = defineEmits<{
  /** 发送消息事件 */
  (e: 'send', message: string): void
}>()

/* ----------------------------------------------------------
 * 输入状态管理
 * ---------------------------------------------------------- */
const inputText = ref('')
const textareaRef = ref<HTMLTextAreaElement>()
const isComposing = ref(false)
const isFocused = ref(false)

/** 输入中状态（用于显示打字指示） */
const isTyping = ref(false)
let typingTimer: ReturnType<typeof setTimeout> | null = null

/* ----------------------------------------------------------
 * 自动调整高度
 * 根据内容自动调整textarea高度，最大5行
 * ---------------------------------------------------------- */
const autoResize = () => {
  nextTick(() => {
    const textarea = textareaRef.value
    if (!textarea) return
    textarea.style.height = 'auto'
    const maxHeight = 5 * 24 // 约5行高度
    textarea.style.height = Math.min(textarea.scrollHeight, maxHeight) + 'px'
  })
}

/* ----------------------------------------------------------
 * 发送消息
 * ---------------------------------------------------------- */
const sendMessage = () => {
  const trimmed = inputText.value.trim()
  if (!trimmed || props.disabled) return

  emit('send', trimmed)
  inputText.value = ''

  // 重置高度
  nextTick(() => {
    const textarea = textareaRef.value
    if (textarea) {
      textarea.style.height = 'auto'
    }
  })
}

/* ----------------------------------------------------------
 * 键盘事件处理
 * Ctrl+Enter 或 Cmd+Enter 发送消息
 * ---------------------------------------------------------- */
const handleKeydown = (e: KeyboardEvent) => {
  // 输入法组合中不处理
  if (isComposing.value) return

  // Ctrl+Enter 或 Cmd+Enter 发送
  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
    e.preventDefault()
    sendMessage()
  }
}

/* ----------------------------------------------------------
 * 输入法组合事件
 * 防止中文输入法中触发发送
 * ---------------------------------------------------------- */
const handleCompositionStart = () => {
  isComposing.value = true
}

const handleCompositionEnd = () => {
  isComposing.value = false
}

/* ----------------------------------------------------------
 * 输入事件
 * ---------------------------------------------------------- */
const handleInput = () => {
  autoResize()

  // 输入中状态指示
  isTyping.value = true
  if (typingTimer) clearTimeout(typingTimer)
  typingTimer = setTimeout(() => {
    isTyping.value = false
  }, 1000)
}

/* ----------------------------------------------------------
 * 监听内容变化
 * ---------------------------------------------------------- */
watch(inputText, () => {
  autoResize()
})
</script>

<template>
  <div class="chat-input-container" :class="{ 'is-focused': isFocused, 'is-disabled': disabled }">
    <!-- 输入区域 -->
    <div class="input-wrapper">
      <textarea
        ref="textareaRef"
        v-model="inputText"
        class="chat-textarea"
        :placeholder="placeholder"
        :disabled="disabled"
        :maxlength="maxLength"
        rows="1"
        @keydown="handleKeydown"
        @compositionstart="handleCompositionStart"
        @compositionend="handleCompositionEnd"
        @input="handleInput"
        @focus="isFocused = true"
        @blur="isFocused = false"
      />
    </div>

    <!-- 底部工具栏 -->
    <div class="input-toolbar">
      <!-- 字数统计 -->
      <span class="char-count" :class="{ 'is-warning': inputText.length > maxLength * 0.9 }">
        {{ inputText.length }} / {{ maxLength }}
      </span>

      <!-- 发送按钮 -->
      <el-button
        class="send-btn"
        :icon="Promotion"
        :disabled="!inputText.trim() || disabled"
        :loading="disabled"
        type="primary"
        @click="sendMessage"
      >
        发送
      </el-button>
    </div>

    <!-- 输入中指示器 -->
    <transition name="fade">
      <div v-if="isTyping && inputText.length > 0" class="typing-indicator">
        <span class="typing-dot" />
        <span class="typing-dot" />
        <span class="typing-dot" />
      </div>
    </transition>
  </div>
</template>

<style scoped>
/* 输入容器 */
.chat-input-container {
  position: relative;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--color-border-primary);
  border-radius: 6px;
  transition: all var(--transition-base);
  overflow: hidden;
}

/* 聚焦状态 */
.chat-input-container.is-focused {
  border-color: rgba(201, 169, 98, 0.4);
  box-shadow: 0 0 0 1px rgba(201, 169, 98, 0.1), 0 4px 24px rgba(0, 0, 0, 0.2);
}

/* 禁用状态 */
.chat-input-container.is-disabled {
  opacity: 0.6;
}

/* 输入区域 */
.input-wrapper {
  padding: var(--spacing-md) var(--spacing-base) 0;
}

/* 多行文本输入框 */
.chat-textarea {
  width: 100%;
  min-height: 24px;
  max-height: 120px;
  resize: none;
  background: transparent;
  border: none;
  outline: none;
  color: var(--color-text-primary);
  font-size: var(--font-size-base);
  line-height: 24px;
  font-family: var(--font-family);
}

.chat-textarea::placeholder {
  color: var(--color-text-tertiary);
}

.chat-textarea:disabled {
  cursor: not-allowed;
}

/* 底部工具栏 */
.input-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-sm) var(--spacing-base) var(--spacing-md);
}

/* 字数统计 */
.char-count {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  transition: color var(--transition-fast);
}

.char-count.is-warning {
  color: var(--color-warning);
}

/* 发送按钮 */
.send-btn {
  border-radius: var(--radius-base) !important;
  background: linear-gradient(135deg, var(--color-brand-blue), var(--color-brand-blue-light)) !important;
  border: none !important;
  color: var(--color-brand-gold) !important;
  font-weight: var(--font-weight-medium) !important;
  padding: 8px 20px !important;
  transition: all var(--transition-base) !important;
}

.send-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, var(--color-brand-blue-light), var(--color-brand-blue)) !important;
  box-shadow: 0 0 16px rgba(201, 169, 98, 0.2) !important;
  transform: translateY(-1px);
}

.send-btn:disabled {
  opacity: 0.5 !important;
}

/* 输入中指示器 */
.typing-indicator {
  position: absolute;
  bottom: 52px;
  right: var(--spacing-base);
  display: flex;
  gap: 3px;
  align-items: center;
}

.typing-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--color-brand-gold);
  animation: typingBounce 1.4s ease-in-out infinite;
}

.typing-dot:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typingBounce {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.4;
  }
  30% {
    transform: translateY(-4px);
    opacity: 1;
  }
}

/* 淡入淡出过渡 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--transition-fast);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
