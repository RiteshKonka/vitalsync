import { useAgentStore } from '../store/agentStore'
import InsightCard from '../components/InsightCard'

interface Props { onBack: () => void }

export default function History({ onBack }: Props) {
  const history = useAgentStore(s => s.history)

  return (
    <div style={{ padding: '24px 28px', maxWidth: 780, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
        <button onClick={onBack} style={{
          background: 'none', border: '0.5px solid #2a2d3a',
          borderRadius: 8, padding: '5px 12px', color: '#8a8d9e',
          fontSize: 12, cursor: 'pointer',
        }}>
          ← Back
        </button>
        <span style={{ fontSize: 16, fontWeight: 500, color: '#e8eaf0' }}>
          Query History
        </span>
        <span style={{ fontSize: 12, color: '#555' }}>
          {history.length} {history.length === 1 ? 'insight' : 'insights'}
        </span>
      </div>

      {history.length === 0 ? (
        <div style={{
          textAlign: 'center', padding: '60px 20px',
          color: '#555', fontSize: 13,
        }}>
          No queries yet — ask VitalSync a health question to see insights here.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {history.map((entry, i) => (
            <InsightCard
              key={i}
              response={entry.response}
              query={entry.query}
              timestamp={entry.timestamp}
            />
          ))}
        </div>
      )}
    </div>
  )
}