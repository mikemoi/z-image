import { useState } from 'react'
import { api } from '../api'
import { ENTRY_TYPES, DOMAINS, USE_TAGS } from '../classification'

// 分类展示 + 编辑:AI 自动填,你随时改(改了就不再被自动分类覆盖)。
export default function ClassificationMeta({ entry }) {
  const [e, setE] = useState(entry)
  const [topic, setTopic] = useState('')
  const source = e.source || (e.source_item_id ? '截图' : '自己')
  const topics = Array.isArray(e.topics) ? e.topics.filter(Boolean) : []
  const pending = e.ai_classify_status === 'pending' || e.ai_classify_status == null

  async function set(field, value) {
    const up = await api.updateEntry(e.id, { [field]: value || null })
    setE(up)
  }
  async function addTopic() {
    const t = topic.trim()
    if (!t || topics.includes(t)) return
    const up = await api.updateEntry(e.id, { topics: [...topics, t] })
    setE(up); setTopic('')
  }
  async function delTopic(t) {
    const up = await api.updateEntry(e.id, { topics: topics.filter((x) => x !== t) })
    setE(up)
  }
  async function reclassify() {
    await api.reclassify(e.id)
    setE({ ...e, ai_classify_status: 'pending' })
  }

  return (
    <div className="class-meta">
      {pending ? (
        <div className="class-source">AI 分类中…</div>
      ) : (
        <div className="class-selects">
          <select value={e.entry_type || ''} onChange={(ev) => set('entry_type', ev.target.value)}>
            <option value="">类型…</option>
            {ENTRY_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
          <select value={e.domain || ''} onChange={(ev) => set('domain', ev.target.value)}>
            <option value="">领域…</option>
            {DOMAINS.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
          <select value={e.use_tag || ''} onChange={(ev) => set('use_tag', ev.target.value)}>
            <option value="">用途…</option>
            {USE_TAGS.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
      )}
      <div className="class-topics">
        {topics.map((t) => (
          <span key={t} className="class-topic" onClick={() => delTopic(t)}>#{t} ×</span>
        ))}
        <input className="class-topic-in" value={topic} placeholder="+标签"
          onChange={(ev) => setTopic(ev.target.value)}
          onKeyDown={(ev) => ev.key === 'Enter' && addTopic()} />
      </div>
      <div className="class-source">
        来源：{source}
        {!pending && <button className="class-reclass" onClick={reclassify}>重新分类</button>}
      </div>
    </div>
  )
}
