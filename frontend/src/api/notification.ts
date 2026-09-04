/**
 * 智法通 - 通知API
 *
 * 提供用户通知查询、未读数量统计、标记已读等接口。
 */

import request from './index'

// 通知项接口
export interface NotificationItem {
  id: number
  type: string
  title: string
  content: string | null
  is_read: boolean
  resource_type: string | null
  resource_id: number | null
  created_at: string
}

// 通知列表响应
interface NotificationListResponse {
  items: NotificationItem[]
  total: number
  unread_count: number
  page: number
  page_size: number
}

export const notificationApi = {
  /**
   * 获取通知列表
   */
  getNotifications(params: {
    page?: number
    page_size?: number
    is_read?: boolean
  }): Promise<NotificationListResponse> {
    return request.get('/notifications/', { params })
  },

  /**
   * 获取未读通知数量
   */
  getUnreadCount(): Promise<{ unread_count: number }> {
    return request.get('/notifications/unread-count')
  },

  /**
   * 标记单条通知为已读
   */
  markAsRead(notificationId: number): Promise<{ message: string }> {
    return request.put(`/notifications/${notificationId}/read`)
  },

  /**
   * 标记所有通知为已读
   */
  markAllAsRead(): Promise<{ message: string; marked_count: number }> {
    return request.put('/notifications/read-all')
  },
}
