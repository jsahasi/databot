import { useState, useEffect, type CSSProperties } from 'react'
import { useSyncStatus, useTriggerSync } from '../hooks/useAnalytics'
import api from '../services/api'

type SyncInterval = 'manual' | '15min' | '1hour' | '4hours'

const SYNC_INTERVAL_OPTIONS: { value: SyncInterval; label: string }[] = [
  { value: 'manual', label: 'Manual only' },
  { value: '15min', label: 'Every 15 minutes' },
  { value: '1hour', label: 'Every hour' },
  { value: '4hours', label: 'Every 4 hours' },
]

const cardStyle: CSSProperties = {
  background: 'white',
  borderRadius: 'var(--radius)',
  border: '1px solid var(--color-border)',
  padding: '1.5rem',
  marginBottom: '1.5rem',
}

const sectionTitleStyle: CSSProperties = {
  fontSize: '1rem',
  fontWeight: 600,
  color: 'var(--color-text)',
  marginBottom: '1rem',
  paddingBottom: '0.5rem',
  borderBottom: '1px solid var(--color-border)',
}

const labelStyle: CSSProperties = {
  display: 'block',
  fontSize: '0.8rem',
  fontWeight: 500,
  color: 'var(--color-text-secondary)',
  marginBottom: '0.375rem',
}

const inputStyle: CSSProperties = {
  width: '100%',
  padding: '0.5rem 0.75rem',
  fontSize: '0.875rem',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius)',
  color: 'var(--color-text)',
  background: 'var(--color-bg)',
  boxSizing: 'border-box',
  cursor: 'not-allowed',
  opacity: 0.7,
}

const fieldGroupStyle: CSSProperties = {
  marginBottom: '1rem',
}

export default function Settings() {
  const [showSecret, setShowSecret] = useState(false)
  const [syncInterval, setSyncInterval] = useState<SyncInterval>('manual')
  const [connectionStatus, setConnectionStatus] = useState<'loading' | 'connected' | 'disconnected'>('loading')

  const { data: syncStatus } = useSyncStatus()
  const syncMutation = useTriggerSync()

  const latestSync = syncStatus?.[0]
  const isSyncing = latestSync?.status === 'running'

  useEffect(() => {
    api.get('/health')
      .then(() => setConnectionStatus('connected'))
      .catch(() => setConnectionStatus('disconnected'))
  }, [])

  return (
    <div style={{ maxWidth: 720 }}>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '1.5rem', color: 'var(--color-text)' }}>
        Settings
      </h1>

      {/* ON24 Credentials */}
      <div style={cardStyle}>
        <h2 style={sectionTitleStyle}>ON24 Credentials</h2>

        {/* Info banner */}
        <div style={{
          background: 'var(--color-info-bg)',
          border: '1px solid var(--color-info-border)',
          borderRadius: 'var(--radius)',
          padding: '0.75rem 1rem',
          marginBottom: '1.25rem',
          fontSize: '0.8rem',
          color: 'var(--color-primary)',
          display: 'flex',
          gap: '0.5rem',
          alignItems: 'flex-start',
        }}>
          <span aria-hidden="true" style={{ flexShrink: 0, marginTop: '0.05rem' }}>&#9432;</span>
          <span>
            These credentials are stored server-side and loaded from environment variables.
            Contact your administrator to update them.
          </span>
        </div>

        {/* Connection status */}
        <div style={{ marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>Connection status:</span>
          {connectionStatus === 'loading' ? (
            <span style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>Checking...</span>
          ) : connectionStatus === 'connected' ? (
            <span style={{
              display: 'inline-flex', alignItems: 'center', gap: '0.3rem',
              fontSize: '0.8rem', fontWeight: 500, color: 'var(--color-success)',
            }}>
              <span aria-hidden="true" style={{
                width: 8, height: 8, borderRadius: '50%',
                background: 'var(--color-success)', display: 'inline-block',
              }} />
              Connected
            </span>
          ) : (
            <span style={{
              display: 'inline-flex', alignItems: 'center', gap: '0.3rem',
              fontSize: '0.8rem', fontWeight: 500, color: 'var(--color-danger)',
            }}>
              <span aria-hidden="true" style={{
                width: 8, height: 8, borderRadius: '50%',
                background: 'var(--color-danger)', display: 'inline-block',
              }} />
              Disconnected
            </span>
          )}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
          <div style={fieldGroupStyle}>
            <label htmlFor="settings-client-id" style={labelStyle}>Client ID</label>
            <input
              id="settings-client-id"
              type="text"
              value="••••••••"
              readOnly
              aria-label="Client ID (hidden)"
              style={inputStyle}
            />
          </div>

          <div style={fieldGroupStyle}>
            <label htmlFor="settings-token-key" style={labelStyle}>Access Token Key</label>
            <input
              id="settings-token-key"
              type="text"
              value="••••••••••••••••"
              readOnly
              aria-label="Access Token Key (hidden)"
              style={inputStyle}
            />
          </div>
        </div>

        <div style={fieldGroupStyle}>
          <label htmlFor="settings-token-secret" style={labelStyle}>Access Token Secret</label>
          <div style={{ position: 'relative' }}>
            <input
              id="settings-token-secret"
              type={showSecret ? 'text' : 'password'}
              value="••••••••••••••••••••••••"
              readOnly
              aria-label="Access Token Secret (hidden)"
              style={{ ...inputStyle, paddingRight: '3rem' }}
            />
            <button
              onClick={() => setShowSecret(v => !v)}
              style={{
                position: 'absolute', right: '0.5rem', top: '50%',
                transform: 'translateY(-50%)',
                background: 'none', border: 'none',
                color: 'var(--color-text-secondary)',
                cursor: 'pointer', fontSize: '0.8rem', padding: '0.25rem',
              }}
              aria-label={showSecret ? 'Hide secret' : 'Show secret'}
            >
              {showSecret ? 'Hide' : 'Show'}
            </button>
          </div>
        </div>
      </div>

      {/* Sync Configuration */}
      <div style={cardStyle}>
        <h2 style={sectionTitleStyle}>Sync Configuration</h2>

        {/* Sync interval */}
        <div style={{ marginBottom: '1.5rem' }}>
          <p style={{ fontSize: '0.875rem', fontWeight: 500, color: 'var(--color-text)', marginBottom: '0.75rem' }}>
            Sync interval
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {SYNC_INTERVAL_OPTIONS.map(option => (
              <label
                key={option.value}
                style={{
                  display: 'flex', alignItems: 'center', gap: '0.625rem',
                  fontSize: '0.875rem', color: 'var(--color-text)', cursor: 'pointer',
                }}
              >
                <input
                  type="radio"
                  name="syncInterval"
                  value={option.value}
                  checked={syncInterval === option.value}
                  onChange={() => setSyncInterval(option.value)}
                  style={{ accentColor: 'var(--color-primary)', cursor: 'pointer' }}
                />
                {option.label}
              </label>
            ))}
          </div>
        </div>

        {/* Current sync status card */}
        <div style={{
          background: 'var(--color-bg)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius)',
          padding: '1rem',
          marginBottom: '1rem',
        }}>
          <p style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-text)', marginBottom: '0.5rem' }}>
            Current sync status
          </p>
          {latestSync ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                <span style={{ color: 'var(--color-text-secondary)' }}>Status</span>
                <span style={{
                  fontWeight: 500,
                  color: latestSync.status === 'completed' ? 'var(--color-success)'
                    : latestSync.status === 'failed' ? 'var(--color-danger)'
                    : 'var(--color-primary)',
                }}>
                  {latestSync.status.charAt(0).toUpperCase() + latestSync.status.slice(1)}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                <span style={{ color: 'var(--color-text-secondary)' }}>Last sync</span>
                <span style={{ fontWeight: 500, color: 'var(--color-text)' }}>
                  {latestSync.completed_at
                    ? new Date(latestSync.completed_at).toLocaleString()
                    : latestSync.status === 'running' ? 'In progress...' : '—'}
                </span>
              </div>
              {latestSync.events_synced != null && (
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                  <span style={{ color: 'var(--color-text-secondary)' }}>Records synced</span>
                  <span style={{ fontWeight: 500, color: 'var(--color-text)' }}>
                    {latestSync.events_synced.toLocaleString()}
                  </span>
                </div>
              )}
              {latestSync.error_message && (
                <div style={{ marginTop: '0.5rem', padding: '0.5rem', background: 'var(--color-danger-bg)', borderRadius: 4, fontSize: '0.75rem', color: 'var(--color-danger)' }}>
                  {latestSync.error_message}
                </div>
              )}
            </div>
          ) : (
            <p style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>No sync history available.</p>
          )}
        </div>

        {/* Manual sync trigger */}
        <button
          onClick={() => syncMutation.mutate()}
          disabled={isSyncing || syncMutation.isPending}
          style={{
            padding: '0.5rem 1.25rem',
            fontSize: '0.875rem',
            background: isSyncing || syncMutation.isPending ? 'var(--color-border)' : 'var(--color-primary)',
            color: 'var(--color-card)',
            border: 'none',
            borderRadius: 'var(--radius)',
            cursor: isSyncing || syncMutation.isPending ? 'not-allowed' : 'pointer',
            fontWeight: 500,
            transition: 'background 0.15s',
          }}
        >
          {isSyncing || syncMutation.isPending ? 'Syncing...' : 'Trigger Manual Sync'}
        </button>
      </div>

      {/* About */}
      <div style={cardStyle}>
        <h2 style={sectionTitleStyle}>About</h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
          <div style={{ display: 'flex', gap: '0.75rem', fontSize: '0.875rem' }}>
            <span style={{ color: 'var(--color-text-secondary)', minWidth: 100 }}>Application</span>
            <span style={{ color: 'var(--color-text)', fontWeight: 500 }}>DataBot</span>
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', fontSize: '0.875rem' }}>
            <span style={{ color: 'var(--color-text-secondary)', minWidth: 100 }}>Version</span>
            <span style={{ color: 'var(--color-text)', fontWeight: 500 }}>1.0.0</span>
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', fontSize: '0.875rem' }}>
            <span style={{ color: 'var(--color-text-secondary)', minWidth: 100 }}>Powered by</span>
            <span style={{ color: 'var(--color-text)', fontWeight: 500 }}>Claude AI + ON24 API</span>
          </div>
        </div>
      </div>
    </div>
  )
}
