/**
 * 智法通 - Axios实例配置
 *
 * 创建Axios实例，配置基础URL、请求拦截器（添加Token）、
 * 响应拦截器（统一错误处理、Token刷新）。
 */

import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig, AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'

// 创建Axios实例
const service: AxiosInstance = axios.create({
  baseURL: '/api/v1', // 基础URL，通过Vite代理转发到后端8000端口
  timeout: 30000, // 请求超时时间30秒
  headers: {
    'Content-Type': 'application/json',
  },
})

// ==================== 请求拦截器 ====================
service.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 从本地存储获取Token
    const token = localStorage.getItem('access_token')
    if (token && config.headers) {
      // 添加Bearer Token到请求头
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error: AxiosError) => {
    console.error('请求错误：', error)
    return Promise.reject(error)
  }
)

// ==================== 响应拦截器 ====================
service.interceptors.response.use(
  (response: AxiosResponse) => {
    // 直接返回响应数据
    return response.data
  },
  async (error: AxiosError<{ code?: number; message?: string; detail?: string }>) => {
    const status = error.response?.status
    const message = error.response?.data?.message || error.response?.data?.detail || '请求失败'

    switch (status) {
      case 401:
        // Token过期或无效，尝试刷新
        ElMessage.error('登录已过期，请重新登录')
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        // 跳转到登录页
        window.location.href = '/login'
        break
      case 403:
        ElMessage.error('没有权限执行此操作')
        break
      case 404:
        ElMessage.error('请求的资源不存在')
        break
      case 422:
        ElMessage.error('请求参数验证失败')
        break
      case 500:
        ElMessage.error('服务器内部错误，请稍后重试')
        break
      default:
        ElMessage.error(message)
    }

    return Promise.reject(error)
  }
)

export default service
