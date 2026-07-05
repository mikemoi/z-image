import { useNavigate } from 'react-router-dom'
import Img from './Img'

// 列表卡片:大缩略图 + title + 标签 + summary + 删除。
export default function ItemCard({ item, onDelete, actionLabel = '删除' }) {
  const nav = useNavigate()
  const go = () => nav(`/item/${item.id}`)

  return (
    <div className="card">
      <div className="card-thumb" onClick={go}>
        <Img checksum={item.checksum} alt={item.title || ''} className="thumb" />
      </div>
      <div className="card-body" onClick={go}>
        {item.title && <div className="card-title">{item.title}</div>}
        <div className="card-tags">
          {item.entry_type && <span className="tag tag-gran">{item.entry_type}</span>}
          {item.domain && <span className="tag tag-theme">{item.domain}</span>}
          {item.main_topic && <span className="tag tag-use">{item.main_topic}</span>}
          {item.status === 'review' && <span className="tag tag-review">待处理</span>}
        </div>
        {item.related_topics?.length > 0 && <div className="class-related">相关：{item.related_topics.join(' / ')}</div>}
        {(item.tags || item.topics)?.length > 0 && <div className="class-topics">
          {(item.tags || item.topics).map((tag) => <span key={tag}>#{tag}</span>)}
        </div>}
        {item.summary && <div className="card-summary">{item.summary}</div>}
      </div>
      <button
        className="card-del"
        onClick={(e) => { e.stopPropagation(); onDelete?.(item) }}
      >
        {actionLabel}
      </button>
    </div>
  )
}
