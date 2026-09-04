/**
 * 智法通 - 法律问答页面（案卷墨蓝 · 鎏金典雅）
 *
 * 结构与上一版完全一致：纸纹底纹层 + 左侧会话档案栏（衬线金区块头/
 * 圆点节点/衬线金读数）+ 右侧问答主区（信息条/元数据行消息面板）+
 * 素净输入面板 + 鎏金天平徽记欢迎空状态。
 *
 * 功能与上一版完全一致：流式回答（SSE）、法条引用高亮、置信度指示、
 * 反馈按钮、推荐问题、会话重命名/删除、额度读数。
 */

<template>
  <div class="qa-page fade-in">
    <!-- 页面级纸纹肌理层（内容浮于其上） -->
    <div class="page-grid-bg"></div>

    <!-- ==================== 左侧会话档案栏 ==================== -->
    <aside class="conv-rail">
      <!-- 区块头：对话记录 + hex 新建按钮（发光形态） -->
      <div class="rail-head">
        <div class="tech-section-header">
          <div class="tsh-bar"></div>
          <span class="tsh-title">对话记录</span>
          <div class="tsh-line"></div>
          <div class="tsh-extra">
            <span class="tech-label new-chat-label">新建对话</span>
            <button type="button" class="new-chat-hex" title="新建对话" @click="handleNewChat">
              <el-icon :size="13"><Plus /></el-icon>
            </button>
          </div>
        </div>
        <!-- 额度读数：终端读出形态（保留原数据绑定与逻辑） -->
        <div class="quota-readout">
          <span
            class="status-light"
            :class="(userStore.isAdmin || remainingQaQuota === -1) ? 'is-on' : (remainingQaQuota <= 0 ? 'is-off' : (remainingQaQuota <= 5 ? 'is-warn' : 'is-on'))"
          ></span>
          <el-icon :size="12" class="quota-icon"><Coin /></el-icon>
          <span class="tech-label">今日剩余咨询次数</span>
          <span v-if="userStore.isAdmin || remainingQaQuota === -1" class="readout-box">
            <strong class="data-readout quota-val">∞</strong>
            <span class="quota-unit">不限</span>
          </span>
          <span v-else class="readout-box">
            <strong class="data-readout quota-val">{{ remainingQaQuota }}</strong>
            <span class="quota-unit">次</span>
          </span>
        </div>
      </div>

      <!-- 会话列表：状态条 + 菱形节点 + 标题/时间 + hover 操作 -->
      <div class="conversation-list">
        <div
          v-for="(conv, index) in qaStore.conversations"
          :key="conv.id"
          class="conv-item stagger-item"
          :class="{ active: conv.id === qaStore.currentConversationId }"
          :style="{ animationDelay: index * 0.06 + 's' }"
          @click="handleSelectConversation(conv.id)"
        >
          <!-- 活跃会话左侧发光状态条（保留原指示逻辑） -->
          <div v-if="conv.id === qaStore.currentConversationId" class="active-glow-bar"></div>
          <span
            class="diamond-node conv-node"
            :class="conv.id === qaStore.currentConversationId ? 'node-cyan' : 'node-hollow'"
          ></span>
          <div class="conv-main">
            <input
              v-if="renamingId === conv.id"
              v-model="renamingTitle"
              class="conv-rename-input"
              @click.stop
              @keyup.enter="confirmRename"
              @keyup.esc="cancelRename"
              @blur="confirmRename"
              ref="renameInputRef"
            />
            <template v-else>
              <span class="conv-title">{{ conv.title || '新对话' }}</span>
              <span v-if="conv.updated_at" class="conv-time">{{ conv.updated_at.slice(5, 16).replace('T', ' ') }}</span>
            </template>
          </div>
          <!-- 操作按钮组：重命名 + 删除（hover 浮现，事件保留） -->
          <div class="conv-actions">
            <el-icon
              class="conv-rename"
              :size="14"
              @click.stop="startRename(conv)"
            >
              <Edit />
            </el-icon>
            <el-icon
              class="conv-delete"
              :size="14"
              @click.stop="handleDeleteConversation(conv.id)"
            >
              <Delete />
            </el-icon>
          </div>
        </div>
        <!-- 空状态：hex 徽章形态 -->
        <div v-if="qaStore.conversations.length === 0" class="empty-state">
          <div class="empty-hex hex-badge hex-ghost">
            <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
              <g stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="32" cy="11" r="2.5" fill="currentColor" stroke="none"/>
                <path d="M32 14V52"/>
                <path d="M14 20H50"/>
                <path d="M14 20L6 33M14 20L22 33"/>
                <path d="M6 33Q14 42 22 33"/>
                <path d="M50 20L42 33M50 20L58 33"/>
                <path d="M42 33Q50 42 58 33"/>
                <path d="M21 52H43"/>
                <path d="M26 57H38"/>
              </g>
            </svg>
          </div>
          <p class="empty-title">暂无对话记录</p>
          <p class="empty-hint">点击右上 + 号开启新对话</p>
        </div>
      </div>
    </aside>

    <!-- ==================== 右侧通讯主区 ==================== -->
    <section class="chat-area">
      <!-- 顶部会话信息条：状态灯 + 元信息 + 消息计数读出 -->
      <div class="chat-topbar tech-scan scan-always">
        <span class="status-light" :class="(qaStore.isStreaming || qaStore.isLoading) ? 'is-warn' : 'is-on'"></span>
        <span class="tech-label topbar-title">AI 法律顾问 · 会话进行中</span>
        <div class="topbar-line"></div>
        <span class="tech-label">消息</span>
        <span class="readout-box"><span class="data-readout msg-count">{{ qaStore.messages.length }}</span></span>
      </div>

      <!-- 消息列表（独立内滚） -->
      <div class="message-list" ref="messageListRef">
        <!-- ==================== 欢迎空状态 ==================== -->
        <div v-if="qaStore.messages.length === 0" class="welcome-area">
          <!-- 装饰性粒子/光点背景 -->
          <div class="welcome-particles">
            <div v-for="i in 12" :key="i" class="particle" :class="'particle-' + i"></div>
          </div>

          <div class="welcome-hero">
            <!-- 鎏金天平线稿徽记 -->
            <div class="welcome-hex hex-badge hex-ghost">
              <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
                <g stroke="#b7791f" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="32" cy="11" r="2.5" fill="#b7791f" stroke="none"/>
                  <path d="M32 14V52"/>
                  <path d="M14 20H50"/>
                  <path d="M14 20L6 33M14 20L22 33"/>
                  <path d="M6 33Q14 42 22 33"/>
                  <path d="M50 20L42 33M50 20L58 33"/>
                  <path d="M42 33Q50 42 58 33"/>
                  <path d="M21 52H43"/>
                  <path d="M26 57H38"/>
                </g>
              </svg>
            </div>
            <!-- 衬线渐变欢迎语 + 欢迎描述 -->
            <h2 class="gradient-title">欢迎使用智法通法律问答</h2>
            <p class="welcome-desc">
              <span>{{ typewriterText }}</span>
              <span v-if="showTypingCursor" class="typing-cursor">|</span>
            </p>
          </div>

          <!-- 推荐问题：科技框架 + hex 序号网格 -->
          <div class="suggested-wrap tech-frame">
            <div class="tech-section-header suggested-head">
              <div class="tsh-bar"></div>
              <span class="tsh-title">常见法律咨询</span>
              <div class="tsh-line"></div>
            </div>
            <div class="suggested-questions">
              <div
                v-for="(q, index) in qaStore.suggestedQuestions"
                :key="index"
                class="suggested-item stagger-item"
                :style="{ animationDelay: 0.6 + index * 0.1 + 's' }"
                @click="handleSuggestedQuestion(q)"
              >
                <span class="q-hex hex-badge hex-ghost">{{ String(index + 1).padStart(2, '0') }}</span>
                <span class="q-text">{{ q }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- ==================== 消息流：元数据行 + 气泡体 + 操作行 ==================== -->
        <div
          v-for="(msg, index) in qaStore.messages"
          :key="msg.id"
          class="message-item message-stagger"
          :class="msg.role"
          :style="{ animationDelay: Math.min(index * 0.05, 0.5) + 's' }"
        >
          <div class="msg-column">
            <!-- 头部元数据行：hex 徽章 + 角色名 + 置信度读出 -->
            <div class="msg-meta-row">
              <template v-if="msg.role === 'assistant'">
                <span class="hex-badge hex-ghost msg-hex">AI</span>
                <span class="msg-name">智法通法律顾问</span>
                <span v-if="msg.isStreaming" class="streaming-chip tech-label">生成中</span>
                <!-- 置信度指示器（原绑定迁移） -->
                <div
                  v-if="msg.role === 'assistant' && msg.confidence !== null && msg.confidence !== undefined"
                  class="confidence-bar enhanced-confidence"
                >
                  <span class="confidence-label">置信度</span>
                  <div class="confidence-track">
                    <div
                      class="confidence-fill"
                      :class="{ 'low-confidence-pulse': msg.confidence < 0.6 }"
                      :style="{
                        width: Math.round(msg.confidence * 100) + '%',
                        background: getConfidenceGradient(msg.confidence),
                      }"
                    ></div>
                  </div>
                  <span class="confidence-value" :style="{ color: getConfidenceColor(msg.confidence) }">
                    {{ Math.round(msg.confidence * 100) }}%
                  </span>
                </div>
              </template>
              <template v-else>
                <span class="msg-name user-name">咨询者</span>
                <span class="hex-badge hex-cyan msg-hex"><el-icon :size="12"><User /></el-icon></span>
              </template>
            </div>

            <!-- 气泡体（markdown 渲染容器类名与 v-html 原样保留） -->
            <div class="msg-bubble">
              <div
                class="message-content"
                :class="{ 'content-reveal': !msg.isStreaming }"
                v-html="renderMessageContent(msg)"
              ></div>
              <span v-if="msg.isStreaming" class="streaming-cursor">▊</span>
            </div>

            <!-- ==================== 法条引用（原逻辑迁移） ==================== -->
            <div
              v-if="msg.role === 'assistant' && msg.citations"
              class="citations enhanced-citations"
            >
              <div class="citations-header" @click="toggleCitation(msg.id)">
                <span class="diamond-node node-gold cite-node"></span>
                <span>引用来源</span>
                <span class="cite-count tech-label">{{ parseCitations(msg.citations).length }} 条</span>
                <!-- 展开/折叠箭头 -->
                <span class="collapse-arrow" :class="{ expanded: isCitationExpanded(msg.id) }"></span>
              </div>
              <!-- 展开/折叠动画 -->
              <transition name="citation-expand">
                <div v-show="isCitationExpanded(msg.id)" class="citation-items">
                  <div
                    v-for="(cite, idx) in parseCitations(msg.citations)"
                    :key="idx"
                    class="citation-item"
                    :class="{ 'cite-highlight': idx < 2 }"
                    @click="handleCitationClick(cite)"
                  >
                    <!-- 引用序号：终端读出形态 -->
                    <span class="cite-index glow-index">[{{ idx + 1 }}]</span>
                    <!-- 引用标题（兼容 document_title/law_name/title 多种字段） -->
                    <span class="cite-title underline-animate">{{ cite.document_title || cite.law_name || cite.title || `来源${idx + 1}` }}</span>
                    <!-- 相似度分数（如有） -->
                    <span v-if="cite.score != null" class="cite-score">相似度 {{ Math.round(cite.score * 100) }}%</span>
                    <el-icon class="cite-link-icon" :size="12"><Link /></el-icon>
                  </div>
                </div>
              </transition>
            </div>

            <!-- 底部操作行（原有反馈/复制按钮保留） -->
            <div v-if="msg.role === 'assistant' && !msg.isStreaming" class="message-actions">
              <el-tooltip content="有用" placement="top">
                <el-button
                  :type="msg.feedback === 'positive' ? 'primary' : 'default'"
                  :size="'small'"
                  circle
                  @click="handleFeedback(msg.id, true)"
                >
                  <el-icon><Select /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="无用" placement="top">
                <el-button
                  :type="msg.feedback === 'negative' ? 'danger' : 'default'"
                  :size="'small'"
                  circle
                  @click="handleFeedback(msg.id, false)"
                >
                  <el-icon><CloseBold /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="复制" placement="top">
                <el-button size="small" circle @click="copyMessage(msg.content)">
                  <el-icon><CopyDocument /></el-icon>
                </el-button>
              </el-tooltip>
            </div>

            <!-- AI生成内容合规提示（满足《生成式AI服务管理暂行办法》合规要求） -->
            <div v-if="msg.role === 'assistant' && !msg.isStreaming" class="ai-content-label">
              <el-icon :size="12"><WarningFilled /></el-icon>
              <span>本回答由AI生成，仅供普法参考，不构成律师正式法律意见，重大法律事项建议咨询执业律师。</span>
            </div>
          </div>
        </div>

        <!-- ==================== 加载中：三色光点打字指示器 ==================== -->
        <div v-if="qaStore.isLoading" class="message-item assistant">
          <div class="msg-column">
            <div class="msg-meta-row">
              <span class="hex-badge hex-ghost msg-hex">AI</span>
              <span class="msg-name">智法通法律顾问</span>
            </div>
            <div class="msg-bubble">
              <div class="typing-indicator enhanced-typing">
                <div class="typing-dots">
                  <span></span><span></span><span></span>
                </div>
                <span class="typing-text">AI正在思考...</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ==================== 输入区：指挥控制台形态 ==================== -->
      <div class="input-area">
        <div class="console-shell corner-brackets" :class="{ 'console-active': inputFocused }">
          <!-- 控制台头部：状态灯 + 通道标识 + 按键提示 -->
          <div class="console-head">
            <span class="status-light" :class="(qaStore.isStreaming || qaStore.isLoading) ? 'is-warn' : 'is-on'"></span>
            <span class="tech-label console-title">咨询输入</span>
            <div class="console-head-line"></div>
            <span class="tech-label console-tip">Enter 发送 · Shift+Enter 换行</span>
          </div>
          <!-- 指令输入主体 -->
          <div class="console-body">
            <el-input
              v-model="inputText"
              type="textarea"
              :autosize="{ minRows: 1, maxRows: 4 }"
              placeholder="输入您的法律问题..."
              :disabled="qaStore.isStreaming || qaStore.isLoading"
              @keydown.enter.exact="handleSend"
              @focus="inputFocused = true"
              @blur="inputFocused = false"
            />
            <!-- 发送按钮：渐变发光形态（保留 disabled/loading/脉冲逻辑） -->
            <el-button
              type="primary"
              :icon="Promotion"
              circle
              :loading="qaStore.isStreaming || qaStore.isLoading"
              :disabled="!inputText.trim()"
              @click="handleSend"
              class="send-btn"
              :class="{ 'send-pulse': inputText.trim() && !qaStore.isStreaming && !qaStore.isLoading }"
            />
          </div>
        </div>
      </div>
    </section>

    <!-- ==================== 引用来源内容查看对话框 ==================== -->
    <el-dialog
      v-model="showCitationDialog"
      :title="currentCitation?.document_title || currentCitation?.law_name || currentCitation?.title || '引用来源详情'"
      width="640px"
      top="8vh"
      destroy-on-close
      class="citation-dialog"
    >
      <div v-if="currentCitation" class="citation-detail">
        <!-- 区块头 -->
        <div class="tech-section-header cite-detail-header">
          <div class="tsh-bar"></div>
          <span class="tsh-title">引用来源</span>
          <div class="tsh-line"></div>
          <span class="tsh-extra tech-label">法条档案</span>
        </div>
        <!-- 引用元信息条（原绑定迁移） -->
        <div class="citation-meta-bar">
          <span v-if="currentCitation.doc_type" class="meta-chip">
            <el-icon :size="12"><Collection /></el-icon>
            {{ currentCitation.doc_type }}
          </span>
          <span v-if="currentCitation.effectiveness" class="meta-chip meta-chip-success">
            <el-icon :size="12"><CircleCheckFilled /></el-icon>
            {{ currentCitation.effectiveness }}
          </span>
          <span v-if="currentCitation.document_id" class="meta-chip">
            <el-icon :size="12"><Document /></el-icon>
            文档ID：{{ currentCitation.document_id }}
          </span>
          <span v-if="currentCitation.score != null" class="meta-chip meta-chip-score">
            <el-icon :size="12"><DataLine /></el-icon>
            相似度 {{ Math.round(currentCitation.score * 100) }}%
          </span>
        </div>
        <!-- 引用正文：角括号容器 -->
        <div class="citation-content-box corner-brackets">
          <div class="content-label">
            <el-icon :size="14"><Reading /></el-icon>
            <span>引用内容</span>
          </div>
          <div class="citation-content-text">
            {{ currentCitation.content || '该引用来源暂无可展示的文本内容。' }}
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useQAStore } from '@/stores/qa'
import { useUserStore } from '@/stores/user'
import { qaApi } from '@/api/qa'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Promotion } from '@element-plus/icons-vue'
import { renderMarkdown } from '@/utils/markdown'

const qaStore = useQAStore()
const userStore = useUserStore()
const inputText = ref('')
const messageListRef = ref<HTMLElement>()

// ==================== 对话重命名功能 ====================
const renamingId = ref<number | null>(null)       // 当前正在重命名的对话ID
const renamingTitle = ref('')                       // 重命名输入框中的标题
const renameInputRef = ref<HTMLInputElement>()      // 重命名输入框引用

/** 开始重命名：将对话标题填入输入框并聚焦 */
const startRename = (conv: any) => {
  renamingId.value = conv.id
  renamingTitle.value = conv.title || '新对话'
  // 等待DOM更新后聚焦输入框
  nextTick(() => {
    renameInputRef.value?.focus()
    renameInputRef.value?.select()
  })
}

/** 确认重命名：调用API更新对话标题 */
const confirmRename = async () => {
  if (renamingId.value === null) return
  const newTitle = renamingTitle.value.trim()
  const convId = renamingId.value
  renamingId.value = null

  // 标题为空或未修改则取消
  if (!newTitle) {
    ElMessage.warning('对话标题不能为空')
    return
  }
  const conv = qaStore.conversations.find((c: any) => c.id === convId)
  if (conv && conv.title === newTitle) return

  try {
    await qaApi.renameConversation(convId, newTitle)
    // 更新本地store中的对话标题
    if (conv) conv.title = newTitle
    ElMessage.success('对话已重命名')
  } catch {
    ElMessage.error('重命名失败，请重试')
  }
}

/** 取消重命名 */
const cancelRename = () => {
  renamingId.value = null
  renamingTitle.value = ''
}

// ==================== 今日问答额度提示 ====================
// 今日剩余咨询次数：数据来源改为后端响应，不再使用localStorage存储（防止用户篡改）
// 默认值20，onMounted时尝试从后端获取真实额度，发送问答时通过响应头实时更新
const remainingQaQuota = ref(20)

/**
 * 从后端获取今日剩余咨询额度
 * 调用 /qa/quota 端点查询用户当前剩余问答次数
 * 若后端暂未实现该端点，保留默认值20，后续通过问答响应头 X-RateLimit-Remaining 更新
 */
const fetchQuotaFromBackend = async () => {
  try {
    const data = await qaApi.getQuota()
    // 后端返回剩余次数时更新前端显示
    if (data.remaining !== undefined && data.remaining !== null) {
      remainingQaQuota.value = data.remaining
    }
  } catch {
    // 后端暂无额度查询端点，保留默认值，不阻断功能
    // 实际额度将在发送问答请求时通过 X-RateLimit-Remaining 响应头获取
  }
}

// ==================== 增强功能：打字机效果 ====================
const fullWelcomeText = '我是您的AI法律顾问，可以为您解答法律问题、分析合同风险、检索法律条文。'
const typewriterText = ref('')
const showTypingCursor = ref(true)
let typewriterTimer: ReturnType<typeof setInterval> | null = null
let typewriterHideCursorTimer: ReturnType<typeof setTimeout> | null = null

/** 启动打字机效果 - 逐字显示欢迎描述文字 */
const startTypewriter = () => {
  let index = 0
  typewriterTimer = setInterval(() => {
    if (index < fullWelcomeText.length) {
      typewriterText.value += fullWelcomeText[index]
      index++
    } else {
      if (typewriterTimer) clearInterval(typewriterTimer)
      // 打字完成后延迟隐藏光标（保存timer引用以便卸载时清理）
      typewriterHideCursorTimer = setTimeout(() => { showTypingCursor.value = false }, 1500)
    }
  }, 50)
}

// ==================== 增强功能：法条引用展开/折叠 ====================
const expandedCitations = reactive<Record<number, boolean>>({})

/** 判断引用区域是否展开（默认展开） */
const isCitationExpanded = (msgId: number) => expandedCitations[msgId] !== false

/** 切换引用区域展开/折叠状态 */
const toggleCitation = (msgId: number) => {
  expandedCitations[msgId] = !isCitationExpanded(msgId)
}

// ==================== 引用来源详情对话框 ====================
const showCitationDialog = ref(false)
const currentCitation = ref<any>(null)

/** 点击引用来源条目，弹出对话框展示引用文档内容 */
const handleCitationClick = (cite: any) => {
  if (!cite) return
  currentCitation.value = cite
  showCitationDialog.value = true
}

// ==================== 增强功能：输入框聚焦状态 ====================
const inputFocused = ref(false)

// ==================== 交互方法 ====================

// 发送消息
const handleSend = async (e?: KeyboardEvent | MouseEvent | Event) => {
  if (e) {
    // Shift+Enter换行，Enter发送
    if (e instanceof KeyboardEvent && e.shiftKey) return
    e.preventDefault()
  }

  const question = inputText.value.trim()
  if (!question || qaStore.isStreaming || qaStore.isLoading) return

  // 检查今日剩余额度（管理员不受次数限制，跳过检查）
  if (!userStore.isAdmin && remainingQaQuota.value <= 0) {
    ElMessage.warning('今日咨询次数已达上限，请明日再试或升级套餐')
    return
  }

  inputText.value = ''

  // 使用流式回答，传入额度更新回调
  // 后端通过 X-RateLimit-Remaining 响应头返回剩余次数，回调中实时更新前端显示
  // 额度用尽（429）时回调收到0，触发友好提示
  await qaStore.askQuestionStream(question, (remaining: number) => {
    // 更新剩余额度显示
    remainingQaQuota.value = remaining
    // 额度耗尽时弹出提示（429场景由store层触发此回调，remaining=0）
    // 管理员返回 remaining=-1 表示不限额度，不触发提示
    if (remaining <= 0 && !userStore.isAdmin) {
      ElMessage.warning('今日咨询次数已用完，请明日再试或升级套餐')
    }
  })

  // 滚动到底部
  await nextTick()
  scrollToBottom()
}

// 点击推荐问题
const handleSuggestedQuestion = (question: string) => {
  inputText.value = question
  handleSend()
}

// 新建对话
const handleNewChat = () => {
  qaStore.newConversation()
}

// 选择对话
const handleSelectConversation = async (id: number) => {
  await qaStore.loadMessages(id)
  await nextTick()
  scrollToBottom()
}

// 删除对话
const handleDeleteConversation = async (id: number) => {
  try {
    await ElMessageBox.confirm('确定删除此对话？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await qaStore.deleteConversation(id)
  } catch {
    // 用户取消
  }
}

// 提交反馈
const handleFeedback = (messageId: number, isPositive: boolean) => {
  qaStore.submitFeedback(messageId, isPositive)
}

// 复制消息
const copyMessage = async (content: string) => {
  try {
    await navigator.clipboard.writeText(content)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败')
  }
}

// ==================== 渲染辅助方法 ====================

// 渲染消息内容（完整 Markdown 渲染 + 法条引用高亮 + XSS 净化）
const renderMessageContent = (msg: any) => {
  if (!msg.content) return ''
  // 流式输出时也使用 markdown 渲染，保证实时格式化
  return renderMarkdown(msg.content)
}

// 解析引用来源
const parseCitations = (citations: string | null | undefined) => {
  if (!citations) return []
  try {
    return JSON.parse(citations)
  } catch {
    return []
  }
}

// 获取置信度颜色（庄重语义色：鼠尾草绿=高 / 琥珀=中 / 砖红=低）
const getConfidenceColor = (confidence: number) => {
  if (confidence >= 0.8) return '#7ca586'
  if (confidence >= 0.6) return '#c9973f'
  return '#c05b52'
}

/** 获取置信度进度条底色 - 语义色静态呈现 */
const getConfidenceGradient = (confidence: number) => {
  if (confidence >= 0.8) return 'linear-gradient(90deg, #688e72, #7ca586)'
  if (confidence >= 0.6) return 'linear-gradient(90deg, #a67c33, #c9973f)'
  return 'linear-gradient(90deg, #a04a43, #c05b52)'
}

// 滚动到底部
const scrollToBottom = () => {
  if (messageListRef.value) {
    messageListRef.value.scrollTop = messageListRef.value.scrollHeight
  }
}

// 监听消息变化，自动滚动
watch(
  () => qaStore.messages.length,
  () => nextTick(scrollToBottom)
)

// ==================== 生命周期 ====================
onMounted(() => {
  qaStore.loadConversations()
  // 从后端获取推荐问题，失败时保留默认问题
  qaStore.fetchSuggestedQuestions()
  // 从后端获取今日剩余咨询额度（替代localStorage，防止用户篡改）
  fetchQuotaFromBackend()
  // 启动欢迎文字打字机效果
  startTypewriter()
})

onUnmounted(() => {
  // 清理打字机定时器（interval + timeout）
  if (typewriterTimer) clearInterval(typewriterTimer)
  if (typewriterHideCursorTimer) clearTimeout(typewriterHideCursorTimer)
})
</script>

<style scoped lang="scss">
/* ==================================================================
   页面骨架：网格底纹层 + 双栏结构
   结构约束：精确填满父容器（.content：flex:1 + padding:24px），
   不依赖视口计算，确保左侧会话栏固定不随页面滚动、消息区独立内滚
   ================================================================== */
.qa-page {
  position: relative;
  display: flex;
  height: calc(100% + 48px); /* 内容区上下各24px padding，撑满抵消 */
  margin: -24px;
  overflow: hidden;
  background: var(--bg-primary);
}

/* 左右两栏浮于网格纹理层之上 */
.conv-rail,
.chat-area {
  position: relative;
  z-index: 1;
}

/* ==================================================================
   左侧会话档案栏
   ================================================================== */
.conv-rail {
  width: 280px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.97), rgba(244, 247, 251, 0.99));
  border-right: 1px solid var(--border-color);
}

/* 顶部区块头 + 额度读出 */
.rail-head {
  padding: 16px 14px 12px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex-shrink: 0;
}

/* 新建对话按钮：素净金描边圆形 + 号 */
.new-chat-hex {
  width: 26px;
  height: 26px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: 1px solid rgba(201, 169, 98, 0.55);
  border-radius: 50%;
  cursor: pointer;
  color: var(--accent-color);
  background: transparent;
  transition: background 0.25s ease, border-color 0.25s ease, color 0.25s ease;

  &:hover {
    background: rgba(201, 169, 98, 0.12);
    border-color: rgba(201, 169, 98, 0.85);
    color: var(--accent-light);
  }
}

/* 额度读出行：状态灯 + 衬线金数值读出 */
.quota-readout {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 5px 8px;
  background: rgba(201, 169, 98, 0.05);
  border-left: 2px solid rgba(201, 169, 98, 0.45);

  .quota-icon {
    color: var(--accent-color);
    margin-left: 2px;
  }

  .quota-val {
    font-size: 14px;
    color: #d99b3d;
  }

  .quota-unit {
    font-size: 10px;
    color: var(--text-muted);
    margin-left: 4px;
  }
}

/* 会话列表 */
.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px 8px;
}

/* 列表项交错入场动画 */
.stagger-item {
  opacity: 0;
  animation: staggerIn 0.4s ease forwards;
}

@keyframes staggerIn {
  from {
    opacity: 0;
    transform: translateX(-10px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

/* 会话项：圆点节点 + 标题/时间 + hover 操作 */
.conv-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 8px 9px 14px;
  margin-bottom: 3px;
  cursor: pointer;
  color: var(--text-secondary);
  background: transparent;
  border-left: 2px solid rgba(148, 158, 178, 0.14);
  transition: all 0.3s var(--ease-smooth);

  &:hover {
    background: rgba(201, 169, 98, 0.06);
    border-left-color: rgba(201, 169, 98, 0.4);
    color: var(--text-primary);

    .conv-actions {
      opacity: 1;
    }
  }

  /* 活跃会话：左侧 2px 金竖线 + 象牙白文字 + 背景微金 */
  &.active {
    background: rgba(201, 169, 98, 0.09);
    border-left-color: var(--accent-color);
    color: var(--text-primary);

    .conv-title {
      color: var(--text-primary);
    }
  }

  .conv-node {
    width: 8px;
    height: 8px;
  }

  .conv-main {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .conv-title {
    font-size: 13px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.3;
  }

  /* 相对时间：等宽暖灰小字 */
  .conv-time {
    font-family: 'Consolas', 'SF Mono', 'Courier New', monospace;
    font-size: 10px;
    letter-spacing: 0.8px;
    color: var(--text-muted);
    font-variant-numeric: tabular-nums;
  }

  /* 重命名输入框 */
  .conv-rename-input {
    height: 26px;
    padding: 0 8px;
    font-size: 13px;
    color: var(--text-primary);
    background: rgba(28, 35, 50, 0.85);
    border: 1px solid rgba(201, 169, 98, 0.55);
    border-radius: 3px;
    outline: none;

    &:focus {
      box-shadow: 0 0 0 2px rgba(201, 169, 98, 0.15);
    }
  }

  /* 操作按钮组：重命名 + 删除（hover 浮现） */
  .conv-actions {
    display: flex;
    align-items: center;
    gap: 5px;
    opacity: 0;
    transition: opacity 0.2s ease;
  }

  .conv-rename {
    color: var(--text-muted);
    cursor: pointer;
    transition: all 0.2s ease;

    &:hover {
      color: var(--accent-light);
    }
  }

  .conv-delete {
    color: var(--text-muted);
    cursor: pointer;
    transition: all 0.2s ease;

    &:hover {
      color: var(--danger-color);
    }
  }
}

/* 活跃会话左侧金竖线（激活态由 conv-item 的 border-left 呈现，此覆盖层肃穆化隐藏） */
.active-glow-bar {
  display: none;
}

/* 空状态：圆形金徽形态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: var(--text-muted);

  .empty-hex {
    width: 44px;
    height: 44px;

    svg {
      width: 24px;
      height: 24px;
    }
  }

  .empty-title {
    font-size: 13px;
    margin-top: 12px;
    color: var(--text-secondary);
  }

  .empty-hint {
    font-size: 11px;
    margin-top: 4px;
    color: var(--text-muted);
  }
}

/* ==================================================================
   右侧通讯主区
   ================================================================== */
.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  /* 墨蓝面板底（透出页面纸纹肌理） */
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.28), transparent 260px);
}

/* 顶部会话信息条 */
.chat-topbar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  padding: 11px 22px;
  border-bottom: 1px solid var(--border-color);
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);

  .topbar-title {
    color: var(--text-secondary);
  }

  .topbar-line {
    flex: 1;
    height: 1px;
    min-width: 24px;
    background: linear-gradient(90deg, rgba(201, 169, 98, 0.35), rgba(201, 169, 98, 0.1), transparent);
  }

  .msg-count {
    font-size: 13px;
    color: #d99b3d;
  }
}

/* ==================================================================
   消息列表（独立内滚）
   ================================================================== */
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 26px 28px;
}

/* ==================================================================
   欢迎空状态：hex 大徽章 + 渐变欢迎语 + 推荐问题网格
   ================================================================== */
.welcome-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  padding: 40px 24px;
  position: relative;
  overflow: hidden;
}

.welcome-hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  z-index: 1;
  margin-bottom: 34px;
}

/* 鎏金天平线稿徽记（圆形素净金环徽记） */
.welcome-hex {
  width: 96px;
  height: 96px;
  margin-bottom: 22px;
  animation: welcomeFadeIn 0.5s ease both;

  svg {
    width: 52px;
    height: 52px;
  }
}

@keyframes welcomeFadeIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 衬线渐变欢迎语 */
.gradient-title {
  font-family: var(--font-serif);
  font-size: 22px;
  font-weight: 600;
  letter-spacing: 3px;
  margin-bottom: 10px;
  background: var(--gradient-text);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* 打字机描述 */
.welcome-desc {
  font-size: 14px;
  color: var(--text-secondary);
  max-width: 480px;
  min-height: 22px;
  line-height: 1.6;
}

/* 打字机彩色光标（肃穆化：隐藏，保留 DOM 结构） */
.typing-cursor {
  display: none;
}

/* 装饰光点背景（肃穆化：隐藏，保留 DOM 结构） */
.welcome-particles {
  display: none;
}

/* 推荐问题：科技框架容器 + hex 序号网格 */
.suggested-wrap {
  width: 100%;
  max-width: 640px;
  padding: 16px 18px 18px;
  position: relative;
  z-index: 1;

  .suggested-head {
    margin-bottom: 12px;
  }
}

/* 推荐问题：素净面板容器 + 衬线金序号网格 */
.suggested-questions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.suggested-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 13px;
  background: rgba(28, 35, 50, 0.6);
  border: 1px solid var(--border-color);
  border-left: 2px solid rgba(201, 169, 98, 0.4);
  cursor: pointer;
  font-size: 13px;
  color: var(--text-secondary);
  text-align: left;
  transition: border-color 0.3s ease, background 0.3s ease, color 0.3s ease;

  /* 序号：衬线金 */
  .q-hex {
    width: 26px;
    height: 26px;
    font-size: 11px;
    letter-spacing: 1px;
    font-family: var(--font-serif);
  }

  .q-text {
    flex: 1;
    min-width: 0;
    line-height: 1.5;
  }

  /* 素净金线 hover 提亮 */
  &:hover {
    border-color: rgba(201, 169, 98, 0.55);
    border-left-color: var(--accent-color);
    color: var(--accent-light);
    background: rgba(201, 169, 98, 0.07);
  }
}

/* ==================================================================
   消息流：元数据行 + 气泡体 + 操作行
   ================================================================== */
/* 消息交错入场动画 */
.message-stagger {
  animation: messageSlideIn 0.3s ease-out both;
}

@keyframes messageSlideIn {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-item {
  margin-bottom: 24px;

  /* 用户消息：右对齐 */
  &.user {
    .msg-column {
      align-items: flex-end;
    }
  }
}

/* 消息主列 */
.msg-column {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  max-width: 78%;
}

/* 头部元数据行 */
.msg-meta-row {
  display: flex;
  align-items: center;
  gap: 9px;
  min-height: 30px;

  .msg-hex {
    width: 26px;
    height: 26px;
    font-size: 10px;
    letter-spacing: 0.5px;
  }

  .msg-name {
    font-size: 12px;
    letter-spacing: 1px;
    font-family: var(--font-serif);
    color: var(--text-secondary);
    white-space: nowrap;
  }

  .user-name {
    color: var(--text-secondary);
  }

  /* 流式生成中小标（静态琥珀） */
  .streaming-chip {
    color: var(--warning-color);
  }
}

/* 气泡体 */
.msg-bubble {
  display: flex;
  flex-direction: column;
  position: relative;
}

/* 消息内容（markdown 渲染容器，类名保留） */
.message-content {
  position: relative;
  padding: 13px 16px;
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-primary);
  word-break: break-word;

  /* 非流式消息淡入显示 */
  &.content-reveal {
    animation: contentReveal 0.3s ease-out;
  }

  /* 法条引用高亮样式 */
  :deep(.law-citation) {
    color: var(--accent-light);
    font-weight: 600;
    background: rgba(201, 169, 98, 0.12);
    padding: 1px 4px;
    border-radius: 3px;
  }

  /* ==================== Markdown 渲染元素样式 ==================== */
  :deep(h1), :deep(h2), :deep(h3), :deep(h4), :deep(h5), :deep(h6) {
    color: var(--text-primary);
    font-family: var(--font-serif);
    font-weight: 700;
    margin: 12px 0 8px;
    line-height: 1.4;
    padding-left: 10px;
    border-left: 3px solid var(--accent-color);
  }
  :deep(h1) { font-size: 20px; }
  :deep(h2) { font-size: 18px; }
  :deep(h3) { font-size: 16px; }
  :deep(h4) { font-size: 15px; }
  :deep(h5), :deep(h6) { font-size: 14px; }

  :deep(p) {
    margin: 0 0 10px;
    &:last-child { margin-bottom: 0; }
  }

  :deep(strong), :deep(b) {
    color: var(--accent-light);
    font-weight: 700;
  }
  :deep(em), :deep(i) { color: var(--text-primary); font-style: italic; }
  :deep(del), :deep(s) { color: var(--text-muted); }
  :deep(mark) {
    background: rgba(201, 169, 98, 0.25);
    color: var(--text-primary);
    padding: 0 4px;
    border-radius: 3px;
  }

  :deep(ul), :deep(ol) {
    margin: 6px 0 10px;
    padding-left: 22px;
    li {
      margin: 3px 0;
      line-height: 1.7;
    }
  }
  :deep(ul li::marker) { color: var(--accent-color); }
  :deep(ol li::marker) { color: var(--accent-color); font-weight: 600; }

  :deep(blockquote) {
    margin: 8px 0;
    padding: 8px 14px;
    border-left: 3px solid var(--accent-color);
    background: rgba(201, 169, 98, 0.06);
    border-radius: 0 6px 6px 0;
    color: var(--text-secondary);
    p { margin: 0; }
  }

  :deep(code) {
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
    font-size: 13px;
    padding: 1px 6px;
    background: rgba(148, 158, 178, 0.14);
    color: #d99b3d;
    border-radius: 4px;
  }

  :deep(pre) {
    margin: 8px 0;
    padding: 12px 14px;
    background: rgba(244, 247, 251, 0.85);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    overflow-x: auto;
    code {
      background: transparent;
      color: #172033;
      padding: 0;
      font-size: 13px;
      line-height: 1.6;
    }
  }

  :deep(a) {
    color: var(--accent-color);
    text-decoration: underline;
    text-decoration-color: rgba(201, 169, 98, 0.45);
    text-underline-offset: 3px;
    transition: color 0.2s ease;
    &:hover {
      color: var(--accent-light);
      text-decoration-color: var(--accent-light);
    }
  }

  :deep(hr) {
    margin: 12px 0;
    border: none;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(201, 169, 98, 0.45), transparent);
  }

  :deep(table) {
    width: 100%;
    margin: 8px 0;
    border-collapse: collapse;
    font-size: 13px;
    th, td {
      padding: 8px 12px;
      border: 1px solid var(--border-color);
      text-align: left;
    }
    th {
      background: rgba(28, 35, 50, 0.9);
      color: var(--accent-light);
      font-family: var(--font-serif);
      font-weight: 600;
    }
    tbody tr:nth-child(odd) {
      background: rgba(148, 158, 178, 0.04);
    }
    tbody tr:hover {
      background: rgba(201, 169, 98, 0.06);
    }
  }

  :deep(img) {
    max-width: 100%;
    border-radius: 6px;
    margin: 6px 0;
  }
}

/* 用户消息：深藏青底 + 金色细边 + 象牙白文字 */
.message-item.user {
  .message-content {
    background: linear-gradient(135deg, #2f6fed, #5b91f2);
    border: 1px solid rgba(201, 169, 98, 0.35);
    border-radius: 6px;
    color: var(--text-primary);

    /* 用户气泡内强调色适配（藏青底象牙白字） */
    :deep(strong), :deep(b) {
      color: #fff;
    }
    :deep(code) {
      background: rgba(244, 247, 251, 0.4);
      color: #172033;
    }
    :deep(a) {
      color: #d99b3d;
      text-decoration-color: rgba(220, 196, 137, 0.5);
    }
  }
}

/* AI 消息：素净面板底 + 左侧 2px 金竖线 */
.message-item.assistant {
  .message-content {
    background: rgba(28, 35, 50, 0.75);
    border: 1px solid var(--border-color);
    border-radius: 6px;

    &::before {
      content: '';
      position: absolute;
      left: 0;
      top: 0;
      bottom: 0;
      width: 2px;
      background: var(--accent-color);
      border-radius: 6px 0 0 6px;
    }
  }
}

/* 消息内容淡入动画 */
@keyframes contentReveal {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

/* ==================================================================
   置信度读出（元数据行内的紧凑 chip 形态）
   ================================================================== */
.confidence-bar {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 3px 10px;
  background: rgba(28, 35, 50, 0.7);
  border: 1px solid var(--border-color);
  border-radius: 3px;

  .confidence-label {
    font-size: 10px;
    letter-spacing: 1.5px;
    color: var(--text-muted);
    white-space: nowrap;
  }

  .confidence-track {
    width: 68px;
    height: 4px;
    background: rgba(148, 158, 178, 0.16);
    border-radius: 2px;
    overflow: hidden;
    position: relative;
  }

  /* 置信度进度：语义色静态填充 */
  .confidence-fill {
    height: 100%;
    transition: width 0.5s ease;
    border-radius: 2px;
  }

  .confidence-value {
    font-size: 11px;
    font-weight: 600;
    min-width: 34px;
    text-align: right;
    font-variant-numeric: tabular-nums;
    transition: color 0.3s ease;
  }
}

/* ==================================================================
   法条引用（消息内嵌面板）
   ================================================================== */
.citations {
  position: relative;
  border: 1px solid var(--border-color);
  background: rgba(255, 255, 255, 0.65);
  padding: 8px 12px;
  width: 100%;
  border-radius: 4px;

  .citations-header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    letter-spacing: 1px;
    color: var(--text-secondary);
    cursor: pointer;
    user-select: none;

    .cite-node {
      width: 8px;
      height: 8px;
    }

    .cite-count {
      color: var(--accent-light);
    }

    &:hover {
      color: var(--accent-light);
    }
  }

  .citation-items {
    display: flex;
    flex-direction: column;
    gap: 5px;
    margin-top: 7px;
  }

  .citation-item {
    font-size: 12px;
    color: var(--text-secondary);
    display: flex;
    gap: 8px;
    align-items: center;
    padding: 6px 10px;
    background: rgba(244, 247, 251, 0.5);
    border: 1px solid var(--border-color);
    border-left: 2px solid rgba(201, 169, 98, 0.4);
    border-radius: 3px;
    cursor: pointer;
    transition: background 0.25s ease, border-color 0.25s ease, color 0.25s ease;

    &:hover {
      background: rgba(201, 169, 98, 0.07);
      border-left-color: var(--accent-color);
      color: var(--text-primary);

      .cite-link-icon {
        color: var(--accent-color);
      }
    }

    /* 前2条引用重点突出 */
    &.cite-highlight {
      background: rgba(201, 169, 98, 0.06);
      border-color: rgba(201, 169, 98, 0.3);
      border-left-color: rgba(201, 169, 98, 0.65);
    }

    .cite-title {
      flex: 1;
      min-width: 0;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      cursor: pointer;
      &:hover { color: var(--accent-light); }
    }

    /* 相似度分数（衬线金数据） */
    .cite-score {
      font-size: 11px;
      color: var(--accent-light);
      padding: 1px 6px;
      background: rgba(201, 169, 98, 0.08);
      border: 1px solid rgba(201, 169, 98, 0.25);
      border-radius: 3px;
      white-space: nowrap;
    }

    .cite-link-icon {
      color: var(--text-muted);
      transition: color 0.25s ease;
    }
  }
}

/* 引用序号：衬线金 */
.glow-index {
  font-family: var(--font-serif);
  color: var(--accent-color) !important;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

/* 引用标题下划线动画 */
.underline-animate {
  position: relative;
  display: inline-block;

  &::after {
    content: '';
    position: absolute;
    bottom: -1px;
    left: 0;
    width: 0;
    height: 1px;
    background: var(--accent-color);
    transition: width 0.3s ease;
  }

  &:hover::after {
    width: 100%;
  }
}

/* 展开/折叠箭头 */
.collapse-arrow {
  display: inline-block;
  width: 0;
  height: 0;
  border-left: 5px solid currentColor;
  border-top: 4px solid transparent;
  border-bottom: 4px solid transparent;
  margin-left: auto;
  transition: transform 0.3s ease;

  &.expanded {
    transform: rotate(90deg);
  }
}

/* 引用区域展开/折叠过渡动画 */
.citation-expand-enter-active,
.citation-expand-leave-active {
  transition: all 0.3s ease;
  overflow: hidden;
}

.citation-expand-enter-from,
.citation-expand-leave-to {
  opacity: 0;
  max-height: 0;
  margin-top: 0;
}

.citation-expand-enter-to,
.citation-expand-leave-from {
  opacity: 1;
  max-height: 200px;
  margin-top: 6px;
}

/* ==================================================================
   底部操作行 + 合规提示
   ================================================================== */
.message-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  opacity: 0;
  transition: opacity 0.2s ease;

  .message-item:hover & {
    opacity: 1;
  }

  :deep(.el-button) {
    background: rgba(28, 35, 50, 0.6);
  }
}

/* AI生成内容合规提示 */
.ai-content-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--warning-color);
  padding: 5px 10px;
  background: rgba(201, 151, 63, 0.07);
  border: 1px solid rgba(201, 151, 63, 0.22);
  border-left: 2px solid var(--warning-color);
  user-select: none;
  line-height: 1.5;

  .el-icon {
    color: var(--warning-color);
    flex-shrink: 0;
  }

  span {
    flex: 1;
  }
}

/* 流式光标（肃穆化：隐藏彩色光标动画） */
.streaming-cursor {
  display: none;
}

/* ==================================================================
   打字指示器（暖灰小点）
   ================================================================== */
.typing-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
}

.enhanced-typing {
  .typing-dots {
    display: flex;
    gap: 4px;

    /* 三个暖灰小点轻微起伏（opacity 起伏） */
    span {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--text-secondary);
      animation: typingFade 1.4s ease-in-out infinite;

      &:nth-child(2) {
        animation-delay: 0.18s;
      }
      &:nth-child(3) {
        animation-delay: 0.36s;
      }
    }
  }

  .typing-text {
    font-size: 12px;
    color: var(--text-muted);
  }
}

@keyframes typingFade {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 1; }
}

/* ==================================================================
   输入区：素净输入面板
   ================================================================== */
.input-area {
  flex-shrink: 0;
  padding: 14px 24px 18px;
  border-top: 1px solid var(--border-color);
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  position: relative;

  /* 顶部鎏金细线分界 */
  &::before {
    content: '';
    position: absolute;
    top: -1px;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(201, 169, 98, 0.5), transparent);
    opacity: 0.6;
    pointer-events: none;
  }
}

/* 输入面板外壳：素净面板 */
.console-shell {
  position: relative;
  max-width: 880px;
  margin: 0 auto;
  border: 1px solid var(--border-color);
  background: rgba(28, 35, 50, 0.75);
  border-radius: 6px;
  padding: 10px 16px 12px;
  transition: border-color 0.3s ease;

  /* 聚焦/生成中：金线点亮 */
  &.console-active {
    border-color: var(--border-strong);
  }
}

/* 输入面板头部 */
.console-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-bottom: 8px;
  margin-bottom: 8px;
  border-bottom: 1px dashed rgba(148, 158, 178, 0.16);

  .console-title {
    color: var(--text-secondary);
  }

  .console-head-line {
    flex: 1;
    height: 1px;
    min-width: 24px;
    background: linear-gradient(90deg, rgba(201, 169, 98, 0.3), transparent);
  }
}

/* 指令输入主体 */
.console-body {
  display: flex;
  align-items: flex-end;
  gap: 10px;

  :deep(.el-textarea) {
    flex: 1;
    min-width: 0;
  }

  :deep(.el-textarea__inner) {
    background: transparent;
    border: none;
    box-shadow: none;
    color: var(--text-primary);
    resize: none;
    padding: 4px 0;
    font-size: 14px;

    &::placeholder {
      color: var(--text-muted);
    }
  }

  /* 发送按钮：纯色黄铜 */
  .send-btn {
    flex-shrink: 0;
    background: #a8874a;
    border: 1px solid rgba(220, 196, 137, 0.4);
    transition: background 0.25s ease, border-color 0.25s ease;

    &:hover:not(:disabled) {
      background: #b89a58;
      border-color: rgba(220, 196, 137, 0.65);
    }
  }
}

/* ==================================================================
   响应式适配（窄屏）
   ================================================================== */
@media (max-width: 992px) {
  .conv-rail {
    width: 210px;
  }

  .suggested-questions {
    grid-template-columns: 1fr;
  }

  .msg-column {
    max-width: 86%;
  }

  .message-list {
    padding: 16px;
  }

  .input-area {
    padding: 12px 16px 14px;
  }
}

@media (max-width: 768px) {
  /* 侧栏折叠为图标模式 */
  .conv-rail {
    width: 56px;

    .rail-head {
      padding: 12px 6px;
      align-items: center;
    }

    .tsh-title,
    .tsh-sub,
    .tsh-line,
    .new-chat-label {
      display: none;
    }

    .quota-readout {
      display: none;
    }
  }

  .conv-item {
    justify-content: center;
    padding: 10px 4px;

    .conv-main,
    .conv-actions {
      display: none;
    }
  }

  .empty-state {
    display: none;
  }

  .msg-column {
    max-width: 92%;
  }

  .welcome-area {
    padding: 24px 16px;

    .welcome-hex {
      width: 72px;
      height: 72px;
      margin-bottom: 16px;

      svg {
        width: 38px;
        height: 38px;
      }
    }

    h2 {
      font-size: 18px;
    }
  }

  .console-tip {
    display: none;
  }
}
/* 工作台化问答：回答、依据与输入操作形成稳定的阅读主线 */
.qa-page {
  .conv-rail {
    background: rgba(255, 255, 255, 0.72);
    border-right-color: rgba(148, 158, 178, 0.16);
  }

  .chat-topbar {
    min-height: 46px;
    background: rgba(255, 255, 255, 0.7);
    border-bottom: 1px solid rgba(148, 158, 178, 0.15);
  }

  .welcome-particles {
    display: none;
  }

  .welcome-hero {
    margin-bottom: 28px;

    .gradient-title {
      color: var(--text-primary);
      background: none;
      -webkit-text-fill-color: currentColor;
    }
  }

  .suggested-wrap {
    max-width: 760px;
    box-shadow: none;
    background: #ffffff;
  }

  .suggested-item {
    min-height: 52px;
    animation: none;
    opacity: 1;
    background: #ffffff;
    border-color: #dfe7f1;
    border-left-color: #2f6fed;
    color: #243247;

    .q-text { color: #243247; }

    &:hover {
      background: #f1f6ff;
      border-color: #9dbdf3;
      color: #1d4ed8;
    }
  }

  .message-item {
    animation: none;
  }

  .msg-bubble {
    box-shadow: none;
  }

  .message-item.assistant .message-content {
    background: #ffffff;
    border-color: #dfe7f1;
    color: #243247;
    box-shadow: 0 4px 12px rgba(31, 61, 104, 0.05);
  }

  .message-item.assistant .message-content :deep(.law-citation) {
    color: #8c5914;
    background: #fff6e5;
  }

  .console-shell {
    background: #ffffff;
    border-color: #cad8eb;
    box-shadow: 0 4px 14px rgba(31, 61, 104, 0.06);
  }

  .console-body :deep(.el-textarea__inner) {
    color: #172033;
    background: #ffffff;
  }

  .citations {
    border-left: 2px solid rgba(201, 169, 98, 0.55);
  }
}

@media (max-width: 768px) {
  .qa-page {
    .conv-rail {
      border-right: 0;
      border-bottom: 1px solid var(--border-color);
    }

    .chat-topbar .topbar-title {
      font-size: 10px;
    }
  }
}
</style>

<!-- ==================== 引用来源详情对话框全局样式（el-dialog teleport到body，需非scoped） ==================== -->
<style lang="scss">
/* 引用来源详情对话框（素净面板 + 衬线区块头） */
.citation-dialog.el-dialog {
  border-radius: 8px;
  overflow: hidden;
  background: linear-gradient(165deg, #ffffff 0%, #ffffff 100%);
  border: 1px solid var(--border-color);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.6);

  .el-dialog__header {
    background: rgba(201, 169, 98, 0.04);
    border-bottom: 1px solid var(--border-color);
    padding: 14px 20px;
    margin: 0;
  }
  .el-dialog__title {
    font-size: 15px;
    font-weight: 600;
    font-family: var(--font-serif);
    letter-spacing: 1px;
    color: var(--text-primary);
  }
  .el-dialog__body {
    padding: 18px 20px 20px;
  }
}

/* 引用详情内容区 */
.citation-detail {
  display: flex;
  flex-direction: column;
  gap: 14px;

  .cite-detail-header {
    padding: 2px 0;
  }
}

/* 元信息条：素净 chip 形态 */
.citation-meta-bar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;

  .meta-chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 4px 10px;
    font-size: 11px;
    letter-spacing: 0.5px;
    color: var(--text-secondary);
    background: rgba(148, 158, 178, 0.07);
    border: 1px solid var(--border-color);
    border-radius: 3px;
  }
  .meta-chip-score {
    background: rgba(201, 169, 98, 0.08);
    border-color: rgba(201, 169, 98, 0.3);
    color: var(--accent-light);
  }
  .meta-chip-success {
    background: rgba(124, 165, 134, 0.08);
    border-color: rgba(124, 165, 134, 0.3);
    color: var(--success-color);
  }
}

/* 引用正文容器：素净面板 */
.citation-content-box {
  position: relative;
  background: rgba(255, 255, 255, 0.65);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  overflow: hidden;

  .content-label {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 9px 14px;
    font-size: 12px;
    font-weight: 600;
    font-family: var(--font-serif);
    letter-spacing: 2px;
    color: var(--accent-light);
    background: rgba(201, 169, 98, 0.07);
    border-bottom: 1px solid rgba(201, 169, 98, 0.25);
  }

  .citation-content-text {
    padding: 14px 16px;
    font-size: 14px;
    line-height: 1.8;
    color: var(--text-primary);
    max-height: 50vh;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-word;

    &::-webkit-scrollbar {
      width: 6px;
    }
    &::-webkit-scrollbar-thumb {
      background: rgba(201, 169, 98, 0.35);
      border-radius: 3px;
    }
  }
}
</style>
