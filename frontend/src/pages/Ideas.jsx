import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import Img from '../components/Img'
import ClassificationMeta from '../components/ClassificationMeta'
import ClassificationGuide from '../components/ClassificationGuide'

// 想法流:看图产生的 + 凭空的。可编辑、打主题、精选入脑。你的"思维镜子"。
const THEMES = ['trading', 'ai', 'adhd', 'language', 'life', 'other']
const LABEL = { trading: '交易', ai: 'AI', adhd: 'ADHD', language: '语言', life: '生活', other: '其他' }

export default function Ideas() {
  const nav = useNavigate()
  const [ideas, setIdeas] = useState([])
  const [body, setBody] = useState('')
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')
  const [editId, setEditId] = useState(null)
  const [editBody, setEditBody] = useState('')

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
  function startEdit(e) { setEditId(e.id); setEditBody(e.body) }
  async function saveEdit(e) {
    const up = await api.updateEntry(e.id, { body: editBody.trim() })
    setIdeas((xs) => xs.map((x) => (x.id === e.id ? { ...x, body: up.body } : x)))
    setEditId(null)
  }
  async function setTheme(e, theme) {
    const t = e.theme === theme ? null : theme
    await api.updateEntry(e.id, { theme: t })
    setIdeas((xs) => xs.map((x) => (x.id === e.id ? { ...x, theme: t } : x)))
  }
  async function promote(e) {
    await api.promoteIdea(e.id)
    setIdeas((xs) => xs.map((x) => (x.id === e.id ? { ...x, promoted_at: new Date().toISOString() } : x)))
  }

  const shown = filter ? ideas.filter((e) => e.theme === filter) : ideas

  return (
    <div className="page">
      <h1 className="page-title">想法</h1>
      <div className="capture-hint">看到什么、想到什么,写下来。它们攒起来就是你怎么思考的镜子。</div>
      <ClassificationGuide />

      <div className="log-compose">
        <textarea className="capture-input" value={body} rows={3}
          onChange={(e) => setBody(e.target.value)} placeholder="此刻的想法…" />
        <div className="mood-row"><button className="log-save" onClick={add} disabled={!body.trim()}>记下</button></div>
      </div>

      {ideas.some((e) => e.theme) && (
        <div className="chips">
          <button className={`chip ${!filter ? 'chip-on' : ''}`} onClick={() => setFilter('')}>全部</button>
          {THEMES.filter((t) => ideas.some((e) => e.theme === t)).map((t) => (
            <button key={t} className={`chip ${filter === t ? 'chip-on' : ''}`} onClick={() => setFilter(t)}>{LABEL[t]}</button>
          ))}
        </div>
      )}

      {loading ? (
        <div className="empty-hint">加载中…</div>
      ) : shown.length === 0 ? (
        <div className="empty-hint">还没有想法 · 翻到一张图有感觉时,在详情页写一条</div>
      ) : (
        <div className="card-list">
          {shown.map((e) => (
            <div key={e.id} className="entry-card">
              {editId === e.id ? (
                <>
                  <textarea className="capture-input" rows={3} value={editBody}
                    onChange={(ev) => setEditBody(ev.target.value)} />
                  <div className="entry-acts">
                    <button className="mini" onClick={() => saveEdit(e)}>保存</button>
                    <button className="mini" onClick={() => setEditId(null)}>取消</button>
                  </div>
                </>
              ) : (
                <>
                  <div className="entry-body">{e.body}</div>
                  <ClassificationMeta entry={e} />
                  <div className="idea-themes">
                    {THEMES.map((t) => (
                      <button key={t} className={`chip chip-sm ${e.theme === t ? 'chip-on' : ''}`}
                        onClick={() => setTheme(e, t)}>{LABEL[t]}</button>
                    ))}
                  </div>
                  <div className="idea-foot">
                    {e.checksum && (
                      <div className="idea-src" onClick={() => nav(`/item/${e.source_item_id}`)}>
                        <Img checksum={e.checksum} className="idea-thumb" /><span>来自截图</span>
                      </div>
                    )}
                    <button className="mini" onClick={() => startEdit(e)}>编辑</button>
                    <button className="mini" onClick={() => promote(e)} disabled={!!e.promoted_at}>
                      {e.promoted_at ? '已精选' : '精选'}
                    </button>
                    <button className="mini mini-danger" onClick={() => del(e)}>删</button>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
