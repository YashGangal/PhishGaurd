/* Single fetch wrapper for the bench API.
    Dev uses the relative base (Vite proxies /api → :8000, prefix stripped).
    Static-hosted builds (HF Static, Vercel) use VITE_API_BASE as the
    absolute backend origin, e.g. VITE_API_BASE=https://my-backend.
    If unset, falls back to "" so fetch stays same-origin. */

const API_BASE = import.meta.env.VITE_API_BASE ?? ''

/* Absolute backend origin — used for Swagger/docs links and copied endpoint URLs. */
export const API_ORIGIN = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
export const DOCS_URL = import.meta.env.VITE_DOCS_URL ?? `${API_ORIGIN}/docs`

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`
  const headers = { ...options.headers }
  if (options.body !== undefined) headers['Content-Type'] = 'application/json'
  const res = await fetch(url, {
    ...options,
    headers,
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    const detail = Array.isArray(body.detail)
      ? body.detail.map((d) => d.msg || JSON.stringify(d)).join('; ')
      : body.detail
    throw new Error(detail || `Request failed: ${res.status}`)
  }

  if (res.status === 204) return null
  return res.json().catch(() => {
    throw new Error('Malformed response from bench')
  })
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
