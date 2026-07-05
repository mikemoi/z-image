import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { TOPICS_BY_DOMAIN } from '../classification'

const ORDERS = {
  entry_types: ['想法', '句子', '规则', '决策', '知识', '资料', '记录'],
  domains: ['身心', '生活', '能力', '财务', '方向'],
  main_topics: Object.values(TOPICS_BY_DOMAIN).flat(),
  sources: ['自己', '截图', '文件'],
}

function StatSection({ title, values, order }) {
  const entries = (order || Object.keys(values || {}))
    .map((name) => [name, values?.[name] || 0])
    .filter(([, count]) => count > 0)
  const max = Math.max(1, ...entries.map(([, count]) => count))
  return (
    <section className="overview-section">
      <h2 className="section-h">{title}</h2>
      {entries.length === 0 ? <div className="overview-empty">还没有数据</div> : entries.map(([name, count]) => (
        <div className="overview-row" key={name}>
          <div className="overview-label"><span>{name}</span><b>{count}</b></div>
          <div className="overview-track"><span style={{ width: `${Math.max(4, count / max * 100)}%` }} /></div>
        </div>
      ))}
    </section>
  )
}

export default function Overview() {
  const nav = useNavigate()
  const [stats, setStats] = useState(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    api.overview().then(setStats).catch(() => setFailed(true))
  }, [])

  return (
    <div className="page overview-page">
      <div className="browse-head"><button className="back" onClick={() => nav('/me')}>‹ 我的</button></div>
      <h1 className="page-title">数据概览</h1>
      <div className="capture-hint">看看内容自然长成了什么样，不是任务清单。</div>

      {failed ? <div className="empty-hint">数据加载失败</div> : !stats ? <div className="empty-hint">加载中…</div> : (
        <>
          <div className="overview-total"><span>全部内容</span><strong>{stats.total}</strong></div>
          <StatSection title="内容" values={stats.contents} />
          <StatSection title="类型" values={stats.entry_types} order={ORDERS.entry_types} />
          <StatSection title="领域" values={stats.domains} order={ORDERS.domains} />
          <StatSection title="主轴" values={stats.main_topics} order={ORDERS.main_topics} />
          <StatSection title="来源" values={stats.sources} order={ORDERS.sources} />
          <StatSection title="分类状态" values={stats.classify_statuses} order={['已分类', '待分类', '分类失败']} />
        </>
      )}
    </div>
  )
}
