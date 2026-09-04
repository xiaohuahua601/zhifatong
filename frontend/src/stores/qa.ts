/**
 * 智法通 - 问答状态管理（Pinia）
 *
 * 管理法律问答的对话列表、当前对话、消息列表。
 * 支持流式响应（SSE）处理。
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { qaApi } from '@/api/qa'

// 对话信息接口
interface Conversation {
  id: number
  title: string | null
  message_count: number
  created_at: string
  updated_at: string
}

// 消息接口
interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  citations?: string | null
  confidence?: number | null
  created_at: string
  // 前端扩展字段
  isStreaming?: boolean
  feedback?: 'positive' | 'negative' | null
}

// 引用来源接口
interface Citation {
  document_id: number
  document_title: string
  content: string
  score: number
}

export const useQAStore = defineStore('qa', () => {
  // ==================== 状态 ====================
  const conversations = ref<Conversation[]>([])
  const currentConversationId = ref<number | null>(null)
  const messages = ref<Message[]>([])
  const isLoading = ref(false)
  const isStreaming = ref(false)
  // 推荐问题默认值（API不可用时回退）
  const suggestedQuestions = ref<string[]>([
    '劳动合同中常见的法律风险有哪些？',
    '如何判断合同条款是否具有法律效力？',
    '企业知识产权保护需要注意什么？',
    '商业秘密与竞业限制的区别是什么？',
  ])

  // ==================== 计算属性 ====================
  // 当前对话
  const currentConversation = computed(() =>
    conversations.value.find((c) => c.id === currentConversationId.value)
  )

  // 对话总数
  const conversationCount = computed(() => conversations.value.length)

  // ==================== 方法 ====================

  /**
   * 加载对话列表
   */
  async function loadConversations() {
    try {
      const data = await qaApi.getConversations({ page: 1, page_size: 50 })
      conversations.value = data.items || data.conversations || []
    } catch (error) {
      console.error('加载对话列表失败：', error)
    }
  }

  /**
   * 加载指定对话的消息列表
   */
  async function loadMessages(conversationId: number) {
    currentConversationId.value = conversationId
    try {
      const data = await qaApi.getMessages(conversationId)
      messages.value = (data.messages || data || []).map((m: Message) => ({
        ...m,
        feedback: null,
        isStreaming: false,
      }))
    } catch (error) {
      console.error('加载消息失败：', error)
      messages.value = []
    }
  }

  /**
   * 发送问题（非流式）
   */
  async function askQuestion(question: string) {
    isLoading.value = true

    // 添加用户消息到列表
    const userMessage: Message = {
      id: Date.now(),
      role: 'user',
      content: question,
      created_at: new Date().toISOString(),
    }
    messages.value.push(userMessage)

    try {
      const data = await qaApi.ask({
        question,
        conversation_id: currentConversationId.value || undefined,
        stream: false,
      })

      // 更新对话ID（新对话时）
      if (!currentConversationId.value) {
        currentConversationId.value = data.conversation_id
        await loadConversations()
      }

      // 添加AI回复
      const assistantMessage: Message = {
        id: data.message_id,
        role: 'assistant',
        content: data.answer,
        citations: JSON.stringify(data.citations),
        confidence: data.confidence,
        created_at: new Date().toISOString(),
        feedback: null,
      }
      messages.value.push(assistantMessage)
    } catch (error) {
      console.error('提问失败：', error)
      // 添加错误消息
      messages.value.push({
        id: Date.now(),
        role: 'assistant',
        content: '抱歉，回答生成失败，请稍后重试。',
        created_at: new Date().toISOString(),
        feedback: null,
      })
    } finally {
      isLoading.value = false
    }
  }

  /**
   * 发送问题（流式SSE）
   *
   * @param question 用户提问内容
   * @param onQuotaUpdate 额度更新回调，后端通过 X-RateLimit-Remaining 响应头返回剩余次数时触发
   */
  async function askQuestionStream(question: string, onQuotaUpdate?: (remaining: number) => void) {
    isStreaming.value = true

    // 添加用户消息
    const userMessage: Message = {
      id: Date.now(),
      role: 'user',
      content: question,
      created_at: new Date().toISOString(),
    }
    messages.value.push(userMessage)

    // 添加占位的AI回复消息
    const assistantMessage: Message = {
      id: Date.now() + 1,
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString(),
      isStreaming: true,
      feedback: null,
    }
    messages.value.push(assistantMessage)

    try {
      await qaApi.askStream(
        {
          question,
          conversation_id: currentConversationId.value || undefined,
          stream: true,
        },
        // 处理流式数据回调
        (chunk: any) => {
          const lastMsg = messages.value[messages.value.length - 1]
          if (lastMsg && lastMsg.role === 'assistant') {
            // 追加内容
            if (chunk.content) {
              lastMsg.content += chunk.content
            }
            // 更新引用
            if (chunk.citations) {
              lastMsg.citations = JSON.stringify(chunk.citations)
            }
            // 更新置信度
            if (chunk.confidence !== undefined) {
              lastMsg.confidence = chunk.confidence
            }
            // 更新对话ID
            if (chunk.conversation_id && !currentConversationId.value) {
              currentConversationId.value = chunk.conversation_id
            }
          }
        },
        // 完成回调
        () => {
          const lastMsg = messages.value[messages.value.length - 1]
          if (lastMsg && lastMsg.role === 'assistant') {
            lastMsg.isStreaming = false
          }
          isStreaming.value = false
          loadConversations()
        },
        // 错误回调：识别429额度用尽错误，显示专门提示并通知上层更新额度
        (error: any) => {
          const lastMsg = messages.value[messages.value.length - 1]
          if (lastMsg && lastMsg.role === 'assistant') {
            // HTTP 429：今日咨询次数已用完，显示专门的额度提示
            if (error?.status === 429) {
              lastMsg.content = '今日咨询次数已用完，请明日再试或升级套餐。'
              // 通知上层额度更新为0
              onQuotaUpdate?.(0)
            } else {
              lastMsg.content = lastMsg.content || '抱歉，回答生成失败，请稍后重试。'
            }
            lastMsg.isStreaming = false
          }
          isStreaming.value = false
        },
        // 额度更新回调：透传后端 X-RateLimit-Remaining 响应头数据
        onQuotaUpdate
      )
    } catch (error) {
      console.error('流式提问失败：', error)
      const lastMsg = messages.value[messages.value.length - 1]
      if (lastMsg && lastMsg.role === 'assistant') {
        // 429错误在catch中同样处理（防止onError未触发的边界情况）
        if ((error as any)?.status === 429) {
          lastMsg.content = '今日咨询次数已用完，请明日再试或升级套餐。'
          onQuotaUpdate?.(0)
        } else {
          lastMsg.content = '抱歉，回答生成失败，请稍后重试。'
        }
        lastMsg.isStreaming = false
      }
      isStreaming.value = false
    }
  }

  /**
   * 创建新对话
   */
  function newConversation() {
    currentConversationId.value = null
    messages.value = []
  }

  /**
   * 删除对话
   */
  async function deleteConversation(conversationId: number) {
    try {
      await qaApi.deleteConversation(conversationId)
      conversations.value = conversations.value.filter((c) => c.id !== conversationId)
      if (currentConversationId.value === conversationId) {
        newConversation()
      }
    } catch (error) {
      console.error('删除对话失败：', error)
    }
  }

  /**
   * 提交反馈
   */
  async function submitFeedback(messageId: number, isPositive: boolean) {
    try {
      await qaApi.submitFeedback({
        message_id: messageId,
        is_positive: isPositive,
      })
      // 更新本地消息的反馈状态
      const msg = messages.value.find((m) => m.id === messageId)
      if (msg) {
        msg.feedback = isPositive ? 'positive' : 'negative'
      }
    } catch (error) {
      console.error('提交反馈失败：', error)
    }
  }

  /**
   * 获取推荐问题
   * 调用后端API获取推荐问题，失败时保留默认问题
   */
  async function fetchSuggestedQuestions() {
    try {
      const data = await qaApi.getSuggestions()
      if (data.suggestions && data.suggestions.length > 0) {
        suggestedQuestions.value = data.suggestions
      }
    } catch (error) {
      console.error('获取推荐问题失败，使用默认问题：', error)
      // 保留默认问题，不做修改
    }
  }

  return {
    // 状态
    conversations,
    currentConversationId,
    messages,
    isLoading,
    isStreaming,
    suggestedQuestions,
    // 计算属性
    currentConversation,
    conversationCount,
    // 方法
    loadConversations,
    loadMessages,
    askQuestion,
    askQuestionStream,
    newConversation,
    deleteConversation,
    submitFeedback,
    fetchSuggestedQuestions,
  }
})
