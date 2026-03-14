import { useState, useRef } from 'react'
import DOMPurify from 'dompurify'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import SmartChart from '../charts/SmartChart'
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

const POLL_COLORS = ['#4f46e5', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#0ea5e9', '#ec4899', '#14b8a6']

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

function EventCardInline({ card }: { card: any }) {
  if (!card) return null
  const kpis: { label: string; value: string }[] = []
  if (card.registrant_count) kpis.push({ label: 'Registrants', value: Number(card.registrant_count).toLocaleString() })
  if (card.attendee_count) kpis.push({ label: 'Attendees', value: Number(card.attendee_count).toLocaleString() })
  if (card.conversion_rate) kpis.push({ label: 'Conversion', value: `${card.conversion_rate}%` })
  if (card.engagement_score_avg) kpis.push({ label: 'Avg Engagement', value: String(card.engagement_score_avg) })
  if (card.poll_response_count) kpis.push({ label: 'Poll Responses', value: Number(card.poll_response_count).toLocaleString() })
  if (card.survey_response_count) kpis.push({ label: 'Survey Responses', value: Number(card.survey_response_count).toLocaleString() })
  if (card.resource_download_count) kpis.push({ label: 'Downloads', value: Number(card.resource_download_count).toLocaleString() })

  return (
    <div style={{
      marginTop: '0.75rem', borderRadius: 10, border: '1px solid var(--color-border)',
      background: 'var(--color-card)', overflow: 'hidden', maxWidth: 420,
    }}>
      <div style={{ height: 4, background: '#4f46e5' }} />
      <div style={{ padding: '0.75rem 1rem' }}>
        <div style={{ fontSize: '0.6rem', color: 'var(--color-text-secondary)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.15rem' }}>
          Event {card.event_id}{card.event_type ? ` · ${card.event_type}` : ''}
        </div>
        <div style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--color-text)', lineHeight: 1.35, marginBottom: '0.4rem' }}>
          {card.title}
        </div>
        {card.start_time && (
          <div style={{ fontSize: '0.72rem', color: 'var(--color-text-secondary)', marginBottom: '0.5rem' }}>
            {new Date(card.start_time).toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}
            {' '}
            {new Date(card.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            {card.end_time ? ` – ${new Date(card.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : ''}
          </div>
        )}
        {kpis.length > 0 && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(100px, 1fr))', gap: '0.4rem' }}>
            {kpis.map(k => (
              <div key={k.label} style={{
                background: 'var(--color-bg)', borderRadius: 6, padding: '0.4rem 0.6rem',
                border: '1px solid var(--color-border)',
              }}>
                <div style={{ fontSize: '0.6rem', color: 'var(--color-text-secondary)' }}>{k.label}</div>
                <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--color-text)' }}>{k.value}</div>
              </div>
            ))}
          </div>
        )}
        {card.ai_content && (() => {
          const { count, client_id, event_id: eid } = card.ai_content
          const mmUrl = `https://wccv.on24.com/webcast/mediamanager?date_range=all&client_ids=${client_id}&types=article&sub_types=autogen_blog,autogen_ebook,autogen_faq,autogen_keytakeaways,autogen_followupemail,autogen_socialmediapost,autogen_transcript&search=${eid ?? card.event_id}`
          return (
            <div style={{ marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '1px solid var(--color-border)' }}>
              <div style={{ fontSize: '0.6rem', color: 'var(--color-text-secondary)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.3rem' }}>
                AI-ACE Content
              </div>
              <a
                href={mmUrl}
                target="_blank"
                rel="noreferrer"
                style={{ fontSize: '0.78rem', fontWeight: 600, color: '#10b981', textDecoration: 'none' }}
              >
                Key Takeaways ↗
              </a>
              <span style={{ fontSize: '0.7rem', color: 'var(--color-text-secondary)', marginLeft: '0.4rem' }}>
                {count} article{count !== 1 ? 's' : ''}
              </span>
            </div>
          )
        })()}
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
  BLOG: '#4f46e5',
  KEYTAKEAWAYS: '#10b981',
  EBOOK: '#f59e0b',
  FAQ: '#0ea5e9',
  FOLLOWUPEMAIL: '#8b5cf6',
  SOCIALMEDIA: '#ec4899',
  TRANSCRIPT: '#6b7280',
}

function ContentArticlesInline({ articles }: { articles: any[] }) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(0)
  if (!articles?.length) return null
  return (
    <div style={{ marginTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.75rem', maxWidth: 560 }}>
      {articles.map((article: any, idx: number) => {
        const typeKey = (article.content_type || '').toUpperCase()
        const typeLabel = CONTENT_TYPE_LABELS[typeKey] || typeKey
        const accentColor = CONTENT_TYPE_COLORS[typeKey] || '#4f46e5'
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
                  style={{ fontSize: '0.65rem', color: '#10b981', textDecoration: 'none', fontWeight: 600, whiteSpace: 'nowrap' }}
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
      maxWidth: cards.length === 1 ? 420 : 860,
    }}>
      {cards.map((card: any, i: number) => (
        <div key={card.event_id || i} style={{
          borderRadius: 10, border: '1px solid var(--color-border)',
          background: 'var(--color-card)', overflow: 'hidden',
        }}>
          <div style={{ height: 4, background: '#4f46e5' }} />
          <div style={{ padding: '0.65rem 0.85rem' }}>
            <div style={{ fontSize: '0.58rem', color: 'var(--color-text-secondary)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.15rem' }}>
              Event {card.event_id}{card.event_type ? ` · ${card.event_type}` : ''}
            </div>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--color-text)', lineHeight: 1.35, marginBottom: '0.3rem' }}>
              {card.title}
            </div>
            {card.start_time && (
              <div style={{ fontSize: '0.68rem', color: 'var(--color-text-secondary)' }}>
                {new Date(card.start_time).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
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

      {/* Message bubble */}
      <div style={{ maxWidth: '90%' }}>
        <div style={{
          padding: '0.625rem 0.875rem',
          borderRadius: isUser ? '1rem 1rem 0.25rem 1rem' : '1rem 1rem 1rem 0.25rem',
          background: isUser ? 'var(--color-primary)' : 'var(--color-card)',
          color: isUser ? '#fff' : 'var(--color-text)',
          fontSize: '0.85rem', lineHeight: 1.5,
          wordBreak: 'break-word',
        }}>
          {message.isLoading ? (
            <span role="status" aria-label="Loading response" style={{ display: 'flex', gap: '0.25rem', padding: '0.25rem 0' }}>
              <span aria-hidden="true" style={{ animation: 'bounce 1s infinite 0s' }}>.</span>
              <span aria-hidden="true" style={{ animation: 'bounce 1s infinite 0.2s' }}>.</span>
              <span aria-hidden="true" style={{ animation: 'bounce 1s infinite 0.4s' }}>.</span>
              <style>{`@keyframes bounce { 0%, 60%, 100% { transform: translateY(0); } 30% { transform: translateY(-4px); } }`}</style>
            </span>
          ) : isUser ? (
            <span style={{ whiteSpace: 'pre-wrap' }}>{message.content}</span>
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
              {message.content}
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
                width: 24, height: 24,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: 'transparent',
                border: '1px solid var(--color-border)',
                borderRadius: 6,
                cursor: 'pointer',
                color: 'var(--color-text-secondary)',
                padding: 0,
                transition: 'color 0.12s, border-color 0.12s',
              }}
              onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.color = '#10b981'; (e.currentTarget as HTMLButtonElement).style.borderColor = '#10b981' }}
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
                width: 24, height: 24,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: 'transparent',
                border: '1px solid var(--color-border)',
                borderRadius: 6,
                cursor: 'pointer',
                color: 'var(--color-text-secondary)',
                padding: 0,
                transition: 'color 0.12s, border-color 0.12s',
              }}
              onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.color = '#ef4444'; (e.currentTarget as HTMLButtonElement).style.borderColor = '#ef4444' }}
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

      {/* Event Card */}
      {message.eventCard && !message.eventCards && <EventCardInline card={message.eventCard} />}

      {/* Event Cards Grid (2–4 events) */}
      {message.eventCards && <EventCardsGrid cards={message.eventCards} />}

      {/* Poll Cards */}
      {message.pollCards && <PollCardsInline polls={message.pollCards} />}

      {/* AI Content Articles */}
      {message.contentArticles && <ContentArticlesInline articles={message.contentArticles} />}

      {/* Thumbs-up confirmation */}
      {!isUser && feedbackState === 'thumbs_up' && (
        <span style={{ fontSize: '0.65rem', color: '#10b981', marginTop: '0.2rem', paddingLeft: '0.25rem' }}>
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
                background: feedbackText.trim() ? 'var(--color-primary)' : '#e5e7eb',
                border: 'none',
                borderRadius: 6,
                cursor: feedbackText.trim() ? 'pointer' : 'not-allowed',
                color: '#fff',
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
