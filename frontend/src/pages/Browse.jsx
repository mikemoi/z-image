import { useEffect, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { api } from '../api'
import ItemCard from '../components/ItemCard'

const USES = ['避坑', '心态', '方法', '工具', '灵感']
const THEMES = [
  { key: 'trading', label: '交易' },
  { key: 'ai', label: 'AI' },
  { key: 'adhd', label: 'ADHD' },
  { key: 'language', label: '语言' },
  { key: 'life', label: '生活' },
]

// 双维度可叠加筛选。q 为客户端标题/摘要过滤(全文检索留到第五步)。
export default function Browse() {
  const [sp, setSp] = useSearchParams()
  const nav = useNavigate()
  const theme = sp.get('theme') || ''
  const use = sp.get('use') || ''
  const granularity = sp.get('granularity') || ''
  const q = sp.get('q') || ''
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)

  function load() {
    setLoading(true)
    // 不强制 status=ok:全部/维度视图都能带出未分类的(靠"待处理"标签自然区分)
    api.listItems({ theme, use, granularity, limit: 200 })
      .then((r) => setItems(r.items))
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }
  useEffect(load, [theme, use, granularity])

  function toggle(kind, val) {
    const next = new URLSearchParams(sp)
    if (next.get(kind) === val) next.delete(kind)
    else next.set(kind, val)
    setSp(next)
  }

  async function del(item) {
    await api.softDelete(item.id)
    setItems((xs) => xs.filter((x) => x.id !== item.id))
  }

  const shown = q
    ? items.filter((it) =>
        `${it.title || ''} ${it.summary || ''}`.toLowerCase().includes(q.toLowerCase()))
    : items

  return (
    <div className="page browse-page">
      <div className="browse-head">
        <button className="back" onClick={() => nav('/')}>‹ 首页</button>
        {q && <span className="browse-q">搜索:{q}</span>}
      </div>

      <div className="chips">
        {USES.map((u) => (
          <button key={u} className={`chip ${use === u ? 'chip-on' : ''}`} onClick={() => toggle('use', u)}>{u}</button>
        ))}
      </div>
      <div className="chips">
        {THEMES.map((t) => (
          <button key={t.key} className={`chip ${theme === t.key ? 'chip-on' : ''}`} onClick={() => toggle('theme', t.key)}>{t.label}</button>
        ))}
      </div>

      {loading ? (
        <div className="empty-hint">加载中…</div>
      ) : shown.length === 0 ? (
        <div className="empty-hint">这个筛选下还没有内容</div>
      ) : (
        <div className="card-list">
          {shown.map((it) => (
            <ItemCard key={it.id} item={it} onDelete={del} />
          ))}
        </div>
      )}
    </div>
  )
}
