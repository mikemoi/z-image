import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api'
import Img from '../components/Img'

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
    await api.softDelete(item.id)
    nav(-1)
  }
  async function markReview() {
    await api.review(item.id)
    const fresh = await api.getItem(item.id)
    setItem(fresh); setDraft(fresh)
  }
  async function digest() {
    try {
      if (item.granularity === 'fragment') {
        await api.toNote(item.id)
        setMsg('已存入收集箱 ✓')
      } else {
        await api.promote(item.id)
        setMsg('已入脑 ✓')
      }
      const fresh = await api.getItem(item.id)
      setItem(fresh); setDraft(fresh)
    } catch (e) {
      setMsg(e.status === 409 ? '请先标记已看' : '操作失败')
    }
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
        {item.theme && <span className="tag tag-theme">{THEME_LABEL[item.theme] || item.theme}</span>}
        {item.use_tag && <span className="tag tag-use">{item.use_tag}</span>}
        {item.granularity && <span className="tag tag-gran">{item.granularity === 'knowledge' ? '知识' : item.granularity === 'asset' ? '资料' : '碎片'}</span>}
        {item.status === 'review' && <span className="tag tag-review">待处理</span>}
      </div>

      {item.summary && (
        <div className="detail-block">
          <div className="block-h">摘要</div>
          <div className="block-text">{item.summary}</div>
        </div>
      )}

      {item.clean_text && (
        <div className="detail-block">
          <div className="block-h">正文</div>
          <div className="block-text pre">{item.clean_text}</div>
        </div>
      )}

      {/* 问问 AI:按需触发,标明是 AI 补充,与上面的原文分开 */}
      <div className="ai-block">
        {!insight && (
          <button className="ai-ask" onClick={() => ask(false)} disabled={asking}>
            {asking ? '正在想…' : '💡 问问 AI'}
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

      {msg && <div className="detail-msg">{msg}</div>}

      {/* 消化状态(资料类不消化,仅存档) */}
      {isAsset ? (
        <div className="detail-state"><span className="st-off">资料 · 仅存档检索,不入脑</span></div>
      ) : (
        <div className="detail-state">
          <span className={reviewed ? 'st-on' : 'st-off'}>{reviewed ? '✓ 已看' : '○ 未看'}</span>
          <span className={digested ? 'st-on' : 'st-off'}>
            {digested ? (isFragment ? '✓ 已入收集箱' : '✓ 已入脑') : (isFragment ? '○ 未收集' : '○ 未入脑')}
          </span>
        </div>
      )}

      {/* 底部拇指热区操作 */}
      <div className="detail-actions">
        <button className="act" onClick={() => setEditing((v) => !v)}>{editing ? '取消' : '改标签'}</button>
        {!isAsset && !reviewed && <button className="act" onClick={markReview}>标记已看</button>}
        {!isAsset && (
          <button
            className="act act-primary"
            onClick={digest}
            disabled={digested || (!isFragment && !reviewed)}
          >
            {isFragment ? '存入收集箱' : '入脑'}
          </button>
        )}
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
