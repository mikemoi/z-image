import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api'
import Img from '../components/Img'

const KIND_ROUTE = { idea: '/ideas', log: '/logs', plan: '/plans' }

function TrendChart({ points }) {
  if (!points || points.length === 0) return <div className="topic-term-trend-empty">还没有足够数据画趋势</div>
  const max = Math.max(1, ...points.map((p) => p.count))
  return (
    <div className="topic-term-trend">
      {points.map((p) => (
        <div key={p.period} className="topic-term-trend-bar"
          style={{ height: `${Math.max(4, p.count / max * 100)}%` }}
          title={`${p.period.slice(0, 10)}: ${p.count}`} />
      ))}
    </div>
  )
}

export default function TopicStats() {
  const { mainTopic } = useParams()
  const nav = useNavigate()
  const [stats, setStats] = useState(null)
  const [failed, setFailed] = useState(false)
  const [selected, setSelected] = useState(null) // { term, type }
  const [trend, setTrend] = useState(null)
  const [itemList, setItemList] = useState(null)

  useEffect(() => {
    setStats(null); setFailed(false); setSelected(null)
    api.topicTerms(mainTopic).then(setStats).catch(() => setFailed(true))
  }, [mainTopic])

  useEffect(() => {
    if (!selected) { setTrend(null); setItemList(null); return }
    setTrend(null); setItemList(null)
    api.topicTermTrend(mainTopic, selected.term, selected.type).then(setTrend).catch(() => setTrend([]))
    api.topicTermItems(mainTopic, selected.term, selected.type).then(setItemList).catch(() => setItemList({ total: 0, items: [] }))
  }, [mainTopic, selected])

  function goToHit(h) {
    if (h.source === 'item') nav(`/item/${h.id}`)
    else if (KIND_ROUTE[h.kind]) nav(KIND_ROUTE[h.kind])
  }

  return (
    <div className="page overview-page">
      <div className="browse-head"><button className="back" onClick={() => nav('/overview')}>‹ 数据概览</button></div>
      <h1 className="page-title">{mainTopic} · 词频</h1>
      <div className="capture-hint">子题和标签在这个主题下各出现了多少次，点一个词看趋势和原文。</div>

      {failed ? <div className="empty-hint">数据加载失败</div> : !stats ? <div className="empty-hint">加载中…</div> : (
        <>
          <div className="overview-total"><span>{mainTopic} 下的内容</span><strong>{stats.total}</strong></div>

          {stats.terms.length === 0 ? <div className="overview-empty">这个主题下还没有子题或标签</div> : stats.terms.map((t) => {
            const active = selected && selected.term === t.term && selected.type === t.type
            return (
              <div key={`${t.type}:${t.term}`}>
                <button className={`topic-term-row ${active ? 'active' : ''}`}
                  onClick={() => setSelected(active ? null : { term: t.term, type: t.type })}>
                  <span><span className="topic-term-name">{t.term}</span>
                    <span className="topic-term-type">{t.type === 'tag' ? '标签' : '子题'}</span></span>
                  <span className="topic-term-count">{t.count}</span>
                </button>
                {active && (
                  <div className="topic-term-detail">
                    {!trend ? <div className="empty-hint">加载趋势…</div> : <TrendChart points={trend} />}
                    {!itemList ? <div className="empty-hint">加载原文…</div> : itemList.items.length === 0 ? (
                      <div className="overview-empty">没有找到具体内容</div>
                    ) : (
                      <div className="card-list">
                        {itemList.items.map((h) => (
                          <div key={`${h.source}${h.id}`} className="card" onClick={() => goToHit(h)}>
                            {h.checksum && <div className="card-thumb"><Img checksum={h.checksum} className="thumb" thumb /></div>}
                            <div className="card-body">
                              {h.title && <div className="card-title">{h.title}</div>}
                              {h.summary && <div className="card-summary" style={{ WebkitLineClamp: 3 }}>{h.summary}</div>}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </>
      )}
    </div>
  )
}
