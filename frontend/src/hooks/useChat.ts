import { useState, useRef, useCallback, useEffect } from 'react'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  agentUsed?: string | null
  chartData?: any | null
  isLoading?: boolean
  timestamp: Date
}

interface UseChatOptions {
  sessionId?: string
}

export function useChat(options: UseChatOptions = {}) {
  const { sessionId = 'default' } = options
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [activeAgent, setActiveAgent] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const pendingMessageRef = useRef<string | null>(null)

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

        case 'message_complete':
          setIsProcessing(false)
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

  const sendMessage = useCallback((content: string) => {
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, userMessage])

    // Add loading assistant message
    setMessages(prev => [
      ...prev,
      {
        id: `loading-${Date.now()}`,
        role: 'assistant',
        content: '',
        isLoading: true,
        timestamp: new Date(),
      },
    ])

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'message',
        content,
        session_id: sessionId,
      }))
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
