/**
 * 智法通 - 知识库API
 *
 * 提供法律知识库文档管理、上传、搜索和统计的API接口。
 */

import request from './index'

// 文档响应
interface DocumentResponse {
  id: number
  title: string
  doc_type: string | null
  source: string
  file_name: string | null
  status: string
  chunk_count: number
  indexing_progress: number
  summary: string | null
  tags: string | null
  is_effective: boolean
  created_at: string
}

// 文档上传响应
interface DocumentUploadResponse {
  id: number
  title: string
  status: string
  message: string
}

// 搜索请求参数
interface SearchParams {
  query: string
  top_k?: number
  doc_type?: string
}

// 知识库统计
interface KnowledgeStats {
  total_documents: number
  total_chunks: number
  doc_type_distribution: Record<string, number>
  recent_uploads: number
  processing_count: number
}

export const knowledgeApi = {
  /**
   * 获取文档列表
   */
  getDocuments(params: {
    page: number
    page_size: number
    doc_type?: string
    keyword?: string
  }): Promise<{ items: DocumentResponse[]; total: number }> {
    return request.get('/knowledge/documents', { params })
  },

  /**
   * 上传法律文档
   */
  uploadDocument(file: File, docType: string = '法律', tags?: string): Promise<DocumentUploadResponse> {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/knowledge/upload', formData, {
      params: { doc_type: docType, tags },
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  /**
   * 搜索知识库
   */
  search(params: SearchParams): Promise<{ results: any[] }> {
    return request.post('/knowledge/search', params)
  },

  /**
   * 获取知识库统计
   */
  getStats(): Promise<KnowledgeStats> {
    return request.get('/knowledge/stats')
  },

  /**
   * 获取文档详情
   */
  getDocumentDetail(documentId: number): Promise<any> {
    return request.get(`/knowledge/documents/${documentId}`)
  },

  /**
   * 获取文档完整内容
   * 返回文档全文及所有分块完整内容，用于文档阅读器展示
   */
  getDocumentContent(documentId: number): Promise<any> {
    return request.get(`/knowledge/documents/${documentId}/content`)
  },

  /**
   * 删除文档
   */
  deleteDocument(documentId: number): Promise<any> {
    return request.delete(`/knowledge/documents/${documentId}`)
  },
}
