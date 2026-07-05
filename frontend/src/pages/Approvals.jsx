import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'

export default function Approvals() {
  const nav = useNavigate()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)

  function load() {
    setLoading(true)
    api.candidates().then(setItems).catch(() => setItems([])).finally(() => setLoading(false))
  }
  useEffect(load, [])

  async function approve(id) { await api.approveCandidate(id); load() }
  async function ignore(id) { await api.ignoreCandidate(id); load() }
  async function merge(id) {
    const target = window.prompt('合并到哪个已有名称？')
    if (!target) return
    await api.mergeCandidate(id, target)
    load()
  }

  return <div className="page">
    <div className="browse-head"><button className="back" onClick={() => nav('/me')}>‹ 我的</button></div>
    <h1 className="page-title">待审批</h1>
    {loading ? <div className="empty-hint">加载中…</div> : items.length === 0 ? <div className="empty-hint">暂无候选项</div> :
      <div className="card-list">{items.map((c) =>
        <div key={c.id} className="card">
          <div className="card-body">
            <span className="entry-kind">{c.candidate_type === 'sub_topic' ? '候选子题' : '候选标签'}</span>
            <div className="card-title">{c.name}</div>
            {(c.domain || c.main_topic) && <div className="card-summary">{[c.domain, c.main_topic].filter(Boolean).join(' / ')}</div>}
            <div className="card-snippet">出现 {c.occurrence_count} 次 · 关联 {c.content_count} 条</div>
            <div className="entry-acts">
              <button className="mini entry-save" onClick={() => approve(c.id)}>批准</button>
              <button className="mini" onClick={() => merge(c.id)}>合并</button>
              <button className="mini mini-danger" onClick={() => ignore(c.id)}>忽略</button>
            </div>
          </div>
        </div>)}</div>}
  </div>
}
