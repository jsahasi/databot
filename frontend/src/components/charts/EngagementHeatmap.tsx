import { lazy, Suspense } from 'react'
import type { HeatmapPoint } from '../../services/api'

const Plot = lazy(() => import('react-plotly.js'))

interface EngagementHeatmapProps {
  data: HeatmapPoint[]
}

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const HOURS = Array.from({ length: 24 }, (_, i) => `${i.toString().padStart(2, '0')}:00`)

export default function EngagementHeatmap({ data }: EngagementHeatmapProps) {
  // Build 7x24 matrix
  const matrix: number[][] = Array.from({ length: 7 }, () => Array(24).fill(0))
  data.forEach(p => {
    if (p.day >= 0 && p.day < 7 && p.hour >= 0 && p.hour < 24) {
      matrix[p.day][p.hour] = p.avg_engagement
    }
  })

  return (
    <Suspense fallback={
      <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        Loading chart...
      </div>
    }>
      <Plot
        data={[{
          type: 'heatmap',
          z: matrix,
          x: HOURS,
          y: DAYS,
          colorscale: 'RdYlGn',
          showscale: true,
          hovertemplate: '%{y} %{x}: %{z:.1f} engagement<extra></extra>',
        }]}
        layout={{
          margin: { t: 10, r: 10, b: 40, l: 50 },
          height: 220,
          paper_bgcolor: 'transparent',
          plot_bgcolor: 'transparent',
          font: { size: 11 },
          xaxis: { tickangle: -45 },
        }}
        config={{ displayModeBar: false, responsive: true }}
        style={{ width: '100%' }}
      />
    </Suspense>
  )
}
