import { useState, useRef, useCallback, useEffect } from 'react'
import { useClientContext } from '../context/ClientContext'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  agentUsed?: string | null
  chartData?: any | null
  eventCard?: any | null
  eventCards?: any[] | null
  pollCards?: any[] | null
  contentArticles?: any[] | null
  proposedEvents?: any[] | null
  suggestions?: string[]
  isLoading?: boolean
  timestamp: Date
}

interface UseChatOptions {
  sessionId?: string
}

export function useChat(options: UseChatOptions = {}) {
  const { sessionId = 'default' } = options
  const { selectedClientId } = useClientContext()
  const clientIdRef = useRef(selectedClientId)
  useEffect(() => { clientIdRef.current = selectedClientId }, [selectedClientId])
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [activeAgent, setActiveAgent] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const pendingMessageRef = useRef<string | null>(null)
  const isProcessingRef = useRef(false)
  const queueRef = useRef<string[]>([])

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/chat`)

    ws.onopen = () => {
      setIsConnected(true)
      // Send any pending message
      if (pendingMessageRef.current) {
        ws.send(JSON.stringify({
          type: 'message',
          content: pendingMessageRef.current,
          session_id: sessionId,
          client_id: clientIdRef.current,
          permissions: JSON.parse(sessionStorage.getItem('adminPermissions') || '[]'),
        }))
        pendingMessageRef.current = null
      }
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)

      switch (data.type) {
        case 'agent_start':
          setActiveAgent(data.agent)
          setIsProcessing(true)
          isProcessingRef.current = true
          break

        case 'agent_routing':
          setActiveAgent(data.target)
          break

        case 'text':
          setMessages(prev => {
            // Update the last assistant message or create new one
            const last = prev[prev.length - 1]
            if (last && last.role === 'assistant' && last.isLoading) {
              return [
                ...prev.slice(0, -1),
                { ...last, content: data.content, isLoading: false },
              ]
            }
            return [
              ...prev,
              {
                id: `msg-${Date.now()}`,
                role: 'assistant',
                content: data.content,
                isLoading: false,
                timestamp: new Date(),
              },
            ]
          })
          break

        case 'chart_data':
          setMessages(prev => {
            const last = prev[prev.length - 1]
            if (last && last.role === 'assistant') {
              return [
                ...prev.slice(0, -1),
                { ...last, chartData: data.data },
              ]
            }
            return prev
          })
          break

        case 'event_card':
          setMessages(prev => {
            const last = prev[prev.length - 1]
            if (last && last.role === 'assistant') {
              return [
                ...prev.slice(0, -1),
                { ...last, eventCard: data.data },
              ]
            }
            return prev
          })
          break

        case 'event_cards':
          setMessages(prev => {
            const last = prev[prev.length - 1]
            if (last && last.role === 'assistant') {
              return [
                ...prev.slice(0, -1),
                { ...last, eventCards: data.data },
              ]
            }
            return prev
          })
          break

        case 'poll_cards':
          setMessages(prev => {
            const last = prev[prev.length - 1]
            if (last && last.role === 'assistant') {
              return [
                ...prev.slice(0, -1),
                { ...last, pollCards: data.data },
              ]
            }
            return prev
          })
          break

        case 'content_articles':
          setMessages(prev => {
            const last = prev[prev.length - 1]
            if (last && last.role === 'assistant') {
              return [
                ...prev.slice(0, -1),
                { ...last, contentArticles: data.data },
              ]
            }
            return prev
          })
          break

        case 'proposed_events':
          setMessages(prev => {
            const last = prev[prev.length - 1]
            if (last && last.role === 'assistant') {
              return [
                ...prev.slice(0, -1),
                { ...last, proposedEvents: data.data },
              ]
            }
            return prev
          })
          break

        case 'message_complete':
          setIsProcessing(false)
          isProcessingRef.current = false
          setActiveAgent(null)
          setMessages(prev => {
            const last = prev[prev.length - 1]
            if (last && last.role === 'assistant') {
              return [
                ...prev.slice(0, -1),
                { ...last, agentUsed: data.agent_used, isLoading: false },
              ]
            }
            return prev
          })
          // Drain queue: send next message if one was typed while processing
          if (queueRef.current.length > 0) {
            const next = queueRef.current.shift()!
            setMessages(prev => [
              ...prev,
              { id: `loading-${Date.now()}`, role: 'assistant', content: '', isLoading: true, timestamp: new Date() },
            ])
            setIsProcessing(true)
            isProcessingRef.current = true
            ws.send(JSON.stringify({ type: 'message', content: next, session_id: sessionId, client_id: selectedClientId, permissions: JSON.parse(sessionStorage.getItem('adminPermissions') || '[]') }))
          }
          break

        case 'suggestions':
          setMessages(prev => {
            // Find the last assistant message and attach suggestions to it
            for (let i = prev.length - 1; i >= 0; i--) {
              if (prev[i].role === 'assistant') {
                const updated = [...prev]
                updated[i] = { ...updated[i], suggestions: data.suggestions }
                return updated
              }
            }
            return prev
          })
          break

        case 'error':
          setIsProcessing(false)
          setActiveAgent(null)
          setMessages(prev => [
            ...prev,
            {
              id: `err-${Date.now()}`,
              role: 'assistant',
              content: `Error: ${data.message}`,
              isLoading: false,
              timestamp: new Date(),
            },
          ])
          break
      }
    }

    ws.onclose = () => {
      setIsConnected(false)
      // Auto-reconnect after 3 seconds
      setTimeout(connect, 3000)
    }

    ws.onerror = () => {
      setIsConnected(false)
    }

    wsRef.current = ws
  }, [sessionId])

  useEffect(() => {
    connect()
    return () => {
      wsRef.current?.close()
    }
  }, [connect])

  const sendMessage = useCallback((content: string, displayText?: string) => {
    // Always show the user message immediately (displayText shown in chat; content sent to LLM)
    setMessages(prev => [
      ...prev,
      { id: `user-${Date.now()}`, role: 'user', content: displayText ?? content, timestamp: new Date() },
    ])

    if (isProcessingRef.current) {
      // Queue the message — it will be sent automatically when current response finishes
      queueRef.current.push(content)
      return
    }

    // Add loading assistant placeholder and send
    setMessages(prev => [
      ...prev,
      { id: `loading-${Date.now()}`, role: 'assistant', content: '', isLoading: true, timestamp: new Date() },
    ])

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'message', content, session_id: sessionId, client_id: selectedClientId }))
    } else {
      pendingMessageRef.current = content
      connect()
    }
  }, [sessionId, connect])

  const resetChat = useCallback(() => {
    setMessages([])
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'reset', session_id: sessionId }))
    }
  }, [sessionId])

  return {
    messages,
    isConnected,
    isProcessing,
    activeAgent,
    sendMessage,
    resetChat,
  }
}
