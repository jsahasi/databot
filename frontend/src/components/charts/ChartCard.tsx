import { ReactNode } from 'react'

interface ChartCardProps {
  title: string
  subtitle?: string
  children: ReactNode
}

export default function ChartCard({ title, subtitle, children }: ChartCardProps) {
  return (
    <div
      style={{
        background: 'var(--color-card)',
        borderRadius: 'var(--radius)',
        boxShadow: 'var(--shadow-card)',
        padding: '1.25rem 1.5rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '1rem',
        minHeight: 320,
      }}
    >
      <div>
        <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--color-text)', margin: 0 }}>{title}</h3>
        {subtitle && (
          <p style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', margin: '0.25rem 0 0 0' }}>
            {subtitle}
          </p>
        )}
      </div>
      <div style={{ flex: 1, width: '100%' }}>{children}</div>
    </div>
  )
}
