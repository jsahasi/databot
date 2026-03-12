import {
  BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import type { ChatMessage as ChatMessageType } from '../../hooks/useChat'

const CHART_COLORS = ['#4f46e5', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']

function ChatChart({ data }: { data: any }) {
  if (!data?.data?.length) return null
  const keys = Object.keys(data.data[0])
  const xKey = keys[0]
  const seriesKeys = keys.slice(1)
  const ChartComponent = data.type === 'line' ? LineChart : BarChart

  return (
    <div style={{ marginTop: '0.75rem', width: '100%', maxWidth: 560 }}>
      {data.title && (
        <p style={{ fontSize: '0.75rem', fontWeight: 600, color: '#374151', marginBottom: '0.375rem' }}>
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

/** Detect whether a line is a markdown table separator (|---|---|) */
function isSeparatorRow(line: string) {
  return /^\s*\|[\s\-:|]+\|\s*$/.test(line)
}

/** Parse a markdown pipe-table line into cell strings */
function parseCells(line: string): string[] {
  return line
    .split('|')
    .slice(1, -1)          // drop before first | and after last |
    .map(c => c.trim())
}

/**
 * Render assistant message content.
 * Splits content into text blocks and markdown tables and renders each appropriately.
 */
function renderContent(content: string) {
  const lines = content.split('\n')
  const segments: Array<{ type: 'text'; text: string } | { type: 'table'; rows: string[][] }> = []

  let i = 0
  while (i < lines.length) {
    const line = lines[i]
    // A table block: current line has pipes AND next line (if any) is a separator
    if (
      line.trim().startsWith('|') &&
      i + 1 < lines.length &&
      isSeparatorRow(lines[i + 1])
    ) {
      const tableRows: string[][] = []
      while (i < lines.length && lines[i].trim().startsWith('|')) {
        if (!isSeparatorRow(lines[i])) {
          tableRows.push(parseCells(lines[i]))
        }
        i++
      }
      segments.push({ type: 'table', rows: tableRows })
    } else {
      // Accumulate into a text block
      const last = segments[segments.length - 1]
      if (last?.type === 'text') {
        last.text += '\n' + line
      } else {
        segments.push({ type: 'text', text: line })
      }
      i++
    }
  }

  return segments.map((seg, idx) => {
    if (seg.type === 'table') {
      const [header, ...body] = seg.rows
      return (
        <div key={idx} style={{ overflowX: 'auto', margin: '0.5rem 0' }}>
          <table style={{
            borderCollapse: 'collapse',
            fontSize: '0.8rem',
            lineHeight: 1.5,
            width: '100%',
            minWidth: 'max-content',
          }}>
            {header && (
              <thead>
                <tr>
                  {header.map((h, j) => (
                    <th key={j} style={{
                      padding: '0.3rem 0.75rem',
                      textAlign: 'left',
                      fontWeight: 600,
                      borderBottom: '2px solid #cbd5e1',
                      whiteSpace: 'nowrap',
                      color: '#374151',
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
            )}
            <tbody>
              {body.map((row, ri) => (
                <tr key={ri} style={{ background: ri % 2 === 1 ? '#f8fafc' : 'transparent' }}>
                  {row.map((cell, ci) => (
                    <td key={ci} style={{
                      padding: '0.3rem 0.75rem',
                      borderBottom: '1px solid #e2e8f0',
                      whiteSpace: 'nowrap',
                      color: '#1a202c',
                    }}>{cell}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )
    }

    // Plain text block — trim leading/trailing blank lines
    const trimmed = seg.text.replace(/^\n+/, '').replace(/\n+$/, '')
    if (!trimmed) return null
    return (
      <span key={idx} style={{ whiteSpace: 'pre-wrap', display: 'block' }}>
        {trimmed}
      </span>
    )
  })
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
        <span style={{
          fontSize: '0.65rem', color: 'var(--color-text-secondary)',
          marginBottom: '0.25rem', paddingLeft: '0.25rem',
        }}>
          via {message.agentUsed.replace('_', ' ')}
        </span>
      )}

      {/* Message bubble */}
      <div style={{
        maxWidth: isUser ? '75%' : '90%',
        padding: '0.625rem 0.875rem',
        borderRadius: isUser ? '1rem 1rem 0.25rem 1rem' : '1rem 1rem 1rem 0.25rem',
        background: isUser ? 'var(--color-primary)' : '#f1f5f9',
        color: isUser ? '#fff' : 'var(--color-text)',
        fontSize: '0.85rem', lineHeight: 1.5,
        wordBreak: 'break-word',
      }}>
        {message.isLoading ? (
          <span style={{ display: 'flex', gap: '0.25rem', padding: '0.25rem 0' }}>
            <span style={{ animation: 'bounce 1s infinite 0s' }}>.</span>
            <span style={{ animation: 'bounce 1s infinite 0.2s' }}>.</span>
            <span style={{ animation: 'bounce 1s infinite 0.4s' }}>.</span>
            <style>{`@keyframes bounce { 0%, 60%, 100% { transform: translateY(0); } 30% { transform: translateY(-4px); } }`}</style>
          </span>
        ) : isUser ? (
          <span style={{ whiteSpace: 'pre-wrap' }}>{message.content}</span>
        ) : (
          renderContent(message.content)
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
