import type { ChatMessage as ChatMessageType } from '../../hooks/useChat'

interface ChatMessageProps {
  message: ChatMessageType
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
        maxWidth: '85%', padding: '0.625rem 0.875rem',
        borderRadius: isUser ? '1rem 1rem 0.25rem 1rem' : '1rem 1rem 1rem 0.25rem',
        background: isUser ? 'var(--color-primary)' : '#f1f5f9',
        color: isUser ? '#fff' : 'var(--color-text)',
        fontSize: '0.85rem', lineHeight: 1.5,
        whiteSpace: 'pre-wrap', wordBreak: 'break-word',
      }}>
        {message.isLoading ? (
          <span style={{ display: 'flex', gap: '0.25rem', padding: '0.25rem 0' }}>
            <span style={{ animation: 'bounce 1s infinite 0s' }}>.</span>
            <span style={{ animation: 'bounce 1s infinite 0.2s' }}>.</span>
            <span style={{ animation: 'bounce 1s infinite 0.4s' }}>.</span>
            <style>{`@keyframes bounce { 0%, 60%, 100% { transform: translateY(0); } 30% { transform: translateY(-4px); } }`}</style>
          </span>
        ) : (
          message.content
        )}
      </div>

      {/* Chart data indicator */}
      {message.chartData && (
        <div style={{
          marginTop: '0.5rem', padding: '0.5rem 0.75rem',
          background: '#f0fdf4', border: '1px solid #bbf7d0',
          borderRadius: 'var(--radius)', fontSize: '0.75rem', color: '#166534',
          maxWidth: '85%',
        }}>
          Chart: {message.chartData.title || 'Visualization data attached'}
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
