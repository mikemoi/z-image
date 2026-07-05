import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import Img from '../components/Img'
import Icon from '../components/Icon'

const USES = ['避坑', '心态', '方法', '工具', '灵感']
// 固定六类的中文名;生长出来的新分类没映射就直接显示原名
const THEME_LABEL = { trading: '交易', ai: 'AI', adhd: 'ADHD', language: '语言', life: '生活', other: '其他' }
const FIXED_THEMES = ['trading', 'ai', 'adhd', 'language', 'life']

export default function Home() {
  const nav = useNavigate()
  const [stats, setStats] = useState({ themes: {}, uses: {}, total: 0 })
  const [today, setToday] = useState(null)
  const [q, setQ] = useState('')
  const [working, setWorking] = useState(false)

  useEffect(() => {
    api.dimensions().then(setStats).catch(() => {})
    api.recommendations(1).then((r) => setToday(r.items[0] || null)).catch(() => {})
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

      {/* 文字入口:想法 / 日志 */}
      <div className="entry-row">
        <button className="entry-nav" onClick={() => nav('/ideas')}>
          <Icon name="bulb" size={22} className="en-ico" /><span className="en-label">想法</span>
        </button>
        <button className="entry-nav" onClick={() => nav('/logs')}>
          <Icon name="book" size={22} className="en-ico" /><span className="en-label">日志</span>
        </button>
      </div>

      {/* 今日推荐:点进单卡阅读器后可前后翻页 */}
      <section className="resurface">
        <h2 className="section-h">今日推荐</h2>
        {!today ? <div className="empty-hint">还没有内容</div> :
          <button className="today-card" onClick={() => nav('/review?mode=today')}>
            <Img checksum={today.checksum} className="resurface-thumb" />
            <div><b>{today.title || '未命名'}</b>{today.summary && <span>{today.summary}</span>}</div>
          </button>}
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
          {Array.from(new Set([...FIXED_THEMES, ...Object.keys(stats.themes || {})]))
            .filter((k) => k !== 'other' && (FIXED_THEMES.includes(k) || (stats.themes?.[k] || 0) > 0))
            .map((k) => (
              <button key={k} className="dim-btn dim-theme" onClick={() => nav(`/browse?theme=${encodeURIComponent(k)}`)}>
                <span className="dim-name">{THEME_LABEL[k] || k}</span>
                <span className="dim-count">{stats.themes?.[k] || 0}</span>
              </button>
            ))}
        </div>
      </section>
    </div>
  )
}
