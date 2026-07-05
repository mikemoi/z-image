import { useNavigate } from 'react-router-dom'
import { api, clearToken } from '../api'
import Icon from '../components/Icon'

// 我的:纯入口。AI 设置单独一页。
export default function Me() {
  const nav = useNavigate()
  function logout() { clearToken(); window.location.assign('/') }

  return (
    <div className="page">
      <h1 className="page-title">我的</h1>

      <div className="me-list">
        <button className="me-item" onClick={() => nav('/settings')}>
          <Icon name="spark" size={20} className="me-ico" /><span>AI 设置 · 用量 / 模型</span><span className="me-arrow">›</span>
        </button>
        <button className="me-item" onClick={() => nav('/plans')}>
          <Icon name="flag" size={20} className="me-ico" /><span>计划</span><span className="me-arrow">›</span>
        </button>
      </div>

      <div className="home-foot">
        <button className="text-link" onClick={logout}>退出登录</button>
      </div>
    </div>
  )
}
