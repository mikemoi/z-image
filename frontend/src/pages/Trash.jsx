import { useEffect, useState } from 'react'
import { api } from '../api'
import Img from '../components/Img'

// 回收站:软删项。恢复 / 彻底销毁(仅彻底销毁二次确认)。
export default function Trash() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)

  function load() {
    setLoading(true)
    api.listItems({ deleted: true, limit: 200 })
      .then((r) => setItems(r.items))
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }
  useEffect(load, [])

  async function restore(it) {
    await api.restore(it.id)
    setItems((xs) => xs.filter((x) => x.id !== it.id))
  }
  async function purge(it) {
    if (!confirm('彻底销毁?将永久删除原图和记录,不可恢复。')) return
    await api.purge(it.id)
    setItems((xs) => xs.filter((x) => x.id !== it.id))
  }

  return (
    <div className="page trash-page">
      <h1 className="page-title">回收站</h1>
      {loading ? (
        <div className="empty-hint">加载中…</div>
      ) : items.length === 0 ? (
        <div className="empty-hint">回收站是空的</div>
      ) : (
        <div className="card-list">
          {items.map((it) => (
            <div key={it.id} className="card trash-card">
              <div className="card-thumb"><Img checksum={it.checksum} className="thumb" /></div>
              <div className="card-body">
                {it.title && <div className="card-title">{it.title}</div>}
                {it.summary && <div className="card-summary">{it.summary}</div>}
              </div>
              <div className="trash-actions">
                <button className="act" onClick={() => restore(it)}>恢复</button>
                <button className="act act-danger" onClick={() => purge(it)}>彻底销毁</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
