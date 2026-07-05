import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import Img from '../components/Img'

export default function Trash() {
  const nav = useNavigate()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => { api.trash().then(setItems).finally(() => setLoading(false)) }, [])

  async function restore(x) {
    if (x.kind === 'item') await api.restoreItem(x.id)
    else if (x.kind === 'entry') await api.restoreEntry(x.id)
    else await api.restoreNote(x.id)
    setItems((xs) => xs.filter((v) => !(v.kind === x.kind && v.id === x.id)))
  }
  async function purge(x) {
    if (!window.confirm('永久删除后无法恢复。确定永久删除？')) return
    if (x.kind === 'item') await api.purgeItem(x.id)
    else if (x.kind === 'entry') await api.purgeEntry(x.id)
    else await api.purgeNote(x.id)
    setItems((xs) => xs.filter((v) => !(v.kind === x.kind && v.id === x.id)))
  }

  return <div className="page">
    <div className="browse-head"><button className="back" onClick={() => nav('/me')}>‹ 我的</button></div>
    <h1 className="page-title">回收站</h1>
    {loading ? <div className="empty-hint">加载中…</div> : items.length === 0 ?
      <div className="empty-hint">回收站是空的</div> :
      <div className="trash-list">{items.map((x) => <div className="trash-card" key={`${x.kind}-${x.id}`}>
        {x.checksum && <Img checksum={x.checksum} className="trash-thumb" />}
        <div className="trash-copy"><b>{x.title || ({entry: '文字', note: '碎片'}[x.kind]) || '截图'}</b>
          {x.body && <span>{x.body}</span>}</div>
        <div className="trash-buttons"><button onClick={() => restore(x)}>恢复</button>
          <button className="mini-danger" onClick={() => purge(x)}>永久删除</button></div>
      </div>)}</div>}
  </div>
}
