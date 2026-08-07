/**
 * 统一的 HTML 净化 / Markdown 渲染工具
 *
 * 背景：项目中多处使用 v-html 渲染 LLM 输出与联网抓取的正文，
 * 这些内容一律视为不可信输入。任何 v-html 之前必须经过本模块净化。
 * （token 存于 localStorage，一次 XSS 即可窃取会话）
 */
import DOMPurify from 'dompurify'
import { marked } from 'marked'

// 允许的标签集合：覆盖 Markdown 常用输出，排除脚本/表单/内联事件
const ALLOWED_TAGS = [
  'p', 'br', 'hr', 'span', 'div',
  'strong', 'b', 'em', 'i', 'u', 's', 'del', 'mark', 'small', 'sub', 'sup',
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
  'ul', 'ol', 'li',
  'blockquote', 'pre', 'code',
  'table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td',
  'a', 'img',
]

const ALLOWED_ATTR = ['href', 'title', 'target', 'rel', 'src', 'alt', 'width', 'height', 'class', 'colspan', 'rowspan']

const CONFIG = {
  ALLOWED_TAGS,
  ALLOWED_ATTR,
  // 只允许安全协议，阻断 javascript: / data:text/html
  ALLOWED_URI_REGEXP: /^(?:(?:https?|mailto|tel):|[^a-z]|[a-z+.-]+(?:[^a-z+.\-:]|$))/i,
  FORBID_TAGS: ['script', 'style', 'iframe', 'object', 'embed', 'form', 'input', 'link', 'base'],
  FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover', 'style'],
}

// 外链统一加 noopener/noreferrer，防 tabnabbing
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A' && node.hasAttribute('href')) {
    node.setAttribute('target', '_blank')
    node.setAttribute('rel', 'noopener noreferrer')
  }
})

/** 净化一段已经是 HTML 的字符串 */
export function sanitizeHtml(html) {
  if (!html) return ''
  return DOMPurify.sanitize(String(html), CONFIG)
}

/** 把 Markdown 渲染成安全的 HTML */
export function renderMarkdown(content) {
  if (!content) return ''
  return DOMPurify.sanitize(marked.parse(String(content)), CONFIG)
}

export default { sanitizeHtml, renderMarkdown }
