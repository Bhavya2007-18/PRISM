import { useState } from 'react'

export default function EscalationPanel({ caseData, onTakeOver }) {
  const [loading, setLoading] = useState(false)
  const [localTakenOver, setLocalTakenOver] = useState(
    caseData?.taken_over || caseData?.status === 'TAKEN_OVER'
  )

  if (!caseData) return null

  const takenOver = localTakenOver || caseData.taken_over || caseData.status === 'TAKEN_OVER'
  const confidence = typeof caseData.confidence_display === 'number' ? caseData.confidence_display : 0
  const confColor = confidence >= 70 ? '#2ecc71' : confidence >= 40 ? '#f39c12' : '#e74c3c'

  async function handleTakeOver() {
    if (takenOver || loading) return
    setLoading(true)
    try {
      const res = await fetch(`/cases/${caseData.case_id}/takeover`, { method: 'POST' })
      if (res.ok) {
        setLocalTakenOver(true)
        onTakeOver?.(caseData.case_id)
      }
    } catch (e) {
      console.error('Take over failed:', e)
    }
    setLoading(false)
  }

  const verifiedItems = []
  if (caseData.transaction_id) verifiedItems.push({ label: 'Transaction', value: caseData.transaction_id })
  if (caseData.amount != null) verifiedItems.push({ label: 'Amount', value: `₹${Number(caseData.amount).toLocaleString('en-IN')}` })
  if (caseData.payment_status) verifiedItems.push({ label: 'Payment', value: caseData.payment_status })
  if (caseData.order_status) verifiedItems.push({ label: 'Order', value: caseData.order_status })

  const uncertainItems = (caseData.unverified || [])
    .filter(f => f !== 'transaction_id' || !caseData.transaction_id)

  return (
    <div style={{
      background: 'var(--bg-card)',
      border: `1px solid ${takenOver ? 'var(--border)' : 'rgba(231,76,60,0.3)'}`,
      borderRadius: 16,
      overflow: 'hidden',
      transition: 'border-color 0.4s ease',
      opacity: takenOver ? 0.75 : 1,
    }}>

      {/* ── Header ─────────────────────────────────────────────────── */}
      <div style={{
        padding: '12px 20px',
        background: takenOver ? 'var(--bg-elevated)' : 'rgba(231,76,60,0.08)',
        borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 10 }}>🔴</span>
          <span style={{
            fontSize: 11, fontWeight: 700, letterSpacing: 2,
            color: takenOver ? 'var(--text-secondary)' : '#ff6b6b',
          }}>
            {takenOver ? 'TAKEN OVER' : 'ESCALATION'}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{
            fontSize: 12, fontFamily: 'monospace',
            color: 'var(--text-secondary)',
          }}>
            {caseData.case_id}
          </span>
          <span style={{ fontSize: 11, color: '#333355' }}>
            {new Date(caseData.created_at).toLocaleTimeString()}
          </span>
        </div>
      </div>

      {/* ── Body ───────────────────────────────────────────────────── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 0,
      }}>

        {/* Left: case info */}
        <div style={{
          padding: 20,
          borderRight: '1px solid var(--border)',
          display: 'flex', flexDirection: 'column', gap: 18,
        }}>

          {/* Issue */}
          <div>
            <div style={labelStyle}>Issue</div>
            <div style={{ fontSize: 15, fontWeight: 600 }}>
              {caseData.issue || 'Payment issue'}
            </div>
          </div>

          {/* Language */}
          <div>
            <div style={labelStyle}>Language</div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 4 }}>
              {(caseData.language?.length ? caseData.language : ['Unknown']).map(lang => (
                <span key={lang} style={{
                  padding: '3px 12px', borderRadius: 20, fontSize: 12,
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border)',
                  color: 'var(--accent)',
                }}>
                  {lang}
                </span>
              ))}
            </div>
          </div>

          {/* Verified */}
          {verifiedItems.length > 0 && (
            <div>
              <div style={labelStyle}>Verified</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 5, marginTop: 4 }}>
                {verifiedItems.map(item => (
                  <div key={item.label} style={{
                    fontSize: 13, color: '#2ecc71',
                    display: 'flex', alignItems: 'center', gap: 6,
                  }}>
                    <span>✓</span>
                    <span style={{ color: 'var(--text-secondary)' }}>{item.label}:</span>
                    <span style={{ fontWeight: 600 }}>{item.value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Uncertain */}
          {uncertainItems.length > 0 && (
            <div>
              <div style={labelStyle}>Uncertain</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 5, marginTop: 4 }}>
                {uncertainItems.map(field => (
                  <div key={field} style={{
                    fontSize: 13, color: '#f39c12',
                    display: 'flex', alignItems: 'center', gap: 6,
                  }}>
                    <span>⚠</span>
                    <span>{field.replace(/_/g, ' ')}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right: confidence + summary */}
        <div style={{
          padding: 20,
          display: 'flex', flexDirection: 'column', gap: 18,
        }}>

          {/* Confidence */}
          <div>
            <div style={labelStyle}>AI Confidence</div>
            <div style={{ marginTop: 8 }}>
              {/* Bar */}
              <div style={{
                height: 6, background: 'var(--bg-elevated)',
                borderRadius: 3, overflow: 'hidden', marginBottom: 8,
              }}>
                <div style={{
                  height: '100%', width: `${confidence}%`,
                  background: confColor, borderRadius: 3,
                  transition: 'width 0.6s ease',
                }} />
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                <span style={{ fontSize: 28, fontWeight: 700, color: confColor }}>
                  {confidence}%
                </span>
                <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                  {caseData.confidence_label || 'UNCERTAIN'}
                </span>
              </div>
            </div>

            {/* Field breakdown */}
            {caseData.confidence_fields && (
              <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 4 }}>
                {Object.entries(caseData.confidence_fields).map(([field, label]) => (
                  <div key={field} style={{
                    display: 'flex', justifyContent: 'space-between',
                    alignItems: 'center', fontSize: 11,
                  }}>
                    <span style={{ color: 'var(--text-secondary)' }}>
                      {field.replace(/_/g, ' ')}
                    </span>
                    <span style={{
                      fontWeight: 700, letterSpacing: 0.5,
                      color: label === 'HIGH' ? '#2ecc71'
                           : label === 'LOW' ? '#f39c12'
                           : '#e74c3c',
                    }}>
                      {label}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Summary */}
          <div>
            <div style={labelStyle}>Summary</div>
            <p style={{
              fontSize: 13, color: 'var(--text-secondary)',
              lineHeight: 1.6, margin: 0, marginTop: 4,
            }}>
              {caseData.summary}
            </p>
          </div>

          {/* Escalation reason */}
          <div>
            <div style={labelStyle}>Reason for Escalation</div>
            <p style={{
              fontSize: 13, color: '#f39c12',
              lineHeight: 1.5, margin: 0, marginTop: 4,
            }}>
              {caseData.reason_for_escalation}
            </p>
          </div>
        </div>
      </div>

      {/* ── Footer ─────────────────────────────────────────────────── */}
      <div style={{
        padding: '14px 20px',
        borderTop: '1px solid var(--border)',
        display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 12,
      }}>
        {takenOver && (
          <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
            Handled by human agent
          </span>
        )}
        <button
          onClick={handleTakeOver}
          disabled={takenOver || loading}
          style={{
            padding: '10px 32px',
            background: takenOver ? 'var(--bg-elevated)' : 'var(--accent)',
            color: takenOver ? 'var(--text-secondary)' : '#fff',
            border: `1px solid ${takenOver ? 'var(--border)' : 'transparent'}`,
            borderRadius: 8,
            fontSize: 13, fontWeight: 700,
            letterSpacing: 1,
            cursor: takenOver ? 'default' : 'pointer',
            opacity: loading ? 0.7 : 1,
            transition: 'all 0.2s ease',
          }}
        >
          {loading ? 'Taking over…' : takenOver ? '✓ TAKEN OVER' : 'TAKE OVER'}
        </button>
      </div>
    </div>
  )
}

const labelStyle = {
  fontSize: 10,
  fontWeight: 700,
  letterSpacing: 2,
  color: 'var(--text-secondary)',
  textTransform: 'uppercase',
  marginBottom: 2,
}
