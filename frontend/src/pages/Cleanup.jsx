import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import Img from '../components/Img'

// 清库仪式:AI 顺手判为『无信息量』的。你主动进来才看到,不推送、不计数。
// 红线:'鸡汤'≠该删,这里只出纯无信息量的;删不删仍是你点头。
export default function Cleanup() {
  const nav = useNavigate()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)

  function load() {
    setLoading(true)
    api.cleanupSuggestions().then(setItems).catch(() => setItems([])).finally(() => setLoading(false))
  }
  useEffect(load, [])

  async function del(it) {
    await api.softDelete(it.id)
    setItems((xs) => xs.filter((x) => x.id !== it.id))
  }
  async function keep(it) {
    // 留下:本地从本次清库列表移除(不再纠缠),不改数据
    setItems((xs) => xs.filter((x) => x.id !== it.id))
  }

  return (
    <div className="page">
      <div className="browse-head">
        <button className="back" onClick={() => nav('/')}>‹ 首页</button>
      </div>
      <h1 className="page-title">清库</h1>
      <div className="capture-hint">AI 觉得这些没什么信息量。扫一眼,该删删、想留留——你说了算。</div>

      {loading ? (
        <div className="empty-hint">加载中…</div>
      ) : items.length === 0 ? (
        <div className="empty-hint">没有可清的 · 库挺干净</div>
      ) : (
        <div className="card-list">
          {items.map((it) => (
            <div key={it.id} className="entry-card">
              <div className="clean-row">
                <Img checksum={it.checksum} className="clean-thumb" />
                <div className="clean-body">
                  {it.title && <div className="card-title">{it.title}</div>}
                  {it.summary && <div className="card-summary">{it.summary}</div>}
                  {it.quality_note && <div className="clean-note">AI:{it.quality_note}</div>}
                </div>
              </div>
              <div className="entry-acts">
                <button className="mini" onClick={() => nav(`/item/${it.id}`)}>看看</button>
                <button className="mini" onClick={() => keep(it)}>留下</button>
                <button className="mini mini-danger" onClick={() => del(it)}>删除</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
