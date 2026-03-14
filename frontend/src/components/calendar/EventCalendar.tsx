import { useState, useEffect, useCallback, useRef } from 'react'

// ─── Types ────────────────────────────────────────────────────────────────────

interface AiContent {
  count: number
  types: string[]
  source_event_id: number
  client_id: number
  articles?: Record<string, string>
  kt_sections?: Record<string, string>  // summary | takeaways | quote | other
}

interface CalendarEvent {
  event_id: number
  title: string
  abstract: string
  start_time: string | null
  end_time: string | null
  event_type: string
  is_future: boolean
  registrant_count?: number | null
  attendee_count?: number | null
  conversion_rate?: number | null
  avg_engagement_score?: number | null
  poll_response_count?: number | null
  survey_response_count?: number | null
  resource_download_count?: number | null
  ai_content?: AiContent | null
}

interface ProposedEvent {
  title: string
  date: string        // YYYY-MM-DD
  time: string        // HH:MM (24h)
  duration_minutes: number
  funnel_stage?: string
  theme?: string
  topic?: string
}

interface Props {
  isOpen: boolean
  onClose: () => void
  onEventToChat?: (event: CalendarEvent) => void
  proposedMode?: boolean
  proposedEvents?: ProposedEvent[]
}

// ─── Palette ──────────────────────────────────────────────────────────────────

const EVENT_COLORS = ['#4f46e5', '#0ea5e9', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#ec4899']
const PROPOSED_COLOR = '#a78bfa'  // lighter purple for proposed events
function eventColor(id: number) { return id < 0 ? PROPOSED_COLOR : EVENT_COLORS[id % EVENT_COLORS.length] }
function isProposed(ev: CalendarEvent) { return ev.event_id < 0 }

// ─── Helpers ──────────────────────────────────────────────────────────────────

function toLocal(iso: string | null): Date | null {
  if (!iso) return null
  return new Date(iso)
}

function fmtTime(d: Date | null): string {
  if (!d) return ''
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function fmtDate(d: Date | null): string {
  if (!d) return ''
  return d.toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })
}

function sameDay(a: Date, b: Date) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
}

function daysInMonth(year: number, month: number) {
  return new Date(year, month + 1, 0).getDate()
}

// ─── Tooltip (fixed-position, never clipped) ─────────────────────────────────

function Tooltip({ text, children }: { text: string; children: React.ReactNode }) {
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null)
  const ref = useRef<HTMLDivElement>(null)
  return (
    <div
      ref={ref}
      onMouseEnter={e => {
        const r = (e.currentTarget as HTMLElement).getBoundingClientRect()
        setPos({ x: r.left + r.width / 2, y: r.top })
      }}
      onMouseLeave={() => setPos(null)}
      style={{ display: 'contents' }}
    >
      {children}
      {pos && (
        <div style={{
          position: 'fixed',
          left: pos.x,
          top: pos.y - 4,
          transform: 'translate(-50%, -100%)',
          background: 'rgba(15,23,42,0.92)',
          color: '#f1f5f9',
          padding: '5px 10px',
          borderRadius: 6,
          fontSize: '0.7rem',
          lineHeight: 1.4,
          whiteSpace: 'pre-line',
          maxWidth: 300,
          zIndex: 9999,
          pointerEvents: 'none',
          boxShadow: '0 4px 12px rgba(0,0,0,0.25)',
        }}>
          {text}
        </div>
      )}
    </div>
  )
}

// ─── Event Detail Panel ───────────────────────────────────────────────────────

// Article type display names (keys match actual DB source values after AUTOGEN_ strip)
const AI_TYPE_LABELS: Record<string, string> = {
  BLOG: 'Blog',
  EBOOK: 'eBook',
  FAQ: 'FAQ',
  FOLLOWUPEMAI: 'Follow-up Email',
  KEYTAKEAWAYS: 'Key Takeaways',
  SOCIALMEDIAP: 'Social Media Post',
  TRANSCRIPT: 'Transcript',
}
function aiTypeLabel(t: string) {
  return AI_TYPE_LABELS[t] ?? t.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, c => c.toUpperCase())
}

// Section tab order for Key Takeaways (keys match backend _parse_kt_sections output)
const KT_TAB_ORDER = ['summary', 'takeaways', 'quote', 'other'] as const
const KT_TAB_LABELS: Record<string, string> = {
  summary: 'Summary', takeaways: 'Takeaways', quote: 'Quote', other: 'Other (type below)',
}

function KeyTakeawaysTile({ ai }: { ai: AiContent }) {
  const articles = ai.articles ?? {}
  const ktSections = ai.kt_sections ?? {}
  const types = ai.types.filter(t => articles[t])
  const defaultType = types.includes('KEYTAKEAWAYS') ? 'KEYTAKEAWAYS' : (types[0] ?? '')
  const [selectedType, setSelectedType] = useState(defaultType)

  const availableTabs = KT_TAB_ORDER.filter(k => ktSections[k])
  const defaultTab = availableTabs.includes('takeaways') ? 'takeaways' : (availableTabs[0] ?? '')
  const [activeTab, setActiveTab] = useState(defaultTab)

  const prevType = useRef(selectedType)
  if (prevType.current !== selectedType) {
    prevType.current = selectedType
    setActiveTab(availableTabs.includes('takeaways') ? 'takeaways' : (availableTabs[0] ?? ''))
  }

  const MM_SUBTYPE: Record<string, string> = {
    BLOG: 'autogen_blog', EBOOK: 'autogen_ebook', FAQ: 'autogen_faq',
    KEYTAKEAWAYS: 'autogen_keytakeaways', FOLLOWUPEMAI: 'autogen_followupemail',
    SOCIALMEDIAP: 'autogen_socialmediapost', TRANSCRIPT: 'autogen_transcript',
  }
  const subType = MM_SUBTYPE[selectedType] ?? 'autogen_' + selectedType.toLowerCase()
  const mmUrl = `https://wccv.on24.com/webcast/mediamanager?date_range=all&client_ids=${ai.client_id}&types=article&sub_types=${subType}&search=${ai.source_event_id}`
  const content = selectedType === 'KEYTAKEAWAYS'
    ? (ktSections[activeTab] ?? articles['KEYTAKEAWAYS'])
    : articles[selectedType]

  return (
    <div style={{ background: 'var(--color-card)', borderRadius: 10, padding: '0.875rem 1rem', border: '1px solid var(--color-border)' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.6rem' }}>
        <span style={{ fontSize: '0.6rem', color: 'var(--color-text-secondary)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          AI-ACE Content
        </span>
        <a href={mmUrl} target="_blank" rel="noreferrer"
          style={{ fontSize: '0.7rem', fontWeight: 600, color: '#10b981', textDecoration: 'none' }}>
          Media Manager ↗
        </a>
      </div>

      {/* Article type dropdown */}
      <select
        value={selectedType}
        onChange={e => setSelectedType(e.target.value)}
        style={{
          width: '100%', marginBottom: '0.5rem',
          fontSize: '0.75rem', fontWeight: 500,
          padding: '0.3rem 0.5rem', borderRadius: 6,
          border: '1px solid rgba(16,185,129,0.4)',
          background: 'rgba(16,185,129,0.08)', color: '#10b981',
          cursor: 'pointer', outline: 'none',
        }}
      >
        {types.map(t => <option key={t} value={t}>{aiTypeLabel(t)}</option>)}
      </select>

      {/* Section tabs — only for Key Takeaways */}
      {selectedType === 'KEYTAKEAWAYS' && availableTabs.length > 0 && (
        <div style={{
          display: 'flex', borderBottom: '2px solid var(--color-border)',
          marginBottom: '0.6rem', gap: 0,
        }}>
          {availableTabs.map(tab => (
            <button key={tab} onClick={() => setActiveTab(tab)} style={{
              fontSize: '0.7rem', fontWeight: activeTab === tab ? 600 : 400,
              padding: '0.3rem 0.65rem',
              border: 'none', borderBottom: activeTab === tab ? '2px solid #10b981' : '2px solid transparent',
              marginBottom: -2,
              background: 'transparent',
              color: activeTab === tab ? '#10b981' : 'var(--color-text-secondary)',
              cursor: 'pointer', whiteSpace: 'nowrap',
            }}>{KT_TAB_LABELS[tab] ?? tab}</button>
          ))}
        </div>
      )}

      {/* Content — scrollable area */}
      {(() => {
        const html = content
        return html ? (
          <div
            dangerouslySetInnerHTML={{ __html: html }}
            style={{
              maxHeight: 220, overflowY: 'auto',
              background: 'var(--color-bg)', border: '1px solid var(--color-border)',
              borderRadius: 6, padding: '0.625rem 0.75rem',
              fontSize: '0.75rem', color: 'var(--color-text)', lineHeight: 1.6,
            }}
          />
        ) : null
      })()}
    </div>
  )
}

function PerformanceSection({ kpis, loadingDetail, defaultCollapsed }: {
  kpis: { label: string; value: string; icon: string }[]
  loadingDetail: boolean
  defaultCollapsed: boolean
}) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed)
  // Auto-collapse when AI-ACE content loads after initial render
  useEffect(() => { if (defaultCollapsed) setCollapsed(true) }, [defaultCollapsed])
  return (
    <div>
      <button
        onClick={() => setCollapsed(c => !c)}
        style={{
          display: 'flex', alignItems: 'center', gap: '0.3rem',
          background: 'none', border: 'none', cursor: 'pointer', padding: 0,
          marginBottom: collapsed ? 0 : '0.5rem',
        }}
      >
        <span style={{ fontSize: '0.6rem', color: 'var(--color-text-secondary)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Performance {loadingDetail && <span style={{ fontWeight: 400 }}>· loading…</span>}
        </span>
        <svg aria-hidden="true" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="var(--color-text-secondary)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
          style={{ transform: collapsed ? 'rotate(-90deg)' : 'rotate(0deg)', transition: 'transform 0.15s', marginTop: 1 }}>
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>
      {!collapsed && (
        kpis.length > 0 ? (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
            {kpis.map(kpi => (
              <div key={kpi.label} style={{
                background: 'var(--color-card)',
                border: '1px solid var(--color-border)',
                borderRadius: 10, padding: '0.625rem 0.75rem',
                boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
              }}>
                <div style={{ fontSize: '0.65rem', color: 'var(--color-text-secondary)', marginBottom: '0.25rem' }}>
                  {kpi.icon} {kpi.label}
                </div>
                <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--color-text)' }}>
                  {kpi.value}
                </div>
              </div>
            ))}
          </div>
        ) : !loadingDetail ? (
          <p style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', fontStyle: 'italic', margin: 0 }}>
            No performance data available.
          </p>
        ) : null
      )}
    </div>
  )
}

function EventDetail({ event: initial, onClose }: { event: CalendarEvent; onClose: () => void }) {
  const [event, setEvent] = useState<CalendarEvent>(initial)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const color = eventColor(event.event_id)
  const start = toLocal(event.start_time)
  const end = toLocal(event.end_time)

  // Fetch full detail (with poll/survey/resource counts) on mount — skip for proposed events
  useEffect(() => {
    setEvent(initial)
    if (initial.is_future || isProposed(initial)) return
    setLoadingDetail(true)
    fetch(`/api/calendar/event/${initial.event_id}`)
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setEvent(d) })
      .catch(() => {})
      .finally(() => setLoadingDetail(false))
  }, [initial.event_id])

  // KPI tiles — always show registrants + attendees for past events (even if 0)
  const proposed = isProposed(event)
  const kpis: { label: string; value: string; icon: string }[] = []
  if (proposed) {
    // Show proposed event metadata instead of KPIs
    const anyEv = event as any
    if (anyEv._funnel_stage) kpis.push({ label: 'Funnel Stage', value: anyEv._funnel_stage, icon: '🎯' })
    if (anyEv._theme) kpis.push({ label: 'Campaign Theme', value: anyEv._theme, icon: '📣' })
    if (anyEv._topic) kpis.push({ label: 'Topic', value: anyEv._topic, icon: '💡' })
  } else if (!event.is_future) {
    kpis.push({ label: 'Registrants', value: (event.registrant_count ?? 0).toLocaleString(), icon: '👥' })
    kpis.push({ label: 'Attendees', value: (event.attendee_count ?? 0).toLocaleString(), icon: '✅' })
    if (event.conversion_rate) kpis.push({ label: 'Conversion', value: `${event.conversion_rate}%`, icon: '📈' })
    if (event.avg_engagement_score != null) kpis.push({ label: 'Avg Engagement', value: event.avg_engagement_score.toFixed(1), icon: '⚡' })
    if (event.poll_response_count) kpis.push({ label: 'Poll Responses', value: event.poll_response_count.toLocaleString(), icon: '📊' })
    if (event.survey_response_count) kpis.push({ label: 'Survey Responses', value: event.survey_response_count.toLocaleString(), icon: '📋' })
    if (event.resource_download_count) kpis.push({ label: 'Resource Downloads', value: event.resource_download_count.toLocaleString(), icon: '⬇️' })
  }

  return (
    <div style={{
      width: 360, flexShrink: 0,
      borderLeft: '1px solid var(--color-border)',
      background: 'var(--color-bg)',
      display: 'flex', flexDirection: 'column',
      overflow: 'hidden',
    }}>
      {/* Colour bar header */}
      <div style={{ height: 4, background: color, flexShrink: 0 }} />

      {/* Close + type badge */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0.75rem 1rem 0',
      }}>
        <span style={{
          padding: '0.2rem 0.6rem',
          background: color + '20', color,
          borderRadius: 20, fontSize: '0.65rem', fontWeight: 700,
          letterSpacing: '0.03em',
        }}>
          {event.event_type || 'Event'}
        </span>
        <button onClick={onClose} aria-label="Close" style={{
          background: 'none', border: 'none', cursor: 'pointer',
          color: 'var(--color-text-secondary)', fontSize: '1.1rem', lineHeight: 1, padding: 0,
        }}>×</button>
      </div>

      <div style={{ padding: '0.75rem 1rem 1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>

        {/* Title card */}
        <div style={{
          background: 'var(--color-card)', borderRadius: 10,
          padding: '0.875rem 1rem',
          boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
          border: '1px solid var(--color-border)',
        }}>
          <div style={{ fontSize: '0.6rem', color: 'var(--color-text-secondary)', marginBottom: '0.3rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Event ID {event.event_id}
          </div>
          <h3 style={{ fontSize: '0.925rem', fontWeight: 700, color: 'var(--color-text)', margin: '0 0 0.5rem', lineHeight: 1.35 }}>
            {event.title}
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--color-text)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span style={{ opacity: 0.5 }}>📅</span>
              {fmtDate(start)}
            </div>
            {start && (
              <div style={{ fontSize: '0.75rem', color: 'var(--color-text)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <span style={{ opacity: 0.5 }}>🕐</span>
                {fmtTime(start)}{end ? ` – ${fmtTime(end)}` : ''}
              </div>
            )}
          </div>
        </div>

        {/* Abstract card */}
        {event.abstract && (
          <div style={{
            background: 'var(--color-card)', borderRadius: 10,
            padding: '0.875rem 1rem',
            border: '1px solid var(--color-border)',
          }}>
            <div style={{ fontSize: '0.6rem', color: 'var(--color-text-secondary)', marginBottom: '0.4rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Description
            </div>
            <p style={{ fontSize: '0.775rem', color: 'var(--color-text)', lineHeight: 1.6, margin: 0 }}>
              {event.abstract}
            </p>
          </div>
        )}

        {/* Performance KPI grid — collapsed by default when AI-ACE content is present */}
        {!event.is_future && (
          <PerformanceSection
            kpis={kpis}
            loadingDetail={loadingDetail}
            defaultCollapsed={!!(event.ai_content?.articles && Object.keys(event.ai_content.articles).length > 0)}
          />
        )}

        {event.is_future && (
          <div style={{
            background: 'var(--color-card)', borderRadius: 10,
            padding: '0.75rem 1rem', border: '1px solid var(--color-border)',
            fontSize: '0.775rem', color: 'var(--color-text-secondary)', fontStyle: 'italic',
          }}>
            Performance data available after the event concludes.
          </div>
        )}

        {/* AI-ACE Key Takeaways — only shown when article content is available */}
        {event.ai_content?.articles && Object.keys(event.ai_content.articles).length > 0 && (
          <KeyTakeawaysTile ai={event.ai_content} />
        )}

      </div>
    </div>
  )
}

// ─── Month View ───────────────────────────────────────────────────────────────

function MonthView({
  year, month, events, onSelectEvent, onDoubleClickEvent,
}: {
  year: number; month: number; events: CalendarEvent[]; onSelectEvent: (e: CalendarEvent) => void; onDoubleClickEvent?: (e: CalendarEvent) => void
}) {
  const today = new Date()
  const firstDay = new Date(year, month, 1).getDay() // 0=Sun
  const totalDays = daysInMonth(year, month)
  const cells: (number | null)[] = [
    ...Array(firstDay).fill(null),
    ...Array.from({ length: totalDays }, (_, i) => i + 1),
  ]
  // Pad to full weeks
  while (cells.length % 7 !== 0) cells.push(null)

  const eventsForDay = (day: number) => events.filter(e => {
    const d = toLocal(e.start_time)
    return d && d.getFullYear() === year && d.getMonth() === month && d.getDate() === day
  })

  const DAY_LABELS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

  const totalRows = Math.ceil(cells.length / 7)

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Day headers */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7,1fr)', borderBottom: '1px solid var(--color-border)', flexShrink: 0 }}>
        {DAY_LABELS.map(d => (
          <div key={d} style={{
            padding: '0.25rem 0', textAlign: 'center',
            fontSize: '0.65rem', fontWeight: 600, color: 'var(--color-text-secondary)',
          }}>{d}</div>
        ))}
      </div>

      {/* Calendar grid — fills available space, no scroll */}
      <div style={{
        flex: 1, display: 'grid',
        gridTemplateColumns: 'repeat(7,1fr)',
        gridTemplateRows: `repeat(${totalRows}, 1fr)`,
      }}>
        {cells.map((day, idx) => {
          const isToday = day !== null && today.getFullYear() === year && today.getMonth() === month && today.getDate() === day
          const dayEvents = day !== null ? eventsForDay(day) : []
          const maxPills = totalRows > 5 ? 2 : 3
          return (
            <div key={idx} style={{
              borderRight: (idx + 1) % 7 === 0 ? 'none' : '1px solid var(--color-border)',
              borderBottom: '1px solid var(--color-border)',
              padding: '2px 3px',
              background: day === null ? 'var(--color-bg)' : 'var(--color-card)',
              overflow: 'hidden',
            }}>
              {day !== null && (
                <>
                  <div style={{
                    fontSize: '0.7rem', fontWeight: isToday ? 700 : 400,
                    color: isToday ? '#fff' : 'var(--color-text)',
                    background: isToday ? 'var(--color-primary)' : 'transparent',
                    width: 20, height: 20, borderRadius: '50%',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    marginBottom: '1px',
                  }}>{day}</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 1, overflow: 'hidden' }}>
                    {dayEvents.slice(0, maxPills).map(ev => {
                      const t = fmtTime(toLocal(ev.start_time))
                      const proposed = isProposed(ev)
                      const tooltipText = `${proposed ? '[PROPOSED] ' : ''}${ev.title}\n${t}${ev.event_type ? ' · ' + ev.event_type : ''}`
                      return (
                        <Tooltip key={ev.event_id} text={tooltipText}>
                          <button onClick={() => onSelectEvent(ev)} onDoubleClick={() => onDoubleClickEvent?.(ev)}
                            style={{
                              display: 'block', width: '100%', textAlign: 'left',
                              padding: '0px 3px', borderRadius: 3,
                              background: proposed ? 'transparent' : eventColor(ev.event_id),
                              color: proposed ? PROPOSED_COLOR : '#fff',
                              fontSize: '0.6rem', fontWeight: 500,
                              border: proposed ? `1.5px dashed ${PROPOSED_COLOR}` : 'none',
                              cursor: 'pointer',
                              overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis',
                              lineHeight: 1.4,
                            }}
                          >
                            {t} {ev.title}
                          </button>
                        </Tooltip>
                      )
                    })}
                    {dayEvents.length > maxPills && (
                      <Tooltip text={dayEvents.slice(maxPills).map(e => e.title).join('\n')}>
                        <span
                          style={{ fontSize: '0.55rem', color: 'var(--color-text-secondary)', paddingLeft: 2, cursor: 'default' }}
                        >
                          +{dayEvents.length - maxPills} more…
                        </span>
                      </Tooltip>
                    )}
                  </div>
                </>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ─── Week View ────────────────────────────────────────────────────────────────

function WeekView({
  weekStart, events, onSelectEvent, onDoubleClickEvent,
}: {
  weekStart: Date; events: CalendarEvent[]; onSelectEvent: (e: CalendarEvent) => void; onDoubleClickEvent?: (e: CalendarEvent) => void
}) {
  const HOUR_START = 7
  const HOUR_END = 21
  const HOURS = Array.from({ length: HOUR_END - HOUR_START }, (_, i) => HOUR_START + i)
  const CELL_HEIGHT = 52 // px per hour

  const days = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(weekStart)
    d.setDate(weekStart.getDate() + i)
    return d
  })

  const today = new Date()
  const DAY_LABELS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

  const eventsForDay = (day: Date) => events.filter(e => {
    const d = toLocal(e.start_time)
    return d && sameDay(d, day)
  })

  function eventTop(e: CalendarEvent): number {
    const d = toLocal(e.start_time)
    if (!d) return 0
    return ((d.getHours() + d.getMinutes() / 60) - HOUR_START) * CELL_HEIGHT
  }

  function eventHeight(e: CalendarEvent): number {
    const s = toLocal(e.start_time)
    const t = toLocal(e.end_time)
    if (!s || !t) return CELL_HEIGHT * 0.5
    const dur = (t.getTime() - s.getTime()) / 3600000
    return Math.max(CELL_HEIGHT * Math.min(dur, HOUR_END - HOUR_START), 20)
  }

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Day headers */}
      <div style={{ display: 'grid', gridTemplateColumns: '48px repeat(7,1fr)', borderBottom: '1px solid var(--color-border)', flexShrink: 0 }}>
        <div />
        {days.map((day, i) => {
          const isToday = sameDay(day, today)
          return (
            <div key={i} style={{ textAlign: 'center', padding: '0.375rem 0' }}>
              <div style={{ fontSize: '0.65rem', fontWeight: 600, color: isToday ? 'var(--color-primary)' : 'var(--color-text-secondary)' }}>
                {DAY_LABELS[day.getDay()]}
              </div>
              <div style={{
                fontSize: '1.1rem', fontWeight: 700,
                color: isToday ? '#fff' : 'var(--color-text)',
                background: isToday ? 'var(--color-primary)' : 'transparent',
                width: 32, height: 32, borderRadius: '50%',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                margin: '0 auto',
              }}>{day.getDate()}</div>
            </div>
          )
        })}
      </div>

      {/* Time grid */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '48px repeat(7,1fr)', position: 'relative' }}>
          {/* Hour rows */}
          {HOURS.map(h => (
            <>
              <div key={`h${h}`} style={{
                height: CELL_HEIGHT, borderBottom: '1px solid var(--color-border)',
                fontSize: '0.6rem', color: 'var(--color-text-secondary)',
                paddingTop: '2px', paddingRight: '6px', textAlign: 'right',
                flexShrink: 0,
              }}>
                {h === 12 ? '12 PM' : h > 12 ? `${h - 12} PM` : `${h} AM`}
              </div>
              {days.map((_, di) => (
                <div key={`c${h}-${di}`} style={{
                  height: CELL_HEIGHT,
                  borderBottom: '1px solid var(--color-border)',
                  borderLeft: '1px solid var(--color-border)',
                }} />
              ))}
            </>
          ))}

          {/* Event blocks — overlaid per column */}
          {days.map((day, di) => {
            const dayEvs = eventsForDay(day)
            if (!dayEvs.length) return null
            return (
              <div key={`evs${di}`} style={{
                position: 'absolute',
                top: 0,
                left: `calc(48px + ${di} * (100% - 48px) / 7)`,
                width: `calc((100% - 48px) / 7)`,
                height: HOURS.length * CELL_HEIGHT,
                pointerEvents: 'none',
              }}>
                {dayEvs.map(ev => {
                  const proposed = isProposed(ev)
                  return (
                  <Tooltip key={ev.event_id} text={`${proposed ? '[PROPOSED] ' : ''}${ev.title}\n${fmtTime(toLocal(ev.start_time))}${ev.event_type ? ' · ' + ev.event_type : ''}`}>
                  <button
                    onClick={() => onSelectEvent(ev)}
                    onDoubleClick={() => onDoubleClickEvent?.(ev)}
                    style={{
                      position: 'absolute',
                      top: eventTop(ev),
                      left: 2, right: 2,
                      height: eventHeight(ev),
                      background: proposed ? 'rgba(167, 139, 250, 0.1)' : eventColor(ev.event_id),
                      color: proposed ? PROPOSED_COLOR : '#fff',
                      fontSize: '0.65rem', fontWeight: 500,
                      borderRadius: 4, padding: '3px 5px',
                      border: proposed ? `1.5px dashed ${PROPOSED_COLOR}` : 'none',
                      cursor: 'pointer', pointerEvents: 'auto',
                      textAlign: 'left', overflow: 'hidden',
                    }}
                  >
                    {proposed && <div style={{ fontSize: '0.5rem', textTransform: 'uppercase', opacity: 0.7, letterSpacing: '0.5px' }}>Proposed</div>}
                    <div style={{ fontSize: '0.6rem', opacity: 0.85, flexShrink: 0 }}>
                      {fmtTime(toLocal(ev.start_time))}
                    </div>
                    <div style={{ fontWeight: 600, lineHeight: 1.3, overflow: 'hidden', wordBreak: 'break-word' }}>
                      {ev.title}
                    </div>
                  </button>
                  </Tooltip>
                  )
                })}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

// ─── Day View ────────────────────────────────────────────────────────────────

function DayView({
  date, events, onSelectEvent, onDoubleClickEvent,
}: {
  date: Date; events: CalendarEvent[]; onSelectEvent: (e: CalendarEvent) => void; onDoubleClickEvent?: (e: CalendarEvent) => void
}) {
  const HOUR_START = 7
  const HOUR_END = 21
  const HOURS = Array.from({ length: HOUR_END - HOUR_START }, (_, i) => HOUR_START + i)
  const CELL_HEIGHT = 60

  function eventTop(e: CalendarEvent): number {
    const d = toLocal(e.start_time)
    if (!d) return 0
    return ((d.getHours() + d.getMinutes() / 60) - HOUR_START) * CELL_HEIGHT
  }

  function eventHeight(e: CalendarEvent): number {
    const s = toLocal(e.start_time)
    const t = toLocal(e.end_time)
    if (!s || !t) return CELL_HEIGHT * 0.75
    const dur = (t.getTime() - s.getTime()) / 3600000
    return Math.max(CELL_HEIGHT * Math.min(dur, HOUR_END - HOUR_START), 28)
  }

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Day header */}
      <div style={{
        padding: '0.5rem 1rem', borderBottom: '1px solid var(--color-border)', flexShrink: 0,
        fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-text)',
      }}>
        {fmtDate(date)} — {events.length} event{events.length !== 1 ? 's' : ''}
      </div>

      {/* Time grid */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '56px 1fr', position: 'relative', minHeight: HOURS.length * CELL_HEIGHT }}>
          {/* Hour labels + rows */}
          {HOURS.map(h => (
            <div key={`h${h}`} style={{ display: 'contents' }}>
              <div style={{
                height: CELL_HEIGHT, borderBottom: '1px solid var(--color-border)',
                fontSize: '0.7rem', color: 'var(--color-text-secondary)',
                paddingTop: '2px', paddingRight: '8px', textAlign: 'right',
              }}>
                {h === 12 ? '12 PM' : h > 12 ? `${h - 12} PM` : `${h} AM`}
              </div>
              <div style={{
                height: CELL_HEIGHT,
                borderBottom: '1px solid var(--color-border)',
                borderLeft: '1px solid var(--color-border)',
              }} />
            </div>
          ))}

          {/* Event blocks */}
          <div style={{
            position: 'absolute', top: 0, left: 56, right: 0,
            height: HOURS.length * CELL_HEIGHT,
            pointerEvents: 'none',
          }}>
            {events.map(ev => {
              const proposed = isProposed(ev)
              return (
              <Tooltip key={ev.event_id} text={`${proposed ? '[PROPOSED] ' : ''}${ev.title}\n${fmtTime(toLocal(ev.start_time))}${ev.event_type ? ' · ' + ev.event_type : ''}`}>
                <button
                  onClick={() => onSelectEvent(ev)}
                  onDoubleClick={() => onDoubleClickEvent?.(ev)}
                  style={{
                    position: 'absolute',
                    top: eventTop(ev),
                    left: 4, right: 4,
                    height: eventHeight(ev),
                    background: proposed ? 'rgba(167, 139, 250, 0.1)' : eventColor(ev.event_id),
                    color: proposed ? PROPOSED_COLOR : '#fff',
                    fontSize: '0.8rem', fontWeight: 500,
                    borderRadius: 6, padding: '4px 10px',
                    border: proposed ? `1.5px dashed ${PROPOSED_COLOR}` : 'none',
                    cursor: 'pointer', pointerEvents: 'auto',
                    textAlign: 'left', overflow: 'hidden',
                  }}
                >
                  {proposed && <div style={{ fontSize: '0.6rem', textTransform: 'uppercase', opacity: 0.7, letterSpacing: '0.5px' }}>Proposed</div>}
                  <div style={{ fontSize: '0.7rem', opacity: 0.85, marginBottom: 2 }}>
                    {fmtTime(toLocal(ev.start_time))}{toLocal(ev.end_time) ? ` – ${fmtTime(toLocal(ev.end_time))}` : ''}
                    {ev.event_type ? ` · ${ev.event_type}` : ''}
                  </div>
                  <div style={{ fontWeight: 700, lineHeight: 1.35, wordBreak: 'break-word' }}>
                    {ev.title}
                  </div>
                </button>
              </Tooltip>
              )})}

          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Main Calendar ────────────────────────────────────────────────────────────

export default function EventCalendar({ isOpen, onClose, onEventToChat, proposedMode = false, proposedEvents = [] }: Props) {
  const today = new Date()
  const [view, setView] = useState<'month' | 'week' | 'day'>('month')
  const [dayDate, setDayDate] = useState(today)
  const [year, setYear] = useState(today.getFullYear())
  const [month, setMonth] = useState(today.getMonth())          // 0-indexed
  const [weekStart, setWeekStart] = useState(() => {
    const d = new Date(today)
    d.setDate(today.getDate() - today.getDay())
    d.setHours(0, 0, 0, 0)
    return d
  })
  const [events, setEvents] = useState<CalendarEvent[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null)
  const [showExistingEvents, setShowExistingEvents] = useState(false)

  const fetchEvents = useCallback(async (y: number, m: number) => {
    setLoading(true)
    try {
      const res = await fetch(`/api/calendar?year=${y}&month=${m + 1}`)
      if (res.ok) setEvents(await res.json())
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }, [])

  // Reset to today + toggle off whenever modal opens
  useEffect(() => {
    if (isOpen) {
      const d = new Date()
      setYear(d.getFullYear())
      setMonth(d.getMonth())
      setDayDate(d)
      const ws = new Date(d)
      ws.setDate(d.getDate() - d.getDay())
      ws.setHours(0, 0, 0, 0)
      setWeekStart(ws)
      setShowExistingEvents(false)
    }
  }, [isOpen])

  // Fetch when month changes or modal opens
  useEffect(() => {
    if (isOpen) fetchEvents(year, month)
  }, [isOpen, year, month, fetchEvents])

  // Also fetch adjacent month when in week view near month boundary
  useEffect(() => {
    if (isOpen && view === 'week') {
      const wEnd = new Date(weekStart)
      wEnd.setDate(weekStart.getDate() + 6)
      if (wEnd.getMonth() !== weekStart.getMonth()) {
        fetchEvents(wEnd.getFullYear(), wEnd.getMonth())
      }
    }
  }, [isOpen, view, weekStart, fetchEvents])

  const goToToday = () => {
    const d = new Date()
    setYear(d.getFullYear())
    setMonth(d.getMonth())
    setDayDate(d)
    const ws = new Date(d)
    ws.setDate(d.getDate() - d.getDay())
    ws.setHours(0, 0, 0, 0)
    setWeekStart(ws)
  }

  // In proposed mode, back navigation is blocked at the current period
  const canGoPrev = !proposedMode || (() => {
    const t = new Date()
    if (view === 'month') return year > t.getFullYear() || (year === t.getFullYear() && month > t.getMonth())
    if (view === 'week') { const prevWeek = new Date(weekStart); prevWeek.setDate(prevWeek.getDate() - 7); return prevWeek >= new Date(t.getFullYear(), t.getMonth(), t.getDate() - t.getDay()) }
    return dayDate > t
  })()

  const navigatePrev = () => {
    if (!canGoPrev) return
    if (view === 'month') {
      if (month === 0) { setYear(y => y - 1); setMonth(11) }
      else setMonth(m => m - 1)
    } else if (view === 'week') {
      setWeekStart(w => { const d = new Date(w); d.setDate(d.getDate() - 7); return d })
    } else {
      setDayDate(d => { const n = new Date(d); n.setDate(n.getDate() - 1); return n })
    }
  }

  const navigateNext = () => {
    if (view === 'month') {
      if (month === 11) { setYear(y => y + 1); setMonth(0) }
      else setMonth(m => m + 1)
    } else if (view === 'week') {
      setWeekStart(w => { const d = new Date(w); d.setDate(d.getDate() + 7); return d })
    } else {
      setDayDate(d => { const n = new Date(d); n.setDate(n.getDate() + 1); return n })
    }
  }

  const VIEWS: ('month' | 'week' | 'day')[] = ['month', 'week', 'day']
  const zoomIn = () => {
    const idx = VIEWS.indexOf(view)
    if (idx < VIEWS.length - 1) setView(VIEWS[idx + 1])
  }
  const zoomOut = () => {
    const idx = VIEWS.indexOf(view)
    if (idx > 0) setView(VIEWS[idx - 1])
  }

  const MONTH_NAMES = ['January','February','March','April','May','June','July','August','September','October','November','December']

  const headerLabel = view === 'month'
    ? `${MONTH_NAMES[month]} ${year}`
    : view === 'day'
    ? fmtDate(dayDate)
    : (() => {
        const wEnd = new Date(weekStart); wEnd.setDate(weekStart.getDate() + 6)
        if (weekStart.getMonth() === wEnd.getMonth())
          return `${MONTH_NAMES[weekStart.getMonth()]} ${weekStart.getDate()}–${wEnd.getDate()}, ${weekStart.getFullYear()}`
        return `${MONTH_NAMES[weekStart.getMonth()]} ${weekStart.getDate()} – ${MONTH_NAMES[wEnd.getMonth()]} ${wEnd.getDate()}, ${wEnd.getFullYear()}`
      })()

  // Sync month/year when day view changes month
  useEffect(() => {
    if (view === 'day' && (dayDate.getMonth() !== month || dayDate.getFullYear() !== year)) {
      setMonth(dayDate.getMonth())
      setYear(dayDate.getFullYear())
    }
  }, [view, dayDate])

  // Convert proposed events to CalendarEvent format with negative IDs (to distinguish)
  const proposedAsCalendar: CalendarEvent[] = proposedEvents.map((pe, i) => ({
    event_id: -(i + 1),  // negative IDs = proposed
    title: pe.title,
    abstract: '',
    start_time: `${pe.date}T${pe.time}:00`,
    end_time: (() => {
      const d = new Date(`${pe.date}T${pe.time}:00`)
      d.setMinutes(d.getMinutes() + (pe.duration_minutes || 60))
      return d.toISOString()
    })(),
    event_type: pe.funnel_stage || 'Proposed',
    is_future: true,
    _proposed: true,
    _funnel_stage: pe.funnel_stage,
    _theme: pe.theme,
    _topic: pe.topic,
  } as CalendarEvent & { _proposed?: boolean; _funnel_stage?: string; _theme?: string; _topic?: string }))

  // In proposed mode: show proposed events + optionally existing future events
  const visibleEvents = proposedMode
    ? [
        ...proposedAsCalendar,
        ...(showExistingEvents ? events.filter(e => { const d = toLocal(e.start_time); return d ? d >= today : true }) : []),
      ]
    : events

  // Filter events for current view
  const filteredEvents = view === 'week' ? visibleEvents.filter(e => {
    const d = toLocal(e.start_time)
    if (!d) return false
    const wEnd = new Date(weekStart); wEnd.setDate(weekStart.getDate() + 7)
    return d >= weekStart && d < wEnd
  }) : view === 'day' ? visibleEvents.filter(e => {
    const d = toLocal(e.start_time)
    return d ? sameDay(d, dayDate) : false
  }) : visibleEvents

  if (!isOpen) return null

  return (
    <div className="calendar-modal-overlay" style={{
      position: 'fixed', inset: 0, zIndex: 1000,
      background: 'rgba(0,0,0,0.5)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }} onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div style={{
        width: '96vw', maxWidth: 1600,
        height: '95vh',
        background: 'var(--color-card)',
        borderRadius: 12,
        boxShadow: '0 24px 48px rgba(0,0,0,0.2)',
        display: 'flex', flexDirection: 'column',
        overflow: 'hidden',
      }}>
        {/* ── Toolbar ── */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: '0.75rem',
          padding: '0.75rem 1.25rem',
          borderBottom: '1px solid var(--color-border)',
          flexShrink: 0,
        }}>
          {/* Zoom out / in */}
          <button onClick={zoomOut} aria-label="Zoom out" disabled={view === 'month'} style={{ ...navBtnStyle, opacity: view === 'month' ? 0.3 : 1 }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><line x1="5" y1="12" x2="19" y2="12"/></svg>
          </button>
          {/* View toggle */}
          <div style={{ display: 'flex', background: 'var(--color-bg)', borderRadius: 6, padding: 2 }}>
            {(['month', 'week', 'day'] as const).map(v => (
              <button key={v} onClick={() => setView(v)} style={{
                padding: '0.25rem 0.75rem', fontSize: '0.775rem', fontWeight: 500,
                borderRadius: 4, border: 'none', cursor: 'pointer',
                background: view === v ? 'var(--color-card)' : 'transparent',
                color: view === v ? 'var(--color-text)' : 'var(--color-text-secondary)',
                boxShadow: view === v ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
                textTransform: 'capitalize',
              }}>{v}</button>
            ))}
          </div>
          <button onClick={zoomIn} aria-label="Zoom in" disabled={view === 'day'} style={{ ...navBtnStyle, opacity: view === 'day' ? 0.3 : 1 }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          </button>

          {/* Navigation */}
          <button onClick={navigatePrev} aria-label="Previous" disabled={!canGoPrev} style={{ ...navBtnStyle, opacity: canGoPrev ? 1 : 0.25, cursor: canGoPrev ? 'pointer' : 'default' }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M15 18l-6-6 6-6"/></svg>
          </button>
          <button onClick={navigateNext} aria-label="Next" style={navBtnStyle}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M9 18l6-6-6-6"/></svg>
          </button>

          <span style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--color-text)', minWidth: 200 }}>
            {headerLabel}
          </span>

          <button onClick={goToToday} style={{
            padding: '0.25rem 0.75rem', fontSize: '0.775rem',
            background: 'transparent', border: '1px solid var(--color-border)',
            borderRadius: 6, cursor: 'pointer', color: 'var(--color-text)',
          }}>Today</button>

          {loading && <span style={{ fontSize: '0.7rem', color: 'var(--color-text-secondary)' }}>Loading…</span>}

          <div style={{ flex: 1 }} />

          {proposedMode && (
            <>
              <span style={{ fontSize: '0.72rem', fontWeight: 600, color: '#8b5cf6', background: 'rgba(139,92,246,0.1)', padding: '0.2rem 0.6rem', borderRadius: 4 }}>
                Proposed Calendar{proposedEvents.length > 0 ? ` (${proposedEvents.length} events)` : ''}
              </span>
              <button
                onClick={() => setShowExistingEvents(v => !v)}
                aria-pressed={showExistingEvents}
                style={{
                  display: 'flex', alignItems: 'center', gap: '0.4rem',
                  padding: '0.25rem 0.75rem', fontSize: '0.775rem',
                  background: showExistingEvents ? 'rgba(139,92,246,0.15)' : 'transparent',
                  border: `1px solid ${showExistingEvents ? '#8b5cf6' : 'var(--color-border)'}`,
                  borderRadius: 6, cursor: 'pointer',
                  color: showExistingEvents ? '#8b5cf6' : 'var(--color-text-secondary)',
                }}
              >
                <span style={{
                  width: 28, height: 16, borderRadius: 8, display: 'inline-flex', alignItems: 'center',
                  background: showExistingEvents ? '#8b5cf6' : 'var(--color-border)',
                  transition: 'background 0.15s', flexShrink: 0,
                }}>
                  <span style={{
                    width: 12, height: 12, borderRadius: '50%', background: '#fff',
                    marginLeft: showExistingEvents ? 14 : 2, transition: 'margin 0.15s',
                  }} />
                </span>
                Show existing events
              </button>
            </>
          )}

          <button onClick={() => {
            const style = document.createElement('style')
            style.id = 'calendar-print-style'
            style.textContent = `@media print {
              body > * { display: none !important; visibility: hidden !important; }
              body > .calendar-modal-overlay,
              body > .calendar-modal-overlay * { display: block !important; visibility: visible !important; }
              .calendar-modal-overlay { position: static !important; background: white !important; inset: auto !important; z-index: auto !important; display: block !important; }
              .calendar-modal-overlay > div { position: static !important; width: 100% !important; height: auto !important; max-height: none !important; max-width: none !important; box-shadow: none !important; border: none !important; overflow: visible !important; border-radius: 0 !important; }
              .calendar-print-hide { display: none !important; }
              * { color-adjust: exact !important; -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
            }`
            document.head.appendChild(style)
            const cleanup = () => document.getElementById('calendar-print-style')?.remove()
            window.addEventListener('afterprint', cleanup, { once: true })
            requestAnimationFrame(() => window.print())
          }} aria-label="Print calendar" style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--color-text-secondary)', fontSize: '1rem', lineHeight: 1, padding: '0.2rem',
          }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 9V2h12v7"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/></svg>
          </button>
          <button onClick={onClose} aria-label="Close calendar" className="calendar-print-hide" style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--color-text-secondary)', fontSize: '1.25rem', lineHeight: 1,
          }}>×</button>
        </div>

        {/* ── Body ── */}
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
          {view === 'month'
            ? <MonthView year={year} month={month} events={filteredEvents} onSelectEvent={setSelectedEvent} onDoubleClickEvent={onEventToChat} />
            : view === 'week'
            ? <WeekView weekStart={weekStart} events={filteredEvents} onSelectEvent={setSelectedEvent} onDoubleClickEvent={onEventToChat} />
            : <DayView date={dayDate} events={filteredEvents} onSelectEvent={setSelectedEvent} onDoubleClickEvent={onEventToChat} />
          }

          {selectedEvent && (
            <EventDetail event={selectedEvent} onClose={() => setSelectedEvent(null)} />
          )}
        </div>
      </div>
    </div>
  )
}

const navBtnStyle: React.CSSProperties = {
  width: 28, height: 28, display: 'flex', alignItems: 'center', justifyContent: 'center',
  background: 'var(--color-bg)', border: '1px solid var(--color-border)',
  borderRadius: 6, cursor: 'pointer', color: 'var(--color-text)',
}
