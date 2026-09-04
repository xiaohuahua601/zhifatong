/**
 * 智法通 - 知识库页面（法规案例检索）
 *
 * 结构化科技组件体系 v2：指挥中心命令栏 + 数据读出阵列 + 检索结果卡组。
 * 业务逻辑与上一版完全一致，仅模板结构 / 视觉形态重构。
 */

<template>
  <div class="knowledge-page fade-in">
    <!-- 页面级网格纹理层 -->
    <div class="page-grid-bg"></div>

    <div class="kp-content">
      <!-- ============ 页头：标准区块头形态 ============ -->
      <div class="page-topbar">
        <div class="tech-section-header">
          <span class="tsh-bar"></span>
          <h2 class="tsh-title">{{ pageTitleText }}</h2>
          <span class="tsh-sub">LEGAL·RETRIEVAL·MATRIX</span>
          <span class="tsh-line"></span>
          <span class="tsh-extra">
            <span class="status-light is-on"></span>
            <span class="tech-label">KB·ONLINE</span>
          </span>
        </div>
      </div>

      <!-- ============ 指挥中心命令栏（搜索 + 筛选 chips） ============ -->
      <div class="command-shell corner-brackets">
        <div class="cmd-row">
          <span class="cmd-hex hex-badge"><el-icon :size="20"><Search /></el-icon></span>
          <el-input
            v-model="searchKeyword"
            placeholder="输入关键词检索法规 / 案例 / 合同模板..."
            :prefix-icon="Search"
            clearable
            class="cmd-input"
            @keyup.enter="loadDocuments"
            @clear="loadDocuments"
          />
          <el-button type="primary" class="cmd-launch" @click="loadDocuments">
            <el-icon><Aim /></el-icon>
            <span class="launch-text">检索</span>
          </el-button>
          <!-- 上传按钮：仅管理员/法务可见（普通用户无知识库管理权限） -->
          <el-button v-if="canManage" type="primary" class="cmd-upload shimmer-btn" @click="showUploadDialog = true">
            <el-icon><Upload /></el-icon>
            上传文档
          </el-button>
        </div>

        <!-- 筛选 chips：hex 色点形态（文档类型 + 有效性） -->
        <div class="cmd-chips">
          <span class="tech-label chip-group-label">TYPE//</span>
          <button type="button" class="chip" :class="{ 'is-active': filterDocType === '' }" @click="filterDocType = ''; loadDocuments()">
            <span class="chip-dot dot-all"></span>全部
          </button>
          <button type="button" class="chip chip-purple" :class="{ 'is-active': filterDocType === '法律' }" @click="filterDocType = '法律'; loadDocuments()">
            <span class="chip-dot dot-purple"></span>法律
          </button>
          <button type="button" class="chip chip-cyan" :class="{ 'is-active': filterDocType === '法规' }" @click="filterDocType = '法规'; loadDocuments()">
            <span class="chip-dot dot-cyan"></span>法规
          </button>
          <button type="button" class="chip chip-pink" :class="{ 'is-active': filterDocType === '案例' }" @click="filterDocType = '案例'; loadDocuments()">
            <span class="chip-dot dot-pink"></span>案例
          </button>
          <button type="button" class="chip chip-gold" :class="{ 'is-active': filterDocType === '合同模板' }" @click="filterDocType = '合同模板'; loadDocuments()">
            <span class="chip-dot dot-gold"></span>合同模板
          </button>

          <span class="chip-divider"></span>

          <span class="tech-label chip-group-label">STATUS//</span>
          <button type="button" class="chip" :class="{ 'is-active': filterEffective === '' }" @click="filterEffective = ''; loadDocuments()">全部状态</button>
          <button type="button" class="chip chip-cyan" :class="{ 'is-active': filterEffective === 'effective' }" @click="filterEffective = 'effective'; loadDocuments()">
            <span class="status-light is-on"></span>现行有效
          </button>
          <button type="button" class="chip chip-off" :class="{ 'is-active': filterEffective === 'invalid' }" @click="filterEffective = 'invalid'; loadDocuments()">
            <span class="status-light is-off"></span>已失效
          </button>
        </div>
      </div>

      <!-- ============ 统计读出阵列 ============ -->
      <!-- 管理员视角：文档总数 / 分块数 / 近期上传 / 处理中 -->
      <div v-if="canManage" class="stats-row">
        <div
          v-for="(item, idx) in statItems"
          :key="idx"
          class="stat-frame tech-frame tilt-card"
          :style="{ animationDelay: `${idx * 0.1}s` }"
          @mouseenter="handleCardHover($event, true)"
          @mouseleave="handleCardHover($event, false)"
        >
          <div class="stat-hex hex-badge" :class="idx === 0 ? 'hex-cyan' : idx === 2 ? 'hex-gold' : idx === 3 ? 'hex-pink' : ''">
            <el-icon :size="18"><component :is="item.icon" /></el-icon>
          </div>
          <div class="stat-body">
            <span class="readout-box"><span class="data-readout stat-value">{{ item.displayValue }}</span></span>
            <span class="stat-label tech-label">{{ item.label }}</span>
          </div>
          <span class="status-light" :class="idx === 3 && item.displayValue > 0 ? 'is-warn' : 'is-on'"></span>
        </div>
      </div>
      <!-- 普通用户视角：我的收藏 / 本月检索（可点击交互） -->
      <div v-else class="stats-row stats-row-user">
        <div
          class="stat-frame tech-frame clickable-stat"
          :class="{ active: showFavoritesOnly }"
          style="animation-delay: 0s"
          @click="handleFavoritesCardClick"
        >
          <div class="stat-hex hex-badge hex-cyan"><el-icon :size="18"><Star /></el-icon></div>
          <div class="stat-body">
            <span class="readout-box"><span class="data-readout stat-value">{{ favoriteCount }}</span></span>
            <span class="stat-label tech-label">我的收藏</span>
            <span class="stat-click-hint">{{ showFavoritesOnly ? '点击取消筛选' : '点击筛选收藏' }}</span>
          </div>
        </div>
        <div
          class="stat-frame tech-frame clickable-stat"
          style="animation-delay: 0.1s"
          @click="handleSearchStatsCardClick"
        >
          <div class="stat-hex hex-badge"><el-icon :size="18"><Search /></el-icon></div>
          <div class="stat-body">
            <span class="readout-box"><span class="data-readout stat-value">{{ monthSearchCount }}</span></span>
            <span class="stat-label tech-label">本月检索</span>
            <span class="stat-click-hint">点击查看统计</span>
          </div>
        </div>
      </div>

      <!-- 收藏筛选提示条 -->
      <div v-if="showFavoritesOnly && !canManage" class="filter-hint-bar tech-frame">
        <span class="fh-left">
          <span class="status-light is-on"></span>
          当前筛选：仅展示已收藏法规（共 {{ filteredDocuments.length }} 条）
        </span>
        <el-button type="info" size="small" link @click="showFavoritesOnly = false">清除筛选</el-button>
      </div>

      <!-- ============ 检索结果卡组 ============ -->
      <div class="result-deck">
        <!-- 卡组区块头 -->
        <div class="tech-section-header list-head">
          <span class="tsh-bar"></span>
          <span class="tsh-title">检索结果</span>
          <span class="tsh-sub">RESULT·FEED</span>
          <span class="tsh-line"></span>
          <span class="tsh-extra">
            <span class="tech-label">MATCH</span>
            <span class="readout-box"><span class="data-readout list-count">{{ filteredDocuments.length }}</span></span>
          </span>
        </div>

        <!-- 结果卡：角括号形态 + hover 扫描线 -->
        <article
          v-for="(row, idx) in filteredDocuments"
          :key="row.id"
          class="result-card corner-brackets"
          :class="{ 'is-favorited': isFavorited(row.id) }"
          :style="{ animationDelay: `${Math.min(idx * 0.06, 0.48)}s` }"
        >
          <div class="rc-scan tech-scan">
            <div class="rc-main">
              <!-- 左：hex 类型徽章 + 有效性指示灯 -->
              <div class="rc-type-col">
                <span class="rc-hex hex-badge" :style="docTypeTagStyle(row.doc_type)">{{ row.doc_type || '未分类' }}</span>
                <span class="rc-effective">
                  <span class="status-light" :class="row.is_effective ? 'is-on' : 'is-off'"></span>
                  <span class="tech-label">{{ row.is_effective ? '有效' : '失效' }}</span>
                </span>
              </div>

              <!-- 中：标题 + 摘要 + 元信息行（等宽字） -->
              <div class="rc-body">
                <div class="rc-title-row">
                  <span class="rc-title" @click="handleViewDetail(row.id)">{{ row.title }}</span>
                  <el-tag :type="getDocStatusType(row.status)" size="small" class="rc-status-tag">
                    {{ getDocStatusLabel(row.status) }}
                  </el-tag>
                </div>
                <p v-if="row.summary" class="rc-summary">{{ row.summary }}</p>
                <div class="rc-meta">
                  <span class="meta-item">
                    <el-icon :size="12"><Clock /></el-icon>
                    {{ formatDate(row.created_at) }}
                  </span>
                  <span v-if="canManage" class="meta-item">
                    CHUNKS <span class="data-readout rc-chunk-num">{{ row.chunk_count }}</span>
                  </span>
                  <span v-if="canManage" class="rc-progress">
                    <span class="tech-label">索引 {{ row.indexing_progress }}%</span>
                    <el-progress
                      :percentage="row.indexing_progress"
                      :stroke-width="4"
                      :show-text="false"
                      :color="row.indexing_progress >= 100 ? '#7ca586' : '#b7791f'"
                      class="progress-glow"
                    />
                  </span>
                </div>
              </div>

              <!-- 右：操作轨 -->
              <div class="rc-actions">
                <el-button type="primary" size="small" @click="handleViewDetail(row.id)">查看原文</el-button>
                <el-button
                  v-if="!canManage"
                  :type="isFavorited(row.id) ? 'warning' : 'info'"
                  size="small"
                  plain
                  @click="toggleFavorite(row)"
                >
                  {{ isFavorited(row.id) ? '已收藏' : '收藏' }}
                </el-button>
                <el-button v-if="canManage" type="danger" size="small" @click="handleDelete(row.id, row.title)">删除</el-button>
              </div>
            </div>
          </div>
        </article>

        <!-- 空状态：hex 大图标 + 渐变文案 -->
        <div v-if="filteredDocuments.length === 0" class="result-empty tech-frame">
          <div class="empty-hex hex-badge hex-ghost"><el-icon :size="32"><Document /></el-icon></div>
          <p class="empty-title">未检索到匹配文档</p>
          <p class="empty-sub tech-label">调整关键词或筛选条件后重新检索 · DATA·EMPTY</p>
        </div>

        <!-- 分页 -->
        <div class="pagination-wrapper">
          <span class="tech-label page-nav-label">PAGE·NAV // {{ total }} RECORDS</span>
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :total="total"
            layout="total, prev, pager, next"
            background
            @current-change="loadDocuments"
          />
        </div>
      </div>

      <!-- AI免责声明（合规提示） -->
      <div class="ai-disclaimer corner-brackets">
        <span class="disc-hex hex-badge hex-gold"><el-icon :size="12"><WarningFilled /></el-icon></span>
        <span class="disc-text">本平台法规案例文档仅供参考，AI基于文档生成的回答仅供普法参考，不构成律师正式法律意见，重大法律事项建议咨询执业律师。</span>
      </div>

      <!-- ============ 上传对话框 ============ -->
      <el-dialog v-model="showUploadDialog" title="上传法律文档" width="520px" :close-on-click-modal="false" class="upload-dialog">
        <el-form :model="uploadForm" label-width="80px">
          <el-form-item label="选择文件">
            <div
              class="upload-area corner-brackets"
              :class="{ dragging: isDragging, 'file-selected': selectedFile }"
              @dragover.prevent="isDragging = true"
              @dragleave="isDragging = false"
              @drop.prevent="handleDrop"
              @click="triggerFileInput"
            >
              <!-- 网格动画背景 -->
              <div class="upload-grid-bg"></div>
              <div class="upload-hex hex-badge hex-ghost">
                <el-icon :size="26" class="upload-icon-float"><Upload /></el-icon>
              </div>
              <p>拖拽文件到此处，或点击上传</p>
              <p class="upload-hint tech-label">支持 PDF、WORD、TXT 格式</p>
            </div>
            <!-- 隐藏的文件选择input（点击上传区域时触发） -->
            <input
              ref="fileInputRef"
              type="file"
              accept=".pdf,.doc,.docx,.txt"
              style="display: none"
              @change="handleFileSelect"
            />
            <!-- 文件选择成功提示 -->
            <div v-if="selectedFile" class="selected-file file-selected-anim">
              <el-icon :size="16" class="file-check-icon"><CircleCheck /></el-icon>
              <span>{{ selectedFile.name }}</span>
              <el-icon class="remove-icon" @click="selectedFile = null"><Close /></el-icon>
            </div>
          </el-form-item>
          <el-form-item label="文档类型">
            <el-select v-model="uploadForm.docType" placeholder="选择文档类型">
              <el-option label="法律" value="法律" />
              <el-option label="法规" value="法规" />
              <el-option label="案例" value="案例" />
              <el-option label="合同模板" value="合同模板" />
            </el-select>
          </el-form-item>
          <el-form-item label="标签">
            <el-input v-model="uploadForm.tags" placeholder="标签（逗号分隔）" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="showUploadDialog = false">取消</el-button>
          <el-button type="primary" :loading="uploading" :disabled="!selectedFile" @click="handleUpload">上传</el-button>
        </template>
      </el-dialog>

      <!-- ============ 文档详情对话框 ============ -->
      <el-dialog v-model="showDetailDialog" title="文档详情" width="680px" destroy-on-close>
        <div v-if="documentDetail" class="doc-detail">
          <!-- 详情项：角括号读出单元阵列 -->
          <div class="detail-grid">
            <div
              v-for="(item, idx) in detailItems"
              :key="idx"
              class="detail-item corner-brackets"
              :style="{ animationDelay: `${idx * 0.08}s` }"
            >
              <span class="label tech-label">{{ item.label }}</span>
              <span v-if="item.isTag" class="value">
                <el-tag :type="item.tagType" size="small" class="gradient-tag">{{ item.value }}</el-tag>
              </span>
              <!-- 文件名：可点击超链接，点击后加载并展示文档完整内容 -->
              <span v-else-if="item.isLink" class="value">
                <a class="file-name-link" @click="handleViewContent(item.docId!)">
                  <el-icon :size="14" class="link-icon"><Link /></el-icon>
                  {{ item.value }}
                </a>
              </span>
              <span v-else class="value">{{ item.value }}</span>
            </div>
          </div>
          <!-- 摘要 -->
          <div v-if="documentDetail.summary" class="doc-summary">
            <div class="tech-section-header">
              <span class="tsh-bar"></span>
              <span class="tsh-title">文档摘要</span>
              <span class="tsh-line"></span>
              <span class="tsh-extra tech-label">SUMMARY</span>
            </div>
            <p>{{ documentDetail.summary }}</p>
          </div>
          <!-- 标签 -->
          <div v-if="documentDetail.tags" class="doc-tags">
            <div class="tech-section-header">
              <span class="tsh-bar"></span>
              <span class="tsh-title">标签</span>
              <span class="tsh-line"></span>
              <span class="tsh-extra tech-label">TAGS</span>
            </div>
            <div class="tag-list">
              <el-tag v-for="tag in documentDetail.tags.split(',')" :key="tag" size="small" effect="plain" class="gradient-tag">
                {{ tag.trim() }}
              </el-tag>
            </div>
          </div>
          <!-- 提示信息：点击文件名查看完整内容 -->
          <div class="content-hint">
            <el-icon :size="14"><InfoFilled /></el-icon>
            <span>点击上方文件名超链接可查看文档完整内容</span>
          </div>
        </div>
      </el-dialog>

      <!-- ==================== 文档内容阅读器对话框 ==================== -->
      <el-dialog
        v-model="showContentDialog"
        title="文档内容阅读器"
        width="80%"
        top="5vh"
        destroy-on-close
        class="content-reader-dialog"
      >
        <!-- 加载中状态 -->
        <div v-if="contentLoading" class="content-loading">
          <div class="loading-spinner"></div>
          <p class="tech-label">正在加载文档内容...</p>
        </div>

        <!-- 文档内容展示 -->
        <div v-else-if="documentContent" class="content-reader">
          <!-- 文档头部：区块头 + 菱形分隔元信息 -->
          <div class="reader-header corner-brackets">
            <div class="tech-section-header">
              <span class="tsh-bar"></span>
              <h3 class="tsh-title reader-title">{{ documentContent.title }}</h3>
              <span class="tsh-line"></span>
              <span class="tsh-extra tech-label">DOC·READER</span>
            </div>
            <div class="reader-meta">
              <span class="meta-item">
                <el-icon :size="12"><Files /></el-icon>
                {{ documentContent.file_name || '未知文件' }}
              </span>
              <span class="diamond-node node-hollow meta-sep"></span>
              <span class="meta-item">
                <el-icon :size="12"><Collection /></el-icon>
                {{ documentContent.doc_type || '未分类' }}
              </span>
              <span class="diamond-node node-hollow meta-sep"></span>
              <span class="meta-item">
                <el-icon :size="12"><Coin /></el-icon>
                {{ formatFileSize(documentContent.file_size) }}
              </span>
              <span class="diamond-node node-hollow meta-sep"></span>
              <span class="meta-item">
                <el-icon :size="12"><DocumentCopy /></el-icon>
                {{ documentContent.chunk_count }} 个分块
              </span>
            </div>
          </div>

          <!-- 文档正文区域：段落渲染容器结构保留 -->
          <div class="reader-body">
            <template v-if="contentParagraphs.length > 0">
              <p
                v-for="(para, idx) in contentParagraphs"
                :key="idx"
                class="reader-paragraph"
                :style="{ animationDelay: `${Math.min(idx * 0.02, 0.4)}s` }"
              >
                {{ para }}
              </p>
            </template>
            <!-- 无内容时的空状态 -->
            <div v-else class="reader-empty">
              <div class="empty-hex hex-badge hex-ghost"><el-icon :size="28"><DocumentRemove /></el-icon></div>
              <p class="empty-title">该文档暂无可显示的文本内容</p>
              <span class="tech-label">可能是图片型PDF或尚未完成解析 · EMPTY</span>
            </div>
          </div>

          <!-- 文档统计信息条：数字读出 -->
          <div v-if="contentParagraphs.length > 0" class="reader-footer">
            <div class="reader-stat">
              <span class="readout-box"><span class="data-readout stat-num">{{ contentParagraphs.length }}</span></span>
              <span class="stat-text tech-label">段落</span>
            </div>
            <div class="reader-stat">
              <span class="readout-box"><span class="data-readout stat-num">{{ documentContent.content?.length || 0 }}</span></span>
              <span class="stat-text tech-label">字符</span>
            </div>
            <div class="reader-stat">
              <span class="readout-box"><span class="data-readout stat-num">{{ documentContent.chunk_count }}</span></span>
              <span class="stat-text tech-label">分块</span>
            </div>
          </div>
        </div>

        <!-- 加载失败状态 -->
        <div v-else class="content-loading">
          <div class="empty-hex hex-badge hex-pink"><el-icon :size="28"><WarningFilled /></el-icon></div>
          <p class="empty-title">文档内容加载失败</p>
        </div>
      </el-dialog>

      <!-- ==================== 检索统计弹窗（个人维度） ==================== -->
      <el-dialog v-model="showSearchStatsDialog" title="我的检索统计" width="600px" destroy-on-close>
        <div class="search-stats-panel">
          <!-- 统计概览：数字读出阵列 -->
          <div class="stats-overview tech-frame">
            <div class="ov-item">
              <span class="readout-box"><span class="data-readout ov-value">{{ monthSearchCount }}</span></span>
              <span class="tech-label">本月检索次数</span>
            </div>
            <span class="ov-divider"></span>
            <div class="ov-item">
              <span class="readout-box"><span class="data-readout ov-value">{{ searchHistory.length }}</span></span>
              <span class="tech-label">历史检索记录</span>
            </div>
            <span class="ov-divider"></span>
            <div class="ov-item">
              <span class="readout-box"><span class="data-readout ov-value">{{ searchKeywordStats.length }}</span></span>
              <span class="tech-label">不同关键词数</span>
            </div>
          </div>

          <!-- 关键词TOP排行：hex 序号 -->
          <div v-if="searchKeywordStats.length > 0" class="search-keyword-ranking">
            <div class="tech-section-header">
              <span class="tsh-bar"></span>
              <span class="tsh-title">检索关键词 TOP</span>
              <span class="tsh-line"></span>
              <span class="tsh-extra tech-label">RANKING</span>
            </div>
            <div v-for="(item, idx) in searchKeywordStats" :key="idx" class="keyword-rank-item">
              <span class="rank-hex hex-badge" :class="idx === 0 ? 'hex-gold' : idx === 1 ? '' : idx === 2 ? 'hex-cyan' : 'hex-ghost'">{{ idx + 1 }}</span>
              <span class="rank-keyword">{{ item.keyword }}</span>
              <span class="readout-box"><span class="data-readout rank-count">{{ item.count }}</span><span class="tech-label rank-unit">次</span></span>
            </div>
          </div>

          <!-- 最近检索记录 -->
          <div v-if="searchHistory.length > 0" class="search-history-list">
            <div class="tech-section-header">
              <span class="tsh-bar"></span>
              <span class="tsh-title">最近检索记录</span>
              <span class="tsh-line"></span>
              <span class="tsh-extra tech-label">HISTORY</span>
            </div>
            <div v-for="(item, idx) in searchHistory.slice(0, 10)" :key="idx" class="history-item">
              <span class="diamond-node node-hollow"></span>
              <span class="history-keyword">{{ item.keyword }}</span>
              <span class="history-time tech-label">{{ item.time }}</span>
            </div>
          </div>

          <!-- 空状态 -->
          <div v-if="searchHistory.length === 0" class="stats-empty">
            <div class="empty-hex hex-badge hex-ghost"><el-icon :size="24"><Search /></el-icon></div>
            <p class="empty-title">暂无检索记录</p>
            <p class="tech-label">去搜索法规试试吧 · NO·DATA</p>
          </div>
        </div>
      </el-dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, nextTick, watch } from 'vue'
import { knowledgeApi } from '@/api/knowledge'
import { ElMessage, ElMessageBox, type TagProps } from 'element-plus'
import { Search, Star } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
// 普通用户仅可检索、查看，禁用上传/删除/批量导入等管理操作
const canManage = computed(() => !userStore.isUserRole)
// 页面标题：普通用户显示「法规案例检索库」弱化管理属性
const pageTitleText = computed(() => userStore.isUserRole ? '法规案例检索库' : '知识库')

// ==================== 文档列表 ====================
const documents = ref<any[]>([])
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const searchKeyword = ref('')
const filterDocType = ref('')
// 筛选条件：发布年份、是否现行有效（提升检索效率）
const filterYear = ref('')
const filterEffective = ref('')

// ==================== 个人收藏（普通用户功能） ====================
// 收藏列表存储于localStorage，模拟个人收藏归档能力
const FAVORITE_KEY = 'zhifatong_favorites'
const favoriteIds = ref<number[]>([])
// 本月检索次数（个人维度统计）
const monthSearchCount = ref(0)
// 是否仅展示收藏法规（点击「我的收藏」卡片切换）
const showFavoritesOnly = ref(false)
// 检索统计弹窗
const showSearchStatsDialog = ref(false)
// 检索历史关键词列表（个人维度，localStorage存储）
const searchHistory = ref<{ keyword: string; time: string }[]>([])

/** 加载本地收藏 */
const loadFavorites = () => {
  try {
    const raw = localStorage.getItem(FAVORITE_KEY)
    favoriteIds.value = raw ? JSON.parse(raw) : []
  } catch {
    favoriteIds.value = []
  }
}

/** 保存收藏到本地 */
const saveFavorites = () => {
  localStorage.setItem(FAVORITE_KEY, JSON.stringify(favoriteIds.value))
}

/** 判断文档是否已收藏 */
const isFavorited = (docId: number) => favoriteIds.value.includes(docId)

/** 切换收藏状态 */
const toggleFavorite = (row: any) => {
  const idx = favoriteIds.value.indexOf(row.id)
  if (idx >= 0) {
    favoriteIds.value.splice(idx, 1)
    ElMessage.success(`已取消收藏"${row.title}"`)
  } else {
    favoriteIds.value.push(row.id)
    ElMessage.success(`已收藏"${row.title}"`)
  }
  saveFavorites()
}

/** 收藏数量（个人统计展示） */
const favoriteCount = computed(() => favoriteIds.value.length)

/** 点击「我的收藏」卡片：切换仅展示收藏法规 */
const handleFavoritesCardClick = () => {
  showFavoritesOnly.value = !showFavoritesOnly.value
  if (showFavoritesOnly.value) {
    ElMessage.info(`已筛选出 ${favoriteCount.value} 条收藏法规`)
  }
}

/** 点击「本月检索」卡片：弹出检索统计面板 */
const handleSearchStatsCardClick = () => {
  loadSearchHistory()
  showSearchStatsDialog.value = true
}

/** 加载个人检索历史（localStorage） */
const loadSearchHistory = () => {
  try {
    const raw = localStorage.getItem('zhifatong_search_history')
    searchHistory.value = raw ? JSON.parse(raw) : []
  } catch {
    searchHistory.value = []
  }
}

/** 记录检索关键词到历史 */
const recordSearchHistory = (keyword: string) => {
  if (!keyword || !keyword.trim()) return
  try {
    const raw = localStorage.getItem('zhifatong_search_history')
    const list: { keyword: string; time: string }[] = raw ? JSON.parse(raw) : []
    list.unshift({ keyword: keyword.trim(), time: new Date().toLocaleString('zh-CN') })
    // 仅保留最近20条
    searchHistory.value = list.slice(0, 20)
    localStorage.setItem('zhifatong_search_history', JSON.stringify(searchHistory.value))
  } catch {
    // 忽略存储异常
  }
}

/** 检索关键词TOP排行（按出现次数降序） */
const searchKeywordStats = computed(() => {
  const map: Record<string, number> = {}
  searchHistory.value.forEach(item => {
    map[item.keyword] = (map[item.keyword] || 0) + 1
  })
  return Object.entries(map)
    .map(([keyword, count]) => ({ keyword, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 10)
})

/** 筛选后的文档列表（根据收藏筛选条件过滤） */
const filteredDocuments = computed(() => {
  if (!showFavoritesOnly.value) return documents.value
  return documents.value.filter((d: any) => favoriteIds.value.includes(d.id))
})

// ==================== 统计 ====================
const stats = reactive({
  total_documents: 0,
  total_chunks: 0,
  recent_uploads: 0,
  processing_count: 0,
})

// 计数动画相关状态
const animatedStats = reactive({
  total_documents: 0,
  total_chunks: 0,
  recent_uploads: 0,
  processing_count: 0,
})

// 计数滚动动画：从0滚动到目标值
const animateCount = (key: keyof typeof animatedStats, target: number, duration = 1200) => {
  const start = animatedStats[key]
  const diff = target - start
  if (diff === 0) return
  const startTime = performance.now()
  const step = (currentTime: number) => {
    const elapsed = currentTime - startTime
    const progress = Math.min(elapsed / duration, 1)
    // 缓出效果
    const eased = 1 - Math.pow(1 - progress, 3)
    animatedStats[key] = Math.round(start + diff * eased)
    if (progress < 1) {
      requestAnimationFrame(step)
    }
  }
  requestAnimationFrame(step)
}

// 统计卡片配置
const statItems = computed(() => [
  {
    key: 'total_documents' as const,
    label: '文档总数',
    displayValue: animatedStats.total_documents,
    icon: 'Collection',
    iconBg: 'rgba(201, 169, 98, 0.15)',
    iconColor: '#b7791f',
  },
  {
    key: 'total_chunks' as const,
    label: '文档分块数',
    displayValue: animatedStats.total_chunks,
    icon: 'Document',
    iconBg: 'rgba(90, 118, 165, 0.15)',
    iconColor: '#4f7fc9',
  },
  {
    key: 'recent_uploads' as const,
    label: '近期上传',
    displayValue: animatedStats.recent_uploads,
    icon: 'CircleCheck',
    iconBg: 'rgba(201, 169, 98, 0.15)',
    iconColor: '#b7791f',
  },
  {
    key: 'processing_count' as const,
    label: '处理中',
    displayValue: animatedStats.processing_count,
    icon: 'Loading',
    iconBg: 'rgba(192, 91, 82, 0.15)',
    iconColor: '#c05b52',
  },
])

// 监听stats变化，触发计数动画
watch(() => stats.total_documents, (val) => animateCount('total_documents', val))
watch(() => stats.total_chunks, (val) => animateCount('total_chunks', val))
watch(() => stats.recent_uploads, (val) => animateCount('recent_uploads', val))
watch(() => stats.processing_count, (val) => animateCount('processing_count', val))

// ==================== 上传 ====================
const showUploadDialog = ref(false)
const isDragging = ref(false)
const selectedFile = ref<File | null>(null)
const uploading = ref(false)
const fileInputRef = ref<HTMLInputElement>()
const uploadForm = reactive({
  docType: '法律',
  tags: '',
})

// ==================== 文档详情 ====================
const showDetailDialog = ref(false)
const documentDetail = ref<any>(null)

// ==================== 文档内容阅读器 ====================
const showContentDialog = ref(false)   // 内容阅读器对话框可见性
const contentLoading = ref(false)       // 内容加载状态
const documentContent = ref<any>(null)  // 文档完整内容数据

// 详情项计算属性
const detailItems = computed<Array<{
  label: string
  value: unknown
  isTag: boolean
  isLink?: boolean
  docId?: number
  tagType?: TagProps['type']
}>>(() => {
  if (!documentDetail.value) return []
  // 文件名显示文本：优先使用file_name，为空时使用title作为可点击链接文本
  const fileNameDisplay = documentDetail.value.file_name || documentDetail.value.title || '查看完整内容'
  return [
    { label: '文档标题', value: documentDetail.value.title, isTag: false },
    { label: '文档类型', value: documentDetail.value.doc_type || '未分类', isTag: false },
    { label: '文件名', value: fileNameDisplay, isTag: false, isLink: true, docId: documentDetail.value.id },
    { label: '状态', value: getDocStatusLabel(documentDetail.value.status), isTag: true, tagType: getDocStatusType(documentDetail.value.status) },
    { label: '分块数', value: documentDetail.value.chunk_count, isTag: false },
    { label: '是否有效', value: documentDetail.value.is_effective ? '有效' : '失效', isTag: true, tagType: documentDetail.value.is_effective ? 'success' : 'info' },
  ]
})

// 文件名点击：加载并展示文档完整内容（含文本、图片描述、表格等所有元素）
const handleViewContent = async (docId: number) => {
  showContentDialog.value = true
  contentLoading.value = true
  documentContent.value = null
  try {
    const data = await knowledgeApi.getDocumentContent(docId)
    documentContent.value = data
  } catch {
    ElMessage.error('加载文档内容失败，请稍后重试')
  } finally {
    contentLoading.value = false
  }
}

// 格式化文件大小
const formatFileSize = (bytes: number) => {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

// 将文档全文按段落分割，用于阅读器排版展示
const contentParagraphs = computed(() => {
  if (!documentContent.value?.content) return []
  return documentContent.value.content
    .split(/\n+/)
    .map((p: string) => p.trim())
    .filter((p: string) => p.length > 0)
})

// 3D倾斜效果处理
const handleCardHover = (e: MouseEvent, entering: boolean) => {
  const card = e.currentTarget as HTMLElement
  if (entering) {
    const rect = card.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    const centerX = rect.width / 2
    const centerY = rect.height / 2
    const rotateX = ((y - centerY) / centerY) * -8
    const rotateY = ((x - centerX) / centerX) * 8
    card.style.transform = `perspective(600px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(1.02)`
  } else {
    card.style.transform = 'perspective(600px) rotateX(0) rotateY(0) scale(1)'
  }
}

// 表格行交错入场动画类名
const tableRowClassName = ({ rowIndex }: { rowIndex: number }) => {
  return `row-stagger row-stagger-${rowIndex % 10}`
}

// 加载文档列表
const loadDocuments = async () => {
  // 记录本月检索次数（普通用户个人统计）
  if (!canManage.value) {
    const searchKey = 'zhifatong_month_search'
    const now = new Date()
    const monthKey = `${now.getFullYear()}-${now.getMonth() + 1}`
    try {
      const raw = localStorage.getItem(searchKey)
      const data = raw ? JSON.parse(raw) : { month: '', count: 0 }
      if (data.month !== monthKey) {
        data.month = monthKey
        data.count = 0
      }
      data.count += 1
      localStorage.setItem(searchKey, JSON.stringify(data))
      monthSearchCount.value = data.count
    } catch {
      monthSearchCount.value = 1
    }
    // 记录检索关键词到个人历史
    if (searchKeyword.value && searchKeyword.value.trim()) {
      recordSearchHistory(searchKeyword.value)
    }
  }

  try {
    const data = await knowledgeApi.getDocuments({
      page: currentPage.value,
      page_size: pageSize.value,
      doc_type: filterDocType.value || undefined,
      keyword: searchKeyword.value || undefined,
    })
    let items = data.items || []
    // 前端二次筛选：是否现行有效（后端未支持时前端兜底）
    if (filterEffective.value === 'effective') {
      items = items.filter((d: any) => d.is_effective)
    } else if (filterEffective.value === 'invalid') {
      items = items.filter((d: any) => !d.is_effective)
    }
    documents.value = items
    total.value = data.total || 0
  } catch {
    documents.value = [
      { id: 1, title: '中华人民共和国民法典', doc_type: '法律', status: 'indexed', chunk_count: 256, indexing_progress: 100, is_effective: true, created_at: '2024-03-10T08:00:00' },
      { id: 2, title: '劳动合同法', doc_type: '法律', status: 'indexed', chunk_count: 128, indexing_progress: 100, is_effective: true, created_at: '2024-03-09T10:30:00' },
      { id: 3, title: '知识产权案例分析集', doc_type: '案例', status: 'processing', chunk_count: 0, indexing_progress: 45, is_effective: true, created_at: '2024-03-15T14:20:00' },
    ]
    total.value = 3
  }
}

// 加载统计
const loadStats = async () => {
  try {
    const data = await knowledgeApi.getStats()
    Object.assign(stats, data)
  } catch {
    stats.total_documents = 156
    stats.total_chunks = 3842
    stats.recent_uploads = 12
    stats.processing_count = 2
  }
}

// 触发文件选择
const triggerFileInput = () => {
  fileInputRef.value?.click()
}

// 处理文件选择
const handleFileSelect = (e: Event) => {
  const input = e.target as HTMLInputElement
  if (input.files && input.files[0]) {
    selectedFile.value = input.files[0]
  }
}

// 处理拖拽
const handleDrop = (e: DragEvent) => {
  isDragging.value = false
  if (e.dataTransfer?.files && e.dataTransfer.files[0]) {
    selectedFile.value = e.dataTransfer.files[0]
  }
}

// 上传文档
const handleUpload = async () => {
  if (!selectedFile.value) return
  uploading.value = true
  try {
    await knowledgeApi.uploadDocument(selectedFile.value, uploadForm.docType, uploadForm.tags || undefined)
    ElMessage.success('文档上传成功，正在处理中...')
    showUploadDialog.value = false
    selectedFile.value = null
    uploadForm.tags = ''
    loadDocuments()
    loadStats()
  } catch {
    ElMessage.error('上传失败，请重试')
  } finally {
    uploading.value = false
  }
}

// 查看文档详情
const handleViewDetail = async (docId: number) => {
  try {
    const data = await knowledgeApi.getDocumentDetail(docId)
    documentDetail.value = data
  } catch {
    const doc = documents.value.find((d) => d.id === docId)
    documentDetail.value = doc || { title: '未知文档', summary: '暂无摘要信息' }
  }
  showDetailDialog.value = true
}

// 删除文档
const handleDelete = async (docId: number, title: string) => {
  try {
    await ElMessageBox.confirm(`确定删除文档"${title}"？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await knowledgeApi.deleteDocument(docId)
    ElMessage.success('删除成功')
    loadDocuments()
    loadStats()
  } catch {
    // 用户取消
  }
}

// 辅助方法
const getDocStatusType = (status: string): TagProps['type'] => {
  const map: Record<string, TagProps['type']> = { pending: 'info', processing: 'warning', indexed: 'success', completed: 'success', failed: 'danger' }
  return map[status] || 'info'
}

const getDocStatusLabel = (status: string) => {
  const map: Record<string, string> = { pending: '待处理', processing: '处理中', indexed: '已索引', completed: '已入库完成', failed: '处理失败' }
  return map[status] || status
}

/** 文档类型标签配色（案卷墨蓝：法律藏青 / 法规蓝灰 / 案例砖红 / 合同鎏金，半透明底） */
const docTypeTagStyle = (docType?: string) => {
  const map: Record<string, { background: string; color: string; borderColor: string; boxShadow: string }> = {
    法律: { background: 'rgba(90, 118, 165, 0.14)', color: '#4f7fc9', borderColor: 'rgba(90, 118, 165, 0.4)', boxShadow: '0 0 8px rgba(90, 118, 165, 0.18)' },
    法规: { background: 'rgba(124, 147, 181, 0.14)', color: '#7897bf', borderColor: 'rgba(124, 147, 181, 0.4)', boxShadow: '0 0 8px rgba(124, 147, 181, 0.18)' },
    案例: { background: 'rgba(192, 91, 82, 0.12)', color: '#c05b52', borderColor: 'rgba(192, 91, 82, 0.4)', boxShadow: '0 0 8px rgba(192, 91, 82, 0.18)' },
    合同模板: { background: 'rgba(201, 169, 98, 0.12)', color: '#b7791f', borderColor: 'rgba(201, 169, 98, 0.4)', boxShadow: '0 0 8px rgba(201, 169, 98, 0.18)' },
  }
  return docType ? map[docType] : undefined
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(() => {
  loadFavorites()
  // 加载本月检索次数（普通用户个人统计）
  if (!canManage.value) {
    try {
      const raw = localStorage.getItem('zhifatong_month_search')
      const data = raw ? JSON.parse(raw) : { month: '', count: 0 }
      const now = new Date()
      const monthKey = `${now.getFullYear()}-${now.getMonth() + 1}`
      monthSearchCount.value = data.month === monthKey ? data.count : 0
    } catch {
      monthSearchCount.value = 0
    }
  }
  loadDocuments()
  loadStats()
})
</script>

<style scoped lang="scss">
/* ==================== 知识库 · 结构化科技组件体系 v2 ==================== */

/* ---- 根容器：网格纹理底 + 内容层 ---- */
.knowledge-page {
  position: relative;
  min-height: 100%;
  color: var(--text-primary);
}

.kp-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

/* ---- 页头区块 ---- */
.page-topbar {
  .tech-section-header .tsh-title {
    margin: 0;
    font-size: 20px;
    letter-spacing: 2px;
    background: var(--gradient-text);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
}

/* ==================== 指挥中心命令栏 ==================== */
.command-shell {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px 20px 12px;
  background:
    linear-gradient(rgba(90, 118, 165, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(90, 118, 165, 0.04) 1px, transparent 1px),
    linear-gradient(160deg, rgba(255, 255, 255, 0.92) 0%, rgba(244, 247, 251, 0.96) 100%);
  background-size: 24px 24px, 24px 24px, cover;
  border: 1px solid var(--border-color);
  transition: border-color var(--duration-normal) var(--ease-smooth),
    box-shadow var(--duration-normal) var(--ease-smooth);

  /* 聚焦任一控件：整条命令栏亮起 */
  &:focus-within {
    border-color: var(--border-strong);
    box-shadow: var(--shadow-glow-accent);
  }
}

.cmd-row {
  display: flex;
  align-items: stretch;
  gap: 12px;
}

/* 命令栏六边形图标块 */
.cmd-hex {
  width: 44px;
  height: 48px;
}

/* 大号检索输入框 */
.cmd-input {
  flex: 1;

  :deep(.el-input__wrapper) {
    padding: 4px 16px;
    background: rgba(8, 10, 16, 0.55);
    border-radius: 0;

    .el-input__inner {
      height: 40px;
      font-size: 15px;
      letter-spacing: 1px;
    }
  }

  &:focus-within :deep(.el-input__wrapper) {
    box-shadow: 0 0 0 1px rgba(90, 118, 165, 0.65) inset,
      0 0 18px rgba(90, 118, 165, 0.28) !important;
  }
}

/* 渐变发光检索按钮 */
.cmd-launch {
  background: linear-gradient(135deg, #2f6fed 0%, #5b91f2 45%, #b7791f 100%) !important;
  border: 1px solid rgba(124, 147, 181, 0.5) !important;
  box-shadow: 0 0 18px rgba(70, 96, 140, 0.45), 0 0 34px rgba(201, 169, 98, 0.16);
  letter-spacing: 6px;

  .launch-text {
    padding-left: 4px;
    font-weight: 700;
  }

  &:hover,
  &:focus {
    background: linear-gradient(135deg, #5b91f2 0%, #4f7fc9 45%, #d99b3d 100%) !important;
    box-shadow: 0 0 26px rgba(90, 118, 165, 0.6), 0 0 48px rgba(201, 169, 98, 0.25) !important;
  }
}

/* 上传按钮：藏青渐变 + 扫光 */
.cmd-upload {
  position: relative;
  overflow: hidden;
}

.shimmer-btn {
  &::after {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: linear-gradient(45deg, transparent 30%, rgba(148, 158, 178, 0.22) 50%, transparent 70%);
    animation: shimmer 3s ease-in-out infinite;
    pointer-events: none;
  }
}

@keyframes shimmer {
  0% { transform: translateX(-100%) rotate(45deg); }
  100% { transform: translateX(100%) rotate(45deg); }
}

/* ---- 筛选 chips 行 ---- */
.cmd-chips {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding-top: 10px;
  border-top: 1px dashed rgba(90, 118, 165, 0.18);
}

.chip-group-label {
  margin-right: 2px;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  background: rgba(255, 255, 255, 0.65);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  font-size: 12px;
  letter-spacing: 1px;
  line-height: 1.4;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-smooth);

  &:hover {
    color: var(--text-primary);
    border-color: var(--border-strong);
  }

  /* 选中态（默认藏青） */
  &.is-active {
    background: rgba(70, 96, 140, 0.18);
    border-color: rgba(90, 118, 165, 0.65);
    color: var(--accent-light);
    box-shadow: 0 0 10px rgba(70, 96, 140, 0.3);
  }
}

/* hex 色点（六边形） */
.chip-dot {
  width: 10px;
  height: 11px;
  flex-shrink: 0;
  clip-path: polygon(50% 0, 100% 25%, 100% 75%, 50% 100%, 0 75%, 0 25%);

  &.dot-all { background: linear-gradient(135deg, #4f7fc9, #b7791f); }
  &.dot-purple { background: #4f7fc9; box-shadow: 0 0 6px rgba(90, 118, 165, 0.6); }
  &.dot-cyan { background: #b7791f; box-shadow: 0 0 6px rgba(201, 169, 98, 0.6); }
  &.dot-pink { background: #c05b52; box-shadow: 0 0 6px rgba(192, 91, 82, 0.6); }
  &.dot-gold { background: #b7791f; box-shadow: 0 0 6px rgba(201, 169, 98, 0.6); }
}

/* 分色选中态：与 docTypeTagStyle 色映射一致 */
.chip-purple.is-active {
  background: rgba(90, 118, 165, 0.16);
  border-color: rgba(90, 118, 165, 0.6);
  color: #7897bf;
  box-shadow: 0 0 10px rgba(90, 118, 165, 0.28);
}

.chip-cyan.is-active {
  background: rgba(201, 169, 98, 0.14);
  border-color: rgba(201, 169, 98, 0.6);
  color: #d99b3d;
  box-shadow: 0 0 10px rgba(201, 169, 98, 0.28);
}

.chip-pink.is-active {
  background: rgba(192, 91, 82, 0.14);
  border-color: rgba(192, 91, 82, 0.6);
  color: #e3a9a3;
  box-shadow: 0 0 10px rgba(192, 91, 82, 0.28);
}

.chip-gold.is-active {
  background: rgba(201, 169, 98, 0.14);
  border-color: rgba(201, 169, 98, 0.6);
  color: #d99b3d;
  box-shadow: 0 0 10px rgba(201, 169, 98, 0.28);
}

.chip-off.is-active {
  background: rgba(192, 91, 82, 0.12);
  border-color: rgba(192, 91, 82, 0.55);
  color: #e3a9a3;
  box-shadow: 0 0 10px rgba(192, 91, 82, 0.25);
}

.chip-divider {
  width: 1px;
  height: 16px;
  margin: 0 6px;
  background: linear-gradient(180deg, transparent, rgba(90, 118, 165, 0.45), transparent);
}

/* ==================== 统计读出阵列 ==================== */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}

.stats-row-user {
  grid-template-columns: repeat(2, 1fr);
  max-width: 760px;
}

.stat-frame {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 18px;

  > .status-light {
    margin-left: auto;
    align-self: flex-start;
  }
}

/* 3D倾斜 + 入场 */
.tilt-card {
  animation: statIn 0.5s var(--ease-spring) backwards;
  transition: transform var(--duration-normal) var(--ease-spring),
    box-shadow var(--duration-normal) var(--ease-spring);
  will-change: transform;

  &:hover {
    box-shadow: var(--shadow-glow-accent);
  }
}

@keyframes statIn {
  from {
    opacity: 0;
    transform: translateY(16px) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.stat-hex {
  width: 42px;
  height: 46px;
}

.stat-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.stat-value {
  font-size: 24px;
}

.stat-click-hint {
  font-size: 10px;
  letter-spacing: 1.5px;
  color: var(--text-muted);
  opacity: 0.8;
}

/* 可点击统计卡 */
.clickable-stat {
  cursor: pointer;
  transition: transform var(--duration-normal) var(--ease-spring),
    box-shadow var(--duration-normal) var(--ease-spring),
    border-color var(--duration-normal) var(--ease-smooth);
  animation: statIn 0.5s var(--ease-spring) backwards;

  &:hover {
    border-color: var(--border-strong) !important;
    box-shadow: var(--shadow-glow-accent) !important;
    transform: translateY(-4px);
  }

  /* 激活态：鎏金内环 */
  &.active {
    border-color: rgba(201, 169, 98, 0.5) !important;
    box-shadow: 0 0 0 1px rgba(201, 169, 98, 0.3) inset, var(--shadow-glow-cyan) !important;
  }
}

/* 收藏筛选提示条 */
.filter-hint-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  font-size: 13px;
  color: var(--neon-cyan-light);

  .fh-left {
    display: inline-flex;
    align-items: center;
    gap: 8px;
  }
}

/* ==================== 检索结果卡组 ==================== */
.result-deck {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.list-head {
  .list-count {
    font-size: 16px;
    color: var(--neon-cyan-light);
    text-shadow: 0 0 12px rgba(201, 169, 98, 0.4);
  }
}

/* 结果卡：角括号形态 */
.result-card {
  position: relative;
  border: 1px solid var(--border-color);
  background: linear-gradient(160deg, rgba(255, 255, 255, 0.88) 0%, rgba(244, 247, 251, 0.95) 100%);
  animation: cardSlideIn 0.45s var(--ease-smooth) both;
  transition: border-color var(--duration-normal) var(--ease-smooth),
    box-shadow var(--duration-normal) var(--ease-smooth),
    transform var(--duration-normal) var(--ease-smooth);

  &:hover {
    border-color: var(--border-strong);
    box-shadow: var(--shadow-glow);
    transform: translateY(-2px);
  }

  /* 已收藏：鎏金描边 */
  &.is-favorited {
    border-color: rgba(201, 169, 98, 0.45);

    &:hover {
      border-color: rgba(201, 169, 98, 0.7);
      box-shadow: var(--shadow-glow-gold);
    }
  }
}

@keyframes cardSlideIn {
  from {
    opacity: 0;
    transform: translateX(-18px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

/* 扫描层：内衬容器（hover 扫描线由全局 .tech-scan 提供） */
.rc-scan {
  padding: 16px 18px;
}

.rc-main {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

/* 左列：hex 类型徽章 + 有效性灯 */
.rc-type-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding-top: 2px;
  flex-shrink: 0;
}

.rc-hex {
  min-width: 64px;
  height: 30px;
  padding: 0 14px;
  font-size: 11px;
  letter-spacing: 2px;
}

.rc-effective {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

/* 中列：标题 / 摘要 / 元信息 */
.rc-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rc-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.rc-title {
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.5px;
  color: var(--text-primary);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-smooth);

  &:hover {
    color: var(--neon-cyan-light);
    text-shadow: 0 0 10px rgba(201, 169, 98, 0.45);
  }
}

.rc-status-tag {
  flex-shrink: 0;
}

.rc-summary {
  font-size: 12.5px;
  line-height: 1.7;
  color: var(--text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 元信息行：等宽字 */
.rc-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  font-family: 'JetBrains Mono', 'Cascadia Mono', Consolas, 'Courier New', monospace;
  font-size: 11px;
  color: var(--text-muted);

  .meta-item {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    letter-spacing: 0.5px;
  }

  .rc-chunk-num {
    font-size: 13px;
    color: var(--neon-cyan);
    text-shadow: 0 0 10px rgba(201, 169, 98, 0.35);
  }
}

.rc-progress {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  width: 170px;
  flex-shrink: 0;
}

.progress-glow {
  flex: 1;

  :deep(.el-progress-bar__inner) {
    box-shadow: 0 0 8px rgba(70, 96, 140, 0.45);
    background: linear-gradient(90deg, #2f6fed, #4f7fc9, #b7791f);
  }
}

/* 右列：操作轨 */
.rc-actions {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: stretch;
  gap: 2px;
  padding-left: 14px;
  border-left: 1px dashed rgba(90, 118, 165, 0.22);
  flex-shrink: 0;

  :deep(.el-button + .el-button) {
    margin-left: 0;
  }
}

/* 空状态 */
.result-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 44px 20px;
}

.empty-hex {
  width: 72px;
  height: 80px;
}

.empty-title {
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 2px;
  background: var(--gradient-text);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.empty-sub {
  color: var(--text-muted);
}

/* 分页 */
.pagination-wrapper {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  border: 1px solid rgba(90, 118, 165, 0.14);
  background: rgba(244, 247, 251, 0.55);
}

/* ==================== AI 免责声明 ==================== */
.ai-disclaimer {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: linear-gradient(135deg, rgba(201, 169, 98, 0.07), rgba(90, 118, 165, 0.05));
  border: 1px solid rgba(201, 169, 98, 0.22);
  font-size: 12px;
  color: var(--neon-gold);
  font-weight: 500;
  line-height: 1.6;

  .disc-hex {
    width: 24px;
    height: 26px;
    flex-shrink: 0;
  }

  .disc-text {
    color: rgba(220, 196, 137, 0.85);
  }
}

/* ==================== 上传区域 ==================== */
.upload-area {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 26px 20px;
  text-align: center;
  border: 2px dashed var(--border-color);
  cursor: pointer;
  overflow: hidden;
  transition: all var(--duration-normal) var(--ease-smooth);

  /* 藏青网格动画背景 */
  .upload-grid-bg {
    position: absolute;
    inset: 0;
    background-image:
      linear-gradient(rgba(90, 118, 165, 0.06) 1px, transparent 1px),
      linear-gradient(90deg, rgba(90, 118, 165, 0.06) 1px, transparent 1px);
    background-size: 20px 20px;
    animation: gridMove 8s linear infinite;
    pointer-events: none;
  }

  .upload-hex {
    width: 64px;
    height: 70px;
    position: relative;
  }

  p {
    position: relative;
    font-size: 13px;
    color: var(--text-secondary);
    margin: 4px 0 0;
  }

  &:hover,
  &.dragging {
    border-color: var(--accent-color);
    background: rgba(90, 118, 165, 0.06);
  }

  /* 拖拽时藏青脉冲边框 */
  &.dragging {
    animation: pulseBorder 1s ease infinite;
  }

  /* 文件选择后成功状态 */
  &.file-selected {
    border-color: var(--success-color);
    background: rgba(124, 165, 134, 0.06);
  }
}

@keyframes gridMove {
  0% { background-position: 0 0; }
  100% { background-position: 20px 20px; }
}

@keyframes pulseBorder {
  0%, 100% {
    border-color: var(--accent-color);
    box-shadow: 0 0 0 0 rgba(90, 118, 165, 0.4);
  }
  50% {
    border-color: rgba(124, 147, 181, 0.85);
    box-shadow: 0 0 14px 4px rgba(90, 118, 165, 0.22);
  }
}

.upload-icon-float {
  animation: uploadFloat 2s ease-in-out infinite;
}

@keyframes uploadFloat {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}

.file-selected-anim {
  animation: fileSelectPop 0.4s var(--ease-spring) both;
}

@keyframes fileSelectPop {
  from {
    opacity: 0;
    transform: scale(0.8) translateY(10px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.selected-file {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  padding: 8px 12px;
  background: rgba(124, 165, 134, 0.08);
  border: 1px solid rgba(124, 165, 134, 0.2);
  font-size: 13px;
  color: var(--text-primary);

  .file-check-icon {
    color: var(--success-color);
  }

  .remove-icon {
    margin-left: auto;
    cursor: pointer;

    &:hover {
      color: var(--danger-color);
    }
  }
}

/* ==================== 文档详情：角括号读出单元 ==================== */
.doc-detail {
  .detail-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-bottom: 18px;
  }

  .detail-item {
    position: relative;
    display: flex;
    flex-direction: column;
    gap: 5px;
    padding: 10px 12px;
    background: rgba(244, 247, 251, 0.55);
    border: 1px solid rgba(90, 118, 165, 0.14);
    animation: detailFadeIn 0.5s var(--ease-smooth) both;

    .label {
      color: var(--text-muted);
    }

    .value {
      font-size: 14px;
      color: var(--text-primary);
      word-break: break-all;
    }
  }

  /* 渐变标签：藏青半透明底 */
  .gradient-tag {
    background: linear-gradient(135deg, rgba(90, 118, 165, 0.16), rgba(201, 169, 98, 0.1));
    border-color: rgba(90, 118, 165, 0.35);
  }

  .doc-summary,
  .doc-tags {
    margin-bottom: 16px;

    p {
      margin-top: 10px;
      font-size: 13px;
      color: var(--text-secondary);
      line-height: 1.8;
    }
  }

  .tag-list {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 10px;
  }
}

@keyframes detailFadeIn {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 文件名超链接 */
.file-name-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--accent-color);
  cursor: pointer;
  font-size: 14px;
  text-decoration: none;
  border-bottom: 1px dashed transparent;
  transition: all var(--duration-normal) var(--ease-smooth);

  .link-icon {
    transition: transform var(--duration-normal) var(--ease-spring);
  }

  &:hover {
    color: var(--neon-cyan);
    border-bottom-color: rgba(201, 169, 98, 0.5);
    text-shadow: 0 0 8px rgba(201, 169, 98, 0.35);

    .link-icon {
      transform: translate(2px, -2px) rotate(8deg);
    }
  }
}

/* 提示信息条 */
.content-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 16px;
  padding: 10px 14px;
  background: rgba(70, 96, 140, 0.08);
  border: 1px solid rgba(90, 118, 165, 0.2);
  border-left: 3px solid var(--accent-color);
  font-size: 12px;
  color: var(--text-secondary);
  animation: hintFadeIn 0.6s ease 0.4s both;
}

@keyframes hintFadeIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ==================== 文档内容阅读器 ==================== */
.content-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 56px 20px;
  gap: 16px;

  p {
    font-size: 14px;
    color: var(--text-secondary);
  }
}

/* 藏青旋转加载 */
.loading-spinner {
  width: 42px;
  height: 42px;
  border: 3px solid rgba(90, 118, 165, 0.18);
  border-top-color: var(--accent-color);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  box-shadow: 0 0 14px rgba(90, 118, 165, 0.2);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.content-reader {
  display: flex;
  flex-direction: column;
  gap: 0;
}

/* 阅读器头部：角括号 + 区块头 + 菱形分隔元信息 */
.reader-header {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px 20px;
  margin-bottom: 16px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.85), rgba(244, 247, 251, 0.6));
  border: 1px solid var(--border-color);

  .reader-title {
    margin: 0;
    font-size: 17px;
    font-weight: 700;
    letter-spacing: 1px;
    background: var(--gradient-text);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .reader-meta {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
    font-size: 12px;
    color: var(--text-secondary);

    .meta-item {
      display: inline-flex;
      align-items: center;
      gap: 5px;
    }

    .meta-sep {
      width: 7px;
      height: 7px;
    }
  }
}

/* 正文容器：段落渲染结构保留 */
.reader-body {
  max-height: 55vh;
  overflow-y: auto;
  padding: 16px 20px;
  background: rgba(244, 247, 251, 0.6);
  border: 1px solid var(--border-color);

  &::-webkit-scrollbar {
    width: 6px;
  }
  &::-webkit-scrollbar-track {
    background: transparent;
  }
  &::-webkit-scrollbar-thumb {
    background: rgba(90, 118, 165, 0.3);
    border-radius: 3px;

    &:hover {
      background: rgba(90, 118, 165, 0.5);
    }
  }
}

.reader-paragraph {
  position: relative;
  font-size: 14px;
  line-height: 1.9;
  color: var(--text-primary);
  margin-bottom: 14px;
  padding-left: 14px;
  text-indent: 2em;
  text-align: justify;
  animation: paragraphFadeIn 0.5s var(--ease-smooth) both;

  /* 段首菱形节点 */
  &::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0.75em;
    width: 5px;
    height: 5px;
    transform: rotate(45deg);
    background: rgba(90, 118, 165, 0.55);
  }

  &:first-child {
    font-size: 15px;
  }
}

@keyframes paragraphFadeIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.reader-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 44px 20px;
  gap: 10px;

  .empty-title {
    font-size: 15px;
  }

  .tech-label {
    color: var(--text-muted);
  }
}

/* 底部统计条：数字读出 */
.reader-footer {
  display: flex;
  justify-content: center;
  gap: 40px;
  padding: 14px 20px;
  margin-top: 16px;
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid var(--border-color);

  .reader-stat {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 5px;

    .stat-num {
      font-size: 20px;
      color: var(--neon-cyan-light);
      text-shadow: 0 0 14px rgba(201, 169, 98, 0.4);
    }

    .stat-text {
      color: var(--text-muted);
    }
  }
}

/* ==================== 检索统计弹窗 ==================== */
.search-stats-panel {
  .stats-overview {
    display: flex;
    align-items: center;
    justify-content: space-around;
    flex-wrap: wrap;
    gap: 14px;
    padding: 20px 16px;
    margin-bottom: 18px;

    .ov-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 7px;

      .ov-value {
        font-size: 26px;
        color: var(--neon-cyan-light);
        text-shadow: 0 0 16px rgba(201, 169, 98, 0.4);
      }
    }

    .ov-divider {
      width: 1px;
      height: 34px;
      background: linear-gradient(180deg, transparent, rgba(90, 118, 165, 0.4), transparent);
    }
  }

  .search-keyword-ranking,
  .search-history-list {
    margin-bottom: 18px;
  }

  /* TOP 排行：hex 序号 + 数字读出 */
  .keyword-rank-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 7px 10px;
    margin-top: 8px;
    background: rgba(255, 255, 255, 0.5);
    border: 1px solid rgba(90, 118, 165, 0.1);
    transition: all var(--duration-fast) ease;

    &:hover {
      background: rgba(70, 96, 140, 0.1);
      border-color: rgba(90, 118, 165, 0.28);
    }

    .rank-hex {
      width: 24px;
      height: 26px;
      font-size: 12px;
    }

    .rank-keyword {
      flex: 1;
      font-size: 13px;
      color: var(--text-primary);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .rank-count {
      font-size: 14px;
    }

    .rank-unit {
      margin-left: 4px;
    }
  }

  .history-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 7px 4px;
    margin-top: 6px;
    font-size: 13px;
    border-bottom: 1px dashed rgba(90, 118, 165, 0.12);

    .history-keyword {
      flex: 1;
      color: var(--text-primary);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .history-time {
      color: var(--text-muted);
    }
  }

  /* 空状态 */
  .stats-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    padding: 30px 20px;

    .empty-hex {
      width: 60px;
      height: 66px;
    }

    .empty-title {
      font-size: 15px;
    }
  }
}

/* ==================== 响应式 ==================== */
@media (max-width: 1200px) {
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 900px) {
  .cmd-row {
    flex-wrap: wrap;
  }

  .cmd-input {
    min-width: 60%;
  }

  .rc-main {
    flex-wrap: wrap;
  }

  .rc-actions {
    flex-direction: row;
    align-items: center;
    flex-wrap: wrap;
    padding-left: 0;
    padding-top: 10px;
    border-left: none;
    border-top: 1px dashed rgba(90, 118, 165, 0.22);
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>

