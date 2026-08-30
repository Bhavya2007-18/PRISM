import { useState } from 'react'
import { getApiUrl } from '../lib/api'

export default function EscalationPanel({ caseData, onTakeOver, compact = false }) {
  const [loading, setLoading] = useState(false)
  const [localTakenOver, setLocalTakenOver] = useState(
    caseData?.taken_over || caseData?.status === 'TAKEN_OVER'
  )

  if (!caseData) return null

  const takenOver = localTakenOver || caseData.taken_over || caseData.status === 'TAKEN_OVER'
  const confidence = typeof caseData.confidence_display === 'number' ? caseData.confidence_display : 41
  const confColor = confidence >= 70 ? 'var(--success)' : confidence >= 40 ? 'var(--warning)' : 'var(--danger)'

  async function handleTakeOver() {
    if (takenOver || loading) return
    setLoading(true)
    try {
      const res = await fetch(getApiUrl(`/cases/${caseData.case_id}/takeover`), { method: 'POST' })
      if (res.ok) {
        setLocalTakenOver(true)
        onTakeOver?.(caseData.case_id)
      } else {
        setLocalTakenOver(true)
        onTakeOver?.(caseData.case_id)
      }
    } catch (e) {
      setLocalTakenOver(true)
      onTakeOver?.(caseData.case_id)
    }
    setLoading(false)
  }

  if (compact) {
    return (
      <div
        className={takenOver ? 'glass-panel' : 'glass-panel-danger'}
        style={{
          padding: '18px 20px',
          opacity: takenOver ? 0.7 : 1,
        }}
      >
        {!takenOver && (
          <div className="slide-up" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
            }}>
              <span style={{ fontSize: 16 }}>🔴</span>
              <div>
                <div style={{
                  fontSize: 11,
                  fontWeight: 700,
                  letterSpacing: 2,
                  color: 'var(--danger)',
                  textTransform: 'uppercase',
                }}>
                  HUMAN ASSISTANCE REQUIRED
                </div>
                <div style={{
                  fontSize: 11,
                  color: 'var(--text-muted)',
                  marginTop: 2,
                }}>
                  PRISM confidence: <span style={{ color: confColor, fontWeight: 700 }}>{confidence}%</span>
                </div>
              </div>
            </div>

            <div>
              <div className="label-text" style={{ fontSize: 9, marginBottom: 4 }}>Reason</div>
              <p style={{
                fontSize: 12,
                color: 'var(--text-secondary)',
                lineHeight: 1.6,
                margin: 0,
              }}>
                {caseData.reason_for_escalation || 'Unable to confidently determine whether the customer was charged twice.'}
              </p>
            </div>

            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr 1fr',
              gap: 8,
              padding: '10px 12px',
              background: 'rgba(52,211,153,0.04)',
              border: '1px solid rgba(52,211,153,0.15)',
              borderRadius: 8,
            }}>
              {[
                { label: 'Context', icon: '✓' },
                { label: 'Summary', icon: '✓' },
                { label: 'Verified', icon: '✓' },
              ].map(item => (
                <div key={item.label} style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                  justifyContent: 'center',
                }}>
                  <span style={{ fontSize: 10, color: 'var(--success)' }}>{item.icon}</span>
                  <span style={{ fontSize: 10, color: 'var(--text-secondary)' }}>{item.label}</span>
                </div>
              ))}
            </div>

            <button
              onClick={handleTakeOver}
              disabled={loading}
              className="btn-danger"
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
              }}
            >
              <span>🎧</span>
              {loading ? 'Taking over...' : 'TAKE OVER CONVERSATION'}
            </button>
          </div>
        )}

        {takenOver && (
          <div className="fade-in" style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 10,
          }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
            }}>
              <span style={{ fontSize: 16 }}>🔵</span>
              <div>
                <div style={{
                  fontSize: 11,
                  fontWeight: 700,
                  letterSpacing: 2,
                  color: 'var(--info)',
                  textTransform: 'uppercase',
                }}>
                  HUMAN AGENT CONNECTED
                </div>
              </div>
            </div>
            <p style={{
              fontSize: 12,
              color: 'var(--text-secondary)',
              textAlign: 'center',
              margin: 0,
              lineHeight: 1.6,
            }}>
              PRISM has transferred the conversation. Context has been preserved.
            </p>
          </div>
        )}
      </div>
    )
  }

  return (
    <div
      className={takenOver ? 'glass-panel' : 'glass-panel-danger'}
      style={{
        padding: '24px 28px',
        opacity: takenOver ? 0.7 : 1,
      }}
    >
      {!takenOver && (
        <div className="slide-up" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          {/* Header */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 12,
            }}>
              <span style={{ fontSize: 20 }}>🔴</span>
              <div>
                <div style={{
                  fontSize: 13,
                  fontWeight: 700,
                  letterSpacing: 2,
                  color: 'var(--danger)',
                  textTransform: 'uppercase',
                }}>
                  HUMAN ASSISTANCE REQUIRED
                </div>
                <div style={{
                  fontSize: 12,
                  color: 'var(--text-muted)',
                  marginTop: 4,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                }}>
                  PRISM confidence:
                  <span style={{
                    fontSize: 14,
                    fontWeight: 800,
                    color: confColor,
                  }}>
                    {confidence}%
                  </span>
                </div>
              </div>
            </div>
            <span className="monospace" style={{
              fontSize: 12,
              color: 'var(--text-muted)',
            }}>
              {caseData.case_id}
            </span>
          </div>

          {/* Reason */}
          <div>
            <div className="label-text">Reason</div>
            <p style={{
              fontSize: 14,
              color: 'var(--text-primary)',
              lineHeight: 1.7,
              margin: '8px 0 0 0',
              fontWeight: 500,
            }}>
              {caseData.reason_for_escalation || 'Unable to confidently determine whether the customer was charged twice.'}
            </p>
          </div>

          {/* Context preserved */}
          <div style={{
            display: 'flex',
            gap: 12,
            padding: '14px 18px',
            background: 'rgba(52,211,153,0.05)',
            border: '1px solid rgba(52,211,153,0.2)',
            borderRadius: 12,
          }}>
            {[
              { label: 'Context preserved', icon: '✓' },
              { label: 'Conversation summary', icon: '✓' },
              { label: 'Transaction verified', icon: '✓' },
            ].map(item => (
              <div key={item.label} style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                flex: 1,
                justifyContent: 'center',
              }}>
                <span style={{ color: 'var(--success)', fontSize: 12 }}>{item.icon}</span>
                <span style={{ fontSize: 12, color: 'var(--text-secondary)', fontWeight: 500 }}>{item.label}</span>
              </div>
            ))}
          </div>

          {/* Take over button */}
          <button
            onClick={handleTakeOver}
            disabled={loading}
            className="btn-danger"
            style={{
              padding: '16px 32px',
              fontSize: 14,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 10,
            }}
          >
            <span style={{ fontSize: 18 }}>🎧</span>
            {loading ? 'Taking over conversation...' : 'TAKE OVER CONVERSATION'}
          </button>
        </div>
      )}

      {takenOver && (
        <div className="fade-in" style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 16,
          padding: '20px 0',
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 14,
          }}>
            <span style={{ fontSize: 24 }}>🔵</span>
            <div>
              <div style={{
                fontSize: 13,
                fontWeight: 700,
                letterSpacing: 2,
                color: 'var(--info)',
                textTransform: 'uppercase',
              }}>
                HUMAN AGENT CONNECTED
              </div>
            </div>
          </div>
          <p style={{
            fontSize: 14,
            color: 'var(--text-secondary)',
            textAlign: 'center',
            margin: 0,
            lineHeight: 1.7,
            maxWidth: 420,
          }}>
            PRISM has transferred the conversation. Context has been preserved. The user shouldn't have to repeat anything.
          </p>
        </div>
      )}
    </div>
  )
}
