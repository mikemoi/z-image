import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useClassificationSchema } from '../classification'

function StatSection({ title, values, order, onSelect }) {
  const entries = (order || Object.keys(values || {}))
    .map((name) => [name, values?.[name] || 0])
    .filter(([, count]) => count > 0)
  const max = Math.max(1, ...entries.map(([, count]) => count))
  return (
    <section className="overview-section">
      <h2 className="section-h">{title}</h2>
      {entries.length === 0 ? <div className="overview-empty">还没有数据</div> : entries.map(([name, count]) => {
        const row = (
          <div className="overview-row" key={name}>
            <div className="overview-label"><span>{name}</span><b>{count}</b></div>
            <div className="overview-track"><span style={{ width: `${Math.max(4, count / max * 100)}%` }} /></div>
          </div>
        )
        return onSelect ? (
          <button key={name} className="overview-row-btn" onClick={() => onSelect(name)}>{row}</button>
        ) : row
      })}
    </section>
  )
}

export default function Overview() {
  const { ENTRY_TYPES, DOMAINS, SOURCES, TOPICS_BY_DOMAIN } = useClassificationSchema()
  const nav = useNavigate()
  const [stats, setStats] = useState(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    api.overview().then(setStats).catch(() => setFailed(true))
  }, [])
  const orders = {
    entry_types: ENTRY_TYPES,
    domains: DOMAINS,
    main_topics: Object.values(TOPICS_BY_DOMAIN).flat(),
    sources: SOURCES,
  }

  return (
    <div className="page overview-page">
      <div className="browse-head"><button className="back" onClick={() => nav('/me')}>‹ 我的</button></div>
      <h1 className="page-title">数据概览</h1>
      <div className="capture-hint">看看内容自然长成了什么样，不是任务清单。</div>

      {failed ? <div className="empty-hint">数据加载失败</div> : !stats ? <div className="empty-hint">加载中…</div> : (
        <>
          <div className="overview-total"><span>全部内容</span><strong>{stats.total}</strong></div>
          <StatSection title="内容" values={stats.contents} />
          <StatSection title="类型" values={stats.entry_types} order={orders.entry_types} />
          <StatSection title="领域" values={stats.domains} order={orders.domains} />
          <StatSection title="主题" values={stats.main_topics} order={orders.main_topics}
            onSelect={(name) => nav(`/overview/topic/${encodeURIComponent(name)}`)} />
          <StatSection title="子题" values={stats.sub_topics} />
          <StatSection title="来源" values={stats.sources} order={orders.sources} />
          <StatSection title="分类状态" values={stats.classify_statuses} order={['已分类', '待分类', '分类失败']} />
        </>
      )}
    </div>
  )
}
