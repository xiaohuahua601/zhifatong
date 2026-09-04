/**
 * 智法通 - 数据分析API
 *
 * 提供热点分析、引用统计、用户聚类和趋势数据的API接口。
 */

import request from './index'

// 热点话题
interface HotTopic {
  category: string
  count: number
  trend: 'up' | 'down' | 'stable'
  sample_queries: string[]
}

// 引用统计项
interface CitationStatItem {
  document_id: number
  document_title: string
  citation_count: number
  positive_rate: number
  avg_confidence: number | null
}

// 用户聚类
interface UserCluster {
  cluster_id: number
  cluster_name: string
  user_count: number
  avg_features?: Record<string, number>
  center?: number[]
}

// 用户聚类散点数据点
interface ClusterScatterPoint {
  user_id: number
  cluster_id: number
  cluster_name: string
  x: number
  y: number
  query_count?: number
  contract_count?: number
}

// 趋势数据点
interface TrendDataPoint {
  date: string
  query_count: number
  positive_feedback_rate: number
  avg_confidence: number
}

export const analysisApi = {
  /**
   * 获取热点法律问题分析
   */
  getHotTopics(params: { days?: number; top_n?: number }): Promise<{ topics: HotTopic[] }> {
    return request.get('/analysis/hot-topics', { params })
  },

  /**
   * 获取引用统计
   */
  getCitationStats(params: { days?: number; top_n?: number }): Promise<{ citations: CitationStatItem[] }> {
    return request.get('/analysis/citations', { params })
  },

  /**
   * 获取用户行为聚类
   */
  getUserClusters(params: { days?: number }): Promise<{ clusters: UserCluster[]; scatter_data: ClusterScatterPoint[] }> {
    return request.get('/analysis/user-clusters', { params })
  },

  /**
   * 获取趋势数据
   */
  getTrendData(params: {
    start_date?: string
    end_date?: string
    granularity?: 'day' | 'week' | 'month'
  }): Promise<{ trends: TrendDataPoint[] }> {
    return request.get('/analysis/trends', { params })
  },

  /**
   * 获取分析概览
   */
  getOverview(): Promise<any> {
    return request.get('/analysis/overview')
  },
}
