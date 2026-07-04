import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import Icon from '../components/Icon'

// 计划:长期北极星,常驻不沉底。最简清单(先用起来,层次以后再长)。
export default function Plans() {
  const nav = useNavigate()
  const [plans, setPlans] = useState([])
  const [loading, setLoading] = useState(true)

  function load() {
    setLoading(true)
    api.plans().then(setPlans).catch(() => setPlans([])).finally(() => setLoading(false))
  }
  useEffect(load, [])

  async function del(p) {
    await api.deleteEntry(p.id)
    setPlans((xs) => xs.filter((x) => x.id !== p.id))
  }

  return (
    <div className="page">
      <div className="browse-head">
        <button className="back" onClick={() => nav('/me')}>‹ 我的</button>
        <button className="text-link" onClick={() => nav('/capture?kind=plan')}>+ 记一条计划</button>
      </div>
      <h1 className="page-title">计划</h1>
      <div className="capture-hint">长期投资、人生阶段、想坚持的事——写在这儿,偶尔回看校准。</div>

      {loading ? (
        <div className="empty-hint">加载中…</div>
      ) : plans.length === 0 ? (
        <div className="empty-hint">还没有计划 · 去「记录 → 计划」写一条</div>
      ) : (
        <div className="plans">
          {plans.map((p) => (
            <div key={p.id} className="plan-card">
              <Icon name="flag" size={18} className="plan-pin" />
              <span className="plan-body">{p.body}</span>
              <button className="log-del" onClick={() => del(p)}>删</button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
