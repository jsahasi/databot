import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import { useDashboard, useTrends, useTopEvents, useEngagementHeatmap } from '../hooks/useAnalytics'
import KPICard from '../components/common/KPICard'
import ChartCard from '../components/charts/ChartCard'
import LoadingState from '../components/common/LoadingState'
import ErrorState from '../components/common/ErrorState'
import EngagementHeatmap from '../components/charts/EngagementHeatmap'

export default function Dashboard() {
  const dashboard = useDashboard()
  const trends = useTrends()
  const topEvents = useTopEvents(10)
  const { data: heatmapData } = useEngagementHeatmap()

  if (dashboard.isLoading) return <LoadingState message="Loading dashboard..." />
  if (dashboard.isError) return <ErrorState message="Failed to load dashboard data." onRetry={() => dashboard.refetch()} />

  const summary = dashboard.data

  return (
    <div>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '1.5rem', color: 'var(--color-text)' }}>
        Dashboard
      </h1>

      {/* KPI Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '1rem',
        marginBottom: '1.5rem',
      }}>
        <KPICard
          title="Total Events"
          value={summary?.totalEvents?.toLocaleString() ?? '—'}
          icon={'\u{1F4C5}'}
        />
        <KPICard
          title="Total Attendees"
          value={summary?.totalAttendees?.toLocaleString() ?? '—'}
          icon={'\u{1F465}'}
        />
        <KPICard
          title="Total Registrants"
          value={summary?.totalRegistrants?.toLocaleString() ?? '—'}
          icon={'\u{1F4DD}'}
        />
        <KPICard
          title="Avg Engagement Rate"
          value={summary?.avgEngagementRate != null ? `${summary.avgEngagementRate.toFixed(1)}%` : '—'}
          icon={'\u{1F4C8}'}
        />
      </div>

      {/* Charts row */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '1rem',
        marginBottom: '1rem',
      }}>
        {/* Attendance Trend */}
        <ChartCard title="Attendance Trend">
          {trends.isLoading ? (
            <LoadingState message="Loading trends..." />
          ) : trends.isError ? (
            <ErrorState message="Failed to load trends." onRetry={() => trends.refetch()} />
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={trends.data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="var(--color-text-secondary)" />
                <YAxis tick={{ fontSize: 12 }} stroke="var(--color-text-secondary)" />
                <Tooltip
                  contentStyle={{
                    background: 'var(--color-card)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius)',
                    fontSize: '0.8rem',
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '0.8rem' }} />
                <Line
                  type="monotone"
                  dataKey="attendees"
                  stroke="var(--color-primary)"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  name="Attendees"
                />
                <Line
                  type="monotone"
                  dataKey="registrants"
                  stroke="var(--color-success)"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  name="Registrants"
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        {/* Top Events */}
        <ChartCard title="Top Events by Attendance">
          {topEvents.isLoading ? (
            <LoadingState message="Loading top events..." />
          ) : topEvents.isError ? (
            <ErrorState message="Failed to load top events." onRetry={() => topEvents.refetch()} />
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={topEvents.data} layout="vertical" margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                <XAxis type="number" tick={{ fontSize: 12 }} stroke="var(--color-text-secondary)" />
                <YAxis
                  dataKey="title"
                  type="category"
                  width={120}
                  tick={{ fontSize: 11 }}
                  stroke="var(--color-text-secondary)"
                />
                <Tooltip
                  contentStyle={{
                    background: 'var(--color-card)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius)',
                    fontSize: '0.8rem',
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '0.8rem' }} />
                <Bar dataKey="attendees" fill="var(--color-primary)" radius={[0, 4, 4, 0]} name="Attendees" />
                <Bar dataKey="registrants" fill="var(--color-success)" radius={[0, 4, 4, 0]} name="Registrants" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>
      </div>

      {/* Engagement Heatmap — full width */}
      {heatmapData && heatmapData.length > 0 && (
        <div style={{ gridColumn: '1 / -1' }}>
          <ChartCard title="Engagement by Day & Time" subtitle="Average engagement score by scheduling slot">
            <EngagementHeatmap data={heatmapData} />
          </ChartCard>
        </div>
      )}
    </div>
  )
}
