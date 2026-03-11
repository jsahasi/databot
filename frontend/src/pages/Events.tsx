import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useEvents } from '../hooks/useEvents'
import DataTable from '../components/common/DataTable'
import LoadingState from '../components/common/LoadingState'
import type { EventSummary } from '../services/api'

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function EngagementBadge({ score }: { score: number | null }) {
  if (score == null) return <span style={{ color: 'var(--color-text-secondary)' }}>-</span>
  const bg = score > 70 ? '#c6f6d5' : score >= 40 ? '#fefcbf' : '#fed7d7'
  const color = score > 70 ? '#22543d' : score >= 40 ? '#744210' : '#9b2c2c'
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '0.2rem 0.6rem',
        borderRadius: '9999px',
        fontSize: '0.75rem',
        fontWeight: 600,
        background: bg,
        color,
      }}
    >
      {score.toFixed(1)}
    </span>
  )
}

function StatusBadge({ active }: { active: boolean }) {
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '0.2rem 0.6rem',
        borderRadius: '9999px',
        fontSize: '0.75rem',
        fontWeight: 600,
        background: active ? '#c6f6d5' : '#e2e8f0',
        color: active ? '#22543d' : '#4a5568',
      }}
    >
      {active ? 'Active' : 'Inactive'}
    </span>
  )
}

export default function Events() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [sortBy, setSortBy] = useState('live_start')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  const { data, isLoading, isError } = useEvents({
    page,
    per_page: 20,
    search: search || undefined,
    sort_by: sortBy,
    sort_order: sortOrder,
  })

  const handleSearch = () => {
    setSearch(searchInput)
    setPage(1)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch()
  }

  const handleSort = (key: string, order: 'asc' | 'desc') => {
    setSortBy(key)
    setSortOrder(order)
    setPage(1)
  }

  const columns = [
    {
      key: 'title',
      header: 'Title',
      sortable: true,
      render: (item: EventSummary) => (
        <Link
          to={`/events/${item.on24_event_id}`}
          style={{
            color: 'var(--color-primary)',
            textDecoration: 'none',
            fontWeight: 500,
          }}
        >
          {item.title}
        </Link>
      ),
    },
    {
      key: 'event_type',
      header: 'Type',
      render: (item: EventSummary) => (
        <span style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>
          {item.event_type || '-'}
        </span>
      ),
    },
    {
      key: 'live_start',
      header: 'Date',
      sortable: true,
      render: (item: EventSummary) => formatDate(item.live_start),
    },
    {
      key: 'total_registrants',
      header: 'Registrants',
      sortable: false,
      render: (item: EventSummary) => item.total_registrants.toLocaleString(),
    },
    {
      key: 'total_attendees',
      header: 'Attendees',
      sortable: true,
      render: (item: EventSummary) => item.total_attendees.toLocaleString(),
    },
    {
      key: 'engagement_score',
      header: 'Engagement',
      sortable: true,
      render: (item: EventSummary) => <EngagementBadge score={item.engagement_score} />,
    },
    {
      key: 'is_active',
      header: 'Status',
      render: (item: EventSummary) => <StatusBadge active={item.is_active} />,
    },
  ]

  if (isLoading && !data) return <LoadingState message="Loading events..." />

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--color-text)', margin: 0 }}>
          Events
        </h1>
        {data && (
          <span style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)' }}>
            {data.total.toLocaleString()} total events
          </span>
        )}
      </div>

      {/* Search */}
      <div
        style={{
          display: 'flex',
          gap: '0.5rem',
          background: 'var(--color-card)',
          borderRadius: 'var(--radius)',
          boxShadow: 'var(--shadow-card)',
          padding: '0.75rem 1rem',
        }}
      >
        <input
          type="text"
          placeholder="Search events by title..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          onKeyDown={handleKeyDown}
          aria-label="Search events"
          style={{
            flex: 1,
            padding: '0.5rem 0.75rem',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius)',
            fontSize: '0.875rem',
            outline: 'none',
            color: 'var(--color-text)',
            background: 'var(--color-bg)',
          }}
        />
        <button
          onClick={handleSearch}
          style={{
            padding: '0.5rem 1.25rem',
            background: 'var(--color-primary)',
            color: '#fff',
            border: 'none',
            borderRadius: 'var(--radius)',
            fontSize: '0.875rem',
            cursor: 'pointer',
            fontWeight: 500,
          }}
        >
          Search
        </button>
        {search && (
          <button
            onClick={() => {
              setSearch('')
              setSearchInput('')
              setPage(1)
            }}
            style={{
              padding: '0.5rem 1rem',
              background: 'transparent',
              color: 'var(--color-text-secondary)',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius)',
              fontSize: '0.875rem',
              cursor: 'pointer',
            }}
          >
            Clear
          </button>
        )}
      </div>

      {isError ? (
        <div
          style={{
            padding: '2rem',
            textAlign: 'center',
            color: 'var(--color-text-secondary)',
            background: 'var(--color-card)',
            borderRadius: 'var(--radius)',
          }}
        >
          Failed to load events. Please try again later.
        </div>
      ) : (
        <DataTable
          columns={columns}
          data={data?.items ?? []}
          total={data?.total}
          page={page}
          perPage={20}
          onPageChange={setPage}
          onSort={handleSort}
          loading={isLoading}
        />
      )}
    </div>
  )
}
