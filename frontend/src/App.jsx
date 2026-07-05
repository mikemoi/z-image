import { Routes, Route } from 'react-router-dom'
import TokenGate from './components/TokenGate'
import TabBar from './components/TabBar'
import Home from './pages/Home'
import Upload from './pages/Upload'
import Browse from './pages/Browse'
import Detail from './pages/Detail'
import Search from './pages/Search'
import Capture from './pages/Capture'
import Logs from './pages/Logs'
import Ideas from './pages/Ideas'
import Me from './pages/Me'
import Settings from './pages/Settings'
import Plans from './pages/Plans'
import Overview from './pages/Overview'
import Trash from './pages/Trash'
import ReviewSession from './pages/ReviewSession'

export default function App() {
  return (
    <TokenGate>
      <div className="app">
        <main className="app-main">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/upload" element={<Upload />} />
            <Route path="/browse" element={<Browse />} />
            <Route path="/search" element={<Search />} />
            <Route path="/item/:id" element={<Detail />} />
            <Route path="/capture" element={<Capture />} />
            <Route path="/logs" element={<Logs />} />
            <Route path="/ideas" element={<Ideas />} />
            <Route path="/me" element={<Me />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/plans" element={<Plans />} />
            <Route path="/overview" element={<Overview />} />
            <Route path="/trash" element={<Trash />} />
            <Route path="/review" element={<ReviewSession />} />
          </Routes>
        </main>
        <TabBar />
      </div>
    </TokenGate>
  )
}
