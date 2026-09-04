/**
 * 智法通 - 应用入口文件
 *
 * 创建Vue应用实例，注册全局插件（Element Plus、路由、Pinia），
 * 并挂载到DOM。
 *
 * 关键逻辑：应用启动时若本地存在Token，先异步加载用户信息，
 * 确保路由守卫在首次导航时即可读到角色信息，避免因userInfo为空
 * 导致的角色鉴权失败与无限重定向（首页空白问题根因）。
 */

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import { useUserStore } from './stores/user'
import './styles/global.scss'

// 创建Vue应用实例
const app = createApp(App)

// 注册Pinia状态管理
const pinia = createPinia()
app.use(pinia)

// 注册Vue Router
app.use(router)

// 注册Element Plus（使用深色主题）
app.use(ElementPlus, {
  size: 'default',
})

// 全局注册Element Plus图标组件
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 全局错误捕获：防止未捕获的Promise拒绝导致页面卡白
app.config.errorHandler = (err, _instance, info) => {
  console.error('Vue全局错误：', err, '\n错误来源：', info)
}

/**
 * 应用启动初始化
 *
 * 必须在挂载前完成用户信息加载，原因：
 * 1. 路由守卫依赖 userStore.roles 判断访问权限
 * 2. 若仅 token 存在但 userInfo 为空，roles 返回空数组
 * 3. 空角色会导致 canAccessRoute 始终返回 false，触发无限重定向
 *
 * 加载失败（如Token过期）由 axios 响应拦截器统一处理：清空Token并跳转登录页
 */
async function bootstrap() {
  const userStore = useUserStore()
  // 本地存在Token时，先拉取用户信息（含角色），再挂载应用
  if (userStore.isLoggedIn) {
    try {
      await userStore.fetchUserInfo()
    } catch (error) {
      // fetchUserInfo 内部已 try/catch，此处仅为兜底
      // 若Token无效，axios 拦截器会清空Token并跳转 /login
      console.error('启动时加载用户信息失败：', error)
    }
  }
  // 用户信息就绪后挂载应用，触发首次路由导航
  app.mount('#app')
}

bootstrap()
