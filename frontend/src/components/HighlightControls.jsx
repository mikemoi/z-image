export default function HighlightControls({ textareaRef, highlights, onChange }) {
  function addSelection() {
    const el = textareaRef.current
    if (!el) return
    const quote = el.value.slice(el.selectionStart, el.selectionEnd).trim()
    if (quote.length < 2 || highlights.includes(quote)) return
    onChange([...highlights, quote].slice(0, 10))
  }

  return (
    <div className="highlight-controls">
      <button type="button" className="mini" onClick={addSelection}>标为重点</button>
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
