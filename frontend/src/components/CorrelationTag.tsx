import { agentColor } from '../lib/colors'
import type { AgentName } from '../types/agents'

interface Props {
  domains:    AgentName[]
  confidence: number
  title:      string
}

export default function CorrelationTag({ domains, confidence, title }: Props) {
  return (
    <div style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      padding: '4px 10px', borderRadius: 99,
      background: '#993C1D18', border: '0.5px solid #993C1D44',
    }}>
      {/* Coloured domain dots */}
      <div style={{ display: 'flex', gap: 3 }}>
        {domains.slice(0, 4).map(d => (
          <span key={d} style={{
            width: 7, height: 7, borderRadius: '50%',
            background: agentColor(d),
            display: 'inline-block',
          }} />
        ))}
      </div>
      <span style={{ fontSize: 11, color: '#D07050' }}>{title}</span>
      <span style={{
        fontSize: 10, padding: '1px 6px', borderRadius: 99,
        background: '#993C1D33', color: '#E08060',
      }}>
        {Math.round(confidence * 100)}%
      </span>
    </div>
  )
}