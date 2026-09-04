/**
 * 智法通 - 根组件
 *
 * 提供整体布局框架：侧边栏导航 + 顶部导航栏 + 主内容区域。
 * 根据路由状态切换登录页和主布局。
 */

<template>
  <router-view v-if="isLoginPage" />
  <div v-else class="app-layout">
    <!-- 侧边栏导航 -->
    <aside class="sidebar" :class="{ collapsed: isCollapsed }">
      <!-- Logo区域（鎏金天平徽记 + 衬线鎏金品牌字） -->
      <div class="sidebar-logo" @click="handleLogoClick">
        <div class="logo-icon">
          <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
            <!-- 鎏金天平线稿：立柱 + 横梁 + 两侧秤盘 + 底座（庄重对称） -->
            <g stroke="currentColor" stroke-linecap="round">
              <!-- 顶端饰珠 + 立柱 -->
              <circle cx="20" cy="6" r="1.8" stroke-width="1.2"/>
              <line x1="20" y1="8.5" x2="20" y2="32" stroke-width="1.6"/>
              <!-- 横梁 + 中轴接点 -->
              <line x1="8" y1="13" x2="32" y2="13" stroke-width="1.6"/>
              <circle cx="20" cy="13" r="1.4" stroke-width="1"/>
              <!-- 左右吊绳 -->
              <g stroke-width="1.1">
                <line x1="8" y1="13" x2="4" y2="22"/>
                <line x1="8" y1="13" x2="12" y2="22"/>
                <line x1="32" y1="13" x2="28" y2="22"/>
                <line x1="32" y1="13" x2="36" y2="22"/>
              </g>
              <!-- 左右秤盘（浅弧盘） -->
              <path d="M4 22 Q8 28 12 22" stroke-width="1.3"/>
              <path d="M28 22 Q32 28 36 22" stroke-width="1.3"/>
              <!-- 底座 -->
              <line x1="16" y1="32" x2="24" y2="32" stroke-width="1.3"/>
              <line x1="12" y1="35.5" x2="28" y2="35.5" stroke-width="1.6"/>
            </g>
          </svg>
        </div>
        <transition name="fade">
          <span v-show="!isCollapsed" class="logo-text">智法通</span>
        </transition>
      </div>

      <!-- 自定义导航结构（替代 el-menu）：主导航 + 系统管理组 -->
      <nav class="sidebar-nav">
        <!-- 主导航 -->
        <div class="nav-group">
          <!-- 仪表盘：仅 admin/法务负责人 可见（含企业全局数据）
               对应路由 meta.roles: ['admin', 'legal_admin'] -->
          <div
            v-if="userStore.hasRole(['admin', 'legal_admin'])"
            class="nav-item"
            :class="{ active: currentRoute === '/dashboard' }"
            @click="router.push('/dashboard')"
          >
            <span class="nav-active-bar"></span>
            <span class="hex-badge hex-ghost nav-icon"><el-icon :size="15"><DataAnalysis /></el-icon></span>
            <span class="nav-text">仪表盘</span>
            <el-icon class="nav-chevron" :size="12"><ChevronRight /></el-icon>
          </div>

          <!-- 法律问答：所有角色可访问 -->
          <div class="nav-item" :class="{ active: currentRoute === '/qa' }" @click="router.push('/qa')">
            <span class="nav-active-bar"></span>
            <span class="hex-badge hex-ghost nav-icon"><el-icon :size="15"><ChatDotRound /></el-icon></span>
            <span class="nav-text">法律问答</span>
            <el-icon class="nav-chevron" :size="12"><ChevronRight /></el-icon>
          </div>

          <!-- 合同审查：所有角色可访问 -->
          <div class="nav-item" :class="{ active: currentRoute === '/contract' }" @click="router.push('/contract')">
            <span class="nav-active-bar"></span>
            <span class="hex-badge hex-ghost nav-icon"><el-icon :size="15"><Document /></el-icon></span>
            <span class="nav-text">合同审查</span>
            <el-icon class="nav-chevron" :size="12"><ChevronRight /></el-icon>
          </div>

          <!-- 知识库：所有角色可访问。普通用户文案改为「法规案例检索库」弱化管理属性 -->
          <div class="nav-item" :class="{ active: currentRoute === '/knowledge' }" @click="router.push('/knowledge')">
            <span class="nav-active-bar"></span>
            <span class="hex-badge hex-ghost nav-icon"><el-icon :size="15"><Collection /></el-icon></span>
            <span class="nav-text">{{ userStore.isUserRole ? '法规案例检索库' : '知识库' }}</span>
            <el-icon class="nav-chevron" :size="12"><ChevronRight /></el-icon>
          </div>

          <!-- 数据分析：仅 admin/法务负责人 可见（含企业汇总数据）
               对应路由 meta.roles: ['admin', 'legal_admin'] -->
          <div
            v-if="userStore.hasRole(['admin', 'legal_admin'])"
            class="nav-item"
            :class="{ active: currentRoute === '/analysis' }"
            @click="router.push('/analysis')"
          >
            <span class="nav-active-bar"></span>
            <span class="hex-badge hex-ghost nav-icon"><el-icon :size="15"><TrendCharts /></el-icon></span>
            <span class="nav-text">数据分析</span>
            <el-icon class="nav-chevron" :size="12"><ChevronRight /></el-icon>
          </div>
        </div>

        <!-- 系统管理组眉标分隔 -->
        <div class="nav-divider">
          <span class="tech-label nav-eyebrow">系统管理</span>
          <span class="nav-divider-line"></span>
        </div>

        <!-- 系统管理组 -->
        <div class="nav-group">
          <!-- 用户管理：仅超级管理员（admin角色）可见，管理用户账号与权限
               对应路由 meta.roles: ['admin'] -->
          <div
            v-if="userStore.isAdmin"
            class="nav-item"
            :class="{ active: currentRoute === '/users' }"
            @click="router.push('/users')"
          >
            <span class="nav-active-bar"></span>
            <span class="hex-badge hex-ghost nav-icon"><el-icon :size="15"><UserFilled /></el-icon></span>
            <span class="nav-text">用户管理</span>
            <el-icon class="nav-chevron" :size="12"><ChevronRight /></el-icon>
          </div>

          <!-- 系统设置/个人中心：所有角色可访问。普通用户文案为「个人中心」 -->
          <div class="nav-item" :class="{ active: currentRoute === '/settings' }" @click="router.push('/settings')">
            <span class="nav-active-bar"></span>
            <span class="hex-badge hex-ghost nav-icon"><el-icon :size="15"><Setting /></el-icon></span>
            <span class="nav-text">{{ userStore.isUserRole ? '个人中心' : '系统设置' }}</span>
            <el-icon class="nav-chevron" :size="12"><ChevronRight /></el-icon>
          </div>
        </div>
      </nav>

      <!-- 侧边栏底部：系统状态条 -->
      <div class="sidebar-status">
        <span class="status-light is-on"></span>
        <span v-show="!isCollapsed" class="tech-label status-text">系统运行 · 稳定</span>
        <span v-show="!isCollapsed" class="tech-label status-version">v4.0</span>
      </div>

      <!-- 折叠按钮 -->
      <div class="sidebar-toggle" @click="toggleSidebar">
        <el-icon :size="18" class="toggle-icon" :class="{ rotated: isCollapsed }">
          <Fold v-if="!isCollapsed" />
          <Expand v-else />
        </el-icon>
      </div>
    </aside>

    <!-- 移动端侧边栏遮罩层：仅在移动端侧边栏展开时显示，点击遮罩关闭抽屉式侧边栏 -->
    <div v-if="!isCollapsed" class="sidebar-mask" @click="toggleSidebar(true)"></div>

    <!-- 右侧主区域 -->
    <div class="main-area">
      <!-- 顶部导航栏：金点节点 + 衬线渐变标题 + 衬线时钟 + 静态状态灯组 -->
      <header class="header">
        <div class="header-left">
          <span class="diamond-node header-node"></span>
          <h2 class="page-title gradient-text">{{ pageTitle }}</h2>
          <span class="header-vline"></span>
          <!-- 实时时钟 + 日期 -->
          <div class="header-clock" v-if="clockTime">
            <span class="data-readout clock-time">{{ clockTime }}</span>
            <span class="tech-label clock-date">{{ clockDate }}</span>
          </div>
        </div>
        <div class="header-right">
          <!-- 系统状态灯组（静态指示点） -->
          <div class="system-status">
            <span class="status-unit">
              <span class="status-light is-on"></span>
              <span class="tech-label">API</span>
            </span>
            <span class="status-unit">
              <span class="status-light is-on"></span>
              <span class="tech-label">数据库</span>
            </span>
            <span class="status-unit">
              <span class="status-light is-on"></span>
              <span class="tech-label">AI 引擎</span>
            </span>
          </div>

          <!-- 通知图标 + 下拉通知面板 -->
          <el-popover
            placement="bottom-end"
            :width="380"
            trigger="click"
            popper-class="notification-popover"
            @show="handleNotificationShow"
          >
            <template #reference>
              <el-badge
                :value="notificationStore.unreadCount"
                :max="99"
                :hidden="!notificationStore.hasUnread"
                class="header-badge"
              >
                <el-icon :size="20" class="header-icon notification-icon" :class="{ 'has-unread': notificationStore.hasUnread }">
                  <Bell />
                </el-icon>
              </el-badge>
            </template>

            <!-- 通知面板内容（区块头 + 时间线列表） -->
            <div class="notification-panel">
              <!-- 面板头部：结构化区块头 -->
              <div class="notification-header">
                <div class="tech-section-header">
                  <span class="tsh-bar"></span>
                  <span class="tsh-title">通知中心</span>
                  <span class="tsh-sub">通告</span>
                  <span class="tsh-line"></span>
                  <span class="tsh-extra">
                    <el-button
                      v-if="notificationStore.hasUnread"
                      type="primary"
                      link
                      size="small"
                      :loading="notificationStore.loading"
                      @click="handleMarkAllRead"
                    >
                      全部已读
                    </el-button>
                  </span>
                </div>
              </div>

              <!-- 通知列表（时间线化） -->
              <div v-loading="notificationStore.loading" class="notification-list">
                <template v-if="notificationStore.notifications.length > 0">
                  <div
                    v-for="item in notificationStore.notifications"
                    :key="item.id"
                    class="notification-item"
                    :class="{ unread: !item.is_read }"
                    @click="handleNotificationClick(item)"
                  >
                    <!-- 时间线轨道：圆点节点（未读鎏金 / 已读空心） -->
                    <span class="nt-rail">
                      <span class="diamond-node" :class="item.is_read ? 'node-hollow' : 'node-gold'"></span>
                    </span>
                    <!-- 通知类型图标（圆形徽记） -->
                    <div class="notification-type-icon" :class="`type-${item.type}`">
                      <el-icon :size="15">
                        <component :is="getNotificationIcon(item.type)" />
                      </el-icon>
                    </div>
                    <!-- 通知内容 -->
                    <div class="notification-content">
                      <div class="notification-item-title">{{ item.title }}</div>
                      <div v-if="item.content" class="notification-item-desc">{{ item.content }}</div>
                      <div class="notification-item-time">{{ formatNotificationTime(item.created_at) }}</div>
                    </div>
                    <!-- 未读指示点 -->
                    <span v-if="!item.is_read" class="unread-dot"></span>
                  </div>
                </template>
                <!-- 空状态 -->
                <div v-else class="notification-empty">
                  <el-icon :size="40" class="empty-icon"><BellFilled /></el-icon>
                  <p class="empty-text">暂无通知</p>
                </div>
              </div>
            </div>
          </el-popover>

          <!-- 用户信息胶囊（圆形金环头像 + 素净描边） -->
          <el-dropdown trigger="click" @command="handleUserCommand">
            <div class="user-capsule">
              <div class="capsule-body">
                <div class="avatar-wrapper">
                  <div class="avatar-hex">
                    <el-avatar v-if="userStore.userInfo?.avatar" :size="32" :src="userStore.userInfo.avatar" class="user-avatar" />
                    <el-avatar v-else :size="32" class="user-avatar">
                      {{ userStore.username?.charAt(0)?.toUpperCase() || 'U' }}
                    </el-avatar>
                  </div>
                  <span class="online-dot"></span>
                </div>
                <span class="user-name">{{ userStore.username || '用户' }}</span>
                <el-icon class="user-chevron" :size="12"><ArrowDown /></el-icon>
              </div>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon>个人信息
                </el-dropdown-item>
                <!-- 系统设置仅 admin/法务负责人 可见；普通用户的"个人信息"已涵盖个人中心入口 -->
                <el-dropdown-item v-if="userStore.hasRole(['admin', 'legal_admin'])" command="settings">
                  <el-icon><Setting /></el-icon>系统设置
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
        <!-- 底部鎏金细线 -->
        <span class="header-edge"></span>
      </header>

      <!-- 内容区域（墨蓝纸感底 + 极淡暖调暗角） -->
      <main class="content">
        <!-- 暖调暗角层（静态，裁剪负偏移防撑出滚动条） -->
        <div class="content-glow-layer">
          <div class="content-glow content-glow--top-right"></div>
          <div class="content-glow content-glow--bottom-left"></div>
        </div>

        <router-view v-slot="{ Component }">
          <transition name="fade-slide" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useNotificationStore } from '@/stores/notification'
import { ElMessageBox, ElMessage } from 'element-plus'
import type { NotificationItem } from '@/api/notification'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const notificationStore = useNotificationStore()

// 侧边栏折叠状态：从 localStorage 读取初始值，实现折叠状态持久化（刷新后保留用户偏好）
const isCollapsed = ref(JSON.parse(localStorage.getItem('sidebarCollapsed') || 'false'))

// 当前路由路径（用于菜单高亮）
const currentRoute = computed(() => route.path)

// 是否为登录页
const isLoginPage = computed(() => route.path === '/login')

// 页面标题映射（普通用户访问 /settings / /knowledge 时显示个性化标题）
const titleMap = computed<Record<string, string>>(() => ({
  '/dashboard': '仪表盘',
  '/qa': '法律问答',
  '/contract': '合同审查',
  '/knowledge': userStore.isUserRole ? '法规案例检索库' : '知识库',
  '/analysis': '数据分析',
  '/users': '用户管理',
  '/settings': userStore.isUserRole ? '个人中心' : '系统设置',
}))

// 当前页面标题
const pageTitle = computed(() => titleMap.value[route.path] || '智法通')

// ==================== 顶栏实时时钟 ====================
const clockTime = ref('')
const clockDate = ref('')
let clockTimer: number | null = null

const WEEKDAYS = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

const updateClock = () => {
  const now = new Date()
  // 等宽数字时钟 HH:MM:SS
  clockTime.value = now.toLocaleTimeString('zh-CN', { hour12: false })
  clockDate.value = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} ${WEEKDAYS[now.getDay()]}`
}

// Logo点击：admin/法务负责人 跳转仪表盘，普通用户跳转法律问答
const handleLogoClick = () => {
  router.push(userStore.hasRole(['admin', 'legal_admin']) ? '/dashboard' : '/qa')
}

// 切换侧边栏折叠状态
// 支持两种调用方式：
// 1. toggleSidebar() - 切换当前状态
// 2. toggleSidebar(true/false) - 显式设置目标状态（便于移动端抽屉控制）
const toggleSidebar = (val?: boolean) => {
  // 显式传入布尔值则直接设置，否则切换当前状态
  isCollapsed.value = typeof val === 'boolean' ? val : !isCollapsed.value
  // 持久化折叠状态到 localStorage，刷新页面后保留用户偏好
  localStorage.setItem('sidebarCollapsed', JSON.stringify(isCollapsed.value))
}

// ==================== 通知相关 ====================

// 通知类型 -> 图标名称映射
const notificationIconMap: Record<string, string> = {
  system: 'Setting',
  contract: 'Document',
  legal_update: 'Collection',
  qa: 'ChatDotRound',
  warning: 'WarningFilled',
}

// 获取通知类型对应的图标
const getNotificationIcon = (type: string): string => {
  return notificationIconMap[type] || 'Bell'
}

// 格式化通知时间为相对时间（如"3分钟前"、"2小时前"、"昨天"）
const formatNotificationTime = (dateStr: string): string => {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 7) return `${days}天前`
  // 超过7天显示具体日期
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${month}-${day}`
}

// 通知面板展开时加载通知列表
const handleNotificationShow = () => {
  notificationStore.fetchNotifications()
}

// 点击单条通知：标记为已读
const handleNotificationClick = async (item: NotificationItem) => {
  if (!item.is_read) {
    await notificationStore.markAsRead(item.id)
  }
}

// 全部标记为已读
const handleMarkAllRead = async () => {
  await notificationStore.markAllAsRead()
  ElMessage.success('已全部标记为已读')
}

// ==================== 生命周期 ====================
onMounted(() => {
  // 用户已登录时获取未读通知数量（用于徽章显示）
  if (userStore.isLoggedIn) {
    notificationStore.fetchUnreadCount()
  }
  // 顶栏实时时钟：每秒更新
  updateClock()
  clockTimer = window.setInterval(updateClock, 1000)
})

onUnmounted(() => {
  if (clockTimer !== null) {
    clearInterval(clockTimer)
    clockTimer = null
  }
})

// 处理用户下拉菜单命令
const handleUserCommand = async (command: string) => {
  switch (command) {
    case 'profile':
      router.push('/settings')
      break
    case 'settings':
      router.push('/settings')
      break
    case 'logout':
      try {
        await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning',
        })
        userStore.logout()
        router.push('/login')
        ElMessage.success('已退出登录')
      } catch {
        // 用户取消
      }
      break
  }
}
</script>

<style scoped lang="scss">
/* ==================== 整体布局 ==================== */
.app-layout {
  display: flex;
  width: 100%;
  height: 100vh;
  overflow: hidden;
}

/* ==================== 侧边栏 ==================== */
.sidebar {
  width: var(--sidebar-width);
  height: 100vh;
  /* 深藏青墨底（沉稳纸感） */
  background: linear-gradient(180deg, #151b29 0%, #121724 100%);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  transition: width var(--duration-normal) var(--ease-smooth);
  overflow: hidden;
  position: relative;
  z-index: 10;

  &.collapsed {
    width: var(--sidebar-collapsed-width);

    /* 折叠态：Logo 居中 */
    .sidebar-logo {
      justify-content: center;
      padding: 0;
    }

    /* 折叠态：图标居中，隐藏文字/箭头/眉标 */
    .nav-item {
      justify-content: center;
      padding: 0;
      gap: 0;
    }

    .nav-text {
      max-width: 0;
      opacity: 0;
    }

    .nav-chevron,
    .nav-divider {
      display: none;
    }

    .sidebar-status {
      justify-content: center;
      margin: 0 12px;
      padding: 8px 0;
    }
  }

  /* 右缘鎏金细线（静态分隔，两端渐隐） */
  &::after {
    content: '';
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    width: 1px;
    background: linear-gradient(
      180deg,
      transparent 0%,
      rgba(201, 169, 98, 0.35) 25%,
      rgba(201, 169, 98, 0.35) 75%,
      transparent 100%
    );
    pointer-events: none;
  }
}

/* Logo区域 */
.sidebar-logo {
  height: var(--header-height);
  display: flex;
  align-items: center;
  padding: 0 14px;
  cursor: pointer;
  border-bottom: 1px solid var(--border-color);
  gap: 12px;
  flex-shrink: 0;
  transition: padding var(--duration-normal) var(--ease-smooth);

  .logo-icon {
    width: 36px;
    height: 36px;
    color: var(--accent-color);
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;

    svg {
      width: 100%;
      height: 100%;
    }
  }

  .logo-text {
    font-family: var(--font-serif);
    font-size: 21px;
    font-weight: 700;
    letter-spacing: 3px;
    /* 鎏金渐变文字（深铜 - 黄铜 - 浅金） */
    background: linear-gradient(180deg, #dcc489 0%, #c9a962 55%, #a3844a 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    white-space: nowrap;
  }
}

/* ==================== 自定义导航结构（替代 el-menu） ==================== */
.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 12px 8px;
  display: flex;
  flex-direction: column;
}

.nav-group {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

/* 系统管理组眉标分隔（小字 + 渐隐金线） */
.nav-divider {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 16px 8px 8px;

  .nav-eyebrow {
    color: rgba(201, 169, 98, 0.6);
  }

  .nav-divider-line {
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, rgba(201, 169, 98, 0.28), transparent);
  }
}

/* 单个导航项：左侧金线激活指示 + 圆形徽记图标 + 文字 + 悬浮箭头 */
.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  height: 42px;
  padding: 0 10px;
  border-radius: 3px;
  cursor: pointer;
  color: var(--text-secondary);
  transition: background var(--duration-normal) var(--ease-smooth),
    color var(--duration-normal) var(--ease-smooth);

  /* 左侧激活金线（默认隐藏，激活时淡入） */
  .nav-active-bar {
    position: absolute;
    left: 0;
    top: 50%;
    transform: translateY(-50%);
    width: 2px;
    height: 55%;
    border-radius: 0 1px 1px 0;
    background: #c9a962;
    opacity: 0;
    transition: opacity var(--duration-normal) ease;
  }

  /* 图标容器（.hex-badge.hex-ghost 全局已为圆形金环徽记） */
  .nav-icon {
    width: 28px;
    height: 28px;
    transition: background var(--duration-normal) var(--ease-smooth),
      box-shadow var(--duration-normal) var(--ease-smooth);
  }

  .nav-text {
    flex: 1;
    min-width: 0;
    font-size: 13.5px;
    letter-spacing: 0.5px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 160px;
    transition: max-width var(--duration-normal) var(--ease-smooth),
      opacity var(--duration-fast) ease;
  }

  /* 右侧箭头：hover 淡入 */
  .nav-chevron {
    color: var(--accent-color);
    opacity: 0;
    transition: opacity var(--duration-fast) ease;
  }

  /* 悬浮：文字转金 + 背景微亮 */
  &:hover {
    color: var(--accent-light);
    background: rgba(201, 169, 98, 0.05);

    .nav-icon {
      box-shadow: inset 0 0 0 1px rgba(201, 169, 98, 0.45);
    }

    .nav-chevron {
      opacity: 0.85;
    }
  }

  /* 激活态：左侧 2px 金色竖线 + 象牙白衬线文字 + 背景微金 */
  &.active {
    color: var(--text-primary);
    background: rgba(201, 169, 98, 0.08);

    .nav-active-bar {
      opacity: 1;
    }

    .nav-icon {
      background: rgba(201, 169, 98, 0.12);
      color: var(--accent-light);
      box-shadow: inset 0 0 0 1px rgba(201, 169, 98, 0.4);
    }

    .nav-text {
      color: var(--text-primary);
      font-family: var(--font-serif);
      font-weight: 600;
      letter-spacing: 1px;
    }
  }
}

/* ==================== 侧边栏底部：系统状态条 ==================== */
.sidebar-status {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 14px;
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: rgba(28, 35, 52, 0.5);
  flex-shrink: 0;
  transition: all var(--duration-normal) var(--ease-smooth);

  .status-text {
    color: var(--text-secondary);
  }

  .status-version {
    margin-left: auto;
    color: var(--text-muted);
  }
}

/* 折叠按钮 */
.sidebar-toggle {
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--text-secondary);
  border-top: 1px solid var(--border-color);
  transition: color var(--duration-normal) var(--ease-smooth),
    background var(--duration-normal) var(--ease-smooth);

  &:hover {
    color: var(--accent-color);
    background: rgba(201, 169, 98, 0.07);
  }

  .toggle-icon {
    transition: transform var(--duration-normal) var(--ease-spring);

    &.rotated {
      transform: rotate(180deg);
    }
  }
}

/* ==================== 主区域 ==================== */
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg-primary);
}

/* ==================== 顶部导航栏 ==================== */
.header {
  height: var(--header-height);
  background: var(--bg-header);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 0 20px;
  flex-shrink: 0;

  /* 底部鎏金细线（静态，两端渐隐） */
  .header-edge {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(
      90deg,
      transparent 0%,
      rgba(201, 169, 98, 0.4) 25%,
      rgba(220, 196, 137, 0.55) 50%,
      rgba(201, 169, 98, 0.4) 75%,
      transparent 100%
    );
    pointer-events: none;
  }
}

/* 顶栏左侧：金色圆点 + 衬线渐变标题 + 金色竖分隔线 + 衬线时钟 */
.header-left {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;

  .page-title {
    font-family: var(--font-serif);
    font-size: 18px;
    font-weight: 700;
    letter-spacing: 2px;
    white-space: nowrap;
  }

  .header-vline {
    width: 1px;
    height: 26px;
    background: linear-gradient(180deg, transparent, rgba(201, 169, 98, 0.35), transparent);
    flex-shrink: 0;
  }

  .header-clock {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
    line-height: 1.1;

    /* 时钟沿用全局 .data-readout：衬线 + 浅金 */
    .clock-time {
      font-size: 17px;
      letter-spacing: 2px;
    }

    .clock-date {
      color: var(--text-muted);
      letter-spacing: 1px;
    }
  }
}

/* 顶栏右侧 */
.header-right {
  display: flex;
  align-items: center;
  gap: 16px;

  /* 系统状态灯组（静态读出条） */
  .system-status {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 6px 14px;
    background: rgba(28, 35, 52, 0.55);
    border: 1px solid var(--border-color);
    border-radius: 4px;

    .status-unit {
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
  }

  .header-badge {
    cursor: pointer;
  }

  .header-icon {
    color: var(--text-secondary);
    cursor: pointer;
    transition: color var(--duration-normal) ease;

    &:hover {
      color: var(--accent-color);
    }
  }

  /* 通知图标（有未读时转金，静态无脉冲） */
  .notification-icon {
    border-radius: 50%;
    transition: color var(--duration-normal) ease;

    &.has-unread {
      color: var(--accent-color);
    }
  }
}

/* ==================== 用户信息胶囊（圆形金环头像 + 素净描边） ==================== */
.user-capsule {
  border: 1px solid var(--border-color);
  border-radius: 999px;
  background: rgba(28, 35, 52, 0.55);
  cursor: pointer;
  transition: border-color var(--duration-normal) ease,
    background var(--duration-normal) ease;

  &:hover {
    border-color: rgba(201, 169, 98, 0.4);
    background: rgba(201, 169, 98, 0.06);
  }

  .capsule-body {
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 4px 12px 4px 5px;
  }

  .avatar-wrapper {
    position: relative;
    display: inline-flex;
  }

  /* 头像外框：鎏金描边圆环 */
  .avatar-hex {
    width: 36px;
    height: 36px;
    padding: 2px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #a3844a, #dcc489);

    :deep(.el-avatar) {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      background: #1c2334;
      color: #dcc489;
      font-weight: 600;
    }
  }

  /* 在线状态指示点（鼠尾草绿，静态） */
  .online-dot {
    position: absolute;
    bottom: -1px;
    right: -2px;
    width: 10px;
    height: 10px;
    background: #7ca586;
    border: 2px solid #171d2a;
    border-radius: 50%;
  }

  .user-name {
    font-size: 13.5px;
    color: var(--text-primary);
    letter-spacing: 0.5px;
    white-space: nowrap;
  }

  .user-chevron {
    color: var(--text-muted);
    transition: color var(--duration-fast) ease;
  }

  &:hover .user-chevron {
    color: var(--accent-color);
  }
}

/* ==================== 内容区域 ==================== */
.content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  background-color: var(--bg-primary);
  position: relative;
}

/* 裁剪层：铺满内容区并裁剪光晕的负偏移，防止撑出滚动条 */
.content-glow-layer {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
  z-index: 0;
}

/* 极淡暖调暗角（静态墨蓝微光，无漂移动画） */
.content-glow {
  position: absolute;
  border-radius: 50%;
  pointer-events: none;

  /* 右上：暖金微光 */
  &--top-right {
    top: -110px;
    right: -90px;
    width: 440px;
    height: 440px;
    background: radial-gradient(circle, rgba(201, 169, 98, 0.05) 0%, transparent 68%);
    opacity: 0.35;
  }

  /* 左下：深藏青微光 */
  &--bottom-left {
    bottom: -100px;
    left: -100px;
    width: 420px;
    height: 420px;
    background: radial-gradient(circle, rgba(70, 96, 140, 0.06) 0%, transparent 68%);
    opacity: 0.35;
  }
}

/* ==================== 过渡动画（仅淡入） ==================== */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--duration-normal) ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 路由切换：淡入 + 轻微位移 */
.fade-slide-enter-active {
  transition: opacity 0.3s var(--ease-smooth), transform 0.3s var(--ease-smooth);
}
.fade-slide-leave-active {
  transition: opacity 0.25s var(--ease-smooth), transform 0.25s var(--ease-smooth);
}
.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(6px);
}
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* ==================== 移动端侧边栏遮罩层（桌面端默认隐藏） ==================== */
.sidebar-mask {
  display: none;
}

/* 中屏：隐藏装饰性状态灯组，避免顶栏拥挤 */
@media (max-width: 1100px) {
  .system-status {
    display: none;
  }
}

/* ==================== 移动端响应式：抽屉式侧边栏 ==================== */
@media (max-width: 768px) {
  .sidebar {
    position: fixed !important;
    left: 0;
    top: 0;
    bottom: 0;
    z-index: 2000;
    transform: translateX(0);
    transition: transform 0.3s var(--ease-smooth);

    &.collapsed {
      transform: translateX(-100%);
    }
  }

  .sidebar-mask {
    display: block;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(8, 10, 16, 0.66);
    backdrop-filter: blur(3px);
    z-index: 1999;
  }

  .main-area {
    margin-left: 0 !important;
  }

  .header-clock {
    display: none;
  }
}
</style>

<!-- ==================== 通知面板全局样式（el-popover内容teleport到body，需非scoped） ==================== -->
<style lang="scss">
.notification-popover.el-popover.el-popper {
  padding: 0 !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 6px !important;
  overflow: hidden;
  box-shadow: var(--shadow-lg) !important;
  background: #1c2334 !important;

  /* 顶部鎏金细线 */
  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(
      90deg,
      transparent 0%,
      rgba(201, 169, 98, 0.6) 40%,
      rgba(201, 169, 98, 0.6) 60%,
      transparent 100%
    );
    z-index: 1;
    pointer-events: none;
  }
}

/* 通知面板容器（墨蓝纸感底） */
.notification-panel {
  position: relative;
  width: 100%;
  background: linear-gradient(170deg, #1c2334 0%, #171d2a 100%);
}

/* 面板头部（内部为 .tech-section-header 区块头） */
.notification-header {
  padding: 12px 14px;
  border-bottom: 1px solid var(--border-color);
  background: rgba(201, 169, 98, 0.05);
}

/* 通知列表（可滚动） */
.notification-list {
  max-height: 380px;
  overflow-y: auto;
  min-height: 80px;

  &::-webkit-scrollbar {
    width: 6px;
  }
  &::-webkit-scrollbar-track {
    background: transparent;
  }
  &::-webkit-scrollbar-thumb {
    background: rgba(148, 158, 178, 0.28);
    border-radius: 3px;
    &:hover {
      background: rgba(201, 169, 98, 0.4);
    }
  }
}

/* 单条通知项（时间线结构） */
.notification-item {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 14px 12px 42px;
  cursor: pointer;
  transition: background 0.25s var(--ease-smooth);
  border-bottom: 1px solid rgba(148, 158, 178, 0.1);

  &:hover {
    background: rgba(201, 169, 98, 0.06);
  }

  /* 未读通知微金高亮 */
  &.unread {
    background: rgba(201, 169, 98, 0.05);

    .notification-item-title {
      color: var(--text-primary);
      font-weight: 600;
    }
  }

  &:last-child {
    border-bottom: none;
  }
}

/* 时间线轨道：竖向连线 + 圆点节点（未读鎏金 / 已读空心） */
.nt-rail {
  position: absolute;
  left: 15px;
  top: 0;
  bottom: 0;
  width: 10px;
  pointer-events: none;

  &::before {
    content: '';
    position: absolute;
    left: 50%;
    top: 30px;
    bottom: 0;
    width: 1px;
    transform: translateX(-50%);
    background: linear-gradient(180deg, rgba(201, 169, 98, 0.3), rgba(148, 158, 178, 0.08));
  }

  .diamond-node {
    position: absolute;
    left: 0;
    top: 16px;
    z-index: 1;
  }
}

.notification-item:last-child .nt-rail::before {
  display: none;
}

/* 通知类型图标（圆形徽记：金 / 藏青 / 语义色底） */
.notification-type-icon {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;

  &.type-system {
    background: linear-gradient(160deg, #c9a962, #a3844a);
    color: #1d1810;
  }
  &.type-contract {
    background: linear-gradient(160deg, #5a76a5, #3c4a68);
    color: #ece7da;
  }
  &.type-legal_update {
    background: linear-gradient(160deg, #7ca586, #688e72);
    color: #f0f4ef;
  }
  &.type-qa {
    background: linear-gradient(160deg, #7c93b5, #46608c);
    color: #ece7da;
  }
  &.type-warning {
    background: linear-gradient(160deg, #c9973f, #a67c33);
    color: #1d1810;
  }
}

/* 通知内容区 */
.notification-content {
  flex: 1;
  min-width: 0;
}

.notification-item-title {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
  margin-bottom: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.notification-item-desc {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  line-height: 1.5;
}

.notification-item-time {
  font-size: 11px;
  color: var(--text-muted);
}

/* 未读指示点（鎏金，静态） */
.unread-dot {
  position: absolute;
  top: 14px;
  right: 12px;
  width: 8px;
  height: 8px;
  background: #c9a962;
  border-radius: 50%;
  flex-shrink: 0;
}

/* 空状态 */
.notification-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  gap: 12px;

  .empty-icon {
    color: var(--text-muted);
  }

  .empty-text {
    font-size: 13px;
    color: var(--text-muted);
    margin: 0;
  }
}
</style>
