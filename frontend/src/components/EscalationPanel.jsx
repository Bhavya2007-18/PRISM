import { useState } from 'react'
import { getApiUrl } from '../lib/api'

export default function EscalationPanel({ caseData, onTakeOver, compact = false }) {
  const [taking, setTaking] = useState(false)
  const [taken, setTaken] = useState(caseData?.taken_over || caseData?.status === 'TAKEN_OVER')
  if (!caseData) return null

  const conf = caseData.confidence_display ?? 0
  const cc = conf >= 70 ? 'var(--ok)' : conf >= 40 ? 'var(--warn)' : 'var(--danger)'

  async function handleTakeOver() {
    if (taken || taking) return
    setTaking(true)
    try {
      await fetch(getApiUrl(`/cases/${caseData.case_id}/takeover`), { method: 'POST' })
      setTaken(true)
      onTakeOver?.(caseData.case_id)
    } catch (e) { console.error(e) }
    setTaking(false)
  }

  const vi = []
  if (caseData.transaction_id) vi.push({ label: 'Transaction', value: caseData.transaction_id })
  if (caseData.amount != null)  vi.push({ label: 'Amount', value: `₹${caseData.amount}` })
  if (caseData.payment_status) vi.push({ label: 'Payment', value: caseData.payment_status })
  if (caseData.order_status)   vi.push({ label: 'Order', value: caseData.order_status })
  const ui = caseData.unverified || []

  if (compact) {
    return (
      <div
        className="card"
        style={{
          padding: '14px 16px',
          background: taken ? 'var(--ok-bg)' : 'var(--danger-bg)',
          border: `1px solid ${taken ? 'var(--ok-border)' : 'var(--danger-border)'}`,
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
          transition: 'background 0.4s ease',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: 12, fontWeight: 700, color: taken ? 'var(--ok)' : 'var(--danger)', letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: 2 }}>
              {taken ? 'Resolved' : 'Human required'}
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
              {caseData.issue || caseData.intent || 'Escalated case'}
            </div>
          </div>
          <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)' }}>
            {caseData.case_id}
          </span>
        </div>
        {caseData.reason_for_escalation && (
          <p style={{ fontSize: 12, color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5 }}>
            {caseData.reason_for_escalation}
          </p>
        )}
        {!taken && (
          <button onClick={handleTakeOver} disabled={taking} className="btn btn--primary btn--sm" style={{ alignSelf: 'flex-end' }}>
            {taking ? 'Connecting…' : 'Take over conversation'}
          </button>
        )}
        {taken && (
          <div style={{ fontSize: 12, color: 'var(--ok)', fontWeight: 500 }}>✓ Human agent connected</div>
        )}
      </div>
    )
  }

  return (
    <div style={{ background: 'var(--surface-0)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', overflow: 'hidden', transition: 'border-color 0.3s ease' }}>
      {/* Header */}
      <div style={{
        padding: '13px 20px',
        background: taken ? 'var(--surface-1)' : 'var(--danger-bg)',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        transition: 'background 0.4s ease',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
          <span style={{ width: 7, height: 7, borderRadius: '50%', display: 'inline-block', background: taken ? 'var(--ok)' : 'var(--danger)', flexShrink: 0 }} />
          <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: taken ? 'var(--text-tertiary)' : 'var(--danger)' }}>
            {taken ? 'Resolved' : 'Escalation'}
          </span>
        </div>
        <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)' }}>
          {caseData.case_id}
        </span>
      </div>

      {/* Body grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr' }}>
        {/* Left column */}
        <div style={{ padding: '16px 20px', borderRight: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <div className="t-label" style={{ color: 'var(--text-muted)', marginBottom: 5 }}>Issue</div>
            <div style={{ fontSize: 14, fontWeight: 600, lineHeight: 1.3 }}>{caseData.issue || 'Payment issue'}</div>
          </div>
          <div>
            <div className="t-label" style={{ color: 'var(--text-muted)', marginBottom: 6 }}>Language</div>
            <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
              {(caseData.language?.length ? caseData.language : ['Unknown']).map(l => (
                <span key={l} style={{ padding: '2px 9px', borderRadius: 'var(--r-full)', background: 'var(--surface-2)', border: '1px solid var(--border)', fontSize: 11, fontWeight: 500, color: 'var(--text-secondary)' }}>
                  {l}
                </span>
              ))}
            </div>
          </div>
          {vi.length > 0 && (
            <div>
              <div className="t-label" style={{ color: 'var(--text-muted)', marginBottom: 6 }}>Verified</div>
              {vi.map(item => (
                <div key={item.label} className="tx-row" style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', gap: 8, borderBottom: 'none' }}>
                  <span style={{ fontSize: 12, color: 'var(--ok)' }}>&#x2713; {item.label}</span>
                  <span style={{ fontSize: 12, fontWeight: 600 }}>{item.value}</span>
                </div>
              ))}
            </div>
          )}
          {ui.length > 0 && (
            <div>
              <div className="t-label" style={{ color: 'var(--text-muted)', marginBottom: 6 }}>Uncertain</div>
              {ui.map(f => (
                <div key={f} style={{ fontSize: 12, color: 'var(--warn)', padding: '2px 0' }}>&ndash; {f.replace(/_/g, ' ')}</div>
              ))}
            </div>
          )}
        </div>

        {/* Right column */}
        <div style={{ padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 8 }}>
              <span className="t-label" style={{ color: 'var(--text-muted)' }}>Confidence</span>
              <span style={{ fontSize: 24, fontWeight: 700, letterSpacing: '-0.03em', color: cc }}>{conf}%</span>
            </div>
            <div className="progress" style={{ marginBottom: 6 }}>
              <div
                className={`progress__fill progress__fill--${conf >= 70 ? 'ok' : conf >= 40 ? 'warn' : 'danger'}`}
                style={{ width: `${conf}%` }}
              />
            </div>
            <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase', color: cc }}>
              {caseData.confidence_label || 'Uncertain'}
            </div>
          </div>
          {caseData.summary && (
            <div>
              <div className="t-label" style={{ color: 'var(--text-muted)', marginBottom: 5 }}>Summary</div>
              <p style={{ fontSize: 12.5, color: 'var(--text-secondary)', margin: 0, lineHeight: 1.55 }}>{caseData.summary}</p>
            </div>
          )}
          {caseData.reason_for_escalation && (
            <div>
              <div className="t-label" style={{ color: 'var(--danger)', marginBottom: 5 }}>Reason</div>
              <p style={{ fontSize: 12.5, color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5 }}>{caseData.reason_for_escalation}</p>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div style={{ padding: '12px 20px', borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 12, background: 'var(--surface-1)' }}>
        {taken && <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>Handled by human agent</span>}
        <button onClick={handleTakeOver} disabled={taken || taking} className="btn btn--primary btn--sm">
          {taking ? 'Connecting…' : taken ? '✓ Taken over' : 'Take over conversation'}
        </button>
      </div>
    </div>
  )
}
