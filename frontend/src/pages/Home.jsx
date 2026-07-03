import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import Img from '../components/Img'

const USES = ['避坑', '心态', '方法', '工具', '灵感']
const THEMES = [
  { key: 'trading', label: '交易' },
  { key: 'ai', label: 'AI' },
  { key: 'adhd', label: 'ADHD' },
  { key: 'language', label: '语言' },
  { key: 'life', label: '生活' },
]

export default function Home() {
  const nav = useNavigate()
  const [stats, setStats] = useState({ themes: {}, uses: {}, total: 0 })
  const [notes, setNotes] = useState([])
  const [recent, setRecent] = useState([])
  const [q, setQ] = useState('')
  const [working, setWorking] = useState(false)

  useEffect(() => {
    api.dimensions().then(setStats).catch(() => {})
    // 重新遇见:优先真碎片;还没有 notes 时用最近入库项占位
    api.resurface(6).then((ns) => {
      setNotes(ns)
      if (ns.length === 0) {
        api.listItems({ status: 'ok', limit: 6 }).then((r) => setRecent(r.items)).catch(() => {})
      }
    }).catch(() => {})
  }, [])

  // 处理进度:只看"在不在整理"这个状态,不显示"还剩几张"。整理中时刷新维度计数。
  useEffect(() => {
    let alive = true
    async function tick() {
      try {
        const s = await api.workerStatus()
        if (!alive) return
        setWorking(s.working)
        if (s.working) api.dimensions().then(setStats).catch(() => {})
      } catch { /* ignore */ }
    }
    tick()
    const t = setInterval(tick, 4000)
    return () => { alive = false; clearInterval(t) }
  }, [])

  async function delNote(id) {
    await api.deleteNote(id)
    setNotes((xs) => xs.filter((n) => n.id !== id))
  }

  function search(e) {
    e.preventDefault()
    if (q.trim()) nav(`/search?q=${encodeURIComponent(q.trim())}`)
  }

  return (
    <div className="page home-page">
      <form className="search-bar" onSubmit={search}>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="搜索"
          autoCapitalize="off"
        />
      </form>

      {/* 处理状态:只显示"在不在整理",不显示待办数字 */}
      {working && (
        <div className="worker-chip">
          <span className="worker-dot" /> AI 正在后台整理…
        </div>
      )}

      {/* 全部 / 资料 快捷入口 */}
      <div className="quick-row">
        <button className="quick-btn" onClick={() => nav('/browse')}>
          <span className="quick-name">全部</span>
          <span className="quick-count">{stats.total || 0}</span>
        </button>
        <button className="quick-btn" onClick={() => nav('/browse?granularity=asset')}>
          <span className="quick-name">资料</span>
          <span className="quick-count">{stats.assets || 0}</span>
        </button>
      </div>

      {/* 重新遇见:真碎片优先,无则占位最近入库 */}
      <section className="resurface">
        <h2 className="section-h">重新遇见</h2>
        {notes.length > 0 ? (
          <div className="resurface-row">
            {notes.map((n) => (
              <div key={n.id} className="resurface-card note-card">
                {n.checksum && <Img checksum={n.checksum} className="resurface-thumb" />}
                <div className="resurface-note-body">{n.body}</div>
                <button className="note-del" onClick={() => delNote(n.id)}>删除</button>
              </div>
            ))}
          </div>
        ) : recent.length === 0 ? (
          <div className="empty-hint">还没有内容,去上传几张试试</div>
        ) : (
          <div className="resurface-row">
            {recent.map((it) => (
              <div key={it.id} className="resurface-card" onClick={() => nav(`/item/${it.id}`)}>
                <Img checksum={it.checksum} className="resurface-thumb" />
                <div className="resurface-cap">{it.title || it.summary || '未命名'}</div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* 维度入口 */}
      <section>
        <h2 className="section-h">用途</h2>
        <div className="dim-grid">
          {USES.map((u) => (
            <button key={u} className="dim-btn dim-use" onClick={() => nav(`/browse?use=${encodeURIComponent(u)}`)}>
              <span className="dim-name">{u}</span>
              <span className="dim-count">{stats.uses[u] || 0}</span>
            </button>
          ))}
        </div>
      </section>

      <section>
        <h2 className="section-h">主题</h2>
        <div className="dim-grid">
          {THEMES.map((t) => (
            <button key={t.key} className="dim-btn dim-theme" onClick={() => nav(`/browse?theme=${t.key}`)}>
              <span className="dim-name">{t.label}</span>
              <span className="dim-count">{stats.themes[t.key] || 0}</span>
            </button>
          ))}
        </div>
      </section>
    </div>
  )
}
