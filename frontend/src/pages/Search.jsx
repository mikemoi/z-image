import { useEffect, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { api } from '../api'
import Img from '../components/Img'

// 全文检索 core.knowledge(精选脑)。
export default function Search() {
  const [sp, setSp] = useSearchParams()
  const nav = useNavigate()
  const [q, setQ] = useState(sp.get('q') || '')
  const [hits, setHits] = useState([])
  const [loading, setLoading] = useState(false)
  const [done, setDone] = useState(false)

  const term = sp.get('q') || ''
  useEffect(() => {
    if (!term) return
    setLoading(true); setDone(false)
    api.search(term)
      .then(setHits)
      .catch(() => setHits([]))
      .finally(() => { setLoading(false); setDone(true) })
  }, [term])

  function submit(e) {
    e.preventDefault()
    if (q.trim()) setSp({ q: q.trim() })
  }

  return (
    <div className="page search-page">
      <div className="browse-head">
        <button className="back" onClick={() => nav('/')}>‹ 首页</button>
      </div>
      <form className="search-bar" onSubmit={submit}>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="搜索精选脑" autoFocus autoCapitalize="off" />
      </form>

      {loading ? (
        <div className="empty-hint">搜索中…</div>
      ) : done && hits.length === 0 ? (
        <div className="empty-hint">没有命中「{term}」</div>
      ) : (
        <div className="card-list">
          {hits.map((h) => (
            <div key={h.id} className="card">
              {h.checksum && <div className="card-thumb"><Img checksum={h.checksum} className="thumb" /></div>}
              <div className="card-body">
                {h.title && <div className="card-title">{h.title}</div>}
                <div className="card-summary" style={{ WebkitLineClamp: 4 }}>{h.body}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
