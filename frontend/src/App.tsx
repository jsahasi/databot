import { Routes, Route } from 'react-router-dom'
import DashboardLayout from './components/layout/DashboardLayout'
import ChatPanel from './components/chat/ChatPanel'
import Dashboard from './pages/Dashboard'
import Events from './pages/Events'
import EventDetail from './pages/EventDetail'
import Audiences from './pages/Audiences'
import ContentInsights from './pages/ContentInsights'
import Settings from './pages/Settings'
import ShareReview from './pages/ShareReview'

export default function App() {
  return (
    <Routes>
      <Route path="/share/:shareId" element={<ShareReview />} />
      <Route element={<DashboardLayout />}>
        <Route path="/" element={<ChatPanel />} />
        <Route path="/analytics" element={<Dashboard />} />
        <Route path="/events" element={<Events />} />
        <Route path="/events/:eventId" element={<EventDetail />} />
        <Route path="/audiences" element={<Audiences />} />
        <Route path="/content" element={<ContentInsights />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
    </Routes>
  )
}
