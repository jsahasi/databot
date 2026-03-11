import { useState, useMemo } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts'
import { useAudienceAnalytics } from '../hooks/useAnalytics'
import type { CompanyAudience } from '../services/api'
import ChartCard from '../components/charts/ChartCard'
import DataTable from '../components/common/DataTable'
import LoadingState from '../components/common/LoadingState'
import ErrorState from '../components/common/ErrorState'

const PIE_COLORS = [
  '#4f46e5', '#7c3aed', '#db2777', '#dc2626', '#d97706',
  '#059669', '#0284c7', '#6d28d9', '#be185d', '#b45309',
]

function engagementColor(score: number | null): string {
  if (score == null) return '#94a3b8'
  if (score > 70) return '#059669'
  if (score > 40) return '#d97706'
  return '#dc2626'
}

function EngagementBadge({ score }: { score: number | null }) {
  const color = engagementColor(score)
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

// Custom bar color based on avg_engagement value in the bar payload
function CompanyBar(props: any) {
  const { x, y, width, height, avg_engagement } = props
  const fill = engagementColor(avg_engagement)
  return <rect x={x} y={y} width={width} height={height} fill={fill} rx={3} />
}

type SortKey = 'company' | 'events_attended' | 'total_attendances' | 'avg_engagement'
type SortOrder = 'asc' | 'desc'

export default function Audiences() {
  const { data, isLoading, isError, refetch } = useAudienceAnalytics()
  const [sortKey, setSortKey] = useState<SortKey>('total_attendances')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')

  const sortedCompanies = useMemo(() => {
    if (!data?.top_companies) return []
    return [...data.top_companies]
      .sort((a, b) => {
        const aVal = a[sortKey] ?? -1
        const bVal = b[sortKey] ?? -1
        if (typeof aVal === 'string' && typeof bVal === 'string') {
          return sortOrder === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal)
        }
        return sortOrder === 'asc'
          ? (aVal as number) - (bVal as number)
          : (bVal as number) - (aVal as number)
      })
      .slice(0, 20)
  }, [data, sortKey, sortOrder])

  const handleSort = (key: string, order: 'asc' | 'desc') => {
    setSortKey(key as SortKey)
    setSortOrder(order)
  }

  if (isLoading) return <LoadingState message="Loading audience data..." />
  if (isError) return <ErrorState message="Failed to load audience analytics." onRetry={() => refetch()} />

  const top15Companies = (data?.top_companies ?? [])
    .slice()
    .sort((a, b) => b.total_attendances - a.total_attendances)
    .slice(0, 15)

  const top10Countries = (data?.country_distribution ?? [])
    .slice()
    .sort((a, b) => b.count - a.count)
    .slice(0, 10)

  const registrationSources = data?.registration_sources ?? []
  const totalSources = registrationSources.reduce((sum, s) => sum + s.count, 0)

  const columns = [
    {
      key: 'company',
      header: 'Company',
      sortable: true,
      render: (item: CompanyAudience) => (
        <span style={{ fontWeight: 500, color: 'var(--color-text)' }}>{item.company || '—'}</span>
      ),
    },
    {
      key: 'events_attended',
      header: 'Events Attended',
      sortable: true,
      width: '140px',
      render: (item: CompanyAudience) => (
        <span style={{ color: 'var(--color-text-secondary)' }}>{item.events_attended.toLocaleString()}</span>
      ),
    },
    {
      key: 'total_attendances',
      header: 'Total Attendances',
      sortable: true,
      width: '160px',
      render: (item: CompanyAudience) => (
        <span style={{ color: 'var(--color-text-secondary)' }}>{item.total_attendances.toLocaleString()}</span>
      ),
    },
    {
      key: 'avg_engagement',
      header: 'Avg Engagement',
      sortable: true,
      width: '150px',
      render: (item: CompanyAudience) => <EngagementBadge score={item.avg_engagement} />,
    },
  ]

  return (
    <div>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '1.5rem', color: 'var(--color-text)' }}>
        Audience Intelligence
      </h1>

      {/* Section 1 + 2: Top Companies (bar) + Registration Sources (pie) */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
        <ChartCard title="Top Companies by Attendance" subtitle="Top 15 companies — bar color reflects engagement level">
          <ResponsiveContainer width="100%" height={360}>
            <BarChart
              data={top15Companies}
              layout="vertical"
              margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis type="number" tick={{ fontSize: 11 }} stroke="var(--color-text-secondary)" />
              <YAxis
                dataKey="company"
                type="category"
                width={130}
                tick={{ fontSize: 10 }}
                stroke="var(--color-text-secondary)"
              />
              <Tooltip
                contentStyle={{
                  background: 'var(--color-card)',
                  border: '1px solid var(--color-border)',
                  borderRadius: 'var(--radius)',
                  fontSize: '0.8rem',
                }}
                formatter={(value: number, _name: string, entry: any) => [
                  `${value.toLocaleString()} attendances (engagement: ${entry.payload.avg_engagement?.toFixed(1) ?? 'N/A'})`,
                  'Total Attendances',
                ]}
              />
              <Bar dataKey="total_attendances" name="Total Attendances" shape={<CompanyBar />} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Registration Sources" subtitle="Breakdown by UTM source">
          {registrationSources.length === 0 ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300, color: 'var(--color-text-secondary)', fontSize: '0.875rem' }}>
              No source data available
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={360}>
              <PieChart>
                <Pie
                  data={registrationSources}
                  dataKey="count"
                  nameKey="source"
                  cx="50%"
                  cy="45%"
                  innerRadius={60}
                  outerRadius={110}
                  paddingAngle={2}
                  label={({ count }: { count: number }) =>
                    totalSources > 0 ? `${((count / totalSources) * 100).toFixed(1)}%` : ''
                  }
                  labelLine={false}
                >
                  {registrationSources.map((_entry, index) => (
                    <Cell key={index} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: 'var(--color-card)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius)',
                    fontSize: '0.8rem',
                  }}
                  formatter={(value: number, name: string) => [
                    `${value.toLocaleString()} (${totalSources > 0 ? ((value / totalSources) * 100).toFixed(1) : 0}%)`,
                    name,
                  ]}
                />
                <Legend
                  wrapperStyle={{ fontSize: '0.75rem', paddingTop: '0.5rem' }}
                  formatter={(value: string, entry: any) => {
                    const count = entry?.payload?.count ?? 0
                    const pct = totalSources > 0 ? ((count / totalSources) * 100).toFixed(1) : '0'
                    return `${value} (${pct}%)`
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </ChartCard>
      </div>

      {/* Section 3: Company Engagement Table */}
      <div style={{ marginBottom: '1rem' }}>
        <h2 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--color-text)', marginBottom: '0.75rem' }}>
          Company Engagement Details
        </h2>
        <DataTable
          columns={columns}
          data={sortedCompanies}
          onSort={handleSort}
        />
      </div>

      {/* Section 4: Country Distribution */}
      <div>
        <ChartCard title="Top Countries by Registrations" subtitle="Top 10 countries">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart
              data={top10Countries}
              layout="vertical"
              margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis type="number" tick={{ fontSize: 11 }} stroke="var(--color-text-secondary)" />
              <YAxis
                dataKey="country"
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
              <Bar dataKey="count" fill="var(--color-primary)" radius={[0, 4, 4, 0]} name="Registrations" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </div>
  )
}
