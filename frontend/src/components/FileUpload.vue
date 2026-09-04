<!-- ============================================================
 * 智法通 - 文件上传组件
 * 功能：拖拽上传区域、文件类型限制、上传进度、文件预览
 * ============================================================ -->
<script setup lang="ts">
import { ref, computed } from 'vue'
import {
  UploadFilled,
  Document,
  Delete,
  CircleCheck,
  CircleClose,
  View
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

/* ----------------------------------------------------------
 * Props 定义
 * ---------------------------------------------------------- */
interface UploadedFile {
  /** 文件唯一标识 */
  uid: string | number
  /** 文件名 */
  name: string
  /** 文件大小（字节） */
  size: number
  /** 文件类型 */
  type: string
  /** 上传状态：uploading上传中 / success成功 / error失败 */
  status: 'uploading' | 'success' | 'error'
  /** 上传进度（0-100） */
  progress: number
  /** 文件预览URL */
  url?: string
}

const props = withDefaults(defineProps<{
  /** 允许的文件类型（MIME类型数组），空数组表示不限 */
  accept?: string[]
  /** 最大文件大小（MB） */
  maxSize?: number
  /** 最大文件数量 */
  maxCount?: number
  /** 是否禁用 */
  disabled?: boolean
  /** 提示文字 */
  tip?: string
}>(), {
  accept: () => ['.pdf', '.doc', '.docx', '.txt', '.jpg', '.png'],
  maxSize: 20,
  maxCount: 5,
  disabled: false,
  tip: '支持 PDF、Word、TXT、图片格式，单文件不超过 20MB',
})

/* ----------------------------------------------------------
 * 事件
 * ---------------------------------------------------------- */
const emit = defineEmits<{
  /** 文件上传成功 */
  (e: 'success', file: UploadedFile): void
  /** 文件上传失败 */
  (e: 'error', file: UploadedFile, error: string): void
  /** 文件被移除 */
  (e: 'remove', file: UploadedFile): void
}>()

/* ----------------------------------------------------------
 * 状态管理
 * ---------------------------------------------------------- */
const fileList = ref<UploadedFile[]>([])
const isDragover = ref(false)
const fileInputRef = ref<HTMLInputElement>()

/** 是否达到最大文件数 */
const isMaxCount = computed(() => fileList.value.length >= props.maxCount)

/** 接受的文件类型字符串（用于input的accept属性） */
const acceptString = computed(() => props.accept.join(','))

/* ----------------------------------------------------------
 * 文件大小格式化
 * ---------------------------------------------------------- */
const formatSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

/* ----------------------------------------------------------
 * 文件校验
 * ---------------------------------------------------------- */
const validateFile = (file: File): string | null => {
  // 文件类型校验
  if (props.accept.length > 0) {
    const ext = '.' + file.name.split('.').pop()?.toLowerCase()
    if (!props.accept.includes(ext)) {
      return `不支持的文件格式 ${ext}，仅支持 ${props.accept.join('、')}`
    }
  }

  // 文件大小校验
  const maxBytes = props.maxSize * 1024 * 1024
  if (file.size > maxBytes) {
    return `文件大小超过限制（最大 ${props.maxSize}MB）`
  }

  // 文件数量校验
  if (isMaxCount.value) {
    return `最多上传 ${props.maxCount} 个文件`
  }

  return null
}

/* ----------------------------------------------------------
 * 上传处理
 * ---------------------------------------------------------- */
const processFile = (file: File) => {
  const error = validateFile(file)
  if (error) {
    ElMessage.warning(error)
    return
  }

  // 创建上传文件对象
  const uploadedFile: UploadedFile = {
    uid: Date.now() + Math.random(),
    name: file.name,
    size: file.size,
    type: file.type,
    status: 'uploading',
    progress: 0,
    url: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined,
  }

  fileList.value.push(uploadedFile)

  // 模拟上传进度（实际项目中替换为真实上传逻辑）
  simulateUpload(uploadedFile)
}

/** 模拟上传过程 */
const simulateUpload = (file: UploadedFile) => {
  let progress = 0
  const timer = setInterval(() => {
    progress += Math.random() * 20 + 5
    if (progress >= 100) {
      progress = 100
      file.progress = 100
      file.status = 'success'
      clearInterval(timer)
      emit('success', file)
      ElMessage.success(`${file.name} 上传成功`)
    } else {
      file.progress = Math.round(progress)
    }
  }, 300)
}

/* ----------------------------------------------------------
 * 拖拽事件处理
 * ---------------------------------------------------------- */
const handleDragover = (e: DragEvent) => {
  e.preventDefault()
  if (!props.disabled) {
    isDragover.value = true
  }
}

const handleDragleave = (e: DragEvent) => {
  e.preventDefault()
  isDragover.value = false
}

const handleDrop = (e: DragEvent) => {
  e.preventDefault()
  isDragover.value = false
  if (props.disabled) return

  const files = e.dataTransfer?.files
  if (files) {
    Array.from(files).forEach(processFile)
  }
}

/* ----------------------------------------------------------
 * 点击选择文件
 * ---------------------------------------------------------- */
const handleClick = () => {
  if (props.disabled || isMaxCount.value) return
  fileInputRef.value?.click()
}

const handleFileChange = (e: Event) => {
  const input = e.target as HTMLInputElement
  if (input.files) {
    Array.from(input.files).forEach(processFile)
  }
  // 重置input，允许重复选择同一文件
  input.value = ''
}

/* ----------------------------------------------------------
 * 移除文件
 * ---------------------------------------------------------- */
const removeFile = (index: number) => {
  const file = fileList.value[index]
  // 释放预览URL
  if (file.url) {
    URL.revokeObjectURL(file.url)
  }
  fileList.value.splice(index, 1)
  emit('remove', file)
}

/* ----------------------------------------------------------
 * 预览文件
 * ---------------------------------------------------------- */
const previewFile = (file: UploadedFile) => {
  if (file.url) {
    window.open(file.url, '_blank')
  }
}

/** 获取文件图标颜色 */
const getFileIconColor = (status: string) => {
  if (status === 'success') return 'var(--color-success)'
  if (status === 'error') return 'var(--color-danger)'
  return 'var(--color-brand-gold)'
}
</script>

<template>
  <div class="file-upload-container">
    <!-- 拖拽上传区域 -->
    <div
      class="upload-area"
      :class="{
        'is-dragover': isDragover,
        'is-disabled': disabled,
        'is-max': isMaxCount,
      }"
      @click="handleClick"
      @dragover="handleDragover"
      @dragleave="handleDragleave"
      @drop="handleDrop"
    >
      <input
        ref="fileInputRef"
        type="file"
        :accept="acceptString"
        :disabled="disabled"
        multiple
        class="file-input"
        @change="handleFileChange"
      />

      <div class="upload-icon">
        <el-icon :size="40" color="var(--color-brand-gold)">
          <UploadFilled />
        </el-icon>
      </div>

      <div class="upload-text">
        <span class="upload-main-text">
          将文件拖到此处，或<em>点击上传</em>
        </span>
        <span class="upload-tip">{{ tip }}</span>
      </div>
    </div>

    <!-- 文件列表 -->
    <transition-group name="list" tag="div" class="file-list" v-if="fileList.length > 0">
      <div
        v-for="(file, index) in fileList"
        :key="file.uid"
        class="file-item"
      >
        <!-- 文件图标 -->
        <div class="file-icon" :style="{ color: getFileIconColor(file.status) }">
          <el-icon :size="20"><Document /></el-icon>
        </div>

        <!-- 文件信息 -->
        <div class="file-info">
          <div class="file-name-row">
            <span class="file-name" :title="file.name">{{ file.name }}</span>
            <span class="file-size">{{ formatSize(file.size) }}</span>
          </div>

          <!-- 上传进度条 -->
          <div v-if="file.status === 'uploading'" class="file-progress">
            <div class="progress-bar">
              <div
                class="progress-fill"
                :style="{ width: file.progress + '%' }"
              />
            </div>
            <span class="progress-text">{{ file.progress }}%</span>
          </div>

          <!-- 上传状态图标 -->
          <div v-else class="file-status">
            <el-icon v-if="file.status === 'success'" :size="14" color="var(--color-success)">
              <CircleCheck />
            </el-icon>
            <el-icon v-else :size="14" color="var(--color-danger)">
              <CircleClose />
            </el-icon>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="file-actions">
          <el-icon
            v-if="file.url"
            :size="14"
            class="action-icon"
            @click.stop="previewFile(file)"
          >
            <View />
          </el-icon>
          <el-icon
            :size="14"
            class="action-icon action-delete"
            @click.stop="removeFile(index)"
          >
            <Delete />
          </el-icon>
        </div>
      </div>
    </transition-group>
  </div>
</template>

<style scoped>
/* 上传容器 */
.file-upload-container {
  width: 100%;
}

/* 拖拽上传区域 */
.upload-area {
  border: 2px dashed var(--color-border-primary);
  border-radius: 6px;
  padding: var(--spacing-3xl) var(--spacing-xl);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-md);
  cursor: pointer;
  background: rgba(255, 255, 255, 0.5);
  transition: all var(--transition-base);
}

.upload-area:hover {
  border-color: var(--color-brand-gold);
  background: rgba(201, 169, 98, 0.03);
}

.upload-area.is-dragover {
  border-color: var(--color-brand-gold);
  background: rgba(201, 169, 98, 0.05);
  box-shadow: 0 0 20px rgba(201, 169, 98, 0.1);
}

.upload-area.is-disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.upload-area.is-max {
  opacity: 0.4;
  cursor: not-allowed;
}

/* 隐藏原生文件输入 */
.file-input {
  display: none;
}

/* 上传图标 */
.upload-icon {
  opacity: 0.7;
  transition: all var(--transition-base);
}

.upload-area:hover .upload-icon {
  opacity: 1;
  transform: translateY(-2px);
}

/* 上传文字 */
.upload-text {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-xs);
}

.upload-main-text {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
}

.upload-main-text em {
  color: var(--color-brand-gold);
  font-style: normal;
  font-weight: var(--font-weight-medium);
}

.upload-tip {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

/* 文件列表 */
.file-list {
  margin-top: var(--spacing-base);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

/* 文件项 */
.file-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md) var(--spacing-base);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border-secondary);
  border-radius: var(--radius-base);
  transition: all var(--transition-fast);
}

.file-item:hover {
  border-color: var(--color-border-primary);
  background: var(--color-bg-tertiary);
}

/* 文件图标 */
.file-icon {
  flex-shrink: 0;
}

/* 文件信息 */
.file-info {
  flex: 1;
  min-width: 0;
}

.file-name-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-sm);
}

.file-name {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  flex-shrink: 0;
}

/* 进度条 */
.file-progress {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-xs);
}

.progress-bar {
  flex: 1;
  height: 4px;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-circle);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-brand-blue-light), var(--color-brand-gold));
  border-radius: var(--radius-circle);
  transition: width 0.3s ease;
}

.progress-text {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  min-width: 36px;
  text-align: right;
}

/* 文件状态 */
.file-status {
  margin-top: var(--spacing-xs);
}

/* 操作按钮 */
.file-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.file-item:hover .file-actions {
  opacity: 1;
}

.action-icon {
  cursor: pointer;
  color: var(--color-text-tertiary);
  transition: color var(--transition-fast);
}

.action-icon:hover {
  color: var(--color-brand-gold);
}

.action-delete:hover {
  color: var(--color-danger) !important;
}

/* 列表过渡动画 */
.list-enter-active,
.list-leave-active {
  transition: all var(--transition-base);
}

.list-enter-from {
  opacity: 0;
  transform: translateX(-16px);
}

.list-leave-to {
  opacity: 0;
  transform: translateX(16px);
}
</style>
