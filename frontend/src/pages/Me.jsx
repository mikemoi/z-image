import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, clearToken } from '../api'
import Icon from '../components/Icon'

// 我的:AI 用量 + 模型切换(OCR / 问问AI 分开)+ 计划/回收站/清库 + 退出。
export default function Me() {
  const nav = useNavigate()
  const [usage, setUsage] = useState(null)
  const [settings, setSettings] = useState(null)
  const [ocr, setOcr] = useState('')
  const [insight, setInsight] = useState('')
  const [msg, setMsg] = useState('')

  useEffect(() => {
    api.workerStatus().then(setUsage).catch(() => {})
    api.getSettings().then((s) => {
      setSettings(s); setOcr(s.ocr_model); setInsight(s.insight_model)
    }).catch(() => {})
  }, [])

  async function saveModels() {
    const s = await api.putSettings({ ocr_model: ocr.trim(), insight_model: insight.trim() })
    setSettings(s); setOcr(s.ocr_model); setInsight(s.insight_model)
    setMsg('已保存,即时生效 ✓'); setTimeout(() => setMsg(''), 2000)
  }
  function logout() {
    clearToken(); window.location.assign('/')
  }

  const cand = settings?.candidates || { ocr_model: [], insight_model: [] }

  return (
    <div className="page">
      <h1 className="page-title">我的</h1>

      {/* AI 用量 */}
      <h2 className="section-h">AI 用量</h2>
      <div className="me-card">
        {usage ? (
          <>
            <div className="me-row">
              <span>今日 AI 调用</span>
              <span className="me-strong">{usage.used}{usage.unlimited ? ' 次' : ` / ${usage.limit}`}</span>
            </div>
            <div className="me-row">
              <span>状态</span>
              <span>{usage.working ? '正在后台整理…' : '空闲'}</span>
            </div>
            {usage.unlimited && <div className="me-hint">不限次数(由你的 API 侧限流)</div>}
          </>
        ) : <div className="me-dim">加载中…</div>}
      </div>

      {/* 模型切换 */}
      <h2 className="section-h">AI 模型(可分开配)</h2>
      <div className="me-card">
        <label className="me-label">自动处理 / OCR(量大,建议省钱档)</label>
        <input className="me-input" list="ocr-cand" value={ocr}
               onChange={(e) => setOcr(e.target.value)} autoCapitalize="off" spellCheck="false" />
        <datalist id="ocr-cand">{cand.ocr_model.map((m) => <option key={m} value={m} />)}</datalist>

        <label className="me-label">问问 AI(低频+缓存,建议质量档)</label>
        <input className="me-input" list="ins-cand" value={insight}
               onChange={(e) => setInsight(e.target.value)} autoCapitalize="off" spellCheck="false" />
        <datalist id="ins-cand">{cand.insight_model.map((m) => <option key={m} value={m} />)}</datalist>

        <div className="me-hint">填任意 OpenRouter 模型 id(下拉是精选建议)。改完即时生效,不用重启。</div>
        <button className="me-save" onClick={saveModels}>保存模型</button>
        {msg && <div className="detail-msg">{msg}</div>}
      </div>

      {/* 管理入口 */}
      <h2 className="section-h">管理</h2>
      <div className="me-list">
        <button className="me-item" onClick={() => nav('/plans')}>
          <Icon name="flag" size={20} className="me-ico" /><span>计划</span><span className="me-arrow">›</span>
        </button>
        <button className="me-item" onClick={() => nav('/cleanup')}>
          <Icon name="spark" size={20} className="me-ico" /><span>清库 · 清掉没信息量的</span><span className="me-arrow">›</span>
        </button>
      </div>

      <div className="home-foot">
        <button className="text-link" onClick={logout}>退出登录</button>
      </div>
    </div>
  )
}
