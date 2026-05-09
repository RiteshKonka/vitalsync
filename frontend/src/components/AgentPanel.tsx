import { useAgentStore } from '../store/agentStore'
import { agentColor, confidenceColor } from '../lib/colors'
import type { AgentName } from '../types/agents'

const DOMAIN_AGENTS: AgentName[] = ['sleep', 'activity', 'nutrition', 'stress', 'weather']

function StatusDot({ status }: { status: string }) {
  const colors: Record<string, string> = {
    idle: '#2a2d3a', running: '#BA7517', done: '#1D9E75',
    skipped: '#3a3d4a', retrying: '#7F77DD',
  }
  const animated = status === 'running' || status === 'retrying'
  return (
    <span style={{
      display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
      background: colors[status] ?? '#555',
      boxShadow: animated ? `0 0 0 3px ${colors[status]}44` : 'none',
      transition: 'background .3s',
    }} />
  )
}

function AgentRow({ name }: { name: AgentName }) {
  const agent = useAgentStore(s => s.agents[name])
  if (!agent) return null
  const color = agentColor(name)

  return (
    <div style={{
      padding: '10px 14px',
      borderBottom: '0.5px solid #1e2030',
      opacity: agent.status === 'skipped' ? 0.35 : 1,
      transition: 'opacity .3s',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: agent.insight ? 6 : 0 }}>
        <StatusDot status={agent.status} />
        <span style={{ fontSize: 13, fontWeight: 500, color }}>{agent.label}</span>
        {agent.status === 'done' && agent.confidence > 0 && (
          <span style={{
            marginLeft: 'auto', fontSize: 11,
            color: confidenceColor(agent.confidence),
          }}>
            {Math.round(agent.confidence * 100)}% conf
          </span>
        )}
        {agent.status === 'running' && (
          <span style={{ marginLeft: 'auto', fontSize: 11, color: '#BA7517' }}>analyzing…</span>
        )}
      </div>

      {agent.insight && (
        <div style={{
          marginLeft: 16, fontSize: 12, color: '#8a8d9e', lineHeight: 1.5,
        }}>
          <div style={{ color: '#b0b3c0', marginBottom: 4 }}>{agent.insight.summary}</div>
          {agent.insight.anomalies.slice(0, 2).map((a, i) => (
            <div key={i} style={{ color: color + 'cc', fontSize: 11 }}>↳ {a}</div>
          ))}
        </div>
      )}
    </div>
  )
}

function CorrelationBlock() {
  const correlation = useAgentStore(s => s.correlation)
  if (!correlation) return null

  return (
    <div style={{
      margin: 12, padding: 12,
      background: '#993C1D18', border: '0.5px solid #993C1D55',
      borderRadius: 10,
    }}>
      <div style={{ fontSize: 11, fontWeight: 500, color: '#993C1D', marginBottom: 6 }}>
        PATTERN FOUND
      </div>
      <div style={{ fontSize: 13, fontWeight: 500, color: '#e8eaf0', marginBottom: 8 }}>
        {correlation.pattern_title}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        {correlation.causal_chain.slice(0, 4).map((step, i) => (
          <div key={i} style={{ fontSize: 12, color: '#9a9db0', display: 'flex', gap: 6 }}>
            <span style={{ color: '#993C1D', flexShrink: 0 }}>{i + 1}.</span>
            <span>{step}</span>
          </div>
        ))}
      </div>
      <div style={{ marginTop: 8, fontSize: 11, color: confidenceColor(correlation.confidence) }}>
        Confidence: {Math.round(correlation.confidence * 100)}%
      </div>
    </div>
  )
}

export default function AgentPanel() {
  const isRunning  = useAgentStore(s => s.isRunning)
  const coachResp  = useAgentStore(s => s.coachResponse)
  const events     = useAgentStore(s => s.streamEvents)
  const a2aCount   = events.filter(e => e.type === 'a2a_message').length

  return (
    <div style={{
      background: '#13151f', border: '0.5px solid #1e2030',
      borderRadius: 14, overflow: 'hidden',
      display: 'flex', flexDirection: 'column', height: '100%',
    }}>
      <div style={{
        padding: '12px 14px', borderBottom: '0.5px solid #1e2030',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <span style={{ fontSize: 13, fontWeight: 500, color: '#e8eaf0' }}>Agents</span>
        {isRunning && (
          <span style={{
            fontSize: 11, padding: '2px 8px', borderRadius: 99,
            background: '#BA751722', color: '#BA7517',
            border: '0.5px solid #BA751744',
          }}>live</span>
        )}
        {a2aCount > 0 && (
          <span style={{ marginLeft: 'auto', fontSize: 11, color: '#555' }}>
            {a2aCount} A2A messages
          </span>
        )}
      </div>

      <div style={{ flex: 1, overflowY: 'auto' }}>
        {DOMAIN_AGENTS.map(name => <AgentRow key={name} name={name} />)}
        <CorrelationBlock />

        {coachResp && (
          <div style={{ margin: 12, padding: 12, background: '#0F6E5618', border: '0.5px solid #0F6E5655', borderRadius: 10 }}>
            <div style={{ fontSize: 11, fontWeight: 500, color: '#1D9E75', marginBottom: 6 }}>COACH</div>
            <div style={{ fontSize: 13, color: '#e8eaf0', lineHeight: 1.6, marginBottom: 8 }}>
              {coachResp.headline}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {coachResp.action_items.map((a, i) => (
                <div key={i} style={{ fontSize: 12, color: '#9a9db0', display: 'flex', gap: 6 }}>
                  <span style={{ color: '#1D9E75' }}>→</span><span>{a}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}