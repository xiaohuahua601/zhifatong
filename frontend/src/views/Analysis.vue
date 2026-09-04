/**
 * 智法通 - 数据分析页面
 *
 * 包含法律咨询热点分析（柱状图）、法条引用统计（排行榜）、
 * 用户聚类分析（散点图）和时间趋势分析。使用ECharts图表。
 * 模板结构 v2：tech-frame 矩形科技框架 + tech-section-header 区块头 +
 * hex 徽章排行序号 + readout-box 终端读数 + tech-scan 扫描图区 + page-grid-bg 网格底纹。
 */

<template>
  <div class="analysis-page fade-in">
    <!-- 页面级网格纹理装饰层（深空监控大屏底纹） -->
    <div class="page-grid-bg"></div>

    <!-- 内容层：浮于网格纹理之上 -->
    <div class="page-content">
      <!-- ===== 页头：科技区块头大形态（hex徽章 + 渐变主标题 + 英文眉标 + 控件区） ===== -->
      <header class="page-header tech-section-header">
        <div class="hex-badge header-hex">
          <el-icon :size="22"><DataAnalysis /></el-icon>
        </div>
        <div class="header-title-group">
          <h2 class="page-title">数据分析</h2>
          <span class="tsh-sub header-eyebrow">DATA ANALYSIS CENTER</span>
        </div>
        <span class="tsh-line header-line"></span>
        <div class="tsh-extra header-actions">
          <span class="status-light is-on"></span>
          <!-- 时间范围选择器（绑定保持不变） -->
          <el-radio-group v-model="analysisDays" size="small" class="time-range-group" @change="loadAllData">
            <el-radio-button :value="7">近7天</el-radio-button>
            <el-radio-button :value="30">近30天</el-radio-button>
            <el-radio-button :value="90">近90天</el-radio-button>
          </el-radio-group>
          <!-- 数据刷新按钮（带旋转动画，绑定保持不变） -->
          <el-button class="refresh-btn" :class="{ spinning: isRefreshing }" circle size="small" @click="handleRefresh">
            <el-icon :size="14"><Refresh /></el-icon>
          </el-button>
        </div>
      </header>

      <!-- ===== 第一行：热点分析 + 引用统计 ===== -->
      <div class="charts-row stagger-section" style="--stagger-delay: 0.1s">
        <!-- 法律咨询热点分析（矩形科技框架外壳） -->
        <section class="chart-frame tech-frame" style="flex: 3">
          <div class="tech-section-header frame-header">
            <span class="tsh-bar"></span>
            <span class="tsh-title">法律咨询热点分析</span>
            <span class="tsh-sub">HOT TOPICS</span>
            <span class="tsh-line"></span>
            <div class="tsh-extra">
              <span class="status-light is-on"></span>
              <span class="tech-label">REALTIME</span>
            </div>
          </div>
          <!-- 图区：hover 扫描光带掠过 -->
          <div class="tech-scan chart-scan">
            <div ref="hotTopicChartRef" class="chart-container"></div>
          </div>
        </section>

        <!-- 法条引用统计排行（矩形科技框架外壳 + 角括号数据板） -->
        <section class="chart-frame tech-frame" style="flex: 2">
          <div class="tech-section-header frame-header">
            <span class="tsh-bar"></span>
            <span class="tsh-title">法条引用排行</span>
            <span class="tsh-sub">CITATION RANK</span>
            <span class="tsh-line"></span>
            <div class="tsh-extra">
              <span class="tech-label">TOP 10</span>
            </div>
          </div>
          <!-- 排行数据板：四角角括号包裹的滚动数据区 -->
          <div class="rank-board corner-brackets">
            <div class="citation-rank">
              <!-- 排行项：hex序号徽章 + 标题/进度条 + 终端读数/趋势，交错入场 -->
              <div
                v-for="(item, idx) in citationStats"
                :key="idx"
                class="rank-item stagger-rank-item"
                :style="{ animationDelay: `${idx * 0.08}s` }"
              >
                <!-- 序号徽章：冠军鎏金 / 亚军铜金 / 季军藏青 / 其余幽灵 -->
                <span
                  class="rank-hex hex-badge"
                  :class="idx === 0 ? 'hex-gold' : idx === 2 ? 'hex-cyan' : idx >= 3 ? 'hex-ghost' : ''"
                >{{ idx + 1 }}</span>
                <div class="rank-content">
                  <div class="rank-title">{{ item.document_title }}</div>
                  <div class="rank-bar-wrapper">
                    <!-- 进度条：藏青→鎏金渐变（保留） -->
                    <div class="rank-bar" :style="{ width: getBarWidth(item.citation_count) }"></div>
                  </div>
                </div>
                <div class="rank-meta">
                  <!-- 引用次数：终端读数框 [ 数值 ] -->
                  <span class="rank-count readout-box">
                    <span class="data-readout rank-num">{{ item.citation_count }}</span>
                    <span class="count-unit">次</span>
                  </span>
                  <!-- 排行变化趋势箭头 -->
                  <span class="rank-trend" :class="getTrendClass(item)">
                    <el-icon :size="12">
                      <component :is="getTrendIcon(item)" />
                    </el-icon>
                  </span>
                </div>
              </div>
              <el-empty v-if="citationStats.length === 0" description="暂无数据" :image-size="60" />
            </div>
          </div>
        </section>
      </div>

      <!-- ===== 第二行：趋势分析 + 用户聚类 ===== -->
      <div class="charts-row stagger-section" style="--stagger-delay: 0.25s">
        <!-- 时间趋势分析（矩形科技框架外壳） -->
        <section class="chart-frame tech-frame" style="flex: 3">
          <div class="tech-section-header frame-header">
            <span class="tsh-bar"></span>
            <span class="tsh-title">查询趋势分析</span>
            <span class="tsh-sub">QUERY TREND</span>
            <span class="tsh-line"></span>
            <div class="tsh-extra">
              <el-radio-group v-model="trendGranularity" size="small" @change="loadTrendData">
                <el-radio-button value="day">日</el-radio-button>
                <el-radio-button value="week">周</el-radio-button>
                <el-radio-button value="month">月</el-radio-button>
              </el-radio-group>
            </div>
          </div>
          <div class="tech-scan chart-scan">
            <div ref="trendChartRef" class="chart-container"></div>
          </div>
        </section>

        <!-- 用户聚类分析（矩形科技框架外壳） -->
        <section class="chart-frame tech-frame" style="flex: 2">
          <div class="tech-section-header frame-header">
            <span class="tsh-bar"></span>
            <span class="tsh-title">用户行为聚类</span>
            <span class="tsh-sub">USER CLUSTERS</span>
            <span class="tsh-line"></span>
            <div class="tsh-extra">
              <span class="tech-label">SCATTER</span>
            </div>
          </div>
          <div class="tech-scan chart-scan">
            <div ref="clusterChartRef" class="chart-container"></div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { analysisApi } from '@/api/analysis'

// ==================== 状态 ====================
const analysisDays = ref(30)
const trendGranularity = ref<'day' | 'week' | 'month'>('day')
const isRefreshing = ref(false)

// 引用统计数据
const citationStats = ref<any[]>([])

// ==================== 图表引用 ====================
const hotTopicChartRef = ref<HTMLElement>()
const trendChartRef = ref<HTMLElement>()
const clusterChartRef = ref<HTMLElement>()

let hotTopicChart: echarts.ECharts | null = null
let trendChart: echarts.ECharts | null = null
let clusterChart: echarts.ECharts | null = null

// ==================== 加载数据 ====================

// 数据刷新（带旋转动画）
const handleRefresh = async () => {
  isRefreshing.value = true
  await loadAllData()
  setTimeout(() => {
    isRefreshing.value = false
  }, 800)
}

// 加载所有数据
const loadAllData = async () => {
  await Promise.all([
    loadHotTopics(),
    loadCitationStats(),
    loadTrendData(),
    loadUserClusters(),
  ])
}

// 加载热点分析
const loadHotTopics = async () => {
  let topics: any[] = []
  try {
    const data = await analysisApi.getHotTopics({ days: analysisDays.value, top_n: 10 })
    topics = data.topics
  } catch {
    // 模拟数据
    topics = [
      { category: '劳动纠纷', count: 342, trend: 'up', sample_queries: ['加班费计算', '违法解除劳动合同'] },
      { category: '合同纠纷', count: 286, trend: 'up', sample_queries: ['违约金条款', '合同效力'] },
      { category: '知识产权', count: 198, trend: 'stable', sample_queries: ['商标侵权', '专利申请'] },
      { category: '公司法务', count: 156, trend: 'down', sample_queries: ['股东权益', '公司治理'] },
      { category: '房产纠纷', count: 134, trend: 'up', sample_queries: ['房屋买卖', '租赁合同'] },
      { category: '婚姻家庭', count: 112, trend: 'stable', sample_queries: ['离婚财产分割', '子女抚养'] },
      { category: '交通事故', count: 98, trend: 'down', sample_queries: ['事故赔偿', '责任认定'] },
      { category: '刑事辩护', count: 76, trend: 'stable', sample_queries: ['取保候审', '量刑标准'] },
    ]
  }

  await nextTick()
  renderHotTopicChart(topics)
}

// 加载引用统计
const loadCitationStats = async () => {
  try {
    const data = await analysisApi.getCitationStats({ days: analysisDays.value, top_n: 10 })
    citationStats.value = data.citations
  } catch {
    citationStats.value = [
      { document_id: 1, document_title: '民法典第464条', citation_count: 89, positive_rate: 0.92 },
      { document_id: 2, document_title: '劳动合同法第47条', citation_count: 76, positive_rate: 0.88 },
      { document_id: 3, document_title: '合同法第52条', citation_count: 65, positive_rate: 0.85 },
      { document_id: 4, document_title: '知识产权法第59条', citation_count: 52, positive_rate: 0.91 },
      { document_id: 5, document_title: '公司法第20条', citation_count: 43, positive_rate: 0.87 },
      { document_id: 6, document_title: '民法典第1064条', citation_count: 38, positive_rate: 0.83 },
      { document_id: 7, document_title: '刑法第264条', citation_count: 31, positive_rate: 0.79 },
      { document_id: 8, document_title: '物权法第9条', citation_count: 25, positive_rate: 0.90 },
    ]
  }
}

// 加载趋势数据
const loadTrendData = async () => {
  let trends: any[] = []
  try {
    const data = await analysisApi.getTrendData({ granularity: trendGranularity.value })
    trends = data.trends
  } catch {
    // 模拟数据
    for (let i = 29; i >= 0; i--) {
      const date = new Date(Date.now() - i * 86400000)
      trends.push({
        date: date.toISOString().slice(0, 10),
        query_count: Math.floor(Math.random() * 80 + 40),
        positive_feedback_rate: Math.random() * 0.3 + 0.7,
        avg_confidence: Math.random() * 0.2 + 0.75,
      })
    }
  }

  await nextTick()
  renderTrendChart(trends)
}

// 加载用户聚类
const loadUserClusters = async () => {
  let clusters: any[] = []
  let scatterData: any[] = []
  let useFallback = false
  try {
    const data = await analysisApi.getUserClusters({ days: analysisDays.value })
    clusters = data.clusters || []
    scatterData = data.scatter_data || []
    // 若后端未返回散点数据，则标记使用兜底
    if (scatterData.length === 0) {
      useFallback = true
    }
  } catch {
    useFallback = true
  }

  if (useFallback) {
    // API调用失败或无散点数据时，回退到默认聚类（无散点，显示空状态）
    clusters = [
      { cluster_id: 1, cluster_name: '劳动法专家', user_count: 120 },
      { cluster_id: 2, cluster_name: '合同审查师', user_count: 85 },
      { cluster_id: 3, cluster_name: '知识产权从业者', user_count: 65 },
      { cluster_id: 4, cluster_name: '综合咨询用户', user_count: 200 },
    ]
    scatterData = []
  }

  await nextTick()
  renderClusterChart(clusters, scatterData)
}

// ==================== 渲染图表 ====================

// 渲染热点分析柱状图（增强版：hover放大效果+更丰富动画）
const renderHotTopicChart = (topics: any[]) => {
  if (!hotTopicChartRef.value) return
  if (!hotTopicChart) {
    hotTopicChart = echarts.init(hotTopicChartRef.value)
  }

  const categories = topics.map((t) => t.category)
  const counts = topics.map((t) => t.count)

  hotTopicChart.setOption({
    tooltip: {
      trigger: 'axis',
      className: 'paper-chart-tooltip',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: 'rgba(90, 118, 165, 0.45)',
      textStyle: { color: '#172033' },
      extraCssText: 'color:#172033 !important;',
    },
    /* 更丰富的动画配置 */
    animationDuration: 1200,
    animationEasing: 'cubicOut',
    animationDelay: (idx: number) => idx * 80,
    grid: { left: '3%', right: '4%', bottom: '3%', top: '20px', containLabel: true },
    xAxis: {
      type: 'category',
      data: categories,
      axisLine: { lineStyle: { color: 'rgba(90, 118, 165, 0.35)' } },
      axisLabel: { color: '#526174', rotate: 30 },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      splitLine: { lineStyle: { color: 'rgba(90, 118, 165, 0.14)' } },
      axisLabel: { color: '#526174' },
    },
    series: [
      {
        type: 'bar',
        data: counts.map((val, idx) => ({
          value: val,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: idx < 3 ? '#4f7fc9' : '#5b91f2' },
              { offset: 1, color: idx < 3 ? 'rgba(90, 118, 165, 0.25)' : 'rgba(70, 96, 140, 0.25)' },
            ]),
            borderRadius: [4, 4, 0, 0],
            /* hover放大效果 */
            shadowBlur: 0,
            shadowColor: 'transparent',
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 15,
              shadowColor: idx < 3 ? 'rgba(90, 118, 165, 0.55)' : 'rgba(70, 96, 140, 0.55)',
            },
          },
        })),
        barWidth: '50%',
        /* hover放大效果 */
        emphasis: {
          itemStyle: {
            borderWidth: 0,
          },
        },
      },
    ],
  })
}

// 渲染趋势分析图（增强版：面积渐变+数据点标记）
const renderTrendChart = (trends: any[]) => {
  if (!trendChartRef.value) return
  if (!trendChart) {
    trendChart = echarts.init(trendChartRef.value)
  }

  const dates = trends.map((t) => t.date?.slice(5) || '')
  const queryCounts = trends.map((t) => t.query_count || 0)
  const feedbackRates = trends.map((t) => Math.round((t.positive_feedback_rate || 0) * 100))
  const confidences = trends.map((t) => Math.round((t.avg_confidence || 0) * 100))

  trendChart.setOption({
    tooltip: {
      trigger: 'axis',
      className: 'paper-chart-tooltip',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: 'rgba(90, 118, 165, 0.45)',
      textStyle: { color: '#172033' },
      extraCssText: 'color:#172033 !important;',
    },
    /* 更丰富的动画配置 */
    animationDuration: 1500,
    animationEasing: 'cubicInOut',
    legend: {
      data: ['查询量', '正面反馈率', '平均置信度'],
      textStyle: { color: '#526174' },
      top: 0,
    },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '40px', containLabel: true },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: 'rgba(90, 118, 165, 0.35)' } },
      axisLabel: { color: '#526174' },
    },
    yAxis: [
      {
        type: 'value',
        name: '查询量',
        axisLine: { show: false },
        splitLine: { lineStyle: { color: 'rgba(90, 118, 165, 0.14)' } },
        axisLabel: { color: '#526174' },
      },
      {
        type: 'value',
        name: '百分比',
        min: 0,
        max: 100,
        axisLine: { show: false },
        splitLine: { show: false },
        axisLabel: { color: '#526174', formatter: '{value}%' },
      },
    ],
    series: [
      {
        name: '查询量',
        type: 'bar',
        data: queryCounts,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(90, 118, 165, 0.65)' },
            { offset: 1, color: 'rgba(70, 96, 140, 0.08)' },
          ]),
          borderRadius: [3, 3, 0, 0],
        },
      },
      {
        name: '正面反馈率',
        type: 'line',
        yAxisIndex: 1,
        data: feedbackRates,
        smooth: true,
        lineStyle: { color: '#7ca586', width: 2 },
        itemStyle: { color: '#7ca586' },
        /* 面积渐变+数据点标记 */
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(124, 165, 134, 0.25)' },
            { offset: 1, color: 'rgba(124, 165, 134, 0.02)' },
          ]),
        },
        symbol: 'circle',
        symbolSize: 6,
        showSymbol: false,
        emphasis: { showSymbol: true, symbolSize: 10 },
      },
      {
        name: '平均置信度',
        type: 'line',
        yAxisIndex: 1,
        data: confidences,
        smooth: true,
        lineStyle: { color: '#b7791f', width: 2 },
        itemStyle: { color: '#b7791f' },
        /* 面积渐变+数据点标记 */
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(201, 169, 98, 0.22)' },
            { offset: 1, color: 'rgba(201, 169, 98, 0.02)' },
          ]),
        },
        symbol: 'diamond',
        symbolSize: 6,
        showSymbol: false,
        emphasis: { showSymbol: true, symbolSize: 10 },
      },
    ],
  })
}

// 渲染用户聚类散点图（增强版：气泡大小动画）
// 使用后端返回的 scatter_data 真实数据，按 cluster_id 区分颜色，cluster_name 作为图例
const renderClusterChart = (clusters: any[], scatterData: any[]) => {
  if (!clusterChartRef.value) return
  if (!clusterChart) {
    clusterChart = echarts.init(clusterChartRef.value)
  }

  const colors = ['#b7791f', '#2f6fed', '#7ca586', '#c9973f', '#c05b52', '#4f7fc9', '#d99b3d']

  // 按 cluster_id 分组散点数据，使用 cluster_name 作为图例名称
  const clusterMap = new Map<number, string>()
  clusters.forEach((c) => {
    clusterMap.set(c.cluster_id, c.cluster_name)
  })

  const grouped: Record<number, { name: string; points: number[][] }> = {}
  scatterData.forEach((p) => {
    const cid = p.cluster_id
    if (!grouped[cid]) {
      grouped[cid] = {
        name: p.cluster_name || clusterMap.get(cid) || `群体${cid}`,
        points: [],
      }
    }
    grouped[cid].points.push([p.x, p.y])
  })

  // 构建散点系列，每个聚类一个 series，以 cluster_name 作为图例
  const clusterIds = Object.keys(grouped).map(Number)
  const series = clusterIds.map((cid, idx) => {
    const color = colors[idx % colors.length]
    return {
      name: grouped[cid].name,
      type: 'scatter',
      data: grouped[cid].points,
      /* 气泡大小动画 */
      symbolSize: (val: number[]) => Math.max(6, Math.min(Math.abs(val[1]) / 8 + 6, 20)),
      itemStyle: {
        color,
        opacity: 0.7,
        shadowBlur: 4,
        shadowColor: color + '40',
      },
      emphasis: {
        itemStyle: {
          opacity: 1,
          shadowBlur: 12,
          shadowColor: color + '80',
        },
        symbolSize: (val: number[]) => Math.max(10, Math.min(Math.abs(val[1]) / 6 + 10, 28)),
      },
      animationDelay: (i: number) => i * 30,
    }
  })

  clusterChart.setOption({
    tooltip: {
      className: 'paper-chart-tooltip',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: 'rgba(90, 118, 165, 0.45)',
      textStyle: { color: '#172033' },
      extraCssText: 'color:#172033 !important;',
      formatter: (params: any) => {
        const name = params.seriesName
        return `${name}<br/>x: ${params.value[0]}<br/>y: ${params.value[1]}`
      },
    },
    /* 更丰富的动画配置 */
    animationDuration: 1500,
    animationEasing: 'elasticOut',
    legend: {
      textStyle: { color: '#526174' },
      top: 0,
    },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '40px', containLabel: true },
    xAxis: {
      name: '特征X',
      axisLine: { lineStyle: { color: 'rgba(90, 118, 165, 0.35)' } },
      axisLabel: { color: '#526174' },
      splitLine: { lineStyle: { color: 'rgba(90, 118, 165, 0.1)' } },
    },
    yAxis: {
      name: '特征Y',
      axisLine: { show: false },
      axisLabel: { color: '#526174' },
      splitLine: { lineStyle: { color: 'rgba(90, 118, 165, 0.1)' } },
    },
    series,
  })

  // 无散点数据时显示空状态提示
  if (scatterData.length === 0) {
    clusterChart.setOption({
      title: {
        text: '暂无聚类数据',
        left: 'center',
        top: 'center',
        textStyle: { color: '#5f7699', fontSize: 14, fontWeight: 'normal' },
      },
    })
  }
}

// 计算排行条宽度百分比
const getBarWidth = (count: number) => {
  const max = Math.max(...citationStats.value.map((c) => c.citation_count), 1)
  return `${(count / max) * 100}%`
}

// 获取排行变化趋势类名
const getTrendClass = (item: any) => {
  if (item.positive_rate >= 0.9) return 'trend-up'
  if (item.positive_rate >= 0.8) return 'trend-stable'
  return 'trend-down'
}

// 获取排行变化趋势图标
const getTrendIcon = (item: any) => {
  if (item.positive_rate >= 0.9) return 'Top'
  if (item.positive_rate >= 0.8) return 'Minus'
  return 'Bottom'
}

// 窗口大小变化时重绘图表
const handleResize = () => {
  hotTopicChart?.resize()
  trendChart?.resize()
  clusterChart?.resize()
}

// ==================== 生命周期 ====================
onMounted(async () => {
  await loadAllData()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  hotTopicChart?.dispose()
  trendChart?.dispose()
  clusterChart?.dispose()
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped lang="scss">
/* ==================== 数据分析页（结构化科技组件 v2 · tech-frame 矩形框架形态） ==================== */

/* ---- 页面根：承载网格纹理层 ---- */
.analysis-page {
  position: relative;
  min-height: 100%;
  animation: pageEnter 0.5s var(--ease-smooth, ease) forwards;
}

@keyframes pageEnter {
  from { opacity: 0; transform: translateY(14px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ---- 内容层：浮于网格纹理之上 ---- */
.page-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ==================== 页头（科技区块头大形态） ==================== */
.page-header {
  flex-wrap: wrap;

  /* 六边形主徽章：drop-shadow 沿六边形轮廓发光 */
  .header-hex {
    width: 44px;
    height: 50px;
    color: #fff;
    filter: drop-shadow(0 0 10px rgba(70, 96, 140, 0.45));
  }

  .header-title-group {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  /* 主标题：藏青→鎏金渐变 + 流光 */
  .page-title {
    font-size: 24px;
    font-weight: 700;
    letter-spacing: 2px;
    line-height: 1.1;
    background: linear-gradient(120deg, #7897bf, #4f7fc9 40%, #b7791f 100%);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: gradientShift 5s ease infinite;
  }

  .header-line {
    background: linear-gradient(90deg, rgba(90, 118, 165, 0.55), rgba(201, 169, 98, 0.28), transparent);
  }

  .header-actions {
    gap: 10px;
  }
}

/* 主标题渐变流光动画 */
@keyframes gradientShift {
  0% { background-position: 0% center; }
  50% { background-position: 100% center; }
  100% { background-position: 0% center; }
}

/* ==================== 时间范围选择器（切角小组件风） ==================== */
.time-range-group {
  :deep(.el-radio-button__inner) {
    background: rgba(255, 255, 255, 0.65);
    border-color: var(--border-color);
    color: var(--text-secondary);
    transition: all var(--duration-normal) var(--ease-smooth);

    &:hover {
      color: var(--accent-light);
    }
  }

  :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
    background: linear-gradient(135deg, rgba(60, 74, 104, 0.85), rgba(90, 118, 165, 0.75));
    border-color: rgba(124, 147, 181, 0.6);
    color: #fff;
    box-shadow: 0 0 12px rgba(70, 96, 140, 0.4);
  }
}

/* ==================== 刷新按钮（藏青旋转） ==================== */
.refresh-btn {
  background: rgba(255, 255, 255, 0.65) !important;
  border-color: var(--border-color) !important;
  color: var(--text-secondary) !important;
  transition: all var(--duration-normal) var(--ease-smooth);

  &:hover {
    color: var(--accent-color) !important;
    border-color: var(--border-strong) !important;
    box-shadow: 0 0 14px rgba(90, 118, 165, 0.25);
  }

  &.spinning {
    :deep(.el-icon) {
      animation: spin 0.8s linear infinite;
    }
  }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* ==================== 图表行与分区交错入场 ==================== */
.charts-row {
  display: flex;
  gap: 20px;
}

.stagger-section {
  animation: sectionFadeIn 0.55s var(--ease-smooth) both;
  animation-delay: var(--stagger-delay, 0s);
}

@keyframes sectionFadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ==================== 图表框架（矩形科技外壳 + 区块头 + 扫描图区） ==================== */
.chart-frame {
  display: flex;
  flex-direction: column;
  padding: 18px 20px 16px;

  .frame-header {
    margin-bottom: 14px;
    flex-wrap: wrap;
  }

  /* 图区：hover 扫描光带掠过 */
  .chart-scan {
    flex: 1;
    min-height: 0;
  }

  .chart-container {
    height: 320px;
  }
}

/* ==================== 引用排行数据板（角括号包裹的滚动数据区） ==================== */
.rank-board {
  position: relative;
  display: flex;
  flex: 1;
  min-height: 0;
  padding: 8px 4px 4px 10px;
}

.citation-rank {
  flex: 1;
  min-width: 0;
  max-height: 320px;
  overflow-y: auto;
  padding-right: 4px;
}

/* ---- 排行项：hex 序号徽章 + 标题/进度条 + 终端读数/趋势 ---- */
.rank-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 6px;
  border-bottom: 1px dashed rgba(90, 118, 165, 0.14);
  transition: background var(--duration-normal) var(--ease-smooth),
    padding-left var(--duration-normal) var(--ease-smooth);

  &:last-child {
    border-bottom: none;
  }

  /* 排行项 hover：藏青浸染右移 */
  &:hover {
    background: linear-gradient(90deg, rgba(70, 96, 140, 0.12), transparent);
    padding-left: 12px;

    .rank-title {
      color: var(--accent-light);
    }
  }

  /* 交错入场动画 */
  &.stagger-rank-item {
    animation: rankSlideIn 0.5s var(--ease-smooth) both;
  }

  /* 序号：六边形徽章（冠军鎏金 / 亚军铜金 / 季军藏青 / 其余幽灵） */
  .rank-hex {
    width: 26px;
    height: 30px;
    font-size: 12px;
  }

  .rank-content {
    flex: 1;
    min-width: 0;

    .rank-title {
      font-size: 13px;
      color: var(--text-primary);
      margin-bottom: 5px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      transition: color var(--duration-fast) ease;
    }

    .rank-bar-wrapper {
      height: 4px;
      background: rgba(255, 255, 255, 0.7);
      overflow: hidden;

      /* 进度条：藏青→鎏金渐变（保留） */
      .rank-bar {
        height: 100%;
        width: 0;
        background: linear-gradient(90deg, #2f6fed, #4f7fc9, #b7791f);
        transition: width 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94);
        position: relative;

        /* 进度条端点光珠 */
        &::after {
          content: '';
          position: absolute;
          right: 0;
          top: -1px;
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: #b7791f;
          box-shadow: 0 0 8px rgba(201, 169, 98, 0.7);
        }
      }
    }
  }

  /* 右侧读数列：终端读数框 + 趋势箭头 */
  .rank-meta {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 5px;
    flex-shrink: 0;
  }

  .rank-count {
    padding: 1px 8px;
    align-items: baseline;
    gap: 2px;

    .rank-num {
      font-size: 14px;
    }

    .count-unit {
      font-size: 10px;
      font-weight: 400;
      letter-spacing: 0.5px;
      color: var(--text-muted);
    }
  }

  /* 排行变化趋势箭头 */
  .rank-trend {
    display: flex;
    align-items: center;
    font-size: 12px;

    &.trend-up {
      color: var(--success-color);
      filter: drop-shadow(0 0 4px rgba(124, 165, 134, 0.5));
    }

    &.trend-stable {
      color: var(--warning-color);
    }

    &.trend-down {
      color: var(--danger-color);
    }
  }
}

/* 排行项交错入场动画 */
@keyframes rankSlideIn {
  from {
    opacity: 0;
    transform: translateX(20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

/* ==================== 响应式 ==================== */
@media (max-width: 1200px) {
  .charts-row {
    flex-direction: column;
  }
}
</style>
