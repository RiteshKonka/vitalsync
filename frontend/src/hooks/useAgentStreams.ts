import { useCallback, useRef } from 'react'
import { wsClient } from '../lib/wsClient'
import { useAgentStore } from '../store/agentStore'
import { api } from '../lib/api'
import { v4 as uuidv4 } from 'uuid'

const SESSION_KEY = 'vitalsync_session_id'

function getSessionId(): string {
  let sid = localStorage.getItem(SESSION_KEY)
  if (!sid) { sid = uuidv4(); localStorage.setItem(SESSION_KEY, sid) }
  return sid
}

export function useAgentStream() {
  const { reset, handleEvent, addHistory } = useAgentStore()
  const queryRef = useRef('')

  const sendQuery = useCallback(async (query: string) => {
    if (!query.trim()) return
    queryRef.current = query
    reset()

    const sid = getSessionId()
    await api.initSession(sid).catch(() => {})

    // Connect if needed
    if (!wsClient.isConnected) {
      await wsClient.connect()
    }

    // Subscribe to events
    const unsub = wsClient.subscribe((raw) => {
      const msg = raw as Record<string, unknown>
      handleEvent(msg)

      // When done, stamp the query into the last history entry
      if (msg.type === 'done') {
        useAgentStore.setState(s => {
          if (s.history.length === 0) return s
          const [first, ...rest] = s.history
          return { history: [{ ...first, query }, ...rest] }
        })
        unsub()
      }
    })

    wsClient.send(sid, query)
  }, [reset, handleEvent])

  return { sendQuery }
}