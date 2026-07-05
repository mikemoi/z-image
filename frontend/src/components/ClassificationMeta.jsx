export default function ClassificationMeta({ entry }) {
  const source = entry.source || (entry.source_item_id ? '截图' : '自己')
  const topics = Array.isArray(entry.topics) ? entry.topics.filter(Boolean) : []

  return (
    <div className="class-meta">
      <div className="class-chips">
        <span className="class-chip">类型 · {entry.entry_type || '未分类'}</span>
        <span className="class-chip">领域 · {entry.domain || '未分类'}</span>
        <span className="class-chip">用途 · {entry.use_tag || '未分类'}</span>
      </div>
      {topics.length > 0 && (
        <div className="class-topics">{topics.map((topic) => <span key={topic}>#{topic}</span>)}</div>
      )}
      <div className="class-source">来源：{source}</div>
    </div>
  )
}
