import { useEffect, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { api } from '../api'
import ItemCard from '../components/ItemCard'
import { ENTRY_TYPES, DOMAINS, TOPICS_BY_DOMAIN, SOURCES } from '../classification'

const FILTER_LABEL = {
  entry_type: '类型',
  domain: '领域',
  main_topic: '主题',
  source: '来源',
}

function ChipGroup({ title, field, values, active, onPick }) {
  if (!values.length) return null
  return (
    <>
      <h2 className="section-h">{title}</h2>
      <div className="chips">
        {values.map((value) => (
          <button key={value} className={`chip ${active === value ? 'chip-on' : ''}`}
            onClick={() => onPick(field, value)}>
            {value}
          </button>
        ))}
      </div>
    </>
  )
}

// 统一分类浏览：只展示类型 / 领域 / 主题 / 来源。
export default function Browse() {
  const [sp, setSp] = useSearchParams()
  const nav = useNavigate()
  const entryType = sp.get('entry_type') || ''
  const domain = sp.get('domain') || ''
  const mainTopic = sp.get('main_topic') || ''
  const source = sp.get('source') || ''
  const q = sp.get('q') || ''
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)

  function load() {
    setLoading(true)
    api.listItems({
      entry_type: entryType,
      domain,
      main_topic: mainTopic,
      source,
      limit: 200,
    })
      .then((r) => setItems(r.items))
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }
  useEffect(load, [entryType, domain, mainTopic, source])

  function pick(field, value) {
    const next = new URLSearchParams(sp)
    if (next.get(field) === value) next.delete(field)
    else next.set(field, value)
    if (field === 'domain') next.delete('main_topic')
    setSp(next)
  }
  function clearAll() {
    const next = new URLSearchParams()
    if (q) next.set('q', q)
    setSp(next)
  }
  async function del(item) {
    if (!window.confirm('删除后会进入回收站。确定删除？')) return
    await api.deleteItem(item.id)
    setItems((xs) => xs.filter((x) => x.id !== item.id))
  }

  const activeFilters = [
    ['entry_type', entryType],
    ['domain', domain],
    ['main_topic', mainTopic],
    ['source', source],
  ].filter(([, value]) => value)
  const topicValues = domain ? TOPICS_BY_DOMAIN[domain] || [] : Object.values(TOPICS_BY_DOMAIN).flat()
  const shown = q
    ? items.filter((it) =>
        `${it.title || ''} ${it.summary || ''}`.toLowerCase().includes(q.toLowerCase()))
    : items

  return (
    <div className="page browse-page">
      <div className="browse-head">
        <button className="back" onClick={() => nav('/')}>‹ 首页</button>
        {q && <span className="browse-q">搜索:{q}</span>}
      </div>

      <h1 className="page-title">分类浏览</h1>
      <div className="capture-hint">这里统一按类型、领域、主题、来源看内容。</div>

      {activeFilters.length > 0 && (
        <button className="review-filter" onClick={clearAll}>
          {activeFilters.map(([field, value]) => `${FILTER_LABEL[field]}：${value}`).join(' · ')} ×
        </button>
      )}

      <ChipGroup title="类型" field="entry_type" values={ENTRY_TYPES} active={entryType} onPick={pick} />
      <ChipGroup title="领域" field="domain" values={DOMAINS} active={domain} onPick={pick} />
      <ChipGroup title={domain ? `${domain} · 主题` : '主题'} field="main_topic"
        values={topicValues} active={mainTopic} onPick={pick} />
      <ChipGroup title="来源" field="source" values={SOURCES} active={source} onPick={pick} />

      {loading ? (
        <div className="empty-hint">加载中…</div>
      ) : shown.length === 0 ? (
        <div className="empty-hint">这个筛选下还没有内容</div>
      ) : (
        <div className="card-list">
          {shown.map((it) => (
            <ItemCard key={it.id} item={it} onDelete={del} />
          ))}
        </div>
      )}
    </div>
  )
}
