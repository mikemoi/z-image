import { useState } from 'react'
import { api } from '../api'
import { displaySource, displayType, useClassificationSchema } from '../classification'

function splitTopics(value) {
  return Array.from(new Set(value.split(/[,，\n]/).map((s) => s.trim()).filter(Boolean)))
}

export default function EntryEditor({ entry, showDate = false, showMood = false, onCancel, onSaved }) {
  const {
    ENTRY_TYPES, DOMAINS, TOPICS_BY_DOMAIN, SUB_TOPICS_BY_TOPIC, ALL_TOPICS,
  } = useClassificationSchema()
  const [draft, setDraft] = useState({
    body: entry.body || '',
    logged_for: entry.logged_for || '',
    mood: entry.mood || '',
    entry_type: displayType(entry.entry_type) || '',
    domain: entry.domain || '',
    main_topic: entry.main_topic || '',
    sub_topic: entry.sub_topic || '',
    related_topics: entry.related_topics || [],
    tags: (entry.tags || entry.topics || []).join('，'),
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  function set(field, value) { setDraft((d) => ({ ...d, [field]: value })) }
  function setRelated(index, value) {
    const next = [...draft.related_topics]
    if (value) next[index] = value
    else next.splice(index, 1)
    set('related_topics', Array.from(new Set(next.filter(Boolean))).slice(0, 2))
  }

  function basePayload() {
    const payload = { body: draft.body.trim() }
    if (showDate) payload.logged_for = draft.logged_for || null
    if (showMood) payload.mood = draft.mood.trim() || null
    return payload
  }

  async function save() {
    if (!draft.body.trim()) return
    setSaving(true); setError('')
    try {
      const updated = await api.updateEntry(entry.id, {
        ...basePayload(),
        entry_type: draft.entry_type || null,
        domain: draft.domain || null,
        main_topic: draft.main_topic || null,
        sub_topic: draft.sub_topic || null,
        related_topics: draft.related_topics.filter((v) => v !== draft.main_topic).slice(0, 2),
        tags: splitTopics(draft.tags).slice(0, 5),
        highlights: (entry.highlights || []).filter((quote) => draft.body.includes(quote)),
      })
      onSaved(updated)
    } catch {
      setError('保存失败，请重试')
    } finally { setSaving(false) }
  }

  return (
    <div className="entry-editor">
      <label>正文</label>
      <textarea className="capture-input" rows={4} value={draft.body} onChange={(e) => set('body', e.target.value)} />
      {showDate && <><label>日期</label><input type="date" value={draft.logged_for} onChange={(e) => set('logged_for', e.target.value)} /></>}
      {showMood && <><label>我填写的心情</label><input value={draft.mood} onChange={(e) => set('mood', e.target.value)} placeholder="可选" /></>}
      <div className="entry-editor-grid">
        <label>类型<select value={draft.entry_type} onChange={(e) => set('entry_type', e.target.value)}>
          <option value="">未分类</option>{ENTRY_TYPES.map((v) => <option key={v}>{v}</option>)}
        </select></label>
        <label>领域<select value={draft.domain} onChange={(e) => {
          const domain = e.target.value
          setDraft((d) => {
            const main_topic = (TOPICS_BY_DOMAIN[domain] || []).includes(d.main_topic) ? d.main_topic : ''
            return { ...d, domain, main_topic, sub_topic: main_topic ? d.sub_topic : '' }
          })
        }}>
          <option value="">未分类</option>{DOMAINS.map((v) => <option key={v}>{v}</option>)}
        </select></label>
        <label>主题<select value={draft.main_topic} onChange={(e) => {
          const main_topic = e.target.value
          setDraft((d) => ({ ...d, main_topic, sub_topic: (SUB_TOPICS_BY_TOPIC[main_topic] || []).includes(d.sub_topic) ? d.sub_topic : '' }))
        }} disabled={!draft.domain}>
          <option value="">未分类</option>{(TOPICS_BY_DOMAIN[draft.domain] || []).map((v) => <option key={v}>{v}</option>)}
        </select></label>
        <label>子题<select value={draft.sub_topic} onChange={(e) => set('sub_topic', e.target.value)} disabled={!draft.main_topic}>
          <option value="">未分类</option>{(SUB_TOPICS_BY_TOPIC[draft.main_topic] || []).map((v) => <option key={v}>{v}</option>)}
        </select></label>
      </div>
      <label>关联（最多 2 个）</label>
      <div className="entry-editor-grid related-selects">
        {[0, 1].map((index) => <select key={index} value={draft.related_topics[index] || ''}
          onChange={(e) => setRelated(index, e.target.value)}>
          <option value="">无</option>
          {ALL_TOPICS.filter((v) => v !== draft.main_topic).map((v) => <option key={v}>{v}</option>)}
        </select>)}
      </div>
      <label>标签</label>
      <input value={draft.tags} onChange={(e) => set('tags', e.target.value)} placeholder="最多 5 个，例如 专注达，反跳，他人经验" />
      <div className="entry-editor-source">来源：{displaySource(entry.source, entry.source_item_id ? '图片' : '我')}</div>
      {error && <div className="banner-error">{error}</div>}
      <div className="entry-editor-actions">
        <span />
        <button className="mini" onClick={onCancel} disabled={saving}>取消</button>
        <button className="mini entry-save" onClick={save} disabled={saving || !draft.body.trim()}>保存</button>
      </div>
    </div>
  )
}
