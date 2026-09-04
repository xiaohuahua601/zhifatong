/**
 * 智法通 - 用户状态管理（Pinia）
 *
 * 管理用户登录状态、Token、用户信息。
 * 提供登录、登出、Token刷新等操作。
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import router from '@/router'

// 用户信息接口
interface UserInfo {
  id: number
  username: string
  email: string
  phone: string | null
  avatar: string | null
  is_active: boolean
  roles: string[]
}

// Token接口
interface TokenData {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export const useUserStore = defineStore('user', () => {
  // ==================== 状态 ====================
  const token = ref<string>(localStorage.getItem('access_token') || '')
  const refreshToken = ref<string>(localStorage.getItem('refresh_token') || '')
  const userInfo = ref<UserInfo | null>(null)

  // ==================== 计算属性 ====================
  // 是否已登录
  const isLoggedIn = computed(() => !!token.value)

  // 用户名
  const username = computed(() => userInfo.value?.username || '')

  // 用户角色
  const roles = computed(() => userInfo.value?.roles || [])

  // 是否为管理员（含超级管理员）
  const isAdmin = computed(() => roles.value.includes('admin'))

  // 是否为法务人员
  const isLawyer = computed(() => roles.value.includes('legal_admin'))

  // 是否为普通用户（仅 user 角色，无 admin/legal_admin）
  const isUserRole = computed(() =>
    roles.value.includes('user') && !roles.value.includes('admin') && !roles.value.includes('legal_admin')
  )

  /**
   * 判断当前用户是否拥有指定角色之一
   * @param roleCodes 角色编码数组（如 ['admin', 'legal_admin']）
   */
  const hasRole = (roleCodes: string[]) =>
    roleCodes.some((code) => roles.value.includes(code))

  // ==================== 方法 ====================

  /**
   * 用户登录
   * @param username 用户名或邮箱
   * @param password 密码
   */
  async function login(username: string, password: string) {
    const data = await authApi.login({ username, password })
    setTokenData(data)
    // 登录成功后获取用户信息
    await fetchUserInfo()
  }

  /**
   * 用户注册
   */
  async function register(params: {
    username: string
    email: string
    password: string
    phone?: string
  }) {
    const data = await authApi.register(params)
    setTokenData(data)
    await fetchUserInfo()
  }

  /**
   * 用户登出
   */
  function logout() {
    token.value = ''
    refreshToken.value = ''
    userInfo.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  /**
   * 获取当前用户信息
   */
  async function fetchUserInfo() {
    try {
      const data = await authApi.getCurrentUser()
      userInfo.value = data
    } catch (error) {
      console.error('获取用户信息失败：', error)
    }
  }

  /**
   * 更新个人信息（邮箱、手机号），成功后同步更新本地 userInfo
   */
  async function updateProfile(params: { email?: string; phone?: string }) {
    const data = await authApi.updateProfile(params)
    userInfo.value = data
    return data
  }

  /**
   * 上传头像，成功后同步更新本地 userInfo.avatar
   */
  async function uploadAvatar(file: File) {
    const data = await authApi.uploadAvatar(file)
    userInfo.value = data
    return data
  }

  /**
   * 删除头像，成功后同步清除本地 userInfo.avatar
   */
  async function removeAvatar() {
    const data = await authApi.removeAvatar()
    userInfo.value = data
    return data
  }

  /**
   * 修改密码
   */
  async function changePassword(oldPassword: string, newPassword: string) {
    return await authApi.changePassword({
      old_password: oldPassword,
      new_password: newPassword,
    })
  }

  /**
   * 刷新Token
   */
  async function refreshAccessToken() {
    try {
      const data = await authApi.refreshToken(refreshToken.value)
      setTokenData(data)
    } catch (error) {
      // 刷新失败，强制登出
      logout()
      router.push('/login')
      throw error
    }
  }

  /**
   * 保存Token数据到状态和本地存储
   */
  function setTokenData(data: TokenData) {
    token.value = data.access_token
    refreshToken.value = data.refresh_token
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
  }

  return {
    // 状态
    token,
    refreshToken,
    userInfo,
    // 计算属性
    isLoggedIn,
    username,
    roles,
    isAdmin,
    isLawyer,
    isUserRole,
    hasRole,
    // 方法
    login,
    register,
    logout,
    fetchUserInfo,
    updateProfile,
    uploadAvatar,
    removeAvatar,
    changePassword,
    refreshAccessToken,
  }
})
