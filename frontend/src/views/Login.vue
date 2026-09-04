/**
 * 智法通 - 登录页面（案卷墨蓝 · 鎏金典雅版）
 *
 * 设计理念：律所级庄重 / 法律文书感 / 无科技霓虹元素
 * - 分屏布局：左侧品牌展示区（鎏金天平徽记 + 衬线标语 + 卷首金线），右侧登录表单区
 * - 色彩方案：深墨蓝底 + 黄铜鎏金点缀 + 象牙白衬线标题 + 纸感肌理
 * - 形态语言：素净面板 + 1px 石板边框 + 顶部鎏金细线 + 圆角 6px
 * - 交互细节：克制的淡入过渡、金色聚焦边线、表单验证抖动反馈
 * - 响应式：移动端自动切换为单列堆叠布局
 */

<template>
  <div class="login-page">
    <!-- ==================== 左侧品牌展示区 ==================== -->
    <aside class="brand-panel">
      <!-- 纸感底：极淡鎏金光晕 + 藏青氛围（静态） -->
      <div class="brand-paper"></div>

      <!-- 卷首 / 卷尾细金线（文书卷首感） -->
      <div class="brand-rule brand-rule-top"></div>
      <div class="brand-rule brand-rule-bottom"></div>

      <!-- 品牌内容区 -->
      <div class="brand-content">
        <!-- 鎏金天平徽记（线稿 · 庄重对称） -->
        <div class="brand-emblem">
          <svg viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
            <!-- 顶部吊环 -->
            <circle cx="48" cy="10" r="4" stroke-width="1.6"/>
            <!-- 中心立柱 -->
            <line x1="48" y1="14" x2="48" y2="70" stroke-width="1.8"/>
            <!-- 衡梁 -->
            <line x1="15" y1="24" x2="81" y2="24" stroke-width="1.8"/>
            <!-- 衡梁中心节点 -->
            <circle cx="48" cy="24" r="2.4" fill="currentColor" stroke="none"/>
            <!-- 左侧吊索与秤盘 -->
            <line x1="15" y1="24" x2="4.5" y2="42" stroke-width="1" opacity="0.85"/>
            <line x1="15" y1="24" x2="25.5" y2="42" stroke-width="1" opacity="0.85"/>
            <path d="M4.5 42 A10.5 7 0 0 0 25.5 42" stroke-width="1.6"/>
            <!-- 右侧吊索与秤盘 -->
            <line x1="81" y1="24" x2="70.5" y2="42" stroke-width="1" opacity="0.85"/>
            <line x1="81" y1="24" x2="91.5" y2="42" stroke-width="1" opacity="0.85"/>
            <path d="M70.5 42 A10.5 7 0 0 0 91.5 42" stroke-width="1.6"/>
            <!-- 底座（三级递宽，青铜基座感） -->
            <line x1="38" y1="70" x2="58" y2="70" stroke-width="1.6"/>
            <line x1="31" y1="76" x2="65" y2="76" stroke-width="1.6"/>
            <line x1="24" y1="82" x2="72" y2="82" stroke-width="2"/>
          </svg>
        </div>

        <!-- 品牌名 + 标语 -->
        <h1 class="brand-name">智法通</h1>
        <p class="brand-tagline">以法为衡 · 以智为鉴</p>

        <!-- 金线分隔（菱形节点 · 文书感） -->
        <div class="brand-divider"></div>

        <!-- 服务说明小字 -->
        <p class="brand-desc">企业级智能法律顾问平台</p>
        <p class="brand-desc-sub">智能法律问答 · 合同风险审查 · 法律知识检索 · 数据可视化分析</p>

        <!-- 核心能力：帮助首次访问者快速理解平台用途 -->
        <div class="brand-capabilities" aria-label="平台核心能力">
          <div class="capability-item">
            <span class="capability-mark">01</span>
            <span>法规与案例联合检索</span>
          </div>
          <div class="capability-item">
            <span class="capability-mark">02</span>
            <span>合同风险智能审查</span>
          </div>
          <div class="capability-item">
            <span class="capability-mark">03</span>
            <span>企业法律事务洞察</span>
          </div>
        </div>

        <div class="brand-trust">
          <span class="trust-dot"></span>
          <span>企业级权限管理与加密保护</span>
        </div>
      </div>
    </aside>

    <!-- ==================== 右侧登录表单区 ==================== -->
    <main class="form-panel">
      <!-- 登录卡片 -->
      <div class="login-card-wrapper">
        <div class="login-card">
          <!-- 卡片标题 -->
          <div class="card-header">
            <h2 class="card-title">{{ activeTab === 'login' ? '登 录' : '创建账户' }}</h2>
            <p class="card-subtitle">{{ activeTab === 'login' ? '请输入您的凭据以继续' : '填写信息注册新账户' }}</p>
          </div>

          <!-- 登录/注册切换 -->
          <div class="tab-switch-wrapper">
            <div class="tab-switch">
              <div
                class="tab-switch-indicator"
                :class="{ 'indicator-right': activeTab === 'register' }"
              ></div>
              <div
                class="tab-switch-item"
                :class="{ active: activeTab === 'login' }"
                @click="activeTab = 'login'"
              >
                登录
              </div>
              <div
                class="tab-switch-item"
                :class="{ active: activeTab === 'register' }"
                @click="activeTab = 'register'"
              >
                注册
              </div>
            </div>
          </div>

          <!-- 登录表单 -->
          <transition name="form-fade" mode="out-in">
            <!-- transition 必须只有一个根节点；登录表单与测试入口作为同一状态内容切换 -->
            <div v-if="activeTab === 'login'" key="login">
              <el-form
              ref="loginFormRef"
              :model="loginForm"
              :rules="loginRules"
              class="login-form"
              :class="{ 'shake-animation': loginShake }"
              @keyup.enter="handleLogin"
            >
              <el-form-item prop="username">
                <el-input
                  v-model="loginForm.username"
                  placeholder="请输入用户名或邮箱"
                  size="large"
                  :prefix-icon="User"
                  clearable
                />
              </el-form-item>
              <el-form-item prop="password">
                <el-input
                  v-model="loginForm.password"
                  type="password"
                  placeholder="请输入密码"
                  size="large"
                  show-password
                  :prefix-icon="Lock"
                />
              </el-form-item>
              <el-form-item>
                <el-button
                  type="primary"
                  size="large"
                  class="submit-btn"
                  :loading="loginLoading"
                  @click="handleLogin"
                >
                  <span class="btn-text">登 录</span>
                </el-button>
              </el-form-item>
              </el-form>

              <!-- 快捷登录：一键填充不同角色账户，便于测试 -->
              <div class="quick-login">
              <div class="quick-login-divider">
                <span>快捷登录（测试用）</span>
              </div>
              <div class="quick-login-buttons">
                <button
                  v-for="account in quickAccounts"
                  :key="account.username"
                  type="button"
                  class="quick-login-btn"
                  :class="`quick-${account.role}`"
                  :disabled="loginLoading"
                  @click="quickLogin(account.username, account.password)"
                >
                  <el-icon :size="14"><component :is="account.icon" /></el-icon>
                  <span>{{ account.label }}</span>
                </button>
              </div>
              </div>
            </div>

            <!-- 注册表单 -->
            <el-form
              v-else
              key="register"
              ref="registerFormRef"
              :model="registerForm"
              :rules="registerRules"
              class="login-form"
              :class="{ 'shake-animation': registerShake }"
              @keyup.enter="handleRegister"
            >
              <el-form-item prop="username">
                <el-input
                  v-model="registerForm.username"
                  placeholder="请输入用户名（3-50个字符）"
                  size="large"
                  :prefix-icon="User"
                  clearable
                />
              </el-form-item>
              <el-form-item prop="email">
                <el-input
                  v-model="registerForm.email"
                  placeholder="请输入邮箱地址"
                  size="large"
                  :prefix-icon="Message"
                  clearable
                />
              </el-form-item>
              <el-form-item prop="password">
                <el-input
                  v-model="registerForm.password"
                  type="password"
                  placeholder="请输入密码（至少6位）"
                  size="large"
                  show-password
                  :prefix-icon="Lock"
                />
              </el-form-item>
              <el-form-item prop="confirmPassword">
                <el-input
                  v-model="registerForm.confirmPassword"
                  type="password"
                  placeholder="请再次输入密码"
                  size="large"
                  show-password
                  :prefix-icon="Lock"
                />
              </el-form-item>
              <el-form-item>
                <el-button
                  type="primary"
                  size="large"
                  class="submit-btn"
                  :loading="registerLoading"
                  @click="handleRegister"
                >
                  <span class="btn-text">注 册</span>
                </el-button>
              </el-form-item>
            </el-form>
          </transition>

          <!-- 分隔线 -->
          <div class="form-divider">
            <span class="divider-line"></span>
            <span class="divider-text">安全登录</span>
            <span class="divider-line"></span>
          </div>

          <!-- 安全提示 -->
          <div class="security-hint">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="11" width="18" height="11" rx="2"/>
              <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
            </svg>
            <span>您的数据通过SSL加密传输，安全无忧</span>
          </div>
        </div>

        <!-- 底部版权 -->
        <div class="form-footer">
          <!-- 版权年份动态获取当前年份，避免每年手动维护 -->
          <span>© {{ new Date().getFullYear() }} 智法通 · 企业级智能法律顾问平台</span>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage, FormInstance, FormRules } from 'element-plus'
import { User, Lock, Message } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

// ==================== 当前标签页 ====================
const activeTab = ref('login')

// ==================== 表单验证抖动 ====================
const loginShake = ref(false)
const registerShake = ref(false)

/** 触发表单抖动动画（验证失败时） */
const triggerShake = (type: 'login' | 'register') => {
  if (type === 'login') {
    loginShake.value = true
    setTimeout(() => { loginShake.value = false }, 600)
  } else {
    registerShake.value = true
    setTimeout(() => { registerShake.value = false }, 600)
  }
}

// ==================== 登录表单 ====================
const loginFormRef = ref<FormInstance>()
const loginLoading = ref(false)
const loginForm = reactive({
  username: '',
  password: '',
})

const loginRules: FormRules = {
  username: [{ required: true, message: '请输入用户名或邮箱', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

/** 处理登录请求 */
const handleLogin = async () => {
  const valid = await loginFormRef.value?.validate().catch(() => false)
  if (!valid) {
    triggerShake('login')
    return
  }

  loginLoading.value = true
  try {
    await userStore.login(loginForm.username, loginForm.password)
    ElMessage.success('登录成功')
    const redirect = (route.query.redirect as string) || '/dashboard'
    router.push(redirect)
  } catch (error: any) {
    triggerShake('login')
    ElMessage.error(error?.response?.data?.message || '登录失败，请检查用户名和密码')
  } finally {
    loginLoading.value = false
  }
}

// ==================== 快捷登录（测试便捷入口） ====================
// 三种角色一键登录：管理员/法务/普通用户，避免手动输入凭据
const quickAccounts = [
  { label: '管理员', username: 'admin', password: 'admin123', role: 'admin', icon: 'UserFilled' },
  { label: '法务', username: 'lawyer', password: 'lawyer123', role: 'lawyer', icon: 'OfficeBuilding' },
  { label: '普通用户', username: 'user', password: 'user123456', role: 'user', icon: 'User' },
]

/** 快捷登录：自动填充凭据并触发表单提交 */
const quickLogin = async (username: string, password: string) => {
  loginForm.username = username
  loginForm.password = password
  await nextTick()
  await handleLogin()
}

// ==================== 注册表单 ====================
const registerFormRef = ref<FormInstance>()
const registerLoading = ref(false)
const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
})

/** 确认密码一致性校验 */
const validateConfirmPassword = (_rule: any, value: string, callback: any) => {
  if (value !== registerForm.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const registerRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度为3-50个字符', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 50, message: '密码长度为6-50个字符', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' },
  ],
}

/** 处理注册请求 */
const handleRegister = async () => {
  const valid = await registerFormRef.value?.validate().catch(() => false)
  if (!valid) {
    triggerShake('register')
    return
  }

  registerLoading.value = true
  try {
    await userStore.register({
      username: registerForm.username,
      email: registerForm.email,
      password: registerForm.password,
    })
    ElMessage.success('注册成功')
    router.push('/dashboard')
  } catch (error: any) {
    triggerShake('register')
    ElMessage.error(error?.response?.data?.message || '注册失败，请稍后重试')
  } finally {
    registerLoading.value = false
  }
}
</script>

<style scoped lang="scss">
/* ==================== 登录页面整体布局（分屏式 · 案卷墨蓝） ==================== */
.login-page {
  width: 100vw;
  height: 100vh;
  display: flex;
  overflow: hidden;
  background: var(--bg-primary);
}

/* ==================== 左侧品牌展示区（深墨蓝 · 纸感底） ==================== */
.brand-panel {
  flex: 0 0 55%;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(162deg, #ffffff 0%, #f4f7fb 55%, #ffffff 100%);
  overflow: hidden;
}

/* 纸感光晕层（极淡鎏金 + 藏青，静态） */
.brand-paper {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(ellipse at 50% 28%, rgba(201, 169, 98, 0.05) 0%, transparent 55%),
    radial-gradient(ellipse at 50% 88%, rgba(70, 96, 140, 0.07) 0%, transparent 50%);
}

/* 卷首 / 卷尾细金线（1px 渐隐，文书卷首感） */
.brand-rule {
  position: absolute;
  left: 48px;
  right: 48px;
  height: 1px;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(201, 169, 98, 0.4) 22%,
    rgba(201, 169, 98, 0.4) 78%,
    transparent 100%
  );
  pointer-events: none;
}

.brand-rule-top {
  top: 42px;
}

.brand-rule-bottom {
  bottom: 42px;
}

/* ==================== 品牌内容区 ==================== */
.brand-content {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 460px;
  padding: 40px;
  text-align: center;
  animation: softFadeIn 0.4s ease;
}

/* 鎏金天平徽记（线稿，庄重对称） */
.brand-emblem {
  width: 96px;
  height: 96px;
  margin: 0 auto 30px;
  color: #b7791f;
  opacity: 0.92;

  svg {
    width: 100%;
    height: 100%;
    display: block;
  }
}

/* 品牌名：大号衬线 + 鎏金渐变 */
.brand-name {
  font-family: var(--font-serif);
  font-size: 44px;
  font-weight: 700;
  letter-spacing: 8px;
  margin-bottom: 14px;
  background: linear-gradient(120deg, #d99b3d 0%, #b7791f 45%, #8c5914 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* 衬线标语 */
.brand-tagline {
  font-family: var(--font-serif);
  font-size: 17px;
  letter-spacing: 4px;
  color: var(--text-secondary);
  margin-bottom: 34px;
}

/* 标语下短金线 + 菱形节点（文书分隔感） */
.brand-divider {
  position: relative;
  width: 220px;
  height: 1px;
  margin: 0 auto 30px;
  background: linear-gradient(90deg, transparent, rgba(201, 169, 98, 0.45), transparent);

  &::after {
    content: '';
    position: absolute;
    left: 50%;
    top: 50%;
    width: 5px;
    height: 5px;
    transform: translate(-50%, -50%) rotate(45deg);
    background: #f4f7fb;
    border: 1px solid rgba(201, 169, 98, 0.55);
  }
}

/* 服务说明小字 */
.brand-desc {
  font-size: 14px;
  letter-spacing: 3px;
  color: var(--text-secondary);
  margin-bottom: 10px;
}

.brand-desc-sub {
  font-size: 12px;
  letter-spacing: 1px;
  color: var(--text-muted);
}

/* 平台能力清单：让左侧品牌区具备业务信息，而不是仅作为装饰。 */
.brand-capabilities {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin: 28px auto 18px;
  text-align: left;
}

.capability-item {
  min-height: 72px;
  padding: 12px 10px;
  border: 1px solid rgba(183, 121, 31, 0.2);
  border-radius: 6px;
  background: rgba(255, 253, 248, 0.68);
  color: #526174;
  font-size: 12px;
  line-height: 1.55;
}

.capability-mark {
  display: block;
  margin-bottom: 5px;
  color: #b7791f;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.2px;
}

.brand-trust {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: #66778c;
  font-size: 11px;
  letter-spacing: 0.6px;
}

.trust-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #159a68;
  box-shadow: 0 0 0 3px rgba(21, 154, 104, 0.1);
}

/* ==================== 右侧登录表单区（深墨蓝） ==================== */
.form-panel {
  flex: 0 0 45%;
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
  border-left: 1px solid var(--border-color);
  overflow: hidden;
}

/* ==================== 登录卡片容器 ==================== */
.login-card-wrapper {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 420px;
  padding: 0 40px;
  animation: softFadeIn 0.4s ease;
}

/* ==================== 登录卡片（素净墨蓝面板 + 顶部鎏金细线） ==================== */
.login-card {
  position: relative;
  padding: 40px 36px 30px;
  border-radius: 6px;
  background: linear-gradient(168deg, #ffffff 0%, #ffffff 100%);
  border: 1px solid var(--border-color);
  box-shadow: var(--shadow-lg);

  /* 顶部鎏金细线（两侧渐隐） */
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
      rgba(201, 169, 98, 0.55) 35%,
      rgba(201, 169, 98, 0.55) 65%,
      transparent 100%
    );
    pointer-events: none;
  }
}

/* 卡片头部 */
.card-header {
  text-align: center;
  margin-bottom: 28px;
}

.card-title {
  font-family: var(--font-serif);
  font-size: 26px;
  font-weight: 600;
  letter-spacing: 6px;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.card-subtitle {
  font-size: 13px;
  letter-spacing: 1px;
  color: var(--text-muted);
}

/* ==================== 登录/注册切换 ==================== */
.tab-switch-wrapper {
  margin-bottom: 26px;
}

.tab-switch {
  display: flex;
  position: relative;
  background: rgba(244, 247, 251, 0.6);
  border-radius: 4px;
  padding: 3px;
  border: 1px solid var(--border-color);
}

/* 滑块：纯色黄铜，无发光 */
.tab-switch-indicator {
  position: absolute;
  top: 3px;
  left: 3px;
  width: calc(50% - 3px);
  height: calc(100% - 6px);
  background: #a8874a;
  border-radius: 3px;
  transition: transform 0.28s var(--ease-smooth, ease);
  z-index: 0;
}

.tab-switch-indicator.indicator-right {
  transform: translateX(100%);
}

.tab-switch-item {
  flex: 1;
  text-align: center;
  padding: 9px 0;
  font-size: 14px;
  color: var(--text-muted);
  cursor: pointer;
  position: relative;
  z-index: 1;
  transition: color 0.28s ease;
  user-select: none;

  &:hover {
    color: var(--text-secondary);
  }

  &.active {
    color: #f5efdf;
    font-weight: 600;
  }
}

/* ==================== 表单切换过渡（纯淡入淡出） ==================== */
.form-fade-enter-active,
.form-fade-leave-active {
  transition: opacity 0.25s ease;
}

.form-fade-enter-from,
.form-fade-leave-to {
  opacity: 0;
}

/* 表单验证抖动（错误反馈） */
.shake-animation {
  animation: formShake 0.5s ease-in-out;
}

@keyframes formShake {
  0%, 100% { transform: translateX(0); }
  10%, 30%, 50%, 70%, 90% { transform: translateX(-4px); }
  20%, 40%, 60%, 80% { transform: translateX(4px); }
}

/* ==================== 表单输入区 ==================== */
/* 输入框形态与金色聚焦边线由全局 Element Plus 定制提供 */
.login-form {
  .el-form-item {
    margin-bottom: 20px;
  }

  /* 自动填充深色适配（避免浏览器白色填充） */
  :deep(.el-input__inner) {
    &:-webkit-autofill {
      -webkit-box-shadow: 0 0 0 1000px #ffffff inset;
      -webkit-text-fill-color: var(--text-primary);
      caret-color: var(--accent-color);
      transition: background-color 5000s ease-in-out 0s;
    }
  }
}

/* ==================== 提交按钮（纯色黄铜） ==================== */
.submit-btn {
  width: 100%;
  height: 46px;
  font-size: 16px;
  font-weight: 600;
  font-family: var(--font-serif);
  border-radius: 4px;
  background: #a8874a !important;
  border: 1px solid rgba(220, 196, 137, 0.4) !important;
  color: #f7f2e4 !important;
  letter-spacing: 6px;
  transition: background 0.28s ease, border-color 0.28s ease;

  &:hover,
  &:focus {
    background: #b89a58 !important;
    border-color: rgba(220, 196, 137, 0.65) !important;
  }

  &:active {
    background: #96793f !important;
  }
}

.btn-text {
  position: relative;
  z-index: 1;
}

/* ==================== 快捷登录（测试入口，统一金系 hover） ==================== */
.quick-login {
  margin-top: 8px;
  margin-bottom: 12px;
}

.quick-login-divider {
  display: flex;
  align-items: center;
  text-align: center;
  margin-bottom: 12px;

  &::before,
  &::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(148, 158, 178, 0.25), transparent);
  }

  span {
    padding: 0 12px;
    font-size: 12px;
    color: var(--text-muted);
    white-space: nowrap;
    letter-spacing: 1px;
  }
}

.quick-login-buttons {
  display: flex;
  gap: 8px;
}

.quick-login-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 8px 4px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.5);
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: border-color 0.25s ease, color 0.25s ease, background 0.25s ease;

  &:hover:not(:disabled) {
    border-color: rgba(201, 169, 98, 0.45);
    color: var(--accent-light);
    background: rgba(201, 169, 98, 0.08);
  }

  &:active:not(:disabled) {
    background: rgba(201, 169, 98, 0.12);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

/* ==================== 分隔线 ==================== */
.form-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 26px 0 16px;
}

.divider-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(148, 158, 178, 0.2), transparent);
}

.divider-text {
  font-size: 11px;
  color: var(--text-muted);
  letter-spacing: 2px;
}

/* ==================== 安全提示 ==================== */
.security-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-muted);

  svg {
    width: 14px;
    height: 14px;
    color: var(--accent-dark);
  }
}

/* ==================== 底部版权 ==================== */
.form-footer {
  text-align: center;
  margin-top: 24px;
  font-size: 12px;
  letter-spacing: 1px;
  color: var(--text-muted);
}

/* ==================== 淡入动效（唯一入场动画） ==================== */
@keyframes softFadeIn {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ==================== 响应式适配 ==================== */
@media (max-width: 1200px) {
  .brand-panel { flex: 0 0 45%; }
  .form-panel { flex: 0 0 55%; }
  .brand-name { font-size: 38px; }
}

@media (max-width: 992px) {
  .brand-panel { flex: 0 0 40%; }
  .form-panel { flex: 0 0 60%; }
  .brand-content { padding: 24px; }
  .brand-rule { left: 28px; right: 28px; }
  .brand-capabilities { grid-template-columns: 1fr; max-width: 260px; }
  .capability-item { min-height: auto; padding: 8px 10px; }
  .capability-mark { display: inline; margin-right: 6px; }
}

@media (max-width: 768px) {
  .login-page {
    flex-direction: column;
  }

  .brand-panel {
    flex: 0 0 auto;
    padding: 44px 24px 36px;
  }

  .brand-rule-top { top: 20px; }
  .brand-rule-bottom { bottom: 20px; }
  .brand-content { max-width: 100%; padding: 0; }
  .brand-emblem {
    width: 72px;
    height: 72px;
    margin-bottom: 20px;
  }
  .brand-capabilities,
  .brand-trust { display: none; }

  .form-panel {
    flex: 1;
    padding: 20px;
    border-left: none;
    border-top: 1px solid var(--border-color);
  }

  .login-card-wrapper {
    max-width: 100%;
    padding: 0;
  }

  .login-card {
    padding: 28px 24px 24px;
  }
}

@media (max-width: 480px) {
  .brand-name { font-size: 32px; }
  .brand-tagline { font-size: 14px; }
  .brand-divider { width: 160px; }
  .brand-desc-sub { font-size: 11px; }
}
</style>
