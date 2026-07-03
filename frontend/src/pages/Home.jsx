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
  const [recent, setRecent] = useState([])
  const [q, setQ] = useState('')

  useEffect(() => {
    api.dimensions().then(setStats).catch(() => {})
    // 重新遇见:notes 未做前,先用最近入库项占位
    api.listItems({ status: 'ok', limit: 6 }).then((r) => setRecent(r.items)).catch(() => {})
  }, [])

  function search(e) {
    e.preventDefault()
    if (q.trim()) nav(`/browse?q=${encodeURIComponent(q.trim())}`)
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

      {/* 重新遇见(占位:最近入库) */}
      <section className="resurface">
        <h2 className="section-h">重新遇见</h2>
        {recent.length === 0 ? (
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
