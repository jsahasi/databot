export interface Event {
  id: number
  on24EventId: number
  title: string
  description: string | null
  eventType: string
  status: string
  startTime: string
  endTime: string
  totalRegistrants: number
  totalAttendees: number
}
