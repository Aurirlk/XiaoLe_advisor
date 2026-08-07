/**
 * exportUtils.js - 导出工具
 * 支持对话导出 PDF、志愿表导出 Excel
 */

/**
 * 导出对话为文本/PDF
 */
export function exportChatAsText(messages, filename = '对话记录') {
  const lines = messages.map(msg => {
    const time = new Date(msg.timestamp).toLocaleString('zh-CN')
    const role = msg.role === 'user' ? '用户' : 'AI助手'
    return `[${time}] ${role}:\n${msg.content}\n`
  })
  
  const content = `小乐AI 对话记录\n导出时间: ${new Date().toLocaleString('zh-CN')}\n${'='.repeat(50)}\n\n${lines.join('\n')}`
  
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  downloadBlob(blob, `${filename}.txt`)
}

/**
 * 导出对话为 HTML（可用于打印为 PDF）
 */
export function exportChatAsHTML(messages, filename = '对话记录') {
  const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>${filename}</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif; max-width: 800px; margin: 0 auto; padding: 40px; }
    h1 { color: #1e3a5f; border-bottom: 2px solid #1e3a5f; padding-bottom: 10px; }
    .meta { color: #718096; font-size: 14px; margin-bottom: 30px; }
    .message { margin-bottom: 20px; padding: 15px; border-radius: 12px; }
    .user { background: #1e3a5f; color: white; margin-left: 20%; }
    .assistant { background: #f0f4f8; border: 1px solid #e2e8f0; margin-right: 20%; }
    .role { font-weight: 600; margin-bottom: 5px; }
    .time { font-size: 12px; opacity: 0.7; }
    .content { line-height: 1.6; white-space: pre-wrap; }
  </style>
</head>
<body>
  <h1>🎓 小乐AI 对话记录</h1>
  <div class="meta">导出时间: ${new Date().toLocaleString('zh-CN')}</div>
  ${messages.map(msg => `
    <div class="message ${msg.role}">
      <div class="role">${msg.role === 'user' ? '👤 用户' : '🎓 AI助手'}</div>
      <div class="content">${escapeHtml(msg.content)}</div>
      <div class="time">${new Date(msg.timestamp).toLocaleString('zh-CN')}</div>
    </div>
  `).join('')}
</body>
</html>`
  
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
  downloadBlob(blob, `${filename}.html`)
}

/**
 * 导出志愿表为 CSV（可用 Excel 打开）
 */
export function exportFormAsCSV(formResult, filename = '志愿表') {
  const headers = ['序号', '类型', '院校', '专业', '录取分数', '录取位次', '录取概率', '理由']
  const rows = []
  
  let index = 1
  const categories = [
    { key: 'rush_items', label: '冲' },
    { key: 'stable_items', label: '稳' },
    { key: 'safe_items', label: '保' }
  ]
  
  categories.forEach(cat => {
    (formResult[cat.key] || []).forEach(item => {
      rows.push([
        index++,
        cat.label,
        item.university,
        item.major,
        item.admission_score,
        item.admission_rank,
        (item.probability * 100).toFixed(0) + '%',
        item.reason || ''
      ])
    })
  })
  
  const csv = [
    headers.join(','),
    ...rows.map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(','))
  ].join('\n')
  
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' })
  downloadBlob(blob, `${filename}.csv`)
}

/**
 * 导出志愿表为 HTML（可打印）
 */
export function exportFormAsHTML(formResult, filename = '志愿表') {
  const categories = [
    { key: 'rush_items', label: '冲一冲', icon: '🚀', color: '#f39c12' },
    { key: 'stable_items', label: '稳一稳', icon: '🎯', color: '#1e3a5f' },
    { key: 'safe_items', label: '保一保', icon: '🛡️', color: '#27ae60' }
  ]
  
  const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>${filename}</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", sans-serif; max-width: 1000px; margin: 0 auto; padding: 40px; }
    h1 { color: #1e3a5f; text-align: center; }
    .info { display: flex; justify-content: center; gap: 30px; margin: 20px 0; color: #718096; }
    .category { margin: 30px 0; }
    .category h2 { display: flex; align-items: center; gap: 10px; }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    th, td { padding: 10px 12px; border: 1px solid #e2e8f0; text-align: left; font-size: 14px; }
    th { background: #f0f4f8; font-weight: 600; }
    .prob-high { color: #27ae60; font-weight: 600; }
    .prob-medium { color: #f39c12; font-weight: 600; }
    .prob-low { color: #e74c3c; font-weight: 600; }
    .notes { background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; padding: 20px; margin-top: 30px; }
    .notes h3 { color: #92400e; margin-bottom: 10px; }
    .notes li { color: #92400e; margin-bottom: 5px; }
  </style>
</head>
<body>
  <h1>🎓 高考志愿填报表</h1>
  <div class="info">
    <span>省份: ${formResult.province}</span>
    <span>选科: ${formResult.subject_type}</span>
    <span>分数: ${formResult.score}</span>
    <span>位次: ${formResult.rank}</span>
  </div>
  
  ${categories.map(cat => `
    <div class="category">
      <h2>${cat.icon} ${cat.label} (${(formResult[cat.key] || []).length} 个)</h2>
      <table>
        <thead>
          <tr><th>序号</th><th>院校</th><th>专业</th><th>分数</th><th>位次</th><th>概率</th><th>理由</th></tr>
        </thead>
        <tbody>
          ${(formResult[cat.key] || []).map((item, i) => `
            <tr>
              <td>${i + 1}</td>
              <td>${item.university}</td>
              <td>${item.major}</td>
              <td>${item.admission_score}</td>
              <td>${item.admission_rank}</td>
              <td class="${probClass(item.probability)}">${(item.probability * 100).toFixed(0)}%</td>
              <td>${item.reason || '-'}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `).join('')}
  
  ${formResult.notes?.length ? `
    <div class="notes">
      <h3>📋 填报建议</h3>
      <ul>${formResult.notes.map(n => `<li>${n}</li>`).join('')}</ul>
    </div>
  ` : ''}
</body>
</html>`
  
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
  downloadBlob(blob, `${filename}.html`)
}

// 辅助函数
function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function probClass(prob) {
  if (prob >= 0.7) return 'prob-high'
  if (prob >= 0.4) return 'prob-medium'
  return 'prob-low'
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
