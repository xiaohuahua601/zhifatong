/**
 * 智法通 - 用户管理页面（仅超级管理员可访问）
 *
 * 功能模块：
 * 1. 用户列表：分页表格，支持按用户名/邮箱/手机号搜索、按角色/状态筛选
 * 2. 创建用户：弹窗表单（用户名、邮箱、密码、手机号、角色多选、启用状态）
 * 3. 编辑用户：弹窗表单（邮箱、手机号、启用状态）
 * 4. 角色分配：弹窗多选角色（完全替换），防止取消自身admin角色
 * 5. 状态切换：一键启用/禁用，防止禁用自己
 * 6. 重置密码：弹窗输入新密码，弱密码校验
 * 7. 删除用户：二次确认，防止删除自己
 *
 * 权限说明：
 * - 后端：所有接口由 get_current_superuser 保护（仅is_superuser=True）
 * - 前端：路由meta.roles=['admin']，菜单仅admin可见
 */

<template>
  <div class="user-management-page fade-in">
    <!-- 页面级网格纹理背景层 -->
    <div class="page-grid-bg"></div>

    <div class="page-content">
      <!-- ==================== 页头：科技区块头大形态 ==================== -->
      <header class="page-header corner-brackets">
        <div class="tech-section-header header-main">
          <span class="hex-badge hex-gold header-hex">
            <el-icon><UserFilled /></el-icon>
          </span>
          <div class="header-heading">
            <span class="tech-label header-eyebrow">IDENTITY / ACCESS CONTROL</span>
            <h2 class="page-title gradient-title">用户管理</h2>
          </div>
          <span class="tsh-line"></span>
          <div class="tsh-extra">
            <span class="status-light is-on"></span>
            <span class="tech-label">SYSTEM ONLINE</span>
            <el-button type="primary" class="shimmer-btn create-btn" @click="openCreateDialog">
              <el-icon><Plus /></el-icon>
              <span>新建用户</span>
            </el-button>
          </div>
        </div>
        <div class="header-sub-row">
          <span class="diamond-node node-hollow"></span>
          <p class="page-subtitle">管理系统用户账号、角色权限与启用状态</p>
          <span class="tech-label">USER REGISTRY</span>
        </div>
      </header>

      <!-- ==================== 筛选命令条 ==================== -->
      <section class="filter-command tech-frame">
        <div class="command-rail">
          <span class="diamond-node node-cyan"></span>
          <div class="command-rail-text">
            <span class="tech-label">FILTER</span>
            <span class="command-rail-cn">筛选</span>
          </div>
        </div>
        <span class="command-divider"></span>
        <div class="command-controls">
          <!-- 关键词搜索 -->
          <el-input
            v-model="filterState.keyword"
            placeholder="搜索用户名 / 邮箱 / 手机号"
            clearable
            class="filter-search"
            :prefix-icon="Search"
            @keyup.enter="handleSearch"
            @clear="handleSearch"
          />
          <!-- 角色筛选 -->
          <el-select
            v-model="filterState.role_code"
            placeholder="全部角色"
            clearable
            class="filter-select"
            @change="handleSearch"
          >
            <el-option
              v-for="role in roles"
              :key="role.code"
              :label="role.name"
              :value="role.code"
            />
          </el-select>
          <!-- 状态筛选 -->
          <el-select
            v-model="filterState.is_active"
            placeholder="全部状态"
            clearable
            class="filter-select"
            @change="handleSearch"
          >
            <el-option label="启用" :value="true" />
            <el-option label="禁用" :value="false" />
          </el-select>
          <!-- 查询按钮 -->
          <el-button type="primary" class="command-exec" @click="handleSearch">
            <el-icon><Search /></el-icon>
            查询
          </el-button>
        </div>
        <span class="command-divider"></span>
        <el-button class="command-reset" @click="handleResetFilter">
          <el-icon><Refresh /></el-icon>
          重置
        </el-button>
      </section>

      <!-- ==================== 用户列表：科技框架外壳 ==================== -->
      <section class="table-shell tech-frame">
        <div class="table-shell-head tech-scan scan-always">
          <div class="tech-section-header">
            <span class="tsh-bar"></span>
            <span class="tsh-title">用户列表</span>
            <span class="tsh-sub">USER REGISTRY</span>
            <span class="tsh-line"></span>
            <div class="tsh-extra">
              <span class="status-light" :class="loading ? 'is-warn' : 'is-on'"></span>
              <span class="tech-label">{{ loading ? 'LOADING' : 'SYNCED' }}</span>
            </div>
          </div>
        </div>
        <div class="table-body">
          <el-table
            v-loading="loading"
            :data="users"
            style="width: 100%"
            :header-cell-style="{ background: 'rgba(23, 29, 42, 0.85)', color: '#5a76a5', fontWeight: 600 }"
            :row-style="{ background: 'transparent' }"
            empty-text="暂无用户数据"
          >
            <!-- 用户信息列（hex描边环头像+用户名+邮箱） -->
            <el-table-column label="用户" min-width="200">
              <template #default="{ row }">
                <div class="user-cell">
                  <div class="user-avatar-wrapper">
                    <div class="hex-avatar" :class="row.is_active ? 'hex-live' : 'hex-dead'">
                      <el-avatar v-if="row.avatar" :size="40" :src="row.avatar" class="hex-avatar-media" />
                      <el-avatar v-else :size="40" class="hex-avatar-media hex-avatar-fallback">
                        {{ row.username?.charAt(0)?.toUpperCase() || 'U' }}
                      </el-avatar>
                    </div>
                    <!-- 状态指示点 -->
                    <span
                      class="status-dot"
                      :class="row.is_active ? 'status-active' : 'status-disabled'"
                    ></span>
                  </div>
                  <div class="user-info-text">
                    <div class="user-name-row">
                      <span class="user-name">{{ row.username }}</span>
                      <el-tag v-if="row.is_superuser" type="danger" size="small" effect="dark" class="super-tag">超管</el-tag>
                    </div>
                    <div class="user-email">{{ row.email }}</div>
                  </div>
                </div>
              </template>
            </el-table-column>

            <!-- 手机号列 -->
            <el-table-column label="手机号" width="120" align="center">
              <template #default="{ row }">
                <span v-if="row.phone" class="phone-text">{{ row.phone }}</span>
                <span v-else class="text-muted">—</span>
              </template>
            </el-table-column>

            <!-- 角色列 -->
            <el-table-column label="角色" min-width="130">
              <template #default="{ row }">
                <div class="roles-cell">
                  <el-tag
                    v-for="role in row.roles"
                    :key="role.code"
                    :type="getRoleTagType(role.code)"
                    size="small"
                    effect="plain"
                    class="role-tag"
                  >
                    {{ role.name }}
                  </el-tag>
                  <span v-if="!row.roles || row.roles.length === 0" class="text-muted">未分配</span>
                </div>
              </template>
            </el-table-column>

            <!-- 状态列 -->
            <el-table-column label="状态" width="80" align="center">
              <template #default="{ row }">
                <el-tag :type="row.is_active ? 'success' : 'info'" size="small" effect="light">
                  {{ row.is_active ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>

            <!-- 登录/创建时间合并列（两行展示，节省横向空间） -->
            <el-table-column label="最后登录 / 创建" width="165">
              <template #default="{ row }">
                <div class="time-cell">
                  <span class="time-main">
                    <span class="time-dot" :class="row.last_login ? 'dot-recent' : 'dot-never'"></span>
                    {{ row.last_login ? formatDateTime(row.last_login) : '从未登录' }}
                  </span>
                  <span class="time-sub">创建于 {{ formatDate(row.created_at) }}</span>
                </div>
              </template>
            </el-table-column>

            <!-- 操作列：高频操作平铺 + 低频操作收进下拉菜单 -->
            <el-table-column label="操作" width="170" fixed="right" align="center">
              <template #default="{ row }">
                <div class="action-cell">
                  <el-button link type="primary" size="small" @click="openEditDialog(row)">
                    <el-icon><Edit /></el-icon>编辑
                  </el-button>
                  <el-button link type="warning" size="small" @click="openRoleDialog(row)">
                    <el-icon><UserFilled /></el-icon>角色
                  </el-button>
                  <el-dropdown trigger="click" @command="(cmd: string) => handleRowCommand(cmd, row)">
                    <el-button link type="info" size="small" class="more-btn">
                      更多<el-icon class="el-icon--right"><ArrowDown /></el-icon>
                    </el-button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item command="resetPassword">
                          <el-icon><Key /></el-icon>重置密码
                        </el-dropdown-item>
                        <el-dropdown-item
                          command="toggleStatus"
                          :disabled="row.id === currentUserId"
                        >
                          <el-icon><Lock v-if="row.is_active" /><Unlock v-else /></el-icon>
                          {{ row.is_active ? '禁用账号' : '启用账号' }}
                        </el-dropdown-item>
                        <el-dropdown-item
                          command="delete"
                          divided
                          :disabled="row.id === currentUserId"
                        >
                          <span class="dropdown-danger"><el-icon><Delete /></el-icon>删除用户</span>
                        </el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- 分页：左侧总数读出 + 右侧分页器 -->
        <div class="pagination-wrapper">
          <div class="pagination-readout">
            <span class="tech-label">TOTAL / 记录总数</span>
            <span class="readout-box">
              <span class="data-readout">{{ pagination.total }}</span>
            </span>
          </div>
          <el-pagination
            v-model:current-page="pagination.page"
            v-model:page-size="pagination.page_size"
            :page-sizes="[10, 20, 50, 100]"
            :total="pagination.total"
            layout="total, sizes, prev, pager, next, jumper"
            background
            @size-change="handleSizeChange"
            @current-change="handlePageChange"
          />
        </div>
      </section>

      <!-- ==================== 创建用户对话框 ==================== -->
      <el-dialog
        v-model="createDialogVisible"
        width="520px"
        :close-on-click-modal="false"
        destroy-on-close
        class="custom-dialog"
      >
        <template #header>
          <div class="tech-section-header dialog-header">
            <span class="hex-badge dialog-hex"><el-icon><Plus /></el-icon></span>
            <span class="tsh-title">新建用户</span>
            <span class="tsh-sub">CREATE USER</span>
            <span class="tsh-line"></span>
          </div>
        </template>
        <el-form
          ref="createFormRef"
          :model="createForm"
          :rules="createRules"
          label-width="90px"
          label-position="right"
        >
          <el-form-item label="用户名" prop="username">
            <el-input v-model="createForm.username" placeholder="3-50位字符" maxlength="50" clearable />
          </el-form-item>
          <el-form-item label="邮箱" prop="email">
            <el-input v-model="createForm.email" placeholder="请输入邮箱" clearable />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input
              v-model="createForm.password"
              type="password"
              placeholder="6-50位，需包含字母和数字"
              show-password
              clearable
            />
          </el-form-item>
          <el-form-item label="手机号" prop="phone">
            <el-input v-model="createForm.phone" placeholder="可选" clearable />
          </el-form-item>
          <el-form-item label="角色" prop="role_codes">
            <el-select
              v-model="createForm.role_codes"
              multiple
              placeholder="请选择角色"
              style="width: 100%"
            >
              <el-option
                v-for="role in roles"
                :key="role.code"
                :label="`${role.name}（${role.description || role.code}）`"
                :value="role.code"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="启用状态">
            <el-switch v-model="createForm.is_active" active-text="启用" inactive-text="禁用" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="createDialogVisible = false">取消</el-button>
          <el-button type="primary" class="dialog-confirm" :loading="submitLoading" @click="handleCreate">确认创建</el-button>
        </template>
      </el-dialog>

      <!-- ==================== 编辑用户对话框 ==================== -->
      <el-dialog
        v-model="editDialogVisible"
        width="480px"
        :close-on-click-modal="false"
        destroy-on-close
        class="custom-dialog"
      >
        <template #header>
          <div class="tech-section-header dialog-header">
            <span class="hex-badge hex-ghost dialog-hex"><el-icon><Edit /></el-icon></span>
            <span class="tsh-title">编辑用户</span>
            <span class="tsh-sub">EDIT USER</span>
            <span class="tsh-line"></span>
          </div>
        </template>
        <el-form
          ref="editFormRef"
          :model="editForm"
          :rules="editRules"
          label-width="90px"
          label-position="right"
        >
          <el-form-item label="用户名">
            <el-input :value="editForm.username" disabled />
          </el-form-item>
          <el-form-item label="邮箱" prop="email">
            <el-input v-model="editForm.email" placeholder="请输入邮箱" clearable />
          </el-form-item>
          <el-form-item label="手机号" prop="phone">
            <el-input v-model="editForm.phone" placeholder="可选，清空则移除" clearable />
          </el-form-item>
          <el-form-item label="启用状态">
            <el-switch
              v-model="editForm.is_active"
              active-text="启用"
              inactive-text="禁用"
              :disabled="editForm.id === currentUserId"
            />
            <span v-if="editForm.id === currentUserId" class="form-hint">不能禁用当前登录账号</span>
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" class="dialog-confirm" :loading="submitLoading" @click="handleEdit">保存修改</el-button>
        </template>
      </el-dialog>

      <!-- ==================== 角色分配对话框 ==================== -->
      <el-dialog
        v-model="roleDialogVisible"
        width="480px"
        :close-on-click-modal="false"
        destroy-on-close
        class="custom-dialog"
      >
        <template #header>
          <div class="tech-section-header dialog-header">
            <span class="hex-badge hex-cyan dialog-hex"><el-icon><UserFilled /></el-icon></span>
            <span class="tsh-title">分配角色</span>
            <span class="tsh-sub">ASSIGN ROLES</span>
            <span class="tsh-line"></span>
          </div>
        </template>
        <div class="role-assign-header">
          <span class="role-assign-user">{{ roleForm.username }}</span>
          <span class="role-assign-hint">勾选角色后将完全替换该用户现有角色</span>
        </div>
        <el-checkbox-group v-model="roleForm.role_codes" class="role-checkbox-group">
          <el-checkbox
            v-for="role in roles"
            :key="role.code"
            :label="role.code"
            class="role-checkbox-item"
          >
            <div class="role-checkbox-content">
              <span class="role-name">{{ role.name }}</span>
              <span class="role-desc">{{ role.description || role.code }}</span>
            </div>
          </el-checkbox>
        </el-checkbox-group>
        <template #footer>
          <el-button @click="roleDialogVisible = false">取消</el-button>
          <el-button type="primary" class="dialog-confirm" :loading="submitLoading" @click="handleAssignRoles">确认分配</el-button>
        </template>
      </el-dialog>

      <!-- ==================== 重置密码对话框 ==================== -->
      <el-dialog
        v-model="resetPwdDialogVisible"
        width="440px"
        :close-on-click-modal="false"
        destroy-on-close
        class="custom-dialog"
      >
        <template #header>
          <div class="tech-section-header dialog-header">
            <span class="hex-badge hex-pink dialog-hex"><el-icon><Key /></el-icon></span>
            <span class="tsh-title">重置密码</span>
            <span class="tsh-sub">RESET PASSWORD</span>
            <span class="tsh-line"></span>
          </div>
        </template>
        <div class="reset-pwd-header">
          <el-icon class="reset-pwd-icon"><WarningFilled /></el-icon>
          <span>将为用户 <strong>{{ resetPwdForm.username }}</strong> 重置密码，无需原密码</span>
        </div>
        <el-form
          ref="resetPwdFormRef"
          :model="resetPwdForm"
          :rules="resetPwdRules"
          label-width="90px"
        >
          <el-form-item label="新密码" prop="password">
            <el-input
              v-model="resetPwdForm.password"
              type="password"
              placeholder="6-50位，需包含字母和数字"
              show-password
              clearable
            />
          </el-form-item>
          <el-form-item label="确认密码" prop="confirmPassword">
            <el-input
              v-model="resetPwdForm.confirmPassword"
              type="password"
              placeholder="请再次输入新密码"
              show-password
              clearable
            />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="resetPwdDialogVisible = false">取消</el-button>
          <el-button type="primary" class="dialog-confirm" :loading="submitLoading" @click="handleResetPassword">确认重置</el-button>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  Plus, Search, Refresh, Edit, Delete, Key, UserFilled,
  Lock, Unlock, WarningFilled, ArrowDown,
} from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import {
  userApi, type UserManageItem, type Role, type UserListParams,
} from '@/api/user'

// ==================== 状态定义 ====================

const userStore = useUserStore()

// 当前登录用户ID（用于禁用"操作自己"按钮）
const currentUserId = computed(() => userStore.userInfo?.id || 0)

// 列表数据
const loading = ref(false)
const users = ref<UserManageItem[]>([])
const roles = ref<Role[]>([])

// 分页与筛选
const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0,
})

const filterState = reactive({
  keyword: '',
  role_code: '',
  is_active: undefined as boolean | undefined,
})

// 提交按钮loading
const submitLoading = ref(false)

// ==================== 对话框状态 ====================

// 创建用户
const createDialogVisible = ref(false)
const createFormRef = ref<FormInstance>()
const createForm = reactive({
  username: '',
  email: '',
  password: '',
  phone: '',
  role_codes: ['user'] as string[],
  is_active: true,
})

// 编辑用户
const editDialogVisible = ref(false)
const editFormRef = ref<FormInstance>()
const editForm = reactive({
  id: 0,
  username: '',
  email: '',
  phone: '',
  is_active: true,
})

// 角色分配
const roleDialogVisible = ref(false)
const roleForm = reactive({
  id: 0,
  username: '',
  role_codes: [] as string[],
})

// 重置密码
const resetPwdDialogVisible = ref(false)
const resetPwdFormRef = ref<FormInstance>()
const resetPwdForm = reactive({
  id: 0,
  username: '',
  password: '',
  confirmPassword: '',
})

// ==================== 表单校验规则 ====================

// 自定义密码校验：至少6位，包含字母和数字
const validatePassword = (_rule: any, value: string, callback: any) => {
  if (!value) {
    callback(new Error('请输入密码'))
  } else if (value.length < 6) {
    callback(new Error('密码长度至少6位'))
  } else if (!/[a-zA-Z]/.test(value) || !/\d/.test(value)) {
    callback(new Error('密码需同时包含字母和数字'))
  } else {
    callback()
  }
}

// 手机号校验
const validatePhone = (_rule: any, value: string, callback: any) => {
  if (!value) {
    callback() // 手机号可选
  } else if (!/^1[3-9]\d{9}$/.test(value)) {
    callback(new Error('请输入有效的手机号'))
  } else {
    callback()
  }
}

const createRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '长度3-50位字符', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  password: [{ required: true, validator: validatePassword, trigger: 'blur' }],
  phone: [{ validator: validatePhone, trigger: 'blur' }],
  role_codes: [{ required: true, message: '请至少选择一个角色', trigger: 'change' }],
}

const editRules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  phone: [{ validator: validatePhone, trigger: 'blur' }],
}

const resetPwdRules: FormRules = {
  password: [{ required: true, validator: validatePassword, trigger: 'blur' }],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value !== resetPwdForm.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
}

// ==================== 工具函数 ====================

/**
 * 格式化日期时间
 */
const formatDateTime = (dateStr: string): string => {
  const date = new Date(dateStr)
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  const h = String(date.getHours()).padStart(2, '0')
  const min = String(date.getMinutes()).padStart(2, '0')
  return `${y}-${m}-${d} ${h}:${min}`
}

/**
 * 格式化日期（仅年月日，用于次要信息行）
 */
const formatDate = (dateStr: string): string => {
  const date = new Date(dateStr)
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

/**
 * 操作列下拉菜单命令分发
 */
const handleRowCommand = (command: string, row: UserManageItem) => {
  switch (command) {
    case 'resetPassword':
      openResetPasswordDialog(row)
      break
    case 'toggleStatus':
      handleToggleStatus(row)
      break
    case 'delete':
      handleDelete(row)
      break
  }
}

/**
 * 根据角色编码返回Tag类型（颜色）
 */
const getRoleTagType = (code: string): 'danger' | 'warning' | 'info' | 'success' | 'primary' => {
  switch (code) {
    case 'admin': return 'danger'
    case 'legal_admin': return 'warning'
    case 'user': return 'info'
    default: return 'primary'
  }
}

// ==================== 数据加载 ====================

/**
 * 加载用户列表
 */
const loadUsers = async () => {
  loading.value = true
  try {
    const params: UserListParams = {
      page: pagination.page,
      page_size: pagination.page_size,
    }
    if (filterState.keyword) params.keyword = filterState.keyword
    if (filterState.role_code) params.role_code = filterState.role_code
    if (filterState.is_active !== undefined) params.is_active = filterState.is_active

    const data = await userApi.getUsers(params)
    users.value = data.items
    pagination.total = data.total
  } catch (error) {
    console.error('加载用户列表失败：', error)
  } finally {
    loading.value = false
  }
}

/**
 * 加载角色列表（用于下拉框）
 */
const loadRoles = async () => {
  try {
    const data = await userApi.getRoles()
    roles.value = data
  } catch (error) {
    console.error('加载角色列表失败：', error)
  }
}

// ==================== 筛选与分页 ====================

const handleSearch = () => {
  pagination.page = 1
  loadUsers()
}

const handleResetFilter = () => {
  filterState.keyword = ''
  filterState.role_code = ''
  filterState.is_active = undefined
  pagination.page = 1
  loadUsers()
}

const handleSizeChange = (size: number) => {
  pagination.page_size = size
  pagination.page = 1
  loadUsers()
}

const handlePageChange = (page: number) => {
  pagination.page = page
  loadUsers()
}

// ==================== 创建用户 ====================

const openCreateDialog = () => {
  // 重置表单
  createForm.username = ''
  createForm.email = ''
  createForm.password = ''
  createForm.phone = ''
  createForm.role_codes = ['user']
  createForm.is_active = true
  createFormRef.value?.resetFields()
  createDialogVisible.value = true
}

const handleCreate = async () => {
  if (!createFormRef.value) return
  await createFormRef.value.validate(async (valid) => {
    if (!valid) return
    submitLoading.value = true
    try {
      await userApi.createUser({
        username: createForm.username,
        email: createForm.email,
        password: createForm.password,
        phone: createForm.phone || undefined,
        role_codes: createForm.role_codes,
        is_active: createForm.is_active,
      })
      ElMessage.success('用户创建成功')
      createDialogVisible.value = false
      loadUsers()
    } catch (error) {
      // 错误信息已由Axios拦截器统一弹出
      console.error('创建用户失败：', error)
    } finally {
      submitLoading.value = false
    }
  })
}

// ==================== 编辑用户 ====================

const openEditDialog = (row: UserManageItem) => {
  editForm.id = row.id
  editForm.username = row.username
  editForm.email = row.email
  editForm.phone = row.phone || ''
  editForm.is_active = row.is_active
  editFormRef.value?.resetFields()
  editDialogVisible.value = true
}

const handleEdit = async () => {
  if (!editFormRef.value) return
  await editFormRef.value.validate(async (valid) => {
    if (!valid) return
    submitLoading.value = true
    try {
      await userApi.updateUser(editForm.id, {
        email: editForm.email,
        phone: editForm.phone || undefined,
        is_active: editForm.is_active,
      })
      ElMessage.success('用户信息已更新')
      editDialogVisible.value = false
      loadUsers()
    } catch (error) {
      console.error('编辑用户失败：', error)
    } finally {
      submitLoading.value = false
    }
  })
}

// ==================== 角色分配 ====================

const openRoleDialog = (row: UserManageItem) => {
  roleForm.id = row.id
  roleForm.username = row.username
  roleForm.role_codes = row.roles.map((r) => r.code)
  roleDialogVisible.value = true
}

const handleAssignRoles = async () => {
  if (roleForm.role_codes.length === 0) {
    ElMessage.warning('请至少选择一个角色')
    return
  }
  submitLoading.value = true
  try {
    await userApi.assignRoles(roleForm.id, { role_codes: roleForm.role_codes })
    ElMessage.success('角色分配成功')
    roleDialogVisible.value = false
    loadUsers()
  } catch (error) {
    console.error('角色分配失败：', error)
  } finally {
    submitLoading.value = false
  }
}

// ==================== 状态切换 ====================

const handleToggleStatus = async (row: UserManageItem) => {
  const action = row.is_active ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(
      `确定要${action}用户「${row.username}」吗？`,
      `${action}确认`,
      {
        confirmButtonText: `确定${action}`,
        cancelButtonText: '取消',
        type: row.is_active ? 'warning' : 'success',
      },
    )
    await userApi.updateUserStatus(row.id, { is_active: !row.is_active })
    ElMessage.success(`已${action}用户`)
    loadUsers()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('切换状态失败：', error)
    }
  }
}

// ==================== 重置密码 ====================

const openResetPasswordDialog = (row: UserManageItem) => {
  resetPwdForm.id = row.id
  resetPwdForm.username = row.username
  resetPwdForm.password = ''
  resetPwdForm.confirmPassword = ''
  resetPwdFormRef.value?.resetFields()
  resetPwdDialogVisible.value = true
}

const handleResetPassword = async () => {
  if (!resetPwdFormRef.value) return
  await resetPwdFormRef.value.validate(async (valid) => {
    if (!valid) return
    submitLoading.value = true
    try {
      await userApi.resetPassword(resetPwdForm.id, resetPwdForm.password)
      ElMessage.success('密码已重置')
      resetPwdDialogVisible.value = false
    } catch (error) {
      console.error('重置密码失败：', error)
    } finally {
      submitLoading.value = false
    }
  })
}

// ==================== 删除用户 ====================

const handleDelete = async (row: UserManageItem) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除用户「${row.username}」吗？此操作不可恢复！`,
      '删除确认',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'error',
        confirmButtonClass: 'el-button--danger',
      },
    )
    await userApi.deleteUser(row.id)
    ElMessage.success('用户已删除')
    // 删除后若当前页无数据，回退一页
    if (users.value.length === 1 && pagination.page > 1) {
      pagination.page--
    }
    loadUsers()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除用户失败：', error)
    }
  }
}

// ==================== 生命周期 ====================
onMounted(() => {
  loadRoles()
  loadUsers()
})
</script>

<style scoped lang="scss">
/* ==================== 页面容器（网格纹理底 + 内容浮层） ==================== */
.user-management-page {
  width: 100%;
  max-width: 1400px;
  margin: 0 auto;
  position: relative;
}

.page-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

/* ==================== 页头：科技区块头大形态 ==================== */
.page-header {
  position: relative;
  padding: 18px 22px 14px;
  border: 1px solid rgba(90, 118, 165, 0.2);
  background:
    linear-gradient(90deg, rgba(70, 96, 140, 0.14), transparent 55%),
    linear-gradient(160deg, rgba(23, 29, 42, 0.62), rgba(17, 21, 31, 0.45));

  .header-main {
    gap: 16px;
  }

  .header-hex {
    width: 46px;
    height: 52px;

    .el-icon {
      font-size: 22px;
    }
  }

  .header-heading {
    display: flex;
    flex-direction: column;
    gap: 5px;
    min-width: 0;
  }

  .header-eyebrow {
    color: var(--neon-cyan);
    letter-spacing: 3.5px;
  }

  .page-title {
    font-size: 25px;
    font-weight: 700;
    margin: 0;
    letter-spacing: 2px;
    line-height: 1.15;
    white-space: nowrap;
  }

  .header-sub-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 14px;
    padding-top: 12px;
    border-top: 1px dashed rgba(90, 118, 165, 0.22);

    .page-subtitle {
      font-size: 13px;
      color: var(--text-secondary);
      margin: 0;
      flex: 1;
    }
  }
}

/* 渐变标题（藏青→鎏金） */
.gradient-title {
  background: var(--gradient-text);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* ==================== 筛选命令条（tech-frame 命令台形态） ==================== */
.filter-command {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 14px 18px;
  flex-wrap: wrap;

  .command-rail {
    display: flex;
    align-items: center;
    gap: 10px;
    padding-right: 2px;

    .command-rail-text {
      display: flex;
      flex-direction: column;
      gap: 3px;

      .command-rail-cn {
        font-size: 14px;
        font-weight: 700;
        color: var(--text-primary);
        letter-spacing: 6px;
      }
    }
  }

  .command-divider {
    width: 1px;
    height: 34px;
    background: linear-gradient(180deg, transparent, rgba(90, 118, 165, 0.4), transparent);
    flex-shrink: 0;
  }

  .command-controls {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
    min-width: 300px;

    .filter-search {
      flex: 1;
      min-width: 220px;
      max-width: 340px;
    }

    .filter-select {
      width: 148px;
    }
  }

  .command-exec,
  .command-reset {
    letter-spacing: 2px;
  }
}

/* ==================== 表格外壳：tech-frame 控制台形态 ==================== */
.table-shell {
  display: flex;
  flex-direction: column;

  .table-shell-head {
    position: relative;
    padding: 12px 18px;
    border-bottom: 1px solid rgba(90, 118, 165, 0.18);
    background: linear-gradient(90deg, rgba(70, 96, 140, 0.13), rgba(201, 169, 98, 0.03) 60%, transparent);
  }

  .table-body {
    padding: 10px 12px 0;
  }
}

/* ==================== 表格深度定制（表头渐变光线 + 无斑马纹统一底色） ==================== */
.table-shell {
  :deep(.el-table) {
    background: transparent;
    --el-table-border-color: rgba(90, 118, 165, 0.14);
    --el-table-header-bg-color: transparent;
    --el-table-tr-bg-color: transparent;
    --el-table-row-hover-bg-color: rgba(70, 96, 140, 0.08);
    color: var(--text-primary);

    /* 选中行高亮：藏青 */
    .current-row > td {
      background: rgba(70, 96, 140, 0.1) !important;
    }

    /* 单元格内边距 */
    .el-table__cell {
      padding: 12px 8px;
    }

    /* 表头：半透底，边框让位给渐变光线 */
    th.el-table__cell {
      background: rgba(17, 21, 31, 0.72) !important;
      border-bottom: 1px solid transparent !important;
    }

    /* 表头行底部渐变光线（藏青→鎏金→金） */
    .el-table__header-wrapper {
      position: relative;

      &::after {
        content: '';
        position: absolute;
        left: 0;
        right: 0;
        bottom: 0;
        height: 2px;
        background: linear-gradient(
          90deg,
          transparent 0%,
          rgba(90, 118, 165, 0.85) 15%,
          rgba(201, 169, 98, 0.55) 55%,
          rgba(201, 169, 98, 0.28) 82%,
          transparent 100%
        );
        pointer-events: none;
      }
    }

    /* 行底部细边框 */
    .el-table__row > td {
      border-bottom: 1px solid rgba(90, 118, 165, 0.08) !important;
    }

    /* 所有行背景统一（无斑马纹，颜色一致） */
    .el-table__row,
    .el-table__row--striped,
    .el-table__row--striped:hover > td {
      background: transparent !important;
    }
  }
}

/* ==================== 用户信息单元格（hex 描边环头像） ==================== */
.user-cell {
  display: flex;
  align-items: center;
  gap: 12px;

  .user-avatar-wrapper {
    position: relative;
    flex-shrink: 0;
    width: 46px;
    height: 46px;
  }

  /* hex 渐变描边环：外环按启用状态着色 */
  .hex-avatar {
    width: 46px;
    height: 46px;
    padding: 3px;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    justify-content: center;
    clip-path: polygon(50% 0, 100% 25%, 100% 75%, 50% 100%, 0 75%, 0 25%);
    background: linear-gradient(150deg, rgba(90, 118, 165, 0.95), rgba(201, 169, 98, 0.6));

    &.hex-dead {
      background: linear-gradient(150deg, rgba(95, 118, 153, 0.55), rgba(95, 118, 153, 0.35));
    }
  }

  /* 头像本体裁切成 hexagon，与描边环嵌套 */
  .hex-avatar :deep(.el-avatar) {
    border-radius: 0;
    clip-path: polygon(50% 0, 100% 25%, 100% 75%, 50% 100%, 0 75%, 0 25%);
  }

  /* 首字母 fallback：藏青芯 + 鎏金字 */
  .hex-avatar-fallback {
    background: linear-gradient(160deg, #1c2334, #141926) !important;
    color: var(--accent-light) !important;
    font-weight: 700;
    text-shadow: 0 0 10px rgba(90, 118, 165, 0.45);
  }

  /* 状态指示点（翡翠绿 = 启用） */
  .status-dot {
    position: absolute;
    bottom: -1px;
    right: -1px;
    width: 11px;
    height: 11px;
    border-radius: 50%;
    border: 2px solid var(--bg-primary);

    &.status-active {
      background: var(--success-color);
      box-shadow: 0 0 8px rgba(124, 165, 134, 0.7);
    }

    &.status-disabled {
      background: var(--text-muted);
    }
  }

  .user-info-text {
    flex: 1;
    min-width: 0;

    .user-name-row {
      display: flex;
      align-items: center;
      gap: 6px;

      .user-name {
        font-weight: 600;
        color: var(--text-primary);
        font-size: 14px;
      }

      .super-tag {
        transform: scale(0.85);
        transform-origin: left center;
      }
    }

    .user-email {
      font-size: 12px;
      color: var(--text-secondary);
      margin-top: 2px;
    }
  }
}

/* ==================== 角色标签 ==================== */
.roles-cell {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: center;

  .role-tag {
    margin: 0;
  }
}

/* ==================== 时间合并单元格（两行，菱形活跃节点） ==================== */
.time-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
  line-height: 1.4;

  .time-main {
    display: flex;
    align-items: center;
    gap: 7px;
    color: var(--text-secondary);
    font-size: 13px;
    font-variant-numeric: tabular-nums;
  }

  .time-sub {
    color: var(--text-muted);
    font-size: 12px;
    padding-left: 13px;
    font-variant-numeric: tabular-nums;
  }

  /* 登录活跃指示（菱形节点：鎏金 = 活跃） */
  .time-dot {
    width: 7px;
    height: 7px;
    border-radius: 1px;
    transform: rotate(45deg);
    flex-shrink: 0;

    &.dot-recent {
      background: var(--neon-cyan);
      box-shadow: 0 0 6px rgba(201, 169, 98, 0.6);
    }

    &.dot-never {
      background: var(--text-muted);
      opacity: 0.5;
    }
  }
}

/* ==================== 文本辅助类 ==================== */
.text-muted {
  color: var(--text-muted);
  font-size: 13px;
}

.phone-text {
  color: var(--text-secondary);
  font-size: 13px;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.5px;
}

/* ==================== 操作列按钮 ==================== */
.action-cell {
  display: flex;
  gap: 2px;
  justify-content: center;
  align-items: center;
  flex-wrap: nowrap;

  /* 覆盖Element Plus相邻按钮默认12px边距，统一用gap控制间距 */
  .el-button + .el-button {
    margin-left: 0;
  }
}

/* 下拉菜单中的危险操作项（玫瑰红） */
.dropdown-danger {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--el-color-danger);
}

/* ==================== 分页：左侧总数读出 + 右侧分页器 ==================== */
.pagination-wrapper {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  padding: 14px 18px 12px;
  border-top: 1px solid rgba(90, 118, 165, 0.12);

  .pagination-readout {
    display: flex;
    align-items: center;
    gap: 10px;

    .data-readout {
      font-size: 18px;
      color: var(--neon-cyan-light);
      text-shadow: 0 0 12px rgba(201, 169, 98, 0.4);
    }
  }

  :deep(.el-pagination) {
    --el-pagination-bg-color: transparent;
    --el-pagination-text-color: var(--text-secondary);
    --el-pagination-button-color: var(--text-secondary);
    --el-pagination-button-bg-color: rgba(23, 29, 42, 0.6);
    --el-pagination-hover-color: var(--accent-light);
  }
}

/* ==================== 对话框（tech-section-header 头部装饰） ==================== */
:deep(.custom-dialog) {
  .el-dialog__header {
    margin-right: 0;
    padding: 0;
    background: linear-gradient(90deg, rgba(70, 96, 140, 0.18), rgba(201, 169, 98, 0.05) 65%, transparent);
    border-bottom: 1px solid var(--border-color);
  }

  .el-dialog__body {
    padding: 22px 22px 12px;
  }

  .el-dialog__footer {
    padding: 12px 22px 18px;
    border-top: 1px solid var(--border-color);
  }
}

/* 对话框头部：hex 徽章 + 标题 + 英文眉标 + 渐变线 */
.dialog-header {
  padding: 14px 44px 14px 18px;

  .dialog-hex {
    width: 28px;
    height: 32px;

    .el-icon {
      font-size: 14px;
    }
  }

  .tsh-title {
    font-size: 16px;
  }
}

/* 确认按钮：藏青→鎏金渐变发光 */
.el-button.dialog-confirm {
  background: linear-gradient(135deg, #2a3448 0%, #46608c 50%, #c9a962 135%) !important;
  border: 1px solid rgba(124, 147, 181, 0.5) !important;
  box-shadow: 0 0 16px rgba(70, 96, 140, 0.45), 0 0 30px rgba(201, 169, 98, 0.14) !important;

  &:hover,
  &:focus {
    background: linear-gradient(135deg, #46608c 0%, #5a76a5 50%, #dcc489 135%) !important;
    border-color: rgba(124, 147, 181, 0.75) !important;
  }
}

/* ==================== 表单提示 ==================== */
.form-hint {
  margin-left: 12px;
  font-size: 12px;
  color: var(--el-color-warning);
}

/* ==================== 角色分配对话框 ==================== */
.role-assign-header {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 16px;
  padding: 12px 14px;
  background: rgba(201, 169, 98, 0.07);
  border: 1px solid rgba(201, 169, 98, 0.22);
  border-left: 3px solid var(--neon-cyan);
  clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%);

  .role-assign-user {
    font-weight: 700;
    color: var(--neon-cyan-light);
  }

  .role-assign-hint {
    font-size: 12px;
    color: var(--text-secondary);
  }
}

.role-checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.role-checkbox-item {
  display: flex;
  align-items: flex-start;
  margin-right: 0 !important;
  padding: 11px 14px;
  border: 1px solid rgba(90, 118, 165, 0.16);
  border-left: 3px solid rgba(90, 118, 165, 0.35);
  background: rgba(23, 29, 42, 0.45);
  transition: all var(--duration-normal) var(--ease-smooth);

  &:hover {
    border-color: var(--border-strong);
    border-left-color: var(--accent-color);
    background: rgba(70, 96, 140, 0.1);
  }

  .role-checkbox-content {
    display: flex;
    flex-direction: column;
    gap: 2px;

    .role-name {
      font-weight: 600;
      color: var(--text-primary);
    }

    .role-desc {
      font-size: 12px;
      color: var(--text-secondary);
    }
  }
}

/* ==================== 重置密码对话框（玫瑰红警示） ==================== */
.reset-pwd-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  margin-bottom: 18px;
  background: rgba(192, 91, 82, 0.08);
  border: 1px solid rgba(192, 91, 82, 0.25);
  border-left: 3px solid var(--danger-color);
  clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%);
  color: var(--text-secondary);
  font-size: 13px;

  .reset-pwd-icon {
    color: var(--danger-color);
    font-size: 18px;
    flex-shrink: 0;
  }
}

/* ==================== Shimmer按钮（新建用户按钮微光扫过） ==================== */
.shimmer-btn {
  position: relative;
  overflow: hidden;

  &::after {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(
      90deg,
      transparent,
      rgba(148, 158, 178, 0.28),
      transparent
    );
    animation: shimmer 2.5s infinite;
  }
}

@keyframes shimmer {
  0% { left: -100%; }
  50% { left: 100%; }
  100% { left: 100%; }
}

/* ==================== Fade-in入场动画 ==================== */
.fade-in {
  animation: fadeIn 0.5s var(--ease-smooth, ease-out);
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ==================== 响应式 ==================== */
@media (max-width: 992px) {
  .page-header .header-main {
    flex-wrap: wrap;

    .tsh-line {
      display: none;
    }
  }

  .filter-command {
    .command-rail,
    .command-divider {
      display: none;
    }

    .command-controls {
      min-width: 100%;

      .filter-search {
        max-width: 100%;
      }
    }
  }
}

@media (max-width: 768px) {
  .page-header {
    .header-main .tsh-extra {
      width: 100%;
      justify-content: flex-start;
    }

    .header-sub-row .tech-label {
      display: none;
    }
  }

  .pagination-wrapper {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
