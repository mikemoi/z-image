import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api'
import { ENTRY_TYPES, DOMAINS, TOPICS_BY_DOMAIN, SOURCES } from '../classification'
import Img from '../components/Img'
import HighlightText from '../components/HighlightText'
import Icon from '../components/Icon'
import ClassificationMeta from '../components/ClassificationMeta'

const FILTER_LABEL = { entry_type: '类型', domain: '领域', main_topic: '主题', tag: '标签', source: '来源' }

function FacetGroup({ title, field, values, counts, onPick }) {
  if (!values.length) return null
  return <section className="review-facet-section">
    <h2 className="section-h">{title}</h2>
    <div className="review-facet-grid">{values.map((value) =>
      <button key={value} className="review-facet" disabled={!counts?.[value]} onClick={() => onPick(field, value)}>
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
  const [facets, setFacets] = useState({ total: 0, entry_types: {}, domains: {}, main_topics: {}, sources: {}, tags: {} })
  const [items, setItems] = useState([])
  const [index, setIndex] = useState(0)
  const [detail, setDetail] = useState(null)
  const [idea, setIdea] = useState('')
  const [insight, setInsight] = useState(null)
  const [asking, setAsking] = useState(false)
  const [aiError, setAiError] = useState('')
  const [classifying, setClassifying] = useState(false)
  const [selectedQuote, setSelectedQuote] = useState('')
  const reviewTextRef = useRef(null)
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
    setDetail(null); setInsight(null); setAsking(false); setAiError(''); setClassifying(false); setSelectedQuote('')
    api.getItem(current.id).then(setDetail).catch(() => setDetail(false))
  }, [items, index])
  useEffect(() => {
    if (!detail) return undefined
    document.addEventListener('selectionchange', readTextSelection)
    return () => document.removeEventListener('selectionchange', readTextSelection)
  }, [detail?.id])

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
  async function ask(refresh = false) {
    if (!detail) return
    setAsking(true); setAiError('')
    try { setInsight(await api.insight(detail.id, refresh)) }
    catch { setAiError('AI 调用失败，稍后再试') }
    finally { setAsking(false) }
  }
  async function reclassify() {
    if (!detail || classifying) return
    setClassifying(true)
    try {
      await api.reclassifyItem(detail.id)
      setDetail((d) => ({ ...d, entry_type: null, domain: null, main_topic: null,
        sub_topic: null, related_topics: null, tags: null, ai_classify_status: 'pending' }))
    } finally { setClassifying(false) }
  }
  function readTextSelection() {
    const selection = window.getSelection()
    const box = reviewTextRef.current
    if (!selection || !box || selection.rangeCount === 0) return
    if (!box.contains(selection.anchorNode) || !box.contains(selection.focusNode)) return
    const quote = selection.toString().trim()
    setSelectedQuote(quote.length >= 2 ? quote : '')
  }
  function rememberTextSelection() {
    readTextSelection()
    setTimeout(readTextSelection, 120)
  }
  async function saveHighlight() {
    if (!detail || !selectedQuote) return
    const current = Array.isArray(detail.highlights) ? detail.highlights : []
    if (current.includes(selectedQuote)) return
    const updated = await api.updateItem(detail.id, { highlights: [...current, selectedQuote].slice(0, 10) })
    setDetail(updated); setSelectedQuote('')
    window.getSelection()?.removeAllRanges()
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
      {Object.entries(TOPICS_BY_DOMAIN).map(([domain, topics]) => <FacetGroup key={domain}
        title={`${domain} · 主题`} field="main_topic" values={topics}
        counts={facets.main_topics} onPick={pickCategory} />)}
      <FacetGroup title="来源" field="source" values={SOURCES} counts={facets.sources} onPick={pickCategory} />
      <FacetGroup title="常用标签" field="tag"
        values={Object.entries(facets.tags || {}).sort((a, b) => b[1] - a[1]).slice(0, 12).map(([name]) => name)}
        counts={facets.tags} onPick={pickCategory} />
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
            <Img checksum={detail.checksum} className="review-image" thumb />
            {detail.title && <h2>{detail.title}</h2>}
            {detail.summary && <p className="review-summary">{detail.summary}</p>}
            {(detail.clean_text || detail.raw_text) && <>
              <div ref={reviewTextRef} className="review-selectable"
                onMouseUp={rememberTextSelection} onTouchEnd={rememberTextSelection}>
                <HighlightText text={detail.clean_text || detail.raw_text}
                  highlights={detail.highlights} className="review-text" />
              </div>
              <button className="review-highlight" onClick={saveHighlight}
                disabled={!selectedQuote || detail.highlights?.includes(selectedQuote)}>标重点</button>
            </>}
            <div className="review-ai">
              {!insight ? <button className="ai-ask" onClick={() => ask(false)} disabled={asking}>
                {asking ? '正在想…' : <><Icon name="spark" size={18} className="ai-ask-ico" />问问 AI</>}
              </button> : <div className="ai-card">
                <div className="ai-head"><span className="ai-badge">AI 补充</span>
                  <span className="ai-note">AI 的看法,可能有错,别当原文</span></div>
                <div className="ai-text">{insight.explanation}</div>
                <button className="ai-again" onClick={() => ask(true)} disabled={asking}>{asking ? '…' : '重新问'}</button>
              </div>}
              {aiError && <div className="banner-error">{aiError}</div>}
            </div>
            <ClassificationMeta entry={detail} actions={<button onClick={reclassify}
              disabled={classifying || detail.ai_classify_status === 'pending'}>
              {classifying || detail.ai_classify_status === 'pending' ? '分类中…' : '重新分类'}
            </button>} />
          </div>
          <textarea className="capture-input" rows={2} value={idea} onChange={(e) => setIdea(e.target.value)} placeholder="写想法" />
          <div className="review-actions">
            <button className="mini" onClick={() => setIndex((i) => Math.max(0, i - 1))} disabled={index === 0}>上一张</button>
            <button className="mini mini-danger" onClick={remove}>删除</button>
            {idea.trim() ? <button className="mini entry-save" onClick={saveIdea}>保存并下一张</button> :
              <button className="mini entry-save" onClick={next}>下一张</button>}
          </div>
        </>}
    </>}
  </div>
}
