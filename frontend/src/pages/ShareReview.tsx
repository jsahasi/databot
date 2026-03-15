import { useState, useEffect, useCallback } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import DOMPurify from 'dompurify'

interface Recipient {
  email: string
  approved: boolean | null
  rating: number | null
  responded_at: string | null
}

interface Comment {
  id: number
  author_email: string
  content: string
  created_at: string
}

interface ShareData {
  id: string
  title: string
  content_html: string
  admin_email: string
  created_at: string
  expires_at: string
  all_approved: boolean
  recipients: Recipient[]
  comments: Comment[]
}

const COLORS = {
  bg: '#f8f9fc',
  card: '#ffffff',
  border: '#e2e6ef',
  primary: '#4f46e5',
  green: '#059669',
  red: '#dc2626',
  amber: '#d97706',
  gold: '#f59e0b',
  text: '#1a1d2e',
  secondary: '#6b7280',
}

function StarIcon({ filled, onClick }: { filled: boolean; onClick: () => void }) {
  return (
    <svg
      onClick={onClick}
      width="28" height="28" viewBox="0 0 24 24"
      fill={filled ? COLORS.gold : 'none'}
      stroke={filled ? COLORS.gold : COLORS.secondary}
      strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
      style={{ cursor: 'pointer', transition: 'transform 0.1s' }}
      onMouseEnter={e => { (e.currentTarget as SVGElement).style.transform = 'scale(1.15)' }}
      onMouseLeave={e => { (e.currentTarget as SVGElement).style.transform = 'scale(1)' }}
    >
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
    </svg>
  )
}

function ThumbsUpIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14z"/>
      <path d="M7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/>
    </svg>
  )
}

function ThumbsDownIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3H10z"/>
      <path d="M17 2h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"/>
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={COLORS.green} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12"/>
    </svg>
  )
}

function XIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={COLORS.red} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
    </svg>
  )
}

function ClockIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={COLORS.secondary} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
    </svg>
  )
}

function MiniStars({ rating }: { rating: number | null }) {
  if (!rating) return null
  return (
    <span style={{ display: 'inline-flex', gap: 1, marginLeft: 6 }}>
      {[1, 2, 3, 4, 5].map(i => (
        <svg key={i} width="12" height="12" viewBox="0 0 24 24" fill={i <= rating ? COLORS.gold : 'none'} stroke={i <= rating ? COLORS.gold : '#d1d5db'} strokeWidth="1.5">
          <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
        </svg>
      ))}
    </span>
  )
}

export default function ShareReview() {
  const { shareId } = useParams<{ shareId: string }>()
  const [searchParams] = useSearchParams()
  const key = searchParams.get('key') || ''
  const email = searchParams.get('email') || ''

  const [data, setData] = useState<ShareData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [commentText, setCommentText] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [respondMessage, setRespondMessage] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch(`/api/shares/${shareId}?key=${encodeURIComponent(key)}&email=${encodeURIComponent(email)}`)
      if (res.status === 410) { setError('This link has expired'); setLoading(false); return }
      if (res.status === 403) { setError('Invalid link'); setLoading(false); return }
      if (res.status === 404) { setError('Not found'); setLoading(false); return }
      if (!res.ok) { setError('Something went wrong'); setLoading(false); return }
      const json = await res.json()
      setData(json)
      setError(null)
    } catch {
      setError('Failed to load')
    } finally {
      setLoading(false)
    }
  }, [shareId, key, email])

  useEffect(() => { fetchData() }, [fetchData])

  const currentRecipient = data?.recipients.find(r => r.email === email)
  const currentRating = currentRecipient?.rating ?? 0
  const currentApproval = currentRecipient?.approved ?? null

  const handleStarClick = async (starIndex: number) => {
    try {
      await fetch(`/api/shares/${shareId}/respond?key=${encodeURIComponent(key)}&email=${encodeURIComponent(email)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approved: currentApproval, rating: starIndex }),
      })
      await fetchData()
    } catch { /* ignore */ }
  }

  const handleApproval = async (approved: boolean) => {
    try {
      await fetch(`/api/shares/${shareId}/respond?key=${encodeURIComponent(key)}&email=${encodeURIComponent(email)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approved, rating: currentRating || null }),
      })
      setRespondMessage('Your response has been recorded')
      setTimeout(() => setRespondMessage(null), 3000)
      await fetchData()
    } catch { /* ignore */ }
  }

  const handleComment = async () => {
    if (!commentText.trim()) return
    setSubmitting(true)
    try {
      await fetch(`/api/shares/${shareId}/comments?key=${encodeURIComponent(key)}&email=${encodeURIComponent(email)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: commentText.trim() }),
      })
      setCommentText('')
      await fetchData()
    } catch { /* ignore */ }
    setSubmitting(false)
  }

  // Sanitize HTML for iframe
  const sanitizedHtml = data ? DOMPurify.sanitize(data.content_html, {
    FORBID_TAGS: ['script', 'iframe', 'object', 'embed', 'form', 'input'],
    FORBID_ATTR: ['onerror', 'onclick', 'onload', 'onmouseover'],
    ALLOW_DATA_ATTR: false,
    ADD_TAGS: ['img'],
    ADD_ATTR: ['src', 'alt', 'width', 'height'],
  }) : ''
  const iframeSrcdoc = `<style>body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;font-size:14px;line-height:1.7;max-width:720px;margin:auto;padding:2rem;color:#1a1d2e;}img{max-width:100%;height:auto;border-radius:8px;margin:1rem 0;}</style>${sanitizedHtml}`

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', background: COLORS.bg, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ fontSize: '1rem', color: COLORS.secondary }}>Loading...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ minHeight: '100vh', background: COLORS.bg, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{
          background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: 12,
          padding: '2.5rem 3rem', textAlign: 'center', maxWidth: 420,
        }}>
          <div style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>
            {error === 'This link has expired' ? '⏰' : '🔒'}
          </div>
          <div style={{ fontSize: '1.1rem', fontWeight: 700, color: COLORS.text, marginBottom: '0.5rem' }}>
            {error}
          </div>
          <div style={{ fontSize: '0.85rem', color: COLORS.secondary }}>
            {error === 'This link has expired'
              ? 'The sharing link is no longer valid. Please request a new one.'
              : 'You do not have access to this content.'}
          </div>
        </div>
      </div>
    )
  }

  if (!data) return null

  const truncateEmail = (e: string) => {
    if (e.length <= 24) return e
    const [local, domain] = e.split('@')
    if (!domain) return e.slice(0, 24) + '...'
    const truncLocal = local.length > 10 ? local.slice(0, 10) + '...' : local
    return `${truncLocal}@${domain}`
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: COLORS.bg,
      fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
      color: COLORS.text,
      padding: '2rem 1rem',
    }}>
      <div style={{ maxWidth: 900, margin: '0 auto' }}>
        {/* Header card */}
        <div style={{
          background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: 12,
          padding: '1.5rem 2rem', marginBottom: '1.25rem',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '0.5rem' }}>
            <h1 style={{ fontSize: '1.35rem', fontWeight: 700, margin: 0, color: COLORS.text }}>
              {data.title}
            </h1>
            {data.all_approved && (
              <span style={{
                fontSize: '0.72rem', fontWeight: 700, color: COLORS.green,
                background: `${COLORS.green}18`, padding: '0.2rem 0.65rem',
                borderRadius: 100, textTransform: 'uppercase', letterSpacing: '0.04em',
              }}>
                Approved
              </span>
            )}
          </div>
          <div style={{ fontSize: '0.82rem', color: COLORS.secondary }}>
            Shared by <strong style={{ color: COLORS.text, fontWeight: 600 }}>{data.admin_email}</strong>
          </div>
          <div style={{ fontSize: '0.75rem', color: COLORS.secondary, marginTop: '0.25rem' }}>
            Expires {new Date(data.expires_at).toLocaleDateString([], { month: 'long', day: 'numeric', year: 'numeric' })}
          </div>
        </div>

        {/* Content card */}
        <div style={{
          background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: 12,
          overflow: 'hidden', marginBottom: '1.25rem',
        }}>
          <div style={{ padding: '0.75rem 1.25rem', borderBottom: `1px solid ${COLORS.border}`, fontSize: '0.8rem', fontWeight: 600, color: COLORS.secondary, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Content
          </div>
          <iframe
            srcDoc={iframeSrcdoc}
            sandbox="allow-same-origin"
            title="Shared content"
            style={{ width: '100%', border: 'none', minHeight: 400 }}
          />
        </div>

        {/* Rating section */}
        <div style={{
          background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: 12,
          padding: '1.25rem 2rem', marginBottom: '1.25rem',
        }}>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, color: COLORS.text, marginBottom: '0.75rem' }}>
            Rate this content
          </div>
          <div style={{ display: 'flex', gap: '0.25rem', marginBottom: '1.25rem' }}>
            {[1, 2, 3, 4, 5].map(i => (
              <StarIcon key={i} filled={i <= currentRating} onClick={() => handleStarClick(i)} />
            ))}
          </div>

          {/* Approval buttons */}
          <div style={{ fontSize: '0.85rem', fontWeight: 600, color: COLORS.text, marginBottom: '0.75rem' }}>
            Approval
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <button
              onClick={() => handleApproval(true)}
              style={{
                display: 'flex', alignItems: 'center', gap: '0.5rem',
                padding: '0.65rem 1.5rem',
                fontSize: '0.85rem', fontWeight: 600,
                border: `2px solid ${currentApproval === true ? COLORS.green : COLORS.border}`,
                borderRadius: 10,
                background: currentApproval === true ? `${COLORS.green}12` : COLORS.card,
                color: currentApproval === true ? COLORS.green : COLORS.text,
                cursor: 'pointer',
                transition: 'all 0.15s',
              }}
            >
              <ThumbsUpIcon /> Approve
            </button>
            <button
              onClick={() => handleApproval(false)}
              style={{
                display: 'flex', alignItems: 'center', gap: '0.5rem',
                padding: '0.65rem 1.5rem',
                fontSize: '0.85rem', fontWeight: 600,
                border: `2px solid ${currentApproval === false ? COLORS.red : COLORS.border}`,
                borderRadius: 10,
                background: currentApproval === false ? `${COLORS.red}12` : COLORS.card,
                color: currentApproval === false ? COLORS.red : COLORS.text,
                cursor: 'pointer',
                transition: 'all 0.15s',
              }}
            >
              <ThumbsDownIcon /> Reject
            </button>
          </div>
          {respondMessage && (
            <div style={{ fontSize: '0.8rem', color: COLORS.green, marginTop: '0.75rem', fontWeight: 500 }}>
              {respondMessage}
            </div>
          )}
        </div>

        {/* Comments section */}
        <div style={{
          background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: 12,
          padding: '1.25rem 2rem', marginBottom: '1.25rem',
        }}>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, color: COLORS.text, marginBottom: '0.75rem' }}>
            Comments ({data.comments.length})
          </div>
          {data.comments.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1rem' }}>
              {data.comments.map(c => (
                <div key={c.id} style={{
                  padding: '0.65rem 0.85rem',
                  background: COLORS.bg, borderRadius: 8,
                  border: `1px solid ${COLORS.border}`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.3rem' }}>
                    <span style={{ fontSize: '0.75rem', fontWeight: 600, color: COLORS.primary }}>
                      {truncateEmail(c.author_email)}
                    </span>
                    <span style={{ fontSize: '0.68rem', color: COLORS.secondary }}>
                      {new Date(c.created_at).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.82rem', color: COLORS.text, lineHeight: 1.5 }}>
                    {c.content}
                  </div>
                </div>
              ))}
            </div>
          )}
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <textarea
              value={commentText}
              onChange={e => setCommentText(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleComment() } }}
              placeholder="Add a comment..."
              rows={2}
              style={{
                flex: 1,
                padding: '0.5rem 0.75rem',
                fontSize: '0.82rem',
                border: `1px solid ${COLORS.border}`,
                borderRadius: 8,
                background: COLORS.card,
                color: COLORS.text,
                resize: 'vertical',
                fontFamily: 'inherit',
                outline: 'none',
                lineHeight: 1.5,
              }}
              onFocus={e => { e.currentTarget.style.borderColor = COLORS.primary }}
              onBlur={e => { e.currentTarget.style.borderColor = COLORS.border }}
            />
            <button
              onClick={handleComment}
              disabled={submitting || !commentText.trim()}
              style={{
                padding: '0.5rem 1rem',
                fontSize: '0.82rem',
                fontWeight: 600,
                background: commentText.trim() && !submitting ? COLORS.primary : '#e5e7eb',
                color: '#fff',
                border: 'none',
                borderRadius: 8,
                cursor: commentText.trim() && !submitting ? 'pointer' : 'not-allowed',
                alignSelf: 'flex-end',
                whiteSpace: 'nowrap',
              }}
            >
              {submitting ? '...' : 'Submit'}
            </button>
          </div>
        </div>

        {/* Recipients section */}
        <div style={{
          background: COLORS.card, border: `1px solid ${COLORS.border}`, borderRadius: 12,
          padding: '1.25rem 2rem', marginBottom: '2rem',
        }}>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, color: COLORS.text, marginBottom: '0.75rem' }}>
            Recipients
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {data.recipients.map(r => (
              <div key={r.email} style={{
                display: 'flex', alignItems: 'center', gap: '0.5rem',
                padding: '0.45rem 0.65rem',
                borderRadius: 6,
                background: r.email === email ? `${COLORS.primary}08` : 'transparent',
              }}>
                {r.approved === true ? <CheckIcon /> : r.approved === false ? <XIcon /> : <ClockIcon />}
                <span style={{
                  fontSize: '0.8rem', color: COLORS.text,
                  fontWeight: r.email === email ? 600 : 400,
                }}>
                  {truncateEmail(r.email)}
                </span>
                <MiniStars rating={r.rating} />
                {r.email === email && (
                  <span style={{ fontSize: '0.65rem', color: COLORS.secondary, marginLeft: 'auto' }}>(you)</span>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
