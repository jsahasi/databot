import { useState, useRef } from 'react'
import {
  BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { ChatMessage as ChatMessageType } from '../../hooks/useChat'

const CHART_COLORS = ['#4f46e5', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']

function ChatChart({ data }: { data: any }) {
  if (!data?.data?.length) return null
  const keys = Object.keys(data.data[0])
  const xKey = keys[0]
  const seriesKeys = keys.slice(1)
  const ChartComponent = data.type === 'line' ? LineChart : BarChart

  return (
    <div
      role="img"
      aria-label={data.title ? `Chart: ${data.title}` : 'Chart'}
      style={{ marginTop: '0.75rem', width: '100%', maxWidth: 560 }}
    >
      {data.title && (
        <p aria-hidden="true" style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', marginBottom: '0.375rem' }}>
          {data.title}
        </p>
      )}
      <ResponsiveContainer width="100%" height={220}>
        <ChartComponent data={data.data} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey={xKey} tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} label={data.yLabel ? { value: data.yLabel, angle: -90, position: 'insideLeft', style: { fontSize: 11 } } : undefined} />
          <Tooltip contentStyle={{ fontSize: '0.75rem' }} />
          {seriesKeys.length > 1 && <Legend wrapperStyle={{ fontSize: '0.75rem' }} />}
          {seriesKeys.map((key, i) =>
            data.type === 'line'
              ? <Line key={key} type="monotone" dataKey={key} stroke={CHART_COLORS[i % CHART_COLORS.length]} dot={false} strokeWidth={2} />
              : <Bar key={key} dataKey={key} fill={CHART_COLORS[i % CHART_COLORS.length]} radius={[3, 3, 0, 0]} />
          )}
        </ChartComponent>
      </ResponsiveContainer>
    </div>
  )
}

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

      {/* Message bubble + hover buttons row */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.375rem', maxWidth: '90%' }}>
        {/* Message bubble */}
        <div style={{
          padding: '0.625rem 0.875rem',
          borderRadius: isUser ? '1rem 1rem 0.25rem 1rem' : '1rem 1rem 1rem 0.25rem',
          background: isUser ? 'var(--color-primary)' : 'var(--color-card)',
          color: isUser ? '#fff' : 'var(--color-text)',
          fontSize: '0.85rem', lineHeight: 1.5,
          wordBreak: 'break-word',
          minWidth: 0,
          flex: 1,
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

        {/* Thumbs up/down — visible on hover for assistant messages */}
        {!isUser && (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '0.25rem',
            paddingTop: '0.25rem',
            opacity: showButtons ? 1 : 0,
            transition: 'opacity 0.15s',
            pointerEvents: showButtons ? 'auto' : 'none',
            flexShrink: 0,
          }}>
            <button
              aria-label="Thumbs up — good response"
              title="Good response"
              onClick={handleThumbsUp}
              style={{
                width: 26, height: 26,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: 'var(--color-card)',
                border: '1px solid var(--color-border)',
                borderRadius: 6,
                cursor: 'pointer',
                color: 'var(--color-text-secondary)',
                fontSize: '0.8rem',
                padding: 0,
                transition: 'color 0.12s, border-color 0.12s',
              }}
              onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.color = '#10b981'; (e.currentTarget as HTMLButtonElement).style.borderColor = '#10b981' }}
              onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.color = 'var(--color-text-secondary)'; (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--color-border)' }}
            >
              <svg aria-hidden="true" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14z"/>
                <path d="M7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/>
              </svg>
            </button>
            <button
              aria-label="Thumbs down — bad response"
              title="Something's wrong"
              onClick={handleThumbsDown}
              style={{
                width: 26, height: 26,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: 'var(--color-card)',
                border: '1px solid var(--color-border)',
                borderRadius: 6,
                cursor: 'pointer',
                color: 'var(--color-text-secondary)',
                fontSize: '0.8rem',
                padding: 0,
                transition: 'color 0.12s, border-color 0.12s',
              }}
              onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.color = '#ef4444'; (e.currentTarget as HTMLButtonElement).style.borderColor = '#ef4444' }}
              onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.color = 'var(--color-text-secondary)'; (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--color-border)' }}
            >
              <svg aria-hidden="true" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3H10z"/>
                <path d="M17 2h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"/>
              </svg>
            </button>
          </div>
        )}
      </div>

      {/* Chart */}
      {message.chartData && <ChatChart data={message.chartData} />}

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
