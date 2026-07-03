import { useNavigate } from 'react-router-dom'
import Img from './Img'

const THEME_LABEL = {
  trading: '交易', ai: 'AI', adhd: 'ADHD',
  language: '语言', life: '生活', other: '其他',
}

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
          {item.theme && <span className="tag tag-theme">{THEME_LABEL[item.theme] || item.theme}</span>}
          {item.use_tag && <span className="tag tag-use">{item.use_tag}</span>}
          {item.status === 'review' && <span className="tag tag-review">待处理</span>}
        </div>
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
