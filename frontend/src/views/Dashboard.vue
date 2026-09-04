/**
 * 智法通 - 仪表盘页面（案卷墨蓝 · 鎏金典雅）
 *
 * 展示系统概览：统计卡片、趋势图、法律领域分布饼图、
 * 最近活动时间线和快捷操作入口。
 * 形态语言：纸纹肌理层 + 圆形金徽 + 鎏金读数框 +
 * 金线区块头 + 圆点节点时间线 + 素净金线快捷卡。
 */

<template>
  <div class="dashboard-page">
    <!-- 页面级网格纹理装饰层 -->
    <div class="page-grid-bg"></div>

    <!-- 内容层（浮于网格纹理之上） -->
    <div class="page-content">
      <!-- 页面标题区域 -->
      <div class="page-header">
        <div class="header-left">
          <span class="tech-label page-eyebrow">企业级智能法律顾问平台</span>
          <h2 class="greeting">{{ greetingText }}</h2>
          <p class="date-text">
            <span class="diamond-node date-diamond"></span>
            {{ currentDate }}
          </p>
        </div>
        <div class="header-right">
          <!-- 迷你系统状态面板（矩形科技框架） -->
          <div class="sys-panel tech-frame">
            <div class="sys-status-item">
              <span class="status-light is-on"></span>
              <span class="tech-label">后端服务</span>
            </div>
            <div class="sys-status-item">
              <span class="status-light is-on"></span>
              <span class="tech-label">数据库</span>
            </div>
            <div class="sys-status-item">
              <span class="status-light is-on"></span>
              <span class="tech-label">AI 引擎</span>
            </div>
            <span class="sys-ok-chip">
              <el-icon :size="12"><TrendCharts /></el-icon>
              运行正常
            </span>
          </div>
        </div>
      </div>

      <!-- 统计卡片行（六边形徽章 + 终端读数框 + 趋势chip 三段结构） -->
      <div class="stats-row">
        <div
          v-for="(stat, index) in statCards"
          :key="stat.key"
          class="stat-card tech-frame"
          :style="{ '--stagger-delay': index * 0.1 + 's' }"
          @mousemove="handleStatMouseMove($event, index)"
          @mouseleave="handleStatMouseLeave(index)"
        >
          <!-- 渐变边框效果 -->
          <div class="stat-card-border" :style="{ background: stat.borderGradient }"></div>
          <div
            class="stat-card-inner"
            :style="statCardStyles[index]"
          >
            <!-- 顶行：六边形图标徽章 + 短标签 + 趋势chip -->
            <div class="stat-top">
              <div class="hex-badge stat-hex" :style="{ background: stat.iconBg }">
                <el-icon :size="20"><component :is="stat.icon" /></el-icon>
              </div>
              <span class="tech-label stat-code">{{ stat.code }}</span>
              <div class="stat-trend" :class="stat.trendType">
                <el-icon :size="12" class="trend-arrow">
                  <Top v-if="stat.trendType === 'up'" />
                  <Bottom v-else />
                </el-icon>
                <span>{{ stat.trend }}</span>
              </div>
            </div>
            <!-- 中部：终端读数框 [ 数值 ] -->
            <div class="stat-mid">
              <div class="readout-box">
                <span class="data-readout stat-value">{{ animatedValues[index] }}</span>
              </div>
            </div>
            <!-- 底部：全称 + 装饰渐变细线 -->
            <div class="stat-bottom">
              <span class="stat-label">{{ stat.label }}</span>
              <span class="stat-deco-line"></span>
            </div>
          </div>
        </div>
      </div>

      <!-- 图表行 -->
      <div class="charts-row">
        <!-- 咨询趋势折线图 -->
        <div class="chart-card glass-card" style="flex: 2">
          <div class="tech-section-header">
            <span class="tsh-bar"></span>
            <span class="tsh-title">咨询趋势</span>
            <span class="tsh-sub">趋势监测</span>
            <span class="tsh-line"></span>
            <div class="tsh-extra">
              <el-radio-group v-model="trendDays" size="small" @change="loadTrends">
                <el-radio-button :value="7">7天</el-radio-button>
                <el-radio-button :value="30">30天</el-radio-button>
                <el-radio-button :value="90">90天</el-radio-button>
              </el-radio-group>
            </div>
          </div>
          <div class="tech-scan chart-scan">
            <div ref="trendChartRef" class="chart-container"></div>
          </div>
        </div>

        <!-- 法律领域分布饼图 -->
        <div class="chart-card glass-card" style="flex: 1">
          <div class="tech-section-header">
            <span class="tsh-bar"></span>
            <span class="tsh-title">法律领域分布</span>
            <span class="tsh-sub">领域分布</span>
            <span class="tsh-line"></span>
          </div>
          <div class="tech-scan chart-scan">
            <div ref="pieChartRef" class="chart-container"></div>
          </div>
        </div>
      </div>

      <!-- 法律知识图谱（Neo4j真实实体关系，对应项目文档4.1.5节 Schema 设计）
           节点类型：Law(法律) / Article(法条) / Case(案例) / Concept(法律概念)
           关系类型：HAS_ARTICLE / REFERENCES / MENTIONS / INVOLVES
           数据来源：GET /dashboard/graph 实时查询Neo4j图谱
           动态效果：自动巡游高亮、关系流动箭头、定时刷新 -->
      <div class="graph-card glass-card">
        <div class="tech-section-header">
          <span class="tsh-bar"></span>
          <span class="tsh-title">法律知识图谱</span>
          <span class="tsh-sub">实体关系图谱</span>
          <span class="tsh-line"></span>
          <div class="tsh-extra graph-extra">
            <!-- 数据源徽标（hex形态）：Neo4j实时 / 本地降级 -->
            <span class="hex-badge graph-source-hex" :class="graphData.source">
              <span class="badge-dot"></span>
            </span>
            <span class="graph-source-text" :class="graphData.source">
              {{ graphData.source === 'neo4j' ? 'Neo4j 实时图谱' : '本地数据（降级）' }}
            </span>
            <span v-if="graphData.total_nodes" class="graph-meta">
              <span class="data-readout graph-meta-num">{{ graphData.total_nodes }}</span> 节点 ·
              <span class="data-readout graph-meta-num">{{ graphData.total_links }}</span> 关系
            </span>
            <el-button text size="small" :loading="graphLoading" @click="loadGraph">
              <el-icon><Refresh /></el-icon>&nbsp;刷新
            </el-button>
          </div>
        </div>
        <!-- 图例（圆形小徽记形态） -->
        <div class="graph-legend-row">
          <span class="legend-item">
            <span class="hex-badge legend-hex" style="background: #b7791f"></span>法律
          </span>
          <span class="legend-item">
            <span class="hex-badge legend-hex" style="background: #5b91f2"></span>法条
          </span>
          <span class="legend-item">
            <span class="hex-badge legend-hex" style="background: #7897bf"></span>案例
          </span>
          <span class="legend-item">
            <span class="hex-badge legend-hex" style="background: #7ca586"></span>概念
          </span>
        </div>
        <div v-loading="graphLoading" class="tech-scan graph-container">
          <div ref="graphChartRef" class="graph-canvas"></div>
        </div>
      </div>

      <!-- 下方区域 -->
      <div class="bottom-row">
        <!-- 最近活动（垂直时间线结构） -->
        <div class="activity-card glass-card" style="flex: 2">
          <div class="tech-section-header">
            <span class="tsh-bar"></span>
            <span class="tsh-title">最近活动</span>
            <span class="tsh-sub">活动记录</span>
            <span class="tsh-line"></span>
            <div class="tsh-extra">
              <el-button type="primary" size="small" class="activity-all-btn">查看全部</el-button>
            </div>
          </div>
          <div class="activity-timeline">
            <div
              v-for="(activity, aIndex) in recentActivities"
              :key="activity.id"
              class="tl-item"
              :style="{ '--item-delay': aIndex * 0.08 + 's' }"
              @mouseenter="activity.hovered = true"
              @mouseleave="activity.hovered = false"
            >
              <!-- 左侧节点列：菱形节点（按类型着色），竖线由CSS绘制 -->
              <div class="tl-node-col">
                <span
                  class="diamond-node"
                  :class="activity.type === 'query' ? 'node-cyan' : activity.type === 'contract' ? 'node-gold' : ''"
                ></span>
              </div>
              <!-- 右侧内容 -->
              <div class="tl-body">
                <div class="tl-head">
                  <div class="activity-icon hex-badge" :class="activity.type">
                    <el-icon :size="13">
                      <ChatDotRound v-if="activity.type === 'query'" />
                      <Document v-else-if="activity.type === 'contract'" />
                      <Collection v-else />
                    </el-icon>
                  </div>
                  <span class="tl-type">{{ activityTypeMap[activity.type] || activity.type }}</span>
                  <span class="tl-time">{{ formatTime(activity.created_at) }}</span>
                </div>
                <div class="tl-title">{{ activity.title }}</div>
                <div class="tl-desc">{{ activity.description }}</div>
                <!-- hover时显示更多详情的展开效果 -->
                <transition name="detail-expand">
                  <div v-if="activity.hovered" class="activity-detail">
                    <span>类型：{{ activityTypeMap[activity.type] || activity.type }}</span>
                    <span>时间：{{ formatTime(activity.created_at) }}</span>
                  </div>
                </transition>
              </div>
            </div>
            <el-empty v-if="recentActivities.length === 0" description="暂无活动" />
          </div>
        </div>

        <!-- 快捷操作（hex图标 + 角括号卡形态） -->
        <div class="quick-card glass-card" style="flex: 1">
          <div class="tech-section-header">
            <span class="tsh-bar"></span>
            <span class="tsh-title">快捷操作</span>
            <span class="tsh-sub">常用功能</span>
            <span class="tsh-line"></span>
          </div>
          <div class="quick-actions">
            <div
              v-for="(quick, qIndex) in quickActions"
              :key="quick.label"
              class="quick-item corner-brackets"
              :style="{
                '--quick-delay': qIndex * 0.1 + 's',
                background: quick.bgGradient
              }"
              @click="handleQuickClick($event, quick.route)"
            >
              <div class="hex-badge quick-hex" :style="{ background: quick.iconBg }">
                <el-icon :size="20" :color="quick.iconColor"><component :is="quick.icon" /></el-icon>
              </div>
              <span class="quick-label">{{ quick.label }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { dashboardApi } from '@/api/dashboard'
import {
  ChatDotRound,
  Document,
  Collection,
  TrendCharts,
  Top,
  Bottom,
  Refresh,
} from '@element-plus/icons-vue'

const router = useRouter()

// ==================== 页面标题区域（问候语+日期） ====================
const greetingText = computed(() => {
  const hour = new Date().getHours()
  if (hour < 6) return '夜深了，注意休息'
  if (hour < 12) return '早上好，开始新的一天'
  if (hour < 14) return '中午好，辛苦了'
  if (hour < 18) return '下午好，继续加油'
  return '晚上好，今天辛苦了'
})

const currentDate = computed(() => {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  const weekDays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']
  const weekDay = weekDays[now.getDay()]
  return `${year}年${month}月${day}日 ${weekDay}`
})

// ==================== 统计卡片数据 ====================
const statCards = reactive([
  {
    key: 'queries',
    code: '咨询',
    label: '今日咨询数',
    value: 0,
    targetValue: 0,
    icon: ChatDotRound,
    iconBg: 'linear-gradient(160deg, #b3944f, #8a6f3c)',
    trend: '+12%',
    trendType: 'up' as const,
    borderGradient: 'linear-gradient(135deg, rgba(201, 169, 98, 0.55), rgba(201, 169, 98, 0.06))',
  },
  {
    key: 'contracts',
    code: '合同',
    label: '合同审查数',
    value: 0,
    targetValue: 0,
    icon: Document,
    iconBg: 'linear-gradient(160deg, #688e72, #55775f)',
    trend: '+8%',
    trendType: 'up' as const,
    borderGradient: 'linear-gradient(135deg, rgba(124, 165, 134, 0.5), rgba(124, 165, 134, 0.06))',
  },
  {
    key: 'documents',
    code: '文档',
    label: '知识库文档数',
    value: 0,
    targetValue: 0,
    icon: Collection,
    iconBg: 'linear-gradient(160deg, #4f7fc9, #2f6fed)',
    trend: '+5%',
    trendType: 'up' as const,
    borderGradient: 'linear-gradient(135deg, rgba(90, 118, 165, 0.5), rgba(90, 118, 165, 0.06))',
  },
  {
    key: 'users',
    code: '用户',
    label: '总用户数',
    value: 0,
    targetValue: 0,
    icon: TrendCharts,
    iconBg: 'linear-gradient(160deg, #7897bf, #5f7699)',
    trend: '+3%',
    trendType: 'up' as const,
    borderGradient: 'linear-gradient(135deg, rgba(124, 147, 181, 0.5), rgba(124, 147, 181, 0.06))',
  },
])

// ==================== 数字滚动计数动画 ====================
const animatedValues = ref<string[]>(['0', '0', '0', '0'])

// 使用requestAnimationFrame实现数字滚动动画
const animateNumber = (index: number, target: number, duration: number = 1500) => {
  const start = 0
  const startTime = performance.now()

  const update = (currentTime: number) => {
    const elapsed = currentTime - startTime
    const progress = Math.min(elapsed / duration, 1)
    // 使用easeOutExpo缓动函数
    const eased = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress)
    const current = Math.floor(start + (target - start) * eased)
    animatedValues.value[index] = current.toLocaleString()

    if (progress < 1) {
      requestAnimationFrame(update)
    }
  }

  requestAnimationFrame(update)
}

// ==================== 统计卡片3D倾斜效果 ====================
const statCardStyles = ref<Record<string, string>[]>([
  {}, {}, {}, {},
])

const handleStatMouseMove = (e: MouseEvent, index: number) => {
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
  const x = (e.clientX - rect.left) / rect.width
  const y = (e.clientY - rect.top) / rect.height
  const rotateX = (0.5 - y) * 5
  const rotateY = (x - 0.5) * 5
  statCardStyles.value[index] = {
    transform: `perspective(600px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`,
    transition: 'transform 0.1s ease-out',
  }
}

const handleStatMouseLeave = (index: number) => {
  statCardStyles.value[index] = {
    transform: 'perspective(600px) rotateX(0deg) rotateY(0deg)',
    transition: 'transform 0.5s ease-out',
  }
}

// ==================== 趋势图 ====================
const trendDays = ref(30)
const trendChartRef = ref<HTMLElement>()
let trendChart: echarts.ECharts | null = null

// ==================== 饼图 ====================
const pieChartRef = ref<HTMLElement>()
let pieChart: echarts.ECharts | null = null

// ==================== 法律知识图谱（Neo4j真实实体关系） ====================
// 对应项目文档4.1.5节 Neo4j 知识图谱 Schema：
// 节点类型：Law(法律) / Article(法条) / Case(案例) / Concept(法律概念)
// 关系类型：HAS_ARTICLE / REFERENCES / MENTIONS / INVOLVES
const graphChartRef = ref<HTMLElement>()
let graphChart: echarts.ECharts | null = null

// 图谱数据（从后端 GET /dashboard/graph 加载，Neo4j实时查询）
const graphData = ref<{
  nodes: any[]
  links: any[]
  source: string
  total_nodes: number
  total_links: number
}>({ nodes: [], links: [], source: 'local', total_nodes: 0, total_links: 0 })
const graphLoading = ref(false)

// 知识图谱分类配置（节点类型 -> 颜色 + 名称，鎏金典雅体系）
const graphCategories = [
  { name: '法律', itemStyle: { color: '#b7791f' } },       // 鎏金 - 法律本体
  { name: '法条', itemStyle: { color: '#5b91f2' } },       // 藏青 - 具体法条
  { name: '案例', itemStyle: { color: '#7897bf' } },       // 蓝灰 - 司法案例
  { name: '概念', itemStyle: { color: '#7ca586' } },       // 鼠尾草绿 - 法律概念
]

// 动态效果：自动巡游高亮（spotlight轮播）
let spotlightTimer: ReturnType<typeof setInterval> | null = null
let spotlightIndex = 0

// 动态效果：定时刷新图谱数据（保持实时性）
let graphRefreshTimer: ReturnType<typeof setInterval> | null = null
const GRAPH_REFRESH_INTERVAL = 60 * 1000  // 60秒

// 加载知识图谱数据（Neo4j真实实体关系；失败时降级为静态示例）
const loadGraph = async () => {
  graphLoading.value = true
  try {
    const data = await dashboardApi.getKnowledgeGraph({ limit: 250 })
    if (data.nodes?.length) {
      graphData.value = data
    } else {
      applyFallbackGraph()
    }
  } catch {
    applyFallbackGraph()
  } finally {
    graphLoading.value = false
  }

  await nextTick()
  renderGraphChart()
}

// 降级数据（API不可用时的最小示例，与后端Schema一致）
const applyFallbackGraph = () => {
  const nodes = [
    { id: 'law_civil', name: '民法典', category: 0, symbolSize: 60, value: '法律 · 示例数据', degree: 0 },
    { id: 'law_labor', name: '劳动合同法', category: 0, symbolSize: 52, value: '法律 · 示例数据', degree: 0 },
    { id: 'art_585', name: '第585条\n违约金', category: 1, symbolSize: 32, value: '法条 · 示例数据', degree: 0 },
    { id: 'art_87', name: '第87条\n违法解除', category: 1, symbolSize: 28, value: '法条 · 示例数据', degree: 0 },
    { id: 'case_001', name: '劳动合同\n纠纷案', category: 2, symbolSize: 26, value: '案例 · 示例数据', degree: 0 },
    { id: 'concept_breach', name: '违约责任', category: 3, symbolSize: 34, value: '概念 · 示例数据', degree: 0 },
  ]
  const links = [
    { source: 'law_civil', target: 'art_585', value: 'HAS_ARTICLE' },
    { source: 'law_labor', target: 'art_87', value: 'HAS_ARTICLE' },
    { source: 'case_001', target: 'art_87', value: 'REFERENCES' },
    { source: 'case_001', target: 'concept_breach', value: 'INVOLVES' },
    { source: 'art_585', target: 'concept_breach', value: 'MENTIONS' },
  ]
  graphData.value = { nodes, links, source: 'local', total_nodes: nodes.length, total_links: links.length }
}

// ==================== 最近活动 ====================
const recentActivities = ref<any[]>([])

// 活动类型映射
const activityTypeMap: Record<string, string> = {
  query: '法律咨询',
  contract: '合同审查',
  document: '知识库',
}

// ==================== 快捷操作数据 ====================
const quickActions = [
  {
    label: '法律咨询',
    icon: ChatDotRound,
    iconBg: 'linear-gradient(160deg, #b3944f, #8a6f3c)',
    iconColor: '#f5efdf',
    route: '/qa',
    bgGradient: 'linear-gradient(135deg, rgba(201, 169, 98, 0.08), rgba(255, 255, 255, 0.4))',
  },
  {
    label: '合同审查',
    icon: Document,
    iconBg: 'linear-gradient(160deg, #688e72, #55775f)',
    iconColor: '#f0f5f1',
    route: '/contract',
    bgGradient: 'linear-gradient(135deg, rgba(124, 165, 134, 0.08), rgba(255, 255, 255, 0.4))',
  },
  {
    label: '知识库',
    icon: Collection,
    iconBg: 'linear-gradient(160deg, #4f7fc9, #2f6fed)',
    iconColor: '#172033',
    route: '/knowledge',
    bgGradient: 'linear-gradient(135deg, rgba(90, 118, 165, 0.08), rgba(255, 255, 255, 0.4))',
  },
  {
    label: '数据分析',
    icon: TrendCharts,
    iconBg: 'linear-gradient(160deg, #7897bf, #5f7699)',
    iconColor: '#f2f5fa',
    route: '/analysis',
    bgGradient: 'linear-gradient(135deg, rgba(124, 147, 181, 0.08), rgba(255, 255, 255, 0.4))',
  },
]

// 快捷操作点击水波纹效果
const handleQuickClick = (e: MouseEvent, route: string) => {
  // 水波纹效果
  const target = e.currentTarget as HTMLElement
  const ripple = document.createElement('span')
  ripple.classList.add('ripple-effect')
  const rect = target.getBoundingClientRect()
  const size = Math.max(rect.width, rect.height)
  ripple.style.width = ripple.style.height = size + 'px'
  ripple.style.left = e.clientX - rect.left - size / 2 + 'px'
  ripple.style.top = e.clientY - rect.top - size / 2 + 'px'
  target.appendChild(ripple)
  setTimeout(() => ripple.remove(), 600)

  router.push(route)
}

// ==================== 加载数据 ====================

// 加载概览统计
const loadOverview = async () => {
  try {
    const data = await dashboardApi.getOverview()
    statCards[0].targetValue = data.today_queries
    statCards[1].targetValue = data.total_contracts
    statCards[2].targetValue = data.total_documents
    statCards[3].targetValue = data.total_users
  } catch {
    // 使用模拟数据
    statCards[0].targetValue = 128
    statCards[1].targetValue = 56
    statCards[2].targetValue = 1024
    statCards[3].targetValue = 386
  }

  // 启动数字滚动动画
  statCards.forEach((_, index) => {
    animateNumber(index, statCards[index].targetValue)
  })
}

// 加载趋势数据
const loadTrends = async () => {
  let trendData: any[] = []
  try {
    const data = await dashboardApi.getTrends({ days: trendDays.value })
    trendData = data.trends
  } catch {
    // 使用模拟数据
    trendData = generateMockTrendData(trendDays.value)
  }

  await nextTick()
  renderTrendChart(trendData)
}

// 加载最近活动
const loadActivities = async () => {
  try {
    const data = await dashboardApi.getRecentActivities({ limit: 8 })
    recentActivities.value = data.activities.map((a: any) => ({ ...a, hovered: false }))
  } catch {
    // 使用模拟数据
    recentActivities.value = [
      { id: 1, type: 'query', title: '劳动合同违约赔偿咨询', description: '用户3 · 置信度92%', created_at: new Date().toISOString(), hovered: false },
      { id: 2, type: 'contract', title: '采购合同审查', description: '风险等级：中 · 评分72', created_at: new Date(Date.now() - 3600000).toISOString(), hovered: false },
      { id: 3, type: 'document', title: '民法典合同编', description: '分块数：156 · 已索引', created_at: new Date(Date.now() - 7200000).toISOString(), hovered: false },
      { id: 4, type: 'query', title: '知识产权侵权纠纷', description: '用户5 · 置信度88%', created_at: new Date(Date.now() - 10800000).toISOString(), hovered: false },
      { id: 5, type: 'contract', title: '租赁合同审查', description: '风险等级：低 · 评分85', created_at: new Date(Date.now() - 14400000).toISOString(), hovered: false },
    ]
  }
}

// 渲染趋势折线图（增强：动画配置 + 数据点hover放大 + 渐变背景）
const renderTrendChart = (data: any[]) => {
  if (!trendChartRef.value) return
  if (!trendChart) {
    trendChart = echarts.init(trendChartRef.value)
  }

  const dates = data.map((d) => d.date?.slice(5) || '')
  const queries = data.map((d) => d.queries || 0)
  const contracts = data.map((d) => d.contracts || 0)
  const users = data.map((d) => d.users || 0)

  trendChart.setOption({
    // 动画配置（收敛）
    animationDuration: 900,
    animationEasing: 'cubicOut',
    animationDurationUpdate: 500,
    animationEasingUpdate: 'cubicOut',
    tooltip: {
      trigger: 'axis',
      className: 'paper-chart-tooltip',
      backgroundColor: '#fffdf8',
      borderColor: '#c9d8ec',
      textStyle: { color: '#172033' },
      extraCssText: 'color:#172033 !important; box-shadow:0 10px 24px rgba(23,32,51,.12);',
    },
    legend: {
      data: ['咨询数', '合同数', '新用户'],
      textStyle: { color: '#526174' },
      top: 0,
    },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '40px', containLabel: true },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: 'rgba(154, 148, 138, 0.25)' } },
      axisLabel: { color: '#9a948a' },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      splitLine: { lineStyle: { color: 'rgba(154, 148, 138, 0.12)' } },
      axisLabel: { color: '#9a948a' },
    },
    series: [
      {
        name: '咨询数',
        type: 'line',
        data: queries,
        smooth: true,
        lineStyle: { color: '#b7791f', width: 2 },
        itemStyle: { color: '#b7791f' },
        // 数据点hover放大效果
        emphasis: {
          scale: true,
          itemStyle: { borderWidth: 3, borderColor: '#d99b3d' },
        },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(201, 169, 98, 0.2)' },
          { offset: 1, color: 'rgba(201, 169, 98, 0)' },
        ]) },
      },
      {
        name: '合同数',
        type: 'line',
        data: contracts,
        smooth: true,
        lineStyle: { color: '#7ca586', width: 2 },
        itemStyle: { color: '#7ca586' },
        emphasis: {
          scale: true,
          itemStyle: { borderWidth: 3, borderColor: '#a5c5ac' },
        },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(124, 165, 134, 0.16)' },
          { offset: 1, color: 'rgba(124, 165, 134, 0)' },
        ]) },
      },
      {
        name: '新用户',
        type: 'line',
        data: users,
        smooth: true,
        lineStyle: { color: '#4f7fc9', width: 2 },
        itemStyle: { color: '#4f7fc9' },
        emphasis: {
          scale: true,
          itemStyle: { borderWidth: 3, borderColor: '#a9b8cd' },
        },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(90, 118, 165, 0.16)' },
          { offset: 1, color: 'rgba(90, 118, 165, 0)' },
        ]) },
      },
    ],
  })
}

// 渲染法律领域分布饼图（增强：选中扇区弹出效果 + 动画配置）
const renderPieChart = (distribution: any[] = []) => {
  if (!pieChartRef.value) return
  if (!pieChart) {
    pieChart = echarts.init(pieChartRef.value)
  }

  // 饼图配色（鎏金典雅系）
  const pieColors = ['#b7791f', '#5b91f2', '#7897bf', '#d99b3d', '#8c5914', '#7ca586', '#4f7fc9', '#9a948a']

  // 将分布数据转换为饼图所需格式，附带配色
  const pieData = distribution.map((item, idx) => ({
    value: item.value,
    name: item.name,
    itemStyle: { color: pieColors[idx % pieColors.length] },
  }))

  pieChart.setOption({
    // 增强动画配置
    animationDuration: 1000,
    animationEasing: 'cubicOut',
    animationDurationUpdate: 500,
    animationEasingUpdate: 'cubicOut',
    tooltip: {
      trigger: 'item',
      className: 'paper-chart-tooltip',
      backgroundColor: '#fffdf8',
      borderColor: '#c9d8ec',
      textStyle: { color: '#172033' },
      extraCssText: 'color:#172033 !important; box-shadow:0 10px 24px rgba(23,32,51,.12);',
    },
    legend: {
      orient: 'vertical',
      right: '5%',
      top: 'center',
      textStyle: { color: '#526174', fontSize: 12 },
    },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['35%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 4, borderColor: '#ffffff', borderWidth: 2 },
        label: { show: false },
        emphasis: {
          label: { show: true, fontSize: 14, fontWeight: 'bold', color: '#172033' },
          // 选中扇区弹出效果
          scaleSize: 10,
        },
        // 选中扇区弹出效果
        selectedMode: 'single',
        selectedOffset: 15,
        data: pieData,
      },
    ],
  })
}

// 加载法律领域分布数据
const loadDomainDistribution = async () => {
  let distribution: any[] = []
  try {
    const data = await dashboardApi.getDomainDistribution()
    distribution = data.distribution || []
  } catch {
    // API调用失败时回退到默认数据（不再是主要数据源）
    distribution = [
      { name: '劳动法', value: 35 },
      { name: '合同法', value: 25 },
      { name: '知识产权', value: 18 },
      { name: '公司法', value: 12 },
      { name: '刑法', value: 10 },
    ]
  }

  await nextTick()
  renderPieChart(distribution)
}

// 渲染法律知识图谱（力导向图，Neo4j真实实体关系）
// 使用ECharts Graph类型展示法条-案例-概念的关联关系网络
// 动态特性：力导向自动布局、节点拖拽、hover高亮邻接、关系流动箭头、
//           自动巡游高亮（spotlight轮播）、点击聚焦子图、定时数据刷新
const renderGraphChart = () => {
  if (!graphChartRef.value) return
  if (!graphChart) {
    graphChart = echarts.init(graphChartRef.value)
    // 点击节点：聚焦该节点邻接子图（与hover一致的交互增强）
    graphChart.on('click', (params: any) => {
      if (params.dataType === 'node') {
        graphChart?.dispatchAction({
          type: 'highlight',
          seriesIndex: 0,
          dataIndex: params.dataIndex,
        })
      }
    })
  }

  const { nodes, links } = graphData.value

  graphChart.setOption({
    // 增强动画配置（数据刷新时平滑过渡）
    animationDuration: 1500,
    animationEasingUpdate: 'quinticInOut',
    animationDurationUpdate: 800,
    tooltip: {
      className: 'paper-chart-tooltip',
      formatter: (params: any) => {
        // 节点tooltip：显示名称、类型、关联度和描述
        if (params.dataType === 'node') {
          return `<b>${params.data.name.replace('\n', ' ')}</b><br/>类型：${graphCategories[params.data.category].name}<br/>${params.data.value || ''}`
        }
        // 边tooltip：显示关系类型
        if (params.dataType === 'edge') {
          return `关系：${params.data.value}`
        }
        return ''
      },
      backgroundColor: '#fffdf8',
      borderColor: '#c9d8ec',
      textStyle: { color: '#172033' },
      extraCssText: 'color:#172033 !important; box-shadow:0 10px 24px rgba(23,32,51,.12);',
    },
    // 力导向布局配置
    series: [
      {
        type: 'graph',
        layout: 'force',
        // 数据（Neo4j真实实体关系，节点大小按关联度动态计算）
        data: nodes,
        links,
        categories: graphCategories,
        // 力导向参数：斥力越大节点越分散，引力使关联节点聚集
        force: {
          repulsion: 400,        // 节点间斥力
          gravity: 0.1,          // 重力，使节点向中心聚集
          edgeLength: [80, 160], // 边长度范围
          layoutAnimation: true, // 布局动画
        },
        // 节点样式
        roam: true,              // 允许缩放和拖拽
        draggable: true,         // 节点可拖拽
        symbol: 'circle',
        label: {
          show: true,
          position: 'inside',
          color: '#172033',
          fontSize: 11,
          fontWeight: 600,
          formatter: (params: any) => params.data.name,
        },
        // 边样式：流动箭头指示关系方向
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: 7,
        lineStyle: {
          color: '#9a948a',      // 暖灰细边
          width: 1.2,
          curveness: 0.15,       // 边弯曲度，避免重叠
          opacity: 0.25,
        },
        // 边标签（关系类型）- 默认不显示，hover时显示
        edgeLabel: {
          show: false,
          formatter: (params: any) => params.data.value,
          fontSize: 10,
          color: '#526174',
        },
        // 强调样式：hover/巡游时高亮邻接节点和边，并显示关系类型标签
        emphasis: {
          focus: 'adjacency',    // 聚焦邻接节点和边
          scale: 1.25,           // 高亮节点放大，突出巡游效果
          lineStyle: {
            width: 2.5,
            color: '#b7791f',
          },
          label: {
            fontSize: 13,
            fontWeight: 700,
          },
          itemStyle: {
            shadowBlur: 10,
            shadowColor: 'rgba(201, 169, 98, 0.45)',  // 金色柔光
          },
          edgeLabel: {
            show: true,           // hover时显示关系类型
          },
        },
      },
    ],
  })

  startSpotlight()
}

// 动态效果：自动巡游高亮
// 每隔2.5秒轮播高亮下一个节点（带邻接聚焦），形成"巡游探照灯"效果
const startSpotlight = () => {
  stopSpotlight()
  if (!graphChart || !graphData.value.nodes.length) return

  spotlightTimer = setInterval(() => {
    if (!graphChart || !graphData.value.nodes.length) return
    const nodeCount = graphData.value.nodes.length
    const prevIndex = spotlightIndex
    // 取消上一个节点的高亮
    graphChart.dispatchAction({
      type: 'downplay',
      seriesIndex: 0,
      dataIndex: prevIndex,
    })
    // 高亮当前节点（emphasis.focus: adjacency自动聚焦邻接子图）
    spotlightIndex = (spotlightIndex + 1) % nodeCount
    graphChart.dispatchAction({
      type: 'highlight',
      seriesIndex: 0,
      dataIndex: spotlightIndex,
    })
  }, 2500)
}

const stopSpotlight = () => {
  if (spotlightTimer) {
    clearInterval(spotlightTimer)
    spotlightTimer = null
  }
}

// 生成模拟趋势数据
const generateMockTrendData = (days: number) => {
  const data = []
  for (let i = days - 1; i >= 0; i--) {
    const date = new Date(Date.now() - i * 86400000)
    data.push({
      date: date.toISOString().slice(0, 10),
      queries: Math.floor(Math.random() * 100 + 50),
      contracts: Math.floor(Math.random() * 30 + 10),
      users: Math.floor(Math.random() * 15 + 3),
    })
  }
  return data
}

// 格式化时间
const formatTime = (time: string) => {
  if (!time) return ''
  const date = new Date(time)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  return `${Math.floor(diff / 86400000)}天前`
}

// 窗口大小变化时重绘图表
const handleResize = () => {
  trendChart?.resize()
  pieChart?.resize()
  graphChart?.resize()
}

// ==================== 生命周期 ====================
onMounted(async () => {
  await Promise.all([loadOverview(), loadTrends(), loadActivities(), loadDomainDistribution()])
  // 知识图谱：从后端加载Neo4j真实实体关系并渲染
  await loadGraph()
  // 动态效果：定时刷新图谱数据，保持与Neo4j实时同步
  graphRefreshTimer = setInterval(() => {
    loadGraph()
  }, GRAPH_REFRESH_INTERVAL)
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  trendChart?.dispose()
  pieChart?.dispose()
  graphChart?.dispose()
  // 清理图谱动态效果定时器
  stopSpotlight()
  if (graphRefreshTimer) {
    clearInterval(graphRefreshTimer)
    graphRefreshTimer = null
  }
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped lang="scss">
/* ==================== 仪表盘页面（案卷墨蓝 · 鎏金典雅） ==================== */

/* 根容器：相对定位，承载页面级纸纹肌理层 */
.dashboard-page {
  position: relative;
  min-height: 100%;
}

/* 内容层：浮于纸纹肌理之上 */
.page-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-height: 100%;
  animation: pageEnter 0.35s var(--ease-smooth, ease) forwards;
}

@keyframes pageEnter {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes staggerEnter {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ==================== 页面标题区域 ==================== */
.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  animation: staggerEnter 0.35s var(--ease-smooth, ease) forwards;
}

.header-left {
  .page-eyebrow {
    display: block;
    margin-bottom: 7px;
    color: var(--text-muted);
  }

  /* 问候语：衬线大字 · 象牙至鎏金渐变 */
  .greeting {
    font-family: var(--font-serif);
    font-size: 26px;
    font-weight: 600;
    margin: 0;
    line-height: 1.25;
    letter-spacing: 2px;
    background: var(--gradient-text);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  /* 日期时间行：圆点节点引导 */
  .date-text {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    color: var(--text-secondary);
    margin: 8px 0 0;
    letter-spacing: 1px;

    .date-diamond {
      width: 7px;
      height: 7px;
    }
  }
}

/* 迷你系统状态面板（素净金线框架 + 静态状态灯） */
.sys-panel {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 18px 10px 16px;

  .sys-status-item {
    display: flex;
    align-items: center;
    gap: 7px;
  }

  /* 运行正常：金边静色章 */
  .sys-ok-chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 2px;
    color: var(--accent-light);
    border: 1px solid rgba(201, 169, 98, 0.45);
    background: rgba(201, 169, 98, 0.08);
    border-radius: 3px;
  }
}

/* ==================== 统计卡片行（三段式结构） ==================== */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.stat-card {
  position: relative;
  padding: 0;
  cursor: default;
  /* stagger入场延迟 */
  animation: staggerEnter 0.35s var(--ease-smooth, ease) forwards;
  animation-delay: var(--stagger-delay);
  opacity: 0;
}

/* 渐变描边效果（随卡片色系：金 / 藏青系） */
.stat-card-border {
  position: absolute;
  inset: 0;
  padding: 1px;
  border-radius: 6px;
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
  z-index: 2;
}

.stat-card-inner {
  position: relative;
  z-index: 1;
  padding: 16px 18px 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transform-style: preserve-3d;

  /* ---- 顶行：圆形徽记 + 短标签 + 趋势chip ---- */
  .stat-top {
    display: flex;
    align-items: center;
    gap: 10px;

    .stat-hex {
      width: 38px;
      height: 38px;
      color: #f5efdf;
    }

    .stat-code {
      flex: 1;
      overflow: hidden;
      text-overflow: ellipsis;
      color: var(--text-muted);
    }
  }

  /* ---- 中部：鎏金读数框 [ 数值 ] ---- */
  .stat-mid {
    display: flex;
    align-items: center;

    .stat-value {
      font-size: 30px;
    }
  }

  /* ---- 底部：全称 + 装饰渐变细线 ---- */
  .stat-bottom {
    display: flex;
    align-items: center;
    gap: 10px;

    .stat-label {
      font-size: 13px;
      color: var(--text-secondary);
      letter-spacing: 1px;
      white-space: nowrap;
    }

    .stat-deco-line {
      flex: 1;
      height: 1px;
      min-width: 20px;
      background: linear-gradient(90deg, rgba(201, 169, 98, 0.4), rgba(148, 158, 178, 0.12), transparent);
    }
  }

  /* 趋势指示器（静色，升鼠尾草绿 / 降砖红） */
  .stat-trend {
    display: inline-flex;
    align-items: center;
    gap: 2px;
    font-size: 11px;
    font-weight: 600;
    padding: 2px 7px;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;

    &.up {
      color: #7ca586;
      background: rgba(124, 165, 134, 0.1);
      border: 1px solid rgba(124, 165, 134, 0.28);
    }

    &.down {
      color: #c05b52;
      background: rgba(192, 91, 82, 0.1);
      border: 1px solid rgba(192, 91, 82, 0.28);
    }
  }
}

/* ==================== 图表行 ==================== */
.charts-row {
  display: flex;
  gap: 20px;
  animation: staggerEnter 0.35s var(--ease-smooth, ease) forwards;
  animation-delay: 0.2s;
  opacity: 0;
}

.chart-card {
  padding: 18px 20px;
  display: flex;
  flex-direction: column;

  /* 图表容器 */
  .chart-scan {
    flex: 1;
    margin-top: 14px;
  }

  .chart-container {
    height: 300px;
  }
}

/* ==================== 知识图谱卡片 ==================== */
.graph-card {
  padding: 18px 20px;
  animation: staggerEnter 0.35s var(--ease-smooth, ease) forwards;
  animation-delay: 0.25s;
  opacity: 0;

  .graph-extra {
    gap: 12px;
    flex-wrap: wrap;
  }

  /* 数据源徽记（圆形）：Neo4j实时=鼠尾草绿 / 本地降级=琥珀 */
  .graph-source-hex {
    width: 18px;
    height: 18px;

    .badge-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: rgba(245, 239, 223, 0.92);
    }

    &.neo4j {
      background: linear-gradient(160deg, #7ca586, #688e72);
    }

    &.local {
      background: linear-gradient(160deg, #c9973f, #a67c33);
    }
  }

  .graph-source-text {
    font-size: 12px;
    white-space: nowrap;

    &.neo4j {
      color: #7ca586;
    }

    &.local {
      color: #c9973f;
    }
  }

  /* 节点/关系统计：数字读出小号 */
  .graph-meta {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    color: var(--text-secondary);
    white-space: nowrap;

    .graph-meta-num {
      font-size: 15px;
    }
  }

  /* 图例行（圆形小徽记） */
  .graph-legend-row {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 18px;
    margin-top: 12px;
    flex-wrap: wrap;

    .legend-item {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      font-size: 12px;
      color: var(--text-secondary);
      transition: color var(--duration-fast, 0.15s) ease;

      &:hover {
        color: var(--text-primary);
      }
    }

    .legend-hex {
      width: 10px;
      height: 10px;
    }
  }

  .graph-container {
    height: 380px;
    position: relative;
    margin-top: 8px;
  }

  .graph-canvas {
    width: 100%;
    height: 100%;
  }
}

/* ==================== 下方区域 ==================== */
.bottom-row {
  display: flex;
  gap: 20px;
  animation: staggerEnter 0.35s var(--ease-smooth, ease) forwards;
  animation-delay: 0.3s;
  opacity: 0;
}

/* ---- 最近活动：垂直时间线 ---- */
.activity-card {
  padding: 18px 20px;

  .activity-timeline {
    position: relative;
    max-height: 340px;
    overflow-y: auto;
    margin-top: 14px;
  }

  .tl-item {
    position: relative;
    display: flex;
    gap: 14px;
    padding: 10px 8px;
    animation: activityItemEnter 0.35s var(--ease-smooth, ease) forwards;
    animation-delay: var(--item-delay);
    opacity: 0;
    transition: background var(--duration-fast, 0.15s) ease;

    /* 左侧竖线：鎏金细线，从当前节点中心延伸到下一项节点中心 */
    &::before {
      content: '';
      position: absolute;
      left: 7.5px;
      top: 20px;
      bottom: -20px;
      width: 1px;
      background: rgba(201, 169, 98, 0.25);
      pointer-events: none;
    }

    &:last-child::before {
      display: none;
    }

    &:hover {
      background: rgba(201, 169, 98, 0.05);
    }
  }

  @keyframes activityItemEnter {
    from {
      opacity: 0;
      transform: translateX(-8px);
    }
    to {
      opacity: 1;
      transform: translateX(0);
    }
  }

  /* 节点列：圆点节点居于竖线之上 */
  .tl-node-col {
    position: relative;
    z-index: 1;
    display: flex;
    justify-content: center;
    width: 16px;
    padding-top: 5px;
    flex-shrink: 0;
  }

  /* 右侧内容 */
  .tl-body {
    flex: 1;
    min-width: 0;

    .tl-head {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 5px;
    }

    /* 活动类型图标：圆形徽记（蓝灰 / 鎏金 / 鼠尾草绿） */
    .activity-icon {
      width: 24px;
      height: 24px;

      &.query {
        background: linear-gradient(160deg, #7897bf, #4f7fc9);
        color: #f2f5fa;
      }

      &.contract {
        background: linear-gradient(160deg, #b7791f, #8c5914);
        color: #1d1810;
      }

      &.document {
        background: linear-gradient(160deg, #7ca586, #688e72);
        color: #f0f5f1;
      }
    }

    .tl-type {
      font-size: 11px;
      letter-spacing: 1.5px;
      color: var(--accent-light);
      padding: 1px 8px;
      border: 1px solid rgba(201, 169, 98, 0.3);
      background: rgba(201, 169, 98, 0.07);
      white-space: nowrap;
    }

    /* 时间：等宽数字 */
    .tl-time {
      margin-left: auto;
      font-size: 11px;
      color: var(--text-muted);
      font-variant-numeric: tabular-nums;
      letter-spacing: 0.5px;
      white-space: nowrap;
    }

    .tl-title {
      font-family: var(--font-serif);
      font-size: 14px;
      color: var(--text-primary);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .tl-desc {
      font-size: 12px;
      color: var(--text-secondary);
      margin-top: 2px;
    }

    /* hover展开详情 */
    .activity-detail {
      display: flex;
      gap: 12px;
      margin-top: 6px;
      font-size: 11px;
      color: #526174;
      padding: 4px 8px;
      background: #fffdf8;
      border: 1px solid #e2e9f2;
      border-left: 2px solid rgba(201, 169, 98, 0.45);
    }
  }
}

/* 详情展开过渡动画 */
.detail-expand-enter-active {
  transition: all 0.3s ease;
}

.detail-expand-leave-active {
  transition: all 0.2s ease;
}

.detail-expand-enter-from,
.detail-expand-leave-to {
  opacity: 0;
  max-height: 0;
  margin-top: 0;
  overflow: hidden;
}

.detail-expand-enter-to,
.detail-expand-leave-from {
  opacity: 1;
  max-height: 40px;
  margin-top: 6px;
}

/* ---- 快捷操作：圆形徽记 + 素净金线卡 ---- */
.quick-card {
  padding: 18px 20px;
  display: flex;
  flex-direction: column;

  .quick-actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
    margin-top: 16px;
  }

  /* 快捷项：素净小面板（水波纹容器） */
  .quick-item {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    padding: 22px 12px 18px;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    cursor: pointer;
    transition: border-color var(--duration-normal, 0.28s) var(--ease-smooth, ease),
      transform var(--duration-normal, 0.28s) var(--ease-smooth, ease);
    overflow: hidden;
    animation: quickItemEnter 0.35s var(--ease-smooth, ease) forwards;
    animation-delay: var(--quick-delay);
    opacity: 0;

    &:hover {
      border-color: rgba(201, 169, 98, 0.45);
      transform: translateY(-2px);

      .quick-hex {
        box-shadow: inset 0 0 0 1px rgba(220, 196, 137, 0.4);
      }
    }

    .quick-label {
      font-size: 13px;
      color: var(--text-secondary);
      letter-spacing: 2px;
    }
  }

  @keyframes quickItemEnter {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }

  .quick-hex {
    width: 44px;
    height: 44px;
    color: #f5efdf;
  }
}

/* 水波纹效果（鎏金，弱化） */
.ripple-effect {
  position: absolute;
  border-radius: 50%;
  background: rgba(201, 169, 98, 0.28);
  transform: scale(0);
  animation: ripple 0.6s ease-out;
  pointer-events: none;
}

@keyframes ripple {
  to {
    transform: scale(4);
    opacity: 0;
  }
}

/* ==================== 响应式 ==================== */
@media (max-width: 1200px) {
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }
  .charts-row {
    flex-direction: column;

    .chart-card {
      flex: none !important;
    }
  }
  .bottom-row {
    flex-direction: column;

    .activity-card,
    .quick-card {
      flex: none !important;
    }
  }
  .graph-container {
    height: 320px;
  }
  .sys-panel {
    flex-wrap: wrap;
    gap: 10px 14px;
  }
}

@media (max-width: 768px) {
  .stats-row {
    grid-template-columns: 1fr;
  }
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  .graph-legend-row {
    justify-content: flex-start;
  }
}
</style>
