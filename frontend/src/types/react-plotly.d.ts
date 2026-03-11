declare module 'react-plotly.js' {
  import * as Plotly from 'plotly.js'
  import { Component, CSSProperties } from 'react'

  interface PlotParams {
    data: Plotly.Data[]
    layout?: Partial<Plotly.Layout>
    config?: Partial<Plotly.Config>
    style?: CSSProperties
    className?: string
    onInitialized?: (figure: Plotly.Figure, graphDiv: HTMLElement) => void
    onUpdate?: (figure: Plotly.Figure, graphDiv: HTMLElement) => void
    onPurge?: (figure: Plotly.Figure, graphDiv: HTMLElement) => void
    onError?: (err: Error) => void
    divId?: string
    useResizeHandler?: boolean
    debug?: boolean
    frames?: Plotly.Frame[]
    onAfterExport?: () => void
    onAfterPlot?: () => void
    onAnimated?: () => void
    onAnimatingFrame?: (event: Plotly.FrameAnimationEvent) => void
    onAnimationInterrupted?: () => void
    onAutoSize?: () => void
    onBeforeExport?: () => void
    onButtonClicked?: (event: Plotly.ButtonClickEvent) => void
    onClick?: (event: Plotly.PlotMouseEvent) => void
    onClickAnnotation?: (event: Plotly.ClickAnnotationEvent) => void
    onDeselect?: () => void
    onDoubleClick?: () => void
    onFramework?: () => void
    onHover?: (event: Plotly.PlotMouseEvent) => void
    onLegendClick?: (event: Plotly.LegendClickEvent) => boolean
    onLegendDoubleClick?: (event: Plotly.LegendClickEvent) => boolean
    onRelayout?: (event: Plotly.PlotRelayoutEvent) => void
    onRestyle?: (event: Plotly.PlotRestyleEvent) => void
    onSelected?: (event: Plotly.PlotSelectionEvent) => void
    onSelecting?: (event: Plotly.PlotSelectionEvent) => void
    onSliderChange?: (event: Plotly.SliderChangeEvent) => void
    onSliderEnd?: (event: Plotly.SliderEndEvent) => void
    onSliderStart?: (event: Plotly.SliderStartEvent) => void
    onTransitioning?: () => void
    onTransitionInterrupted?: () => void
    onUnhover?: (event: Plotly.PlotMouseEvent) => void
    onWebGlContextLost?: () => void
    revision?: number
  }

  class Plot extends Component<PlotParams> {}
  export default Plot
}
