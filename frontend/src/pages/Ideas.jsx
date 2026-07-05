import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import Img from '../components/Img'
import ClassificationMeta from '../components/ClassificationMeta'
import EntryEditor from '../components/EntryEditor'

// 想法本身就是一等内容，不再要求二次“精选”。
function fmtTime(ts) {
  if (!ts) return ''
  const dt = new Date(ts)
  return `${dt.getFullYear()}.${String(dt.getMonth() + 1).padStart(2, '0')}.${String(dt.getDate()).padStart(2, '0')}  ${String(dt.getHours()).padStart(2, '0')}:${String(dt.getMinutes()).padStart(2, '0')}`
}

export default function Ideas() {
  const nav = useNavigate()
  const [ideas, setIdeas] = useState([])
  const [body, setBody] = useState('')
  const [loading, setLoading] = useState(true)
  const [editId, setEditId] = useState(null)

  function load() {
    setLoading(true)
    api.ideas().then(setIdeas).catch(() => setIdeas([])).finally(() => setLoading(false))
  }
  useEffect(load, [])

  async function add() {
    if (!body.trim()) return
    await api.createEntry({ kind: 'idea', body: body.trim() })
    setBody(''); load()
  }
  async function del(e) {
    await api.deleteEntry(e.id)
    setIdeas((xs) => xs.filter((x) => x.id !== e.id))
  }
  function saved(up) {
    setIdeas((xs) => xs.map((x) => (x.id === up.id ? up : x)))
    setEditId(null)
  }

  return (
    <div className="page">
      <h1 className="page-title">想法</h1>
      <div className="capture-hint">看到什么、想到什么,写下来。AI 自动归类,你随时改。</div>

      <div className="log-compose">
        <textarea className="capture-input" value={body} rows={3}
          onChange={(e) => setBody(e.target.value)} placeholder="此刻的想法…" />
        <div className="mood-row"><button className="log-save" onClick={add} disabled={!body.trim()}>记下</button></div>
      </div>

      {loading ? (
        <div className="empty-hint">加载中…</div>
      ) : ideas.length === 0 ? (
        <div className="empty-hint">还没有想法 · 翻到一张图有感觉时,在详情页写一条</div>
      ) : (
        <div className="card-list">
          {ideas.map((e) => (
            <div key={e.id} className="entry-card">
              {editId === e.id ? (
                <EntryEditor entry={e} onCancel={() => setEditId(null)} onSaved={saved} />
              ) : (
                <>
                  <div className="entry-time">{fmtTime(e.created_at)}</div>
                  <div className="entry-body">{e.body}</div>
                  {e.checksum && (
                    <button className="idea-src" onClick={() => nav(`/item/${e.source_item_id}`)}>
                      <Img checksum={e.checksum} className="idea-thumb" /><span>查看来源截图</span>
                    </button>
                  )}
                  <ClassificationMeta entry={e} actions={<>
                    <button onClick={() => setEditId(e.id)}>编辑</button>
                    <button className="mini-danger" onClick={() => del(e)}>删除</button>
                  </>} />
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
