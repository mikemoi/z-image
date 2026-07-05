import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import ClassificationMeta from '../components/ClassificationMeta'
import EntryEditor from '../components/EntryEditor'

function today() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function ftime(ts) {
  const d = new Date(ts)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

export default function Timeline() {
  const nav = useNavigate()
  const [date, setDate] = useState(today())
  const [items, setItems] = useState([])
  const [editId, setEditId] = useState(null)

  function load(day = date) {
    api.timeline(day).then(setItems).catch(() => setItems([]))
  }
  useEffect(() => { load(date) }, [date])

  async function del(e) {
    await api.deleteEntry(e.id)
    setItems((xs) => xs.filter((x) => x.id !== e.id))
  }
  function saved(updated) {
    setItems((xs) => xs.map((x) => x.id === updated.id ? updated : x))
    setEditId(null)
  }

  return <div className="page">
    <div className="browse-head"><button className="back" onClick={() => nav('/me')}>‹ 我的</button></div>
    <h1 className="page-title">时间线</h1>
    <label>选择日期</label>
    <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
    <div className="log-list" style={{ marginTop: 16 }}>
      {items.length === 0 ? <div className="empty-hint">这天还没有记录</div> : items.map((e) =>
        <div key={e.id} className="log-item">
          {editId === e.id ? <EntryEditor entry={e} showDate showMood onCancel={() => setEditId(null)} onSaved={saved} /> : <>
            <div className="log-date">{ftime(e.created_at)} {e.mood || ''}</div>
            <div className="entry-body">{e.body}</div>
            <ClassificationMeta entry={e} actions={<>
              <button onClick={() => setEditId(e.id)}>编辑</button>
              <button className="mini-danger" onClick={() => del(e)}>删除</button>
            </>} />
          </>}
        </div>)}
    </div>
  </div>
}
