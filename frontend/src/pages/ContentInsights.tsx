import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts'
import { useContentPerformance } from '../hooks/useAnalytics'
import type { TopEvent } from '../services/api'
import ChartCard from '../components/charts/ChartCard'
import DataTable from '../components/common/DataTable'
import LoadingState from '../components/common/LoadingState'
import ErrorState from '../components/common/ErrorState'

const DAY_LABELS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

// Placeholder data for scheduling charts until Content Agent provides real data
const DAY_PLACEHOLDER = DAY_LABELS.map(day => ({ day, avg_attendees: 0 }))
const HOUR_PLACEHOLDER = Array.from({ length: 24 }, (_, i) => ({
  hour: `${i.toString().padStart(2, '0')}:00`,
  avg_attendees: 0,
}))

function EngagementBadge({ score }: { score: number | null }) {
  let color = '#94a3b8'
  if (score != null) {
    if (score > 70) color = '#059669'
    else if (score > 40) color = '#d97706'
    else color = '#dc2626'
  }
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '0.2rem 0.6rem',
        borderRadius: '9999px',
        fontSize: '0.75rem',
        fontWeight: 600,
        background: color + '20',
        color,
      }}
    >
      {score != null ? score.toFixed(1) : 'N/A'}
    </span>
  )
}

export default function ContentInsights() {
  const { data, isLoading, isError, refetch } = useContentPerformance()

  if (isLoading) return <LoadingState message="Loading content insights..." />
  if (isError) return <ErrorState message="Failed to load content performance data." onRetry={() => refetch()} />

  const byType = data?.by_type ?? []
  const topEvents = data?.top_events ?? []

  const eventColumns = [
    {
      key: 'title',
      header: 'Event Title',
      sortable: true,
      render: (item: TopEvent) => (
        <span style={{ fontWeight: 500, color: 'var(--color-text)' }}>{item.title}</span>
      ),
    },
    {
      key: 'live_start',
      header: 'Date',
      width: '160px',
      render: (item: TopEvent) =>
        item.live_start
          ? new Date(item.live_start).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
          : '—',
    },
    {
      key: 'total_attendees',
      header: 'Attendees',
      sortable: true,
      width: '120px',
      render: (item: TopEvent) => (
        <span style={{ color: 'var(--color-text-secondary)' }}>{item.total_attendees.toLocaleString()}</span>
      ),
    },
    {
      key: 'engagement_score',
      header: 'Engagement Score',
      sortable: true,
      width: '160px',
      render: (item: TopEvent) => <EngagementBadge score={item.engagement_score} />,
    },
  ]

  return (
    <div>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '1.5rem', color: 'var(--color-text)' }}>
        Content Insights
      </h1>

      {/* Section 1: Performance by Event Type */}
      <div style={{ marginBottom: '1rem' }}>
        <ChartCard
          title="Performance by Event Type"
          subtitle="Average attendees and engagement score grouped by event type"
        >
          {byType.length === 0 ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 240, color: 'var(--color-text-secondary)', fontSize: '0.875rem' }}>
              No event type data available
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={byType} margin={{ top: 5, right: 20, left: 0, bottom: 40 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                <XAxis
                  dataKey="event_type"
                  tick={{ fontSize: 11 }}
                  stroke="var(--color-text-secondary)"
                  angle={-25}
                  textAnchor="end"
                />
                <YAxis
                  yAxisId="left"
                  tick={{ fontSize: 11 }}
                  stroke="var(--color-text-secondary)"
                  label={{ value: 'Avg Attendees', angle: -90, position: 'insideLeft', offset: 10, style: { fontSize: 10 } }}
                />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  tick={{ fontSize: 11 }}
                  stroke="var(--color-text-secondary)"
                  domain={[0, 100]}
                  label={{ value: 'Avg Engagement', angle: 90, position: 'insideRight', offset: 10, style: { fontSize: 10 } }}
                />
                <Tooltip
                  contentStyle={{
                    background: 'var(--color-card)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius)',
                    fontSize: '0.8rem',
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '0.8rem', paddingTop: '0.5rem' }} />
                <Bar yAxisId="left" dataKey="avg_attendees" fill="var(--color-primary)" radius={[4, 4, 0, 0]} name="Avg Attendees" />
                <Bar yAxisId="right" dataKey="avg_engagement" fill="#059669" radius={[4, 4, 0, 0]} name="Avg Engagement" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>
      </div>

      {/* Section 2: Optimal Scheduling */}
      <div style={{ marginBottom: '1rem' }}>
        <h2 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--color-text)', marginBottom: '0.75rem' }}>
          Optimal Scheduling
          <span style={{ marginLeft: '0.5rem', fontSize: '0.75rem', fontWeight: 400, color: 'var(--color-text-secondary)' }}>
            (scheduling data will be provided by Content Agent)
          </span>
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
          <ChartCard title="Avg Attendance by Day of Week" subtitle="Best days to schedule events">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={DAY_PLACEHOLDER} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                <XAxis dataKey="day" tick={{ fontSize: 11 }} stroke="var(--color-text-secondary)" />
                <YAxis tick={{ fontSize: 11 }} stroke="var(--color-text-secondary)" />
                <Tooltip
                  contentStyle={{
                    background: 'var(--color-card)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius)',
                    fontSize: '0.8rem',
                  }}
                />
                <Bar dataKey="avg_attendees" fill="var(--color-primary)" radius={[4, 4, 0, 0]} name="Avg Attendees" />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="Avg Attendance by Hour of Day" subtitle="Best hours to schedule events">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={HOUR_PLACEHOLDER} margin={{ top: 5, right: 10, left: 0, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                <XAxis
                  dataKey="hour"
                  tick={{ fontSize: 9 }}
                  stroke="var(--color-text-secondary)"
                  angle={-45}
                  textAnchor="end"
                  interval={1}
                />
                <YAxis tick={{ fontSize: 11 }} stroke="var(--color-text-secondary)" />
                <Tooltip
                  contentStyle={{
                    background: 'var(--color-card)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius)',
                    fontSize: '0.8rem',
                  }}
                />
                <Bar dataKey="avg_attendees" fill="#7c3aed" radius={[4, 4, 0, 0]} name="Avg Attendees" />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>
      </div>

      {/* Section 3: Top Performing Events */}
      <div>
        <h2 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--color-text)', marginBottom: '0.75rem' }}>
          Top Performing Events
        </h2>
        <DataTable columns={eventColumns} data={topEvents} />
      </div>
    </div>
  )
}
