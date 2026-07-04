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
      <NavLink to="/upload" className="tab">
        <Icon name="image" className="tab-icon" />
        <span className="tab-label">上传</span>
      </NavLink>
      <NavLink to="/ideas" className="tab">
        <Icon name="bulb" className="tab-icon" />
        <span className="tab-label">想法</span>
      </NavLink>
      <NavLink to="/logs" className="tab">
        <Icon name="book" className="tab-icon" />
        <span className="tab-label">记录</span>
      </NavLink>
      <NavLink to="/me" className="tab">
        <Icon name="user" className="tab-icon" />
        <span className="tab-label">我的</span>
      </NavLink>
    </nav>
  )
}
