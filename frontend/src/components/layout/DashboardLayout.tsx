import { Outlet } from 'react-router-dom'
import { ChatProvider, useChatContext } from '../../context/ChatContext'
import { ClientProvider } from '../../context/ClientContext'
import TopNav from './TopNav'
import ChatSidebar from './ChatSidebar'
import AccountBreadcrumb from './AccountBreadcrumb'
import EventCalendar from '../calendar/EventCalendar'

function LayoutInner() {
  const { isCalendarOpen, calendarProposedMode, proposedEvents, closeCalendar, sendMessage } = useChatContext()
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      <a
        href="#main-content"
        style={{ position: 'absolute', left: '-9999px', top: 'auto', width: '1px', height: '1px', overflow: 'hidden', zIndex: 9999 }}
        onFocus={e => { e.currentTarget.style.position = 'static'; e.currentTarget.style.width = 'auto'; e.currentTarget.style.height = 'auto' }}
        onBlur={e => { e.currentTarget.style.position = 'absolute'; e.currentTarget.style.left = '-9999px'; e.currentTarget.style.width = '1px'; e.currentTarget.style.height = '1px' }}
      >
        Skip to main content
      </a>
      <TopNav breadcrumb={<AccountBreadcrumb />} />
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <ChatSidebar />
        <main id="main-content" style={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column' }}>
          <Outlet />
        </main>
      </div>
      <EventCalendar isOpen={isCalendarOpen} proposedMode={calendarProposedMode} proposedEvents={proposedEvents} onClose={closeCalendar} onEventToChat={(ev) => {
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
