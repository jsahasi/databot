import { useEffect, useState, type ReactNode } from 'react'
import { useChatContext } from '../../context/ChatContext'
import { useClientContext } from '../../context/ClientContext'

interface AdminUser {
  admin_id: number
  email: string
  name: string
  profile: string
}

export default function TopNav({ breadcrumb }: { breadcrumb?: ReactNode }) {
  const { isConnected, openCalendar, resetChat } = useChatContext()
  const { selectedClientId } = useClientContext()
  const [dark, setDark] = useState(() => document.documentElement.getAttribute('data-theme') === 'dark')
  const [dbEnv, setDbEnv] = useState<string>('')
  const [qaAvailable, setQaAvailable] = useState(false)
  const [switching, setSwitching] = useState(false)
  const [admins, setAdmins] = useState<AdminUser[]>([])
  const [selectedAdmin, setSelectedAdmin] = useState<string>('')

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light')
    localStorage.setItem('theme', dark ? 'dark' : 'light')
  }, [dark])

  // Fetch active admins on mount and when client_id changes
  useEffect(() => {
    setSelectedAdmin('')
    sessionStorage.removeItem('adminPermissions')
    sessionStorage.removeItem('adminInfo')
    fetch('/api/admins')
      .then(r => r.json())
      .then(d => setAdmins(d.admins || []))
      .catch(() => setAdmins([]))
  }, [selectedClientId])

  // Poll DB environment status every 30s
  useEffect(() => {
    let mounted = true
    const fetchStatus = () => {
      fetch('/api/status')
        .then(r => r.json())
        .then(d => { if (mounted) { setDbEnv(d.on24_db || ''); setQaAvailable(!!d.qa_available) } })
        .catch(() => { if (mounted) setDbEnv('') })
    }
    fetchStatus()
    const interval = setInterval(fetchStatus, 30000)
    return () => { mounted = false; clearInterval(interval) }
  }, [])

  return (
    <header
      aria-label="Application header"
      style={{
        height: 52,
        flexShrink: 0,
        background: 'var(--color-card)',
        borderBottom: '1px solid var(--color-border)',
        display: 'flex',
        alignItems: 'center',
        paddingLeft: '1.25rem',
        paddingRight: '1.25rem',
        gap: '2rem',
        zIndex: 20,
      }}
    >
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexShrink: 0 }}>
        <div style={{
          width: 28, height: 28, borderRadius: 6,
          background: 'var(--color-primary)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: '#fff', fontSize: '0.6rem', fontWeight: 800, letterSpacing: '-0.02em',
        }}>ON24</div>
        <span style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--color-text)', letterSpacing: '-0.01em' }}>
          ON24 Nexus
        </span>
      </div>

      {/* Breadcrumb (inline, separated by left border) */}
      {breadcrumb}

      {/* Spacer */}
      <div style={{ flex: 1 }} />

      {/* Simulated Admin dropdown */}
      {admins.length > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', flexShrink: 0 }}>
          <label htmlFor="admin-select" style={{ fontSize: '0.7rem', color: 'var(--color-text-secondary)', fontWeight: 600, whiteSpace: 'nowrap' }}>
            Simulated Admin:
          </label>
          <select
            id="admin-select"
            value={selectedAdmin}
            onChange={e => {
              const email = e.target.value
              setSelectedAdmin(email)
              if (!email) { sessionStorage.removeItem('adminPermissions'); return }
              const admin = admins.find(a => a.email === email)
              if (admin) {
                fetch(`/api/admins/${admin.admin_id}/permissions`)
                  .then(r => r.json())
                  .then(d => {
                    const perms: string[] = d.permissions || []
                    sessionStorage.setItem('adminPermissions', JSON.stringify(perms))
                    sessionStorage.setItem('adminInfo', JSON.stringify({ email: admin.email, name: admin.name, profile: admin.profile }))
                    // Reset chat to home page (tiles will re-render with filtered permissions)
                    resetChat()
                  })
                  .catch(() => sessionStorage.removeItem('adminPermissions'))
              }
            }}
            style={{
              fontSize: '0.75rem',
              padding: '0.2rem 0.4rem',
              borderRadius: 4,
              border: '1px solid var(--color-border)',
              background: 'var(--color-card)',
              color: 'var(--color-text)',
              maxWidth: 220,
              cursor: 'pointer',
            }}
          >
            <option value="">— None —</option>
            {admins.map(a => (
              <option key={a.admin_id} value={a.email}>{a.email} ({a.profile})</option>
            ))}
          </select>
        </div>
      )}

      {/* Right side */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexShrink: 0 }}>
        {/* Dark mode toggle */}
        <button
          onClick={() => setDark(d => !d)}
          aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
          aria-pressed={dark}
          title={dark ? 'Switch to light mode' : 'Switch to dark mode'}
          style={{
            width: 36, height: 20,
            borderRadius: 10,
            background: dark ? 'var(--color-primary)' : '#d1d5db',
            border: 'none',
            cursor: 'pointer',
            position: 'relative',
            transition: 'background 0.2s',
            flexShrink: 0,
          }}
        >
          <span aria-hidden="true" style={{
            position: 'absolute',
            top: 2, left: dark ? 18 : 2,
            width: 16, height: 16,
            borderRadius: '50%',
            background: '#fff',
            transition: 'left 0.2s',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '0.6rem',
          }}>
            {dark ? '🌙' : '☀️'}
          </span>
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
          <div
            aria-hidden="true"
            style={{
              width: 6, height: 6, borderRadius: '50%',
              background: isConnected ? '#10b981' : '#ef4444',
            }}
          />
          <span style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>
            {isConnected ? 'Connected' : 'Reconnecting'}
          </span>
          {dbEnv && dbEnv !== 'disconnected' && (
            <button
              onClick={() => {
                if (!qaAvailable || switching) return
                const target = dbEnv === 'PROD' ? 'QA' : 'PROD'
                setSwitching(true)
                fetch(`/api/status/switch-db?target=${target}`, { method: 'POST' })
                  .then(r => r.json())
                  .then(d => setDbEnv(d.on24_db || 'disconnected'))
                  .catch(() => {})
                  .finally(() => setSwitching(false))
              }}
              title={qaAvailable ? `Click to switch to ${dbEnv === 'PROD' ? 'QA' : 'PROD'}` : 'QA database not configured'}
              style={{
                fontSize: '0.65rem',
                fontWeight: 600,
                padding: '0.1rem 0.4rem',
                borderRadius: 4,
                background: dbEnv === 'PROD' ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.15)',
                color: dbEnv === 'PROD' ? '#10b981' : '#f59e0b',
                letterSpacing: '0.03em',
                border: 'none',
                cursor: qaAvailable ? 'pointer' : 'default',
                opacity: switching ? 0.5 : 1,
              }}
            >
              {switching ? '...' : dbEnv}
            </button>
          )}
          {dbEnv === 'disconnected' && (
            <span style={{
              fontSize: '0.65rem',
              fontWeight: 600,
              padding: '0.1rem 0.4rem',
              borderRadius: 4,
              background: 'rgba(239,68,68,0.15)',
              color: '#ef4444',
            }}>
              DB offline
            </span>
          )}
        </div>
        {/* Calendar button */}
        <button
          onClick={openCalendar}
          aria-label="Open event calendar"
          title="Event Calendar"
          style={{
            width: 32, height: 32,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: 'transparent',
            border: '1px solid var(--color-border)',
            borderRadius: 6,
            color: 'var(--color-text-secondary)',
            cursor: 'pointer',
          }}
        >
          <svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
            <line x1="16" y1="2" x2="16" y2="6"/>
            <line x1="8" y1="2" x2="8" y2="6"/>
            <line x1="3" y1="10" x2="21" y2="10"/>
          </svg>
        </button>

        <button style={{
          padding: '0.3rem 0.75rem',
          fontSize: '0.775rem',
          background: 'transparent',
          border: '1px solid var(--color-border)',
          borderRadius: 6,
          color: 'var(--color-text)',
          cursor: 'pointer',
        }}>
          Get Help
        </button>
        <button
          aria-label="User menu — Jayesh Sahasi"
          style={{
            width: 30, height: 30, borderRadius: '50%',
            background: 'var(--color-border)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '0.75rem', color: 'var(--color-text)', fontWeight: 600,
            cursor: 'pointer', border: 'none',
          }}
        >
          JS
        </button>
      </div>
    </header>
  )
}
