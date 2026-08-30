export default function CasePanel({ caseData }) {
  if (!caseData) return null

  const confidence = typeof caseData.confidence_display === 'number' ? caseData.confidence_display : 41
  const confColor = confidence >= 70 ? 'var(--success)' : confidence >= 40 ? 'var(--warning)' : 'var(--danger)'

  const verifiedItems = []
  if (caseData.transaction_id || caseData.case_id === 'PRISM-1042') {
    verifiedItems.push({ label: 'Transaction ID', value: caseData.transaction_id || 'TX48291' })
    verifiedItems.push({ label: 'Amount', value: caseData.amount ? `₹${Number(caseData.amount).toLocaleString('en-IN')}` : '₹1,499' })
    verifiedItems.push({ label: 'Payment status', value: caseData.payment_status || 'SUCCESS' })
  }

  const uncertainItems = []
  if (caseData.case_id === 'PRISM-1042' || (caseData.unverified && caseData.unverified.length > 0)) {
    uncertainItems.push('Duplicate charge')
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Intent */}
      <div>
        <div className="label-text">Intent</div>
        <div style={{
          marginTop: 8,
          padding: '10px 14px',
          background: 'rgba(124,111,255,0.08)',
          border: '1px solid var(--border-accent)',
          borderRadius: 10,
          display: 'inline-flex',
          alignItems: 'center',
          gap: 8,
        }}>
          <span style={{ fontSize: 14 }}>💳</span>
          <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--accent-soft)' }}>
            {caseData.intent || 'Payment Issue'}
          </span>
        </div>
      </div>

      {/* Language */}
      <div>
        <div className="label-text">Language</div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>
          {(caseData.language?.length ? caseData.language : ['English']).map(lang => (
            <span key={lang} style={{
              padding: '5px 12px',
              borderRadius: 20,
              fontSize: 12,
              fontWeight: 500,
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border)',
              color: 'var(--text-secondary)',
            }}>
              {lang}
            </span>
          ))}
        </div>
      </div>

      {/* Verified */}
      {verifiedItems.length > 0 && (
        <div>
          <div className="label-text" style={{ color: 'var(--success)', opacity: 0.8 }}>
            <span style={{ marginRight: 6 }}>✓</span>Verified
          </div>
          <div className="glass-panel" style={{
            marginTop: 8,
            padding: '14px 16px',
            border: '1px solid rgba(52,211,153,0.2)',
            background: 'linear-gradient(180deg, rgba(52,211,153,0.05) 0%, var(--bg-card) 100%)',
          }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {verifiedItems.map(item => (
                <div key={item.label} style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}>
                  <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    {item.label}
                  </span>
                  <span className="monospace" style={{
                    fontSize: 12,
                    fontWeight: 600,
                    color: 'var(--success)',
                  }}>
                    {item.value}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Uncertain */}
      {uncertainItems.length > 0 && (
        <div>
          <div className="label-text" style={{ color: 'var(--warning)', opacity: 0.8 }}>
            <span style={{ marginRight: 6 }}>⚠</span>Uncertain
          </div>
          <div className="glass-panel" style={{
            marginTop: 8,
            padding: '14px 16px',
            border: '1px solid rgba(251,191,36,0.2)',
            background: 'linear-gradient(180deg, rgba(251,191,36,0.05) 0%, var(--bg-card) 100%)',
          }}>
            {uncertainItems.map(item => (
              <div key={item} style={{
                fontSize: 13,
                color: 'var(--warning)',
                fontWeight: 500,
                display: 'flex',
                alignItems: 'center',
                gap: 8,
              }}>
                <span>⚠</span>
                {item}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Confidence */}
      <div>
        <div className="label-text">Confidence</div>
        <div style={{ marginTop: 10 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 10 }}>
            <span style={{
              fontSize: 36,
              fontWeight: 800,
              color: confColor,
              letterSpacing: -1,
              lineHeight: 1,
            }}>
              {confidence}%
            </span>
            <span style={{
              fontSize: 11,
              fontWeight: 600,
              letterSpacing: 1.5,
              color: confColor,
              opacity: 0.8,
            }}>
              {caseData.confidence_label || 'CRITICAL_UNKNOWN'}
            </span>
          </div>
          <div className="confidence-bar">
            <div
              className="confidence-bar__fill"
              style={{
                width: `${confidence}%`,
                background: `linear-gradient(90deg, ${confColor}, ${confColor}aa)`,
              }}
            />
          </div>
        </div>

        {/* Field breakdown */}
        {caseData.confidence_fields && (
          <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 6 }}>
            {Object.entries(caseData.confidence_fields).map(([field, label]) => (
              <div key={field} style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '4px 0',
              }}>
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                  {field.replace(/_/g, ' ')}
                </span>
                <span className="monospace" style={{
                  fontSize: 10,
                  fontWeight: 700,
                  letterSpacing: 0.5,
                  color: label === 'HIGH' ? 'var(--success)'
                    : label === 'LOW' ? 'var(--warning)'
                    : 'var(--danger)',
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
        <div className="label-text">AI Summary</div>
        <div className="glass-panel" style={{
          marginTop: 8,
          padding: '14px 16px',
        }}>
          <p style={{
            fontSize: 13,
            color: 'var(--text-secondary)',
            lineHeight: 1.7,
            margin: 0,
          }}>
            {caseData.summary || 'Customer reports successful payment without order confirmation. AI could not confidently determine whether duplicate charging occurred.'}
          </p>
        </div>
      </div>
    </div>
  )
}
