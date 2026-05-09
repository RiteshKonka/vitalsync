import { create } from 'zustand'
import type { AgentName, AgentStatus, AgentState, CoachResponse, CorrelationResult, InsightMessage, StreamEvent, QueryHistoryEntry } from '../types/agents'
import { DOMAIN_COLORS, DOMAIN_LABELS } from '../lib/colors'

const AGENT_NAMES: AgentName[] = ['sleep', 'activity', 'nutrition', 'stress', 'weather', 'correlator', 'coach']

function makeAgents(): Record<AgentName, AgentState> {
  return Object.fromEntries(
    AGENT_NAMES.map(name => [name, {
      name, status: 'idle' as AgentStatus,
      thoughts: [], confidence: 0,
      color: DOMAIN_COLORS[name] ?? '#888',
      label: DOMAIN_LABELS[name] ?? name,
    }])
  ) as unknown as Record<AgentName, AgentState>
}

interface AgentStore {
  agents:        Record<AgentName, AgentState>
  streamEvents:  StreamEvent[]
  correlation:   CorrelationResult | null
  coachResponse: CoachResponse | null
  isRunning:     boolean
  history:       QueryHistoryEntry[]

  handleEvent:   (raw: unknown) => void
  reset:         () => void
  addHistory:    (entry: QueryHistoryEntry) => void
}

export const useAgentStore = create<AgentStore>((set, get) => ({
  agents:        makeAgents(),
  streamEvents:  [],
  correlation:   null,
  coachResponse: null,
  isRunning:     false,
  history:       [],

  reset() {
    set({
      agents: makeAgents(),
      streamEvents: [],
      correlation: null,
      coachResponse: null,
      isRunning: true,
    })
  },

  handleEvent(raw: unknown) {
    const msg = raw as Record<string, unknown>
    const type    = msg.type    as string
    const agent   = msg.agent   as AgentName | undefined
    const content = (msg.content as string) ?? ''
    const meta    = (msg.metadata as Record<string, unknown>) ?? {}

    set(state => {
      const agents = { ...state.agents }
      const events = [...state.streamEvents]

      // Append to stream log
      if (type !== 'done' && type !== 'processing') {
        events.push(msg as unknown as StreamEvent)
      }

      // Update agent state
      if (agent && agents[agent]) {
        const a = { ...agents[agent] }

        if (type === 'agent_start')   a.status = 'running'
        if (type === 'agent_done')    { a.status = 'done'; a.confidence = (meta.confidence as number) ?? 0 }
        if (type === 'agent_thought') a.thoughts = [...a.thoughts, content]

        if (type === 'a2a_message') {
          a.insight = {
            agent: agent,
            domain: agent,
            summary: content,
            key_metrics: (meta.key_metrics as Record<string, number>) ?? {},
            anomalies:   (meta.anomalies   as string[]) ?? [],
            confidence:  (meta.confidence  as number)  ?? 0,
          } as InsightMessage
          a.confidence = (meta.confidence as number) ?? 0
        }

        agents[agent] = a
      }

      // Correlation result
      if (type === 'correlation') {
        return {
          ...state, agents, streamEvents: events,
          correlation: {
            pattern_title:           content,
            causal_chain:            (meta.causal_chain            as string[]) ?? [],
            involved_domains:        (meta.involved_domains        as AgentName[]) ?? [],
            supporting_metrics:      (meta.supporting_metrics      as Record<string, Record<string, number>>) ?? {},
            confidence:              (meta.confidence              as number) ?? 0,
            alternative_hypotheses:  (meta.alternative_hypotheses  as string[]) ?? [],
          }
        }
      }

      // Final answer
      if (type === 'final_answer') {
        return {
          ...state, agents, streamEvents: events,
          coachResponse: {
            headline:      content,
            explanation:   (meta.explanation   as string)   ?? '',
            action_items:  (meta.action_items  as string[]) ?? [],
            domains_cited: (meta.domains_cited as AgentName[]) ?? [],
          }
        }
      }

      // Done
      if (type === 'done') {
        const coach = state.coachResponse
        if (coach) {
          const entry: QueryHistoryEntry = {
            query: '',
            timestamp: Date.now(),
            response: coach,
          }
          return { ...state, agents, streamEvents: events, isRunning: false, history: [entry, ...state.history] }
        }
        return { ...state, agents, streamEvents: events, isRunning: false }
      }

      return { ...state, agents, streamEvents: events }
    })
  },

  addHistory(entry) {
    set(s => ({ history: [entry, ...s.history] }))
  },
}))