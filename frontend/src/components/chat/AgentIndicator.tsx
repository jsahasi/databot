interface AgentIndicatorProps {
  agent: string | null
  isProcessing: boolean
}

const AGENT_LABELS: Record<string, { label: string; color: string }> = {
  orchestrator: { label: 'Thinking', color: '#8b5cf6' },
  data_agent: { label: 'Analyzing Data', color: '#3b82f6' },
  content_agent: { label: 'Content Analysis', color: '#10b981' },
  admin_agent: { label: 'Admin Action', color: '#f59e0b' },
}

export default function AgentIndicator({ agent, isProcessing }: AgentIndicatorProps) {
  if (!isProcessing || !agent) return null

  const info = AGENT_LABELS[agent] || { label: agent, color: 'var(--color-primary)' }

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '0.5rem',
      padding: '0.375rem 0.75rem', fontSize: '0.75rem',
      color: info.color, background: `${info.color}10`,
      borderRadius: '1rem', width: 'fit-content',
    }}>
      <div style={{
        width: 6, height: 6, borderRadius: '50%',
        background: info.color, animation: 'pulse 1.5s infinite',
      }} />
      <span>{info.label}...</span>
      <style>{`@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }`}</style>
    </div>
  )
}
