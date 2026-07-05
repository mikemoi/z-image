import { useEffect, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { api } from '../api'
import ItemCard from '../components/ItemCard'

const USES = ['避坑', '心态', '方法', '工具', '灵感']
const THEME_LABEL = { trading: '交易', ai: 'AI', adhd: 'ADHD', language: '语言', life: '生活', other: '其他' }
const FIXED_THEMES = ['trading', 'ai', 'adhd', 'language', 'life']

// 双维度可叠加筛选。q 为客户端标题/摘要过滤(全文检索留到第五步)。
export default function Browse() {
  const [sp, setSp] = useSearchParams()
  const nav = useNavigate()
  const theme = sp.get('theme') || ''
  const use = sp.get('use') || ''
  const granularity = sp.get('granularity') || ''
  const q = sp.get('q') || ''
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [candidate, setCandidate] = useState(null)
  const [growMsg, setGrowMsg] = useState('')
  const [themeStats, setThemeStats] = useState({})

  useEffect(() => { api.dimensions().then((d) => setThemeStats(d.themes || {})).catch(() => {}) }, [growMsg])

  function load() {
    setLoading(true)
    // 不强制 status=ok:全部/维度视图都能带出未分类的(靠"待处理"标签自然区分)
    api.listItems({ theme, use, granularity, limit: 200 })
      .then((r) => setItems(r.items))
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }
  useEffect(load, [theme, use, granularity])

  // 生长的分类:偶遇不催办——攒够一簇才冒一次,忽略过的本地记住、不再冒
  useEffect(() => {
    api.themeCandidates(3).then((cands) => {
      const dismissed = JSON.parse(localStorage.getItem('zbrain_dismissed_themes') || '[]')
      const top = cands.find((c) => !dismissed.includes(c.name))
      setCandidate(top || null)
    }).catch(() => {})
  }, [])

  async function adoptCandidate() {
    const r = await api.adoptThemeCluster(candidate.name)
    setGrowMsg(`已建「${candidate.name}」· 归入 ${r.count} 条 ✓`)
    setCandidate(null)
    load()
  }
  function dismissCandidate() {
    const dismissed = JSON.parse(localStorage.getItem('zbrain_dismissed_themes') || '[]')
    localStorage.setItem('zbrain_dismissed_themes', JSON.stringify([...dismissed, candidate.name]))
    setCandidate(null)
  }

  function toggle(kind, val) {
    const next = new URLSearchParams(sp)
    if (next.get(kind) === val) next.delete(kind)
    else next.set(kind, val)
    setSp(next)
  }

  async function del(item) {
    await api.deleteItem(item.id)
    setItems((xs) => xs.filter((x) => x.id !== item.id))
  }

  const shown = q
    ? items.filter((it) =>
        `${it.title || ''} ${it.summary || ''}`.toLowerCase().includes(q.toLowerCase()))
    : items

  return (
    <div className="page browse-page">
      <div className="browse-head">
        <button className="back" onClick={() => nav('/')}>‹ 首页</button>
        {q && <span className="browse-q">搜索:{q}</span>}
      </div>

      {growMsg && <div className="detail-msg">{growMsg}</div>}
      {candidate && (
        <div className="grow-card">
          <div className="grow-text">
            发现一簇「<b>{candidate.name}</b>」· {candidate.count} 条
            <span className="grow-sub">现有分类装不下它,建个新的?</span>
          </div>
          <div className="grow-acts">
            <button className="grow-yes" onClick={adoptCandidate}>建</button>
            <button className="grow-no" onClick={dismissCandidate}>忽略</button>
          </div>
        </div>
      )}

      <div className="chips">
        {USES.map((u) => (
          <button key={u} className={`chip ${use === u ? 'chip-on' : ''}`} onClick={() => toggle('use', u)}>{u}</button>
        ))}
      </div>
      <div className="chips">
        {Array.from(new Set([...FIXED_THEMES, ...Object.keys(themeStats)]))
          .filter((k) => k !== 'other' && (FIXED_THEMES.includes(k) || (themeStats[k] || 0) > 0))
          .map((k) => (
            <button key={k} className={`chip ${theme === k ? 'chip-on' : ''}`} onClick={() => toggle('theme', k)}>{THEME_LABEL[k] || k}</button>
          ))}
      </div>

      {loading ? (
        <div className="empty-hint">加载中…</div>
      ) : shown.length === 0 ? (
        <div className="empty-hint">这个筛选下还没有内容</div>
      ) : (
        <div className="card-list">
          {shown.map((it) => (
            <ItemCard key={it.id} item={it} onDelete={del} />
          ))}
        </div>
      )}
    </div>
  )
}
