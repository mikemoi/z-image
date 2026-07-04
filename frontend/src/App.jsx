import { Routes, Route } from 'react-router-dom'
import TokenGate from './components/TokenGate'
import TabBar from './components/TabBar'
import Home from './pages/Home'
import Upload from './pages/Upload'
import Browse from './pages/Browse'
import Detail from './pages/Detail'
import Trash from './pages/Trash'
import Search from './pages/Search'
import Capture from './pages/Capture'
import Inbox from './pages/Inbox'
import Logs from './pages/Logs'
import Cleanup from './pages/Cleanup'

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
            <Route path="/trash" element={<Trash />} />
            <Route path="/capture" element={<Capture />} />
            <Route path="/inbox" element={<Inbox />} />
            <Route path="/logs" element={<Logs />} />
            <Route path="/cleanup" element={<Cleanup />} />
          </Routes>
        </main>
        <TabBar />
      </div>
    </TokenGate>
  )
}
