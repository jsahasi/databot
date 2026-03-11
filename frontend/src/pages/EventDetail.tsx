import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useEvent, useEventAttendees, useEventRegistrants } from '../hooks/useEvents'
import DataTable from '../components/common/DataTable'
import KPICard from '../components/common/KPICard'
import LoadingState from '../components/common/LoadingState'
import ErrorState from '../components/common/ErrorState'
import type { AttendeeSummary, RegistrantSummary } from '../services/api'

type TabKey = 'attendees' | 'registrants' | 'polls' | 'surveys' | 'resources' | 'ctas'

const TABS: { key: TabKey; label: string }[] = [
  { key: 'attendees', label: 'Attendees' },
  { key: 'registrants', label: 'Registrants' },
  { key: 'polls', label: 'Polls' },
  { key: 'surveys', label: 'Surveys' },
  { key: 'resources', label: 'Resources' },
  { key: 'ctas', label: 'CTAs' },
]

function formatDateTime(dateStr: string | null): string {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
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

function ComingSoon({ label }: { label: string }) {
  return (
    <div
      style={{
        padding: '3rem',
        textAlign: 'center',
        color: 'var(--color-text-secondary)',
        background: 'var(--color-card)',
        borderRadius: 'var(--radius)',
        boxShadow: 'var(--shadow-card)',
      }}
    >
      <p style={{ fontSize: '1rem', fontWeight: 500 }}>{label}</p>
      <p style={{ fontSize: '0.85rem', marginTop: '0.5rem' }}>
        This tab is coming soon. Data will appear here once the feature is implemented.
      </p>
    </div>
  )
}

export default function EventDetail() {
  const { eventId } = useParams<{ eventId: string }>()
  const eventIdNum = eventId ? Number(eventId) : 0
  const [activeTab, setActiveTab] = useState<TabKey>('attendees')
  const [attendeePage, setAttendeePage] = useState(1)
  const [registrantPage, setRegistrantPage] = useState(1)

  const { data: event, isLoading, isError, refetch } = useEvent(eventIdNum)
  const {
    data: attendeesData,
    isLoading: attendeesLoading,
  } = useEventAttendees(eventIdNum, { page: attendeePage, per_page: 20 })
  const {
    data: registrantsData,
    isLoading: registrantsLoading,
  } = useEventRegistrants(eventIdNum, { page: registrantPage, per_page: 20 })

  if (isLoading) return <LoadingState message="Loading event details..." />
  if (isError || !event) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <Link
          to="/events"
          style={{ color: 'var(--color-primary)', textDecoration: 'none', fontSize: '0.875rem' }}
        >
          &larr; Back to Events
        </Link>
        <ErrorState message="Failed to load event details." onRetry={() => refetch()} />
      </div>
    )
  }

  const attendeeColumns = [
    {
      key: 'name',
      header: 'Name',
      render: (item: AttendeeSummary) =>
        [item.first_name, item.last_name].filter(Boolean).join(' ') || '-',
    },
    { key: 'email', header: 'Email' },
    {
      key: 'company',
      header: 'Company',
      render: (item: AttendeeSummary) => item.company || '-',
    },
    {
      key: 'engagement_score',
      header: 'Engagement',
      render: (item: AttendeeSummary) => <EngagementBadge score={item.engagement_score} />,
    },
    {
      key: 'live_minutes',
      header: 'Live Min',
      render: (item: AttendeeSummary) => item.live_minutes ?? '-',
    },
    {
      key: 'archive_minutes',
      header: 'Archive Min',
      render: (item: AttendeeSummary) => item.archive_minutes ?? '-',
    },
    {
      key: 'asked_questions',
      header: 'Questions',
      render: (item: AttendeeSummary) => item.asked_questions,
    },
    {
      key: 'answered_polls',
      header: 'Polls',
      render: (item: AttendeeSummary) => item.answered_polls,
    },
  ]

  const registrantColumns = [
    {
      key: 'name',
      header: 'Name',
      render: (item: RegistrantSummary) =>
        [item.first_name, item.last_name].filter(Boolean).join(' ') || '-',
    },
    { key: 'email', header: 'Email' },
    {
      key: 'company',
      header: 'Company',
      render: (item: RegistrantSummary) => item.company || '-',
    },
    {
      key: 'job_title',
      header: 'Job Title',
      render: (item: RegistrantSummary) => item.job_title || '-',
    },
    {
      key: 'registration_date',
      header: 'Registered',
      render: (item: RegistrantSummary) => formatDate(item.registration_date),
    },
    {
      key: 'utm_source',
      header: 'UTM Source',
      render: (item: RegistrantSummary) => item.utm_source || '-',
    },
  ]

  const engagementScore = event.engagement_score

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Back link */}
      <Link
        to="/events"
        style={{ color: 'var(--color-primary)', textDecoration: 'none', fontSize: '0.875rem' }}
      >
        &larr; Back to Events
      </Link>

      {/* Event header */}
      <div
        style={{
          background: 'var(--color-card)',
          borderRadius: 'var(--radius)',
          boxShadow: 'var(--shadow-card)',
          padding: '1.5rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--color-text)', margin: 0 }}>
              {event.title}
            </h1>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
              {event.event_type && (
                <span
                  style={{
                    display: 'inline-block',
                    padding: '0.2rem 0.6rem',
                    borderRadius: '9999px',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    background: '#ebf4ff',
                    color: '#3182ce',
                  }}
                >
                  {event.event_type}
                </span>
              )}
              <span style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary)' }}>
                {formatDateTime(event.live_start)}
                {event.live_end && ` - ${formatDateTime(event.live_end)}`}
              </span>
            </div>
          </div>
          <span
            style={{
              display: 'inline-block',
              padding: '0.25rem 0.75rem',
              borderRadius: '9999px',
              fontSize: '0.8rem',
              fontWeight: 600,
              background: event.is_active ? '#c6f6d5' : '#e2e8f0',
              color: event.is_active ? '#22543d' : '#4a5568',
            }}
          >
            {event.is_active ? 'Active' : 'Inactive'}
          </span>
        </div>
      </div>

      {/* KPI cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem' }}>
        <KPICard
          title="Registrants"
          value={event.total_registrants.toLocaleString()}
          subtitle="Total sign-ups"
        />
        <KPICard
          title="Attendees"
          value={event.total_attendees.toLocaleString()}
          subtitle={`${event.live_attendees} live, ${event.on_demand_attendees} on-demand`}
        />
        <KPICard
          title="No-Shows"
          value={event.no_show_count.toLocaleString()}
          subtitle={
            event.total_registrants > 0
              ? `${((event.no_show_count / event.total_registrants) * 100).toFixed(1)}% of registrants`
              : 'No registrants'
          }
        />
        <KPICard
          title="Engagement Score"
          value={engagementScore != null ? engagementScore.toFixed(1) : '-'}
          subtitle={
            engagementScore == null
              ? 'Not available'
              : engagementScore > 70
              ? 'High engagement'
              : engagementScore >= 40
              ? 'Moderate engagement'
              : 'Low engagement'
          }
        />
      </div>

      {/* Tab navigation */}
      <div
        style={{
          display: 'flex',
          gap: '0',
          borderBottom: '2px solid var(--color-border)',
          overflowX: 'auto',
        }}
      >
        {TABS.map((tab) => {
          const isActive = activeTab === tab.key
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              style={{
                padding: '0.75rem 1.25rem',
                fontSize: '0.875rem',
                fontWeight: isActive ? 600 : 400,
                color: isActive ? 'var(--color-primary)' : 'var(--color-text-secondary)',
                background: 'transparent',
                border: 'none',
                borderBottom: isActive ? '2px solid var(--color-primary)' : '2px solid transparent',
                marginBottom: '-2px',
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                transition: 'color 0.15s, border-color 0.15s',
              }}
            >
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Tab content */}
      {activeTab === 'attendees' && (
        <DataTable
          columns={attendeeColumns}
          data={attendeesData?.items ?? []}
          total={attendeesData?.total}
          page={attendeePage}
          perPage={20}
          onPageChange={setAttendeePage}
          loading={attendeesLoading}
        />
      )}

      {activeTab === 'registrants' && (
        <DataTable
          columns={registrantColumns}
          data={registrantsData?.items ?? []}
          total={registrantsData?.total}
          page={registrantPage}
          perPage={20}
          onPageChange={setRegistrantPage}
          loading={registrantsLoading}
        />
      )}

      {activeTab === 'polls' && <ComingSoon label="Polls" />}
      {activeTab === 'surveys' && <ComingSoon label="Surveys" />}
      {activeTab === 'resources' && <ComingSoon label="Resources" />}
      {activeTab === 'ctas' && <ComingSoon label="CTAs" />}
    </div>
  )
}
