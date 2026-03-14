import { Outlet } from 'react-router-dom'
import { ChatProvider, useChatContext } from '../../context/ChatContext'
import { ClientProvider } from '../../context/ClientContext'
import TopNav from './TopNav'
import ChatSidebar from './ChatSidebar'
import AccountBreadcrumb from './AccountBreadcrumb'
import EventCalendar from '../calendar/EventCalendar'

function LayoutInner() {
  const { isCalendarOpen, closeCalendar, sendMessage } = useChatContext()
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      <TopNav />
      <AccountBreadcrumb />
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <ChatSidebar />
        <main style={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column' }}>
          <Outlet />
        </main>
      </div>
      <EventCalendar isOpen={isCalendarOpen} onClose={closeCalendar} onEventToChat={(ev) => {
        sendMessage(`Tell me about event ${ev.event_id} — ${ev.title}`)
        closeCalendar()
      }} />
    </div>
  )
}

export default function DashboardLayout() {
  return (
    <ClientProvider>
      <ChatProvider>
        <LayoutInner />
      </ChatProvider>
    </ClientProvider>
  )
}
