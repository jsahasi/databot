import { Routes, Route } from 'react-router-dom'
import DashboardLayout from './components/layout/DashboardLayout'
import Dashboard from './pages/Dashboard'
import Events from './pages/Events'
import EventDetail from './pages/EventDetail'
import Audiences from './pages/Audiences'
import ContentInsights from './pages/ContentInsights'
import Settings from './pages/Settings'

export default function App() {
  return (
    <Routes>
      <Route element={<DashboardLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/events" element={<Events />} />
        <Route path="/events/:eventId" element={<EventDetail />} />
        <Route path="/audiences" element={<Audiences />} />
        <Route path="/content" element={<ContentInsights />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
    </Routes>
  )
}
