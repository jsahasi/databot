import { ReactNode } from 'react'

interface ChartCardProps {
  title: string
  children: ReactNode
}

export default function ChartCard({ title, children }: ChartCardProps) {
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
      <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--color-text)' }}>{title}</h3>
      <div style={{ flex: 1, width: '100%' }}>{children}</div>
    </div>
  )
}
