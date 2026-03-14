import { useEffect, useRef, useState } from 'react'
import { useClientContext } from '../../context/ClientContext'

interface ClientNode {
  client_id: number
  company_name: string
}

interface HierarchyData {
  root_client_id: number
  path: ClientNode[]
  children: ClientNode[]
  db_mode: 'PROD' | 'QA'
}

export default function AccountBreadcrumb() {
  const { selectedClientId, setSelectedClientId } = useClientContext()
  const [data, setData] = useState<HierarchyData | null>(null)
  const [expanded, setExpanded] = useState(false)   // "..." clicked to show full path
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Fetch hierarchy whenever selected client changes
  useEffect(() => {
    setLoading(true)
    setExpanded(false)
    fetch(`/api/hierarchy?client_id=${selectedClientId}`)
      .then(r => r.json())
      .then((d: HierarchyData) => setData(d))
      .catch(() => {/* silent — breadcrumb is non-critical */})
      .finally(() => setLoading(false))
  }, [selectedClientId])

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  if (!data && !loading) return null

  const { path = [], children = [], db_mode = 'PROD' } = data ?? {}

  // Determine which nodes to display as breadcrumbs
  // Rules:
  //   ≤ 3 nodes: show all
  //   > 3 nodes + not expanded: [root, '...', current]
  //   > 3 nodes + expanded: show all
  const showFull = path.length <= 3 || expanded
  const visibleCrumbs: Array<ClientNode | '__ellipsis__'> = showFull
    ? path
    : [path[0], '__ellipsis__' as const, path[path.length - 1]]

  const handleCrumbClick = (node: ClientNode) => {
    if (node.client_id !== selectedClientId) {
      setSelectedClientId(node.client_id)
    }
  }

  const handleChildSelect = (child: ClientNode) => {
    setDropdownOpen(false)
    setSelectedClientId(child.client_id)
  }

  const dbBadgeStyle: React.CSSProperties = {
    fontSize: '0.6rem',
    fontWeight: 700,
    padding: '0.15rem 0.45rem',
    borderRadius: 4,
    letterSpacing: '0.06em',
    background: db_mode === 'QA' ? 'rgba(251,191,36,0.18)' : 'rgba(52,211,153,0.14)',
    color: db_mode === 'QA' ? '#f59e0b' : '#34d399',
    border: `1px solid ${db_mode === 'QA' ? 'rgba(251,191,36,0.35)' : 'rgba(52,211,153,0.3)'}`,
    flexShrink: 0,
  }

  const crumbStyle = (active: boolean): React.CSSProperties => ({
    fontSize: '0.78rem',
    fontWeight: active ? 600 : 400,
    color: active ? 'var(--color-text)' : 'var(--color-text-secondary)',
    cursor: active ? 'default' : 'pointer',
    padding: '0.1rem 0.25rem',
    borderRadius: 4,
    whiteSpace: 'nowrap',
    flexShrink: 0,
    transition: 'color 0.12s, background 0.12s',
  })

  const sepStyle: React.CSSProperties = {
    color: 'var(--color-text-secondary)',
    opacity: 0.4,
    fontSize: '0.7rem',
    flexShrink: 0,
    margin: '0 0.1rem',
  }

  return (
    <nav
      aria-label="Account hierarchy"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.25rem',
        padding: '0.35rem 1rem',
        background: 'var(--color-card)',
        borderBottom: '1px solid var(--color-border)',
        minHeight: 32,
        overflow: 'visible',
      }}
    >
      {/* Breadcrumb nodes */}
      {loading && !data ? (
        <span style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', opacity: 0.5 }}>
          Loading…
        </span>
      ) : (
        <>
          {visibleCrumbs.map((crumb, i) => {
            const isLast = i === visibleCrumbs.length - 1

            if (crumb === '__ellipsis__') {
              return (
                <span key="ellipsis" style={{ display: 'flex', alignItems: 'center', gap: '0.1rem', flexShrink: 0 }}>
                  <span style={sepStyle}>›</span>
                  <button
                    onClick={() => setExpanded(true)}
                    title="Show full path"
                    style={{
                      ...crumbStyle(false),
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      letterSpacing: '0.05em',
                    }}
                    onMouseEnter={e => {
                      (e.currentTarget as HTMLButtonElement).style.background = 'var(--color-chip-hover-bg)'
                      ;(e.currentTarget as HTMLButtonElement).style.color = 'var(--color-text)'
                    }}
                    onMouseLeave={e => {
                      (e.currentTarget as HTMLButtonElement).style.background = 'none'
                      ;(e.currentTarget as HTMLButtonElement).style.color = 'var(--color-text-secondary)'
                    }}
                  >
                    •••
                  </button>
                </span>
              )
            }

            const node = crumb as ClientNode
            const isCurrent = node.client_id === selectedClientId && isLast

            return (
              <span key={node.client_id} style={{ display: 'flex', alignItems: 'center', gap: '0.1rem', flexShrink: 0 }}>
                {i > 0 && <span style={sepStyle}>›</span>}
                <button
                  onClick={() => !isCurrent && handleCrumbClick(node)}
                  style={{
                    ...crumbStyle(isCurrent),
                    background: 'none',
                    border: 'none',
                  }}
                  onMouseEnter={e => {
                    if (!isCurrent) {
                      (e.currentTarget as HTMLButtonElement).style.background = 'var(--color-chip-hover-bg)'
                      ;(e.currentTarget as HTMLButtonElement).style.color = 'var(--color-text)'
                    }
                  }}
                  onMouseLeave={e => {
                    if (!isCurrent) {
                      (e.currentTarget as HTMLButtonElement).style.background = 'none'
                      ;(e.currentTarget as HTMLButtonElement).style.color = 'var(--color-text-secondary)'
                    }
                  }}
                >
                  {node.company_name}
                </button>
              </span>
            )
          })}

          {/* Children dropdown — always shown at end */}
          {children.length > 0 && (
            <span style={{ display: 'flex', alignItems: 'center', gap: '0.1rem', flexShrink: 0 }} ref={dropdownRef}>
              <span style={sepStyle}>›</span>
              <div style={{ position: 'relative' }}>
                <button
                  onClick={() => setDropdownOpen(o => !o)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.25rem',
                    fontSize: '0.75rem',
                    color: 'var(--color-text-secondary)',
                    background: dropdownOpen ? 'var(--color-chip-hover-bg)' : 'none',
                    border: '1px solid var(--color-border)',
                    borderRadius: 5,
                    padding: '0.15rem 0.5rem',
                    cursor: 'pointer',
                    transition: 'background 0.12s, color 0.12s',
                    whiteSpace: 'nowrap',
                  }}
                  onMouseEnter={e => {
                    if (!dropdownOpen) (e.currentTarget as HTMLButtonElement).style.background = 'var(--color-chip-hover-bg)'
                  }}
                  onMouseLeave={e => {
                    if (!dropdownOpen) (e.currentTarget as HTMLButtonElement).style.background = 'none'
                  }}
                >
                  Select subaccount
                  <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.6 }}>
                    <polyline points="2,3.5 5,6.5 8,3.5" />
                  </svg>
                </button>

                {dropdownOpen && (
                  <div
                    style={{
                      position: 'absolute',
                      top: 'calc(100% + 4px)',
                      left: 0,
                      zIndex: 1000,
                      background: 'var(--color-card)',
                      border: '1px solid var(--color-border)',
                      borderRadius: 8,
                      boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
                      minWidth: 200,
                      maxHeight: 280,
                      overflowY: 'auto',
                      padding: '0.3rem 0',
                    }}
                  >
                    {children.map(child => (
                      <button
                        key={child.client_id}
                        onClick={() => handleChildSelect(child)}
                        style={{
                          display: 'block',
                          width: '100%',
                          textAlign: 'left',
                          padding: '0.45rem 0.875rem',
                          fontSize: '0.8rem',
                          color: 'var(--color-text)',
                          background: 'none',
                          border: 'none',
                          cursor: 'pointer',
                          transition: 'background 0.1s',
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                        }}
                        onMouseEnter={e => {
                          (e.currentTarget as HTMLButtonElement).style.background = 'var(--color-chip-hover-bg)'
                        }}
                        onMouseLeave={e => {
                          (e.currentTarget as HTMLButtonElement).style.background = 'none'
                        }}
                      >
                        {child.company_name}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </span>
          )}
        </>
      )}

      {/* Spacer + DB mode badge */}
      <span style={{ flex: 1 }} />
      {data && (
        <span style={dbBadgeStyle}>{db_mode}</span>
      )}
    </nav>
  )
}
