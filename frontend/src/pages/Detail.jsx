import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api'
import Img from '../components/Img'
import Icon from '../components/Icon'
import HighlightText from '../components/HighlightText'
import HighlightControls from '../components/HighlightControls'

const THEMES = ['trading', 'ai', 'adhd', 'language', 'life', 'other']
const THEME_LABEL = { trading: '交易', ai: 'AI', adhd: 'ADHD', language: '语言', life: '生活', other: '其他' }
const USES = ['方法', '避坑', '心态', '工具', '灵感']

export default function Detail() {
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
  const [marking, setMarking] = useState(false)
  const [markDraft, setMarkDraft] = useState([])
  const markTextRef = useRef(null)

  useEffect(() => {
    setInsight(null)
    api.getItem(id).then((it) => { setItem(it); setDraft(it) }).catch(() => setItem(false))
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
  async function adoptTheme(theme) {
    const updated = await api.adoptTheme(item.id, theme)
    setItem(updated); setDraft(updated)
    setInsight({ ...insight, suggested_theme: null, suggested_theme_reason: null })
    setMsg(`已归入「${theme}」✓`)
  }

  if (item === false) return <div className="page"><div className="empty-hint">条目不存在</div></div>
  if (!item) return <div className="page"><div className="empty-hint">加载中…</div></div>

  async function saveTags() {
    const patch = { title: draft.title, theme: draft.theme, use_tag: draft.use_tag }
    const updated = await api.updateItem(item.id, patch)
    setItem(updated); setDraft(updated); setEditing(false)
  }
  async function del() {
    await api.deleteItem(item.id)
    nav(-1)
  }
  async function saveHighlights() {
    const updated = await api.updateItem(item.id, { highlights: markDraft })
    setItem(updated); setDraft(updated); setMarking(false)
  }
  async function keep() {   // 留下:留档,标记已处理
    await api.review(item.id)
    const fresh = await api.getItem(item.id)
    setItem(fresh); setDraft(fresh)
    setMsg('已留下 ✓')
  }
  async function pick() {   // 精选:入脑
    try {
      if (item.granularity === 'fragment') await api.toNote(item.id)
      else await api.promote(item.id)
      const fresh = await api.getItem(item.id)
      setItem(fresh); setDraft(fresh)
      setMsg('已精选 ✓')
    } catch { setMsg('操作失败') }
  }
  async function saveIdea() {
    if (!idea.trim()) return
    await api.createEntry({ kind: 'idea', body: idea.trim(), source_item_id: item.id })
    setIdea(''); setMsg('想法记下了 ✓'); setTimeout(() => setMsg(''), 1800)
  }

  const reviewed = !!item.reviewed_at
  const digested = !!item.promoted_at
  const isFragment = item.granularity === 'fragment'
  const isAsset = item.granularity === 'asset'

  return (
    <div className="page detail-page">
      <div className="detail-head">
        <button className="back" onClick={() => nav(-1)}>‹ 返回</button>
      </div>

      <div className="detail-img" onClick={() => setZoom(true)}>
        <Img checksum={item.checksum} alt={item.title || ''} className="detail-img-el" />
      </div>

      {item.title && <h1 className="detail-title">{item.title}</h1>}

      <div className="detail-tags">
        {item.entry_type && <span className="tag tag-gran">{item.entry_type}</span>}
        {item.domain && <span className="tag tag-theme">{item.domain}</span>}
        {item.use_tag && <span className="tag tag-use">{item.use_tag}</span>}
        {item.ai_classify_status == null && item.status === 'ok' && <span className="tag tag-review">AI 分类中</span>}
        {item.status === 'review' && <span className="tag tag-review">待处理</span>}
      </div>
      {Array.isArray(item.topics) && item.topics.length > 0 && (
        <div className="class-topics" style={{ margin: '0 2px 8px' }}>
          {item.topics.map((t) => <span key={t}>#{t}</span>)}
        </div>
      )}

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

      {/* 问问 AI:按需触发,标明是 AI 补充,与上面的原文分开 */}
      <div className="ai-block">
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
            {insight.suggested_theme && (
              <div className="ai-suggest">
                <span>建议新分类:「{insight.suggested_theme}」</span>
                {insight.suggested_theme_reason && <em> {insight.suggested_theme_reason}</em>}
                <button className="ai-adopt" onClick={() => adoptTheme(insight.suggested_theme)}>采用</button>
              </div>
            )}
            <button className="ai-again" onClick={() => ask(true)} disabled={asking}>
              {asking ? '…' : '重新问'}
            </button>
          </div>
        )}
      </div>

      {editing && (
        <div className="edit-box">
          <label>标题</label>
          <input value={draft.title || ''} onChange={(e) => setDraft({ ...draft, title: e.target.value })} />
          <label>主题</label>
          <div className="chips">
            {THEMES.map((t) => (
              <button key={t} className={`chip ${draft.theme === t ? 'chip-on' : ''}`} onClick={() => setDraft({ ...draft, theme: t })}>{THEME_LABEL[t]}</button>
            ))}
          </div>
          <label>用途</label>
          <div className="chips">
            {USES.map((u) => (
              <button key={u} className={`chip ${draft.use_tag === u ? 'chip-on' : ''}`} onClick={() => setDraft({ ...draft, use_tag: u })}>{u}</button>
            ))}
          </div>
          <button className="btn-primary" onClick={saveTags}>保存</button>
        </div>
      )}

      {/* 我的想法:看这张图产生的思考,存进想法流(挂上来源截图) */}
      <div className="detail-block">
        <div className="block-h">我的想法</div>
        <textarea className="capture-input" rows={3} value={idea}
          onChange={(e) => setIdea(e.target.value)}
          placeholder="看到这张图,你想到了什么?" />
        <button className="me-save" style={{ marginTop: 8 }} onClick={saveIdea} disabled={!idea.trim()}>记下想法</button>
      </div>

      {msg && <div className="detail-msg">{msg}</div>}

      {/* 底部操作:标签 / 精选 / 删除(不删即留下) */}
      <div className="detail-actions">
        <button className="act" onClick={() => setEditing((v) => !v)}>{editing ? '取消' : '标签'}</button>
        {(item.clean_text || item.raw_text) && <button className="act" onClick={() => {
          setMarkDraft(Array.isArray(item.highlights) ? item.highlights : []); setMarking((v) => !v)
        }}>{marking ? '取消重点' : '标重点'}</button>}
        {!isAsset && <button className="act act-primary" onClick={pick} disabled={digested}>{digested ? '已精选' : '精选'}</button>}
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
