interface KPICardProps {
  title: string
  value: string | number
  subtitle?: string
  icon?: string
}

export default function KPICard({ title, value, subtitle, icon }: KPICardProps) {
  return (
    <div
      style={{
        background: 'var(--color-card)',
        borderRadius: 'var(--radius)',
        boxShadow: 'var(--shadow-card)',
        padding: '1.25rem 1.5rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.25rem',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', fontWeight: 500 }}>
          {title}
        </span>
        {icon && <span aria-hidden="true" style={{ fontSize: '1.25rem' }}>{icon}</span>}
      </div>
      <span style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--color-text)', lineHeight: 1.2 }}>
        {value}
      </span>
      {subtitle && (
        <span style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>
          {subtitle}
        </span>
      )}
    </div>
  )
}
