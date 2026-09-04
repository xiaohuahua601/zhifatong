/**
 * 智法通 - 合同审查API
 *
 * 提供合同上传、审查、获取报告和历史记录的API接口。
 */

import request from './index'

// 合同上传响应
interface ContractUploadResponse {
  id: number
  title: string
  file_name: string
  status: string
}

// 审查请求参数
interface ReviewParams {
  contract_id: number
  contract_type?: string
}

// 审查报告响应
interface ReviewReportResponse {
  id: number
  contract_id: number
  overall_score: number | null
  risk_level: string | null
  risk_clause_count: number
  summary: string | null
  suggestions: string | null
  completeness: string | null
  compliance: string | null
  consistency: string | null
  review_duration_ms: number | null
  risk_clauses: any[]
}

// 合同列表项
interface ContractListItem {
  id: number
  title: string
  file_name: string
  contract_type: string | null
  status: string
  overall_score: number | null
  risk_level: string | null
  created_at: string
}

export const contractApi = {
  /**
   * 上传合同文件
   */
  uploadContract(file: File): Promise<ContractUploadResponse> {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/contract/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  /**
   * 启动合同审查
   * 多Agent审查含多次LLM调用，耗时可达数分钟，
   * 单独设置5分钟超时（覆盖全局30s默认值，避免长流程被误判为失败）
   */
  reviewContract(params: ReviewParams): Promise<any> {
    return request.post('/contract/review', params, {
      timeout: 300000,
    })
  },

  /**
   * 获取审查报告
   */
  getReviewReport(contractId: number): Promise<ReviewReportResponse> {
    return request.get(`/contract/report/${contractId}`)
  },

  /**
   * 获取合同历史记录
   */
  getContractHistory(params: {
    page: number
    page_size: number
    status_filter?: string
  }): Promise<{ items: ContractListItem[]; total: number }> {
    return request.get('/contract/history', { params })
  },

  /**
   * 获取合同详情
   */
  getContractDetail(contractId: number): Promise<any> {
    return request.get(`/contract/${contractId}`)
  },

  /**
   * 删除合同
   */
  deleteContract(contractId: number): Promise<any> {
    return request.delete(`/contract/${contractId}`)
  },

  /**
   * 更新合同分类
   */
  updateContractType(contractId: number, contractType: string): Promise<any> {
    return request.patch(`/contract/${contractId}/type`, { contract_type: contractType })
  },

  /**
   * 优化合同并生成Markdown（V6.0.6新增）
   * 基于审查报告修改建议优化原合同，返回markdown全文与建议文件名。
   * 含LLM逐条改写调用，耗时可达1-2分钟，单独设置3分钟超时。
   */
  optimizeContract(contractId: number): Promise<{
    markdown: string
    file_name: string
    suggestion_count: number
    replaced_count: number
  }> {
    return request.post('/contract/optimize', { contract_id: contractId }, {
      timeout: 180000,
    })
  },
}
