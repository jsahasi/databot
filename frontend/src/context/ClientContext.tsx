import { createContext, useContext, useState, ReactNode } from 'react'

const DEFAULT_CLIENT_ID = 10710

interface ClientContextValue {
  selectedClientId: number
  setSelectedClientId: (id: number) => void
}

const ClientContext = createContext<ClientContextValue>({
  selectedClientId: DEFAULT_CLIENT_ID,
  setSelectedClientId: () => {},
})

export function ClientProvider({ children }: { children: ReactNode }) {
  const [selectedClientId, setSelectedClientId] = useState(DEFAULT_CLIENT_ID)
  return (
    <ClientContext.Provider value={{ selectedClientId, setSelectedClientId }}>
      {children}
    </ClientContext.Provider>
  )
}

export function useClientContext(): ClientContextValue {
  return useContext(ClientContext)
}
