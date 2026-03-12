import { useChatContext } from '../../context/ChatContext'

export default function TopNav() {
  const { isConnected } = useChatContext()

  return (
    <header style={{
      height: 52,
      flexShrink: 0,
      background: '#fff',
      borderBottom: '1px solid #e5e7eb',
      display: 'flex',
      alignItems: 'center',
      paddingLeft: '1.25rem',
      paddingRight: '1.25rem',
      gap: '2rem',
      zIndex: 20,
    }}>
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexShrink: 0 }}>
        <div style={{
          width: 28, height: 28, borderRadius: 6,
          background: 'var(--color-primary)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: '#fff', fontSize: '0.7rem', fontWeight: 800, letterSpacing: '-0.02em',
        }}>DB</div>
        <span style={{ fontSize: '0.95rem', fontWeight: 700, color: '#111827', letterSpacing: '-0.01em' }}>
          DataBot
        </span>
      </div>

      {/* Spacer */}
      <div style={{ flex: 1 }} />

      {/* Right side */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
          <div style={{
            width: 6, height: 6, borderRadius: '50%',
            background: isConnected ? '#10b981' : '#ef4444',
          }} />
          <span style={{ fontSize: '0.75rem', color: '#6b7280' }}>
            {isConnected ? 'Connected' : 'Reconnecting'}
          </span>
        </div>
        <button style={{
          padding: '0.3rem 0.75rem',
          fontSize: '0.775rem',
          background: 'transparent',
          border: '1px solid #d1d5db',
          borderRadius: 6,
          color: '#374151',
          cursor: 'pointer',
        }}>
          Get Help
        </button>
        <div style={{
          width: 30, height: 30, borderRadius: '50%',
          background: '#e5e7eb',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '0.75rem', color: '#374151', fontWeight: 600,
          cursor: 'pointer',
        }}>
          JS
        </div>
      </div>
    </header>
  )
}
