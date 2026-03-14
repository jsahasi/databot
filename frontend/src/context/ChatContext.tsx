import { createContext, useContext, useState, ReactNode } from 'react'
import { useChat } from '../hooks/useChat'

export interface ProposedEvent {
  title: string
  date: string        // YYYY-MM-DD
  time: string        // HH:MM
  duration_minutes: number
  funnel_stage?: string
  topic?: string
}

interface CalendarContextValue {
  isCalendarOpen: boolean
  calendarProposedMode: boolean
  proposedEvents: ProposedEvent[]
  openCalendar: () => void
  openProposedCalendar: () => void
  setProposedEvents: (events: ProposedEvent[]) => void
  closeCalendar: () => void
}

type ChatContextValue = ReturnType<typeof useChat> & CalendarContextValue

const ChatContext = createContext<ChatContextValue | null>(null)

export function ChatProvider({ children }: { children: ReactNode }) {
  const chat = useChat()
  const [isCalendarOpen, setIsCalendarOpen] = useState(false)
  const [calendarProposedMode, setCalendarProposedMode] = useState(false)
  const [proposedEvents, setProposedEvents] = useState<ProposedEvent[]>([])

  const value: ChatContextValue = {
    ...chat,
    isCalendarOpen,
    calendarProposedMode,
    proposedEvents,
    openCalendar: () => { setCalendarProposedMode(false); setIsCalendarOpen(true) },
    openProposedCalendar: () => { setCalendarProposedMode(true); setIsCalendarOpen(true) },
    setProposedEvents,
    closeCalendar: () => setIsCalendarOpen(false),
  }

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>
}

export function useChatContext(): ChatContextValue {
  const ctx = useContext(ChatContext)
  if (!ctx) throw new Error('useChatContext must be used inside ChatProvider')
  return ctx
}
