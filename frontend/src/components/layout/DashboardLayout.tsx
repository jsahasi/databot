import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { ChatProvider, useChatContext } from '../../context/ChatContext'
import { ClientProvider } from '../../context/ClientContext'
import { useIsMobile } from '../../hooks/useMediaQuery'
import { Menu } from 'lucide-react'
import TopNav from './TopNav'
import ChatSidebar from './ChatSidebar'
import AccountBreadcrumb from './AccountBreadcrumb'
import EventCalendar from '../calendar/EventCalendar'

function LayoutInner() {
  const { isCalendarOpen, calendarProposedMode, proposedEvents, closeCalendar, sendMessage } = useChatContext()
  const isMobile = useIsMobile()
  const [sidebarOpen, setSidebarOpen] = useState(false)
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
        {isMobile ? (
          sidebarOpen && <ChatSidebar onClose={() => setSidebarOpen(false)} />
        ) : (
          <ChatSidebar />
        )}
        <main id="main-content" style={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column' }}>
          <Outlet />
        </main>
      </div>
      {isMobile && !sidebarOpen && (
        <button
          onClick={() => setSidebarOpen(true)}
          aria-label="Open sidebar menu"
          style={{
            position: 'fixed', bottom: 16, left: 16, zIndex: 25,
            width: 48, height: 48, borderRadius: '50%',
            background: 'var(--color-primary)', color: '#fff',
            border: 'none', cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
          }}
        >
          <Menu size={20} />
        </button>
      )}
      <EventCalendar isOpen={isCalendarOpen} proposedMode={calendarProposedMode} proposedEvents={proposedEvents} onClose={closeCalendar} onEventToChat={(ev) => {
        const msg = ev.event_id < 0
          ? `Tell me about this proposed event — ${ev.title}`
          : `Tell me about event ${ev.event_id} — ${ev.title}`
        sendMessage(msg)
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
