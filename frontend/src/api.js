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
//
// blob 按 checksum(+是否缩略图)缓存:同一张图在列表间来回翻页/返回不用重新走网络。
// 只缓存 blob 本身,objectURL 仍按每次挂载现造现收(避免不销毁地累积 URL)。
const _blobCache = new Map()
const _BLOB_CACHE_LIMIT = 300

function _cacheKey(checksum, thumb) {
  return `${checksum}:${thumb ? 't' : 'f'}`
}

export async function fileObjectUrl(checksum, { thumb = false } = {}) {
  const key = _cacheKey(checksum, thumb)
  let blob = _blobCache.get(key)
  if (!blob) {
    const res = await fetch(`/api/files/${checksum}${thumb ? '?thumb=true' : ''}`, {
      headers: authHeaders(),
    })
    if (!res.ok) throw new Error('file load failed')
    blob = await res.blob()
    if (_blobCache.size >= _BLOB_CACHE_LIMIT) {
      _blobCache.delete(_blobCache.keys().next().value)
    }
    _blobCache.set(key, blob)
  }
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
  deleteItem: (id) => req(`/items/${id}/soft-delete`, { method: 'PATCH' }),
  restoreItem: (id) => req(`/items/${id}/restore`, { method: 'POST' }),
  purgeItem: (id) => req(`/items/${id}/purge`, { method: 'DELETE' }),
  reviewQueue: (limit = 10, filters = {}) => {
    const q = new URLSearchParams({ limit: String(limit) })
    Object.entries(filters).forEach(([k, v]) => { if (v) q.set(k, v) })
    return req(`/items/review-queue?${q.toString()}`)
  },
  reviewFacets: () => req('/items/review-facets'),
  reclassifyItem: (id) => req(`/items/${id}/reclassify`, { method: 'POST' }),
  recommendations: (limit = 10) => req(`/items/recommendations?limit=${limit}`),

  uploadItems: (files) => {
    const fd = new FormData()
    for (const f of files) fd.append('images', f)
    return req('/items/upload', { method: 'POST', body: fd })
  },

  dimensions: () => req('/stats/dimensions'),
  overview: () => req('/stats/overview'),
  workerStatus: () => req('/worker/status'),

  // 消化闭环
  review: (id) => req(`/items/${id}/review`, { method: 'PATCH' }),
  promote: (id) => req(`/items/${id}/promote`, { method: 'PATCH' }),
  toNote: (id) => req(`/items/${id}/to-note`, { method: 'POST' }),
  resurface: (limit = 5) => req(`/feed/resurface?limit=${limit}`),
  deleteNote: (id) => req(`/feed/notes/${id}/soft-delete`, { method: 'PATCH' }),
  restoreNote: (id) => req(`/feed/notes/${id}/restore`, { method: 'POST' }),
  purgeNote: (id) => req(`/feed/notes/${id}/purge`, { method: 'DELETE' }),
  search: (q, scope = 'all') => req(`/search?q=${encodeURIComponent(q)}&scope=${encodeURIComponent(scope)}`),

  // 「问问 AI」:按需生成看法
  insight: (id, refresh = false) =>
    req(`/items/${id}/insight${refresh ? '?refresh=true' : ''}`, { method: 'POST' }),

  // 清库仪式:AI 判为无信息量的
  cleanupSuggestions: () => req('/items/cleanup'),

  // 文字入口:速记 / 日志 / 计划 / 剪藏(core.entries)
  createEntry: (payload) =>
    req('/entries', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  listEntries: (params = {}) => {
    const s = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => { if (v) s.set(k, v) })
    return req(`/entries?${s.toString()}`)
  },
  ideas: () => req('/entries/ideas'),
  plans: () => req('/entries/plans'),
  logs: () => req('/entries/logs'),
  timeline: (date) => req(`/entries/timeline${date ? `?date=${encodeURIComponent(date)}` : ''}`),
  onThisDay: () => req('/entries/logs/on-this-day'),
  updateEntry: (id, patch) =>
    req(`/entries/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
    }),
  fileEntry: (id, target) =>
    req(`/entries/${id}/file`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target }),
    }),
  deleteEntry: (id) => req(`/entries/${id}`, { method: 'DELETE' }),
  restoreEntry: (id) => req(`/entries/${id}/restore`, { method: 'POST' }),
  purgeEntry: (id) => req(`/entries/${id}/purge`, { method: 'DELETE' }),
  promoteIdea: (id) => req(`/entries/${id}/promote`, { method: 'POST' }),
  reclassify: (id) => req(`/entries/${id}/reclassify`, { method: 'POST' }),
  trash: () => req('/trash'),

  // 设置:OCR / 问问AI 模型切换
  getSettings: () => req('/settings'),
  classificationSchema: () => req('/settings/classification-schema'),
  putSettings: (patch) =>
    req('/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
    }),
  reclassifyAll: (payload) =>
    req('/admin/reclassify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  candidates: () => req('/candidates'),
  approveCandidate: (id) => req(`/candidates/${id}/approve`, { method: 'POST' }),
  mergeCandidate: (id, target_name) =>
    req(`/candidates/${id}/merge`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target_name }),
    }),
  ignoreCandidate: (id) => req(`/candidates/${id}/ignore`, { method: 'POST' }),
}
