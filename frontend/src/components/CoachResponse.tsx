import { useAgentStore } from '../store/agentStore'
import DomainBadge from './DomainBadge'

export default function CoachResponse() {
  const coachResp  = useAgentStore(s => s.coachResponse)
  const isRunning  = useAgentStore(s => s.isRunning)
  const correlation = useAgentStore(s => s.correlation)

  if (isRunning && !coachResp) {
    return (
      <div style={{
        background: '#13151f', border: '0.5px solid #1e2030',
        borderRadius: 14, padding: 20,
        display: 'flex', alignItems: 'center', gap: 12,
      }}>
        <div style={{
          width: 8, height: 8, borderRadius: '50%',
          background: '#BA7517',
          boxShadow: '0 0 0 4px #BA751730',
          animation: 'pulse 1.2s infinite',
          flexShrink: 0,
        }} />
        <span style={{ fontSize: 13, color: '#8a8d9e' }}>
          Agents are analyzing your health data…
        </span>
        <style>{`@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }`}</style>
      </div>
    )
  }

  if (!coachResp) {
    return (
      <div style={{
        background: '#13151f', border: '0.5px solid #1e2030',
        borderRadius: 14, padding: 24,
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        gap: 10, textAlign: 'center',
      }}>
        <div style={{ fontSize: 28 }}>🏃</div>
        <div style={{ fontSize: 14, fontWeight: 500, color: '#e8eaf0' }}>
          Ask a health question
        </div>
        <div style={{ fontSize: 13, color: '#555', maxWidth: 340, lineHeight: 1.6 }}>
          Five specialist agents will analyse your sleep, activity,
          nutrition, stress and weather data in parallel — then correlate
          across domains to find patterns you wouldn't see otherwise.
        </div>
      </div>
    )
  }

  return (
    <div style={{
      background: '#13151f', border: '0.5px solid #0F6E5640',
      borderRadius: 14, overflow: 'hidden',
    }}>
      {/* Headline */}
      <div style={{
        padding: '16px 18px',
        borderBottom: '0.5px solid #1e2030',
        background: '#0F6E5610',
      }}>
        <div style={{ fontSize: 11, fontWeight: 500, color: '#1D9E75', letterSpacing: '.06em', textTransform: 'uppercase', marginBottom: 8 }}>
          VitalSync Analysis
        </div>
        <div style={{ fontSize: 16, fontWeight: 500, color: '#e8eaf0', lineHeight: 1.55, marginBottom: 10 }}>
          {coachResp.headline}
        </div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {coachResp.domains_cited.map(d => (
            <DomainBadge key={d} agent={d} size="sm" />
          ))}
          {correlation && (
            <span style={{
              fontSize: 11, padding: '2px 10px', borderRadius: 99,
              background: '#993C1D22', color: '#D07050',
              border: '0.5px solid #993C1D44',
            }}>
              {Math.round(correlation.confidence * 100)}% confidence
            </span>
          )}
        </div>
      </div>

      {/* Explanation */}
      <div style={{ padding: '14px 18px', borderBottom: '0.5px solid #1e2030' }}>
        <div style={{ fontSize: 13, color: '#9a9db0', lineHeight: 1.75 }}>
          {coachResp.explanation}
        </div>
      </div>

      {/* Action items */}
      {coachResp.action_items.length > 0 && (
        <div style={{ padding: '14px 18px', borderBottom: coachResp.correlation ? '0.5px solid #1e2030' : 'none' }}>
          <div style={{ fontSize: 11, fontWeight: 500, color: '#1D9E75', textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 10 }}>
            Try these
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {coachResp.action_items.map((item, i) => (
              <div key={i} style={{
                display: 'flex', gap: 10,
                padding: '8px 12px',
                background: '#1a1d2b',
                borderRadius: 8,
                border: '0.5px solid #2a2d3a',
              }}>
                <span style={{
                  color: '#1D9E75', fontWeight: 600,
                  fontSize: 13, flexShrink: 0, marginTop: 1,
                }}>
                  {i + 1}
                </span>
                <span style={{ fontSize: 13, color: '#c0c3d0', lineHeight: 1.55 }}>
                  {item}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Causal chain */}
      {(coachResp.correlation?.causal_chain?.length ?? 0) > 0 && (
        <div style={{ padding: '14px 18px', background: '#0a0b10' }}>
          <div style={{ fontSize: 11, fontWeight: 500, color: '#555', textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 10 }}>
            How the agents connected the dots
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {(coachResp.correlation?.causal_chain ?? []).map((step, i) => (
              <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                <div style={{
                  width: 20, height: 20, borderRadius: '50%', flexShrink: 0,
                  background: '#993C1D22', border: '0.5px solid #993C1D55',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 10, color: '#993C1D', fontWeight: 600,
                }}>
                  {i + 1}
                </div>
                <span style={{ fontSize: 12, color: '#6a6d80', lineHeight: 1.6, paddingTop: 2 }}>
                  {step}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}