import { useState, useEffect, useCallback } from 'react'

// ─── Types ────────────────────────────────────────────────────────────────────

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
  poll_response_count?: number | null
  survey_response_count?: number | null
  resource_download_count?: number | null
}

interface Props {
  isOpen: boolean
  onClose: () => void
}

// ─── Palette ──────────────────────────────────────────────────────────────────

const EVENT_COLORS = ['#4f46e5', '#0ea5e9', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#ec4899']
function eventColor(id: number) { return EVENT_COLORS[id % EVENT_COLORS.length] }

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

// ─── Event Detail Panel ───────────────────────────────────────────────────────

function EventDetail({ event: initial, onClose }: { event: CalendarEvent; onClose: () => void }) {
  const [event, setEvent] = useState<CalendarEvent>(initial)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const color = eventColor(event.event_id)
  const start = toLocal(event.start_time)
  const end = toLocal(event.end_time)

  // Fetch full detail (with poll/survey/resource counts) on mount
  useEffect(() => {
    setEvent(initial)
    if (initial.is_future) return
    setLoadingDetail(true)
    fetch(`/api/calendar/event/${initial.event_id}`)
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setEvent(d) })
      .catch(() => {})
      .finally(() => setLoadingDetail(false))
  }, [initial.event_id])

  // KPI tiles — only show non-zero, non-null values for past events
  const kpis: { label: string; value: string; icon: string }[] = []
  if (!event.is_future) {
    if (event.registrant_count) kpis.push({ label: 'Registrants', value: event.registrant_count.toLocaleString(), icon: '👥' })
    if (event.attendee_count) kpis.push({ label: 'Attendees', value: event.attendee_count.toLocaleString(), icon: '✅' })
    if (event.conversion_rate) kpis.push({ label: 'Conversion', value: `${event.conversion_rate}%`, icon: '📈' })
    if (event.poll_response_count) kpis.push({ label: 'Poll Responses', value: event.poll_response_count.toLocaleString(), icon: '📊' })
    if (event.survey_response_count) kpis.push({ label: 'Survey Responses', value: event.survey_response_count.toLocaleString(), icon: '📋' })
    if (event.resource_download_count) kpis.push({ label: 'Resource Downloads', value: event.resource_download_count.toLocaleString(), icon: '⬇️' })
  }

  return (
    <div style={{
      width: 340, flexShrink: 0,
      borderLeft: '1px solid var(--color-border)',
      background: 'var(--color-bg)',
      display: 'flex', flexDirection: 'column',
      overflow: 'auto',
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

        {/* Performance KPI grid */}
        {!event.is_future && (
          <div>
            <div style={{ fontSize: '0.6rem', color: 'var(--color-text-secondary)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>
              Performance {loadingDetail && <span style={{ fontWeight: 400 }}>· loading…</span>}
            </div>
            {kpis.length > 0 ? (
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
            ) : null}
          </div>
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
      </div>
    </div>
  )
}

// ─── Month View ───────────────────────────────────────────────────────────────

function MonthView({
  year, month, events, onSelectEvent,
}: {
  year: number; month: number; events: CalendarEvent[]; onSelectEvent: (e: CalendarEvent) => void
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

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Day headers */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7,1fr)', borderBottom: '1px solid var(--color-border)' }}>
        {DAY_LABELS.map(d => (
          <div key={d} style={{
            padding: '0.375rem 0', textAlign: 'center',
            fontSize: '0.7rem', fontWeight: 600, color: 'var(--color-text-secondary)',
          }}>{d}</div>
        ))}
      </div>

      {/* Calendar grid */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7,1fr)', gridAutoRows: 'minmax(100px, 1fr)' }}>
          {cells.map((day, idx) => {
            const isToday = day !== null && today.getFullYear() === year && today.getMonth() === month && today.getDate() === day
            const dayEvents = day !== null ? eventsForDay(day) : []
            return (
              <div key={idx} style={{
                borderRight: (idx + 1) % 7 === 0 ? 'none' : '1px solid var(--color-border)',
                borderBottom: '1px solid var(--color-border)',
                padding: '0.25rem',
                background: day === null ? 'var(--color-bg)' : 'var(--color-card)',
                minHeight: 100,
              }}>
                {day !== null && (
                  <>
                    <div style={{
                      fontSize: '0.75rem', fontWeight: isToday ? 700 : 400,
                      color: isToday ? '#fff' : 'var(--color-text)',
                      background: isToday ? 'var(--color-primary)' : 'transparent',
                      width: 22, height: 22, borderRadius: '50%',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      marginBottom: '0.2rem',
                    }}>{day}</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                      {dayEvents.slice(0, 3).map(ev => (
                        <button key={ev.event_id} onClick={() => onSelectEvent(ev)}
                          title={ev.title}
                          style={{
                            display: 'block', width: '100%', textAlign: 'left',
                            padding: '1px 4px', borderRadius: 3,
                            background: eventColor(ev.event_id),
                            color: '#fff', fontSize: '0.65rem', fontWeight: 500,
                            border: 'none', cursor: 'pointer',
                            overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis',
                            lineHeight: 1.5,
                          }}
                        >
                          {fmtTime(toLocal(ev.start_time))} {ev.title}
                        </button>
                      ))}
                      {dayEvents.length > 3 && (
                        <span style={{ fontSize: '0.6rem', color: 'var(--color-text-secondary)', paddingLeft: 4 }}>
                          +{dayEvents.length - 3} more
                        </span>
                      )}
                    </div>
                  </>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

// ─── Week View ────────────────────────────────────────────────────────────────

function WeekView({
  weekStart, events, onSelectEvent,
}: {
  weekStart: Date; events: CalendarEvent[]; onSelectEvent: (e: CalendarEvent) => void
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
                {dayEvs.map(ev => (
                  <button
                    key={ev.event_id}
                    onClick={() => onSelectEvent(ev)}
                    title={ev.title}
                    style={{
                      position: 'absolute',
                      top: eventTop(ev),
                      left: 2, right: 2,
                      height: eventHeight(ev),
                      background: eventColor(ev.event_id),
                      color: '#fff', fontSize: '0.65rem', fontWeight: 500,
                      borderRadius: 4, padding: '2px 5px',
                      border: 'none', cursor: 'pointer', pointerEvents: 'auto',
                      textAlign: 'left', overflow: 'hidden',
                      display: 'flex', flexDirection: 'column', gap: 1,
                    }}
                  >
                    <span style={{ fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {ev.title}
                    </span>
                    <span style={{ opacity: 0.85, fontSize: '0.6rem' }}>
                      {fmtTime(toLocal(ev.start_time))}
                    </span>
                  </button>
                ))}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

// ─── Main Calendar ────────────────────────────────────────────────────────────

export default function EventCalendar({ isOpen, onClose }: Props) {
  const today = new Date()
  const [view, setView] = useState<'month' | 'week'>('month')
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

  const fetchEvents = useCallback(async (y: number, m: number) => {
    setLoading(true)
    try {
      const res = await fetch(`/api/calendar?year=${y}&month=${m + 1}`)
      if (res.ok) setEvents(await res.json())
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }, [])

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
    const ws = new Date(d)
    ws.setDate(d.getDate() - d.getDay())
    ws.setHours(0, 0, 0, 0)
    setWeekStart(ws)
  }

  const navigatePrev = () => {
    if (view === 'month') {
      if (month === 0) { setYear(y => y - 1); setMonth(11) }
      else setMonth(m => m - 1)
    } else {
      setWeekStart(w => { const d = new Date(w); d.setDate(d.getDate() - 7); return d })
    }
  }

  const navigateNext = () => {
    if (view === 'month') {
      if (month === 11) { setYear(y => y + 1); setMonth(0) }
      else setMonth(m => m + 1)
    } else {
      setWeekStart(w => { const d = new Date(w); d.setDate(d.getDate() + 7); return d })
    }
  }

  const MONTH_NAMES = ['January','February','March','April','May','June','July','August','September','October','November','December']

  const headerLabel = view === 'month'
    ? `${MONTH_NAMES[month]} ${year}`
    : (() => {
        const wEnd = new Date(weekStart); wEnd.setDate(weekStart.getDate() + 6)
        if (weekStart.getMonth() === wEnd.getMonth())
          return `${MONTH_NAMES[weekStart.getMonth()]} ${weekStart.getDate()}–${wEnd.getDate()}, ${weekStart.getFullYear()}`
        return `${MONTH_NAMES[weekStart.getMonth()]} ${weekStart.getDate()} – ${MONTH_NAMES[wEnd.getMonth()]} ${wEnd.getDate()}, ${wEnd.getFullYear()}`
      })()

  // Filter events for week view
  const weekEvents = view === 'week' ? events.filter(e => {
    const d = toLocal(e.start_time)
    if (!d) return false
    const wEnd = new Date(weekStart); wEnd.setDate(weekStart.getDate() + 7)
    return d >= weekStart && d < wEnd
  }) : events

  if (!isOpen) return null

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1000,
      background: 'rgba(0,0,0,0.5)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }} onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div style={{
        width: '92vw', maxWidth: 1200,
        height: '90vh',
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
          {/* View toggle */}
          <div style={{ display: 'flex', background: 'var(--color-bg)', borderRadius: 6, padding: 2 }}>
            {(['month', 'week'] as const).map(v => (
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

          {/* Navigation */}
          <button onClick={navigatePrev} aria-label="Previous" style={navBtnStyle}>
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

          <button onClick={onClose} aria-label="Close calendar" style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--color-text-secondary)', fontSize: '1.25rem', lineHeight: 1,
          }}>×</button>
        </div>

        {/* ── Body ── */}
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
          {view === 'month'
            ? <MonthView year={year} month={month} events={weekEvents} onSelectEvent={setSelectedEvent} />
            : <WeekView weekStart={weekStart} events={weekEvents} onSelectEvent={setSelectedEvent} />
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
