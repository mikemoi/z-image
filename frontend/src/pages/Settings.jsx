import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'

// AI 设置:用量 + 三个模型分开配(OCR / 问问AI / 自动分类)。
const FIELDS = [
  ['ocr_model', '自动处理 / OCR', '量大,建议省钱档'],
  ['insight_model', '问问 AI', '低频+缓存,建议质量档'],
  ['classify_model', '自动分类', '简单任务,省钱档即可'],
]

export default function Settings() {
  const nav = useNavigate()
  const [usage, setUsage] = useState(null)
  const [s, setS] = useState(null)
  const [vals, setVals] = useState({})
  const [msg, setMsg] = useState('')

  useEffect(() => {
    api.workerStatus().then(setUsage).catch(() => {})
    api.getSettings().then((r) => {
      setS(r); setVals({ ocr_model: r.ocr_model, insight_model: r.insight_model, classify_model: r.classify_model })
    }).catch(() => {})
  }, [])

  async function save() {
    const r = await api.putSettings(vals)
    setS(r); setVals({ ocr_model: r.ocr_model, insight_model: r.insight_model, classify_model: r.classify_model })
    setMsg('已保存,即时生效 ✓'); setTimeout(() => setMsg(''), 2000)
  }

  const cand = s?.candidates || {}

  return (
    <div className="page">
      <div className="browse-head"><button className="back" onClick={() => nav('/me')}>‹ 我的</button></div>
      <h1 className="page-title">AI 设置</h1>

      <h2 className="section-h">用量</h2>
      <div className="me-card">
        {usage ? (
          <>
            <div className="me-row"><span>今日 AI 调用</span>
              <span className="me-strong">{usage.used}{usage.unlimited ? ' 次' : ` / ${usage.limit}`}</span></div>
            <div className="me-row"><span>状态</span><span>{usage.working ? '正在后台整理…' : '空闲'}</span></div>
            {usage.unlimited && <div className="me-hint">不限次数(由你的 API 侧限流)</div>}
          </>
        ) : <div className="me-dim">加载中…</div>}
      </div>

      <h2 className="section-h">模型(三处分开配)</h2>
      <div className="me-card">
        {FIELDS.map(([key, label, hint]) => (
          <div key={key}>
            <label className="me-label">{label}<span className="me-dim">（{hint}）</span></label>
            <input className="me-input" list={`c-${key}`} value={vals[key] || ''}
              onChange={(e) => setVals({ ...vals, [key]: e.target.value })} autoCapitalize="off" spellCheck="false" />
            <datalist id={`c-${key}`}>{(cand[key] || []).map((m) => <option key={m} value={m} />)}</datalist>
          </div>
        ))}
        <div className="me-hint">填任意 OpenRouter 模型 id。改完即时生效,不用重启。</div>
        <button className="me-save" onClick={save}>保存</button>
        {msg && <div className="detail-msg">{msg}</div>}
      </div>
    </div>
  )
}
