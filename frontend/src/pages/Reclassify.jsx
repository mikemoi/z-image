import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'

const SCOPES = [
  ['all', '全部内容'],
  ['mine', '我的内容'],
  ['external', '外部材料'],
  ['unclassified', '未分类内容'],
]

export default function Reclassify() {
  const nav = useNavigate()
  const [scope, setScope] = useState('all')
  const [mode, setMode] = useState('fill_missing')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  async function run() {
    if (mode === 'force' && !window.confirm('强制重算会清空现有分类后重新排队。确定继续？')) return
    setLoading(true); setResult(null)
    try {
      setResult(await api.reclassifyAll({ scope, mode }))
    } finally {
      setLoading(false)
    }
  }

  return <div className="page">
    <div className="browse-head"><button className="back" onClick={() => nav('/me')}>‹ 我的</button></div>
    <h1 className="page-title">重新整理</h1>
    <div className="capture-hint">只把内容排队，后台慢慢整理，不会同步调用大量 AI。</div>
    <h2 className="section-h">范围</h2>
    <div className="chips">{SCOPES.map(([key, label]) =>
      <button key={key} className={`chip ${scope === key ? 'chip-on' : ''}`} onClick={() => setScope(key)}>{label}</button>)}</div>
    <h2 className="section-h">模式</h2>
    <div className="chips">
      <button className={`chip ${mode === 'fill_missing' ? 'chip-on' : ''}`} onClick={() => setMode('fill_missing')}>补全缺失</button>
      <button className={`chip ${mode === 'force' ? 'chip-on' : ''}`} onClick={() => setMode('force')}>强制重算</button>
    </div>
    <button className="btn-primary" onClick={run} disabled={loading}>{loading ? '排队中…' : '开始重新整理'}</button>
    {result && <div className="detail-msg">已排队：文字 {result.queued_entries} 条，图片 {result.queued_items} 条</div>}
  </div>
}
