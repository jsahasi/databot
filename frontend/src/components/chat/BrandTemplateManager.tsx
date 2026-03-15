import { useState, useEffect, useCallback } from 'react'

interface BrandTemplate {
  id: string
  name: string
  primaryColor: string
  backgroundColor: string
  accentColor: string
  fontColor: string
  fontFamily: string
  logoUrl: string
  isDefault: boolean
  createdAt: string
}

interface Props {
  open: boolean
  onClose: () => void
}

const EMPTY_FORM = {
  name: '',
  primaryColor: '#4f46e5',
  backgroundColor: '#ffffff',
  accentColor: '#6366f1',
  fontColor: '#1a1d2e',
  fontFamily: 'Inter',
  logoUrl: '',
  isDefault: false,
}

export default function BrandTemplateManager({ open, onClose }: Props) {
  const [templates, setTemplates] = useState<BrandTemplate[]>([])
  const [fonts, setFonts] = useState<string[]>([])
  const [editing, setEditing] = useState<string | null>(null) // template id or 'new'
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)

  const fetchTemplates = useCallback(async () => {
    try {
      const res = await fetch('/api/brand-templates')
      const data = await res.json()
      setTemplates(data.templates || [])
    } catch { /* ignore */ }
  }, [])

  const fetchFonts = useCallback(async () => {
    try {
      const res = await fetch('/api/brand-templates/fonts')
      const data = await res.json()
      setFonts(data.fonts || [])
    } catch { /* ignore */ }
  }, [])

  useEffect(() => {
    if (open) {
      fetchTemplates()
      fetchFonts()
    }
  }, [open, fetchTemplates, fetchFonts])

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  const handleEdit = (t: BrandTemplate) => {
    setEditing(t.id)
    setForm({
      name: t.name,
      primaryColor: t.primaryColor,
      backgroundColor: t.backgroundColor,
      accentColor: t.accentColor,
      fontColor: t.fontColor,
      fontFamily: t.fontFamily,
      logoUrl: t.logoUrl,
      isDefault: t.isDefault,
    })
  }

  const handleNew = () => {
    setEditing('new')
    setForm(EMPTY_FORM)
  }

  const handleCancel = () => {
    setEditing(null)
    setForm(EMPTY_FORM)
  }

  const handleSave = async () => {
    if (!form.name.trim()) return
    setSaving(true)
    try {
      if (editing === 'new') {
        await fetch('/api/brand-templates', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(form),
        })
      } else {
        await fetch(`/api/brand-templates/${editing}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(form),
        })
      }
      await fetchTemplates()
      setEditing(null)
      setForm(EMPTY_FORM)
    } catch { /* ignore */ }
    setSaving(false)
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this template?')) return
    await fetch(`/api/brand-templates/${id}`, { method: 'DELETE' })
    await fetchTemplates()
  }

  if (!open) return null

  const colorField = (label: string, key: keyof typeof form) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
      <label style={{ fontSize: '0.75rem', fontWeight: 500, color: 'var(--color-text-secondary)', width: 90 }}>{label}</label>
      <input
        type="color"
        value={form[key] as string}
        onChange={e => setForm({ ...form, [key]: e.target.value })}
        style={{ width: 32, height: 28, border: '1px solid var(--color-border)', borderRadius: 4, cursor: 'pointer', padding: 0 }}
      />
      <input
        type="text"
        value={form[key] as string}
        onChange={e => setForm({ ...form, [key]: e.target.value })}
        style={{
          width: 80, padding: '0.25rem 0.4rem', fontSize: '0.75rem',
          border: '1px solid var(--color-border)', borderRadius: 4,
          background: 'var(--color-bg)', color: 'var(--color-text)',
          fontFamily: 'monospace',
        }}
      />
    </div>
  )

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Brand Template Manager"
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 9999,
        background: 'rgba(0,0,0,0.5)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '1rem',
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          width: '100%', maxWidth: 640, maxHeight: '85vh',
          display: 'flex', flexDirection: 'column',
          background: 'var(--color-card)', borderRadius: 12,
          border: '1px solid var(--color-border)',
          boxShadow: '0 20px 60px rgba(0,0,0,0.2)',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '0.75rem 1rem', borderBottom: '1px solid var(--color-border)', flexShrink: 0,
        }}>
          <span style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--color-heading, var(--color-text))' }}>
            Brand Templates
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <button
              onClick={handleNew}
              style={{
                padding: '0.3rem 0.75rem', fontSize: '0.75rem', fontWeight: 600,
                background: 'var(--color-primary)', color: '#fff', border: 'none',
                borderRadius: 6, cursor: 'pointer',
              }}
            >
              + Add Template
            </button>
            <button
              onClick={onClose}
              title="Close"
              aria-label="Close"
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-secondary)', padding: 4, display: 'flex', borderRadius: 4 }}
            >
              <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        </div>

        {/* Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '1rem' }}>
          {/* Edit/Create form */}
          {editing && (
            <div style={{
              background: 'var(--color-bg)', borderRadius: 10, border: '1px solid var(--color-border)',
              padding: '1rem', marginBottom: '1rem',
            }}>
              <div style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--color-text)', marginBottom: '0.75rem' }}>
                {editing === 'new' ? 'New Template' : 'Edit Template'}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {/* Name */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <label style={{ fontSize: '0.75rem', fontWeight: 500, color: 'var(--color-text-secondary)', width: 90 }}>Name</label>
                  <input
                    type="text"
                    value={form.name}
                    onChange={e => setForm({ ...form, name: e.target.value })}
                    placeholder="e.g. ON24 Corporate"
                    style={{
                      flex: 1, padding: '0.35rem 0.5rem', fontSize: '0.78rem',
                      border: '1px solid var(--color-border)', borderRadius: 6,
                      background: 'var(--color-card)', color: 'var(--color-text)', fontFamily: 'inherit',
                    }}
                  />
                </div>
                {colorField('Primary', 'primaryColor')}
                {colorField('Background', 'backgroundColor')}
                {colorField('Accent', 'accentColor')}
                {colorField('Font Color', 'fontColor')}
                {/* Font */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <label style={{ fontSize: '0.75rem', fontWeight: 500, color: 'var(--color-text-secondary)', width: 90 }}>Font</label>
                  <select
                    value={form.fontFamily}
                    onChange={e => setForm({ ...form, fontFamily: e.target.value })}
                    style={{
                      flex: 1, padding: '0.35rem 0.5rem', fontSize: '0.78rem',
                      border: '1px solid var(--color-border)', borderRadius: 6,
                      background: 'var(--color-card)', color: 'var(--color-text)', fontFamily: 'inherit',
                    }}
                  >
                    {fonts.map(f => <option key={f} value={f}>{f}</option>)}
                  </select>
                </div>
                {/* Logo URL */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <label style={{ fontSize: '0.75rem', fontWeight: 500, color: 'var(--color-text-secondary)', width: 90 }}>Logo URL</label>
                  <input
                    type="text"
                    value={form.logoUrl}
                    onChange={e => setForm({ ...form, logoUrl: e.target.value })}
                    placeholder="https://..."
                    style={{
                      flex: 1, padding: '0.35rem 0.5rem', fontSize: '0.78rem',
                      border: '1px solid var(--color-border)', borderRadius: 6,
                      background: 'var(--color-card)', color: 'var(--color-text)', fontFamily: 'inherit',
                    }}
                  />
                </div>
                {/* Default checkbox */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <label style={{ fontSize: '0.75rem', fontWeight: 500, color: 'var(--color-text-secondary)', width: 90 }}>Default</label>
                  <input
                    type="checkbox"
                    checked={form.isDefault}
                    onChange={e => setForm({ ...form, isDefault: e.target.checked })}
                    style={{ cursor: 'pointer' }}
                  />
                </div>
              </div>
              {/* Actions */}
              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem', justifyContent: 'flex-end' }}>
                <button
                  onClick={handleCancel}
                  style={{
                    padding: '0.35rem 0.75rem', fontSize: '0.75rem',
                    background: 'transparent', border: '1px solid var(--color-border)',
                    borderRadius: 6, cursor: 'pointer', color: 'var(--color-text-secondary)',
                  }}
                >
                  Cancel
                </button>
                <button
                  onClick={handleSave}
                  disabled={saving || !form.name.trim()}
                  style={{
                    padding: '0.35rem 0.75rem', fontSize: '0.75rem', fontWeight: 600,
                    background: form.name.trim() && !saving ? 'var(--color-primary)' : '#e5e7eb',
                    color: '#fff', border: 'none', borderRadius: 6,
                    cursor: form.name.trim() && !saving ? 'pointer' : 'not-allowed',
                  }}
                >
                  {saving ? 'Saving...' : 'Save'}
                </button>
              </div>
            </div>
          )}

          {/* Template cards */}
          {templates.length === 0 && !editing && (
            <div style={{ textAlign: 'center', padding: '2rem 0', color: 'var(--color-text-secondary)', fontSize: '0.82rem' }}>
              No templates yet. Click "+ Add Template" to create one.
            </div>
          )}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {templates.map(t => (
              <div key={t.id} style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '0.65rem 0.85rem', borderRadius: 10,
                border: `1px solid ${editing === t.id ? 'var(--color-primary)' : 'var(--color-border)'}`,
                background: 'var(--color-card)',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  {/* Color swatches */}
                  <div style={{ display: 'flex', gap: 3 }}>
                    {[t.primaryColor, t.accentColor, t.backgroundColor, t.fontColor].map((c, i) => (
                      <div key={i} style={{
                        width: 16, height: 16, borderRadius: 3,
                        background: c, border: '1px solid var(--color-border)',
                      }} title={c} />
                    ))}
                  </div>
                  <div>
                    <div style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--color-text)' }}>
                      {t.name}
                      {t.isDefault && (
                        <span style={{
                          marginLeft: '0.4rem', fontSize: '0.6rem', fontWeight: 700,
                          color: '#10b981', background: 'rgba(16,185,129,0.1)',
                          padding: '0.1rem 0.35rem', borderRadius: 3, textTransform: 'uppercase',
                        }}>
                          Default
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: '0.68rem', color: 'var(--color-text-secondary)' }}>
                      {t.fontFamily}
                    </div>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '0.35rem' }}>
                  <button
                    onClick={() => handleEdit(t)}
                    title="Edit"
                    style={{
                      padding: '0.25rem 0.5rem', fontSize: '0.7rem', fontWeight: 500,
                      background: 'transparent', border: '1px solid var(--color-border)',
                      borderRadius: 5, cursor: 'pointer', color: 'var(--color-text-secondary)',
                    }}
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(t.id)}
                    title="Delete"
                    style={{
                      padding: '0.25rem 0.5rem', fontSize: '0.7rem', fontWeight: 500,
                      background: 'transparent', border: '1px solid var(--color-border)',
                      borderRadius: 5, cursor: 'pointer', color: '#ef4444',
                    }}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
