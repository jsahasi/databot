import { useNavigate, useLocation } from 'react-router-dom'
import { useChatContext } from '../../context/ChatContext'

export default function ChatSidebar() {
  const { resetChat } = useChatContext()
  const navigate = useNavigate()
  const location = useLocation()

  const handleNewChat = () => {
    resetChat()
    if (location.pathname !== '/') {
      navigate('/')
    }
  }

  return (
    <aside style={{
      width: 200,
      flexShrink: 0,
      height: '100%',
      background: 'var(--color-card)',
      borderRight: '1px solid var(--color-border)',
      display: 'flex',
      flexDirection: 'column',
      padding: '0.875rem 0.75rem',
      gap: '1.25rem',
    }}>
      {/* New Chat button + toggle */}
      <div style={{ display: 'flex', gap: '0.375rem' }}>
        <button
          onClick={handleNewChat}
          style={{
            flex: 1,
            display: 'flex', alignItems: 'center', gap: '0.5rem',
            padding: '0.5rem 0.75rem',
            background: 'var(--color-primary)',
            color: '#fff',
            border: 'none',
            borderRadius: 8,
            fontSize: '0.8rem',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
          </svg>
          New Chat
        </button>
        <button style={{
          width: 34, height: 34, flexShrink: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'transparent',
          border: '1px solid var(--color-border)',
          borderRadius: 8,
          cursor: 'pointer',
          color: 'var(--color-text-secondary)',
        }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" />
            <rect x="14" y="14" width="7" height="7" /><rect x="3" y="14" width="7" height="7" />
          </svg>
        </button>
      </div>

      {/* Recent Chats */}
      <div style={{ flex: 1 }}>
        <p style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>
          Recent Chats
        </p>
        <p style={{ fontSize: '0.775rem', color: 'var(--color-text-secondary)', fontStyle: 'italic' }}>
          No recent chats
        </p>
      </div>
    </aside>
  )
}
