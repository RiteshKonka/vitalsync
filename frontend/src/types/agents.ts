export type AgentName =
  | 'supervisor' | 'sleep' | 'activity' | 'nutrition'
  | 'stress' | 'weather' | 'correlator' | 'coach'

export type AgentStatus = 'idle' | 'running' | 'done' | 'skipped' | 'retrying'

export type StreamEventType =
  | 'processing' | 'agent_start' | 'agent_thought' | 'agent_done'
  | 'tool_call' | 'tool_result' | 'a2a_message' | 'correlation'
  | 'final_answer' | 'done' | 'error'

export interface StreamEvent {
  type:      StreamEventType
  agent:     AgentName
  content:   string
  metadata:  Record<string, unknown>
  timestamp: string
}

export interface InsightMessage {
  agent:       AgentName
  domain:      string
  summary:     string
  key_metrics: Record<string, number>
  anomalies:   string[]
  confidence:  number
}

export interface CorrelationResult {
  pattern_title:           string
  causal_chain:            string[]
  involved_domains:        AgentName[]
  supporting_metrics:      Record<string, Record<string, number>>
  confidence:              number
  alternative_hypotheses:  string[]
}

export interface CoachResponse {
  headline:      string
  explanation:   string
  action_items:  string[]
  domains_cited: AgentName[]
  correlation?:  CorrelationResult
}

export interface AgentState {
  name:       AgentName
  status:     AgentStatus
  thoughts:   string[]
  insight?:   InsightMessage
  confidence: number
  color:      string
  label:      string
}

export interface QueryHistoryEntry {
  query:     string
  timestamp: number
  response:  CoachResponse
}