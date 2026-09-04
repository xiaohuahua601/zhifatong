/**
 * 智法通 - 路由配置
 *
 * 定义所有页面路由，包括登录页、仪表盘、法律问答、合同审查、
 * 知识库、数据分析和系统设置。包含路由守卫进行认证与角色鉴权检查。
 *
 * RBAC 权限策略：
 * - admin / legal_admin：可访问全部页面（含仪表盘、数据分析、系统设置）
 * - user（普通用户）：仅可访问 法律问答、合同审查、法规案例检索库、个人中心
 *   仪表盘与数据分析菜单隐藏，直接访问路由将重定向至 /qa
 */

import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { useUserStore } from '@/stores/user'

// 路由配置
const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录', requiresAuth: false },
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    // 仪表盘含企业全局数据，仅 admin/lawyer 可访问
    meta: { title: '仪表盘', requiresAuth: true, roles: ['admin', 'legal_admin'] },
  },
  {
    path: '/qa',
    name: 'QA',
    component: () => import('@/views/QA.vue'),
    meta: { title: '法律问答', requiresAuth: true, roles: ['admin', 'legal_admin', 'user'] },
  },
  {
    path: '/contract',
    name: 'Contract',
    component: () => import('@/views/Contract.vue'),
    meta: { title: '合同审查', requiresAuth: true, roles: ['admin', 'legal_admin', 'user'] },
  },
  {
    path: '/knowledge',
    name: 'Knowledge',
    component: () => import('@/views/Knowledge.vue'),
    meta: { title: '知识库', requiresAuth: true, roles: ['admin', 'legal_admin', 'user'] },
  },
  {
    path: '/analysis',
    name: 'Analysis',
    component: () => import('@/views/Analysis.vue'),
    // 数据分析含企业汇总数据，仅 admin/lawyer 可访问
    meta: { title: '数据分析', requiresAuth: true, roles: ['admin', 'legal_admin'] },
  },
  {
    path: '/users',
    name: 'UserManagement',
    component: () => import('@/views/UserManagement.vue'),
    // 用户管理：仅超级管理员（admin角色）可访问，管理用户账号与权限
    meta: { title: '用户管理', requiresAuth: true, roles: ['admin'] },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/Settings.vue'),
    // 系统设置/个人中心：所有角色可访问，页面内部根据角色显示不同内容
    meta: { title: '系统设置', requiresAuth: true, roles: ['admin', 'legal_admin', 'user'] },
  },
  // 默认重定向：登录后由守卫根据角色跳转
  {
    path: '/',
    redirect: '/dashboard',
  },
  // 404页面重定向到仪表盘
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard',
  },
]

// 创建路由实例
const router = createRouter({
  history: createWebHistory(),
  routes,
})

/**
 * 判断当前用户是否可访问目标路由（基于 meta.roles 角色白名单）
 */
function canAccessRoute(toRoles: string[] | undefined, userRoles: string[]): boolean {
  if (!toRoles || toRoles.length === 0) return true
  if (userRoles.includes('admin')) return true // 超级管理员放行所有
  return toRoles.some((r) => userRoles.includes(r))
}

// 路由守卫 - 认证 + 角色鉴权
router.beforeEach((to, _from, next) => {
  const userStore = useUserStore()

  // 设置页面标题
  if (to.meta.title) {
    document.title = `${to.meta.title} - 智法通`
  }

  // 不需要认证的页面直接放行
  if (!to.meta.requiresAuth) {
    // 已登录用户访问登录页，根据角色重定向到默认首页
    if (to.path === '/login' && userStore.isLoggedIn) {
      const userRoles = userStore.roles
      // 普通用户默认进入法律问答，管理员/法务进入仪表盘
      next(userRoles.includes('admin') || userRoles.includes('legal_admin') ? '/dashboard' : '/qa')
      return
    }
    next()
    return
  }

  // 需要认证的页面，检查登录状态
  if (!userStore.isLoggedIn) {
    // 保存目标路径，登录后跳转
    next({
      path: '/login',
      query: { redirect: to.fullPath },
    })
    return
  }

  // 防护：Token存在但角色为空（userInfo加载失败或异常状态）
  // 此时无法进行角色鉴权，强制登出并跳转登录页，避免无限重定向导致首页空白
  const userRoles = userStore.roles
  if (userRoles.length === 0) {
    userStore.logout()
    next({
      path: '/login',
      query: { redirect: to.fullPath },
    })
    return
  }

  // 角色鉴权：无权访问的路由重定向到默认首页
  if (!canAccessRoute(to.meta.roles as string[] | undefined, userRoles)) {
    // 普通用户越权访问仪表盘/数据分析等，重定向至法律问答
    const fallback = userRoles.includes('admin') || userRoles.includes('legal_admin') ? '/dashboard' : '/qa'
    next(fallback)
    return
  }

  next()
})

export default router
