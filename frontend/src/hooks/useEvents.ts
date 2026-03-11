import { useQuery } from '@tanstack/react-query'
import { eventsApi } from '../services/api'

export function useEvents(params?: { page?: number; per_page?: number; search?: string; sort_by?: string; sort_order?: string }) {
  return useQuery({
    queryKey: ['events', params],
    queryFn: () => eventsApi.list(params),
  })
}

export function useEvent(eventId: number) {
  return useQuery({
    queryKey: ['event', eventId],
    queryFn: () => eventsApi.get(eventId),
    enabled: !!eventId,
  })
}

export function useEventAttendees(eventId: number, params?: { page?: number; per_page?: number; search?: string }) {
  return useQuery({
    queryKey: ['event-attendees', eventId, params],
    queryFn: () => eventsApi.attendees(eventId, params),
    enabled: !!eventId,
  })
}

export function useEventRegistrants(eventId: number, params?: { page?: number; per_page?: number; search?: string }) {
  return useQuery({
    queryKey: ['event-registrants', eventId, params],
    queryFn: () => eventsApi.registrants(eventId, params),
    enabled: !!eventId,
  })
}
