import { NavLink, Outlet } from 'react-router-dom'
import { useSyncStatus, useTriggerSync } from '../../hooks/useAnalytics'

const navItems = [
  { path: '/', label: 'Dashboard', icon: '\u{1F4CA}' },
  { path: '/events', label: 'Events', icon: '\u{1F4C5}' },
  { path: '/audiences', label: 'Audiences', icon: '\u{1F465}' },
  { path: '/content', label: 'Content Insights', icon: '\u{1F4C8}' },
  { path: '/settings', label: 'Settings', icon: '\u{2699}\u{FE0F}' },
]

export default function DashboardLayout() {
  const { data: syncStatus } = useSyncStatus()
  const syncMutation = useTriggerSync()
  const latestSync = syncStatus?.[0]
  const isSyncing = latestSync?.status === 'running'

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      {/* Sidebar */}
      <aside style={{
        width: 240, minHeight: '100vh', background: 'var(--color-sidebar)',
        color: 'var(--color-sidebar-text)', display: 'flex', flexDirection: 'column',
        position: 'fixed', left: 0, top: 0, bottom: 0, zIndex: 10,
      }}>
        <div style={{ padding: '1.5rem', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
          <h1 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fff', letterSpacing: '-0.02em' }}>
            DataBot
          </h1>
          <p style={{ fontSize: '0.7rem', marginTop: '0.25rem', opacity: 0.6 }}>ON24 Analytics</p>
        </div>
        <nav style={{ flex: 1, padding: '0.75rem 0' }}>
          {navItems.map(item => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              style={({ isActive }) => ({
                display: 'flex', alignItems: 'center', gap: '0.75rem',
                padding: '0.625rem 1.5rem', fontSize: '0.875rem',
                color: isActive ? '#fff' : 'var(--color-sidebar-text)',
                background: isActive ? 'rgba(79,70,229,0.2)' : 'transparent',
                borderRight: isActive ? '3px solid var(--color-primary)' : '3px solid transparent',
                textDecoration: 'none', transition: 'all 0.15s',
              })}
            >
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>

      {/* Main area */}
      <div style={{ flex: 1, marginLeft: 240, display: 'flex', flexDirection: 'column' }}>
        {/* Top bar */}
        <header style={{
          height: 56, background: 'var(--color-card)', borderBottom: '1px solid var(--color-border)',
          display: 'flex', alignItems: 'center', justifyContent: 'flex-end',
          padding: '0 1.5rem', position: 'sticky', top: 0, zIndex: 5,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            {latestSync && (
              <span style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>
                Last sync: {latestSync.completed_at ? new Date(latestSync.completed_at).toLocaleString() : 'In progress...'}
              </span>
            )}
            <button
              onClick={() => syncMutation.mutate()}
              disabled={isSyncing || syncMutation.isPending}
              style={{
                padding: '0.375rem 1rem', fontSize: '0.8rem',
                background: isSyncing ? 'var(--color-border)' : 'var(--color-primary)',
                color: '#fff', border: 'none', borderRadius: 'var(--radius)',
                cursor: isSyncing ? 'not-allowed' : 'pointer',
              }}
            >
              {isSyncing ? 'Syncing...' : 'Sync Now'}
            </button>
          </div>
        </header>

        {/* Page content */}
        <main style={{ flex: 1, padding: '1.5rem', overflow: 'auto' }}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}
