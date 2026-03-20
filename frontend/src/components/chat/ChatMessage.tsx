import { useState, useRef, useEffect, useCallback } from 'react'
import DOMPurify from 'dompurify'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import SmartChart from '../charts/SmartChart'
import { DeliveryChip } from '../calendar/EventCalendar'
import type { ChatMessage as ChatMessageType } from '../../hooks/useChat'

interface ChatMessageProps {
  message: ChatMessageType
  userQuestion?: string
}

const mdComponents = {
  h1: ({ children }: any) => <h1 style={{ fontSize: '1rem', fontWeight: 700, margin: '0.75rem 0 0.25rem' }}>{children}</h1>,
  h2: ({ children }: any) => <h2 style={{ fontSize: '0.95rem', fontWeight: 700, margin: '0.75rem 0 0.25rem' }}>{children}</h2>,
  h3: ({ children }: any) => <h3 style={{ fontSize: '0.875rem', fontWeight: 600, margin: '0.5rem 0 0.2rem' }}>{children}</h3>,
  p: ({ children }: any) => <p style={{ margin: '0.3rem 0' }}>{children}</p>,
  strong: ({ children }: any) => <strong style={{ fontWeight: 600 }}>{children}</strong>,
  em: ({ children }: any) => <em>{children}</em>,
  hr: () => <hr style={{ border: 'none', borderTop: '1px solid var(--color-border)', margin: '0.5rem 0' }} />,
  blockquote: ({ children }: any) => (
    <blockquote style={{ borderLeft: '3px solid var(--color-primary)', paddingLeft: '0.75rem', margin: '0.4rem 0', color: 'var(--color-text-secondary)', fontStyle: 'italic' }}>
      {children}
    </blockquote>
  ),
  ul: ({ children }: any) => <ul style={{ paddingLeft: '1.25rem', margin: '0.3rem 0' }}>{children}</ul>,
  ol: ({ children }: any) => <ol style={{ paddingLeft: '1.25rem', margin: '0.3rem 0' }}>{children}</ol>,
  li: ({ children }: any) => <li style={{ margin: '0.15rem 0' }}>{children}</li>,
  code: ({ children, className }: any) => className
    ? <pre style={{ background: 'var(--color-sidebar)', color: 'var(--color-text)', borderRadius: '0.375rem', padding: '0.5rem 0.75rem', fontSize: '0.78rem', overflowX: 'auto', margin: '0.4rem 0' }}><code>{children}</code></pre>
    : <code style={{ background: 'var(--color-border)', color: 'var(--color-text)', borderRadius: '0.2rem', padding: '0.1rem 0.3rem', fontSize: '0.8rem' }}>{children}</code>,
  table: ({ children }: any) => (
    <div style={{ overflowX: 'auto', margin: '0.5rem 0' }}>
      <table style={{ borderCollapse: 'collapse', fontSize: '0.8rem', lineHeight: 1.5, width: '100%', minWidth: 'max-content' }}>
        {children}
      </table>
    </div>
  ),
  th: ({ children }: any) => (
    <th style={{ padding: '0.3rem 0.75rem', textAlign: 'left', fontWeight: 600, borderBottom: '2px solid var(--color-border)', whiteSpace: 'nowrap', color: 'var(--color-text)' }}>
      {children}
    </th>
  ),
  td: ({ children }: any) => (
    <td style={{ padding: '0.3rem 0.75rem', borderBottom: '1px solid var(--color-border)', whiteSpace: 'nowrap', color: 'var(--color-text)' }}>
      {children}
    </td>
  ),
  tr: ({ children }: any) => <tr>{children}</tr>,
}

type FeedbackState = null | 'thumbs_up' | 'form' | 'submitted'

async function postFeedback(payload: {
  feedback_type: string
  feedback_text: string
  message_content: string
  user_question: string
  agent_used: string
  message_timestamp: string
}) {
  await fetch('/api/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

const POLL_COLORS = [
  'var(--color-chart-1)', 'var(--color-chart-2)', 'var(--color-chart-3)',
  'var(--color-chart-4)', 'var(--color-chart-5)', 'var(--color-chart-6)',
  'var(--color-chart-7)', 'var(--color-chart-8)',
]

function PollCardsInline({ polls }: { polls: any[] }) {
  if (!polls?.length) return null
  return (
    <div style={{ marginTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.75rem', maxWidth: 500 }}>
      {polls.map((poll: any, pi: number) => {
        const isOpenText = poll.question_type_cd === 'singletext' || poll.question_type_cd === 'singleanswer'
        return (
          <div key={poll.question_id || pi} style={{
            borderRadius: 10, border: '1px solid var(--color-border)',
            background: 'var(--color-card)', overflow: 'hidden',
          }}>
            <div style={{ height: 3, background: POLL_COLORS[pi % POLL_COLORS.length] }} />
            <div style={{ padding: '0.65rem 0.85rem' }}>
              <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--color-text)', marginBottom: '0.5rem', lineHeight: 1.35 }}>
                {poll.question_text}
              </div>
              {!isOpenText && poll.answers?.length > 0 && (() => {
                const total = poll.answers.reduce((s: number, a: any) => s + (a.response_count || 0), 0)
                return (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                    {poll.answers.map((a: any, ai: number) => {
                      const pct = total > 0 ? Math.round((a.response_count / total) * 100) : 0
                      return (
                        <div key={a.answer_cd || ai}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', marginBottom: 2 }}>
                            <span style={{ color: 'var(--color-text)', fontWeight: 500 }}>{a.answer_text}</span>
                            <span style={{ color: 'var(--color-text-secondary)' }}>{pct}% ({a.response_count})</span>
                          </div>
                          <div style={{ height: 16, background: 'var(--color-bg)', borderRadius: 4, overflow: 'hidden' }}>
                            <div style={{
                              height: '100%', width: `${pct}%`,
                              background: POLL_COLORS[ai % POLL_COLORS.length],
                              borderRadius: 4, transition: 'width 0.3s ease',
                              minWidth: pct > 0 ? 4 : 0,
                            }} />
                          </div>
                        </div>
                      )
                    })}
                    <div style={{ fontSize: '0.6rem', color: 'var(--color-text-secondary)', marginTop: '0.15rem' }}>
                      {total} total response{total !== 1 ? 's' : ''}
                    </div>
                  </div>
                )
              })()}
              {isOpenText && (
                <div>
                  <div style={{ fontSize: '0.65rem', color: 'var(--color-text-secondary)', marginBottom: '0.3rem' }}>
                    {poll.response_count} response{poll.response_count !== 1 ? 's' : ''} — sample answers:
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
                    {(poll.sample_answers || []).map((ans: string, ai: number) => (
                      <span key={ai} style={{
                        padding: '0.2rem 0.5rem', borderRadius: 12,
                        background: 'var(--color-bg)', border: '1px solid var(--color-border)',
                        fontSize: '0.65rem', color: 'var(--color-text)',
                      }}>
                        {ans}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ─── Elite Deep Links ────────────────────────────────────────────────────────

const ELITE_BASE = 'https://wcc.on24.com'

const ELITE_ACTIONS: { key: string; label: string; path: (id: number) => string; when: 'past' | 'future' | 'always' }[] = [
  { key: 'overview',     label: 'Overview',      path: id => `/webcast/update/${id}`,         when: 'always' },
  { key: 'registration', label: 'Registration',  path: id => `/webcast/registration/${id}`,   when: 'future' },
  { key: 'console',      label: 'Console',       path: id => `/webcast/html5console/${id}`,   when: 'future' },
  { key: 'archive',      label: 'Archive',       path: id => `/webcast/archive/${id}`,        when: 'past' },
  { key: 'aicontent',    label: 'AI Content',    path: id => `/webcast/aicontent/${id}`,      when: 'past' },
  { key: 'managereg',    label: 'Manage Reg',    path: id => `/webcast/managereg/${id}`,      when: 'past' },
  { key: 'share',        label: 'Share Event',   path: id => `/webcast/eventadmin/${id}`,     when: 'future' },
]

function EventActionChips({ eventId, isFuture }: { eventId: number; isFuture: boolean }) {
  const actions = ELITE_ACTIONS.filter(a => a.when === 'always' || (isFuture ? a.when === 'future' : a.when === 'past'))
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '1px solid var(--color-border)' }}>
      {actions.map(a => (
        <a
          key={a.key}
          href={`${ELITE_BASE}${a.path(eventId)}`}
          target="_blank"
          rel="noreferrer"
          style={{
            display: 'inline-flex', alignItems: 'center', gap: '0.2rem',
            padding: '0.25rem 0.6rem',
            borderRadius: 999,
            fontSize: '0.65rem', fontWeight: 600,
            color: 'var(--color-primary)',
            background: 'var(--color-primary-light)',
            border: '1px solid var(--color-chip-border)',
            textDecoration: 'none',
            transition: 'background 0.12s, box-shadow 0.12s',
            cursor: 'pointer',
            lineHeight: 1.3,
          }}
          onMouseEnter={e => { e.currentTarget.style.background = 'var(--color-chip-hover-bg)'; e.currentTarget.style.boxShadow = '0 1px 4px rgba(0,0,0,0.08)' }}
          onMouseLeave={e => { e.currentTarget.style.background = 'var(--color-primary-light)'; e.currentTarget.style.boxShadow = 'none' }}
        >
          {a.label} <span style={{ fontSize: '0.6rem', opacity: 0.7 }}>{'\u2197'}</span>
        </a>
      ))}
    </div>
  )
}

function EngagementSection({ kpis, defaultOpen }: { kpis: { label: string; value: string }[]; defaultOpen: boolean }) {
  const [open, setOpen] = useState(defaultOpen)
  if (kpis.length === 0 && !defaultOpen) return null
  return (
    <div style={{ marginTop: '0.5rem', borderTop: '1px solid var(--color-border)', paddingTop: '0.5rem' }}>
      <button
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        aria-label={open ? 'Collapse engagement section' : 'Expand engagement section'}
        style={{
          display: 'flex', alignItems: 'center', gap: '0.3rem', width: '100%',
          background: 'none', border: 'none', cursor: 'pointer', padding: 0,
          marginBottom: open ? '0.5rem' : 0,
        }}
      >
        <span style={{ fontSize: '0.6rem', color: 'var(--color-text-secondary)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Engagement
        </span>
        <svg aria-hidden="true" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="var(--color-text-secondary)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
          style={{ transform: open ? 'rotate(0deg)' : 'rotate(-90deg)', transition: 'transform 0.15s', marginTop: 1 }}>
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>
      {open && (
        kpis.length > 0 ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(100px, 1fr))', gap: '0.4rem' }}>
            {kpis.map(k => (
              <div key={k.label} style={{
                background: 'var(--color-bg)', borderRadius: 'var(--radius-sm)', padding: '0.4rem 0.6rem',
                border: '1px solid var(--color-border)',
              }}>
                <div style={{ fontSize: '0.58rem', color: 'var(--color-text-secondary)', fontWeight: 500 }}>{k.label}</div>
                <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--color-text)' }}>{k.value}</div>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ fontSize: '0.72rem', color: 'var(--color-text-secondary)', fontStyle: 'italic', margin: 0 }}>
            No engagement data available yet.
          </p>
        )
      )}
    </div>
  )
}

const AI_TYPE_LABELS: Record<string, string> = {
  KEYTAKEAWAYS: 'Key Takeaways', BLOG: 'Blog Post', EBOOK: 'eBook',
  FAQ: 'FAQ', FOLLOWUPEMAIL: 'Follow-up Email', FOLLOWUPEMAI: 'Follow-up Email',
  SOCIALMEDIAPOST: 'Social Media Post', SOCIALMEDIAP: 'Social Media Post',
  TRANSCRIPT: 'Transcript',
}
const KT_TAB_LABELS: Record<string, string> = {
  summary: 'Summary', takeaways: 'Takeaways', quote: 'Key Quote', other: 'Details',
}
const KT_TAB_ORDER = ['summary', 'takeaways', 'quote', 'other']

function AiAceSection({ eventId, aiContent }: { eventId: number; aiContent: { count: number; client_id?: number } }) {
  const [open, setOpen] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const [loading, setLoading] = useState(false)
  const [articles, setArticles] = useState<Record<string, string>>({})
  const [ktSections, setKtSections] = useState<Record<string, string>>({})
  const [types, setTypes] = useState<string[]>([])
  const [selectedType, setSelectedType] = useState('')
  const [activeTab, setActiveTab] = useState('')

  const handleToggle = () => {
    const next = !open
    setOpen(next)
    if (next && !loaded && !loading) {
      setLoading(true)
      fetch(`/api/calendar/event/${eventId}`)
        .then(r => r.ok ? r.json() : null)
        .then(d => {
          if (d?.ai_content) {
            const ai = d.ai_content
            const arts = ai.articles ?? {}
            const kts = ai.kt_sections ?? {}
            const ts = (ai.types ?? []).filter((t: string) => arts[t])
            setArticles(arts)
            setKtSections(kts)
            setTypes(ts)
            const defaultType = ts.includes('KEYTAKEAWAYS') ? 'KEYTAKEAWAYS' : (ts[0] ?? '')
            setSelectedType(defaultType)
            const tabs = KT_TAB_ORDER.filter(k => kts[k])
            setActiveTab(tabs.includes('takeaways') ? 'takeaways' : (tabs[0] ?? ''))
          }
          setLoaded(true)
        })
        .catch(() => setLoaded(true))
        .finally(() => setLoading(false))
    }
  }

  const mmUrl = aiContent.client_id
    ? `https://wccv.on24.com/webcast/mediamanager?date_range=all&client_ids=${aiContent.client_id}&types=article&sub_types=autogen_blog,autogen_ebook,autogen_faq,autogen_keytakeaways,autogen_followupemail,autogen_socialmediapost,autogen_transcript&search=${eventId}`
    : null

  const availableTabs = KT_TAB_ORDER.filter(k => ktSections[k])
  const content = selectedType === 'KEYTAKEAWAYS'
    ? (ktSections[activeTab] ?? articles['KEYTAKEAWAYS'])
    : articles[selectedType]

  return (
    <div style={{ marginTop: '0.5rem', borderTop: '1px solid var(--color-border)', paddingTop: '0.5rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <button
          onClick={handleToggle}
          aria-expanded={open}
          style={{
            display: 'flex', alignItems: 'center', gap: '0.3rem',
            background: 'none', border: 'none', cursor: 'pointer', padding: 0,
          }}
        >
          <span style={{ fontSize: '0.6rem', color: 'var(--color-text-secondary)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            AI-ACE Content {loading ? '· loading…' : `· ${aiContent.count} article${aiContent.count !== 1 ? 's' : ''}`}
          </span>
          <svg aria-hidden="true" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="var(--color-text-secondary)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
            style={{ transform: open ? 'rotate(0deg)' : 'rotate(-90deg)', transition: 'transform 0.15s', marginTop: 1 }}>
            <path d="M6 9l6 6 6-6" />
          </svg>
        </button>
        {mmUrl && (
          <a href={mmUrl} target="_blank" rel="noreferrer"
            style={{ fontSize: '0.58rem', fontWeight: 600, color: 'var(--color-success)', textDecoration: 'none' }}>
            Media Manager {'\u2197'}
          </a>
        )}
      </div>

      {open && loaded && types.length > 0 && (
        <div style={{ marginTop: '0.4rem' }}>
          <select
            value={selectedType}
            onChange={e => {
              setSelectedType(e.target.value)
              if (e.target.value === 'KEYTAKEAWAYS') {
                const tabs = KT_TAB_ORDER.filter(k => ktSections[k])
                setActiveTab(tabs.includes('takeaways') ? 'takeaways' : (tabs[0] ?? ''))
              }
            }}
            style={{
              width: '100%', marginBottom: '0.4rem',
              fontSize: '0.72rem', fontWeight: 500,
              padding: '0.25rem 0.45rem', borderRadius: 'var(--radius-sm)',
              border: '1px solid rgba(5,150,105,0.4)',
              background: 'rgba(5,150,105,0.08)', color: 'var(--color-success)',
              cursor: 'pointer', outline: 'none',
            }}
          >
            {types.map(t => <option key={t} value={t}>{AI_TYPE_LABELS[t] ?? t}</option>)}
          </select>

          {selectedType === 'KEYTAKEAWAYS' && availableTabs.length > 0 && (
            <div style={{ display: 'flex', borderBottom: '2px solid var(--color-border)', marginBottom: '0.4rem', gap: 0 }}>
              {availableTabs.map(tab => (
                <button key={tab} onClick={() => setActiveTab(tab)} style={{
                  fontSize: '0.65rem', fontWeight: activeTab === tab ? 600 : 400,
                  padding: '0.25rem 0.5rem',
                  border: 'none', borderBottom: activeTab === tab ? '2px solid var(--color-success)' : '2px solid transparent',
                  marginBottom: -2, background: 'transparent',
                  color: activeTab === tab ? 'var(--color-success)' : 'var(--color-text-secondary)',
                  cursor: 'pointer', whiteSpace: 'nowrap',
                }}>{KT_TAB_LABELS[tab] ?? tab}</button>
              ))}
            </div>
          )}

          {content && (
            <div
              dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(content) }}
              style={{
                maxHeight: 180, overflowY: 'auto',
                background: 'var(--color-bg)', border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-sm)', padding: '0.5rem 0.65rem',
                fontSize: '0.72rem', color: 'var(--color-text)', lineHeight: 1.6,
              }}
            />
          )}
        </div>
      )}

      {open && loaded && types.length === 0 && (
        <p style={{ fontSize: '0.72rem', color: 'var(--color-text-secondary)', fontStyle: 'italic', marginTop: '0.3rem' }}>
          No AI-ACE articles found for this event.
        </p>
      )}
    </div>
  )
}

function EventCardInline({ card }: { card: any }) {
  if (!card) return null
  const kpis: { label: string; value: string }[] = []
  if (card.registrant_count) kpis.push({ label: 'Registrants', value: Number(card.registrant_count).toLocaleString() })
  if (card.attendee_count) kpis.push({ label: 'Attendees', value: Number(card.attendee_count).toLocaleString() })
  if (card.conversion_rate) kpis.push({ label: 'Conversion', value: `${card.conversion_rate}%` })
  if (card.engagement_score_avg) kpis.push({ label: 'Avg Engagement', value: String(card.engagement_score_avg) })
  if (card.avg_live_minutes) kpis.push({ label: 'Avg Minutes', value: String(card.avg_live_minutes) })
  if (card.poll_response_count) kpis.push({ label: 'Poll Responses', value: Number(card.poll_response_count).toLocaleString() })
  if (card.survey_response_count) kpis.push({ label: 'Survey Responses', value: Number(card.survey_response_count).toLocaleString() })
  if (card.qa_count) kpis.push({ label: 'Q&A', value: Number(card.qa_count).toLocaleString() })
  if (card.chat_message_count) kpis.push({ label: 'Chat Messages', value: Number(card.chat_message_count).toLocaleString() })
  if (card.resource_download_count) kpis.push({ label: 'Downloads', value: Number(card.resource_download_count).toLocaleString() })

  // Past events with engagement data → open by default; future/empty → hidden
  const isFuture = card.is_future || (card.start_time && new Date(card.start_time) > new Date())
  const hasEngagement = kpis.length > 0
  const showEngagement = hasEngagement || !isFuture

  return (
    <div style={{
      marginTop: '0.75rem', borderRadius: 'var(--radius)', border: '1px solid var(--color-border)',
      background: 'var(--color-card)', overflow: 'hidden', maxWidth: 440,
      boxShadow: 'var(--shadow-card)',
    }}>
      <div style={{ height: 4, background: 'var(--color-primary)' }} />
      <div style={{ padding: '0.75rem 1rem' }}>
        {/* Type badge + delivery chip */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', marginBottom: '0.35rem', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.58rem', color: 'var(--color-text-secondary)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Event {card.event_id}
          </span>
          <DeliveryChip eventType={card.event_type} />
        </div>
        <div style={{ fontSize: '0.925rem', fontWeight: 700, color: 'var(--color-text)', lineHeight: 1.35, marginBottom: '0.4rem' }}>
          {card.title}
        </div>
        {card.start_time && (
          <div style={{ fontSize: '0.72rem', color: 'var(--color-text-secondary)', marginBottom: '0.25rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <svg aria-hidden="true" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.6 }}>
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
            </svg>
            {new Date(card.start_time).toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}
            {' · '}
            {new Date(card.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            {card.end_time ? ` – ${new Date(card.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : ''}
          </div>
        )}

        {/* Collapsible Engagement section */}
        {showEngagement && (
          <EngagementSection kpis={kpis} defaultOpen={hasEngagement} />
        )}

        {card.ai_content && (
          <AiAceSection eventId={card.event_id} aiContent={card.ai_content} />
        )}

        {/* Elite deep link action chips */}
        {card.event_id && (
          <EventActionChips eventId={card.event_id} isFuture={!!isFuture} />
        )}
      </div>
    </div>
  )
}

const CONTENT_TYPE_LABELS: Record<string, string> = {
  BLOG: 'Blog Post',
  KEYTAKEAWAYS: 'Key Takeaways',
  EBOOK: 'eBook',
  FAQ: 'FAQ',
  FOLLOWUPEMAIL: 'Follow-up Email',
  SOCIALMEDIA: 'Social Media',
  TRANSCRIPT: 'Transcript',
}

const CONTENT_TYPE_COLORS: Record<string, string> = {
  BLOG: 'var(--color-primary)',
  KEYTAKEAWAYS: 'var(--color-success)',
  EBOOK: 'var(--color-warning)',
  FAQ: 'var(--color-primary)',
  FOLLOWUPEMAIL: 'var(--color-agent-calendar)',
  SOCIALMEDIA: 'var(--color-agent-content)',
  TRANSCRIPT: 'var(--color-text-secondary)',
}

function ContentArticlesInline({ articles }: { articles: any[] }) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(0)
  if (!articles?.length) return null
  return (
    <div style={{ marginTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.75rem', maxWidth: 560 }}>
      {articles.map((article: any, idx: number) => {
        const typeKey = (article.content_type || '').toUpperCase()
        const typeLabel = CONTENT_TYPE_LABELS[typeKey] || typeKey
        const accentColor = CONTENT_TYPE_COLORS[typeKey] || 'var(--color-primary)'
        const isExpanded = expandedIdx === idx
        const dateStr = article.created_at
          ? new Date(article.created_at).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })
          : null
        // Media Manager link
        const mmUrl = article.event_id
          ? `https://wccv.on24.com/webcast/mediamanager?date_range=all&types=article&sub_types=autogen_${typeKey.toLowerCase()}&search=${article.event_id}`
          : `https://wccv.on24.com/webcast/mediamanager?date_range=all&types=article&sub_types=autogen_${typeKey.toLowerCase()}`

        return (
          <div key={idx} style={{
            borderRadius: 10, border: '1px solid var(--color-border)',
            background: 'var(--color-card)', overflow: 'hidden',
          }}>
            <div style={{ height: 3, background: accentColor }} />
            <div style={{ padding: '0.65rem 0.85rem' }}>
              {/* Header row */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <span style={{
                    fontSize: '0.6rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em',
                    color: accentColor, background: `${accentColor}18`,
                    padding: '0.15rem 0.45rem', borderRadius: 4,
                  }}>
                    {typeLabel}
                  </span>
                  {dateStr && (
                    <span style={{ fontSize: '0.65rem', color: 'var(--color-text-secondary)' }}>{dateStr}</span>
                  )}
                </div>
                <a
                  href={mmUrl}
                  target="_blank"
                  rel="noreferrer"
                  style={{ fontSize: '0.65rem', color: 'var(--color-success)', textDecoration: 'none', fontWeight: 600, whiteSpace: 'nowrap' }}
                >
                  Open in Media Manager ↗
                </a>
              </div>
              {/* Event title */}
              {article.event_title && (
                <div style={{ fontSize: '0.72rem', color: 'var(--color-text-secondary)', marginBottom: '0.4rem' }}>
                  {article.event_title}
                </div>
              )}
              {/* Content — collapsible */}
              {article.content && (
                <>
                  <div
                    style={{
                      fontSize: '0.78rem', color: 'var(--color-text)', lineHeight: 1.55,
                      maxHeight: isExpanded ? 'none' : '4.5rem',
                      overflow: 'hidden',
                      maskImage: isExpanded ? 'none' : 'linear-gradient(to bottom, black 60%, transparent 100%)',
                      WebkitMaskImage: isExpanded ? 'none' : 'linear-gradient(to bottom, black 60%, transparent 100%)',
                    }}
                    dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(article.content) }}
                  />
                  <button
                    onClick={() => setExpandedIdx(isExpanded ? null : idx)}
                    aria-expanded={isExpanded}
                    style={{
                      marginTop: '0.35rem', fontSize: '0.7rem', color: accentColor,
                      background: 'transparent', border: 'none', cursor: 'pointer', padding: 0,
                      fontWeight: 600,
                    }}
                  >
                    {isExpanded ? 'Show less ▲' : 'Read more ▼'}
                  </button>
                </>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

function EventCardsGrid({ cards }: { cards: any[] }) {
  if (!cards?.length) return null
  return (
    <div style={{
      marginTop: '0.75rem',
      display: 'grid',
      gridTemplateColumns: cards.length === 1 ? '1fr' : 'repeat(2, 1fr)',
      gap: 20,
      maxWidth: cards.length === 1 ? 440 : 880,
    }}>
      {cards.map((card: any, i: number) => (
        <div key={card.event_id || i} style={{
          borderRadius: 'var(--radius)', border: '1px solid var(--color-border)',
          background: 'var(--color-card)', overflow: 'hidden',
          boxShadow: 'var(--shadow-card)',
        }}>
          <div style={{ height: 4, background: 'var(--color-primary)' }} />
          <div style={{ padding: '0.65rem 0.85rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', marginBottom: '0.2rem', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '0.55rem', color: 'var(--color-text-secondary)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Event {card.event_id}
              </span>
              <DeliveryChip eventType={card.event_type} />
            </div>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--color-text)', lineHeight: 1.35, marginBottom: '0.3rem' }}>
              {card.title}
            </div>
            {card.start_time && (
              <div style={{ fontSize: '0.68rem', color: 'var(--color-text-secondary)', marginBottom: '0.3rem' }}>
                {new Date(card.start_time).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })}
              </div>
            )}
            {card.event_id && (
              <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
                <a href={`${ELITE_BASE}/webcast/update/${card.event_id}`} target="_blank" rel="noreferrer"
                  style={{ padding: '0.15rem 0.45rem', borderRadius: 999, fontSize: '0.58rem', fontWeight: 600, color: 'var(--color-primary)', background: 'var(--color-primary-light)', border: '1px solid var(--color-chip-border)', textDecoration: 'none' }}>
                  Overview {'\u2197'}
                </a>
                <a href={`${ELITE_BASE}/webcast/${card.start_time && new Date(card.start_time) > new Date() ? 'registration' : 'archive'}/${card.event_id}`} target="_blank" rel="noreferrer"
                  style={{ padding: '0.15rem 0.45rem', borderRadius: 999, fontSize: '0.58rem', fontWeight: 600, color: 'var(--color-primary)', background: 'var(--color-primary-light)', border: '1px solid var(--color-chip-border)', textDecoration: 'none' }}>
                  {card.start_time && new Date(card.start_time) > new Date() ? 'Registration' : 'Archive'} {'\u2197'}
                </a>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

interface BrandTemplate {
  id: string
  name: string
  primaryColor: string
  backgroundColor: string
  accentColor: string
  fontColor: string
  fontFamily: string
  logoUrl: string
  bannerImageUrl: string
  isDefault: boolean
}

const FALLBACK_TEMPLATE: BrandTemplate = {
  id: 'default',
  name: 'ON24 Nexus',
  primaryColor: '#4f46e5',
  backgroundColor: '#ffffff',
  accentColor: '#6366f1',
  fontColor: '#1a1d2e',
  fontFamily: 'Inter',
  logoUrl: '',
  bannerImageUrl: '',
  isDefault: true,
}

function ContentHtmlPreview({ html }: { html: string }) {
  const [open, setOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const [showShareForm, setShowShareForm] = useState(false)
  const [shareEmails, setShareEmails] = useState('')
  const [shareStatus, setShareStatus] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle')
  const [templates, setTemplates] = useState<BrandTemplate[]>([])
  const [selectedTemplate, setSelectedTemplate] = useState<BrandTemplate>(FALLBACK_TEMPLATE)
  const iframeRef = useRef<HTMLIFrameElement>(null)

  // Fetch brand templates when modal opens
  useEffect(() => {
    if (!open) return
    const load = async () => {
      try {
        const [listRes, defaultRes] = await Promise.all([
          fetch('/api/brand-templates'),
          fetch('/api/brand-templates/default'),
        ])
        const listData = await listRes.json()
        const defaultData = await defaultRes.json()
        const tpls = listData.templates || []
        setTemplates(tpls)
        if (defaultData && defaultData.id) {
          setSelectedTemplate(defaultData)
        } else if (tpls.length > 0) {
          setSelectedTemplate(tpls[0])
        }
      } catch { /* use fallback */ }
    }
    load()
  }, [open])

  const sanitized = DOMPurify.sanitize(html, {
    FORBID_TAGS: ['script', 'iframe', 'object', 'embed', 'form', 'input'],
    FORBID_ATTR: ['onerror', 'onclick', 'onload', 'onmouseover'],
    ALLOW_DATA_ATTR: false,
    ADD_TAGS: ['img'],
    ADD_ATTR: ['src', 'alt', 'width', 'height'],
  })

  const fontImport = `@import url('https://fonts.googleapis.com/css2?family=${encodeURIComponent(selectedTemplate.fontFamily)}&display=swap');`
  const baseStyles = `<style>${fontImport}body{font-family:'${selectedTemplate.fontFamily}',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;font-size:14px;line-height:1.7;max-width:720px;margin:auto;padding:2rem;color:${selectedTemplate.fontColor};background:${selectedTemplate.backgroundColor};}a{color:${selectedTemplate.primaryColor};}h1,h2,h3{color:${selectedTemplate.primaryColor};}img{max-width:100%;height:auto;border-radius:8px;margin:1rem 0;}</style>`
  const srcdoc = baseStyles + sanitized

  const handleClose = useCallback(() => setOpen(false), [])

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') handleClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, handleClose])

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(html)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch { /* ignore */ }
  }

  const handlePrint = () => {
    iframeRef.current?.contentWindow?.print()
  }

  const handleShare = () => {
    setShowShareForm(true)
    setShareStatus('idle')
    setShareEmails('')
  }

  const handleShareSend = async () => {
    const emails = shareEmails.split(',').map(e => e.trim()).filter(Boolean)
    if (emails.length === 0) return
    setShareStatus('sending')
    try {
      const adminInfo = JSON.parse(sessionStorage.getItem('adminInfo') || 'null')
      const adminId = sessionStorage.getItem('selectedAdmin') || ''
      const res = await fetch('/api/shares', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content_html: html,
          title: 'Content Preview',
          recipients: emails,
          admin_id: parseInt(adminId) || 0,
          admin_email: adminInfo?.email || '',
          session_id: '',
        }),
      })
      if (!res.ok) throw new Error('Failed to share')
      setShareStatus('sent')
      setTimeout(() => { setShowShareForm(false); setShareStatus('idle') }, 2000)
    } catch {
      setShareStatus('error')
    }
  }

  return (
    <>
      {/* Chip / button */}
      <button
        onClick={() => setOpen(true)}
        style={{
          marginTop: '0.75rem',
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.5rem',
          padding: '0.6rem 1rem',
          borderRadius: 10,
          border: '1px solid var(--color-border)',
          borderLeft: '3px solid #ec4899',
          background: 'var(--color-card)',
          cursor: 'pointer',
          fontSize: '0.8rem',
          fontWeight: 600,
          color: 'var(--color-text)',
          boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
          transition: 'background 0.12s',
        }}
        onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = 'rgba(236,72,153,0.07)' }}
        onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--color-card)' }}
      >
        {/* Document icon */}
        <svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ec4899" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
          <polyline points="10 9 9 9 8 9" />
        </svg>
        View Generated Content
      </button>

      {/* Modal */}
      {open && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="content-preview-title"
          onClick={handleClose}
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 9999,
            background: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '1rem',
          }}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{
              width: '100%',
              maxWidth: 800,
              maxHeight: '85vh',
              display: 'flex',
              flexDirection: 'column',
              background: 'var(--color-card)',
              borderRadius: 12,
              border: '1px solid var(--color-border)',
              boxShadow: '0 20px 60px rgba(0,0,0,0.2)',
              overflow: 'hidden',
            }}
          >
            {/* Header */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '0.75rem 1rem',
              borderBottom: '1px solid var(--color-border)',
              flexShrink: 0,
            }}>
              <span id="content-preview-title" style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--color-heading, var(--color-text))' }}>
                Content Preview
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                {/* Template selector */}
                {templates.length > 0 && (
                  <select
                    value={selectedTemplate.id}
                    onChange={e => {
                      const t = templates.find(tpl => tpl.id === e.target.value)
                      if (t) setSelectedTemplate(t)
                    }}
                    title="Brand template"
                    style={{
                      fontSize: '0.72rem', padding: '0.2rem 0.4rem',
                      border: '1px solid var(--color-border)', borderRadius: 5,
                      background: 'var(--color-bg)', color: 'var(--color-text)',
                      cursor: 'pointer', fontFamily: 'inherit', maxWidth: 160,
                    }}
                  >
                    {templates.map(t => (
                      <option key={t.id} value={t.id}>{t.name}{t.isDefault ? ' *' : ''}</option>
                    ))}
                  </select>
                )}
                {/* Copy */}
                <button
                  onClick={handleCopy}
                  title={copied ? 'Copied!' : 'Copy HTML'}
                  aria-label="Copy HTML to clipboard"
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: copied ? 'var(--color-success)' : 'var(--color-text-secondary)', padding: 4, display: 'flex', borderRadius: 4 }}
                >
                  <svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                  </svg>
                </button>
                {/* Print */}
                <button
                  onClick={handlePrint}
                  title="Print"
                  aria-label="Print content"
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-secondary)', padding: 4, display: 'flex', borderRadius: 4 }}
                >
                  <svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="6 9 6 2 18 2 18 9" />
                    <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" />
                    <rect x="6" y="14" width="12" height="8" />
                  </svg>
                </button>
                {/* Share */}
                <button
                  onClick={handleShare}
                  title="Share"
                  aria-label="Share content"
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-secondary)', padding: 4, display: 'flex', borderRadius: 4 }}
                >
                  <svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                    <polyline points="15 3 21 3 21 9" />
                    <line x1="10" y1="14" x2="21" y2="3" />
                  </svg>
                </button>
                {/* Close */}
                <button
                  onClick={handleClose}
                  title="Close"
                  aria-label="Close preview"
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-secondary)', padding: 4, display: 'flex', borderRadius: 4, marginLeft: '0.25rem' }}
                >
                  <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              </div>
            </div>
            {/* Share form — inline below header */}
            {showShareForm && (
              <div style={{
                padding: '0.75rem 1rem',
                borderBottom: '1px solid var(--color-border)',
                background: 'var(--color-bg)',
              }}>
                {shareStatus === 'sent' ? (
                  <div style={{ fontSize: '0.82rem', color: 'var(--color-success)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                    Link sent!
                  </div>
                ) : (
                  <>
                    <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--color-text)', marginBottom: '0.4rem' }}>
                      Share via email
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                      <input
                        type="text"
                        value={shareEmails}
                        onChange={e => setShareEmails(e.target.value)}
                        placeholder="email1@example.com, email2@example.com"
                        onKeyDown={e => { if (e.key === 'Enter') handleShareSend() }}
                        style={{
                          flex: 1,
                          padding: '0.4rem 0.6rem',
                          fontSize: '0.78rem',
                          border: '1px solid var(--color-border)',
                          borderRadius: 6,
                          background: 'var(--color-card)',
                          color: 'var(--color-text)',
                          outline: 'none',
                          fontFamily: 'inherit',
                        }}
                      />
                      <button
                        onClick={handleShareSend}
                        disabled={shareStatus === 'sending' || !shareEmails.trim()}
                        style={{
                          padding: '0.4rem 0.85rem',
                          fontSize: '0.78rem',
                          fontWeight: 600,
                          background: shareEmails.trim() && shareStatus !== 'sending' ? 'var(--color-primary)' : 'var(--color-border)',
                          color: 'var(--color-card)',
                          border: 'none',
                          borderRadius: 6,
                          cursor: shareEmails.trim() && shareStatus !== 'sending' ? 'pointer' : 'not-allowed',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {shareStatus === 'sending' ? 'Sending...' : 'Send'}
                      </button>
                      <button
                        onClick={() => { setShowShareForm(false); setShareStatus('idle') }}
                        style={{
                          background: 'none',
                          border: 'none',
                          fontSize: '0.75rem',
                          color: 'var(--color-text-secondary)',
                          cursor: 'pointer',
                          textDecoration: 'underline',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        Cancel
                      </button>
                    </div>
                    {shareStatus === 'error' && (
                      <div style={{ fontSize: '0.72rem', color: 'var(--color-danger)', marginTop: '0.35rem' }}>
                        Failed to send. Please try again.
                      </div>
                    )}
                  </>
                )}
              </div>
            )}
            {/* Body — iframe */}
            <div style={{ flex: 1, overflow: 'hidden' }}>
              <iframe
                ref={iframeRef}
                srcDoc={srcdoc}
                sandbox="allow-same-origin"
                title="Content preview"
                style={{ width: '100%', height: '100%', border: 'none', minHeight: 400 }}
              />
            </div>
          </div>
        </div>
      )}
    </>
  )
}

export default function ChatMessage({ message, userQuestion = '' }: ChatMessageProps) {
  const isUser = message.role === 'user'
  const [hovered, setHovered] = useState(false)
  const [feedbackState, setFeedbackState] = useState<FeedbackState>(null)
  const [feedbackText, setFeedbackText] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleThumbsUp = async () => {
    setFeedbackState('thumbs_up')
    await postFeedback({
      feedback_type: 'positive',
      feedback_text: '',
      message_content: message.content,
      user_question: userQuestion,
      agent_used: message.agentUsed || '',
      message_timestamp: message.timestamp.toISOString(),
    })
  }

  const handleThumbsDown = () => {
    setFeedbackState('form')
    setTimeout(() => textareaRef.current?.focus(), 50)
  }

  const handleSubmitFeedback = async () => {
    if (!feedbackText.trim()) return
    await postFeedback({
      feedback_type: 'negative',
      feedback_text: feedbackText.trim(),
      message_content: message.content,
      user_question: userQuestion,
      agent_used: message.agentUsed || '',
      message_timestamp: message.timestamp.toISOString(),
    })
    setFeedbackState('submitted')
    setFeedbackText('')
  }

  const showButtons = hovered && !message.isLoading && feedbackState === null

  return (
    <div
      style={{
        display: 'flex', flexDirection: 'column',
        alignItems: isUser ? 'flex-end' : 'flex-start',
        marginBottom: '0.75rem',
        position: 'relative',
      }}
      onMouseEnter={() => !isUser && setHovered(true)}
      onMouseLeave={() => !isUser && setHovered(false)}
    >
      {/* Agent badge */}
      {!isUser && message.agentUsed && (
        <span
          aria-label={`Response via ${message.agentUsed.replace('_', ' ')}`}
          style={{
            fontSize: '0.65rem', color: 'var(--color-text-secondary)',
            marginBottom: '0.25rem', paddingLeft: '0.25rem',
          }}
        >
          via {message.agentUsed.replace('_', ' ')}
        </span>
      )}

      {/* Event Card — shown BEFORE text when present */}
      <div style={{ maxWidth: '90%' }}>
        {!isUser && message.eventCard && !message.eventCards && <EventCardInline card={message.eventCard} />}
        {!isUser && message.eventCards && <EventCardsGrid cards={message.eventCards} />}

        {/* Message bubble */}
        <div style={{
          padding: '0.625rem 0.875rem',
          borderRadius: isUser ? '1rem 1rem 0.25rem 1rem' : '1rem 1rem 1rem 0.25rem',
          background: isUser ? 'var(--color-primary)' : 'var(--color-card)',
          color: isUser ? 'var(--color-card)' : 'var(--color-text)',
          fontSize: '0.85rem', lineHeight: 1.5,
          wordBreak: 'break-word',
          marginTop: (!isUser && (message.eventCard || message.eventCards)) ? '0.5rem' : undefined,
        }}>
          {message.isLoading ? (
            <span role="status" aria-live="polite" aria-label="Loading response" style={{ display: 'flex', gap: '0.25rem', padding: '0.25rem 0' }}>
              <span aria-hidden="true" style={{ animation: 'bounce 1s infinite 0s' }}>.</span>
              <span aria-hidden="true" style={{ animation: 'bounce 1s infinite 0.2s' }}>.</span>
              <span aria-hidden="true" style={{ animation: 'bounce 1s infinite 0.4s' }}>.</span>
              <style>{`@keyframes bounce { 0%, 60%, 100% { transform: translateY(0); } 30% { transform: translateY(-4px); } }`}</style>
            </span>
          ) : isUser ? (
            <span style={{ whiteSpace: 'pre-wrap' }}>{message.content}</span>
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
              {message.suggestions && message.suggestions.length > 0
                ? message.content.replace(/(\n\s*\d+\.\s+.+)+\s*$/m, '').trim()
                : message.content}
            </ReactMarkdown>
          )}
        </div>

        {/* Thumbs up/down — below the assistant response, visible on hover */}
        {!isUser && (
          <div style={{
            display: 'flex',
            gap: '0.375rem',
            paddingTop: '0.375rem',
            paddingLeft: '0.25rem',
            opacity: showButtons ? 1 : 0,
            transition: 'opacity 0.15s',
            pointerEvents: showButtons ? 'auto' : 'none',
          }}>
            <button
              aria-label="Thumbs up — good response"
              title="Good response"
              onClick={handleThumbsUp}
              style={{
                width: 44, height: 44,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: 'transparent',
                border: '1px solid var(--color-border)',
                borderRadius: 6,
                cursor: 'pointer',
                color: 'var(--color-text-secondary)',
                padding: 0,
                transition: 'color 0.12s, border-color 0.12s',
              }}
              onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.color = 'var(--color-success)'; (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--color-success)' }}
              onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.color = 'var(--color-text-secondary)'; (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--color-border)' }}
            >
              <svg aria-hidden="true" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14z"/>
                <path d="M7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/>
              </svg>
            </button>
            <button
              aria-label="Thumbs down — bad response"
              title="Something's wrong"
              onClick={handleThumbsDown}
              style={{
                width: 44, height: 44,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: 'transparent',
                border: '1px solid var(--color-border)',
                borderRadius: 6,
                cursor: 'pointer',
                color: 'var(--color-text-secondary)',
                padding: 0,
                transition: 'color 0.12s, border-color 0.12s',
              }}
              onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.color = 'var(--color-danger)'; (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--color-danger)' }}
              onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.color = 'var(--color-text-secondary)'; (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--color-border)' }}
            >
              <svg aria-hidden="true" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3H10z"/>
                <path d="M17 2h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"/>
              </svg>
            </button>
          </div>
        )}
      </div>

      {/* Chart */}
      {message.chartData && <SmartChart data={message.chartData} />}

      {/* Poll Cards */}
      {message.pollCards && <PollCardsInline polls={message.pollCards} />}

      {/* AI Content Articles */}
      {message.contentArticles && <ContentArticlesInline articles={message.contentArticles} />}

      {/* Generated HTML content preview */}
      {message.contentHtml && <ContentHtmlPreview html={message.contentHtml} />}

      {/* Thumbs-up confirmation */}
      {!isUser && feedbackState === 'thumbs_up' && (
        <span style={{ fontSize: '0.65rem', color: 'var(--color-success)', marginTop: '0.2rem', paddingLeft: '0.25rem' }}>
          Thanks for the feedback!
        </span>
      )}

      {/* Submitted confirmation */}
      {!isUser && feedbackState === 'submitted' && (
        <span style={{ fontSize: '0.65rem', color: 'var(--color-text-secondary)', marginTop: '0.2rem', paddingLeft: '0.25rem' }}>
          Feedback recorded — thanks.
        </span>
      )}

      {/* Thumbs-down feedback form */}
      {!isUser && feedbackState === 'form' && (
        <div style={{
          marginTop: '0.5rem',
          background: 'var(--color-card)',
          border: '1px solid var(--color-border)',
          borderRadius: '0.75rem',
          padding: '0.75rem',
          maxWidth: 380,
          boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
        }}>
          <p style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--color-text)', marginBottom: '0.5rem' }}>
            Tell me what I got wrong
          </p>
          <textarea
            ref={textareaRef}
            value={feedbackText}
            onChange={e => setFeedbackText(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmitFeedback() } }}
            placeholder="Describe the issue..."
            rows={3}
            style={{
              width: '100%',
              padding: '0.5rem',
              fontSize: '0.8rem',
              border: '1px solid var(--color-border)',
              borderRadius: '0.5rem',
              background: 'var(--color-bg)',
              color: 'var(--color-text)',
              resize: 'vertical',
              fontFamily: 'inherit',
              outline: 'none',
              boxSizing: 'border-box',
            }}
          />
          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem', justifyContent: 'flex-end' }}>
            <button
              onClick={() => { setFeedbackState(null); setFeedbackText('') }}
              style={{
                padding: '0.3rem 0.75rem',
                fontSize: '0.75rem',
                background: 'transparent',
                border: '1px solid var(--color-border)',
                borderRadius: 6,
                cursor: 'pointer',
                color: 'var(--color-text-secondary)',
              }}
            >
              Cancel
            </button>
            <button
              onClick={handleSubmitFeedback}
              disabled={!feedbackText.trim()}
              style={{
                padding: '0.3rem 0.75rem',
                fontSize: '0.75rem',
                background: feedbackText.trim() ? 'var(--color-primary)' : 'var(--color-border)',
                border: 'none',
                borderRadius: 6,
                cursor: feedbackText.trim() ? 'pointer' : 'not-allowed',
                color: 'var(--color-card)',
                fontWeight: 500,
              }}
            >
              Submit
            </button>
          </div>
          <p style={{ fontSize: '0.6rem', color: '#9ca3af', marginTop: '0.5rem', lineHeight: 1.4 }}>
            Your suggestion will inform LLM refinement.
            {' '}Saved to <span style={{ fontFamily: 'monospace' }}>improvement-inbox.txt</span>
          </p>
        </div>
      )}

      {/* Timestamp */}
      <span style={{
        fontSize: '0.6rem', color: 'var(--color-text-secondary)',
        marginTop: '0.25rem', paddingLeft: '0.25rem',
      }}>
        {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
      </span>
    </div>
  )
}
