import DomainBadge from './DomainBadge'
import { confidenceColor } from '../lib/colors'
import type { CoachResponse } from '../types/agents'

interface Props {
  response:  CoachResponse
  query:     string
  timestamp: number
  compact?:  boolean
}

export default function InsightCard({ response, query, timestamp, compact }: Props) {
  const date = new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

  return (
    <div style={{
      background: '#13151f', border: '0.5px solid #1e2030',
      borderRadius: 12, overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{ padding: '10px 14px', borderBottom: '0.5px solid #1e2030', display: 'flex', alignItems: 'flex-start', gap: 8 }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 11, color: '#555', marginBottom: 3 }}>{date} — you asked</div>
          <div style={{ fontSize: 13, color: '#8a8d9e', fontStyle: 'italic' }}>"{query}"</div>
        </div>
        {response.correlation && (
          <span style={{
            fontSize: 10, padding: '2px 8px', borderRadius: 99, whiteSpace: 'nowrap',
            background: '#7F77DD22', color: '#7F77DD', border: '0.5px solid #7F77DD44',
          }}>
            {Math.round(response.correlation.confidence * 100)}% conf
          </span>
        )}
      </div>

      {/* Headline */}
      <div style={{ padding: '12px 14px', borderBottom: compact ? 'none' : '0.5px solid #1e2030' }}>
        <div style={{ fontSize: 14, fontWeight: 500, color: '#e8eaf0', lineHeight: 1.5, marginBottom: 8 }}>
          {response.headline}
        </div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {response.domains_cited.map(d => <DomainBadge key={d} agent={d} />)}
        </div>
      </div>

      {!compact && (
        <>
          {/* Explanation */}
          <div style={{ padding: '10px 14px', borderBottom: '0.5px solid #1e2030' }}>
            <div style={{ fontSize: 12, color: '#8a8d9e', lineHeight: 1.7 }}>
              {response.explanation}
            </div>
          </div>

          {/* Action items */}
          {response.action_items.length > 0 && (
            <div style={{ padding: '10px 14px' }}>
              <div style={{ fontSize: 11, fontWeight: 500, color: '#1D9E75', textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: 8 }}>
                Actions
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {response.action_items.map((a, i) => (
                  <div key={i} style={{ display: 'flex', gap: 8, fontSize: 13, color: '#b0b3c0' }}>
                    <span style={{ color: '#1D9E75', flexShrink: 0 }}>→</span>
                    <span>{a}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Causal chain */}
          {(response.correlation?.causal_chain?.length ?? 0) > 0 && (
            <div style={{ padding: '10px 14px', borderTop: '0.5px solid #1e2030', background: '#0a0b10' }}>
              <div style={{ fontSize: 11, fontWeight: 500, color: '#555', textTransform: 'uppercase', letterSpacing: '.05em', marginBottom: 8 }}>
                Causal chain
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {(response.correlation?.causal_chain ?? []).map((step, i) => (
                  <div key={i} style={{ display: 'flex', gap: 8, fontSize: 12, color: '#6a6d80' }}>
                    <span style={{ color: '#993C1D', flexShrink: 0, minWidth: 14 }}>{i + 1}.</span>
                    <span>{step}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}