<!-- ============================================================
 * 智法通 - ECharts 封装组件
 * 功能：响应式图表、自动resize、主题配色
 * ============================================================ -->
<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick, shallowRef } from 'vue'
import * as echarts from 'echarts'

/* ----------------------------------------------------------
 * Props 定义
 * ---------------------------------------------------------- */
const props = withDefaults(defineProps<{
  /** ECharts 配置项 */
  option: Record<string, any>
  /** 图表宽度（CSS值） */
  width?: string
  /** 图表高度（CSS值） */
  height?: string
  /** 主题名称 */
  theme?: string
  /** 是否自动resize */
  autoResize?: boolean
}>(), {
  width: '100%',
  height: '400px',
  theme: 'dark',
  autoResize: true,
})

/* ----------------------------------------------------------
 * 事件
 * ---------------------------------------------------------- */
const emit = defineEmits<{
  /** 图表初始化完成 */
  (e: 'ready', chart: echarts.ECharts): void
  /** 图表点击事件 */
  (e: 'chart-click', params: any): void
}>()

/* ----------------------------------------------------------
 * 图表实例管理
 * 使用 shallowRef 避免深度响应式代理导致的性能问题
 * ---------------------------------------------------------- */
const chartRef = ref<HTMLDivElement>()
const chartInstance = shallowRef<echarts.ECharts>()

/* ----------------------------------------------------------
 * 深色主题配色
 * 定义智法通专属的ECharts深色主题
 * ---------------------------------------------------------- */
const darkThemeConfig = {
  color: [
    '#b7791f',   // 鎏金
    '#2f6fed',   // 藏青
    '#7ca586',   // 鼠尾草绿
    '#c9973f',   // 琥珀
    '#c05b52',   // 砖红
    '#4f7fc9',   // 藏青蓝
    '#d99b3d',   // 浅金
    '#9a948a',   // 暖灰
  ],
  backgroundColor: 'transparent',
  textStyle: {
    color: '#526174',
  },
  title: {
    textStyle: {
      color: '#172033',
    },
    subtextStyle: {
      color: '#526174',
    },
  },
  legend: {
    textStyle: {
      color: '#526174',
    },
  },
  tooltip: {
    className: 'paper-chart-tooltip',
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
    borderColor: 'rgba(148, 158, 178, 0.2)',
    textStyle: {
      color: '#172033',
    },
    extraCssText: 'color:#172033 !important;',
  },
  categoryAxis: {
    axisLine: {
      lineStyle: {
        color: 'rgba(148, 158, 178, 0.2)',
      },
    },
    axisTick: {
      lineStyle: {
        color: 'rgba(148, 158, 178, 0.2)',
      },
    },
    axisLabel: {
      color: '#526174',
    },
    splitLine: {
      lineStyle: {
        color: 'rgba(148, 158, 178, 0.12)',
      },
    },
  },
  valueAxis: {
    axisLine: {
      lineStyle: {
        color: 'rgba(148, 158, 178, 0.2)',
      },
    },
    axisTick: {
      lineStyle: {
        color: 'rgba(148, 158, 178, 0.2)',
      },
    },
    axisLabel: {
      color: '#526174',
    },
    splitLine: {
      lineStyle: {
        color: 'rgba(148, 158, 178, 0.12)',
      },
    },
  },
}

/* ----------------------------------------------------------
 * 初始化图表
 * ---------------------------------------------------------- */
const initChart = () => {
  if (!chartRef.value) return

  // 注册自定义主题
  echarts.registerTheme('zhifatong-dark', darkThemeConfig)

  // 创建实例，使用自定义主题
  const themeName = props.theme === 'dark' ? 'zhifatong-dark' : props.theme
  chartInstance.value = echarts.init(chartRef.value, themeName)

  // 设置配置项
  chartInstance.value.setOption(props.option)

  // 绑定点击事件
  chartInstance.value.on('click', (params: any) => {
    emit('chart-click', params)
  })

  emit('ready', chartInstance.value)
}

/* ----------------------------------------------------------
 * 更新图表配置
 * ---------------------------------------------------------- */
const updateChart = () => {
  if (!chartInstance.value) return
  chartInstance.value.setOption(props.option, { notMerge: false })
}

/* ----------------------------------------------------------
 * 自动resize
 * 使用 ResizeObserver 监听容器尺寸变化
 * ---------------------------------------------------------- */
let resizeObserver: ResizeObserver | null = null

const setupResize = () => {
  if (!props.autoResize || !chartRef.value) return

  resizeObserver = new ResizeObserver(() => {
    chartInstance.value?.resize()
  })
  resizeObserver.observe(chartRef.value)
}

/* ----------------------------------------------------------
 * 监听配置项变化
 * ---------------------------------------------------------- */
watch(
  () => props.option,
  () => {
    nextTick(() => {
      updateChart()
    })
  },
  { deep: true }
)

/* ----------------------------------------------------------
 * 生命周期
 * ---------------------------------------------------------- */
onMounted(() => {
  nextTick(() => {
    initChart()
    setupResize()
  })
})

onBeforeUnmount(() => {
  // 清理resize监听
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
  // 销毁图表实例
  if (chartInstance.value) {
    chartInstance.value.dispose()
    chartInstance.value = undefined
  }
})

/* ----------------------------------------------------------
 * 暴露方法（供父组件调用）
 * ---------------------------------------------------------- */
defineExpose({
  /** 获取ECharts实例 */
  getChartInstance: () => chartInstance.value,
  /** 手动触发resize */
  resize: () => chartInstance.value?.resize(),
  /** 清空图表 */
  clear: () => chartInstance.value?.clear(),
})
</script>

<template>
  <div
    ref="chartRef"
    class="echarts-wrapper"
    :style="{ width, height }"
  />
</template>

<style scoped>
.echarts-wrapper {
  min-height: 200px;
}
</style>
