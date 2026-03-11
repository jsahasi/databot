import React, { useState, useRef, useEffect } from 'react'
import { useChat } from '../../hooks/useChat'
import ChatMessage from './ChatMessage'
import AgentIndicator from './AgentIndicator'

interface ChatPanelProps {
  isOpen: boolean
  onToggle: () => void
}

export default function ChatPanel({ isOpen, onToggle }: ChatPanelProps) {
  const { messages, isConnected, isProcessing, activeAgent, sendMessage, resetChat } = useChat()
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Focus input when panel opens
  useEffect(() => {
    if (isOpen) inputRef.current?.focus()
  }, [isOpen])

  const handleSend = () => {
    const trimmed = input.trim()
    if (!trimmed || isProcessing) return
    sendMessage(trimmed)
    setInput('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  if (!isOpen) {
    return (
      <button onClick={onToggle} style={{
        position: 'fixed', bottom: 24, right: 24, width: 56, height: 56,
        borderRadius: '50%', background: 'var(--color-primary)',
        color: '#fff', border: 'none', cursor: 'pointer',
        boxShadow: '0 4px 12px rgba(79,70,229,0.4)',
        fontSize: '1.25rem', display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 50, transition: 'transform 0.2s',
      }}
        onMouseEnter={e => (e.currentTarget.style.transform = 'scale(1.1)')}
        onMouseLeave={e => (e.currentTarget.style.transform = 'scale(1)')}
        title="Open AI Chat"
      >
        AI
      </button>
    )
  }

  return (
    <div style={{
      width: 380, height: '100vh', position: 'fixed', right: 0, top: 0,
      background: 'var(--color-card)', borderLeft: '1px solid var(--color-border)',
      display: 'flex', flexDirection: 'column', zIndex: 40,
      boxShadow: '-4px 0 12px rgba(0,0,0,0.05)',
    }}>
      {/* Header */}
      <div style={{
        padding: '0.875rem 1rem', borderBottom: '1px solid var(--color-border)',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        background: 'var(--color-sidebar)', color: '#fff',
      }}>
        <div>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600 }}>DataBot AI</h3>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', marginTop: '0.125rem' }}>
            <div style={{
              width: 6, height: 6, borderRadius: '50%',
              background: isConnected ? '#48bb78' : '#f56565',
            }} />
            <span style={{ fontSize: '0.65rem', opacity: 0.7 }}>
              {isConnected ? 'Connected' : 'Reconnecting...'}
            </span>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button onClick={resetChat} style={{
            padding: '0.25rem 0.5rem', fontSize: '0.7rem',
            background: 'rgba(255,255,255,0.1)', color: '#fff',
            border: '1px solid rgba(255,255,255,0.2)', borderRadius: '4px',
            cursor: 'pointer',
          }}>
            Clear
          </button>
          <button onClick={onToggle} style={{
            padding: '0.25rem 0.5rem', fontSize: '0.85rem',
            background: 'transparent', color: '#fff',
            border: 'none', cursor: 'pointer',
          }}>
            ✕
          </button>
        </div>
      </div>

      {/* Messages */}
      <div style={{
        flex: 1, overflowY: 'auto', padding: '1rem',
        display: 'flex', flexDirection: 'column',
      }}>
        {messages.length === 0 && (
          <div style={{
            textAlign: 'center', padding: '2rem 1rem',
            color: 'var(--color-text-secondary)', fontSize: '0.85rem',
          }}>
            <p style={{ fontWeight: 600, marginBottom: '0.5rem', color: 'var(--color-text)' }}>
              Ask me anything about your webinars
            </p>
            <p>Try: "Show me attendance trends" or "Which events had the best engagement?"</p>
          </div>
        )}
        {messages.map(msg => (
          <React.Fragment key={msg.id}>
            <ChatMessage message={msg} />
            {msg.role === 'assistant' && msg.suggestions && msg.suggestions.length > 0 && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.375rem', marginBottom: '0.75rem' }}>
                {msg.suggestions.map((s, i) => (
                  <button key={i} onClick={() => { sendMessage(s); setInput('') }} style={{
                    padding: '0.25rem 0.625rem', fontSize: '0.72rem',
                    background: 'var(--color-bg)', border: '1px solid var(--color-primary)',
                    borderRadius: '1rem', color: 'var(--color-primary)',
                    cursor: 'pointer', lineHeight: 1.4,
                  }}>
                    {s}
                  </button>
                ))}
              </div>
            )}
          </React.Fragment>
        ))}
        {isProcessing && <AgentIndicator agent={activeAgent} isProcessing={isProcessing} />}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div style={{
        padding: '0.75rem', borderTop: '1px solid var(--color-border)',
        display: 'flex', gap: '0.5rem',
      }}>
        <input
          ref={inputRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isProcessing ? 'Processing...' : 'Ask about your data...'}
          disabled={isProcessing}
          style={{
            flex: 1, padding: '0.5rem 0.75rem', fontSize: '0.85rem',
            border: '1px solid var(--color-border)', borderRadius: 'var(--radius)',
            outline: 'none', background: 'var(--color-bg)',
          }}
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || isProcessing}
          style={{
            padding: '0.5rem 1rem', fontSize: '0.85rem',
            background: input.trim() && !isProcessing ? 'var(--color-primary)' : 'var(--color-border)',
            color: '#fff', border: 'none', borderRadius: 'var(--radius)',
            cursor: input.trim() && !isProcessing ? 'pointer' : 'not-allowed',
          }}
        >
          Send
        </button>
      </div>
    </div>
  )
}
