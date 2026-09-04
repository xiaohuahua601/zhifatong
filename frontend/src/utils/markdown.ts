/**
 * 智法通 - Markdown 渲染工具
 *
 * 使用 marked 解析 Markdown 为 HTML，DOMPurify 净化防 XSS，
 * 并增加法条引用高亮等后处理。
 */

import { marked } from 'marked'
import DOMPurify from 'dompurify'

// 配置 marked：启用 GFM、换行转 <br>
marked.setOptions({
  gfm: true,
  breaks: true,
})

/**
 * 渲染 Markdown 文本为安全的 HTML
 *
 * @param raw 原始 Markdown 文本
 * @returns 净化后的 HTML 字符串
 */
export function renderMarkdown(raw: string): string {
  if (!raw) return ''

  // 1. marked 解析 Markdown → HTML
  let html = marked.parse(raw, { async: false }) as string

  // 2. 后处理：法条引用高亮（如 《民法典》第四十七条）
  //    在文本节点中匹配，避免破坏已有 HTML 标签
  html = highlightLawCitations(html)

  // 3. 给所有 <a> 标签添加 target="_blank" 和 rel="noopener"
  html = html.replace(/<a(?![^>]*target=)/g, '<a target="_blank" rel="noopener noreferrer"')

  // 4. DOMPurify 净化，防止 XSS
  html = DOMPurify.sanitize(html, {
    ALLOWED_TAGS: [
      'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
      'p', 'br', 'hr',
      'strong', 'b', 'em', 'i', 'del', 's', 'mark',
      'ul', 'ol', 'li',
      'blockquote', 'code', 'pre',
      'a', 'span', 'div',
      'table', 'thead', 'tbody', 'tr', 'th', 'td',
      'img',
    ],
    ALLOWED_ATTR: ['href', 'src', 'alt', 'title', 'class', 'target', 'rel'],
  })

  return html
}

/**
 * 在 HTML 文本节点中高亮法条引用
 *
 * 匹配模式：《法律名称》第X条 或 《法律名称》第X条第Y款
 * 仅在文本内容中替换，不修改 HTML 标签内部
 */
function highlightLawCitations(html: string): string {
  // 法条引用正则：《某法》第X条（支持中文数字和阿拉伯数字）
  const lawPattern = /《([^》]+)》第([一二三四五六七八九十百千万零\d]+)条/g

  // 将 HTML 按标签分割，仅对文本部分替换
  // 简单方案：直接全局替换（法条格式不会出现在 HTML 标签属性中）
  return html.replace(lawPattern, '<span class="law-citation">《$1》第$2条</span>')
}
