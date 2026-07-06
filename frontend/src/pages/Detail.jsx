import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api'
import Img from '../components/Img'
import Icon from '../components/Icon'
import HighlightText from '../components/HighlightText'
import HighlightControls from '../components/HighlightControls'
import ClassificationMeta from '../components/ClassificationMeta'
import { displayType, useClassificationSchema } from '../classification'

function asDraft(item) {
  return { ...item, entry_type: displayType(item.entry_type), tags_text: (item.tags || item.topics || []).join('，') }
}
function splitTags(value) {
  return Array.from(new Set((value || '').split(/[,，\n]/).map((v) => v.trim()).filter(Boolean))).slice(0, 5)
}
function fmtIdeaTime(ts) {
  if (!ts) return ''
  const dt = new Date(ts)
  return `${dt.getFullYear()}.${String(dt.getMonth() + 1).padStart(2, '0')}.${String(dt.getDate()).padStart(2, '0')}  ${String(dt.getHours()).padStart(2, '0')}:${String(dt.getMinutes()).padStart(2, '0')}`
}

export default function Detail() {
  const {
    ENTRY_TYPES, DOMAINS, TOPICS_BY_DOMAIN, SUB_TOPICS_BY_TOPIC, ALL_TOPICS,
  } = useClassificationSchema()
  const { id } = useParams()
  const nav = useNavigate()
  const [item, setItem] = useState(null)
  const [editing, setEditing] = useState(false)
  const [zoom, setZoom] = useState(false)
  const [draft, setDraft] = useState({})
  const [msg, setMsg] = useState('')
  const [insight, setInsight] = useState(null)
  const [asking, setAsking] = useState(false)
  const [idea, setIdea] = useState('')
  const [linkedIdeas, setLinkedIdeas] = useState([])
  const [marking, setMarking] = useState(false)
  const [markDraft, setMarkDraft] = useState([])
  const markTextRef = useRef(null)

  useEffect(() => {
    setInsight(null)
    api.getItem(id).then((it) => { setItem(it); setDraft(asDraft(it)) }).catch(() => setItem(false))
    api.listEntries({ kind: 'idea', source_item_id: id }).then(setLinkedIdeas).catch(() => setLinkedIdeas([]))
  }, [id])

  async function ask(refresh = false) {
    setAsking(true); setMsg('')
    try {
      const r = await api.insight(item.id, refresh)
      setInsight(r)
    } catch (e) {
      setMsg(e.status === 502 ? 'AI 调用失败,稍后再试' : '出错了')
    } finally {
      setAsking(false)
    }
  }
  if (item === false) return <div className="page"><div className="empty-hint">条目不存在</div></div>
  if (!item) return <div className="page"><div className="empty-hint">加载中…</div></div>

  async function saveTags() {
    const patch = {
      title: draft.title, entry_type: draft.entry_type || null, domain: draft.domain || null,
      main_topic: draft.main_topic || null,
      sub_topic: draft.sub_topic || null,
      related_topics: (draft.related_topics || []).filter((v) => v && v !== draft.main_topic).slice(0, 2),
      tags: splitTags(draft.tags_text),
    }
    const updated = await api.updateItem(item.id, patch)
    setItem(updated); setDraft(asDraft(updated)); setEditing(false)
  }
  async function del() {
    await api.deleteItem(item.id)
    nav(-1)
  }
  async function saveHighlights() {
    const updated = await api.updateItem(item.id, { highlights: markDraft })
    setItem(updated); setDraft(asDraft(updated)); setMarking(false)
  }
  async function reclassify() {
    await api.reclassifyItem(item.id)
    const pending = { ...item, entry_type: null, domain: null, main_topic: null,
      sub_topic: null, related_topics: null, tags: null, ai_classify_status: 'pending' }
    setItem(pending); setDraft(asDraft(pending)); setMsg('正在重新分类…')
  }
  async function saveIdea() {
    if (!idea.trim()) return
    const created = await api.createEntry({ kind: 'idea', body: idea.trim(), source_item_id: item.id })
    setLinkedIdeas((xs) => [created, ...xs])
    setIdea(''); setMsg('想法记下了 ✓'); setTimeout(() => setMsg(''), 1800)
  }

  return (
    <div className="page detail-page">
      <div className="detail-head">
        <button className="back" onClick={() => nav(-1)}>‹ 返回</button>
      </div>

      <div className="detail-img" onClick={() => setZoom(true)}>
        <Img checksum={item.checksum} alt={item.title || ''} className="detail-img-el" />
      </div>

      {item.title && <h1 className="detail-title">{item.title}</h1>}

      {/* AI 是理解入口，独立于后面的人工编辑。 */}
      <div className="ai-block ai-block-first">
        {!insight && (
          <button className="ai-ask" onClick={() => ask(false)} disabled={asking}>
            {asking ? '正在想…' : <><Icon name="spark" size={18} className="ai-ask-ico" />问问 AI</>}
          </button>
        )}
        {insight && (
          <div className="ai-card">
            <div className="ai-head">
              <span className="ai-badge">AI 补充</span>
              {insight.cached && <span className="ai-cached">已存</span>}
              <span className="ai-note">AI 的看法,可能有错,别当原文</span>
            </div>
            <div className="ai-text">{insight.explanation}</div>
            {insight.quality && (
              <div className={`ai-quality q-${insight.quality === '无信息量' ? 'low' : insight.quality === '反面样本' ? 'mid' : 'high'}`}>
                <b>{insight.quality}</b>
                {insight.quality_note && <span> · {insight.quality_note}</span>}
              </div>
            )}
            <button className="ai-again" onClick={() => ask(true)} disabled={asking}>
              {asking ? '…' : '重新问'}
            </button>
          </div>
        )}
      </div>

      {item.status === 'review' && <div className="detail-tags"><span className="tag tag-review">待处理</span></div>}
      <ClassificationMeta entry={item} />

      {item.summary && (
        <div className="detail-block">
          <div className="block-h">摘要</div>
          <div className="block-text">{item.summary}</div>
        </div>
      )}

      {(item.clean_text || item.raw_text) && (
        <div className="detail-block">
          <div className="block-h">正文</div>
          <HighlightText text={item.clean_text || item.raw_text} highlights={item.highlights} className="block-text pre" />
        </div>
      )}

      {marking && (
        <div className="edit-box highlight-editor">
          <label>选中原文后标为重点</label>
          <textarea ref={markTextRef} className="capture-input" rows={10}
            value={item.clean_text || item.raw_text || ''} readOnly />
          <HighlightControls textareaRef={markTextRef} highlights={markDraft} onChange={setMarkDraft} />
          <div className="entry-acts">
            <button className="mini" onClick={() => setMarking(false)}>取消</button>
            <button className="mini entry-save" onClick={saveHighlights}>保存</button>
          </div>
        </div>
      )}

      {editing && (
        <div className="edit-box">
          <label>标题</label>
          <input value={draft.title || ''} onChange={(e) => setDraft({ ...draft, title: e.target.value })} />
          <label>类型</label><select value={draft.entry_type || ''} onChange={(e) => setDraft({ ...draft, entry_type: e.target.value })}>
            <option value="">未分类</option>{ENTRY_TYPES.map((v) => <option key={v}>{v}</option>)}
          </select>
          <label>领域</label><select value={draft.domain || ''} onChange={(e) => {
            const domain = e.target.value
            const main_topic = (TOPICS_BY_DOMAIN[domain] || []).includes(draft.main_topic) ? draft.main_topic : ''
            setDraft({ ...draft, domain, main_topic, sub_topic: main_topic ? draft.sub_topic : '' })
          }}><option value="">未分类</option>{DOMAINS.map((v) => <option key={v}>{v}</option>)}</select>
          <label>主题</label><select value={draft.main_topic || ''} disabled={!draft.domain}
            onChange={(e) => {
              const main_topic = e.target.value
              setDraft({ ...draft, main_topic, sub_topic: (SUB_TOPICS_BY_TOPIC[main_topic] || []).includes(draft.sub_topic) ? draft.sub_topic : '' })
            }}>
            <option value="">未分类</option>{(TOPICS_BY_DOMAIN[draft.domain] || []).map((v) => <option key={v}>{v}</option>)}
          </select>
          <label>子题</label><select value={draft.sub_topic || ''} disabled={!draft.main_topic}
            onChange={(e) => setDraft({ ...draft, sub_topic: e.target.value })}>
            <option value="">未分类</option>{(SUB_TOPICS_BY_TOPIC[draft.main_topic] || []).map((v) => <option key={v}>{v}</option>)}
          </select>
          <label>关联</label>
          <div className="entry-editor-grid related-selects">{[0, 1].map((index) => <select key={index}
            value={draft.related_topics?.[index] || ''} onChange={(e) => {
              const next = [...(draft.related_topics || [])]
              if (e.target.value) next[index] = e.target.value
              else next.splice(index, 1)
              setDraft({ ...draft, related_topics: Array.from(new Set(next.filter(Boolean))).slice(0, 2) })
            }}><option value="">无</option>{ALL_TOPICS.filter((v) => v !== draft.main_topic).map((v) => <option key={v}>{v}</option>)}</select>)}</div>
          <label>标签</label><input value={draft.tags_text || ''}
            onChange={(e) => setDraft({ ...draft, tags_text: e.target.value })} placeholder="最多 5 个，用逗号分隔" />
          <button className="btn-primary" onClick={saveTags}>保存</button>
        </div>
      )}

      {/* 我的想法:看这张图产生的思考,存进想法流(挂上来源截图)。先看已有的,再写新的。 */}
      <div className="detail-block">
        <div className="block-h">我的想法{linkedIdeas.length > 0 ? `(${linkedIdeas.length})` : ''}</div>
        {linkedIdeas.length > 0 && (
          <div className="linked-ideas">
            {linkedIdeas.map((li) => (
              <div key={li.id} className="entry-card">
                <div className="entry-time">{fmtIdeaTime(li.created_at)}</div>
                <HighlightText text={li.body} highlights={li.highlights} className="entry-body" />
              </div>
            ))}
          </div>
        )}
        <textarea className="capture-input" rows={3} value={idea}
          onChange={(e) => setIdea(e.target.value)}
          placeholder="看到这张图,你想到了什么?" />
        <button className="me-save" style={{ marginTop: 8 }} onClick={saveIdea} disabled={!idea.trim()}>记下想法</button>
      </div>

      {msg && <div className="detail-msg">{msg}</div>}

      {/* 人工操作与 AI 重分类分开；精选入口已取消。 */}
      <div className="detail-actions">
        <button className="act" onClick={() => setEditing((v) => !v)}>{editing ? '取消' : '编辑'}</button>
        {(item.clean_text || item.raw_text) && <button className="act" onClick={() => {
          setMarkDraft(Array.isArray(item.highlights) ? item.highlights : []); setMarking((v) => !v)
        }}>{marking ? '取消重点' : '标重点'}</button>}
        <button className="act" onClick={reclassify} disabled={item.ai_classify_status === 'pending'}>
          {item.ai_classify_status === 'pending' ? '分类中…' : '重新分类'}
        </button>
        <button className="act act-danger" onClick={del}>删除</button>
      </div>

      {zoom && (
        <div className="zoom-overlay" onClick={() => setZoom(false)}>
          <Img checksum={item.checksum} className="zoom-img" />
        </div>
      )}
    </div>
  )
}
