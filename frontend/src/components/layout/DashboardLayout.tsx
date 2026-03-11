import { Outlet } from 'react-router-dom'
import { ChatProvider } from '../../context/ChatContext'
import TopNav from './TopNav'
import ChatSidebar from './ChatSidebar'

export default function DashboardLayout() {
  return (
    <ChatProvider>
      <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
        <TopNav />
        <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
          <ChatSidebar />
          <main style={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column' }}>
            <Outlet />
          </main>
        </div>
      </div>
    </ChatProvider>
  )
}
