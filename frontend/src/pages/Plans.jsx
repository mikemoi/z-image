import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import Icon from '../components/Icon'
import ClassificationMeta from '../components/ClassificationMeta'
import EntryEditor from '../components/EntryEditor'
import HighlightText from '../components/HighlightText'
import EntryHighlighter from '../components/EntryHighlighter'

// 计划:长期北极星,常驻不沉底。最简清单(先用起来,层次以后再长)。
export default function Plans() {
  const nav = useNavigate()
  const [plans, setPlans] = useState([])
  const [loading, setLoading] = useState(true)
  const [editId, setEditId] = useState(null)
  const [markId, setMarkId] = useState(null)

  function load() {
    setLoading(true)
    api.plans().then(setPlans).catch(() => setPlans([])).finally(() => setLoading(false))
  }
  useEffect(load, [])

  async function del(p) {
    await api.deleteEntry(p.id)
    setPlans((xs) => xs.filter((x) => x.id !== p.id))
  }
  function saved(up) {
    setPlans((xs) => xs.map((x) => (x.id === up.id ? up : x)))
    setEditId(null)
    setMarkId(null)
  }

  return (
    <div className="page">
      <div className="browse-head">
        <button className="back" onClick={() => nav('/me')}>‹ 我的</button>
        <button className="text-link" onClick={() => nav('/capture?kind=plan')}>+ 记一条长期计划</button>
      </div>
      <h1 className="page-title">长期计划</h1>
      <div className="capture-hint">长期投资、人生阶段、想坚持的事——写在这儿,偶尔回看校准。</div>

      {loading ? (
        <div className="empty-hint">加载中…</div>
      ) : plans.length === 0 ? (
        <div className="empty-hint">还没有长期计划 · 想清楚方向时再写</div>
      ) : (
        <div className="plans">
          {plans.map((p) => (
            <div key={p.id} className="plan-card">
              {editId === p.id ? <EntryEditor entry={p} onCancel={() => setEditId(null)} onSaved={saved} /> : markId === p.id ? <EntryHighlighter entry={p} onCancel={() => setMarkId(null)} onSaved={saved} /> : <>
                <Icon name="flag" size={18} className="plan-pin" />
                <div className="plan-content">
                  <HighlightText text={p.body} highlights={p.highlights} className="plan-body" />
                  <ClassificationMeta entry={p} actions={<>
                    <button onClick={() => { setMarkId(p.id); setEditId(null) }}>标重点</button>
                    <button onClick={() => { setEditId(p.id); setMarkId(null) }}>编辑</button>
                    <button className="mini-danger" onClick={() => del(p)}>删除</button>
                  </>} />
                </div>
              </>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
