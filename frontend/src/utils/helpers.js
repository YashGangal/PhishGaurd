export function getRiskColor(score) {
  if (score <= 33) return 'text-safe'
  if (score <= 66) return 'text-caution'
  return 'text-danger'
}

export function truncateUrl(url, maxLen = 48) {
  if (!url) return ''
  return url.length <= maxLen ? url : url.substring(0, maxLen) + '…'
}

export function downloadCsv(filename, rows) {
  const escape = (v) => {
    const s = String(v ?? '')
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
  }
  const csv = rows.map((r) => r.map(escape).join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(objectUrl)
}
