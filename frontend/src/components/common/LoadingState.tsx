interface LoadingStateProps {
  message?: string
}

export default function LoadingState({ message = 'Loading...' }: LoadingStateProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-label={message}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '3rem',
        color: 'var(--color-text-secondary)',
      }}
    >
      <div
        aria-hidden="true"
        style={{
          width: 32,
          height: 32,
          border: '3px solid var(--color-border)',
          borderTopColor: 'var(--color-primary)',
          borderRadius: '50%',
          animation: 'spin 0.8s linear infinite',
          marginBottom: '1rem',
        }}
      />
      <p style={{ fontSize: '0.875rem' }}>{message}</p>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}
