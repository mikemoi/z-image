import { useEffect, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { api } from '../api'
import Img from '../components/Img'

// 全文检索:覆盖全部上传条目(标题/摘要/正文),点击进详情。
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
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="搜索全部内容" autoFocus autoCapitalize="off" />
      </form>

      {loading ? (
        <div className="empty-hint">搜索中…</div>
      ) : done && hits.length === 0 ? (
        <div className="empty-hint">没有命中「{term}」</div>
      ) : (
        <div className="card-list">
          {hits.map((h) => {
            const isEntry = h.source === 'entry'
            const key = isEntry ? `e${h.entry_id}` : `i${h.item_id}`
            const go = () => nav(isEntry ? (h.kind === 'log' ? '/logs' : '/inbox') : `/item/${h.item_id}`)
            const kindLabel = { note: '速记', log: '日志', plan: '计划', clip: '剪藏' }[h.kind]
            return (
              <div key={key} className="card" onClick={go}>
                {h.checksum && <div className="card-thumb"><Img checksum={h.checksum} className="thumb" /></div>}
                <div className="card-body">
                  {isEntry && <span className="entry-kind">{kindLabel || '文字'}</span>}
                  {h.title && <div className="card-title">{h.title}</div>}
                  {h.summary && <div className="card-summary" style={{ WebkitLineClamp: 3 }}>{h.summary}</div>}
                  {h.snippet && <div className="card-snippet">{h.snippet}</div>}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
