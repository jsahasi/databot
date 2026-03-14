import { createContext, useContext, useState, ReactNode } from 'react'
import { useChat } from '../hooks/useChat'

interface CalendarContextValue {
  isCalendarOpen: boolean
  calendarProposedMode: boolean
  openCalendar: () => void
  openProposedCalendar: () => void
  closeCalendar: () => void
}

type ChatContextValue = ReturnType<typeof useChat> & CalendarContextValue

const ChatContext = createContext<ChatContextValue | null>(null)

export function ChatProvider({ children }: { children: ReactNode }) {
  const chat = useChat()
  const [isCalendarOpen, setIsCalendarOpen] = useState(false)
  const [calendarProposedMode, setCalendarProposedMode] = useState(false)

  const value: ChatContextValue = {
    ...chat,
    isCalendarOpen,
    calendarProposedMode,
    openCalendar: () => { setCalendarProposedMode(false); setIsCalendarOpen(true) },
    openProposedCalendar: () => { setCalendarProposedMode(true); setIsCalendarOpen(true) },
    closeCalendar: () => setIsCalendarOpen(false),
  }

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>
}

export function useChatContext(): ChatContextValue {
  const ctx = useContext(ChatContext)
  if (!ctx) throw new Error('useChatContext must be used inside ChatProvider')
  return ctx
}
