import { useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api'
import HighlightControls from '../components/HighlightControls'

// 记一条:零摩擦捕捉。速记/日志/计划/剪藏共用,写完就走。
const KINDS = [
  { key: 'log', label: '日志', hint: '今天怎么样?写完就走' },
  { key: 'plan', label: '计划', hint: '五年/十年计划,钉在眼前' },
]
const MOODS = ['😞', '😕', '😐', '🙂', '😄']

export default function Capture() {
  const nav = useNavigate()
  const [sp] = useSearchParams()
  const [kind, setKind] = useState(sp.get('kind') || 'log')
  const [body, setBody] = useState('')
  const [highlights, setHighlights] = useState([])
  const bodyRef = useRef(null)
  const [mood, setMood] = useState('')
  const [msg, setMsg] = useState('')
  const [saving, setSaving] = useState(false)

  const cur = KINDS.find((k) => k.key === kind)

  async function save() {
    if (!body.trim()) return
    setSaving(true)
    try {
      const payload = { kind, body: body.trim(), highlights }
      if (kind === 'log' && mood) payload.mood = mood
      await api.createEntry(payload)
      setBody(''); setMood(''); setHighlights([])
      setMsg(kind === 'log' ? '记下了 ✓' : kind === 'plan' ? '已钉住 ✓' : '收好了 ✓')
      setTimeout(() => setMsg(''), 1800)
    } catch {
      setMsg('出错了')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="page capture-page">
      <h1 className="page-title">记一条</h1>

      <div className="chips">
        {KINDS.map((k) => (
          <button key={k.key} className={`chip ${kind === k.key ? 'chip-on' : ''}`} onClick={() => setKind(k.key)}>{k.label}</button>
        ))}
      </div>
      <div className="capture-hint">{cur.hint}</div>

      <textarea ref={bodyRef}
        className="capture-input"
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder={cur.hint}
        rows={7}
        autoFocus
      />
      <HighlightControls textareaRef={bodyRef} highlights={highlights} onChange={setHighlights} />

      {kind === 'log' && (
        <div className="mood-row">
          <span className="mood-label">心情(可选)</span>
          {MOODS.map((m) => (
            <button key={m} className={`mood ${mood === m ? 'mood-on' : ''}`} onClick={() => setMood(mood === m ? '' : m)}>{m}</button>
          ))}
        </div>
      )}

      {msg && <div className="detail-msg">{msg}</div>}

      <div className="detail-actions">
        <button className="act" onClick={() => nav(-1)}>返回</button>
        <button className="act act-primary" onClick={save} disabled={saving || !body.trim()}>
          {saving ? '…' : '记下'}
        </button>
      </div>

      <div className="capture-links">
        <button className="text-link" onClick={() => nav('/logs')}>日志时间线 →</button>
      </div>
    </div>
  )
}
