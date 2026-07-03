// 单用户 API 客户端。token 存 localStorage,每次请求带在 header。
const TOKEN_KEY = 'zbrain_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}
export function setToken(t) {
  localStorage.setItem(TOKEN_KEY, t)
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

function authHeaders() {
  return { Authorization: `Bearer ${getToken()}` }
}

async function req(path, opts = {}) {
  const res = await fetch(`/api${path}`, {
    ...opts,
    headers: { ...authHeaders(), ...(opts.headers || {}) },
  })
  if (res.status === 401) {
    const e = new Error('unauthorized')
    e.status = 401
    throw e
  }
  if (!res.ok) {
    const e = new Error(`HTTP ${res.status}`)
    e.status = res.status
    throw e
  }
  const ct = res.headers.get('content-type') || ''
  return ct.includes('application/json') ? res.json() : res
}

// 原图 URL(带 token 走 query 不方便,改用 fetch blob 也可;这里图片直接用 <img> + 代理,
// 但接口需鉴权 → 用 fetch 拿 blob 生成 objectURL)
export async function fileObjectUrl(checksum) {
  const res = await fetch(`/api/files/${checksum}`, { headers: authHeaders() })
  if (!res.ok) throw new Error('file load failed')
  const blob = await res.blob()
  return URL.createObjectURL(blob)
}

export const api = {
  health: () => req('/health'),
  whoami: () => req('/whoami'),

  listItems: (params = {}) => {
    const q = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') q.set(k, v)
    })
    return req(`/items?${q.toString()}`)
  },
  getItem: (id) => req(`/items/${id}`),
  updateItem: (id, patch) =>
    req(`/items/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
    }),
  softDelete: (id) => req(`/items/${id}/soft-delete`, { method: 'PATCH' }),
  restore: (id) => req(`/items/${id}/restore`, { method: 'POST' }),
  purge: (id) => req(`/items/${id}/purge`, { method: 'DELETE' }),

  uploadItems: (files) => {
    const fd = new FormData()
    for (const f of files) fd.append('images', f)
    return req('/items/upload', { method: 'POST', body: fd })
  },

  dimensions: () => req('/stats/dimensions'),

  // 消化闭环
  review: (id) => req(`/items/${id}/review`, { method: 'PATCH' }),
  promote: (id) => req(`/items/${id}/promote`, { method: 'PATCH' }),
  toNote: (id) => req(`/items/${id}/to-note`, { method: 'POST' }),
  resurface: (limit = 5) => req(`/feed/resurface?limit=${limit}`),
  deleteNote: (id) => req(`/feed/notes/${id}/soft-delete`, { method: 'PATCH' }),
  search: (q) => req(`/search?q=${encodeURIComponent(q)}`),
}
