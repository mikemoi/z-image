import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import Img from '../components/Img'

// 想法流:看图产生的 + 凭空的,汇聚成"思维镜子",可回顾、以后分析思维模式。
export default function Ideas() {
  const nav = useNavigate()
  const [ideas, setIdeas] = useState([])
  const [body, setBody] = useState('')
  const [loading, setLoading] = useState(true)

  function load() {
    setLoading(true)
    api.ideas().then(setIdeas).catch(() => setIdeas([])).finally(() => setLoading(false))
  }
  useEffect(load, [])

  async function add() {
    if (!body.trim()) return
    await api.createEntry({ kind: 'idea', body: body.trim() })
    setBody(''); load()
  }
  async function del(e) {
    await api.deleteEntry(e.id)
    setIdeas((xs) => xs.filter((x) => x.id !== e.id))
  }

  return (
    <div className="page">
      <h1 className="page-title">想法</h1>
      <div className="capture-hint">看到什么、想到什么,写下来。它们攒起来就是你怎么思考的镜子。</div>

      <div className="log-compose">
        <textarea className="capture-input" value={body} rows={3}
          onChange={(e) => setBody(e.target.value)} placeholder="此刻的想法…" />
        <div className="mood-row"><button className="log-save" onClick={add} disabled={!body.trim()}>记下</button></div>
      </div>

      {loading ? (
        <div className="empty-hint">加载中…</div>
      ) : ideas.length === 0 ? (
        <div className="empty-hint">还没有想法 · 翻到一张图有感觉时,在详情页写一条</div>
      ) : (
        <div className="card-list">
          {ideas.map((e) => (
            <div key={e.id} className="entry-card">
              <div className="entry-body">{e.body}</div>
              <div className="idea-foot">
                {e.checksum && (
                  <div className="idea-src" onClick={() => nav(`/item/${e.source_item_id}`)}>
                    <Img checksum={e.checksum} className="idea-thumb" /><span>来自截图</span>
                  </div>
                )}
                <button className="log-del" onClick={() => del(e)}>删</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
