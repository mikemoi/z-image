import { useNavigate } from 'react-router-dom'
import Img from './Img'
import ClassificationMeta from './ClassificationMeta'

// 列表卡片:大缩略图 + title + 统一分类 + summary + 删除。
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
        {item.status === 'review' && <span className="tag tag-review">待处理</span>}
        <ClassificationMeta entry={item} />
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
