import { useEffect, useRef, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import DOMPurify from 'dompurify'
import { useChatContext } from '../../context/ChatContext'

const DOC_BASES = [
  { label: 'Market Requirements', path: '/docs/mrd.html' },
  { label: 'Product Requirements', path: '/docs/prd.html' },
  { label: 'Technical Specifications', path: '/docs/tech-spec.html' },
  { label: 'Test Plan & Results', path: '/docs/test-plan.html' },
  { label: 'Scalability', path: '/docs/scalability.html' },
  { label: 'Security Review', path: '/docs/security-review.html' },
  { label: 'Accessibility (VPAT)', path: '/docs/accessibility-vpat.html' },
  { label: 'API vs DB Benchmark', path: '/docs/api-vs-db-benchmark.html' },
]

export default function ChatSidebar() {
  const { resetChat } = useChatContext()
  const navigate = useNavigate()
  const location = useLocation()
  const [recentChanges, setRecentChanges] = useState<string>('')
  const [docsOpen, setDocsOpen] = useState(false)
  const docsRef = useRef<HTMLDivElement>(null)
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark'
  const themeParam = isDark ? '?theme=dark' : '?theme=light'
  const docLinks = DOC_BASES.map(d => ({ label: d.label, href: d.path + themeParam }))

  // Close docs dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (docsRef.current && !docsRef.current.contains(e.target as Node)) setDocsOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

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

      {/* Docs dropdown */}
      <div ref={docsRef} style={{ position: 'relative' }}>
        <button
          onClick={() => setDocsOpen(o => !o)}
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            width: '100%',
            padding: '0.4rem 0.5rem',
            background: docsOpen ? 'var(--color-chip-hover-bg)' : 'transparent',
            border: '1px solid var(--color-border)',
            borderRadius: 6,
            cursor: 'pointer',
            color: 'var(--color-text-secondary)',
            fontSize: '0.775rem',
            fontWeight: 600,
            transition: 'background 0.15s',
          }}
          onMouseEnter={e => { if (!docsOpen) (e.currentTarget as HTMLButtonElement).style.background = 'var(--color-chip-hover-bg)' }}
          onMouseLeave={e => { if (!docsOpen) (e.currentTarget as HTMLButtonElement).style.background = 'transparent' }}
        >
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <svg aria-hidden="true" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.6 }}>
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
            Documents
          </span>
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.5, transform: docsOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s' }}>
            <polyline points="2,3.5 5,6.5 8,3.5" />
          </svg>
        </button>
        {docsOpen && (
          <div style={{
            position: 'absolute',
            top: 'calc(100% + 4px)',
            left: 0,
            right: 0,
            zIndex: 1000,
            background: 'var(--color-card)',
            border: '1px solid var(--color-border)',
            borderRadius: 8,
            boxShadow: '0 4px 16px rgba(0,0,0,0.25)',
            padding: '0.3rem 0',
            maxHeight: 280,
            overflowY: 'auto',
          }}>
            {docLinks.map(({ label, href }) => (
              <a
                key={href}
                href={href}
                target="_blank"
                rel="noreferrer"
                onClick={() => setDocsOpen(false)}
                style={{
                  display: 'block',
                  padding: '0.4rem 0.75rem',
                  fontSize: '0.775rem',
                  color: 'var(--color-text-secondary)',
                  textDecoration: 'none',
                  transition: 'background 0.1s, color 0.1s',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
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
                {label}
              </a>
            ))}
          </div>
        )}
      </div>

      {/* Recent Changes */}
      {recentChanges && (
        <div style={{ flex: 1 }}>
          <p style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>
            Recent Changes
          </p>
          <div
            dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(recentChanges) }}
            style={{ fontSize: '0.72rem' }}
          />
        </div>
      )}
    </aside>
  )
}
