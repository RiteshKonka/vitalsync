import type { StreamEvent } from '../types/agents'

type Handler = (event: StreamEvent | { type: 'done'; session_id: string } | { type: 'error'; message: string } | { type: 'processing'; content: string }) => void

class WsClient {
  private ws: WebSocket | null = null
  private handlers: Set<Handler> = new Set()
  private url = `ws://${window.location.hostname}:8000/ws`

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws?.readyState === WebSocket.OPEN) { resolve(); return }
      this.ws = new WebSocket(this.url)
      this.ws.onopen    = () => resolve()
      this.ws.onerror   = () => reject(new Error('WebSocket connection failed'))
      this.ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data)
          this.handlers.forEach(h => h(msg))
        } catch { /* ignore malformed frames */ }
      }
      this.ws.onclose = () => { this.ws = null }
    })
  }

  send(sessionId: string, query: string) {
    if (this.ws?.readyState !== WebSocket.OPEN)
      throw new Error('WebSocket not connected')
    this.ws.send(JSON.stringify({ type: 'query', session_id: sessionId, query }))
  }

  subscribe(handler: Handler): () => void {
    this.handlers.add(handler)
    return () => this.handlers.delete(handler)
  }

  disconnect() {
    this.ws?.close()
    this.ws = null
  }

  get isConnected() {
    return this.ws?.readyState === WebSocket.OPEN
  }
}

export const wsClient = new WsClient()