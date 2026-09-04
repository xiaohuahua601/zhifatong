/**
 * 智法通 - 用户管理API调用层（管理员专用）
 *
 * 封装用户管理模块的所有后端接口调用，包括：
 * - 用户列表查询（分页+搜索+筛选）
 * - 用户创建、编辑、删除
 * - 角色查询与分配
 * - 用户状态切换（启用/禁用）
 * - 密码重置
 *
 * 所有接口均由后端 get_current_superuser 依赖保护，
 * 仅 is_superuser=True 的超级管理员可访问。
 */

import service from '@/api/index'

// ==================== 类型定义 ====================

/** 角色信息 */
export interface Role {
  id: number
  name: string
  code: string
  description: string | null
  is_default: boolean
}

/** 用户管理列表项 */
export interface UserManageItem {
  id: number
  username: string
  email: string
  phone: string | null
  avatar: string | null
  is_active: boolean
  is_superuser: boolean
  last_login: string | null
  created_at: string
  roles: Role[]
}

/** 用户列表分页响应 */
export interface UserListResponse {
  total: number
  page: number
  page_size: number
  items: UserManageItem[]
}

/** 用户列表查询参数 */
export interface UserListParams {
  page?: number
  page_size?: number
  keyword?: string
  role_code?: string
  is_active?: boolean
}

/** 创建用户请求参数 */
export interface UserCreateParams {
  username: string
  email: string
  password: string
  phone?: string
  role_codes: string[]
  is_active?: boolean
}

/** 编辑用户请求参数 */
export interface UserUpdateParams {
  email?: string
  phone?: string
  is_active?: boolean
}

/** 角色分配请求参数 */
export interface RoleAssignParams {
  role_codes: string[]
}

/** 用户状态切换请求参数 */
export interface UserStatusParams {
  is_active: boolean
}

// ==================== API 接口 ====================

export const userApi = {
  /**
   * 获取用户列表（分页+搜索+筛选）
   * @param params 查询参数（页码、每页数量、关键词、角色筛选、状态筛选）
   */
  getUsers(params: UserListParams): Promise<UserListResponse> {
    return service.get('/users', { params })
  },

  /**
   * 获取所有角色列表（用于角色分配下拉框）
   */
  getRoles(): Promise<Role[]> {
    return service.get('/users/roles')
  },

  /**
   * 创建新用户
   * @param params 用户信息（用户名、邮箱、密码、角色等）
   */
  createUser(params: UserCreateParams): Promise<UserManageItem> {
    return service.post('/users', params)
  },

  /**
   * 为用户分配角色（完全替换现有角色）
   * @param userId 用户ID
   * @param params 角色分配参数
   */
  assignRoles(userId: number, params: RoleAssignParams): Promise<UserManageItem> {
    return service.put(`/users/${userId}/roles`, params)
  },

  /**
   * 切换用户启用/禁用状态
   * @param userId 用户ID
   * @param params 状态参数
   */
  updateUserStatus(userId: number, params: UserStatusParams): Promise<UserManageItem> {
    return service.put(`/users/${userId}/status`, params)
  },

  /**
   * 编辑用户信息（邮箱、手机号、状态）
   * @param userId 用户ID
   * @param params 编辑参数
   */
  updateUser(userId: number, params: UserUpdateParams): Promise<UserManageItem> {
    return service.put(`/users/${userId}`, params)
  },

  /**
   * 删除用户
   * @param userId 用户ID
   */
  deleteUser(userId: number): Promise<{ message: string }> {
    return service.delete(`/users/${userId}`)
  },

  /**
   * 重置用户密码（管理员无需旧密码）
   * @param userId 用户ID
   * @param newPassword 新密码
   */
  resetPassword(userId: number, newPassword: string): Promise<{ message: string }> {
    return service.post(`/users/${userId}/reset-password`, null, {
      params: { new_password: newPassword },
    })
  },
}

export default userApi
