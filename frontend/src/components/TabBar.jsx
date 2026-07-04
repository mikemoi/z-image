import { NavLink } from 'react-router-dom'

// 底部导航,落在拇指热区。上传是主动作,居中放大。
export default function TabBar() {
  return (
    <nav className="tabbar">
      <NavLink to="/" end className="tab">
        <span className="tab-icon">🏠</span>
        <span className="tab-label">首页</span>
      </NavLink>
      <NavLink to="/upload" className="tab tab-primary">
        <span className="tab-plus">＋</span>
        <span className="tab-label">上传</span>
      </NavLink>
      <NavLink to="/capture" className="tab">
        <span className="tab-icon">✎</span>
        <span className="tab-label">记</span>
      </NavLink>
      <NavLink to="/trash" className="tab">
        <span className="tab-icon">🗑</span>
        <span className="tab-label">回收站</span>
      </NavLink>
    </nav>
  )
}
