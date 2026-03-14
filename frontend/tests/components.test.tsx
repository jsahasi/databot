import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import KPICard from '@/components/common/KPICard'
import ErrorState from '@/components/common/ErrorState'
import LoadingState from '@/components/common/LoadingState'
import AgentIndicator from '@/components/chat/AgentIndicator'

// ---------- KPICard ----------

describe('KPICard', () => {
  it('renders title and value', () => {
    render(<KPICard title="Registrants" value={1200} />)
    expect(screen.getByText('Registrants')).toBeInTheDocument()
    expect(screen.getByText('1200')).toBeInTheDocument()
  })

  it('renders subtitle when provided', () => {
    render(<KPICard title="Events" value={15} subtitle="Last 30 days" />)
    expect(screen.getByText('Last 30 days')).toBeInTheDocument()
  })

  it('does not render subtitle when omitted', () => {
    render(<KPICard title="Events" value={15} />)
    expect(screen.queryByText('Last 30 days')).not.toBeInTheDocument()
  })

  it('renders icon when provided', () => {
    const { container } = render(<KPICard title="Score" value="85%" icon="📊" />)
    expect(container.textContent).toContain('📊')
  })

  it('handles string values', () => {
    render(<KPICard title="Rate" value="72.5%" />)
    expect(screen.getByText('72.5%')).toBeInTheDocument()
  })
})

// ---------- ErrorState ----------

describe('ErrorState', () => {
  it('renders default message', () => {
    render(<ErrorState />)
    expect(screen.getByText('Something went wrong. Please try again.')).toBeInTheDocument()
  })

  it('renders custom message', () => {
    render(<ErrorState message="Network error" />)
    expect(screen.getByText('Network error')).toBeInTheDocument()
  })

  it('has alert role for accessibility', () => {
    render(<ErrorState />)
    expect(screen.getByRole('alert')).toBeInTheDocument()
  })

  it('renders retry button when onRetry provided', () => {
    const onRetry = vi.fn()
    render(<ErrorState onRetry={onRetry} />)
    const btn = screen.getByText('Retry')
    expect(btn).toBeInTheDocument()
    fireEvent.click(btn)
    expect(onRetry).toHaveBeenCalledOnce()
  })

  it('does not render retry button when onRetry omitted', () => {
    render(<ErrorState />)
    expect(screen.queryByText('Retry')).not.toBeInTheDocument()
  })
})

// ---------- LoadingState ----------

describe('LoadingState', () => {
  it('renders default message', () => {
    render(<LoadingState />)
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('renders custom message', () => {
    render(<LoadingState message="Fetching events..." />)
    expect(screen.getByText('Fetching events...')).toBeInTheDocument()
  })

  it('has status role for accessibility', () => {
    render(<LoadingState />)
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('has aria-live polite', () => {
    render(<LoadingState />)
    const el = screen.getByRole('status')
    expect(el).toHaveAttribute('aria-live', 'polite')
  })

  it('has aria-label matching message', () => {
    render(<LoadingState message="Loading data..." />)
    expect(screen.getByRole('status')).toHaveAttribute('aria-label', 'Loading data...')
  })
})

// ---------- AgentIndicator ----------

describe('AgentIndicator', () => {
  it('renders nothing when not processing', () => {
    const { container } = render(<AgentIndicator agent="data_agent" isProcessing={false} />)
    expect(container.innerHTML).toBe('')
  })

  it('renders nothing when agent is null', () => {
    const { container } = render(<AgentIndicator agent={null} isProcessing={true} />)
    expect(container.innerHTML).toBe('')
  })

  it('renders data agent label', () => {
    render(<AgentIndicator agent="data_agent" isProcessing={true} />)
    expect(screen.getByText('Analyzing Data...')).toBeInTheDocument()
  })

  it('renders orchestrator label', () => {
    render(<AgentIndicator agent="orchestrator" isProcessing={true} />)
    expect(screen.getByText('Thinking...')).toBeInTheDocument()
  })

  it('renders content agent label', () => {
    render(<AgentIndicator agent="content_agent" isProcessing={true} />)
    expect(screen.getByText('Content Analysis...')).toBeInTheDocument()
  })

  it('renders admin agent label', () => {
    render(<AgentIndicator agent="admin_agent" isProcessing={true} />)
    expect(screen.getByText('Admin Action...')).toBeInTheDocument()
  })

  it('falls back to agent name for unknown agents', () => {
    render(<AgentIndicator agent="custom_agent" isProcessing={true} />)
    expect(screen.getByText('custom_agent...')).toBeInTheDocument()
  })

  it('has status role and aria-live', () => {
    render(<AgentIndicator agent="data_agent" isProcessing={true} />)
    const el = screen.getByRole('status')
    expect(el).toHaveAttribute('aria-live', 'polite')
    expect(el).toHaveAttribute('aria-label', 'Analyzing Data, please wait')
  })
})
