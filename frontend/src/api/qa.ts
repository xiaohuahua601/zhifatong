/**
 * 智法通 - 法律问答API
 *
 * 提供法律提问、流式回答、对话历史和反馈的API接口。
 */

import request from './index'

// 提问请求参数
interface AskParams {
  question: string
  conversation_id?: number | null
  stream?: boolean
}

// 提问响应
interface AskResponse {
  conversation_id: number
  message_id: number
  answer: string
  citations: any[]
  confidence: number | null
}

// 对话列表响应
interface ConversationListResponse {
  items?: any[]
  conversations?: any[]
  total?: number
}

// 反馈请求参数
interface FeedbackParams {
  message_id: number
  is_positive: boolean
  rating?: number
  comment?: string
}

export const qaApi = {
  /**
   * 法律提问（非流式）
   */
  ask(params: AskParams): Promise<AskResponse> {
    return request.post('/qa/ask', params)
  },

  /**
   * 流式法律提问（SSE）
   * 使用EventSource接收流式数据
   *
   * 增强功能：
   * - 读取后端响应头 X-RateLimit-Remaining，实时更新前端额度显示
   * - 识别 HTTP 429 状态码（额度用尽），抛出带 status 属性的错误便于上层处理
   *
   * @param params 提问参数
   * @param onChunk 流式数据回调
   * @param onDone 完成回调
   * @param onError 错误回调
   * @param onQuotaUpdate 额度更新回调（后端通过 X-RateLimit-Remaining 响应头返回剩余次数）
   */
  askStream(
    params: AskParams,
    onChunk: (data: any) => void,
    onDone: () => void,
    onError: (error: any) => void,
    onQuotaUpdate?: (remaining: number) => void
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      const token = localStorage.getItem('access_token')

      // 使用fetch API发送POST请求，处理SSE流
      fetch('/api/v1/qa/ask/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(params),
      })
        .then((response) => {
          // 从响应头读取剩余咨询额度（后端通过 X-RateLimit-Remaining 头返回）
          // 注意：需后端配置 Access-Control-Expose-Headers 才能跨域读取自定义头
          const remainingHeader = response.headers.get('X-RateLimit-Remaining')
          if (remainingHeader !== null && onQuotaUpdate) {
            const remaining = parseInt(remainingHeader, 10)
            if (!isNaN(remaining)) {
              onQuotaUpdate(remaining)
            }
          }

          if (!response.ok) {
            // HTTP 429：今日咨询次数已用完，构造带状态码的错误对象便于上层识别处理
            if (response.status === 429) {
              const rateLimitError: any = new Error('今日咨询次数已用完')
              rateLimitError.status = 429
              throw rateLimitError
            }
            throw new Error(`HTTP error! status: ${response.status}`)
          }

          const reader = response.body?.getReader()
          const decoder = new TextDecoder()

          if (!reader) {
            throw new Error('ReadableStream not supported')
          }

          // 递归读取流数据
          const readChunk = () => {
            reader
              .read()
              .then(({ done, value }) => {
                if (done) {
                  onDone()
                  resolve()
                  return
                }

                // 解码数据
                const text = decoder.decode(value, { stream: true })
                // 解析SSE格式数据
                const lines = text.split('\n')
                for (const line of lines) {
                  if (line.startsWith('data: ')) {
                    const data = line.slice(6)
                    if (data === '[DONE]') {
                      onDone()
                      resolve()
                      return
                    }
                    try {
                      const parsed = JSON.parse(data)
                      onChunk(parsed)
                    } catch {
                      // 忽略解析错误
                    }
                  }
                }

                // 继续读取
                readChunk()
              })
              .catch((error) => {
                onError(error)
                reject(error)
              })
          }

          readChunk()
        })
        .catch((error) => {
          onError(error)
          reject(error)
        })
    })
  },

  /**
   * 获取今日剩余咨询额度
   * 调用后端 /qa/quota 端点查询用户当前剩余问答次数
   * 若后端暂未实现该端点，调用方应捕获异常并使用默认值
   */
  getQuota(): Promise<{ remaining: number; total: number }> {
    return request.get('/qa/quota')
  },

  /**
   * 获取对话列表
   */
  getConversations(params: { page: number; page_size: number }): Promise<ConversationListResponse> {
    return request.get('/qa/conversations', { params })
  },

  /**
   * 获取对话消息
   */
  getMessages(conversationId: number): Promise<any> {
    return request.get(`/qa/conversations/${conversationId}/messages`)
  },

  /**
   * 提交问答反馈
   */
  submitFeedback(params: FeedbackParams): Promise<any> {
    return request.post('/qa/feedback', params)
  },

  /**
   * 删除对话
   */
  deleteConversation(conversationId: number): Promise<any> {
    return request.delete(`/qa/conversations/${conversationId}`)
  },

  /**
   * 重命名对话
   */
  renameConversation(conversationId: number, title: string): Promise<any> {
    return request.patch(`/qa/conversations/${conversationId}`, { title })
  },

  /**
   * 获取推荐问题
   */
  getSuggestions(): Promise<{ suggestions: string[] }> {
    return request.get('/qa/suggestions')
  },
}
