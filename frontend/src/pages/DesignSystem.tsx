import { useState } from 'react'

// ─── Helpers ─────────────────────────────────────────────────────────────────

function getCssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

function Swatch({ name, cssVar }: { name: string; cssVar: string }) {
  const color = getCssVar(cssVar)
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.4rem 0' }}>
      <div style={{
        width: 40, height: 40, borderRadius: 8,
        background: `var(${cssVar})`,
        border: '1px solid var(--color-border)',
        flexShrink: 0,
      }} />
      <div>
        <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-text)' }}>{name}</div>
        <div style={{ fontSize: '0.7rem', color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)' }}>
          {cssVar} {'\u2192'} {color}
        </div>
      </div>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: '2.5rem' }}>
      <h2 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--color-text)', marginBottom: '1rem', paddingBottom: '0.5rem', borderBottom: '2px solid var(--color-border)' }}>
        {title}
      </h2>
      {children}
    </div>
  )
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function DesignSystem() {
  const [btnHover, setBtnHover] = useState('')

  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: '1.5rem' }}>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--color-text)', marginBottom: '0.25rem' }}>
        Design System
      </h1>
      <p style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)', marginBottom: '2rem' }}>
        Live tokens from global.css — always in sync with production. Source: ON24 Admin 2025 Figma.
      </p>

      {/* ── Colors ── */}
      <Section title="Colors">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.5rem' }}>
          <div>
            <h3 style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>Brand</h3>
            <Swatch name="Primary" cssVar="--color-primary" />
            <Swatch name="Primary Hover" cssVar="--color-primary-hover" />
            <Swatch name="Primary Light" cssVar="--color-primary-light" />
            <Swatch name="CTA" cssVar="--color-cta" />
            <Swatch name="CTA Hover" cssVar="--color-cta-hover" />
            <Swatch name="Accent" cssVar="--color-accent" />
          </div>
          <div>
            <h3 style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>Surfaces</h3>
            <Swatch name="Background" cssVar="--color-bg" />
            <Swatch name="Card" cssVar="--color-card" />
            <Swatch name="Muted" cssVar="--color-muted" />
            <Swatch name="Sidebar" cssVar="--color-sidebar" />
            <Swatch name="Border" cssVar="--color-border" />
            <Swatch name="Toggle BG" cssVar="--color-toggle-bg" />
          </div>
          <div>
            <h3 style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>Text</h3>
            <Swatch name="Text" cssVar="--color-text" />
            <Swatch name="Text Secondary" cssVar="--color-text-secondary" />
            <Swatch name="Sidebar Text" cssVar="--color-sidebar-text" />
            <Swatch name="Sidebar Active" cssVar="--color-sidebar-active" />
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.5rem', marginTop: '1.5rem' }}>
          <div>
            <h3 style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>Status</h3>
            <Swatch name="Success" cssVar="--color-success" />
            <Swatch name="Success BG" cssVar="--color-success-bg" />
            <Swatch name="Success Text" cssVar="--color-success-text" />
            <Swatch name="Warning" cssVar="--color-warning" />
            <Swatch name="Warning BG" cssVar="--color-warning-bg" />
            <Swatch name="Danger" cssVar="--color-danger" />
            <Swatch name="Danger BG" cssVar="--color-danger-bg" />
            <Swatch name="Danger Text" cssVar="--color-danger-text" />
          </div>
          <div>
            <h3 style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>Chips</h3>
            <Swatch name="Chip BG" cssVar="--color-chip-bg" />
            <Swatch name="Chip Border" cssVar="--color-chip-border" />
            <Swatch name="Chip Text" cssVar="--color-chip-text" />
            <Swatch name="Chip Hover" cssVar="--color-chip-hover-bg" />
          </div>
          <div>
            <h3 style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>Agents</h3>
            <Swatch name="Data" cssVar="--color-agent-data" />
            <Swatch name="Concierge" cssVar="--color-agent-concierge" />
            <Swatch name="Config" cssVar="--color-agent-config" />
            <Swatch name="Calendar" cssVar="--color-agent-calendar" />
            <Swatch name="Content" cssVar="--color-agent-content" />
          </div>
        </div>
      </Section>

      {/* ── Typography ── */}
      <Section title="Typography">
        <div style={{ background: 'var(--color-card)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius)', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div>
            <span style={{ fontSize: '0.65rem', color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)' }}>Title 1 — Open Sans 700 36px/44px</span>
            <div style={{ fontSize: '36px', fontWeight: 700, lineHeight: '44px', letterSpacing: '0.2px', color: 'var(--color-text)' }}>The quick brown fox</div>
          </div>
          <div>
            <span style={{ fontSize: '0.65rem', color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)' }}>Title 2 — Open Sans 700 24px/32px</span>
            <div style={{ fontSize: '24px', fontWeight: 700, lineHeight: '32px', letterSpacing: '0.2px', color: 'var(--color-text)' }}>The quick brown fox jumps over the lazy dog</div>
          </div>
          <div>
            <span style={{ fontSize: '0.65rem', color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)' }}>Title 3 — Open Sans 700 18px/24px</span>
            <div style={{ fontSize: '18px', fontWeight: 700, lineHeight: '24px', letterSpacing: '0.2px', color: 'var(--color-text)' }}>The quick brown fox jumps over the lazy dog</div>
          </div>
          <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: '1rem' }}>
            <span style={{ fontSize: '0.65rem', color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)' }}>Body Large — Open Sans 400 16px/24px</span>
            <div style={{ fontSize: '16px', fontWeight: 400, lineHeight: '24px', letterSpacing: '0.1px', color: 'var(--color-text)' }}>The quick brown fox jumps over the lazy dog. Pack my box with five dozen liquor jugs.</div>
          </div>
          <div>
            <span style={{ fontSize: '0.65rem', color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)' }}>Body Medium — Open Sans 400 14px/20px</span>
            <div style={{ fontSize: '14px', fontWeight: 400, lineHeight: '20px', letterSpacing: '0.1px', color: 'var(--color-text)' }}>The quick brown fox jumps over the lazy dog. Pack my box with five dozen liquor jugs.</div>
          </div>
          <div>
            <span style={{ fontSize: '0.65rem', color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)' }}>Body Small — Open Sans 400 12px/16px</span>
            <div style={{ fontSize: '12px', fontWeight: 400, lineHeight: '16px', letterSpacing: '0.1px', color: 'var(--color-text)' }}>The quick brown fox jumps over the lazy dog. Pack my box with five dozen liquor jugs.</div>
          </div>
          <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: '1rem' }}>
            <span style={{ fontSize: '0.65rem', color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)' }}>Monospace — Fira Code 400 14px</span>
            <div style={{ fontSize: '14px', fontWeight: 400, lineHeight: '20px', fontFamily: 'var(--font-mono)', color: 'var(--color-text)' }}>const primary = '#4A50DD';</div>
          </div>
        </div>
      </Section>

      {/* ── Buttons ── */}
      <Section title="Buttons">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', alignItems: 'center', marginBottom: '1rem' }}>
          {[
            { label: 'Primary', bg: 'var(--color-primary)', hover: 'var(--color-primary-hover)', color: '#fff', id: 'primary' },
            { label: 'CTA', bg: 'var(--color-cta)', hover: 'var(--color-cta-hover)', color: '#fff', id: 'cta' },
            { label: 'Success', bg: 'var(--color-success)', hover: 'var(--color-success-text)', color: '#fff', id: 'success' },
            { label: 'Danger', bg: 'var(--color-danger)', hover: 'var(--color-danger-text)', color: '#fff', id: 'danger' },
          ].map(b => (
            <button key={b.id}
              onMouseEnter={() => setBtnHover(b.id)} onMouseLeave={() => setBtnHover('')}
              style={{
                padding: '0.5rem 1.25rem', borderRadius: 'var(--radius)', border: 'none', cursor: 'pointer',
                fontSize: '14px', fontWeight: 600, letterSpacing: '0.2px', lineHeight: '16px',
                background: btnHover === b.id ? b.hover : b.bg, color: b.color,
                transition: 'background 0.15s',
              }}>{b.label}</button>
          ))}
          <button style={{
            padding: '0.5rem 1.25rem', borderRadius: 'var(--radius)', cursor: 'pointer',
            fontSize: '14px', fontWeight: 600, letterSpacing: '0.2px', lineHeight: '16px',
            background: 'var(--color-card)', color: 'var(--color-text)',
            border: '1px solid var(--color-border)',
          }}>Secondary</button>
          <button disabled style={{
            padding: '0.5rem 1.25rem', borderRadius: 'var(--radius)', cursor: 'not-allowed',
            fontSize: '14px', fontWeight: 600, letterSpacing: '0.2px', lineHeight: '16px',
            background: 'var(--color-border)', color: 'var(--color-text-secondary)',
            border: 'none', opacity: 0.6,
          }}>Disabled</button>
        </div>
        <p style={{ fontSize: '0.7rem', color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)' }}>
          Button Medium: Open Sans 600 14px/16px, letter-spacing 0.2px, border-radius var(--radius)
        </p>
      </Section>

      {/* ── Chips ── */}
      <Section title="Chips &amp; Badges">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center', marginBottom: '1rem' }}>
          <span style={{ padding: '0.3rem 0.75rem', borderRadius: 999, fontSize: '0.75rem', fontWeight: 600, background: 'var(--color-chip-bg)', color: 'var(--color-chip-text)', border: '1px solid var(--color-chip-border)' }}>Default Chip</span>
          <span style={{ padding: '0.3rem 0.75rem', borderRadius: 999, fontSize: '0.75rem', fontWeight: 600, background: 'var(--color-success-bg)', color: 'var(--color-success-text)' }}>Success</span>
          <span style={{ padding: '0.3rem 0.75rem', borderRadius: 999, fontSize: '0.75rem', fontWeight: 600, background: 'var(--color-warning-bg)', color: 'var(--color-warning-text)' }}>Warning</span>
          <span style={{ padding: '0.3rem 0.75rem', borderRadius: 999, fontSize: '0.75rem', fontWeight: 600, background: 'var(--color-danger-bg)', color: 'var(--color-danger-text)' }}>Danger</span>
          <span style={{ padding: '0.15rem 0.5rem', borderRadius: 999, fontSize: '0.6rem', fontWeight: 700, color: '#008556', background: '#D6F3E2', border: '1px solid #00855630' }}>Live</span>
          <span style={{ padding: '0.15rem 0.5rem', borderRadius: 999, fontSize: '0.6rem', fontWeight: 700, color: '#F6881F', background: '#FDDFC4', border: '1px solid #F6881F30' }}>Simulive</span>
          <span style={{ padding: '0.15rem 0.5rem', borderRadius: 999, fontSize: '0.6rem', fontWeight: 700, color: '#7C3AED', background: '#F5F3FF', border: '1px solid #7C3AED30' }}>Sim2Live</span>
          <span style={{ padding: '0.15rem 0.5rem', borderRadius: 999, fontSize: '0.6rem', fontWeight: 700, color: '#656565', background: '#FCFCFC', border: '1px solid #65656530' }}>On Demand</span>
        </div>
      </Section>

      {/* ── Cards ── */}
      <Section title="Cards &amp; Elevation">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
          {[
            { label: 'Card (shadow-card)', shadow: 'var(--shadow-card)' },
            { label: 'Elevated (shadow-elevated)', shadow: 'var(--shadow-elevated)' },
            { label: 'Dropdown (shadow-dropdown)', shadow: 'var(--shadow-dropdown)' },
          ].map(c => (
            <div key={c.label} style={{
              background: 'var(--color-card)', borderRadius: 'var(--radius)',
              border: '1px solid var(--color-border)', boxShadow: c.shadow,
              padding: '1.25rem', textAlign: 'center',
            }}>
              <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-text)', marginBottom: '0.25rem' }}>{c.label}</div>
              <div style={{ fontSize: '0.65rem', color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)' }}>{c.shadow.replace('var(', '').replace(')', '')}</div>
            </div>
          ))}
        </div>
      </Section>

      {/* ── Spacing & Radius ── */}
      <Section title="Spacing &amp; Radius">
        <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap' }}>
          {[
            { label: 'radius-sm', val: 'var(--radius-sm)' },
            { label: 'radius', val: 'var(--radius)' },
            { label: 'radius-lg', val: 'var(--radius-lg)' },
            { label: 'radius-pill', val: 'var(--radius-pill)' },
          ].map(r => (
            <div key={r.label} style={{ textAlign: 'center' }}>
              <div style={{
                width: 60, height: 60, background: 'var(--color-primary-light)',
                border: '2px solid var(--color-primary)', borderRadius: r.val,
                marginBottom: '0.4rem',
              }} />
              <div style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--color-text)' }}>{r.label}</div>
              <div style={{ fontSize: '0.6rem', color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)' }}>{getCssVar(`--${r.label}`)}</div>
            </div>
          ))}
        </div>
      </Section>

      {/* ── Chart Palette ── */}
      <Section title="Chart Palette">
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {Array.from({ length: 10 }, (_, i) => i + 1).map(n => (
            <div key={n} style={{ textAlign: 'center' }}>
              <div style={{
                width: 48, height: 48, borderRadius: 8,
                background: `var(--color-chart-${n})`,
              }} />
              <div style={{ fontSize: '0.6rem', color: 'var(--color-text-secondary)', marginTop: '0.25rem', fontFamily: 'var(--font-mono)' }}>
                {getCssVar(`--color-chart-${n}`)}
              </div>
            </div>
          ))}
        </div>
      </Section>
    </div>
  )
}
