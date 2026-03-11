import React, { useState, useRef, useEffect } from 'react'
import { useChatContext } from '../../context/ChatContext'
import ChatMessage from './ChatMessage'
import AgentIndicator from './AgentIndicator'

const SUGGESTIONS = [
  'Show attendance trends',
  'Which events had the best engagement?',
  'How many events ran this month?',
  'Top audience companies',
  'Average engagement score',
  'Event registration rates',
  'Poll results overview',
  'Content performance insights',
]

export default function ChatPanel() {
  const { messages, isProcessing, activeAgent, sendMessage } = useChatContext()
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = () => {
    const trimmed = input.trim()
    if (!trimmed || isProcessing) return
    sendMessage(trimmed)
    setInput('')
    inputRef.current?.focus()
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const hasMessages = messages.length > 0

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      background: '#f9fafb',
      backgroundImage: 'radial-gradient(#d1d5db 1px, transparent 1px)',
      backgroundSize: '20px 20px',
      position: 'relative',
    }}>
      {/* Messages / Welcome area */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
      }}>
        {!hasMessages ? (
          /* Welcome state */
          <div style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '3rem 2rem 6rem',
          }}>
            {/* Bot avatar */}
            <div style={{
              width: 56, height: 56,
              borderRadius: '50%',
              background: 'var(--color-primary)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              marginBottom: '1.25rem',
              boxShadow: '0 4px 14px rgba(79, 70, 229, 0.35)',
            }}>
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                <circle cx="12" cy="16" r="1" fill="#fff" stroke="none" />
              </svg>
            </div>

            <h2 style={{
              fontSize: '1.25rem',
              fontWeight: 700,
              color: '#111827',
              marginBottom: '2rem',
              textAlign: 'center',
            }}>
              Hi, Jayesh! What would you like to do today?
            </h2>

            {/* Suggestion tiles — 2-column grid */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '0.625rem',
              width: '100%',
              maxWidth: 680,
            }}>
              {SUGGESTIONS.map((s, i) => (
                <button
                  key={i}
                  onClick={() => { sendMessage(s); setInput('') }}
                  style={{
                    padding: '0.875rem 1rem',
                    background: '#fff',
                    border: '1px solid #c7d2fe',
                    borderRadius: 8,
                    color: 'var(--color-primary-hover, #4338ca)',
                    fontSize: '0.825rem',
                    fontWeight: 500,
                    textAlign: 'left',
                    cursor: 'pointer',
                    lineHeight: 1.4,
                    transition: 'border-color 0.12s, background 0.12s',
                    boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
                  }}
                  onMouseEnter={e => {
                    (e.currentTarget as HTMLButtonElement).style.background = '#eef2ff'
                    ;(e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--color-primary)'
                  }}
                  onMouseLeave={e => {
                    (e.currentTarget as HTMLButtonElement).style.background = '#fff'
                    ;(e.currentTarget as HTMLButtonElement).style.borderColor = '#c7d2fe'
                  }}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* Chat messages */
          <div style={{ padding: '1.5rem 2rem', display: 'flex', flexDirection: 'column' }}>
            {messages.map(msg => (
              <React.Fragment key={msg.id}>
                <ChatMessage message={msg} />
                {msg.role === 'assistant' && msg.suggestions && msg.suggestions.length > 0 && (
                  <div style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: '0.375rem',
                    marginBottom: '1rem',
                    marginLeft: '0.5rem',
                  }}>
                    {msg.suggestions.map((s, i) => (
                      <button
                        key={i}
                        onClick={() => { sendMessage(s); setInput('') }}
                        style={{
                          padding: '0.35rem 0.875rem',
                          fontSize: '0.775rem',
                          background: '#fff',
                          border: '1px solid #c7d2fe',
                          borderRadius: 20,
                          color: '#4338ca',
                          cursor: 'pointer',
                          lineHeight: 1.4,
                          fontWeight: 500,
                        }}
                      >
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
        )}
      </div>

      {/* Input bar — pinned to bottom */}
      <div style={{
        flexShrink: 0,
        background: '#fff',
        borderTop: '1px solid #e5e7eb',
        padding: '0.875rem 2rem',
      }}>
        {activeAgent && (
          <p style={{ fontSize: '0.7rem', color: '#6b7280', marginBottom: '0.375rem' }}>
            {activeAgent.replace('_', ' ')} is thinking...
          </p>
        )}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
          {/* Attachment icon */}
          <button style={{
            flexShrink: 0,
            width: 36, height: 36,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: 'transparent',
            border: 'none',
            cursor: 'pointer',
            color: '#9ca3af',
            borderRadius: 6,
          }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
            </svg>
          </button>

          {/* Text input */}
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Or type your message to chat here..."
            disabled={isProcessing}
            rows={1}
            style={{
              flex: 1,
              padding: '0.625rem 0',
              fontSize: '0.875rem',
              border: 'none',
              outline: 'none',
              background: 'transparent',
              resize: 'none',
              lineHeight: 1.5,
              fontFamily: 'inherit',
              color: '#111827',
              maxHeight: 120,
              overflowY: 'auto',
            }}
          />

          {/* Send button */}
          <button
            onClick={handleSend}
            disabled={!input.trim() || isProcessing}
            style={{
              flexShrink: 0,
              width: 36, height: 36,
              borderRadius: '50%',
              background: input.trim() && !isProcessing ? 'var(--color-primary)' : '#e5e7eb',
              color: '#fff',
              border: 'none',
              cursor: input.trim() && !isProcessing ? 'pointer' : 'not-allowed',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              transition: 'background 0.15s',
            }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}
