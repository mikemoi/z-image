import { useState, useRef } from 'react'
import { api } from '../api'

// 清空节奏:选图→上传→大字"已接收 N 张,手机可清空"。不显示待处理计数。
export default function Upload() {
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const inputRef = useRef(null)

  async function onPick(e) {
    const files = Array.from(e.target.files || [])
    if (!files.length) return
    setBusy(true); setError(''); setResult(null)
    try {
      const r = await api.uploadItems(files)
      setResult(r)
    } catch (err) {
      setError('上传失败,请重试')
    } finally {
      setBusy(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  return (
    <div className="page upload-page">
      <h1 className="page-title">上传</h1>

      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        multiple
        hidden
        onChange={onPick}
      />

      {!result && (
        <button
          className="upload-drop"
          onClick={() => inputRef.current?.click()}
          disabled={busy}
        >
          {busy ? '上传中…' : '＋ 从相册选图'}
          <span className="upload-hint">支持多选,上传即走</span>
        </button>
      )}

      {result && (
        <div className="upload-done">
          <div className="upload-check">✓</div>
          <div className="upload-big">已接收 {result.received} 张</div>
          <div className="upload-sub">手机可清空,现在就去删掉相册里的原图</div>
          <div className="upload-note">AI 会在后台慢慢整理,不用等,回头首页看就好</div>
          <button className="btn-primary" onClick={() => setResult(null)}>
            再传一批
          </button>
        </div>
      )}

      {error && <div className="banner-error">{error}</div>}
    </div>
  )
}
