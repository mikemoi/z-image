import { NavLink } from 'react-router-dom'
import Icon from './Icon'

// 底部导航,落在拇指热区。上传是主动作,居中放大。
export default function TabBar() {
  return (
    <nav className="tabbar">
      <NavLink to="/" end className="tab">
        <Icon name="home" className="tab-icon" />
        <span className="tab-label">首页</span>
      </NavLink>
      <NavLink to="/upload" className="tab tab-primary">
        <span className="tab-plus"><Icon name="plus" size={26} stroke={2.2} /></span>
        <span className="tab-label">上传</span>
      </NavLink>
      <NavLink to="/capture" className="tab">
        <Icon name="pen" className="tab-icon" />
        <span className="tab-label">记</span>
      </NavLink>
      <NavLink to="/trash" className="tab">
        <Icon name="trash" className="tab-icon" />
        <span className="tab-label">回收站</span>
      </NavLink>
    </nav>
  )
}
