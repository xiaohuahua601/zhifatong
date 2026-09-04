/**
 * 智法通 - 认证API
 *
 * 提供用户注册、登录、令牌刷新和获取当前用户信息的API接口。
 */

import request from './index'

// 登录请求参数
interface LoginParams {
  username: string
  password: string
}

// 注册请求参数
interface RegisterParams {
  username: string
  email: string
  password: string
  phone?: string
}

// Token响应
interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

// 用户信息响应
interface UserResponse {
  id: number
  username: string
  email: string
  phone: string | null
  avatar: string | null
  is_active: boolean
  roles: string[]
}

export const authApi = {
  /**
   * 用户登录
   */
  login(params: LoginParams): Promise<TokenResponse> {
    return request.post('/auth/login', params)
  },

  /**
   * 用户注册
   */
  register(params: RegisterParams): Promise<TokenResponse> {
    return request.post('/auth/register', params)
  },

  /**
   * 刷新令牌
   */
  refreshToken(refreshToken: string): Promise<TokenResponse> {
    return request.post('/auth/refresh', { refresh_token: refreshToken })
  },

  /**
   * 获取当前用户信息
   */
  getCurrentUser(): Promise<UserResponse> {
    return request.get('/auth/me')
  },

  /**
   * 更新个人信息（邮箱、手机号）
   */
  updateProfile(params: { email?: string; phone?: string }): Promise<UserResponse> {
    return request.put('/auth/me', params)
  },

  /**
   * 上传用户头像
   * @param file 头像图片文件
   */
  uploadAvatar(file: File): Promise<UserResponse> {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/auth/avatar', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  /**
   * 删除用户头像
   */
  removeAvatar(): Promise<UserResponse> {
    return request.delete('/auth/avatar')
  },

  /**
   * 修改密码
   */
  changePassword(params: { old_password: string; new_password: string }): Promise<{ message: string }> {
    return request.put('/auth/password', params)
  },
}
