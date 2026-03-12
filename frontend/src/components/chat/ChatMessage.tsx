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

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user'

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      alignItems: isUser ? 'flex-end' : 'flex-start',
      marginBottom: '0.75rem',
    }}>
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
      <div style={{
        maxWidth: isUser ? '75%' : '90%',
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

      {/* Chart */}
      {message.chartData && <ChatChart data={message.chartData} />}

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
