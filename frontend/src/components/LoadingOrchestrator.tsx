import { useAgentStore } from '../store/agentStore'
import { agentColor } from '../lib/colors'
import type { AgentName } from '../types/agents'

const DOMAIN_AGENTS: AgentName[] = ['sleep', 'activity', 'nutrition', 'stress', 'weather']

const POSITIONS: Record<AgentName, { x: number; y: number }> = {
  sleep:      { x: 50,  y: 15  },
  activity:   { x: 82,  y: 38  },
  nutrition:  { x: 72,  y: 75  },
  stress:     { x: 28,  y: 75  },
  weather:    { x: 18,  y: 38  },
  correlator: { x: 50,  y: 47  },
  coach:      { x: 50,  y: 47  },
  supervisor: { x: 50,  y: 47  },
}

function AgentNode({ name }: { name: AgentName }) {
  const agent  = useAgentStore(s => s.agents[name])
  const color  = agentColor(name)
  const pos    = POSITIONS[name]
  const status = agent?.status ?? 'idle'

  const glowing  = status === 'running' || status === 'retrying'
  const done     = status === 'done'
  const skipped  = status === 'skipped'

  return (
    <g transform={`translate(${pos.x}%,${pos.y}%)`} style={{ transition: 'all .3s' }}>
      {/* Glow ring */}
      {glowing && (
        <circle r="14" fill="none" stroke={color} strokeWidth="1"
          opacity="0.35" style={{ animation: 'ring 1.2s infinite' }} />
      )}
      {/* Main circle */}
      <circle
        r="10"
        fill={done ? color + '33' : skipped ? '#1e2030' : '#13151f'}
        stroke={skipped ? '#2a2d3a' : color}
        strokeWidth={glowing ? 1.5 : 0.75}
        opacity={skipped ? 0.3 : 1}
        style={{ transition: 'all .3s' }}
      />
      {/* Label */}
      <text
        textAnchor="middle" dominantBaseline="middle"
        fontSize="5" fontWeight="500"
        fill={skipped ? '#3a3d4a' : color}
        style={{ userSelect: 'none' }}
      >
        {name.slice(0, 3).toUpperCase()}
      </text>
      {/* Confidence dot when done */}
      {done && agent?.confidence > 0 && (
        <text
          x="0" y="16"
          textAnchor="middle"
          fontSize="4" fill={color} opacity={0.8}
        >
          {Math.round(agent.confidence * 100)}%
        </text>
      )}
    </g>
  )
}

function CenterNode() {
  const correlation = useAgentStore(s => s.correlation)
  const coachResp   = useAgentStore(s => s.coachResponse)
  const isRunning   = useAgentStore(s => s.isRunning)

  const active = isRunning && !coachResp
  const color  = coachResp ? '#0F6E56' : correlation ? '#993C1D' : '#7F77DD'
  const label  = coachResp ? 'DONE' : correlation ? 'CORR' : 'ORCH'

  return (
    <g transform="translate(50%,50%)">
      {active && (
        <circle r="18" fill="none" stroke={color} strokeWidth="0.75"
          opacity="0.2" strokeDasharray="4 3"
          style={{ animation: 'spin 4s linear infinite' }}
        />
      )}
      <circle
        r="13"
        fill={coachResp ? '#0F6E5622' : '#13151f'}
        stroke={color}
        strokeWidth={active ? 1.5 : 0.75}
        style={{ transition: 'all .4s' }}
      />
      <text
        textAnchor="middle" dominantBaseline="middle"
        fontSize="4.5" fontWeight="600" fill={color}
        style={{ userSelect: 'none' }}
      >
        {label}
      </text>
    </g>
  )
}

function ConnectionLines() {
  const agents = useAgentStore(s => s.agents)
  const CENTER = { x: 50, y: 50 }

  return (
    <>
      {DOMAIN_AGENTS.map(name => {
        const pos    = POSITIONS[name]
        const status = agents[name]?.status ?? 'idle'
        const color  = agentColor(name)
        const active = status === 'running' || status === 'done'

        return (
          <line key={name}
            x1={`${pos.x}%`} y1={`${pos.y}%`}
            x2={`${CENTER.x}%`} y2={`${CENTER.y}%`}
            stroke={active ? color : '#1e2030'}
            strokeWidth={active ? 0.75 : 0.5}
            strokeDasharray={status === 'done' ? 'none' : '3 3'}
            opacity={active ? 0.6 : 0.3}
            style={{ transition: 'all .4s' }}
          />
        )
      })}
    </>
  )
}

export default function LoadingOrchestrator() {
  const isRunning   = useAgentStore(s => s.isRunning)
  const coachResp   = useAgentStore(s => s.coachResponse)
  const streamEvents = useAgentStore(s => s.streamEvents)

  const lastEvent = streamEvents[streamEvents.length - 1]
  const statusText = coachResp
    ? 'Analysis complete'
    : lastEvent
      ? `${lastEvent.agent} — ${lastEvent.content.slice(0, 50)}`
      : isRunning ? 'Activating agents…' : 'Ready'

  return (
    <div style={{
      background: '#13151f', border: '0.5px solid #1e2030',
      borderRadius: 14, padding: '16px',
      display: 'flex', flexDirection: 'column', gap: 12,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ fontSize: 13, fontWeight: 500, color: '#e8eaf0' }}>
          Orchestrator
        </span>
        {isRunning && !coachResp && (
          <span style={{
            fontSize: 11, padding: '2px 8px', borderRadius: 99,
            background: '#BA751720', color: '#BA7517',
            border: '0.5px solid #BA751740',
          }}>live</span>
        )}
      </div>

      <style>{`
        @keyframes ring { 0%,100%{r:14;opacity:.35} 50%{r:18;opacity:.1} }
        @keyframes spin  { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
      `}</style>

      {/* SVG diagram */}
      <svg
        viewBox="0 0 100 100"
        style={{ width: '100%', height: 180, display: 'block' }}
        overflow="visible"
      >
        <ConnectionLines />
        {DOMAIN_AGENTS.map(name => <AgentNode key={name} name={name} />)}
        <CenterNode />
      </svg>

      {/* Status bar */}
      <div style={{
        fontSize: 11, color: '#555',
        padding: '6px 10px',
        background: '#0a0b10',
        borderRadius: 6,
        fontFamily: 'monospace',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
      }}>
        {statusText}
      </div>
    </div>
  )
}