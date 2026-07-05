import { useState } from 'react'
import { api } from '../api'
import { ENTRY_TYPES, DOMAINS, USE_TAGS } from '../classification'

function splitTopics(value) {
  return Array.from(new Set(value.split(/[,，\n]/).map((s) => s.trim()).filter(Boolean)))
}

export default function EntryEditor({ entry, showDate = false, showMood = false, onCancel, onSaved }) {
  const [draft, setDraft] = useState({
    body: entry.body || '',
    logged_for: entry.logged_for || '',
    mood: entry.mood || '',
    entry_type: entry.entry_type || '',
    domain: entry.domain || '',
    use_tag: entry.use_tag || '',
    topics: (entry.topics || []).join('，'),
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  function set(field, value) { setDraft((d) => ({ ...d, [field]: value })) }

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
        use_tag: draft.use_tag || null,
        topics: splitTopics(draft.topics),
      })
      onSaved(updated)
    } catch {
      setError('保存失败，请重试')
    } finally { setSaving(false) }
  }

  async function reclassify() {
    if (!draft.body.trim()) return
    setSaving(true); setError('')
    try {
      const updated = await api.updateEntry(entry.id, basePayload())
      await api.reclassify(entry.id)
      onSaved({
        ...updated, entry_type: null, domain: null, use_tag: null, topics: null,
        ai_classify_status: 'pending', ai_classified_at: null, ai_classify_output: null,
      })
    } catch {
      setError('重新分类失败，请重试')
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
        <label>领域<select value={draft.domain} onChange={(e) => set('domain', e.target.value)}>
          <option value="">未分类</option>{DOMAINS.map((v) => <option key={v}>{v}</option>)}
        </select></label>
        <label>用途<select value={draft.use_tag} onChange={(e) => set('use_tag', e.target.value)}>
          <option value="">未分类</option>{USE_TAGS.map((v) => <option key={v}>{v}</option>)}
        </select></label>
      </div>
      <label>标签</label>
      <input value={draft.topics} onChange={(e) => set('topics', e.target.value)} placeholder="用逗号分隔，例如 ADHD，药物" />
      <div className="entry-editor-source">来源：{entry.source || (entry.source_item_id ? '截图' : '自己')}</div>
      {error && <div className="banner-error">{error}</div>}
      <div className="entry-editor-actions">
        <button className="mini entry-reclass" onClick={reclassify} disabled={saving}>让 AI 重新分类</button>
        <span />
        <button className="mini" onClick={onCancel} disabled={saving}>取消</button>
        <button className="mini entry-save" onClick={save} disabled={saving || !draft.body.trim()}>保存</button>
      </div>
    </div>
  )
}
