import { useEffect, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useChatContext } from '../../context/ChatContext'

const DOC_BASES = [
  { label: 'Market Requirements', path: '/docs/mrd.html' },
  { label: 'Product Requirements', path: '/docs/prd.html' },
  { label: 'Technical Specifications', path: '/docs/tech-spec.html' },
]

export default function ChatSidebar() {
  const { resetChat } = useChatContext()
  const navigate = useNavigate()
  const location = useLocation()
  const [recentChanges, setRecentChanges] = useState<string>('')
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark'
  const themeParam = isDark ? '?theme=dark' : '?theme=light'
  const docLinks = DOC_BASES.map(d => ({ label: d.label, href: d.path + themeParam }))

  useEffect(() => {
    fetch('/docs/recent-changes.html')
      .then(r => r.text())
      .then(html => {
        // Extract just the body content
        const match = html.match(/<body[^>]*>([\s\S]*)<\/body>/i)
        setRecentChanges(match ? match[1] : html)
      })
      .catch(() => {/* silent */})
  }, [])

  const handleNewChat = () => {
    resetChat()
    if (location.pathname !== '/') navigate('/')
  }

  return (
    <aside
      aria-label="Chat history"
      style={{
        width: 200,
        flexShrink: 0,
        height: '100%',
        background: 'var(--color-card)',
        borderRight: '1px solid var(--color-border)',
        display: 'flex',
        flexDirection: 'column',
        padding: '0.875rem 0.75rem',
        gap: '1.25rem',
        overflowY: 'auto',
      }}
    >
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
          <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
          </svg>
          New Chat
        </button>
        <button
          aria-label="View all chats"
          style={{
            width: 34, height: 34, flexShrink: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: 'transparent',
            border: '1px solid var(--color-border)',
            borderRadius: 8,
            cursor: 'pointer',
            color: 'var(--color-text-secondary)',
          }}
        >
          <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" />
            <rect x="14" y="14" width="7" height="7" /><rect x="3" y="14" width="7" height="7" />
          </svg>
        </button>
      </div>

      {/* Docs */}
      <div>
        <p style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>
          Docs
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
          {docLinks.map(({ label, href }) => (
            <a
              key={href}
              href={href}
              target="_blank"
              rel="noreferrer"
              style={{
                display: 'flex', alignItems: 'center', gap: '0.4rem',
                fontSize: '0.775rem',
                color: 'var(--color-text-secondary)',
                textDecoration: 'none',
                padding: '0.3rem 0.5rem',
                borderRadius: 6,
                transition: 'background 0.15s, color 0.15s',
              }}
              onMouseEnter={e => {
                (e.currentTarget as HTMLAnchorElement).style.background = 'var(--color-chip-hover-bg)'
                ;(e.currentTarget as HTMLAnchorElement).style.color = 'var(--color-text)'
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLAnchorElement).style.background = 'transparent'
                ;(e.currentTarget as HTMLAnchorElement).style.color = 'var(--color-text-secondary)'
              }}
            >
              <svg aria-hidden="true" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, opacity: 0.6 }}>
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
              {label}
            </a>
          ))}
        </div>
      </div>

      {/* Recent Changes */}
      {recentChanges && (
        <div style={{ flex: 1 }}>
          <p style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>
            Recent Changes
          </p>
          <div
            dangerouslySetInnerHTML={{ __html: recentChanges }}
            style={{ fontSize: '0.72rem' }}
          />
        </div>
      )}
    </aside>
  )
}
