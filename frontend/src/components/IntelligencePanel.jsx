import { PRISM_STATE_CONFIG as PHASE_CONFIG } from '../config/prismState'

const ACTION_LABELS = {
  ASK_CLARIFICATION:   'Asking for information',
  CONFIRM_INFORMATION: 'Confirming details',
  VERIFY_TRANSACTION:  'Verifying transaction',
  CHECK_ORDER:         'Checking order status',
  RESOLVE_CASE:        'Resolving case',
  ESCALATE_TO_HUMAN:   'Escalating to specialist',
  UNDERSTAND_REQUEST:  'Understanding request',
  NO_ACTION:           'Processing',
}

const PIPELINE = ['LISTENING', 'UNDERSTANDING', 'THINKING', 'ACTING', 'SPEAKING', 'ESCALATING']

const TIMELINE_STEPS = [
  { label: 'User intent detected',    states: ['LISTENING', 'UNDERSTANDING'] },
  { label: 'Context extracted',        states: ['UNDERSTANDING', 'THINKING'] },
  { label: 'Action identified',        states: ['THINKING', 'ACTING'] },
  { label: 'Verification',             states: ['ACTING'] },
  { label: 'Resolution / Escalation', states: ['SPEAKING', 'ESCALATING', 'HUMAN_CONNECTED'] },
]

function voiceStateToStepIndex(voiceState) {
  switch (voiceState) {
    case 'LISTENING':
    case 'UNDERSTANDING':    return 0
    case 'THINKING':         return 2
    case 'ACTING':           return 3
    case 'SPEAKING':         return 4
    case 'ESCALATING':
    case 'HUMAN_CONNECTED':  return 4
    default:                 return -1 // IDLE / CONNECTING / ERROR
  }
}

export default function IntelligencePanel({ voiceState = 'IDLE', aiState = null, compact = false }) {
  const cfg = PHASE_CONFIG[voiceState] || PHASE_CONFIG.IDLE
  const sc = voiceState === 'ESCALATING' || voiceState === 'ERROR' ? 'var(--danger)'
           : voiceState === 'HUMAN_CONNECTED' ? 'var(--ok)'
           : voiceState === 'ACTING' ? 'var(--warn)'
           : 'var(--text-primary)'

  const activeStepIdx = voiceStateToStepIndex(voiceState)
  // For ESCALATING / HUMAN_CONNECTED, all steps are done
  const allDone = voiceState === 'ESCALATING' || voiceState === 'HUMAN_CONNECTED'

  if (compact) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8, padding: '7px 12px',
        background: voiceState === 'ESCALATING' ? 'var(--danger-bg)' : voiceState === 'HUMAN_CONNECTED' ? 'var(--ok-bg)' : 'var(--surface-1)',
        border: `1px solid ${voiceState === 'ESCALATING' ? 'var(--danger-border)' : voiceState === 'HUMAN_CONNECTED' ? 'var(--ok-border)' : 'var(--border)'}`,
        borderRadius: 'var(--r-md)',
      }}>
        <span style={{ width: 7, height: 7, borderRadius: '50%', display: 'inline-block', background: sc, flexShrink: 0 }} />
        <span className="t-label" style={{ color: sc, fontSize: 10 }}>PRISM INTELLIGENCE</span>
        <span style={{ fontSize: 11, fontWeight: 600, color: sc }}>{cfg.label}</span>
        {aiState?.intent && <span style={{ fontSize: 11, color: 'var(--text-tertiary)', marginLeft: 2 }}>— {aiState.intent.replace(/_/g, ' ')}</span>}
        {aiState?.confidence != null && <span style={{ marginLeft: 'auto', fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{aiState.confidence}%</span>}
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflowY: 'auto' }}>
      {/* Header */}
      <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border-subtle)', background: 'var(--surface-1)', flexShrink: 0 }}>
        <div className="t-label-sm" style={{ marginBottom: 8 }}>PRISM INTELLIGENCE</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 13 }}>{cfg.icon}</span>
          <span key={voiceState} className="d-state state-label" style={{ color: sc }}>{cfg.label}</span>
          <span style={{ marginLeft: 'auto', width: 7, height: 7, borderRadius: '50%', background: sc, flexShrink: 0 }} />
        </div>
      </div>

      {/* Timeline + aiState data */}
      <div style={{ padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 18, flex: 1 }}>

        {/* Execution Timeline */}
        <div>
          <div className="t-label" style={{ color: 'var(--text-muted)', marginBottom: 10 }}>Execution Pipeline</div>
          <div className="intelligence-timeline">
            {TIMELINE_STEPS.map((step, idx) => {
              const isDone   = allDone ? true : idx < activeStepIdx
              const isActive = !allDone && idx === activeStepIdx
              const dotClass = isDone ? 'timeline-dot--done' : isActive ? 'timeline-dot--active' : 'timeline-dot--pending'
              const connClass = isDone ? 'timeline-connector--done' : 'timeline-connector--pending'
              return (
                <div key={idx}>
                  <div className="timeline-step">
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 8 }}>
                      <div className={`timeline-dot ${dotClass}`} />
                      {idx < TIMELINE_STEPS.length - 1 && (
                        <div className={`timeline-connector ${connClass}`} />
                      )}
                    </div>
                    <div style={{ paddingBottom: idx < TIMELINE_STEPS.length - 1 ? 14 : 0, paddingLeft: 2 }}>
                      <span style={{
                        fontSize: 12.5,
                        fontWeight: isActive ? 600 : 400,
                        color: isActive ? 'var(--text-primary)' : isDone ? 'var(--text-muted)' : 'var(--text-tertiary)',
                        transition: 'color 0.2s ease',
                      }}>
                        {step.label}
                      </span>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* aiState data */}
        {aiState && (<>
          {(aiState.intent || aiState.language?.length > 0) && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
              {aiState.intent && (
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span className="t-label" style={{ color: 'var(--text-muted)' }}>Intent</span>
                  <span style={{ fontSize: 12.5, fontWeight: 500 }}>
                    {aiState.intent.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                  </span>
                </div>
              )}
              {aiState.language?.length > 0 && (
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span className="t-label" style={{ color: 'var(--text-muted)' }}>Language</span>
                  <span style={{ fontSize: 12.5, fontWeight: 500 }}>{aiState.language.join(' + ')}</span>
                </div>
              )}
            </div>
          )}

          {aiState.confidence != null && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 8 }}>
                <span className="t-label" style={{ color: 'var(--text-muted)' }}>Confidence</span>
                <span style={{
                  fontSize: 20, fontWeight: 700, letterSpacing: '-0.03em',
                  color: aiState.confidence >= 70 ? 'var(--ok)' : aiState.confidence >= 40 ? 'var(--warn)' : 'var(--danger)',
                }}>
                  {aiState.confidence}%
                </span>
              </div>
              <div className="progress">
                <div className="progress__fill" style={{
                  width: `${aiState.confidence}%`,
                  background: aiState.confidence >= 70 ? 'var(--ok)' : aiState.confidence >= 40 ? 'var(--warn)' : 'var(--danger)',
                }} />
              </div>
              {aiState.confidence_fields && (
                <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 4 }}>
                  {Object.entries(aiState.confidence_fields).map(([f, l]) => (
                    <div key={f} style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{f.replace(/_/g, ' ')}</span>
                      <span style={{
                        fontSize: 10, fontWeight: 700, letterSpacing: '0.03em',
                        color: l === 'HIGH' ? 'var(--ok)' : l === 'LOW' ? 'var(--warn)' : 'var(--danger)',
                      }}>
                        {l}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {aiState.verified?.length > 0 && (
            <div>
              <div className="t-label" style={{ color: 'var(--text-muted)', marginBottom: 7 }}>Verified</div>
              {aiState.verified.map(f => (
                <div key={f} style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '3px 0' }}>
                  <span style={{ fontSize: 11, color: 'var(--ok)', fontWeight: 700 }}>✓</span>
                  <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{f.replace(/_/g, ' ')}</span>
                </div>
              ))}
            </div>
          )}

          {aiState.unverified?.length > 0 && (
            <div>
              <div className="t-label" style={{ color: 'var(--text-muted)', marginBottom: 7 }}>Uncertain</div>
              {aiState.unverified.map(f => (
                <div key={f} style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '3px 0' }}>
                  <span style={{ fontSize: 11, color: 'var(--warn)', fontWeight: 600 }}>–</span>
                  <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{f.replace(/_/g, ' ')}</span>
                </div>
              ))}
            </div>
          )}

          {aiState.action && aiState.action !== 'UNDERSTAND_REQUEST' && (
            <div style={{ padding: '10px 12px', background: 'var(--surface-1)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)' }}>
              <div className="t-label" style={{ color: 'var(--text-muted)', marginBottom: 5 }}>
                {voiceState === 'ACTING' ? 'Current action' : 'Next action'}
              </div>
              <div style={{ fontSize: 12.5, fontWeight: 500 }}>
                {aiState.tool_status === 'completed' ? '✓ ' : aiState.tool_status === 'running' ? '→ ' : ''}
                {ACTION_LABELS[aiState.action] || aiState.action.replace(/_/g, ' ')}
              </div>
              {aiState.tool && (
                <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 3, fontFamily: 'var(--font-mono)' }}>
                  {aiState.tool}
                  {aiState.tool_status && (
                    <span style={{
                      marginLeft: 6,
                      color: aiState.tool_status === 'completed' ? 'var(--ok)' : aiState.tool_status === 'failed' ? 'var(--danger)' : 'var(--warn)',
                    }}>
                      [{aiState.tool_status}]
                    </span>
                  )}
                </div>
              )}
            </div>
          )}

          {aiState.tool_result && (
            <div style={{ padding: '10px 12px', background: 'var(--ok-bg)', border: '1px solid var(--ok-border)', borderRadius: 'var(--r-md)' }}>
              <div className="t-label" style={{ color: 'var(--ok)', marginBottom: 5 }}>Tool result</div>
              {aiState.tool_result.amount && (
                <div style={{ fontSize: 12 }}>✓ Amount: ₹{Number(aiState.tool_result.amount).toLocaleString('en-IN')}</div>
              )}
              {aiState.tool_result.status && (
                <div style={{ fontSize: 12, marginTop: 2 }}>✓ Payment: {aiState.tool_result.status}</div>
              )}
              {aiState.tool_result.order_status && (
                <div style={{
                  fontSize: 12,
                  color: aiState.tool_result.order_status === 'CONFIRMED' ? 'var(--ok)' : 'var(--warn)',
                  marginTop: 2,
                }}>
                  {aiState.tool_result.order_status === 'CONFIRMED' ? '✓' : '–'} Order: {aiState.tool_result.order_status}
                </div>
              )}
            </div>
          )}
        </>)}

        {!aiState && voiceState === 'IDLE' && (
          <div style={{ fontSize: 12, color: 'var(--text-muted)', textAlign: 'center', padding: '12px 0' }}>
            Start a conversation to see live AI state
          </div>
        )}
      </div>
    </div>
  )
}

