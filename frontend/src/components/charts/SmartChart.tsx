/**
 * SmartChart — picks the best charting library for each visualization type.
 *
 * Nivo:    bar, pie, radar, calendar-heatmap  (beautiful defaults, dark-mode)
 * ECharts: funnel, gauge, treemap, sankey     (rich interactive types)
 * Plotly:  scatter, waterfall, heatmap-2d     (analytical / exploratory)
 * Recharts (fallback): basic line             (already in bundle, lightweight)
 */

import { lazy, Suspense, useMemo } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'

/* ---------- lazy imports (code-split per library) ---------- */

const ResponsiveBar = lazy(() => import('@nivo/bar').then(m => ({ default: m.ResponsiveBar })))
const ResponsivePie = lazy(() => import('@nivo/pie').then(m => ({ default: m.ResponsivePie })))
const ResponsiveRadar = lazy(() => import('@nivo/radar').then(m => ({ default: m.ResponsiveRadar })))
// ResponsiveFunnel replaced by custom FunnelChart (centered horizontal bars with drop-off labels)
const ReactECharts = lazy(() => import('echarts-for-react'))
const Plot = lazy(() => import('react-plotly.js'))

/* ---------- palette ---------- */

const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#0ea5e9', '#ec4899', '#14b8a6', '#f97316', '#64748b']

/* ---------- axis label formatting ---------- */

/** Intelligently format x-axis labels based on data density and range */
function formatAxisLabel(value: string, _index: number, allLabels: string[]): string {
  if (!value) return value

  // Try parsing as a date
  const d = new Date(value)
  if (!isNaN(d.getTime()) && value.length >= 6) {
    const rangeMs = allLabels.length > 1
      ? Math.abs(new Date(allLabels[allLabels.length - 1]).getTime() - new Date(allLabels[0]).getTime())
      : 0
    const rangeDays = rangeMs / (1000 * 60 * 60 * 24)

    if (rangeDays > 365) {
      // Multi-year: show quarters or just month + year
      const q = Math.floor(d.getMonth() / 3) + 1
      return allLabels.length > 12
        ? `Q${q} ${d.getFullYear()}`
        : d.toLocaleDateString('en-US', { month: 'short', year: '2-digit' })
    }
    if (rangeDays > 90) {
      // Several months: "Mar '26"
      return d.toLocaleDateString('en-US', { month: 'short', year: '2-digit' })
    }
    if (rangeDays > 14) {
      // Weeks: "Mar 5"
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    }
    // Days: "Mar 5"
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  // Non-date: truncate long labels
  if (value.length > 20) return value.slice(0, 18) + '...'
  return value
}

/** Decide how many ticks to show based on label count */
function tickInterval(count: number): number | undefined {
  if (count <= 8) return 0 // show all
  if (count <= 16) return 1 // every other
  if (count <= 30) return 2
  return Math.floor(count / 10)
}

/* ---------- Nivo dark theme ---------- */

const NIVO_THEME = {
  text: { fill: '#94a3b8' },
  axis: {
    ticks: { text: { fill: '#94a3b8', fontSize: 11 } },
    legend: { text: { fill: '#94a3b8', fontSize: 12 } },
  },
  grid: { line: { stroke: '#1e293b' } },
  legends: { text: { fill: '#94a3b8', fontSize: 11 } },
  tooltip: {
    container: { background: '#1e293b', color: '#e2e8f0', fontSize: 12, borderRadius: 6, boxShadow: '0 4px 12px rgba(0,0,0,0.3)' },
  },
}

/* ---------- chart type definitions ---------- */

export interface SmartChartData {
  type: 'bar' | 'line' | 'pie' | 'radar' | 'funnel' | 'gauge' | 'treemap' | 'scatter' | 'heatmap' | 'waterfall'
  data: any[]
  title?: string
  x_key?: string
  y_keys?: string[]
  yLabel?: string
  groupMode?: 'stacked' | 'grouped'
}

const ChartLoading = () => (
  <div style={{ height: 260, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b', fontSize: '0.8rem' }}>
    Loading chart...
  </div>
)

/* ---------- individual chart renderers ---------- */

function NivoBar({ data, xKey, yKeys, groupMode = 'grouped' }: { data: any[]; xKey: string; yKeys: string[]; groupMode?: 'stacked' | 'grouped' }) {
  // Format labels for axis
  const allLabels = data.map(d => String(d[xKey]))

  // Pretty-print y_key labels for legend
  const formatKeyLabel = (key: string) => key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())

  return (
    <div style={{ height: 280 }}>
      <Suspense fallback={<ChartLoading />}>
        <ResponsiveBar
          data={data}
          keys={yKeys}
          indexBy={xKey}
          groupMode={groupMode}
          margin={{ top: 10, right: yKeys.length > 1 ? 140 : 20, bottom: 50, left: 60 }}
          padding={0.3}
          colors={COLORS}
          borderRadius={groupMode === 'stacked' ? 0 : 3}
          theme={NIVO_THEME}
          axisBottom={{
            tickSize: 0,
            tickPadding: 8,
            format: (v: any) => formatAxisLabel(String(v), 0, allLabels),
            tickRotation: allLabels.some(l => l.length > 10) ? -35 : 0,
          }}
          axisLeft={{
            tickSize: 0,
            tickPadding: 8,
            format: (v: any) => typeof v === 'number' && v >= 1000 ? `${(v / 1000).toFixed(v >= 10000 ? 0 : 1)}k` : v,
          }}
          labelSkipWidth={32}
          labelSkipHeight={16}
          labelTextColor={{ from: 'color', modifiers: [['brighter', 3]] }}
          animate
          motionConfig="gentle"
          legends={yKeys.length > 1 ? [{
            dataFrom: 'keys',
            anchor: 'bottom-right',
            direction: 'column',
            translateX: 130,
            itemWidth: 120,
            itemHeight: 20,
            symbolSize: 10,
            symbolShape: 'circle',
          }] : []}
          tooltip={({ id, value, indexValue }) => (
            <div style={{ background: '#1e293b', color: '#e2e8f0', padding: '6px 10px', borderRadius: 6, fontSize: 12, boxShadow: '0 4px 12px rgba(0,0,0,0.3)' }}>
              <strong>{formatKeyLabel(String(id))}</strong>: {typeof value === 'number' && value >= 1000 ? value.toLocaleString() : value}
              <br /><span style={{ color: '#94a3b8' }}>{indexValue}</span>
            </div>
          )}
        />
      </Suspense>
    </div>
  )
}

function NivoPie({ data }: { data: any[] }) {
  // Expects [{name, value}] format from generate_chart_data
  const pieData = data.map((d, i) => ({
    id: d.name || d.label || `item-${i}`,
    label: d.name || d.label || `item-${i}`,
    value: d.value || 0,
  }))

  return (
    <div style={{ height: 280 }}>
      <Suspense fallback={<ChartLoading />}>
        <ResponsivePie
          data={pieData}
          margin={{ top: 20, right: 80, bottom: 20, left: 80 }}
          innerRadius={0.45}
          padAngle={1.5}
          cornerRadius={4}
          colors={COLORS}
          borderWidth={0}
          theme={NIVO_THEME}
          arcLinkLabelsSkipAngle={12}
          arcLinkLabelsTextColor="#94a3b8"
          arcLinkLabelsThickness={1.5}
          arcLinkLabelsColor={{ from: 'color' }}
          arcLabelsSkipAngle={15}
          arcLabelsTextColor={{ from: 'color', modifiers: [['brighter', 3]] }}
          animate
          motionConfig="gentle"
        />
      </Suspense>
    </div>
  )
}

function NivoRadar({ data, xKey, yKeys }: { data: any[]; xKey: string; yKeys: string[] }) {
  return (
    <div style={{ height: 300 }}>
      <Suspense fallback={<ChartLoading />}>
        <ResponsiveRadar
          data={data}
          keys={yKeys}
          indexBy={xKey}
          maxValue="auto"
          margin={{ top: 40, right: 60, bottom: 40, left: 60 }}
          colors={COLORS}
          borderWidth={2}
          dotSize={8}
          dotColor={{ theme: 'background' }}
          dotBorderWidth={2}
          dotBorderColor={{ from: 'color' }}
          theme={NIVO_THEME}
          gridShape="circular"
          animate
          motionConfig="gentle"
        />
      </Suspense>
    </div>
  )
}

function FunnelChart({ data, xKey }: { data: any[]; xKey: string }) {
  const valueKey = Object.keys(data[0] || {}).find(k => k !== xKey && typeof data[0][k] === 'number') || 'value'
  const stages = data.map((d, i) => ({
    label: d[xKey] || d.name || `Stage ${i + 1}`,
    value: d[valueKey] || d.value || 0,
    color: COLORS[i % COLORS.length],
  }))

  const maxValue = Math.max(...stages.map(s => s.value), 1)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, padding: '12px 0' }}>
      {stages.map((stage, i) => {
        const widthPct = Math.max(20, (stage.value / maxValue) * 100)
        const dropoff = i > 0 ? ((stages[i - 1].value - stage.value) / stages[i - 1].value * 100) : 0

        return (
          <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '100%' }}>
            <div
              style={{
                width: `${widthPct}%`,
                minWidth: 120,
                background: `linear-gradient(135deg, ${stage.color}, ${stage.color}cc)`,
                borderRadius: 6,
                padding: '10px 16px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                transition: 'width 0.6s ease',
                position: 'relative',
              }}
            >
              <span style={{ color: '#fff', fontSize: 13, fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {stage.label}
              </span>
              <span style={{ color: '#fff', fontSize: 13, fontWeight: 600, marginLeft: 12 }}>
                {stage.value.toLocaleString()}
              </span>
            </div>
            {i > 0 && dropoff > 0 && (
              <span style={{ fontSize: 10, color: '#ef4444', marginTop: -2, marginBottom: -2 }}>
                ▼ {dropoff.toFixed(1)}% drop-off
              </span>
            )}
          </div>
        )
      })}
    </div>
  )
}

function EChartsGauge({ data }: { data: any[] }) {
  const value = data[0]?.value ?? data[0]?.engagement ?? 0
  const label = data[0]?.name ?? data[0]?.label ?? 'Score'

  const option = useMemo(() => ({
    series: [{
      type: 'gauge',
      startAngle: 200,
      endAngle: -20,
      min: 0,
      max: 100,
      radius: '90%',
      progress: { show: true, width: 14, itemStyle: { color: '#6366f1' } },
      axisLine: { lineStyle: { width: 14, color: [[1, '#1e293b']] } },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { show: false },
      pointer: { show: false },
      title: { offsetCenter: [0, '60%'], fontSize: 13, color: '#94a3b8' },
      detail: {
        offsetCenter: [0, '10%'],
        fontSize: 28,
        fontWeight: 600,
        color: '#e2e8f0',
        formatter: '{value}',
      },
      data: [{ value, name: label }],
    }],
  }), [value, label])

  return (
    <div style={{ height: 220 }}>
      <Suspense fallback={<ChartLoading />}>
        <ReactECharts option={option} style={{ height: '100%' }} theme="dark" />
      </Suspense>
    </div>
  )
}

function EChartsTreemap({ data, xKey }: { data: any[]; xKey: string }) {
  const valueKey = Object.keys(data[0] || {}).find(k => k !== xKey && typeof data[0][k] === 'number') || 'value'
  const option = useMemo(() => ({
    tooltip: { formatter: '{b}: {c}' },
    series: [{
      type: 'treemap',
      roam: false,
      breadcrumb: { show: false },
      label: { show: true, fontSize: 11, color: '#fff' },
      itemStyle: { borderColor: '#0f172a', borderWidth: 2, gapWidth: 2 },
      levels: [{ itemStyle: { borderColor: '#0f172a', borderWidth: 3, gapWidth: 3 }, upperLabel: { show: false } }],
      data: data.map((d, i) => ({
        name: d[xKey] || d.name || `item-${i}`,
        value: d[valueKey] || 0,
        itemStyle: { color: COLORS[i % COLORS.length] },
      })),
    }],
  }), [data, xKey, valueKey])

  return (
    <div style={{ height: 280 }}>
      <Suspense fallback={<ChartLoading />}>
        <ReactECharts option={option} style={{ height: '100%' }} theme="dark" />
      </Suspense>
    </div>
  )
}

function PlotlyScatter({ data, xKey, yKeys }: { data: any[]; xKey: string; yKeys: string[] }) {
  const yKey = yKeys[0] || Object.keys(data[0] || {}).find(k => k !== xKey) || ''
  const allLabels = data.map(d => String(d[xKey]))

  return (
    <div style={{ height: 280 }}>
      <Suspense fallback={<ChartLoading />}>
        <Plot
          data={[{
            type: 'scatter',
            mode: 'markers',
            x: data.map(d => d[xKey]),
            y: data.map(d => d[yKey]),
            text: data.map(d => d.name || d.label || d[xKey]),
            marker: {
              size: data.map(d => Math.max(8, Math.min(30, (d.size || d.attendees || 12)))),
              color: data.map(d => d[yKey]),
              colorscale: 'Viridis',
              showscale: true,
              opacity: 0.8,
            },
            hovertemplate: '%{text}<br>%{xaxis.title.text}: %{x}<br>%{yaxis.title.text}: %{y}<extra></extra>',
          }]}
          layout={{
            margin: { t: 10, r: 10, b: 50, l: 60 },
            height: 280,
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'transparent',
            font: { size: 11, color: '#94a3b8' },
            xaxis: {
              title: xKey.replace(/_/g, ' '),
              gridcolor: '#1e293b',
              tickvals: allLabels.length > 15 ? undefined : undefined,
            },
            yaxis: { title: yKey.replace(/_/g, ' '), gridcolor: '#1e293b' },
          }}
          config={{ displayModeBar: false, responsive: true }}
          style={{ width: '100%' }}
        />
      </Suspense>
    </div>
  )
}

function PlotlyHeatmap({ data, xKey, yKeys }: { data: any[]; xKey: string; yKeys: string[] }) {
  // Build matrix from flat data
  const xVals = [...new Set(data.map(d => d[xKey]))]
  const yKey = yKeys[0] || 'category'
  const zKey = yKeys[1] || Object.keys(data[0] || {}).find(k => k !== xKey && k !== yKey) || 'value'
  const yVals = [...new Set(data.map(d => d[yKey]))]
  const z = yVals.map(y => xVals.map(x => {
    const row = data.find(d => d[xKey] === x && d[yKey] === y)
    return row ? row[zKey] : 0
  }))

  return (
    <div style={{ height: 280 }}>
      <Suspense fallback={<ChartLoading />}>
        <Plot
          data={[{
            type: 'heatmap',
            z,
            x: xVals.map(v => formatAxisLabel(String(v), 0, xVals.map(String))),
            y: yVals.map(String),
            colorscale: 'RdYlGn',
            showscale: true,
            hovertemplate: '%{y} / %{x}: %{z:.1f}<extra></extra>',
          }]}
          layout={{
            margin: { t: 10, r: 10, b: 50, l: 80 },
            height: 280,
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'transparent',
            font: { size: 11, color: '#94a3b8' },
          }}
          config={{ displayModeBar: false, responsive: true }}
          style={{ width: '100%' }}
        />
      </Suspense>
    </div>
  )
}

function PlotlyWaterfall({ data, xKey, yKeys }: { data: any[]; xKey: string; yKeys: string[] }) {
  const yKey = yKeys[0] || Object.keys(data[0] || {}).find(k => k !== xKey) || 'value'
  return (
    <div style={{ height: 280 }}>
      <Suspense fallback={<ChartLoading />}>
        <Plot
          data={[{
            type: 'waterfall',
            orientation: 'v',
            x: data.map(d => formatAxisLabel(String(d[xKey]), 0, data.map(dd => String(dd[xKey])))),
            y: data.map(d => d[yKey]),
            connector: { line: { color: '#475569' } },
            increasing: { marker: { color: '#10b981' } },
            decreasing: { marker: { color: '#ef4444' } },
            totals: { marker: { color: '#6366f1' } },
          }]}
          layout={{
            margin: { t: 10, r: 10, b: 50, l: 60 },
            height: 280,
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'transparent',
            font: { size: 11, color: '#94a3b8' },
            xaxis: { gridcolor: '#1e293b' },
            yaxis: { gridcolor: '#1e293b' },
            showlegend: false,
          }}
          config={{ displayModeBar: false, responsive: true }}
          style={{ width: '100%' }}
        />
      </Suspense>
    </div>
  )
}

function RechartsLine({ data, xKey, yKeys, yLabel }: { data: any[]; xKey: string; yKeys: string[]; yLabel?: string }) {
  const allLabels = data.map(d => String(d[xKey]))
  const interval = tickInterval(allLabels.length)

  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis
          dataKey={xKey}
          tick={{ fontSize: 11, fill: '#94a3b8' }}
          tickFormatter={(v, i) => formatAxisLabel(String(v), i, allLabels)}
          interval={interval}
        />
        <YAxis
          tick={{ fontSize: 11, fill: '#94a3b8' }}
          tickFormatter={(v: number) => v >= 1000 ? `${(v / 1000).toFixed(v >= 10000 ? 0 : 1)}k` : String(v)}
          label={yLabel ? { value: yLabel, angle: -90, position: 'insideLeft', style: { fontSize: 11, fill: '#94a3b8' } } : undefined}
        />
        <Tooltip contentStyle={{ fontSize: '0.75rem', background: '#1e293b', border: '1px solid #334155', borderRadius: 6, color: '#e2e8f0' }} />
        {yKeys.length > 1 && <Legend wrapperStyle={{ fontSize: '0.75rem' }} />}
        {yKeys.map((key, i) => (
          <Line key={key} type="monotone" dataKey={key} stroke={COLORS[i % COLORS.length]} dot={false} strokeWidth={2} />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}

/* ---------- main component ---------- */

export default function SmartChart({ data: chartData }: { data: SmartChartData }) {
  if (!chartData?.data?.length) return null

  const { type, data, title, x_key, y_keys, yLabel, groupMode } = chartData

  // Derive keys if not provided
  const keys = Object.keys(data[0] || {})
  const xKey = x_key || keys[0] || ''
  const yKeys = y_keys || keys.filter(k => k !== xKey && typeof data[0][k] === 'number')

  return (
    <div
      role="img"
      aria-label={title ? `Chart: ${title}` : 'Chart'}
      style={{ marginTop: '0.75rem', width: '100%', maxWidth: 580 }}
    >
      {title && (
        <p aria-hidden="true" style={{ fontSize: '0.78rem', fontWeight: 600, color: '#94a3b8', marginBottom: '0.5rem' }}>
          {title}
        </p>
      )}

      {type === 'bar'       && <NivoBar data={data} xKey={xKey} yKeys={yKeys} groupMode={groupMode} />}
      {type === 'pie'       && <NivoPie data={data} />}
      {type === 'radar'     && <NivoRadar data={data} xKey={xKey} yKeys={yKeys} />}
      {type === 'funnel'    && <FunnelChart data={data} xKey={xKey} />}
      {type === 'gauge'     && <EChartsGauge data={data} />}
      {type === 'treemap'   && <EChartsTreemap data={data} xKey={xKey} />}
      {type === 'scatter'   && <PlotlyScatter data={data} xKey={xKey} yKeys={yKeys} />}
      {type === 'heatmap'   && <PlotlyHeatmap data={data} xKey={xKey} yKeys={yKeys} />}
      {type === 'waterfall' && <PlotlyWaterfall data={data} xKey={xKey} yKeys={yKeys} />}
      {type === 'line'      && <RechartsLine data={data} xKey={xKey} yKeys={yKeys} yLabel={yLabel} />}
    </div>
  )
}
