import React, { useState, useRef, useEffect } from 'react'
import { useChatContext } from '../../context/ChatContext'
import ChatMessage from './ChatMessage'
import AgentIndicator from './AgentIndicator'

type AgentKey = 'data' | 'concierge' | 'config' | 'calendar' | 'content' | 'neutral'

const AGENT_COLORS: Record<AgentKey, { border: string; bg: string; hoverBg: string; hoverBorder: string }> = {
  data:      { border: '#6366f1', bg: 'rgba(99,102,241,0.07)',  hoverBg: 'rgba(99,102,241,0.13)',  hoverBorder: '#6366f1' },
  concierge: { border: '#f59e0b', bg: 'rgba(245,158,11,0.07)',  hoverBg: 'rgba(245,158,11,0.13)',  hoverBorder: '#f59e0b' },
  config:    { border: '#10b981', bg: 'rgba(16,185,129,0.07)',  hoverBg: 'rgba(16,185,129,0.13)',  hoverBorder: '#10b981' },
  calendar:  { border: '#8b5cf6', bg: 'rgba(139,92,246,0.07)', hoverBg: 'rgba(139,92,246,0.13)',  hoverBorder: '#8b5cf6' },
  content:   { border: '#ec4899', bg: 'rgba(236,72,153,0.07)', hoverBg: 'rgba(236,72,153,0.13)',  hoverBorder: '#ec4899' },
  neutral:   { border: 'var(--color-border)', bg: 'var(--color-card)', hoverBg: 'var(--color-chip-hover-bg)', hoverBorder: 'var(--color-border)' },
}

const SMART_TIPS_URL = 'https://wcc.on24.com/webcast/keyinsightssummary'

const SUGGESTIONS: { text: string; agent: AgentKey; href?: string }[] = [
  { text: 'Recent events',             agent: 'concierge'                    },
  { text: 'Experiences',               agent: 'config'                       },
  { text: 'How do I ...? (ON24 help)',  agent: 'concierge'                    },
  { text: 'Configure environment',     agent: 'config'                       },
  { text: 'Trends',                    agent: 'data'                         },
  { text: 'Insights',                  agent: 'data',  href: SMART_TIPS_URL  },
  { text: 'Event data exploration',    agent: 'data'                         },
  { text: 'Explore Content',           agent: 'content'                      },
]

const EXPERIENCE_LINKS = [
  { label: 'Elite — Webinars',        url: 'https://wcc.on24.com/webcast/webcasts' },
  { label: 'Engagement Hub',          url: 'https://wccv.on24.com/webcast/managemychannel' },
  { label: 'Target — Landing Pages',  url: 'https://wccv.on24.com/webcast/gatewayexperience' },
  { label: 'GoLive — Virtual Events', url: 'https://wccgl.on24.com/webcast/events' },
]

const CONFIG_LINKS = [
  { label: 'Media Manager',         url: 'https://wccv.on24.com/webcast/mediamanager' },
  { label: 'Segment Builder',       url: 'https://segment.on24.com/segments/segments' },
  { label: 'Connect / Integrations',url: 'https://wcc.on24.com/webcast/integrations' },
  { label: 'Branding',              url: 'https://wcc.on24.com/webcast/accountdashboard?tab=branding&clientId=10710' },
  { label: 'Manage Users',          url: 'https://wcc.on24.com/webcast/manageusers' },
]

export default function ChatPanel() {
  const { messages, isProcessing, activeAgent, sendMessage, openCalendar, resetChat } = useChatContext()
  const [input, setInput] = useState('')
  const [showHowDoI, setShowHowDoI] = useState(false)
  const [showExperiences, setShowExperiences] = useState(false)
  const [showConfigureEnv, setShowConfigureEnv] = useState(false)
  const [showExploreContent, setShowExploreContent] = useState(false)
  const [showContentCreate, setShowContentCreate] = useState(false)
  const [showContentExplore, setShowContentExplore] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const HOW_DO_I_OPTIONS = [
    'How do I set up a webinar?',
    'How do I set up polls for my event?',
    'How do I configure a registration page?',
    'How do I set up an integration?',
    'How do I view my event analytics?',
    'How do I create an Engagement Hub?',
    'How do I prepare as a presenter?',
    'How do I use Connect integrations?',
  ]

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Restore focus to input whenever processing finishes
  useEffect(() => {
    if (!isProcessing) {
      inputRef.current?.focus()
    }
  }, [isProcessing])

  const handleSend = () => {
    const trimmed = input.trim()
    if (!trimmed) return
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
      background: 'var(--color-bg)',
      backgroundImage: 'radial-gradient(var(--color-border) 1px, transparent 1px)',
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
              <svg aria-hidden="true" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
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
              Hi, Jayesh! What would you like to explore?
            </h2>

            {/* Suggestion tiles — 2-column grid */}
            {!showHowDoI && !showExperiences && !showConfigureEnv && !showExploreContent && !showContentCreate && !showContentExplore ? (
              <div style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '0.625rem',
                width: '100%',
                maxWidth: 680,
              }}>
                {SUGGESTIONS.map(({ text: s, agent, href }, i) => {
                  const c = AGENT_COLORS[agent]
                  return (
                    <button
                      key={i}
                      aria-label={`Suggest: ${s}`}
                      onClick={() => {
                        if (s === 'Recent events' || s === 'View proposed calendar') { openCalendar() }
                        else if (s === 'How do I ...? (ON24 help)') { setShowHowDoI(true) }
                        else if (s === 'Experiences') { setShowExperiences(true) }
                        else if (s === 'Configure environment') { setShowConfigureEnv(true) }
                        else if (s === 'Explore Content') { setShowExploreContent(true) }
                        else if (s === 'Event data exploration') { sendMessage('What is the event ID?'); setInput('') }
                        else if (href) { window.open(href, '_blank', 'noreferrer') }
                        else { sendMessage(s); setInput('') }
                      }}
                      style={{
                        padding: '0.875rem 1rem',
                        background: c.bg,
                        border: `1px solid ${c.border}`,
                        borderLeft: `3px solid ${c.border}`,
                        borderRadius: 8,
                        color: 'var(--color-chip-text)',
                        fontSize: '0.825rem',
                        fontWeight: 500,
                        textAlign: 'left',
                        cursor: 'pointer',
                        lineHeight: 1.4,
                        transition: 'border-color 0.12s, background 0.12s',
                        boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
                      }}
                      onMouseEnter={e => {
                        (e.currentTarget as HTMLButtonElement).style.background = c.hoverBg
                      }}
                      onMouseLeave={e => {
                        (e.currentTarget as HTMLButtonElement).style.background = c.bg
                      }}
                    >
                      {s}{href ? ' ↗' : ''}
                    </button>
                  )
                })}
              </div>
            ) : showExperiences ? (
              /* Experiences sub-menu */
              <div style={{ width: '100%', maxWidth: 680 }}>
                <button
                  onClick={() => setShowExperiences(false)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '0.375rem',
                    background: 'none', border: 'none', cursor: 'pointer',
                    color: AGENT_COLORS.config.border, fontSize: '0.8rem', fontWeight: 500,
                    marginBottom: '0.75rem', padding: 0,
                  }}
                >
                  <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M19 12H5M12 19l-7-7 7-7" />
                  </svg>
                  Back
                </button>
                <p style={{ fontSize: '0.85rem', fontWeight: 600, color: '#374151', marginBottom: '0.75rem' }}>
                  Which ON24 experience?
                </p>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.625rem' }}>
                  {EXPERIENCE_LINKS.map(({ label, url }) => (
                    <a
                      key={label}
                      href={url}
                      target="_blank"
                      rel="noreferrer"
                      style={{
                        padding: '0.875rem 1rem',
                        background: AGENT_COLORS.config.bg,
                        border: `1px solid ${AGENT_COLORS.config.border}`,
                        borderLeft: `3px solid ${AGENT_COLORS.config.border}`,
                        borderRadius: 8,
                        color: 'var(--color-chip-text)',
                        fontSize: '0.825rem',
                        fontWeight: 500,
                        textAlign: 'left',
                        cursor: 'pointer',
                        lineHeight: 1.4,
                        textDecoration: 'none',
                        display: 'block',
                        transition: 'background 0.12s',
                        boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
                      }}
                      onMouseEnter={e => { (e.currentTarget as HTMLAnchorElement).style.background = AGENT_COLORS.config.hoverBg }}
                      onMouseLeave={e => { (e.currentTarget as HTMLAnchorElement).style.background = AGENT_COLORS.config.bg }}
                    >
                      {label} ↗
                    </a>
                  ))}
                </div>
              </div>
            ) : showConfigureEnv ? (
              /* Configure environment sub-menu */
              <div style={{ width: '100%', maxWidth: 680 }}>
                <button
                  onClick={() => setShowConfigureEnv(false)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '0.375rem',
                    background: 'none', border: 'none', cursor: 'pointer',
                    color: AGENT_COLORS.config.border, fontSize: '0.8rem', fontWeight: 500,
                    marginBottom: '0.75rem', padding: 0,
                  }}
                >
                  <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M19 12H5M12 19l-7-7 7-7" />
                  </svg>
                  Back
                </button>
                <p style={{ fontSize: '0.85rem', fontWeight: 600, color: '#374151', marginBottom: '0.75rem' }}>
                  What would you like to configure?
                </p>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.625rem' }}>
                  {CONFIG_LINKS.map(({ label, url }) => (
                    <a
                      key={label}
                      href={url}
                      target="_blank"
                      rel="noreferrer"
                      style={{
                        padding: '0.875rem 1rem',
                        background: AGENT_COLORS.config.bg,
                        border: `1px solid ${AGENT_COLORS.config.border}`,
                        borderLeft: `3px solid ${AGENT_COLORS.config.border}`,
                        borderRadius: 8,
                        color: 'var(--color-chip-text)',
                        fontSize: '0.825rem',
                        fontWeight: 500,
                        textAlign: 'left',
                        cursor: 'pointer',
                        lineHeight: 1.4,
                        textDecoration: 'none',
                        display: 'block',
                        transition: 'background 0.12s',
                        boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
                      }}
                      onMouseEnter={e => { (e.currentTarget as HTMLAnchorElement).style.background = AGENT_COLORS.config.hoverBg }}
                      onMouseLeave={e => { (e.currentTarget as HTMLAnchorElement).style.background = AGENT_COLORS.config.bg }}
                    >
                      {label} ↗
                    </a>
                  ))}
                </div>
              </div>
            ) : showExploreContent ? (
              /* Explore Content top-level: Create new | Explore existing */
              <div style={{ width: '100%', maxWidth: 680 }}>
                <button
                  onClick={() => setShowExploreContent(false)}
                  style={{ display:'flex', alignItems:'center', gap:'0.375rem', background:'none', border:'none', cursor:'pointer', color: AGENT_COLORS.content.border, fontSize:'0.8rem', fontWeight:500, marginBottom:'0.75rem', padding:0 }}
                >
                  <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
                  Back
                </button>
                <p style={{ fontSize:'0.85rem', fontWeight:600, color:'var(--color-text)', marginBottom:'0.75rem' }}>
                  What would you like to do?
                </p>
                <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'0.625rem' }}>
                  {[
                    { label: 'Create new content', desc: 'Scripts, blogs, social posts, eBooks — written in your brand voice', action: () => { setShowExploreContent(false); setShowContentCreate(true) } },
                    { label: 'Explore existing content', desc: 'Browse AI-generated articles from your past webinars', action: () => { setShowExploreContent(false); setShowContentExplore(true) } },
                    { label: 'Propose content calendar', desc: 'Suggest a 3-month webinar plan based on your best-performing topics and audience', action: () => { sendMessage('Propose a content calendar for the next 3 months. Analyze my existing webinar cadence and top-performing topics, then suggest a schedule with ~10% more events, balanced across funnel stages (TOFU, MOFU, BOFU), and ranked by normalized engagement score. Explain why you proposed each event and what assumptions you made.'); setInput(''); setShowExploreContent(false) } },
                  ].map(({ label, desc, action }) => (
                    <button key={label} onClick={action}
                      style={{ padding:'0.875rem 1rem', background: AGENT_COLORS.content.bg, border:`1px solid ${AGENT_COLORS.content.border}`, borderLeft:`3px solid ${AGENT_COLORS.content.border}`, borderRadius:8, color:'var(--color-chip-text)', fontSize:'0.825rem', fontWeight:500, textAlign:'left', cursor:'pointer', lineHeight:1.4, transition:'background 0.12s', boxShadow:'0 1px 2px rgba(0,0,0,0.04)' }}
                      onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = AGENT_COLORS.content.hoverBg }}
                      onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = AGENT_COLORS.content.bg }}
                    >
                      <div style={{ fontWeight:600 }}>{label}</div>
                      <div style={{ fontSize:'0.75rem', color:'var(--color-text-secondary)', marginTop:'0.25rem', fontWeight:400 }}>{desc}</div>
                    </button>
                  ))}
                </div>
              </div>

            ) : showContentCreate ? (
              /* Create new content — pick article type */
              <div style={{ width:'100%', maxWidth:680 }}>
                <button onClick={() => { setShowContentCreate(false); setShowExploreContent(true) }}
                  style={{ display:'flex', alignItems:'center', gap:'0.375rem', background:'none', border:'none', cursor:'pointer', color: AGENT_COLORS.content.border, fontSize:'0.8rem', fontWeight:500, marginBottom:'0.75rem', padding:0 }}
                >
                  <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
                  Back
                </button>
                <p style={{ fontSize:'0.85rem', fontWeight:600, color:'var(--color-text)', marginBottom:'0.75rem' }}>
                  What type of content would you like to create?
                </p>
                <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'0.625rem' }}>
                  {[
                    { label:'Webinar script',      prompt:'I want to create a webinar script. What topic or event should it be based on?' },
                    { label:'Blog post',           prompt:'I want to write a blog post. What topic should it cover, and should it be based on a recent webinar?' },
                    { label:'Social media posts',  prompt:'I want to create social media posts. What event or topic should they promote?' },
                    { label:'eBook',               prompt:'I want to create an eBook. What topic or series of webinars should it be based on?' },
                  ].map(({ label, prompt }) => (
                    <button key={label}
                      onClick={() => { sendMessage(prompt); setInput(''); setShowContentCreate(false) }}
                      style={{ padding:'0.875rem 1rem', background: AGENT_COLORS.content.bg, border:`1px solid ${AGENT_COLORS.content.border}`, borderLeft:`3px solid ${AGENT_COLORS.content.border}`, borderRadius:8, color:'var(--color-chip-text)', fontSize:'0.825rem', fontWeight:600, textAlign:'left', cursor:'pointer', lineHeight:1.4, transition:'background 0.12s', boxShadow:'0 1px 2px rgba(0,0,0,0.04)' }}
                      onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = AGENT_COLORS.content.hoverBg }}
                      onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = AGENT_COLORS.content.bg }}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

            ) : showContentExplore ? (
              /* Explore existing AI-ACE content — pick article type */
              <div style={{ width:'100%', maxWidth:680 }}>
                <button onClick={() => { setShowContentExplore(false); setShowExploreContent(true) }}
                  style={{ display:'flex', alignItems:'center', gap:'0.375rem', background:'none', border:'none', cursor:'pointer', color: AGENT_COLORS.content.border, fontSize:'0.8rem', fontWeight:500, marginBottom:'0.75rem', padding:0 }}
                >
                  <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
                  Back
                </button>
                <p style={{ fontSize:'0.85rem', fontWeight:600, color:'var(--color-text)', marginBottom:'0.75rem' }}>
                  Which type of AI-generated content?
                </p>
                <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'0.625rem' }}>
                  {[
                    { label:'Key Takeaways',    prompt:'Show me the most recent AI-generated Key Takeaways articles' },
                    { label:'Blog Posts',       prompt:'Show me the most recent AI-generated blog posts' },
                    { label:'eBooks',           prompt:'Show me the most recent AI-generated eBooks' },
                    { label:'FAQs',             prompt:'Show me the most recent AI-generated FAQ articles' },
                    { label:'Follow-up Emails', prompt:'Show me the most recent AI-generated follow-up emails' },
                    { label:'Social Media',     prompt:'Show me the most recent AI-generated social media posts' },
                  ].map(({ label, prompt }) => (
                    <button key={label}
                      onClick={() => { sendMessage(prompt); setInput(''); setShowContentExplore(false) }}
                      style={{ padding:'0.875rem 1rem', background: AGENT_COLORS.content.bg, border:`1px solid ${AGENT_COLORS.content.border}`, borderLeft:`3px solid ${AGENT_COLORS.content.border}`, borderRadius:8, color:'var(--color-chip-text)', fontSize:'0.825rem', fontWeight:600, textAlign:'left', cursor:'pointer', lineHeight:1.4, transition:'background 0.12s', boxShadow:'0 1px 2px rgba(0,0,0,0.04)' }}
                      onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = AGENT_COLORS.content.hoverBg }}
                      onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = AGENT_COLORS.content.bg }}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

            ) : (
              /* "How do I...?" sub-menu */
              <div style={{ width: '100%', maxWidth: 680 }}>
                <button
                  onClick={() => setShowHowDoI(false)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '0.375rem',
                    background: 'none', border: 'none', cursor: 'pointer',
                    color: AGENT_COLORS.concierge.border, fontSize: '0.8rem', fontWeight: 500,
                    marginBottom: '0.75rem', padding: 0,
                  }}
                >
                  <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M19 12H5M12 19l-7-7 7-7" />
                  </svg>
                  Back
                </button>
                <p style={{ fontSize: '0.85rem', fontWeight: 600, color: '#374151', marginBottom: '0.75rem' }}>
                  What would you like help with?
                </p>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.625rem' }}>
                  {HOW_DO_I_OPTIONS.map((q, i) => (
                    <button
                      key={i}
                      aria-label={q}
                      onClick={() => { sendMessage(q); setInput(''); setShowHowDoI(false) }}
                      style={{
                        padding: '0.875rem 1rem',
                        background: AGENT_COLORS.concierge.bg,
                        border: `1px solid ${AGENT_COLORS.concierge.border}`,
                        borderLeft: `3px solid ${AGENT_COLORS.concierge.border}`,
                        borderRadius: 8,
                        color: 'var(--color-chip-text)',
                        fontSize: '0.825rem',
                        fontWeight: 500,
                        textAlign: 'left',
                        cursor: 'pointer',
                        lineHeight: 1.4,
                        transition: 'background 0.12s',
                        boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
                      }}
                      onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = AGENT_COLORS.concierge.hoverBg }}
                      onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = AGENT_COLORS.concierge.bg }}
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          /* Chat messages */
          <div role="log" aria-live="polite" aria-label="Chat messages" style={{ padding: '1.5rem 2rem', display: 'flex', flexDirection: 'column' }}>
            {messages.map((msg, idx) => {
              // Find the most recent user question before this assistant message
              let userQuestion = ''
              if (msg.role === 'assistant') {
                for (let i = idx - 1; i >= 0; i--) {
                  if (messages[i].role === 'user') { userQuestion = messages[i].content; break }
                }
              }
              return (
              <React.Fragment key={msg.id}>
                <ChatMessage message={msg} userQuestion={userQuestion} />
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
                        aria-label={`Suggest: ${s}`}
                        onClick={() => {
                          if (s === 'Home') { resetChat() }
                          else if (s === 'How do I...?') { setShowHowDoI(true) }
                          else if (s === 'Recent events' || s === 'View proposed calendar') { openCalendar() }
                          else { sendMessage(s); setInput('') }
                        }}
                        style={{
                          padding: '0.35rem 0.875rem',
                          fontSize: '0.775rem',
                          background: 'var(--color-chip-bg)',
                          border: '1px solid var(--color-chip-border)',
                          borderRadius: 20,
                          color: 'var(--color-chip-text)',
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
              )
            })}
            {isProcessing && <AgentIndicator agent={activeAgent} isProcessing={isProcessing} />}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input bar — pinned to bottom */}
      <div style={{
        flexShrink: 0,
        background: 'var(--color-card)',
        borderTop: '1px solid var(--color-border)',
        padding: '0.875rem 2rem',
      }}>
        {activeAgent && (
          <p aria-live="polite" aria-atomic="true" style={{ fontSize: '0.7rem', color: '#6b7280', marginBottom: '0.375rem' }}>
            {activeAgent.replace('_', ' ')} is thinking...
          </p>
        )}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
          {/* Attachment icon */}
          <button
            aria-label="Attach file"
            style={{
              flexShrink: 0,
              width: 36, height: 36,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              color: '#9ca3af',
              borderRadius: 6,
            }}
          >
            <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
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
            aria-label="Chat message input"
            autoFocus
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
            disabled={!input.trim()}
            aria-label="Send message"
            style={{
              flexShrink: 0,
              width: 36, height: 36,
              borderRadius: '50%',
              background: input.trim() ? 'var(--color-primary)' : '#e5e7eb',
              color: '#fff',
              border: 'none',
              cursor: input.trim() ? 'pointer' : 'not-allowed',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              transition: 'background 0.15s',
            }}
          >
            <svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}
