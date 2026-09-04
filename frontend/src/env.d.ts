/**
 * 智法通 - TypeScript 环境声明文件
 * 声明 Vue 单文件组件、CSS 模块、Vite 环境变量等类型
 * 使 TypeScript 能正确识别这些模块的类型
 */

/// <reference types="vite/client" />

/* ----------------------------------------------------------
 * Vue 单文件组件类型声明
 * 使 .vue 文件在 TypeScript 中可被正确导入
 * ---------------------------------------------------------- */
declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<
    Record<string, unknown>,
    Record<string, unknown>,
    unknown
  >
  export default component
}

/* ----------------------------------------------------------
 * CSS 模块类型声明
 * 当使用 <style module> 时提供类型支持
 * ---------------------------------------------------------- */
declare module '*.module.css' {
  const classes: Record<string, string>
  export default classes
}

declare module '*.module.scss' {
  const classes: Record<string, string>
  export default classes
}

declare module '*.module.less' {
  const classes: Record<string, string>
  export default classes
}

/* ----------------------------------------------------------
 * 静态资源类型声明
 * 图片、字体等静态资源的导入类型
 * ---------------------------------------------------------- */
declare module '*.png' {
  const src: string
  export default src
}

declare module '*.jpg' {
  const src: string
  export default src
}

declare module '*.jpeg' {
  const src: string
  export default src
}

declare module '*.gif' {
  const src: string
  export default src
}

declare module '*.svg' {
  const src: string
  export default src
}

declare module '*.webp' {
  const src: string
  export default src
}

declare module '*.ico' {
  const src: string
  export default src
}

declare module '*.woff' {
  const src: string
  export default src
}

declare module '*.woff2' {
  const src: string
  export default src
}

declare module '*.ttf' {
  const src: string
  export default src
}

declare module '*.eot' {
  const src: string
  export default src
}

/* ----------------------------------------------------------
 * Vite 环境变量类型声明
 * 定义 import.meta.env 上可用的环境变量
 * ---------------------------------------------------------- */
interface ImportMetaEnv {
  /** API 基础地址 */
  readonly VITE_API_BASE_URL: string
  /** 应用标题 */
  readonly VITE_APP_TITLE: string
  /** 是否启用调试模式 */
  readonly VITE_DEBUG: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

/* ----------------------------------------------------------
 * 全局类型扩展
 * ---------------------------------------------------------- */
/** 扩展 Window 接口，添加全局属性 */
interface Window {
  /** ECharts 实例映射（用于多图表场景） */
  __echarts_instances__?: Map<string, unknown>
}
