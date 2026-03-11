import { NavLink } from 'react-router-dom'
import { useChatContext } from '../../context/ChatContext'

const NAV_ITEMS = [
  { path: '/', label: 'Home', end: true },
  { path: '/analytics', label: 'Analytics' },
  { path: '/events', label: 'Events' },
  { path: '/audiences', label: 'Audiences' },
  { path: '/content', label: 'Content Insights' },
  { path: '/settings', label: 'Settings' },
]

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

      {/* Nav links */}
      <nav style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', flex: 1 }}>
        {NAV_ITEMS.map(item => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.end}
            style={({ isActive }) => ({
              padding: '0.375rem 0.75rem',
              fontSize: '0.825rem',
              fontWeight: isActive ? 600 : 400,
              color: isActive ? 'var(--color-primary)' : '#374151',
              borderBottom: isActive ? '2px solid var(--color-primary)' : '2px solid transparent',
              textDecoration: 'none',
              lineHeight: '36px',
              whiteSpace: 'nowrap',
              transition: 'color 0.12s',
            })}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

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
