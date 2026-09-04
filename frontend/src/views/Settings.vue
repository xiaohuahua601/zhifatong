/**
 * 智法通 - 系统设置页面（案卷墨蓝 · 鎏金典雅）
 *
 * 包含个人信息设置、密码修改和系统参数配置。
 * 结构化组件体系：tech-frame 素净面板、竖向控制轨（圆点节点 + 滑动金条）、
 * 圆形徽记、readout-box 读数、双行式表单标签等。
 */

<template>
  <div class="settings-page fade-in">
    <!-- 页面级网格纹理层 -->
    <div class="page-grid-bg"></div>

    <!-- 页头：圆形徽记 + 衬线渐变主标题 + 状态灯读数 -->
    <header class="settings-header tech-section-header tech-scan scan-always">
      <span class="hex-badge hex-ghost header-hex"><el-icon :size="18"><Monitor /></el-icon></span>
      <h2 class="page-title">{{ pageTitleText }}</h2>
      <span class="tsh-sub">{{ userStore.isUserRole ? '个人中心' : '系统控制台' }}</span>
      <span class="tsh-line"></span>
      <span class="tsh-extra">
        <span class="status-light is-on"></span>
        <span class="tech-label">安全链路</span>
      </span>
    </header>

    <div class="settings-content">
      <!-- 左侧竖向控制轨：圆点节点 + 滑动金条 -->
      <nav class="settings-tabs tech-frame">
        <div class="tech-section-header nav-header">
          <span class="tsh-bar"></span>
          <span class="tsh-title">控制台</span>
          <span class="tsh-sub">导航</span>
        </div>
        <div class="rail-body">
          <!-- 滑动金条（位置由 indicatorStyle 计算） -->
          <div class="tab-indicator" :style="indicatorStyle"></div>
          <div
            v-for="(tab, idx) in tabs"
            :key="tab.key"
            class="tab-item"
            :class="{ active: activeTab === tab.key }"
            :ref="el => tabRefs[idx] = el as HTMLElement"
            @click="activeTab = tab.key"
          >
            <span class="diamond-node node-hollow tab-node"></span>
            <span class="tab-text">
              <span class="tab-label">{{ tab.label }}</span>
              <span class="tech-label tab-code">{{ { profile: '基础资料', usage: '额度统计', logs: '操作留痕', password: '安全设置', system: '系统参数' }[tab.key] }}</span>
            </span>
            <el-icon :size="18" class="tab-icon"><component :is="tab.icon" /></el-icon>
          </div>
        </div>
        <div class="nav-footer">
          <span class="tech-label">智法通系统</span>
          <span class="diamond-node node-cyan nav-node"></span>
        </div>
      </nav>

      <!-- 右侧设置内容 -->
      <div class="settings-panel tech-frame">
        <!-- 个人信息设置 -->
        <transition name="panel-fade" mode="out-in">
          <div v-if="activeTab === 'profile'" key="profile" class="panel-content">
            <!-- 面板头：圆形徽记 + 中文标题 + 眉标 -->
            <div class="tech-section-header panel-header">
              <span class="hex-badge hex-ghost panel-hex"><el-icon :size="16"><User /></el-icon></span>
              <span class="tsh-title panel-title">个人信息</span>
              <span class="tsh-sub">基本资料</span>
              <span class="tsh-line"></span>
              <span class="tsh-extra"><span class="tech-label">身份已核验</span></span>
            </div>

            <!-- 头像上传区域：素净面板 + 静态金环头像框 -->
            <div class="avatar-section corner-brackets stagger-form-item" style="--item-delay: 0s">
              <div class="avatar-preview-wrapper">
                <!-- 当前头像预览（有头像显示图片，无头像显示首字母） -->
                <div class="avatar-preview">
                  <el-avatar v-if="userStore.userInfo?.avatar" :size="100" :src="userStore.userInfo.avatar" />
                  <el-avatar v-else :size="100" class="avatar-placeholder">
                    {{ userStore.username?.charAt(0)?.toUpperCase() || 'U' }}
                  </el-avatar>
                </div>
                <!-- 上传/裁剪操作按钮 -->
                <div class="avatar-actions">
                  <el-button type="primary" size="small" @click="triggerAvatarUpload">
                    <el-icon><Camera /></el-icon>
                    {{ userStore.userInfo?.avatar ? '更换头像' : '上传头像' }}
                  </el-button>
                  <el-button v-if="userStore.userInfo?.avatar" size="small" @click="handleRemoveAvatarPreview">
                    移除
                  </el-button>
                  <input ref="avatarInputRef" type="file" accept="image/png,image/jpeg,image/jpg,image/gif,image/webp" style="display: none" @change="handleAvatarFileChange" />
                </div>
                <p class="avatar-hint">支持 JPG、PNG、GIF、WEBP，大小不超过 5MB</p>
              </div>
            </div>

            <!-- 头像裁剪对话框 -->
            <el-dialog v-model="showCropDialog" title="裁剪头像" width="420px" :close-on-click-modal="false" destroy-on-close>
              <div class="crop-container">
                <!-- Canvas 裁剪预览区 -->
                <div class="crop-canvas-wrapper">
                  <canvas ref="cropCanvasRef" class="crop-canvas" @mousedown="startDrag" @mousemove="onDrag" @mouseup="endDrag" @mouseleave="endDrag"></canvas>
                </div>
                <!-- 裁剪框尺寸提示 -->
                <p class="crop-hint">拖动选择头像区域，将裁剪为正方形</p>
                <!-- 实时预览 -->
                <div class="crop-preview-row">
                  <span class="crop-preview-label">预览：</span>
                  <div class="crop-preview-sizes">
                    <div class="crop-preview-item">
                      <img v-if="croppedDataUrl" :src="croppedDataUrl" class="crop-preview-img large" />
                      <div v-else class="crop-preview-placeholder large"></div>
                      <span>64px</span>
                    </div>
                    <div class="crop-preview-item">
                      <img v-if="croppedDataUrl" :src="croppedDataUrl" class="crop-preview-img small" />
                      <div v-else class="crop-preview-placeholder small"></div>
                      <span>32px</span>
                    </div>
                  </div>
                </div>
              </div>
              <template #footer>
                <el-button @click="showCropDialog = false">取消</el-button>
                <el-button type="primary" :loading="avatarUploading" @click="handleUploadAvatar">确认上传</el-button>
              </template>
            </el-dialog>

            <el-form
              ref="profileFormRef"
              :model="profileForm"
              :rules="profileRules"
              label-width="100px"
              class="settings-form"
            >
              <!-- 表单项：交错淡入 + 双行式标签（眉标 + 主文字） -->
              <el-form-item label="用户名" class="stagger-form-item" style="--item-delay: 0s">
                <template #label>
                  <span class="field-label">
                    <span class="tech-label">账户标识</span>
                    <span class="field-label-text">用户名</span>
                  </span>
                </template>
                <el-input v-model="profileForm.username" disabled />
              </el-form-item>
              <el-form-item label="邮箱" prop="email" class="stagger-form-item" style="--item-delay: 0.06s">
                <template #label>
                  <span class="field-label">
                    <span class="tech-label">电子联络</span>
                    <span class="field-label-text">邮箱</span>
                  </span>
                </template>
                <el-input v-model="profileForm.email" placeholder="请输入邮箱" />
              </el-form-item>
              <el-form-item label="手机号" prop="phone" class="stagger-form-item" style="--item-delay: 0.12s">
                <template #label>
                  <span class="field-label">
                    <span class="tech-label">移动联络</span>
                    <span class="field-label-text">手机号</span>
                  </span>
                </template>
                <el-input v-model="profileForm.phone" placeholder="请输入手机号" />
              </el-form-item>
              <el-form-item label="角色" class="stagger-form-item" style="--item-delay: 0.18s">
                <template #label>
                  <span class="field-label">
                    <span class="tech-label">权限身份</span>
                    <span class="field-label-text">角色</span>
                  </span>
                </template>
                <!-- 角色字段只读置灰：禁止用户误以为可修改自身角色权限 -->
                <el-input
                  :model-value="roleDisplayText"
                  disabled
                  class="role-readonly-input"
                >
                  <template #suffix>
                    <el-icon :size="14" color="#526174"><Lock /></el-icon>
                  </template>
                </el-input>
                <span class="role-hint">角色由系统管理员分配，如需变更请联系管理员</span>
              </el-form-item>
              <el-form-item class="stagger-form-item" style="--item-delay: 0.24s">
                <el-button type="primary" @click="handleSaveProfile">
                  <transition name="check-fade">
                    <el-icon v-if="showProfileCheck" class="save-check-icon"><CircleCheck /></el-icon>
                  </transition>
                  保存修改
                </el-button>
                <!-- 重置按钮 -->
                <el-button class="reset-btn" @click="resetProfileForm">
                  <el-icon class="reset-icon"><RefreshLeft /></el-icon>
                  重置
                </el-button>
              </el-form-item>
            </el-form>

            <!-- 账号注销入口：满足《个人信息保护法》用户权益要求 -->
            <div class="account-deletion-section tech-frame stagger-form-item" style="--item-delay: 0.3s">
              <div class="deletion-info">
                <span class="hex-badge hex-pink deletion-hex"><el-icon :size="16" color="#fff"><WarningFilled /></el-icon></span>
                <div class="deletion-text">
                  <h4>账号注销 <span class="tech-label">高危操作</span></h4>
                  <p>注销后将永久删除您的个人信息、问答记录、合同数据及收藏内容，且不可恢复。</p>
                </div>
              </div>
              <el-button type="danger" plain size="small" @click="handleAccountDeletion">
                <el-icon><Delete /></el-icon>
                申请注销账号
              </el-button>
            </div>
          </div>
        </transition>

        <!-- 用量套餐统计（普通用户专属） -->
        <transition name="panel-fade" mode="out-in">
          <div v-if="activeTab === 'usage'" key="usage" class="panel-content usage-panel">
            <div class="tech-section-header panel-header">
              <span class="hex-badge hex-gold panel-hex"><el-icon :size="16"><DataAnalysis /></el-icon></span>
              <span class="tsh-title panel-title">用量套餐</span>
              <span class="tsh-sub">额度信息</span>
              <span class="tsh-line"></span>
              <span class="tsh-extra">
                <span class="status-light is-on"></span>
                <span class="tech-label">实时读数</span>
              </span>
            </div>

            <!-- 套餐基本信息 -->
            <div class="package-info tech-frame stagger-form-item" style="--item-delay: 0s">
              <div class="package-card">
                <div class="package-header">
                  <span class="hex-badge hex-gold package-hex"><el-icon :size="18" color="#1d1810"><Medal /></el-icon></span>
                  <div class="package-name-group">
                    <span class="package-name">免费体验版</span>
                    <span class="tech-label">免费套餐</span>
                  </div>
                  <el-tag type="warning" effect="dark" size="small">当前套餐</el-tag>
                </div>
                <div class="package-detail">
                  <span class="detail-label">到期时间</span>
                  <span class="readout-box"><span class="detail-value data-readout">{{ packageExpiry }}</span></span>
                </div>
              </div>
              <el-button
                type="primary"
                class="upgrade-btn"
                :disabled="currentPackageLevel >= 2"
                @click="handleUpgradeClick"
              >
                <el-icon><Top /></el-icon>
                {{ currentPackageLevel >= 2 ? '已是最高版本' : '升级套餐' }}
              </el-button>
            </div>

            <!-- 用量统计卡片 -->
            <div class="usage-cards">
              <!-- 法律问答用量 -->
              <div class="usage-card tech-frame stagger-form-item" style="--item-delay: 0.06s">
                <div class="usage-card-header">
                  <span class="hex-badge hex-cyan usage-hex"><el-icon :size="20"><ChatDotRound /></el-icon></span>
                  <div class="usage-title-group">
                    <span class="usage-title">法律问答</span>
                    <span class="tech-label">问答额度</span>
                  </div>
                  <span class="status-light" :class="qaPercentage >= 60 ? 'is-warn' : 'is-on'"></span>
                </div>
                <div class="usage-body">
                  <div class="usage-numbers readout-box">
                    <span class="used data-readout">{{ qaUsage.used }}</span>
                    <span class="divider">/</span>
                    <span class="total">{{ qaUsage.total }}</span>
                    <span class="unit">次/月</span>
                  </div>
                  <el-progress
                    :percentage="qaPercentage"
                    :stroke-width="8"
                    :color="qaPercentage >= 80 ? '#c05b52' : qaPercentage >= 60 ? '#c9973f' : '#7ca586'"
                    class="usage-progress"
                  />
                  <span class="usage-hint">本月剩余 {{ Math.max(0, qaUsage.total - qaUsage.used) }} 次</span>
                </div>
              </div>

              <!-- 合同审查用量 -->
              <div class="usage-card tech-frame stagger-form-item" style="--item-delay: 0.12s">
                <div class="usage-card-header">
                  <span class="hex-badge hex-gold usage-hex"><el-icon :size="20"><Document /></el-icon></span>
                  <div class="usage-title-group">
                    <span class="usage-title">合同审查</span>
                    <span class="tech-label">合同额度</span>
                  </div>
                  <span class="status-light" :class="contractPercentage >= 60 ? 'is-warn' : 'is-on'"></span>
                </div>
                <div class="usage-body">
                  <div class="usage-numbers readout-box">
                    <span class="used data-readout">{{ contractUsage.used }}</span>
                    <span class="divider">/</span>
                    <span class="total">{{ contractUsage.total }}</span>
                    <span class="unit">份/日</span>
                  </div>
                  <el-progress
                    :percentage="contractPercentage"
                    :stroke-width="8"
                    :color="contractPercentage >= 80 ? '#c05b52' : contractPercentage >= 60 ? '#c9973f' : '#7ca586'"
                    class="usage-progress"
                  />
                  <span class="usage-hint">今日剩余 {{ Math.max(0, contractUsage.total - contractUsage.used) }} 份</span>
                </div>
              </div>

              <!-- 存储空间用量 -->
              <div class="usage-card tech-frame stagger-form-item" style="--item-delay: 0.18s">
                <div class="usage-card-header">
                  <span class="hex-badge usage-hex"><el-icon :size="20"><FolderOpened /></el-icon></span>
                  <div class="usage-title-group">
                    <span class="usage-title">个人存储</span>
                    <span class="tech-label">存储额度</span>
                  </div>
                  <span class="status-light" :class="storagePercentage >= 60 ? 'is-warn' : 'is-on'"></span>
                </div>
                <div class="usage-body">
                  <div class="usage-numbers readout-box">
                    <span class="used data-readout">{{ formatStorage(storageUsage.used) }}</span>
                    <span class="divider">/</span>
                    <span class="total">{{ formatStorage(storageUsage.total) }}</span>
                  </div>
                  <el-progress
                    :percentage="storagePercentage"
                    :stroke-width="8"
                    :color="storagePercentage >= 80 ? '#c05b52' : storagePercentage >= 60 ? '#c9973f' : '#7ca586'"
                    class="usage-progress"
                  />
                  <span class="usage-hint">已使用 {{ storagePercentage }}%</span>
                </div>
              </div>
            </div>

            <!-- 套餐说明 -->
            <div class="package-notice stagger-form-item" style="--item-delay: 0.24s">
              <el-icon :size="14"><InfoFilled /></el-icon>
              <span>免费体验版套餐每月提供50次法律问答、每日10份合同审查、500MB个人存储空间。如需更高额度，请升级至专业版或企业版。</span>
            </div>
          </div>
        </transition>

        <!-- 操作日志（普通用户专属，仅展示本人操作记录） -->
        <transition name="panel-fade" mode="out-in">
          <div v-if="activeTab === 'logs'" key="logs" class="panel-content logs-panel">
            <div class="tech-section-header panel-header">
              <span class="hex-badge hex-cyan panel-hex"><el-icon :size="16"><List /></el-icon></span>
              <span class="tsh-title panel-title">我的操作日志</span>
              <span class="tsh-sub">操作审计</span>
              <span class="tsh-line"></span>
              <span class="tsh-extra"><span class="tech-label">留存三十日</span></span>
            </div>
            <p class="panel-subtitle">仅展示您本人的近期操作记录，满足审计合规要求</p>

            <div class="logs-summary stagger-form-item" style="--item-delay: 0s">
              <div class="logs-summary-item tech-frame">
                <span class="hex-badge hex-ghost summary-hex"><el-icon :size="18" color="#7897bf"><List /></el-icon></span>
                <div class="summary-info">
                  <span class="summary-value readout-box data-readout">{{ operationLogs.length }}</span>
                  <span class="summary-label">操作记录总数</span>
                </div>
              </div>
              <div class="logs-summary-item tech-frame">
                <span class="hex-badge hex-ghost summary-hex"><el-icon :size="18" color="#7ca586"><CircleCheck /></el-icon></span>
                <div class="summary-info">
                  <span class="summary-value readout-box data-readout">{{ operationLogs.filter(l => l.action === '登录').length }}</span>
                  <span class="summary-label">登录次数</span>
                </div>
              </div>
              <div class="logs-summary-item tech-frame">
                <span class="hex-badge hex-ghost summary-hex"><el-icon :size="18" color="#b7791f"><Document /></el-icon></span>
                <div class="summary-info">
                  <span class="summary-value readout-box data-readout">{{ operationLogs.filter(l => l.module === '合同审查').length }}</span>
                  <span class="summary-label">合同操作</span>
                </div>
              </div>
            </div>

            <el-table
              :data="operationLogs"
              style="width: 100%"
              :header-cell-style="{ background: 'rgba(255, 255, 255, 0.9)', color: '#526174', borderBottom: '1px solid rgba(201, 169, 98, 0.35)' }"
              :cell-style="{ background: 'transparent', color: '#172033', borderBottom: '1px solid rgba(148, 158, 178, 0.12)' }"
              empty-text="暂无操作记录"
            >
              <el-table-column prop="action" label="操作类型" width="120">
                <template #default="{ row }">
                  <el-tag :type="getLogActionTagType(row.action)" size="small">{{ row.action }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="module" label="功能模块" width="120">
                <template #default="{ row }">
                  <span class="log-module">{{ row.module }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="detail" label="操作详情" min-width="220" show-overflow-tooltip />
              <el-table-column prop="time" label="操作时间" width="180" />
            </el-table>

            <div class="logs-notice">
              <el-icon :size="14"><InfoFilled /></el-icon>
              <span>操作日志仅保留近30天记录，如需查看更早的记录请联系系统管理员。</span>
            </div>
          </div>
        </transition>

        <!-- 密码修改 -->
        <transition name="panel-fade" mode="out-in">
          <div v-if="activeTab === 'password'" key="password" class="panel-content">
            <div class="tech-section-header panel-header">
              <span class="hex-badge hex-pink panel-hex"><el-icon :size="16"><Lock /></el-icon></span>
              <span class="tsh-title panel-title">修改密码</span>
              <span class="tsh-sub">账户安全</span>
              <span class="tsh-line"></span>
              <span class="tsh-extra"><span class="tech-label">加密传输</span></span>
            </div>
            <el-form
              ref="passwordFormRef"
              :model="passwordForm"
              :rules="passwordRules"
              label-width="100px"
              class="settings-form"
            >
              <el-form-item label="当前密码" prop="oldPassword" class="stagger-form-item" style="--item-delay: 0s">
                <template #label>
                  <span class="field-label">
                    <span class="tech-label">当前口令</span>
                    <span class="field-label-text">当前密码</span>
                  </span>
                </template>
                <el-input v-model="passwordForm.oldPassword" type="password" show-password placeholder="请输入当前密码" />
              </el-form-item>
              <el-form-item label="新密码" prop="newPassword" class="stagger-form-item" style="--item-delay: 0.06s">
                <template #label>
                  <span class="field-label">
                    <span class="tech-label">新设口令</span>
                    <span class="field-label-text">新密码</span>
                  </span>
                </template>
                <el-input v-model="passwordForm.newPassword" type="password" show-password placeholder="请输入新密码（至少6位）" />
              </el-form-item>
              <el-form-item label="确认密码" prop="confirmPassword" class="stagger-form-item" style="--item-delay: 0.12s">
                <template #label>
                  <span class="field-label">
                    <span class="tech-label">确认口令</span>
                    <span class="field-label-text">确认密码</span>
                  </span>
                </template>
                <el-input v-model="passwordForm.confirmPassword" type="password" show-password placeholder="请再次输入新密码" />
              </el-form-item>
              <el-form-item class="stagger-form-item" style="--item-delay: 0.18s">
                <el-button type="primary" @click="handleChangePassword">修改密码</el-button>
                <el-button class="reset-btn" @click="resetPasswordForm">
                  <el-icon class="reset-icon"><RefreshLeft /></el-icon>
                  重置
                </el-button>
              </el-form-item>
            </el-form>
          </div>
        </transition>

        <!-- 系统参数配置 -->
        <transition name="panel-fade" mode="out-in">
          <div v-if="activeTab === 'system'" key="system" class="panel-content">
            <div class="tech-section-header panel-header">
              <span class="hex-badge panel-hex"><el-icon :size="16"><Setting /></el-icon></span>
              <span class="tsh-title panel-title">系统参数</span>
              <span class="tsh-sub">参数配置</span>
              <span class="tsh-line"></span>
              <span class="tsh-extra">
                <span class="status-light is-on"></span>
                <span class="tech-label">引擎就绪</span>
              </span>
            </div>
            <el-form label-width="140px" class="settings-form">
              <el-form-item label="AI回答温度" class="stagger-form-item" style="--item-delay: 0s">
                <template #label>
                  <span class="field-label">
                    <span class="tech-label">生成温度</span>
                    <span class="field-label-text">AI回答温度</span>
                  </span>
                </template>
                <!-- 滑块：鎏金轨道 -->
                <el-slider v-model="systemConfig.temperature" :min="0" :max="1" :step="0.1" show-input class="gradient-slider" />
                <!-- 参数说明添加图标装饰 -->
                <span class="form-hint hint-with-icon">
                  <el-icon :size="12"><InfoFilled /></el-icon>
                  值越高回答越有创造性，值越低回答越精确
                </span>
              </el-form-item>
              <el-form-item label="最大生成Token数" class="stagger-form-item" style="--item-delay: 0.06s">
                <template #label>
                  <span class="field-label">
                    <span class="tech-label">生成上限</span>
                    <span class="field-label-text">最大生成Token数</span>
                  </span>
                </template>
                <!-- 数字输入框 -->
                <el-input-number v-model="systemConfig.maxTokens" :min="256" :max="8192" :step="256" class="glow-input-number" />
              </el-form-item>
              <el-form-item label="检索文档数量" class="stagger-form-item" style="--item-delay: 0.12s">
                <template #label>
                  <span class="field-label">
                    <span class="tech-label">检索数量</span>
                    <span class="field-label-text">检索文档数量</span>
                  </span>
                </template>
                <el-input-number v-model="systemConfig.topK" :min="1" :max="20" class="glow-input-number" />
                <span class="form-hint hint-with-icon">
                  <el-icon :size="12"><InfoFilled /></el-icon>
                  RAG检索返回的文档片段数量
                </span>
              </el-form-item>
              <el-form-item label="分块大小" class="stagger-form-item" style="--item-delay: 0.18s">
                <template #label>
                  <span class="field-label">
                    <span class="tech-label">分块字符</span>
                    <span class="field-label-text">分块大小</span>
                  </span>
                </template>
                <el-input-number v-model="systemConfig.chunkSize" :min="100" :max="2000" :step="100" class="glow-input-number" />
                <span class="form-hint hint-with-icon">
                  <el-icon :size="12"><InfoFilled /></el-icon>
                  文档分块的字符数
                </span>
              </el-form-item>
              <el-form-item label="启用流式回答" class="stagger-form-item" style="--item-delay: 0.24s">
                <template #label>
                  <span class="field-label">
                    <span class="tech-label">流式传输</span>
                    <span class="field-label-text">启用流式回答</span>
                  </span>
                </template>
                <!-- 开关：选中态黄铜金 -->
                <el-switch
                  v-model="systemConfig.enableStream"
                  active-text="开启"
                  inactive-text="关闭"
                  class="gradient-switch"
                />
              </el-form-item>
              <el-form-item label="启用引用来源" class="stagger-form-item" style="--item-delay: 0.3s">
                <template #label>
                  <span class="field-label">
                    <span class="tech-label">引用出处</span>
                    <span class="field-label-text">启用引用来源</span>
                  </span>
                </template>
                <el-switch
                  v-model="systemConfig.enableCitations"
                  active-text="开启"
                  inactive-text="关闭"
                  class="gradient-switch"
                />
              </el-form-item>
              <el-form-item class="stagger-form-item" style="--item-delay: 0.36s">
                <el-button type="primary" @click="handleSaveSystemConfig">
                  <transition name="check-fade">
                    <el-icon v-if="showSystemCheck" class="save-check-icon"><CircleCheck /></el-icon>
                  </transition>
                  保存配置
                </el-button>
                <el-button class="reset-btn" @click="resetSystemConfig">
                  <el-icon class="reset-icon"><RefreshLeft /></el-icon>
                  恢复默认
                </el-button>
              </el-form-item>
            </el-form>
          </div>
        </transition>
      </div>
    </div>

    <!-- ==================== 升级套餐弹窗 ==================== -->
    <el-dialog
      v-model="showUpgradeDialog"
      title="升级套餐"
      width="900px"
      :close-on-click-modal="false"
      destroy-on-close
      class="upgrade-dialog"
    >
      <div class="upgrade-intro">
        <span class="hex-badge hex-gold intro-hex"><el-icon :size="16" color="#1d1810"><Medal /></el-icon></span>
        <span>选择适合您的套餐版本，升级后额度立即生效，剩余用量按比例折算。</span>
      </div>
      <div class="package-tiers">
        <div
          v-for="pkg in packageTiers"
          :key="pkg.level"
          class="package-tier-card tech-frame"
          :class="{
            current: pkg.level === currentPackageLevel,
            disabled: pkg.level < currentPackageLevel,
            featured: pkg.level === 1
          }"
        >
          <div v-if="pkg.level === currentPackageLevel" class="tier-badge current-badge">当前套餐</div>
          <div v-else-if="pkg.level === 1" class="tier-badge featured-badge">推荐</div>
          <div class="tier-head">
            <span class="hex-badge hex-ghost tier-hex"><span class="tier-hex-num">{{ pkg.level }}</span></span>
            <div class="tier-name-group">
              <span class="tier-name">{{ pkg.name }}</span>
              <span class="tech-label">{{ ['壹号档位', '贰号档位', '叁号档位'][pkg.level] || '档位' }}</span>
            </div>
          </div>
          <div class="tier-price readout-box">
            <span class="price data-readout">{{ pkg.price }}</span>
            <span class="period">{{ pkg.period }}</span>
          </div>
          <ul class="tier-features">
            <li v-for="(feat, idx) in pkg.features" :key="idx">
              <span class="diamond-node node-hollow feat-node"></span>
              <span>{{ feat }}</span>
            </li>
          </ul>
          <el-button
            v-if="pkg.level === currentPackageLevel"
            type="info"
            disabled
            class="tier-btn"
          >
            当前套餐
          </el-button>
          <el-button
            v-else-if="pkg.level < currentPackageLevel"
            type="info"
            disabled
            class="tier-btn"
          >
            低于当前版本
          </el-button>
          <el-button
            v-else
            type="primary"
            class="tier-btn"
            @click="handleSelectPackage(pkg.level)"
          >
            升级至此
          </el-button>
        </div>
      </div>
      <div class="upgrade-notice">
        <el-icon :size="14"><InfoFilled /></el-icon>
        <span>套餐升级为增值付费服务，确认后将跳转支付页面完成订购。如有疑问请联系客服。</span>
      </div>
    </el-dialog>

    <!-- ==================== 账号注销确认弹窗（由 handleAccountDeletion 内部触发，此处仅为占位） ==================== -->
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, nextTick, watch } from 'vue'
import { useUserStore } from '@/stores/user'
import { ElMessage, ElMessageBox, FormInstance, FormRules } from 'element-plus'

const userStore = useUserStore()

// ==================== 标签页 ====================
const activeTab = ref('profile')
const tabRefs = ref<HTMLElement[]>([])
// 标签页列表根据角色动态过滤：普通用户显示「个人信息」「用量套餐」「操作日志」「修改密码」，管理员/法务显示「个人信息」「修改密码」「系统参数」
const allTabs = [
  { key: 'profile', label: '个人信息', icon: 'User' },
  { key: 'usage', label: '用量套餐', icon: 'DataAnalysis' },
  { key: 'logs', label: '操作日志', icon: 'List' },
  { key: 'password', label: '修改密码', icon: 'Lock' },
  { key: 'system', label: '系统参数', icon: 'Setting' },
]
const tabs = computed(() => {
  // 普通用户：显示个人信息、用量套餐、操作日志、修改密码（隐藏系统参数）
  if (userStore.isUserRole) {
    return allTabs.filter(t => t.key !== 'system')
  }
  // 管理员/法务：显示个人信息、修改密码、系统参数（隐藏用量套餐、操作日志，管理员无个人额度限制）
  return allTabs.filter(t => !['usage', 'logs'].includes(t.key))
})

// 页面标题：普通用户显示「个人中心」，管理员/法务显示「系统设置」
const pageTitleText = computed(() => userStore.isUserRole ? '个人中心' : '系统设置')

// 角色展示文本：将角色编码映射为中文友好的显示名称
const roleDisplayText = computed(() => {
  const roleMap: Record<string, string> = {
    admin: '超级管理员',
    legal_admin: '法务负责人',
    user: '普通用户',
  }
  if (userStore.roles.length === 0) return '暂无角色'
  return userStore.roles.map(r => roleMap[r] || r).join('、')
})

// ==================== 用量套餐统计（普通用户专属） ====================
// 本月问答使用情况
const qaUsage = reactive({
  used: 0,
  total: 50, // 免费用户每月50次问答
})

// 合同审查使用情况
const contractUsage = reactive({
  used: 0,
  total: 10, // 每日10份合同审查
})

// 个人云存储占用（MB）
const storageUsage = reactive({
  used: 0,
  total: 500, // 500MB个人存储空间
})

// 套餐到期时间
const packageExpiry = ref('2026-12-31')

// 加载用量数据（从localStorage读取本地统计，实际生产应从后端获取）
const loadUsageData = () => {
  try {
    // 读取本月问答使用次数
    const qaRaw = localStorage.getItem('zhifatong_qa_usage')
    if (qaRaw) {
      const qaData = JSON.parse(qaRaw)
      const now = new Date()
      const monthKey = `${now.getFullYear()}-${now.getMonth() + 1}`
      qaUsage.used = qaData.month === monthKey ? qaData.count : 0
    }

    // 读取今日合同审查次数
    const contractRaw = localStorage.getItem('zhifatong_contract_usage')
    if (contractRaw) {
      const contractData = JSON.parse(contractRaw)
      const today = new Date().toDateString()
      contractUsage.used = contractData.date === today ? contractData.count : 0
    }

    // 读取存储占用（模拟：基于上传合同数量估算）
    const storageRaw = localStorage.getItem('zhifatong_storage_used')
    storageUsage.used = storageRaw ? parseFloat(storageRaw) : 12.5
  } catch {
    // 读取失败时使用默认值
  }
}

// 用量百分比计算
const qaPercentage = computed(() => Math.min(100, Math.round((qaUsage.used / qaUsage.total) * 100)))
const contractPercentage = computed(() => Math.min(100, Math.round((contractUsage.used / contractUsage.total) * 100)))
const storagePercentage = computed(() => Math.min(100, Math.round((storageUsage.used / storageUsage.total) * 100)))

// 格式化存储大小
const formatStorage = (mb: number) => {
  if (mb < 1) return (mb * 1024).toFixed(1) + ' KB'
  if (mb < 1024) return mb.toFixed(1) + ' MB'
  return (mb / 1024).toFixed(2) + ' GB'
}

// ==================== 升级套餐弹窗 ====================
const showUpgradeDialog = ref(false)
// 当前套餐等级（0=免费版, 1=专业版, 2=企业版）
const currentPackageLevel = ref(0)
// 套餐档位配置
const packageTiers = [
  {
    level: 0,
    name: '免费体验版',
    price: '￥0',
    period: '/永久',
    features: ['每月50次法律问答', '每日10份合同审查', '500MB个人存储', '基础法规检索'],
    current: true,
  },
  {
    level: 1,
    name: '专业个人版',
    price: '￥99',
    period: '/月',
    features: ['无限次法律问答', '每日50份合同审查', '5GB个人存储', '高级法规检索+导出', '优先客服支持'],
    current: false,
  },
  {
    level: 2,
    name: '企业版',
    price: '￥999',
    period: '/月',
    features: ['无限次法律问答', '无限合同审查', '50GB团队存储', '多人协作+权限管理', '专属法律顾问对接'],
    current: false,
  },
]

/** 点击升级套餐按钮 */
const handleUpgradeClick = () => {
  // 当前已是最高版本时提示
  if (currentPackageLevel.value >= 2) {
    ElMessage.info('您当前已是最高版本套餐（企业版）')
    return
  }
  showUpgradeDialog.value = true
}

/** 选择套餐升级 */
const handleSelectPackage = (level: number) => {
  if (level <= currentPackageLevel.value) {
    ElMessage.warning('请选择比当前更高的套餐版本')
    return
  }
  const pkg = packageTiers.find(p => p.level === level)
  ElMessageBox.confirm(
    `确认升级至「${pkg?.name}」？\n费用：${pkg?.price}${pkg?.period}\n升级后套餐额度立即生效，剩余用量按比例折算。`,
    '套餐升级确认',
    { confirmButtonText: '确认升级', cancelButtonText: '再想想', type: 'info' }
  ).then(() => {
    // 模拟升级流程（实际应跳转支付页面）
    ElMessage.success(`升级请求已提交，即将跳转支付页面完成订购「${pkg?.name}」`)
    showUpgradeDialog.value = false
  }).catch(() => {})
}

// ==================== 操作日志（普通用户专属） ====================
interface OperationLog {
  action: string
  module: string
  time: string
  detail: string
}
const operationLogs = ref<OperationLog[]>([])

/** 加载操作日志（从localStorage读取个人操作记录） */
const loadOperationLogs = () => {
  try {
    const raw = localStorage.getItem('zhifatong_operation_logs')
    operationLogs.value = raw ? JSON.parse(raw) : generateMockLogs()
  } catch {
    operationLogs.value = generateMockLogs()
  }
}

/** 生成模拟操作日志（首次访问时） */
const generateMockLogs = (): OperationLog[] => {
  const now = new Date()
  return [
    { action: '登录', module: '认证', time: new Date(now.getTime() - 3600000).toLocaleString('zh-CN'), detail: '账号密码登录' },
    { action: '法律问答', module: '问答', time: new Date(now.getTime() - 7200000).toLocaleString('zh-CN'), detail: '发起1次法律咨询' },
    { action: '合同上传', module: '合同审查', time: new Date(now.getTime() - 86400000).toLocaleString('zh-CN'), detail: '上传1份合同文件' },
    { action: '法规检索', module: '法规库', time: new Date(now.getTime() - 172800000).toLocaleString('zh-CN'), detail: '检索关键词：劳动合同' },
    { action: '收藏法规', module: '法规库', time: new Date(now.getTime() - 259200000).toLocaleString('zh-CN'), detail: '收藏《民法典》' },
  ]
}

/** 根据操作类型返回对应的标签颜色 */
const getLogActionTagType = (action: string): 'success' | 'warning' | 'info' | 'primary' | 'danger' => {
  const map: Record<string, 'success' | 'warning' | 'info' | 'primary' | 'danger'> = {
    '登录': 'success',
    '法律问答': 'primary',
    '合同上传': 'warning',
    '合同审查': 'warning',
    '法规检索': 'info',
    '收藏法规': 'info',
  }
  return map[action] || 'info'
}

// ==================== 账号注销 ====================
/** 账号注销申请 */
const handleAccountDeletion = () => {
  ElMessageBox.prompt('请输入"确认注销"以验证操作', '账号注销申请', {
    confirmButtonText: '提交注销申请',
    cancelButtonText: '取消',
    inputPlaceholder: '请输入"确认注销"',
    inputValidator: (val: string) => {
      if (val !== '确认注销') return '请准确输入"确认注销"以确认操作'
      return true
    },
  }).then(() => {
    ElMessageBox.confirm(
      '账号注销后将永久删除您的个人信息、问答记录、合同数据及收藏内容，且不可恢复。是否继续？',
      '最终确认',
      { confirmButtonText: '确认注销', cancelButtonText: '取消', type: 'error' }
    ).then(() => {
      // 模拟注销申请提交（实际应调用后端接口）
      ElMessage.success('注销申请已提交，客服将在3个工作日内联系您核实处理')
    }).catch(() => {})
  }).catch(() => {})
}

// 滑动指示器位置计算
const indicatorStyle = computed(() => {
  const idx = tabs.value.findIndex(t => t.key === activeTab.value)
  if (idx < 0) return { top: '0px', height: '0px' }
  // 指示器高度和位置基于tab索引
  const itemHeight = 48 // 每个tab项高度（padding 12*2 + 内容24）
  const gap = 4
  return {
    top: `${idx * (itemHeight + gap) + 12}px`,
    height: `${itemHeight - 8}px`,
  }
})

// ==================== 保存成功勾选动画 ====================
const showProfileCheck = ref(false)
const showSystemCheck = ref(false)

const triggerCheckAnimation = (checkRef: typeof showProfileCheck) => {
  checkRef.value = true
  setTimeout(() => {
    checkRef.value = false
  }, 1500)
}

// ==================== 个人信息表单 ====================
const profileFormRef = ref<FormInstance>()
const profileForm = reactive({
  username: '',
  email: '',
  phone: '',
})

const profileRules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
  phone: [
    { pattern: /^1[3-9]\d{9}$/, message: '请输入有效的手机号', trigger: 'blur' },
  ],
}

// 保存个人信息
const handleSaveProfile = async () => {
  const valid = await profileFormRef.value?.validate().catch(() => false)
  if (!valid) return

  try {
    // 调用API保存个人信息，成功后store自动更新
    await userStore.updateProfile({
      email: profileForm.email,
      phone: profileForm.phone || undefined,
    })
    triggerCheckAnimation(showProfileCheck)
    ElMessage.success('个人信息保存成功')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '保存失败，请重试')
  }
}

// 重置个人信息表单
const resetProfileForm = () => {
  profileForm.username = userStore.userInfo?.username || ''
  profileForm.email = userStore.userInfo?.email || ''
  profileForm.phone = userStore.userInfo?.phone || ''
}

// ==================== 密码修改表单 ====================
const passwordFormRef = ref<FormInstance>()
const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})

// 确认密码校验
const validateConfirmPassword = (_rule: any, value: string, callback: any) => {
  if (value !== passwordForm.newPassword) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const passwordRules: FormRules = {
  oldPassword: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, max: 50, message: '密码长度为6-50个字符', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' },
  ],
}

// 修改密码
const handleChangePassword = async () => {
  const valid = await passwordFormRef.value?.validate().catch(() => false)
  if (!valid) return

  try {
    // 调用API修改密码
    await userStore.changePassword(passwordForm.oldPassword, passwordForm.newPassword)
    ElMessage.success('密码修改成功，请重新登录')
    userStore.logout()
    window.location.href = '/login'
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '密码修改失败，请重试')
  }
}

// 重置密码表单
const resetPasswordForm = () => {
  passwordForm.oldPassword = ''
  passwordForm.newPassword = ''
  passwordForm.confirmPassword = ''
}

// ==================== 头像上传与裁剪 ====================
const avatarInputRef = ref<HTMLInputElement>()     // 隐藏的文件输入
const showCropDialog = ref(false)                   // 裁剪对话框可见性
const avatarUploading = ref(false)                  // 头像上传中状态
const cropCanvasRef = ref<HTMLCanvasElement>()      // 裁剪画布引用
const croppedDataUrl = ref('')                      // 裁剪后的图片Data URL
const croppedBlob = ref<Blob | null>(null)          // 裁剪后的Blob对象

// 裁剪相关状态
const cropState = reactive({
  image: null as HTMLImageElement | null,
  imgX: 0,        // 图片在画布上的x偏移
  imgY: 0,
  imgW: 0,        // 图片绘制宽度
  imgH: 0,        // 图片绘制高度
  cropSize: 200,  // 裁剪框大小（正方形边长）
  cropX: 50,      // 裁剪框左上角x
  cropY: 50,      // 裁剪框左上角y
  dragging: false,
  dragStartX: 0,
  dragStartY: 0,
})

// 触发文件选择
const triggerAvatarUpload = () => {
  avatarInputRef.value?.click()
}

// 文件选择后加载到裁剪画布
const handleAvatarFileChange = (e: Event) => {
  const input = e.target as HTMLInputElement
  if (!input.files || !input.files[0]) return

  const file = input.files[0]
  // 验证文件大小（5MB）
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.error('头像文件大小不能超过5MB')
    input.value = ''
    return
  }

  // 读取图片文件
  const reader = new FileReader()
  reader.onload = (event) => {
    const img = new Image()
    img.onload = () => {
      cropState.image = img
      showCropDialog.value = true
      // 等待对话框渲染后初始化画布
      nextTick(() => initCropCanvas())
    }
    img.src = event.target?.result as string
  }
  reader.readAsDataURL(file)
  // 重置input以便重复选择同一文件
  input.value = ''
}

// 初始化裁剪画布
const initCropCanvas = () => {
  const canvas = cropCanvasRef.value
  if (!canvas || !cropState.image) return

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const img = cropState.image
  // 画布固定尺寸
  const canvasSize = 300
  canvas.width = canvasSize
  canvas.height = canvasSize

  // 按比例缩放图片以适应画布
  const scale = Math.min(canvasSize / img.width, canvasSize / img.height)
  cropState.imgW = img.width * scale
  cropState.imgH = img.height * scale
  cropState.imgX = (canvasSize - cropState.imgW) / 2
  cropState.imgY = (canvasSize - cropState.imgH) / 2

  // 裁剪框默认居中，大小为画布的60%
  cropState.cropSize = Math.min(cropState.imgW, cropState.imgH, 180)
  cropState.cropX = (canvasSize - cropState.cropSize) / 2
  cropState.cropY = (canvasSize - cropState.cropSize) / 2

  drawCropCanvas()
  updateCroppedPreview()
}

// 绘制裁剪画布
const drawCropCanvas = () => {
  const canvas = cropCanvasRef.value
  if (!canvas || !cropState.image) return

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const size = canvas.width
  // 清空画布
  ctx.clearRect(0, 0, size, size)

  // 绘制图片
  ctx.drawImage(cropState.image, cropState.imgX, cropState.imgY, cropState.imgW, cropState.imgH)

  // 绘制半透明遮罩（裁剪框外区域）
  ctx.fillStyle = 'rgba(0, 0, 0, 0.55)'
  // 上方遮罩
  ctx.fillRect(0, 0, size, cropState.cropY)
  // 下方遮罩
  ctx.fillRect(0, cropState.cropY + cropState.cropSize, size, size - cropState.cropY - cropState.cropSize)
  // 左侧遮罩
  ctx.fillRect(0, cropState.cropY, cropState.cropX, cropState.cropSize)
  // 右侧遮罩
  ctx.fillRect(cropState.cropX + cropState.cropSize, cropState.cropY, size - cropState.cropX - cropState.cropSize, cropState.cropSize)

  // 绘制裁剪框边框
  ctx.strokeStyle = '#b7791f'
  ctx.lineWidth = 2
  ctx.strokeRect(cropState.cropX, cropState.cropY, cropState.cropSize, cropState.cropSize)

  // 绘制九宫格辅助线
  ctx.strokeStyle = 'rgba(201, 169, 98, 0.4)'
  ctx.lineWidth = 1
  const third = cropState.cropSize / 3
  for (let i = 1; i < 3; i++) {
    ctx.beginPath()
    ctx.moveTo(cropState.cropX + third * i, cropState.cropY)
    ctx.lineTo(cropState.cropX + third * i, cropState.cropY + cropState.cropSize)
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(cropState.cropX, cropState.cropY + third * i)
    ctx.lineTo(cropState.cropX + cropState.cropSize, cropState.cropY + third * i)
    ctx.stroke()
  }
}

// 拖拽裁剪框
const startDrag = (e: MouseEvent) => {
  const canvas = cropCanvasRef.value
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  const x = e.clientX - rect.left
  const y = e.clientY - rect.top
  // 判断是否在裁剪框内
  if (x >= cropState.cropX && x <= cropState.cropX + cropState.cropSize &&
      y >= cropState.cropY && y <= cropState.cropY + cropState.cropSize) {
    cropState.dragging = true
    cropState.dragStartX = x - cropState.cropX
    cropState.dragStartY = y - cropState.cropY
  }
}

const onDrag = (e: MouseEvent) => {
  if (!cropState.dragging) return
  const canvas = cropCanvasRef.value
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  const x = e.clientX - rect.left
  const y = e.clientY - rect.top

  // 计算新位置（限制在画布范围内）
  cropState.cropX = Math.max(0, Math.min(canvas.width - cropState.cropSize, x - cropState.dragStartX))
  cropState.cropY = Math.max(0, Math.min(canvas.height - cropState.cropSize, y - cropState.dragStartY))

  drawCropCanvas()
  updateCroppedPreview()
}

const endDrag = () => {
  cropState.dragging = false
}

// 更新裁剪预览
const updateCroppedPreview = () => {
  const canvas = cropCanvasRef.value
  if (!canvas || !cropState.image) return

  // 创建临时画布提取裁剪区域
  const tempCanvas = document.createElement('canvas')
  const tempCtx = tempCanvas.getContext('2d')
  if (!tempCtx) return

  // 输出尺寸为256x256（高清头像）
  const outputSize = 256
  tempCanvas.width = outputSize
  tempCanvas.height = outputSize

  // 从原图中提取裁剪区域并绘制到临时画布
  const img = cropState.image
  // 计算裁剪区域在原图中的坐标
  const scaleX = img.width / cropState.imgW
  const scaleY = img.height / cropState.imgH
  const srcX = (cropState.cropX - cropState.imgX) * scaleX
  const srcY = (cropState.cropY - cropState.imgY) * scaleY
  const srcSize = cropState.cropSize * scaleX

  tempCtx.drawImage(img, srcX, srcY, srcSize, srcSize, 0, 0, outputSize, outputSize)

  croppedDataUrl.value = tempCanvas.toDataURL('image/png')
  // 转换为Blob用于上传
  tempCanvas.toBlob((blob) => {
    croppedBlob.value = blob
  }, 'image/png')
}

// 确认上传头像
const handleUploadAvatar = async () => {
  if (!croppedBlob.value) {
    ElMessage.warning('请先选择裁剪区域')
    return
  }
  avatarUploading.value = true
  try {
    // 调用store上传头像，成功后store和App.vue头像会自动更新
    const file = new File([croppedBlob.value], 'avatar.png', { type: 'image/png' })
    await userStore.uploadAvatar(file)
    ElMessage.success('头像更新成功')
    showCropDialog.value = false
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '头像上传失败，请重试')
  } finally {
    avatarUploading.value = false
  }
}

// 移除头像：调用后端删除接口，清除用户头像
const handleRemoveAvatarPreview = () => {
  ElMessageBox.confirm('确定要移除当前头像吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(async () => {
    try {
      // 调用后端删除头像接口，store 自动更新本地 userInfo
      await userStore.removeAvatar()
      ElMessage.success('头像已移除')
    } catch (error: any) {
      ElMessage.error(error?.response?.data?.detail || '移除头像失败，请重试')
    }
  }).catch(() => {})
}

// ==================== 系统参数配置 ====================
const systemConfig = reactive({
  temperature: 0.7,
  maxTokens: 4096,
  topK: 5,
  chunkSize: 500,
  enableStream: true,
  enableCitations: true,
})

// 保存系统配置
const handleSaveSystemConfig = () => {
  // 保存到本地存储
  localStorage.setItem('systemConfig', JSON.stringify(systemConfig))
  triggerCheckAnimation(showSystemCheck)
  ElMessage.success('系统配置保存成功')
}

// 恢复默认配置
const resetSystemConfig = () => {
  systemConfig.temperature = 0.7
  systemConfig.maxTokens = 4096
  systemConfig.topK = 5
  systemConfig.chunkSize = 500
  systemConfig.enableStream = true
  systemConfig.enableCitations = true
  ElMessage.info('已恢复默认配置')
}

// ==================== 生命周期 ====================
onMounted(() => {
  // 初始化个人信息表单
  resetProfileForm()

  // 加载用量套餐数据 + 操作日志（普通用户专属）
  if (userStore.isUserRole) {
    loadUsageData()
    loadOperationLogs()
  }

  // 加载系统配置
  const savedConfig = localStorage.getItem('systemConfig')
  if (savedConfig) {
    try {
      Object.assign(systemConfig, JSON.parse(savedConfig))
    } catch {
      // 忽略解析错误
    }
  }
})
</script>

<style scoped lang="scss">
/* ==================== 系统设置页（案卷墨蓝 · 鎏金典雅） ==================== */

/* ---- 页面根：纸纹肌理背景层 + 前景内容 ---- */
.settings-page {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-height: 100%;
}

.settings-header,
.settings-content {
  position: relative;
  z-index: 1;
}

/* ---- 页头：圆形徽记 + 衬线渐变主标题 + 状态灯读数 ---- */
.settings-header {
  padding: 2px 2px 0;

  .header-hex {
    width: 34px;
    height: 34px;
  }

  .page-title {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
    font-family: var(--font-serif);
    letter-spacing: 2px;
    background: var(--gradient-text);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
}

.settings-content {
  display: flex;
  gap: 20px;
  min-height: 500px;
  align-items: stretch;
}

/* ==================== 左侧竖向控制轨（圆点节点 + 滑动金条） ==================== */
.settings-tabs {
  width: 220px;
  flex-shrink: 0;
  padding: 14px 10px 12px;
  display: flex;
  flex-direction: column;

  .nav-header {
    padding: 0 6px 12px;
  }

  /* 滑轨主体：indicatorStyle 的几何按 48px 分段 + 4px 间距 + 12px 内边距锁定 */
  .rail-body {
    position: relative;
    flex: 1;
    padding: 12px;
  }

  /* 滑动金条（top/height 由 indicatorStyle 计算） */
  .tab-indicator {
    position: absolute;
    left: 2px;
    width: 3px;
    border-radius: 2px;
    background: linear-gradient(180deg, #d99b3d, #b7791f 45%, #8c5914);
    transition: top 0.35s var(--ease-smooth, ease), height 0.35s var(--ease-smooth, ease);
    z-index: 1;
  }

  /* 控制轨分段项：石板描边素净条目 */
  .tab-item {
    display: flex;
    align-items: center;
    gap: 10px;
    height: 48px;
    margin-bottom: 4px;
    padding: 0 12px 0 10px;
    cursor: pointer;
    color: var(--text-secondary);
    background: rgba(148, 158, 178, 0.04);
    border-left: 2px solid rgba(148, 158, 178, 0.18);
    border-radius: 3px;
    transition: all var(--duration-normal, 0.32s) var(--ease-smooth, ease);

    &:hover {
      color: var(--text-primary);
      background: rgba(201, 169, 98, 0.07);
      border-left-color: rgba(201, 169, 98, 0.45);
    }

    /* 选中态：金线左边 + 背景微金 + 鎏金圆点节点 */
    &.active {
      background: rgba(201, 169, 98, 0.1);
      color: var(--text-primary);
      border-left-color: var(--accent-color);

      .tab-label {
        font-weight: 600;
      }

      .tab-code {
        color: var(--accent-light);
      }

      .tab-icon {
        color: var(--accent-light);
      }

      .tab-node {
        border: none;
        background: #b7791f;
      }
    }

    .tab-text {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
      gap: 2px;
      line-height: 1.2;

      .tab-label {
        font-size: 13.5px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .tab-code {
        font-size: 10px;
        letter-spacing: 2px;
      }
    }

    .tab-icon {
      margin-left: auto;
      color: var(--text-muted);
      transition: color var(--duration-fast, 0.16s) ease;
    }

    &:hover .tab-icon {
      color: var(--accent-light);
    }
  }

  /* 轨道底部标识 */
  .nav-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 8px 0;
    margin-top: 8px;
    border-top: 1px dashed rgba(148, 158, 178, 0.18);
  }
}

/* ==================== 右侧设置面板 ==================== */
.settings-panel {
  flex: 1;
  padding: 22px 26px 26px;
  min-width: 0;
}

/* 面板内容切换淡入动画 */
.panel-fade-enter-active {
  animation: panelFadeIn 0.4s var(--ease-smooth, ease);
}

.panel-fade-leave-active {
  animation: panelFadeOut 0.2s ease;
}

@keyframes panelFadeIn {
  from {
    opacity: 0;
    transform: translateY(14px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes panelFadeOut {
  from {
    opacity: 1;
    transform: translateY(0);
  }
  to {
    opacity: 0;
    transform: translateY(-8px);
  }
}

/* 面板头：区块头 + 底部渐变残线 */
.panel-header {
  position: relative;
  margin-bottom: 22px;
  padding-bottom: 14px;
  border-bottom: 1px solid rgba(90, 118, 165, 0.16);

  &::after {
    content: '';
    position: absolute;
    left: 0;
    bottom: -1px;
    width: 72px;
    height: 2px;
    background: linear-gradient(90deg, #4f7fc9, #b7791f);
    box-shadow: 0 0 8px rgba(90, 118, 165, 0.5);
  }

  .panel-hex {
    width: 30px;
    height: 34px;
  }

  .panel-title {
    font-size: 17px;
  }
}

/* ==================== 头像上传区（角括号取景框 + 四色旋转光环） ==================== */
.avatar-section {
  position: relative;
  display: flex;
  align-items: flex-start;
  margin-bottom: 26px;
  padding: 22px 24px;
  background: linear-gradient(160deg, rgba(255, 255, 255, 0.5), rgba(244, 247, 251, 0.72));
  border: 1px solid rgba(90, 118, 165, 0.15);
  transition: border-color var(--duration-normal, 0.32s) var(--ease-smooth, ease);

  /* 四角 L 型角括号由全局 .corner-brackets 提供 */
  &:hover {
    border-color: rgba(90, 118, 165, 0.4);
  }
}

.avatar-preview-wrapper {
  display: flex;
  align-items: center;
  gap: 22px;
  flex-wrap: wrap;
}

/* 头像预览：四色旋转光环（保留） */
.avatar-preview {
  position: relative;
  flex-shrink: 0;

  /* 预览外圈光环（藏青→鎏金→鼠尾草绿→砖红） */
  &::after {
    content: '';
    position: absolute;
    inset: -4px;
    border-radius: 50%;
    background: conic-gradient(
      from 0deg,
      #4f7fc9,
      #b7791f,
      #7ca586,
      #c05b52,
      #4f7fc9
    );
    z-index: -1;
    opacity: 0.6;
    animation: avatarRingRotate 6s linear infinite;
  }

  /* 头像占位符藏青渐变背景 */
  .avatar-placeholder {
    background: linear-gradient(135deg, #2f6fed, #5b91f2);
    color: #fff;
    font-size: 36px;
    font-weight: 700;
    box-shadow: 0 0 18px rgba(70, 96, 140, 0.35);
  }
}

@keyframes avatarRingRotate {
  to {
    transform: rotate(360deg);
  }
}

/* 头像操作按钮区 */
.avatar-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
}

/* 头像格式提示文字 */
.avatar-hint {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
  line-height: 1.6;
}

/* ==================== 头像裁剪对话框 ==================== */
.crop-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

/* 裁剪画布容器：L 型角括号取景框 */
.crop-canvas-wrapper {
  position: relative;
  padding: 10px;
  background: linear-gradient(160deg, rgba(255, 255, 255, 0.9), rgba(244, 247, 251, 0.85));
  border: 1px solid var(--border-color);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4), var(--shadow-glow);

  &::before,
  &::after {
    content: '';
    position: absolute;
    width: 14px;
    height: 14px;
    pointer-events: none;
  }

  &::before {
    top: 4px;
    left: 4px;
    border-top: 2px solid rgba(90, 118, 165, 0.65);
    border-left: 2px solid rgba(90, 118, 165, 0.65);
  }

  &::after {
    bottom: 4px;
    right: 4px;
    border-bottom: 2px solid rgba(201, 169, 98, 0.55);
    border-right: 2px solid rgba(201, 169, 98, 0.55);
  }
}

/* 裁剪画布 */
.crop-canvas {
  display: block;
  cursor: move;
  user-select: none;
  -webkit-user-drag: none;
}

/* 裁剪提示文字 */
.crop-hint {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0;
  text-align: center;
}

/* 裁剪实时预览行 */
.crop-preview-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid var(--border-color);
}

.crop-preview-label {
  font-size: 13px;
  color: var(--text-secondary);
  flex-shrink: 0;
}

/* 预览尺寸容器 */
.crop-preview-sizes {
  display: flex;
  gap: 16px;
  align-items: flex-end;
}

/* 单个预览项 */
.crop-preview-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;

  span {
    font-size: 11px;
    color: var(--text-muted);
  }
}

/* 预览图片圆形裁剪 */
.crop-preview-img {
  border-radius: 50%;
  object-fit: cover;
  border: 1px solid rgba(90, 118, 165, 0.35);
  display: block;

  &.large {
    width: 64px;
    height: 64px;
  }

  &.small {
    width: 32px;
    height: 32px;
  }
}

/* 预览占位符（未裁剪时） */
.crop-preview-placeholder {
  border-radius: 50%;
  background: repeating-conic-gradient(
    rgba(90, 118, 165, 0.14) 0deg 90deg,
    rgba(90, 118, 165, 0.05) 90deg 180deg
  );
  background-size: 12px 12px;
  border: 1px dashed rgba(90, 118, 165, 0.4);

  &.large {
    width: 64px;
    height: 64px;
  }

  &.small {
    width: 32px;
    height: 32px;
  }
}

/* ==================== 表单（双行式标签：英文眉标 + 主文字） ==================== */
.settings-form {
  max-width: 580px;

  :deep(.el-form-item__label) {
    line-height: 1.3;
    padding-right: 14px;
  }

  /* 双行式标签块 */
  .field-label {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 3px;

    .field-label-text {
      font-size: 13.5px;
      font-weight: 500;
      color: var(--text-primary);
      line-height: 1.2;
    }
  }

  /* 参数说明 */
  .form-hint {
    display: block;
    font-size: 12px;
    color: var(--text-muted);
    margin-top: 4px;
  }

  .hint-with-icon {
    display: flex;
    align-items: center;
    gap: 4px;
  }
}

/* 表单项交错入场动画 */
.stagger-form-item {
  animation: formItemSlideIn 0.4s var(--ease-smooth, ease) both;
  animation-delay: var(--item-delay, 0s);
}

@keyframes formItemSlideIn {
  from {
    opacity: 0;
    transform: translateY(14px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 保存按钮shimmer微光效果 */
.shimmer-btn {
  position: relative;
  overflow: hidden;

  &::after {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: linear-gradient(
      45deg,
      transparent 30%,
      rgba(148, 158, 178, 0.18) 50%,
      transparent 70%
    );
    animation: shimmer 3s ease-in-out infinite;
  }
}

@keyframes shimmer {
  0% { transform: translateX(-100%) rotate(45deg); }
  100% { transform: translateX(100%) rotate(45deg); }
}

/* 保存成功勾选动画 */
.save-check-icon {
  color: var(--success-color, #7ca586);
  animation: checkPop 0.4s var(--ease-spring, cubic-bezier(0.34, 1.56, 0.64, 1)) both;
  margin-right: 4px;
}

@keyframes checkPop {
  from {
    opacity: 0;
    transform: scale(0);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.check-fade-enter-active {
  animation: checkPop 0.4s var(--ease-spring, cubic-bezier(0.34, 1.56, 0.64, 1));
}

.check-fade-leave-active {
  animation: checkFade 0.3s ease;
}

@keyframes checkFade {
  to {
    opacity: 0;
    transform: scale(0.5);
  }
}

/* 重置按钮hover旋转效果 */
.reset-btn {
  .reset-icon {
    transition: transform 0.4s var(--ease-smooth, ease);
  }

  &:hover .reset-icon {
    transform: rotate(-360deg);
  }
}

/* ==================== 系统参数配置增强 ==================== */

/* 滑块藏青渐变轨道+发光滑块 */
.gradient-slider {
  :deep(.el-slider__runway) {
    background: linear-gradient(90deg, rgba(70, 96, 140, 0.2), rgba(201, 169, 98, 0.1));
  }

  :deep(.el-slider__bar) {
    background: linear-gradient(90deg, #2f6fed, #4f7fc9);
    box-shadow: 0 0 8px rgba(90, 118, 165, 0.35);
  }

  :deep(.el-slider__button) {
    border-color: var(--accent-color, #4f7fc9);
    box-shadow: 0 0 8px rgba(90, 118, 165, 0.45);
    transition: all var(--duration-normal, 0.32s) var(--ease-spring, ease);

    &:hover {
      box-shadow: 0 0 14px rgba(90, 118, 165, 0.7);
      transform: scale(1.2);
    }
  }
}

/* 数字输入框聚焦藏青发光 */
.glow-input-number {
  :deep(.el-input__wrapper) {
    transition: all var(--duration-normal, 0.32s) ease;

    &.is-focus {
      box-shadow: 0 0 12px rgba(90, 118, 165, 0.25), 0 0 4px rgba(90, 118, 165, 0.15);
    }
  }
}

/* 开关：选中态渐变发光由全局 EP 定制，此处仅补暗色未选中轨道 */
.gradient-switch {
  :deep(.el-switch__core) {
    background-color: rgba(95, 118, 153, 0.4);
    border-color: rgba(95, 118, 153, 0.4);
  }
}

/* ==================== 角色只读字段样式 ==================== */
.role-readonly-input {
  :deep(.el-input__wrapper) {
    background: rgba(90, 118, 165, 0.05);
    box-shadow: 0 0 0 1px rgba(90, 118, 165, 0.2) inset;
  }

  :deep(.el-input__inner) {
    color: var(--text-secondary, #526174);
    -webkit-text-fill-color: var(--text-secondary, #526174);
    cursor: not-allowed;
  }
}

.role-hint {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-muted, #5f7699);
  line-height: 1.5;
}

/* ==================== 用量套餐面板 ==================== */
.usage-panel {
  /* 套餐基本信息：tech-frame 外壳 + 鎏金徽章 + 读数框 */
  .package-info {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 22px;
    padding: 16px 20px;

    .package-card {
      flex: 1;
      min-width: 0;

      .package-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 10px;

        .package-hex {
          width: 36px;
          height: 40px;
        }

        .package-name-group {
          flex: 1;
          min-width: 0;
          display: flex;
          flex-direction: column;
          gap: 2px;
          line-height: 1.2;
        }

        .package-name {
          font-size: 16px;
          font-weight: 600;
          color: var(--text-primary, #172033);
        }
      }

      .package-detail {
        display: flex;
        align-items: center;
        gap: 10px;
        padding-left: 48px;
        font-size: 13px;

        .detail-label {
          color: var(--text-muted, #5f7699);
        }

        .detail-value {
          font-size: 14px;
        }
      }
    }

    .upgrade-btn {
      flex-shrink: 0;
    }
  }
}

/* 用量统计卡片：tech-frame + 六边形徽章 + readout 读数 */
.usage-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 18px;
}

.usage-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;

  .usage-card-header {
    display: flex;
    align-items: center;
    gap: 10px;

    .usage-hex {
      width: 38px;
      height: 42px;
    }

    .usage-title-group {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
      gap: 2px;
      line-height: 1.2;
    }

    .usage-title {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-primary, #172033);
    }
  }

  .usage-body {
    .usage-numbers {
      align-items: baseline;
      gap: 5px;
      margin-bottom: 10px;

      .used {
        font-size: 26px;
      }

      .divider {
        font-size: 15px;
        color: var(--text-muted, #5f7699);
      }

      .total {
        font-size: 15px;
        color: var(--text-secondary, #526174);
      }

      .unit {
        font-size: 11px;
        color: var(--text-muted, #5f7699);
        margin-left: 2px;
      }
    }

    .usage-progress {
      margin-bottom: 6px;
    }

    .usage-hint {
      font-size: 12px;
      color: var(--text-muted, #5f7699);
    }
  }
}

/* 套餐说明 */
.package-notice {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px 16px;
  background: rgba(70, 96, 140, 0.06);
  border: 1px solid rgba(90, 118, 165, 0.16);
  border-left: 2px solid var(--accent-color, #4f7fc9);
  font-size: 12px;
  color: var(--text-secondary, #526174);
  line-height: 1.6;

  :deep(.el-icon) {
    color: var(--accent-color, #4f7fc9);
    flex-shrink: 0;
    margin-top: 2px;
  }
}

/* 响应式：小屏幕用量卡片改为单列 */
@media (max-width: 900px) {
  .usage-cards {
    grid-template-columns: 1fr;
  }
}

/* ==================== 面板副标题 ==================== */
.panel-subtitle {
  margin: -8px 0 20px;
  font-size: 13px;
  color: var(--text-secondary, #526174);
}

/* ==================== 账号注销入口（tech-frame 危险区变体） ==================== */
.account-deletion-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 32px;
  padding: 16px 20px;
  /* tech-frame 提供框架+网格纹理+角括号，危险区以砖红边框与辉光标识 */
  border: 1px solid rgba(192, 91, 82, 0.32);

  &:hover {
    border-color: rgba(192, 91, 82, 0.55);
    box-shadow: 0 0 16px rgba(192, 91, 82, 0.14);
  }

  .deletion-hex {
    width: 30px;
    height: 34px;
  }

  .deletion-info {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    flex: 1;

    .deletion-text {
      h4 {
        margin: 0 0 4px;
        font-size: 14px;
        font-weight: 600;
        color: var(--danger-color, #c05b52);
      }
      p {
        margin: 0;
        font-size: 12px;
        color: var(--text-secondary, #526174);
        line-height: 1.5;
      }
    }
  }
}

/* ==================== 操作日志面板（v2：tech-frame 读数卡 + 六边形徽章） ==================== */
.logs-panel {
  .logs-summary {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin-bottom: 20px;

    /* tech-frame 提供框架/网格纹理/角括号，此处仅负责布局 */
    .logs-summary-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 14px 16px;

      &:hover {
        transform: translateY(-2px);
      }

      .summary-hex {
        width: 34px;
        height: 38px;
      }

      .summary-info {
        display: flex;
        flex-direction: column;
        gap: 4px;

        /* readout-box + data-readout 全局提供括号读数形态 */
        .summary-value {
          font-size: 20px;
        }

        .summary-label {
          font-size: 12px;
          color: var(--text-secondary, #526174);
        }
      }
    }
  }

  .log-module {
    font-size: 13px;
    color: var(--text-secondary, #526174);
  }

  /* 鎏金数据光提示条 */
  .logs-notice {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 16px;
    padding: 10px 14px;
    background: rgba(201, 169, 98, 0.05);
    border: 1px solid rgba(201, 169, 98, 0.18);
    border-left: 2px solid var(--neon-cyan, #b7791f);
    font-size: 12px;
    color: var(--text-secondary, #526174);

    :deep(.el-icon) {
      color: var(--neon-cyan, #b7791f);
      flex-shrink: 0;
    }
  }
}

@media (max-width: 900px) {
  .logs-panel .logs-summary {
    grid-template-columns: 1fr;
  }
}

/* ==================== 升级套餐弹窗（v2：tech-frame 档位卡 + readout 价格） ==================== */
.upgrade-dialog {
  .upgrade-intro {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 24px;
    padding: 12px 16px;
    background: linear-gradient(135deg, rgba(70, 96, 140, 0.1), rgba(255, 255, 255, 0.5));
    border: 1px solid rgba(90, 118, 165, 0.25);
    font-size: 13px;
    color: var(--text-secondary, #526174);

    .intro-hex {
      width: 26px;
      height: 30px;
    }
  }

  .package-tiers {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    margin-bottom: 20px;

    /* tech-frame 提供框架/网格纹理/角括号，此处仅负责布局与状态 */
    .package-tier-card {
      position: relative;
      display: flex;
      flex-direction: column;
      padding: 22px 18px;

      &:hover:not(.disabled):not(.current) {
        transform: translateY(-4px);
      }

      /* 当前套餐：翠绿边框辉光 */
      &.current {
        border-color: rgba(124, 165, 134, 0.5);
        box-shadow: 0 0 16px rgba(124, 165, 134, 0.12);
      }

      /* 推荐档位：藏青加强 */
      &.featured {
        border-color: rgba(90, 118, 165, 0.55);
        box-shadow: 0 0 18px rgba(90, 118, 165, 0.22);
      }

      &.disabled {
        opacity: 0.45;
        filter: grayscale(0.3);
      }

      /* 档位角标：平边科技标签 */
      .tier-badge {
        position: absolute;
        top: 12px;
        right: 12px;
        z-index: 2;
        padding: 2px 8px;
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 1.5px;

        &.current-badge {
          background: rgba(124, 165, 134, 0.14);
          border: 1px solid rgba(124, 165, 134, 0.5);
          color: #7ca586;
        }

        &.featured-badge {
          background: rgba(201, 169, 98, 0.12);
          border: 1px solid rgba(201, 169, 98, 0.55);
          color: #b7791f;
        }
      }

      /* 档位头：六边形序号徽章 + 名称组 */
      .tier-head {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 16px;
        padding-right: 80px;

        .tier-hex {
          width: 34px;
          height: 38px;

          .tier-hex-num {
            font-size: 15px;
          }
        }

        .tier-name-group {
          display: flex;
          flex-direction: column;
          gap: 2px;
          line-height: 1.2;
          min-width: 0;
        }

        .tier-name {
          font-size: 16px;
          font-weight: 700;
          color: var(--text-primary, #172033);
        }
      }

      /* 价格：readout-box 括号读数 + 鎏金渐变数字 */
      .tier-price {
        align-items: baseline;
        gap: 4px;
        align-self: flex-start;
        margin-bottom: 16px;

        .price {
          font-size: 26px;
          text-shadow: none;
          background: var(--gradient-gold);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }

        .period {
          font-size: 12px;
          color: var(--text-secondary, #526174);
        }
      }

      /* 特性清单：菱形节点列表 */
      .tier-features {
        list-style: none;
        padding: 0;
        margin: 0 0 18px;
        flex: 1;

        li {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 5px 0;
          font-size: 13px;
          color: var(--text-secondary, #526174);
        }
      }

      .tier-btn {
        width: 100%;
      }
    }
  }

  .upgrade-notice {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 10px 14px;
    background: rgba(90, 118, 165, 0.06);
    border: 1px solid rgba(90, 118, 165, 0.16);
    border-left: 2px solid var(--accent-color, #4f7fc9);
    font-size: 12px;
    color: var(--text-secondary, #526174);
  }
}

@media (max-width: 900px) {
  .upgrade-dialog .package-tiers {
    grid-template-columns: 1fr;
  }
}
</style>
