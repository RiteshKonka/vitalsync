export type AgentStatus = 'idle' | 'running' | 'done'

export interface InsightMessage {
  domain: string
  summary: string
}

export interface StreamEvent {
  event: string
  payload: any
}
