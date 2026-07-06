import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import Img from '../components/Img'

export default function Home() {
  const nav = useNavigate()
  const [today, setToday] = useState(null)
  const [q, setQ] = useState('')
  const [working, setWorking] = useState(false)

  useEffect(() => {
    api.recommendations(1).then((r) => setToday(r.items[0] || null)).catch(() => {})
  }, [])

  // 处理进度:只看"在不在整理"这个状态,不显示"还剩几张"。
  useEffect(() => {
    let alive = true
    async function tick() {
      if (document.visibilityState !== 'visible') return
      try {
        const s = await api.workerStatus()
        if (!alive) return
        setWorking(s.working)
      } catch { /* ignore */ }
    }
    function onVisibilityChange() {
      if (document.visibilityState === 'visible') tick()
    }
    tick()
    const t = setInterval(tick, 4000)
    document.addEventListener('visibilitychange', onVisibilityChange)
    return () => {
      alive = false
      clearInterval(t)
      document.removeEventListener('visibilitychange', onVisibilityChange)
    }
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

      {/* 今日推荐:点进单卡阅读器后可前后翻页 */}
      <section className="resurface">
        <h2 className="section-h">今日推荐</h2>
        {!today ? <div className="empty-hint">还没有内容</div> :
          <button className="today-card" onClick={() => nav('/review?mode=today')}>
            <Img checksum={today.checksum} className="resurface-thumb" thumb />
            <div><b>{today.title || '未命名'}</b>{today.summary && <span>{today.summary}</span>}</div>
          </button>}
      </section>

    </div>
  )
}
