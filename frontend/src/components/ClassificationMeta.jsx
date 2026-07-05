// 普通卡片只展示分类。所有修改集中到统一“编辑”入口，避免误删标签或误改分类。
export default function ClassificationMeta({ entry, actions }) {
  const source = entry.source || (entry.source_item_id ? '截图' : '自己')
  const tags = Array.isArray(entry.tags) ? entry.tags.filter(Boolean)
    : (Array.isArray(entry.topics) ? entry.topics.filter(Boolean) : [])
  const related = Array.isArray(entry.related_topics) ? entry.related_topics.filter(Boolean) : []
  const pending = entry.ai_classify_status === 'pending' || entry.ai_classify_status == null
  const failed = entry.ai_classify_status === 'failed'
  const values = [entry.entry_type, entry.domain, entry.main_topic, source].filter(Boolean)
  const summary = pending ? `AI 整理中… · ${source}` : failed
    ? `分类暂未完成 · ${source}`
    : (values.length ? values.join(' · ') : `未分类 · ${source}`)

  return (
    <div className="class-meta">
      {related.length > 0 && <div className="class-related">相关：{related.join(' / ')}</div>}
      {tags.length > 0 && (
        <div className="class-topics">{tags.map((t) => <span key={t}>#{t}</span>)}</div>
      )}
      <div className="class-meta-foot">
        <span className="class-summary">{summary}</span>
        {actions && <div className="class-actions">{actions}</div>}
      </div>
    </div>
  )
}
