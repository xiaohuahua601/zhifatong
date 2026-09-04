/**
 * 智法通 - 仪表盘API
 *
 * 提供仪表盘概览统计、最近活动和趋势数据的API接口。
 */

import request from './index'

// 概览统计
interface OverviewStats {
  total_users: number
  total_conversations: number
  total_contracts: number
  total_documents: number
  today_queries: number
  today_new_users: number
  avg_confidence: number
  positive_feedback_rate: number
}

// 最近活动
interface RecentActivity {
  id: number
  type: 'query' | 'contract' | 'document'
  title: string
  description: string
  user: string
  created_at: string
}

// 趋势数据
interface DashboardTrend {
  date: string
  queries: number
  contracts: number
  users: number
}

// 法律领域分布项
interface DomainDistributionItem {
  name: string
  value: number
}

// 知识图谱节点（ECharts graph格式）
interface GraphNode {
  id: string
  name: string
  category: number
  symbolSize: number
  value: string
  degree: number
}

// 知识图谱关系边
interface GraphLink {
  source: string
  target: string
  value: string
}

// 知识图谱数据（Neo4j真实实体关系）
interface KnowledgeGraph {
  nodes: GraphNode[]
  links: GraphLink[]
  source: 'neo4j' | 'local'
  total_nodes: number
  total_links: number
}

export const dashboardApi = {
  /**
   * 获取概览统计数据
   */
  getOverview(): Promise<OverviewStats> {
    return request.get('/dashboard/overview')
  },

  /**
   * 获取最近活动
   */
  getRecentActivities(params?: { limit?: number }): Promise<{ activities: RecentActivity[] }> {
    return request.get('/dashboard/recent-activities', { params })
  },

  /**
   * 获取趋势数据
   */
  getTrends(params?: { days?: number }): Promise<{ trends: DashboardTrend[] }> {
    return request.get('/dashboard/trends', { params })
  },

  /**
   * 获取法律领域分布统计数据
   */
  getDomainDistribution(): Promise<{ distribution: DomainDistributionItem[] }> {
    return request.get('/dashboard/domain-distribution')
  },

  /**
   * 获取法律知识图谱数据（Neo4j真实实体关系）
   */
  getKnowledgeGraph(params?: { limit?: number }): Promise<KnowledgeGraph> {
    return request.get('/dashboard/graph', { params })
  },

  /**
   * 手动触发Neo4j知识图谱构建
   */
  buildKnowledgeGraph(): Promise<{ message: string; stats: Record<string, number> }> {
    return request.post('/dashboard/graph/build')
  },
}
