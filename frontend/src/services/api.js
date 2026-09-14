const API_BASE = '/api'

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    const detail = Array.isArray(body.detail)
      ? body.detail.map((d) => d.msg || JSON.stringify(d)).join('; ')
      : body.detail
    throw new Error(detail || `Request failed: ${res.status}`)
  }

  if (res.status === 204) return null
  return res.json()
}

export const api = {
  predict: (url, signal) => request('/predict', { method: 'POST', body: JSON.stringify({ url }), signal }),

  history: (params = {}) => {
    const qs = new URLSearchParams()
    if (params.page) qs.set('page', params.page)
    if (params.per_page) qs.set('per_page', params.per_page)
    if (params.prediction) qs.set('prediction', params.prediction)
    const query = qs.toString()
    return request(`/history${query ? `?${query}` : ''}`)
  },

  deleteScan: (id) => request(`/history/${id}`, { method: 'DELETE' }),

  modelInfo: () => request('/model-info'),

  health: () => request('/health'),
}
