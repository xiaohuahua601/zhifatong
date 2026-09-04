/**
 * 智法通 - 通知状态管理（Pinia）
 *
 * 管理用户通知列表、未读数量，提供通知查询、标记已读等操作。
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { notificationApi, type NotificationItem } from '@/api/notification'

export const useNotificationStore = defineStore('notification', () => {
  // ==================== 状态 ====================
  const notifications = ref<NotificationItem[]>([])
  const unreadCount = ref(0)
  const loading = ref(false)

  // ==================== 计算属性 ====================
  // 是否有未读通知
  const hasUnread = computed(() => unreadCount.value > 0)

  // ==================== 方法 ====================

  /**
   * 获取未读通知数量（轻量接口，用于徽章数字）
   */
  async function fetchUnreadCount() {
    try {
      const data = await notificationApi.getUnreadCount()
      unreadCount.value = data.unread_count
    } catch (error) {
      console.error('获取未读通知数量失败：', error)
    }
  }

  /**
   * 获取通知列表
   */
  async function fetchNotifications(params?: { is_read?: boolean }) {
    loading.value = true
    try {
      const data = await notificationApi.getNotifications({
        page: 1,
        page_size: 20,
        ...params,
      })
      notifications.value = data.items
      unreadCount.value = data.unread_count
    } catch (error) {
      console.error('获取通知列表失败：', error)
    } finally {
      loading.value = false
    }
  }

  /**
   * 标记单条通知为已读
   */
  async function markAsRead(notificationId: number) {
    try {
      await notificationApi.markAsRead(notificationId)
      // 本地更新状态
      const item = notifications.value.find((n) => n.id === notificationId)
      if (item && !item.is_read) {
        item.is_read = true
        unreadCount.value = Math.max(0, unreadCount.value - 1)
      }
    } catch (error) {
      console.error('标记通知已读失败：', error)
    }
  }

  /**
   * 标记所有通知为已读
   */
  async function markAllAsRead() {
    try {
      await notificationApi.markAllAsRead()
      // 本地更新状态
      notifications.value.forEach((n) => (n.is_read = true))
      unreadCount.value = 0
    } catch (error) {
      console.error('标记所有通知已读失败：', error)
    }
  }

  return {
    // 状态
    notifications,
    unreadCount,
    loading,
    // 计算属性
    hasUnread,
    // 方法
    fetchUnreadCount,
    fetchNotifications,
    markAsRead,
    markAllAsRead,
  }
})
