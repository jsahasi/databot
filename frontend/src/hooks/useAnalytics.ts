import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../services/api'
import { analyticsApi } from '../services/api'

export interface SyncStatus {
  id: number
  status: 'running' | 'completed' | 'failed'
  started_at: string
  completed_at: string | null
  events_synced: number
  error_message: string | null
}

export interface DashboardSummary {
  totalEvents: number
  totalAttendees: number
  totalRegistrants: number
  avgEngagementRate: number
}

export interface TrendPoint {
  date: string
  attendees: number
  registrants: number
}

export interface TopEvent {
  title: string
  attendees: number
  registrants: number
}

export function useSyncStatus() {
  return useQuery<SyncStatus[]>({
    queryKey: ['syncStatus'],
    queryFn: async () => {
      const { data } = await api.get('/sync/status')
      return data
    },
    refetchInterval: 10000,
  })
}

export function useTriggerSync() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post('/sync/trigger')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['syncStatus'] })
    },
  })
}

export function useDashboard() {
  return useQuery<DashboardSummary>({
    queryKey: ['dashboard'],
    queryFn: async () => {
      const { data } = await api.get('/analytics/dashboard')
      return data
    },
  })
}

export function useTrends() {
  return useQuery<TrendPoint[]>({
    queryKey: ['trends'],
    queryFn: async () => {
      const { data } = await api.get('/analytics/trends')
      return data
    },
  })
}

export function useTopEvents(limit = 10) {
  return useQuery<TopEvent[]>({
    queryKey: ['topEvents', limit],
    queryFn: async () => {
      const { data } = await api.get('/analytics/top-events', { params: { limit } })
      return data
    },
  })
}

export function useAudienceAnalytics() {
  return useQuery({
    queryKey: ['audience-analytics'],
    queryFn: analyticsApi.audiences,
  })
}

export function useContentPerformance() {
  return useQuery({
    queryKey: ['content-performance'],
    queryFn: analyticsApi.contentPerformance,
  })
}

export function useEngagementHeatmap() {
  return useQuery({
    queryKey: ['engagement-heatmap'],
    queryFn: analyticsApi.engagementHeatmap,
  })
}
