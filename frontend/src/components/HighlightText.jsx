export default function HighlightText({ text = '', highlights = [], className = '' }) {
  const ranges = []
  for (const quote of highlights || []) {
    if (!quote) continue
    const start = text.indexOf(quote)
    if (start >= 0) ranges.push({ start, end: start + quote.length, quote })
  }
  ranges.sort((a, b) => a.start - b.start)
  const parts = []
  let pos = 0
  for (const range of ranges) {
    if (range.start < pos) continue
    if (range.start > pos) parts.push(text.slice(pos, range.start))
    parts.push(<mark key={`${range.start}-${range.quote}`}>{text.slice(range.start, range.end)}</mark>)
    pos = range.end
  }
  if (pos < text.length) parts.push(text.slice(pos))
  return <div className={className}>{parts.length ? parts : text}</div>
}
