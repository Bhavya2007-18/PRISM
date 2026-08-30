/**
 * ThinkingPanel -- PRISM Live AI State
 *
 * Displays the real operational state of PRISM's decision pipeline.
 * Every element shown here corresponds to an actual backend operation.
 * No fake animations. No artificial delays.
 */

const PHASE_CONFIG = {
  IDLE:            { icon: '○',  color: '#565674', label: 'Idle' },
  CONNECTING:      { icon: '◌',  color: '#60a5fa', label: 'Connecting' },
  LISTENING:       { icon: '🎙', color: '#34d399', label: 'Listening' },
  UNDERSTANDING:   { icon: '◉',  color: '#a78bfa', label: 'Understanding' },
  THINKING:        { icon: '◌',  color: '#7c6fff', label: 'Thinking' },
  ACTING:          { icon: '⚡',  color: '#fbbf24', label: 'Checking' },
  SPEAKING:        { icon: '🔊', color: '#34d399', label: 'Speaking' },
  ESCALATING:      { icon: '⚠',  color: '#f87171', label: 'Escalating' },
  HUMAN_CONNECTED: { icon: '🟢', color: '#34d399', label: 'Human Connected' },
  ERROR:           { icon: '✕',  color: '#f87171', label: 'Error' },
}

const ACTION_LABELS = {
  ASK_CLARIFICATION:  'Asking for information',
  CONFIRM_INFORMATION:'Confirming details',
  VERIFY_TRANSACTION: 'Verifying transaction',
  CHECK_ORDER:        'Checking order status',
  RESOLVE_CASE:       'Resolving case',
  ESCALATE_TO_HUMAN:  'Escalating to specialist',
  UNDERSTAND_REQUEST: 'Understanding request',
  NO_ACTION:          'Processing',
}

function Dot({ color, pulse }) {
  return (
    <span style={{
      width: 6, height: 6, borderRadius: '50%', display: 'inline-block',
      background: color,
      boxShadow: pulse ? `0 0 8px ${color}` : 'none',
      transition: 'all 0.3s',
    }} />
  )
}

function SectionLabel({ children }) {
  return (
    <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 2, color: '#565674', textTransform: 'uppercase', marginBottom: 8 }}>
      {children}
    </div>
  )
}

export default function ThinkingPanel({ voiceState = 'IDLE', aiState = null, compact = false }) {
  const cfg = PHASE_CONFIG[voiceState] || PHASE_CONFIG.IDLE

  if (compact) {
    return (
      <div style={{ padding: '8px 12px', background: `${cfg.color}0d`, borderRadius: 8, border: `1px solid ${cfg.color}22`, display: 'flex', alignItems: 'center', gap: 8 }}>
        <Dot color={cfg.color} pulse />
        <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: 1, color: cfg.color }}>{cfg.label.toUpperCase()}</span>
        {aiState?.intent && <span style={{ fontSize: 11, color: '#8a8aa8', marginLeft: 4 }}>{aiState.intent.replace(/_/g, ' ')}</span>}
        {aiState?.confidence != null && (
          <span style={{ marginLeft: 'auto', fontSize: 12, fontWeight: 700, color: aiState.confidence >= 60 ? '#34d399' : '#f87171' }}>
            {aiState.confidence}%
          </span>
        )}
      </div>
    )
  }

  const PIPELINE = ['LISTENING', 'UNDERSTANDING', 'THINKING', 'ACTING', voiceState === 'HUMAN_CONNECTED' ? 'HUMAN_CONNECTED' : 'SPEAKING', 'ESCALATING']
  const activeIdx = PIPELINE.indexOf(voiceState)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18, height: '100%', overflowY: 'auto', padding: '16px 14px' }}>

      {/* Phase header */}
      <div style={{ padding: '10px 14px', background: `${cfg.color}0d`, borderRadius: 10, border: `1px solid ${cfg.color}25`, display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ fontSize: 14 }}>{cfg.icon}</span>
        <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: 1.5, color: cfg.color }}>{cfg.label.toUpperCase()}</span>
        <Dot color={cfg.color} pulse style={{ marginLeft: 'auto' }} />
      </div>

      {/* Pipeline steps */}
      <div>
        <SectionLabel>Pipeline</SectionLabel>
        {PIPELINE.filter((p, i, arr) => arr.indexOf(p) === i).map((p, i) => {
          const pcfg = PHASE_CONFIG[p] || PHASE_CONFIG.IDLE
          const isActive = p === voiceState
          const isDone = PIPELINE.indexOf(p) < activeIdx
          return (
            <div key={p} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '5px 0', opacity: isActive ? 1 : isDone ? 0.5 : 0.25, transition: 'opacity 0.3s' }}>
              <span style={{ fontSize: 11, width: 18, textAlign: 'center', color: isActive ? pcfg.color : '#565674' }}>{pcfg.icon}</span>
              <span style={{ fontSize: 12, color: isActive ? pcfg.color : '#8a8aa8', fontWeight: isActive ? 600 : 400 }}>{pcfg.label}</span>
              {isActive && <Dot color={pcfg.color} pulse style={{ marginLeft: 'auto' }} />}
              {isDone && <span style={{ marginLeft: 'auto', fontSize: 10, color: '#34d399' }}>✓</span>}
            </div>
          )
        })}
      </div>

      {aiState && (
        <>
          {/* Intent */}
          {aiState.intent && (
            <div>
              <SectionLabel>Intent</SectionLabel>
              <div style={{ fontSize: 13, fontWeight: 600 }}>{aiState.intent.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</div>
            </div>
          )}

          {/* Language */}
          {aiState.language?.length > 0 && (
            <div>
              <SectionLabel>Language</SectionLabel>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {aiState.language.map(l => (
                  <span key={l} style={{ padding: '2px 8px', borderRadius: 20, fontSize: 11, background: 'rgba(124,111,255,0.1)', color: '#7c6fff', border: '1px solid rgba(124,111,255,0.2)' }}>{l}</span>
                ))}
              </div>
            </div>
          )}

          {/* Confidence */}
          {aiState.confidence != null && (
            <div>
              <SectionLabel>Confidence</SectionLabel>
              {(() => {
                const c = aiState.confidence
                const color = c >= 70 ? '#34d399' : c >= 40 ? '#fbbf24' : '#f87171'
                return (
                  <>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 6 }}>
                      <span style={{ fontSize: 26, fontWeight: 700, color }}>{c}%</span>
                      <span style={{ fontSize: 10, color: '#565674' }}>{aiState.confidence_label}</span>
                    </div>
                    <div style={{ height: 4, background: '#1a1a2a', borderRadius: 2, overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${c}%`, background: color, borderRadius: 2, transition: 'width 0.6s ease' }} />
                    </div>
                    {aiState.confidence_fields && (
                      <div style={{ marginTop: 8 }}>
                        {Object.entries(aiState.confidence_fields).map(([f, l]) => (
                          <div key={f} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, padding: '2px 0' }}>
                            <span style={{ color: '#565674' }}>{f.replace(/_/g, ' ')}</span>
                            <span style={{ fontWeight: 700, color: l === 'HIGH' ? '#34d399' : l === 'LOW' ? '#fbbf24' : '#f87171' }}>{l}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                )
              })()}
            </div>
          )}

          {/* Verified */}
          {aiState.verified?.length > 0 && (
            <div>
              <SectionLabel>Verified</SectionLabel>
              {aiState.verified.map(f => (
                <div key={f} style={{ fontSize: 12, color: '#34d399', display: 'flex', gap: 6, padding: '2px 0' }}>
                  <span>✓</span><span>{f.replace(/_/g, ' ')}</span>
                </div>
              ))}
            </div>
          )}

          {/* Uncertain */}
          {aiState.unverified?.length > 0 && (
            <div>
              <SectionLabel>Uncertain</SectionLabel>
              {aiState.unverified.map(f => (
                <div key={f} style={{ fontSize: 12, color: '#fbbf24', display: 'flex', gap: 6, padding: '2px 0' }}>
                  <span>⚠</span><span>{f.replace(/_/g, ' ')}</span>
                </div>
              ))}
            </div>
          )}

          {/* Current action */}
          {aiState.action && aiState.action !== 'UNDERSTAND_REQUEST' && (
            <div style={{ padding: '10px 12px', background: 'rgba(251,191,36,0.07)', borderRadius: 8, border: '1px solid rgba(251,191,36,0.18)' }}>
              <div style={{ fontSize: 10, color: '#fbbf24', fontWeight: 700, letterSpacing: 1, marginBottom: 3 }}>
                {voiceState === 'ACTING' ? '⚡ CURRENT ACTION' : 'NEXT ACTION'}
              </div>
              <div style={{ fontSize: 12, color: '#fbbf24' }}>
                {aiState.tool_status === 'completed' ? '✓ ' : aiState.tool_status === 'running' ? '⚡ ' : ''}
                {ACTION_LABELS[aiState.action] || aiState.action.replace(/_/g, ' ')}
              </div>
              {aiState.tool && (
                <div style={{ fontSize: 11, color: '#565674', marginTop: 3 }}>
                  {aiState.tool}
                  {aiState.tool_status && (
                    <span style={{ marginLeft: 6, color: aiState.tool_status === 'completed' ? '#34d399' : aiState.tool_status === 'failed' ? '#f87171' : '#fbbf24' }}>
                      [{aiState.tool_status}]
                    </span>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Tool result */}
          {aiState.tool_result && (
            <div style={{ padding: '10px 12px', background: 'rgba(52,211,153,0.07)', borderRadius: 8, border: '1px solid rgba(52,211,153,0.18)' }}>
              <div style={{ fontSize: 10, color: '#34d399', fontWeight: 700, letterSpacing: 1, marginBottom: 5 }}>TOOL RESULT</div>
              {aiState.tool_result.amount && <div style={{ fontSize: 12, color: '#34d399' }}>✓ Amount: ₹{Number(aiState.tool_result.amount).toLocaleString('en-IN')}</div>}
              {aiState.tool_result.status && <div style={{ fontSize: 12, color: '#34d399' }}>✓ Payment: {aiState.tool_result.status}</div>}
              {aiState.tool_result.order_status && (
                <div style={{ fontSize: 12, color: aiState.tool_result.order_status === 'CONFIRMED' ? '#34d399' : '#fbbf24' }}>
                  {aiState.tool_result.order_status === 'CONFIRMED' ? '✓' : '⚠'} Order: {aiState.tool_result.order_status}
                </div>
              )}
            </div>
          )}
        </>
      )}

      {!aiState && (
        <div style={{ color: '#565674', fontSize: 12, textAlign: 'center', paddingTop: 20 }}>
          {voiceState === 'IDLE' ? 'Start a conversation to see live AI state' : 'Waiting...'}
        </div>
      )}
    </div>
  )
}