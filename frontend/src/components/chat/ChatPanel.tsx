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
  { text: 'Create Content',            agent: 'content'                      },
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

// Permission → UI element mapping for filtering
const PERM_FILTER: Record<string, string[]> = {
  'view-webcasts':             ['Elite — Webinars'],
  'manage-engagement-hub':    ['Engagement Hub'],
  'manage-target-experiences': ['Target — Landing Pages'],
  'manage-virtual-events':    ['GoLive — Virtual Events'],
  'manage-brand-settings':    ['Branding'],
  'manage-integrations':      ['Connect / Integrations'],
  'manage-users':             ['Manage Users'],
}

function filterByPermissions<T extends { label: string }>(items: T[], perms: string[]): T[] {
  // If no admin selected (perms empty), show everything
  if (perms.length === 0) return items
  // Build set of labels to hide (permission exists but is NOT in the admin's active perms)
  const hiddenLabels = new Set<string>()
  for (const [perm, labels] of Object.entries(PERM_FILTER)) {
    if (!perms.includes(perm)) {
      labels.forEach(l => hiddenLabels.add(l))
    }
  }
  return items.filter(item => !hiddenLabels.has(item.label))
}

export default function ChatPanel() {
  const { messages, isProcessing, activeAgent, sendMessage, openCalendar, openProposedCalendar, setProposedEvents, resetChat } = useChatContext()
  const [input, setInput] = useState('')
  const [showHowDoI, setShowHowDoI] = useState(false)
  const [showExperiences, setShowExperiences] = useState(false)
  const [showConfigureEnv, setShowConfigureEnv] = useState(false)
  const [showTrends, setShowTrends] = useState(false)
  const [showExploreContent, setShowExploreContent] = useState(false)
  const [showContentCreate, setShowContentCreate] = useState(false)
  const [showContentExplore, setShowContentExplore] = useState(false)
  const [attachment, setAttachment] = useState<{ name: string; extractedText?: string | null } | null>(null)
  const [uploading, setUploading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

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

  // Read permissions + admin info from sessionStorage (set by TopNav on admin selection)
  const storedPerms: string[] = JSON.parse(sessionStorage.getItem('adminPermissions') || '[]')
  const adminInfo: { email: string; name: string; profile: string } | null = JSON.parse(sessionStorage.getItem('adminInfo') || 'null')

  const PERM_LABELS: Record<string, string> = {
    'create-event': 'Create events', 'view-analytics': 'View analytics',
    'view-event-analytics': 'View event analytics', 'view-webcasts': 'View Elite webcasts',
    'manage-brand-settings': 'Manage branding', 'manage-engagement-hub': 'Manage Engagement Hub',
    'manage-target-experiences': 'Manage Target', 'manage-virtual-events': 'Manage GoLive',
    'manage-integrations': 'Manage integrations', 'manage-users': 'Manage users',
    'manage-meetups': 'Manage Forums', 'elite-order-services': 'Order Elite services',
    'manage-audience-console': 'Manage Audience Console',
  }
  const filteredExperiences = filterByPermissions(EXPERIENCE_LINKS, storedPerms)
  const filteredConfigLinks = filterByPermissions(CONFIG_LINKS, storedPerms)
  const hasAnalytics = storedPerms.length === 0 || storedPerms.includes('view-analytics')
  const filteredSuggestions = SUGGESTIONS.filter(s => {
    if (s.text === 'Experiences' && filteredExperiences.length === 0) return false
    if (s.text === 'Configure environment' && filteredConfigLinks.length === 0) return false
    // Hide data agent tiles if no view-analytics permission
    if (!hasAnalytics && s.agent === 'data') return false
    return true
  })
  const filteredHowDoI = HOW_DO_I_OPTIONS.filter(opt => {
    if (storedPerms.length === 0) return true
    if (opt.includes('Engagement Hub') && !storedPerms.includes('manage-engagement-hub')) return false
    if (opt.includes('Connect integrations') && !storedPerms.includes('manage-integrations')) return false
    return true
  })

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // When a message arrives with proposedEvents, store them in context and auto-open calendar
  useEffect(() => {
    const last = messages[messages.length - 1]
    if (last?.role === 'assistant' && last.proposedEvents?.length) {
      setProposedEvents(last.proposedEvents)
      openProposedCalendar()
    }
  }, [messages, setProposedEvents, openProposedCalendar])

  // Restore focus to input whenever processing finishes
  useEffect(() => {
    if (!isProcessing) {
      inputRef.current?.focus()
    }
  }, [isProcessing])

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    e.target.value = '' // reset so same file can be re-selected
    setUploading(true)
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch('/api/upload', { method: 'POST', body: form })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Upload failed' }))
        alert(err.detail || 'Upload failed')
        return
      }
      const data = await res.json()
      setAttachment({ name: data.original_name, extractedText: data.extracted_text })
    } catch {
      alert('Upload failed — check your connection')
    } finally {
      setUploading(false)
    }
  }

  const handleSend = () => {
    const trimmed = input.trim()
    if (!trimmed && !attachment) return
    let content = trimmed
    let displayText: string | undefined
    if (attachment) {
      displayText = trimmed ? `${trimmed} [attached: ${attachment.name}]` : `[attached: ${attachment.name}]`
      if (attachment.extractedText) {
        content = `${trimmed}\n\n[Attached PDF: ${attachment.name}]\nContent:\n${attachment.extractedText}`
      } else {
        content = `${trimmed}\n\n[Attached file: ${attachment.name}]`
      }
      setAttachment(null)
    }
    sendMessage(content, displayText)
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
            {!showHowDoI && !showExperiences && !showConfigureEnv && !showTrends && !showExploreContent && !showContentCreate && !showContentExplore ? (
              <>
              <div style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '0.625rem',
                width: '100%',
                maxWidth: 680,
              }}>
                {filteredSuggestions.map(({ text: s, agent, href }, i) => {
                  const c = AGENT_COLORS[agent]
                  return (
                    <button
                      key={i}
                      aria-label={`Suggest: ${s}`}
                      onClick={() => {
                        if (s === 'Recent events') { openCalendar() }
                        else if (s === 'View proposed calendar') { openProposedCalendar() }
                        else if (s === 'How do I ...? (ON24 help)') { setShowHowDoI(true) }
                        else if (s === 'Experiences') { setShowExperiences(true) }
                        else if (s === 'Configure environment') { setShowConfigureEnv(true) }
                        else if (s === 'Trends') { setShowTrends(true) }
                        else if (s === 'Explore Content') { setShowContentExplore(true) }
                        else if (s === 'Create Content') { setShowContentCreate(true) }
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
              {adminInfo && storedPerms.length > 0 && (
                <div style={{ marginTop: '1.25rem', width: '100%', maxWidth: 680 }}>
                  <p style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-secondary)', marginBottom: '0.375rem' }}>
                    Login Permissions — {adminInfo.name} ({adminInfo.profile})
                  </p>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
                    {storedPerms.map(p => (
                      <span key={p} style={{
                        fontSize: '0.65rem', padding: '0.15rem 0.5rem', borderRadius: 4,
                        background: 'rgba(99,102,241,0.08)', color: 'var(--color-text-secondary)',
                      }}>
                        {PERM_LABELS[p] || p}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </>
            ) : showTrends ? (
              /* Trends sub-menu */
              <div style={{ width: '100%', maxWidth: 680 }}>
                <button
                  onClick={() => setShowTrends(false)}
                  style={{ display:'flex', alignItems:'center', gap:'0.375rem', background:'none', border:'none', cursor:'pointer', color: AGENT_COLORS.data.border, fontSize:'0.8rem', fontWeight:500, marginBottom:'0.75rem', padding:0 }}
                >
                  <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
                  Back
                </button>
                <p style={{ fontSize:'0.85rem', fontWeight:600, color:'var(--color-text)', marginBottom:'0.75rem' }}>
                  What trend would you like to see?
                </p>
                <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'0.625rem' }}>
                  {[
                    { label: 'Attendance over time',       prompt: 'Show me attendance trends over the last 12 months as a line chart. Use get_attendance_trends with months=12, then generate_chart_data with chart_type="line", x_key="period", y_keys=["attendees"]. Title: "Attendance Over Time".', display: 'Attendance over time' },
                    { label: 'Registrations over time',    prompt: 'Show me registration trends over the last 12 months as a line chart. Use get_attendance_trends with months=12, then generate_chart_data with chart_type="line", x_key="period", y_keys=["registrants"]. Title: "Registrations Over Time".', display: 'Registrations over time' },
                    { label: 'Engagement scores over time', prompt: 'Show me average engagement score trends over the last 12 months as a line chart. Use get_attendance_trends with months=12, then generate_chart_data with chart_type="line", x_key="period", y_keys=["avg_engagement"]. Title: "Avg Engagement Score Over Time".', display: 'Engagement scores over time' },
                    { label: 'Show funnel',                prompt: 'Show me events by funnel stage for the last month. Use get_events_by_tag with tag_type="funnel", aggregate=true, months=1. Then show a bar chart with the funnel stages on the x-axis and total attendees on the y-axis. Title it "Leads by Funnel Stage — Last 30 Days".', display: 'Show funnel stages' },
                    { label: 'Show campaigns',             prompt: 'Show me events by campaign tag for the last month. Use get_events_by_tag with tag_type="campaign", aggregate=true, months=1. Then show a pie chart of total attendees per campaign tag. Title it "Leads by Campaign — Last 30 Days".', display: 'Show campaigns' },
                    { label: 'Performance by tags',        prompt: 'Show me performance by all tags used in the last month. Use get_events_by_tag with aggregate=true, months=1. List all tags with their event count, average engagement score, total registrants, and total attendees. Then show a bar chart of avg engagement by tag.', display: 'Performance by tags — last month' },
                    { label: 'Top events by engagement',   prompt: 'Show me the top 10 events by engagement score as a bar chart.', display: 'Top events by engagement' },
                    { label: 'Poll trends',      prompt: 'Poll trends', display: 'Poll trends' },
                  ].map(({ label, prompt, display }) => (
                    <button key={label}
                      onClick={() => { sendMessage(prompt, display); setInput(''); setShowTrends(false) }}
                      style={{ padding:'0.875rem 1rem', background: AGENT_COLORS.data.bg, border:`1px solid ${AGENT_COLORS.data.border}`, borderLeft:`3px solid ${AGENT_COLORS.data.border}`, borderRadius:8, color:'var(--color-chip-text)', fontSize:'0.825rem', fontWeight:600, textAlign:'left', cursor:'pointer', lineHeight:1.4, transition:'background 0.12s', boxShadow:'0 1px 2px rgba(0,0,0,0.04)' }}
                      onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = AGENT_COLORS.data.hoverBg }}
                      onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = AGENT_COLORS.data.bg }}
                    >
                      {label}
                    </button>
                  ))}
                </div>
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
                  {filteredExperiences.map(({ label, url }) => (
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
                  {filteredConfigLinks.map(({ label, url }) => (
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
                    { label: 'Propose content calendar', desc: 'Suggest a 3-month webinar plan based on your best-performing topics and audience', action: () => { sendMessage('Propose a content calendar for the next 3 months. Analyze my existing webinar cadence and top-performing topics, then suggest a schedule with ~10% more events, balanced across funnel stages (TOFU, MOFU, BOFU), and ranked by normalized engagement score. Explain why you proposed each event and what assumptions you made.', 'Propose a content calendar for the next 3 months.'); setInput(''); setShowExploreContent(false) } },
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
                    { label:'Webinar script',      prompt:'Help me write a webinar script' },
                    { label:'Blog post',           prompt:'Help me write a blog post' },
                    { label:'Social media posts',  prompt:'Help me create social media posts' },
                    { label:'eBook',               prompt:'Help me create an eBook' },
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
                <button onClick={() => { setShowContentExplore(false) }}
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
                  {filteredHowDoI.map((q, i) => (
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
                          else if (s === 'Recent events') { openCalendar() }
                          else if (s === 'View proposed calendar') { openProposedCalendar() }
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
          <p id="chat-status" aria-live="polite" aria-atomic="true" style={{ fontSize: '0.7rem', color: 'var(--color-text-secondary)', marginBottom: '0.375rem' }}>
            {activeAgent.replace('_', ' ')} is thinking...
          </p>
        )}
        {attachment && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.375rem', fontSize: '0.75rem', color: '#6366f1' }}>
            <span style={{ background: 'rgba(99,102,241,0.1)', padding: '0.2rem 0.6rem', borderRadius: 12, display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
              {attachment.name}
              <button onClick={() => setAttachment(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#6366f1', fontSize: '0.85rem', padding: 0, lineHeight: 1 }}>&times;</button>
            </span>
          </div>
        )}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
          {/* Attachment icon */}
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.gif,.webp"
            style={{ display: 'none' }}
            onChange={handleFileSelect}
          />
          <button
            aria-label="Attach file"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            style={{
              flexShrink: 0,
              width: 36, height: 36,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: 'transparent',
              border: 'none',
              cursor: uploading ? 'wait' : 'pointer',
              color: attachment ? '#6366f1' : '#9ca3af',
              borderRadius: 6,
              opacity: uploading ? 0.5 : 1,
            }}
          >
            <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
            </svg>
          </button>

          {/* Text input */}
          <label htmlFor="chat-input" style={{ position: 'absolute', width: '1px', height: '1px', overflow: 'hidden', clip: 'rect(0,0,0,0)' }}>Type your message</label>
          <textarea
            id="chat-input"
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Or type your message to chat here..."
            aria-label="Type your message"
            aria-describedby={activeAgent ? 'chat-status' : undefined}
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
              color: 'var(--color-text)',
              caretColor: 'var(--color-text)',
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
