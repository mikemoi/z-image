import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'

// 待整理:速记/剪藏还没归位的。消化节奏——无计数、无催促,想整理才整理。
const KIND_LABEL = { note: '速记', clip: '剪藏', log: '日志', plan: '计划' }

export default function Inbox() {
  const nav = useNavigate()
  const [entries, setEntries] = useState([])
  const [loading, setLoading] = useState(true)

  function load() {
    setLoading(true)
    api.inbox().then(setEntries).catch(() => setEntries([])).finally(() => setLoading(false))
  }
  useEffect(load, [])

  async function file(e, target) {
    await api.fileEntry(e.id, target)
    setEntries((xs) => xs.filter((x) => x.id !== e.id))
  }
  async function del(e) {
    await api.deleteEntry(e.id)
    setEntries((xs) => xs.filter((x) => x.id !== e.id))
  }

  return (
    <div className="page">
      <div className="browse-head">
        <button className="back" onClick={() => nav('/')}>‹ 首页</button>
        <button className="text-link" onClick={() => nav('/capture')}>+ 记一条</button>
      </div>
      <h1 className="page-title">待整理</h1>

      {loading ? (
        <div className="empty-hint">加载中…</div>
      ) : entries.length === 0 ? (
        <div className="empty-hint">这里空了 · 没有要整理的,挺好</div>
      ) : (
        <div className="card-list">
          {entries.map((e) => (
            <div key={e.id} className="entry-card">
              <div className="entry-top">
                <span className="entry-kind">{KIND_LABEL[e.kind] || e.kind}</span>
              </div>
              <div className="entry-body">{e.body}</div>
              <div className="entry-acts">
                <button className="mini" onClick={() => file(e, 'knowledge')}>入脑(知识)</button>
                <button className="mini" onClick={() => file(e, 'note')}>收进碎片</button>
                <button className="mini mini-danger" onClick={() => del(e)}>删除</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
