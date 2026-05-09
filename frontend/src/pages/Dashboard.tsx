import { useState, useEffect } from 'react'
import { useAgentStream }      from '../hooks/useAgentStreams'
import { useHealthData }       from '../hooks/useHealthData'
import { useAgentStore }       from '../store/agentStore'
import { api }                 from '../lib/api'

import ChatBar              from '../components/ChatBar'
import AgentPanel           from '../components/AgentPanel'
import Timeline             from '../components/Timeline'
import CoachResponse        from '../components/CoachResponse'
import LoadingOrchestrator  from '../components/LoadingOrchestrator'
import History              from './History'

export default function Dashboard() {
  const { sendQuery }  = useAgentStream()
  const { loading }    = useHealthData()
  const isRunning      = useAgentStore(s => s.isRunning)
  const history        = useAgentStore(s => s.history)

  const [page,      setPage]      = useState<'dashboard' | 'history'>('dashboard')
  const [backStatus, setBackend]  = useState<'checking' | 'ok' | 'offline'>('checking')

  // Check backend health on mount
  useEffect(() => {
    api.health().then(r => setBackend(r.status === 'ok' ? 'ok' : 'offline'))
  }, [])

  if (page === 'history') {
    return <History onBack={() => setPage('dashboard')} />
  }

  return (
    <div style={{ minHeight: '100vh', background: '#0f1117', padding: '20px 24px' }}>

      {/* Top bar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12,
        marginBottom: 20,
      }}>
        <div>
          <span style={{ fontSize: 17, fontWeight: 600, color: '#e8eaf0' }}>VitalSync</span>
          <span style={{ fontSize: 11, color: '#555', marginLeft: 8 }}>
            multi-agent health intelligence
          </span>
        </div>

        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 10 }}>
          {/* Backend status pill */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 5,
            fontSize: 11, padding: '3px 10px', borderRadius: 99,
            background: backStatus === 'ok' ? '#1D9E7520' : backStatus === 'offline' ? '#D85A3020' : '#2a2d3a',
            color: backStatus === 'ok' ? '#1D9E75' : backStatus === 'offline' ? '#D85A30' : '#555',
            border: `0.5px solid ${backStatus === 'ok' ? '#1D9E7540' : backStatus === 'offline' ? '#D85A3040' : '#3a3d4a'}`,
          }}>
            <span style={{
              width: 5, height: 5, borderRadius: '50%', background: 'currentColor',
              display: 'inline-block',
            }} />
            {backStatus === 'checking' ? 'connecting…' : backStatus === 'ok' ? 'backend online' : 'backend offline'}
          </div>

          {/* History button */}
          {history.length > 0 && (
            <button onClick={() => setPage('history')} style={{
              fontSize: 12, padding: '4px 12px', borderRadius: 8,
              background: 'none', border: '0.5px solid #2a2d3a',
              color: '#8a8d9e', cursor: 'pointer',
            }}>
              History ({history.length})
            </button>
          )}
        </div>
      </div>

      {backStatus === 'offline' && (
        <div style={{
          marginBottom: 16, padding: '10px 16px', borderRadius: 10,
          background: '#D85A3015', border: '0.5px solid #D85A3040',
          fontSize: 12, color: '#D07050',
        }}>
          ⚠ Backend is offline. Start it with:{' '}
          <code style={{ background: '#1a1d2b', padding: '1px 6px', borderRadius: 4 }}>
            cd backend && uvicorn main:app --reload --port 8000
          </code>
        </div>
      )}

      {/* Main grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 320px',
        gridTemplateRows: 'auto auto 1fr',
        gap: 14,
        minHeight: 'calc(100vh - 120px)',
      }}>

        {/* Timeline — top left */}
        <div style={{ gridColumn: '1', gridRow: '1' }}>
          <Timeline />
        </div>

        {/* Orchestrator diagram — top right */}
        <div style={{ gridColumn: '2', gridRow: '1 / 3' }}>
          <LoadingOrchestrator />
        </div>

        {/* Coach response — middle left */}
        <div style={{ gridColumn: '1', gridRow: '2' }}>
          <CoachResponse />
        </div>

        {/* Agent panel — bottom right (spans remaining rows) */}
        <div style={{ gridColumn: '2', gridRow: '3' }}>
          <AgentPanel />
        </div>

        {/* Chat bar — bottom, full width */}
        <div style={{ gridColumn: '1 / 3', gridRow: '3', alignSelf: 'end' }}>
          <ChatBar onSend={sendQuery} isRunning={isRunning} />
        </div>

      </div>
    </div>
  )
}