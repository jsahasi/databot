import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

// Sentinel: 0 means "use server root" — resolved on first /api/hierarchy fetch
const UNRESOLVED_CLIENT_ID = 0

interface ClientProperties {
  [propCode: string]: { value: string | null; label: string | null }
}

interface ClientContextValue {
  selectedClientId: number
  setSelectedClientId: (id: number) => void
  clientProperties: ClientProperties
  clientPropertiesLoading: boolean
}

const ClientContext = createContext<ClientContextValue>({
  selectedClientId: UNRESOLVED_CLIENT_ID,
  setSelectedClientId: () => {},
  clientProperties: {},
  clientPropertiesLoading: false,
})

export function ClientProvider({ children }: { children: ReactNode }) {
  const [selectedClientId, setSelectedClientId] = useState(UNRESOLVED_CLIENT_ID)
  const [clientProperties, setClientProperties] = useState<ClientProperties>({})
  const [clientPropertiesLoading, setClientPropertiesLoading] = useState(false)

  // Resolve the true root client_id from the server on mount — avoids hardcoding
  // tenant IDs in the frontend bundle (security: A02, information disclosure).
  useEffect(() => {
    if (selectedClientId !== UNRESOLVED_CLIENT_ID) return
    fetch('/api/hierarchy')
      .then(r => r.json())
      .then(data => {
        if (data?.root_client_id) setSelectedClientId(data.root_client_id)
      })
      .catch(() => {/* keep sentinel — backend will use config root */})
  }, [])

  // Fetch client properties when client_id resolves or changes
  useEffect(() => {
    if (selectedClientId === UNRESOLVED_CLIENT_ID) return
    setClientPropertiesLoading(true)
    fetch(`/api/client-properties?client_id=${selectedClientId}`)
      .then(r => r.json())
      .then(data => {
        if (data?.properties) setClientProperties(data.properties)
      })
      .catch(() => setClientProperties({}))
      .finally(() => setClientPropertiesLoading(false))
  }, [selectedClientId])

  return (
    <ClientContext.Provider value={{ selectedClientId, setSelectedClientId, clientProperties, clientPropertiesLoading }}>
      {children}
    </ClientContext.Provider>
  )
}

export function useClientContext(): ClientContextValue {
  return useContext(ClientContext)
}
