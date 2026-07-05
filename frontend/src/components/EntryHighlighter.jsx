import { useRef, useState } from 'react'
import { api } from '../api'
import HighlightControls from './HighlightControls'

export default function EntryHighlighter({ entry, onCancel, onSaved }) {
  const textRef = useRef(null)
  const [highlights, setHighlights] = useState(Array.isArray(entry.highlights) ? entry.highlights : [])
  const [saving, setSaving] = useState(false)

  async function save() {
    setSaving(true)
    try { onSaved(await api.updateEntry(entry.id, { highlights })) }
    finally { setSaving(false) }
  }

  return <div className="entry-editor highlight-editor">
    <label>选中正文后标为重点</label>
    <textarea ref={textRef} className="capture-input" rows={5} value={entry.body} readOnly />
    <HighlightControls textareaRef={textRef} highlights={highlights} onChange={setHighlights} />
    <div className="entry-acts">
      <button className="mini" onClick={onCancel} disabled={saving}>取消</button>
      <button className="mini entry-save" onClick={save} disabled={saving}>保存</button>
    </div>
  </div>
}
