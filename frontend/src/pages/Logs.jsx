import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'

// 日志:带日期的文字,按天翻。价值在回看——往年今天温柔冒出。绝不 streak、不催写。
const MOODS = ['😞', '😕', '😐', '🙂', '😄']

function fmt(d) {
  if (!d) return ''
  const dt = new Date(d)
  return `${dt.getFullYear()}.${String(dt.getMonth() + 1).padStart(2, '0')}.${String(dt.getDate()).padStart(2, '0')}`
}
function ftime(ts) {
  if (!ts) return ''
  const dt = new Date(ts)
  return `${String(dt.getHours()).padStart(2, '0')}:${String(dt.getMinutes()).padStart(2, '0')}`
}

export default function Logs() {
  const nav = useNavigate()
  const [logs, setLogs] = useState([])
  const [past, setPast] = useState([])
  const [body, setBody] = useState('')
  const [mood, setMood] = useState('')
  const [loading, setLoading] = useState(true)

  function load() {
    setLoading(true)
    api.logs().then(setLogs).catch(() => setLogs([])).finally(() => setLoading(false))
    api.onThisDay().then(setPast).catch(() => setPast([]))
  }
  useEffect(load, [])

  async function quickLog() {
    if (!body.trim()) return
    const payload = { kind: 'log', body: body.trim() }
    if (mood) payload.mood = mood
    await api.createEntry(payload)
    setBody(''); setMood('')
    load()
  }
  async function del(e) {
    await api.deleteEntry(e.id)
    setLogs((xs) => xs.filter((x) => x.id !== e.id))
  }

  return (
    <div className="page">
      <div className="browse-head">
        <button className="back" onClick={() => nav('/')}>‹ 首页</button>
      </div>
      <h1 className="page-title">日志</h1>

      {/* 快速记一条 */}
      <div className="log-compose">
        <textarea
          className="capture-input"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="今天怎么样?"
          rows={3}
        />
        <div className="mood-row">
          {MOODS.map((m) => (
            <button key={m} className={`mood ${mood === m ? 'mood-on' : ''}`} onClick={() => setMood(mood === m ? '' : m)}>{m}</button>
          ))}
          <button className="log-save" onClick={quickLog} disabled={!body.trim()}>记下</button>
        </div>
      </div>

      {/* 往年今天:偶遇,不催办 */}
      {past.length > 0 && (
        <section className="onthisday">
          <h2 className="section-h">往年今天</h2>
          {past.map((e) => (
            <div key={e.id} className="log-item log-past">
              <div className="log-date">{fmt(e.logged_for)} {ftime(e.created_at)} {e.mood || ''}</div>
              <div className="entry-body">{e.body}</div>
            </div>
          ))}
        </section>
      )}

      <h2 className="section-h">时间线</h2>
      {loading ? (
        <div className="empty-hint">加载中…</div>
      ) : logs.length === 0 ? (
        <div className="empty-hint">还没有日志 · 想写就写,不写也没关系</div>
      ) : (
        <div className="log-list">
          {logs.map((e) => (
            <div key={e.id} className="log-item">
              <div className="log-date">{fmt(e.logged_for)} {ftime(e.created_at)} {e.mood || ''}
                <button className="log-del" onClick={() => del(e)}>删</button>
              </div>
              <div className="entry-body">{e.body}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
