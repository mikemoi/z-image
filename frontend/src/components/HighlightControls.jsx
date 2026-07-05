import { useEffect, useState } from 'react'

export default function HighlightControls({ textareaRef, highlights, onChange }) {
  const [selection, setSelection] = useState('')

  useEffect(() => {
    const el = textareaRef.current
    if (!el) return undefined
    const remember = () => {
      const quote = el.value.slice(el.selectionStart, el.selectionEnd).trim()
      setSelection(quote.length >= 2 ? quote : '')
    }
    for (const event of ['select', 'keyup', 'mouseup', 'touchend']) el.addEventListener(event, remember)
    document.addEventListener('selectionchange', remember)
    return () => {
      for (const event of ['select', 'keyup', 'mouseup', 'touchend']) el.removeEventListener(event, remember)
      document.removeEventListener('selectionchange', remember)
    }
  }, [textareaRef])

  function addSelection() {
    const el = textareaRef.current
    const current = el ? el.value.slice(el.selectionStart, el.selectionEnd).trim() : ''
    const quote = selection || current
    if (quote.length < 2 || highlights.includes(quote)) return
    onChange([...highlights, quote].slice(0, 10))
    setSelection('')
  }

  return (
    <div className="highlight-controls">
      <button type="button" className="mini" disabled={!selection || highlights.includes(selection)}
        onClick={addSelection}>标为重点</button>
      {highlights.length > 0 && <div className="highlight-list">
        {highlights.map((quote) => (
          <div key={quote} className="highlight-row">
            <mark>{quote}</mark>
            <button type="button" onClick={() => onChange(highlights.filter((x) => x !== quote))}>取消重点</button>
          </div>
        ))}
      </div>}
    </div>
  )
}
