import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// Types
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
}

export interface EventSummary {
  id: number
  on24_event_id: number
  title: string
  event_type: string | null
  content_type: string | null
  is_active: boolean
  live_start: string | null
  live_end: string | null
  total_registrants: number
  total_attendees: number
  engagement_score: number | null
}

export interface EventDetail extends EventSummary {
  description: string | null
  start_time: string | null
  end_time: string | null
  live_attendees: number
  on_demand_attendees: number
  no_show_count: number
  tags: Record<string, any> | null
  synced_at: string | null
}

export interface AttendeeSummary {
  id: number
  on24_attendee_id: number
  on24_event_id: number
  email: string
  first_name: string | null
  last_name: string | null
  company: string | null
  engagement_score: number | null
  live_minutes: number | null
  archive_minutes: number | null
  asked_questions: number
  answered_polls: number
}

export interface RegistrantSummary {
  id: number
  on24_registrant_id: number
  on24_event_id: number
  email: string
  first_name: string | null
  last_name: string | null
  company: string | null
  job_title: string | null
  registration_date: string | null
  utm_source: string | null
}

export interface DashboardKPI {
  total_events: number
  total_attendees: number
  total_registrants: number
  avg_engagement_score: number | null
  conversion_rate: number | null
}

export interface TrendPoint {
  period: string
  event_count: number
  total_attendees: number
  avg_engagement: number | null
}

export interface TopEvent {
  on24_event_id: number
  title: string
  live_start: string | null
  total_attendees: number
  engagement_score: number | null
}

export interface SyncStatus {
  id: number
  entity_type: string
  status: string
  records_synced: number
  started_at: string | null
  completed_at: string | null
  error_message: string | null
}

export interface CompanyAudience {
  company: string
  events_attended: number
  total_attendances: number
  avg_engagement: number | null
}

export interface AudienceAnalytics {
  top_companies: CompanyAudience[]
  registration_sources: Array<{ source: string; count: number }>
  country_distribution: Array<{ country: string; count: number }>
}

export interface ContentTypePerformance {
  event_type: string
  event_count: number
  avg_attendees: number
  avg_engagement: number | null
  avg_conversion_rate: number | null
}

export interface ContentPerformance {
  by_type: ContentTypePerformance[]
  top_events: TopEvent[]
}

export interface HeatmapPoint {
  day: number
  hour: number
  avg_engagement: number
  event_count: number
}

// API functions
export const eventsApi = {
  list: (params?: { page?: number; per_page?: number; search?: string; sort_by?: string; sort_order?: string }) =>
    api.get<PaginatedResponse<EventSummary>>('/events', { params }).then(r => r.data),

  get: (eventId: number) =>
    api.get<EventDetail>(`/events/${eventId}`).then(r => r.data),

  attendees: (eventId: number, params?: { page?: number; per_page?: number; search?: string }) =>
    api.get<PaginatedResponse<AttendeeSummary>>(`/events/${eventId}/attendees`, { params }).then(r => r.data),

  registrants: (eventId: number, params?: { page?: number; per_page?: number; search?: string }) =>
    api.get<PaginatedResponse<RegistrantSummary>>(`/events/${eventId}/registrants`, { params }).then(r => r.data),
}

export const analyticsApi = {
  dashboard: () => api.get<DashboardKPI>('/analytics/dashboard').then(r => r.data),
  trends: (months?: number) => api.get<TrendPoint[]>('/analytics/trends', { params: { months } }).then(r => r.data),
  topEvents: (limit?: number, sort_by?: string) =>
    api.get<TopEvent[]>('/analytics/top-events', { params: { limit, sort_by } }).then(r => r.data),
  audiences: () => api.get<AudienceAnalytics>('/analytics/audiences').then(r => r.data),
  contentPerformance: () => api.get<ContentPerformance>('/analytics/content-performance').then(r => r.data),
  engagementHeatmap: () => api.get<HeatmapPoint[]>('/analytics/engagement-heatmap').then(r => r.data),
}

export const syncApi = {
  trigger: () => api.post('/sync/trigger').then(r => r.data),
  status: () => api.get<SyncStatus[]>('/sync/status').then(r => r.data),
}

export default api
