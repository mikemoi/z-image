import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api'
import { ENTRY_TYPES, DOMAINS, USE_TAGS } from '../classification'
import Img from '../components/Img'
import HighlightText from '../components/HighlightText'

const FILTER_LABEL = { entry_type: '类型', domain: '领域', use_tag: '用途' }

function FacetGroup({ title, field, values, counts, onPick }) {
  return <section className="review-facet-section">
    <h2 className="section-h">{title}</h2>
    <div className="review-facet-grid">{values.map((value) =>
      <button key={value} className="review-facet" onClick={() => onPick(field, value)}>
        <span>{value}</span><b>{counts?.[value] || 0}</b>
      </button>)}</div>
  </section>
}

export default function ReviewSession() {
  const nav = useNavigate()
  const [sp] = useSearchParams()
  const batch = sp.get('mode') === 'batch'
  const [view, setView] = useState('continuous')
  const [filter, setFilter] = useState({})
  const [facets, setFacets] = useState({ total: 0, entry_types: {}, domains: {}, uses: {} })
  const [items, setItems] = useState([])
  const [index, setIndex] = useState(0)
  const [detail, setDetail] = useState(null)
  const [idea, setIdea] = useState('')
  const [loading, setLoading] = useState(true)

  function load(nextFilter = filter) {
    setFilter(nextFilter); setLoading(true); setItems([]); setIndex(0); setDetail(null)
    const req = batch ? api.reviewQueue(10, nextFilter) : api.recommendations(10)
    req.then((r) => setItems(r.items)).finally(() => setLoading(false))
  }
  useEffect(() => {
    load({})
    if (batch) api.reviewFacets().then(setFacets).catch(() => {})
  }, [batch])
  useEffect(() => {
    const current = items[index]
    if (!current) { setDetail(null); return }
    setDetail(null); api.getItem(current.id).then(setDetail).catch(() => setDetail(false))
  }, [items, index])

  function pickCategory(field, value) {
    setView('continuous'); load({ [field]: value })
  }
  async function next() {
    if (detail) await api.review(detail.id).catch(() => {})
    setIdea(''); setIndex((i) => i + 1)
  }
  async function saveIdea() {
    if (!idea.trim() || !detail) return
    await api.createEntry({ kind: 'idea', body: idea.trim(), source_item_id: detail.id })
    await next()
  }
  async function remove() {
    if (!detail) return
    await api.deleteItem(detail.id)
    setItems((xs) => xs.filter((x) => x.id !== detail.id))
    setIndex((i) => Math.min(i, Math.max(0, items.length - 2)))
  }

  const filterKey = Object.keys(filter)[0]
  const finished = !loading && items.length > 0 && index >= items.length
  return <div className="page review-page">
    <div className="review-head"><button className="back" onClick={() => nav(batch ? '/me' : '/')}>‹ 返回</button>
      {batch && view === 'continuous' && items.length > 0 && !finished && <span>{index + 1} / {items.length}</span>}</div>
    <h1 className="page-title">{batch ? '集中批阅' : '今日推荐'}</h1>

    {batch && <div className="review-mode">
      <button className={view === 'continuous' ? 'active' : ''} onClick={() => setView('continuous')}>连续批阅</button>
      <button className={view === 'category' ? 'active' : ''} onClick={() => setView('category')}>按分类批阅</button>
    </div>}

    {batch && view === 'category' ? <div className="review-facets">
      <button className="review-facet review-facet-all" onClick={() => { setView('continuous'); load({}) }}>
        <span>全部</span><b>{facets.total || 0}</b>
      </button>
      <FacetGroup title="类型" field="entry_type" values={ENTRY_TYPES} counts={facets.entry_types} onPick={pickCategory} />
      <FacetGroup title="领域" field="domain" values={DOMAINS} counts={facets.domains} onPick={pickCategory} />
      <FacetGroup title="用途" field="use_tag" values={USE_TAGS} counts={facets.uses} onPick={pickCategory} />
    </div> : <>
      {batch && filterKey && <button className="review-filter" onClick={() => load({})}>
        {FILTER_LABEL[filterKey]}：{filter[filterKey]} ×
      </button>}
      {loading ? <div className="empty-hint">加载中…</div> : items.length === 0 ?
        <div className="empty-hint">没有可看的内容</div> : finished ?
        <div className="review-finished"><button className="mini" onClick={() => nav(batch ? '/me' : '/')}>结束</button>
          <button className="mini entry-save" onClick={() => load(filter)}>再看 10 张</button></div> : !detail ?
        <div className="empty-hint">加载中…</div> : <>
          <div className="review-card">
            <Img checksum={detail.checksum} className="review-image" />
            {detail.title && <h2>{detail.title}</h2>}
            {detail.summary && <p className="review-summary">{detail.summary}</p>}
            {(detail.clean_text || detail.raw_text) && <HighlightText
              text={detail.clean_text || detail.raw_text} highlights={detail.highlights} className="review-text" />}
            {detail.topics?.length > 0 && <div className="class-topics">{detail.topics.map((t) => <span key={t}>#{t}</span>)}</div>}
            <div className="class-summary">{[detail.entry_type, detail.domain, detail.use_tag, '截图'].filter(Boolean).join(' · ')}</div>
          </div>
          <textarea className="capture-input" rows={2} value={idea} onChange={(e) => setIdea(e.target.value)} placeholder="写想法" />
          <div className="review-actions">
            <button className="mini" onClick={() => setIndex((i) => Math.max(0, i - 1))} disabled={index === 0}>上一张</button>
            <button className="mini" onClick={() => nav(`/item/${detail.id}`)}>编辑</button>
            <button className="mini mini-danger" onClick={remove}>删除</button>
            {idea.trim() ? <button className="mini entry-save" onClick={saveIdea}>保存并下一张</button> :
              <button className="mini entry-save" onClick={next}>下一张</button>}
          </div>
        </>}
    </>}
  </div>
}
