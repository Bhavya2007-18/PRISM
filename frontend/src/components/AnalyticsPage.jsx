export default function AnalyticsPage({ cases = [], demoMode }) {
  const total = cases.length || 1
  const resolved = cases.filter(c => c.taken_over).length
  const escalated = cases.filter(c => c.escalated).length
  const aiResolved = cases.filter(c => !c.escalated && c.status !== 'LIVE').length
  const resolutionRate = Math.round((resolved / total) * 100)
  const escalationRate = Math.round((escalated / total) * 100)
  const avgConfidence = Math.round(cases.reduce((a, c) => a + (c.confidence_display || 0), 0) / total)

  return (
    <div style={{ padding: 28, display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>Analytics</h2>
        <span className="t-label" style={{ color: 'var(--text-muted)' }}>DEMO DATA</span>
      </div>

      {/* Metric cards grid */}
      <div className="metric-grid metric-grid--4">
        {/* Resolution Rate */}
        <div className="metric-card">
          <div className="metric-card__label">Resolution Rate</div>
          <div className="metric-card__value" style={{ color: 'var(--ok)' }}>{resolutionRate}%</div>
          <div className="metric-card__sub">{resolved} of {total} cases</div>
        </div>
        {/* Escalation Rate */}
        <div className="metric-card">
          <div className="metric-card__label">Escalation Rate</div>
          <div className="metric-card__value" style={{ color: escalationRate > 30 ? 'var(--danger)' : 'var(--warn)' }}>{escalationRate}%</div>
          <div className="metric-card__sub">{escalated} escalated</div>
        </div>
        {/* Avg AI Confidence */}
        <div className="metric-card">
          <div className="metric-card__label">Avg AI Confidence</div>
          <div className="metric-card__value">{avgConfidence}%</div>
          <div className="metric-card__sub">Across all cases</div>
        </div>
        {/* AI Resolved */}
        <div className="metric-card">
          <div className="metric-card__label">AI Resolved</div>
          <div className="metric-card__value">{aiResolved}</div>
          <div className="metric-card__sub">No human needed</div>
        </div>
      </div>

      {/* Breakdown table */}
      <div className="card" style={{ overflow: 'hidden', padding: 0 }}>
        <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span className="t-label" style={{ color: 'var(--text-tertiary)' }}>Case Breakdown</span>
          <span className="t-label" style={{ color: 'var(--text-muted)' }}>DEMO DATA</span>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Case ID</th><th>Intent</th><th>Status</th><th>Confidence</th>
            </tr>
          </thead>
          <tbody>
            {cases.map(c => (
              <tr key={c.case_id}>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-tertiary)' }}>{c.case_id}</td>
                <td>{c.intent || '—'}</td>
                <td>
                  <span className={`status-pill status-pill--${c.taken_over ? 'ok' : c.escalated ? 'danger' : 'warn'}`}>
                    {c.taken_over ? 'Resolved' : c.escalated ? 'Escalated' : 'Live'}
                  </span>
                </td>
                <td>
                  {typeof c.confidence_display === 'number' ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div className="progress" style={{ flex: 1, maxWidth: 60 }}>
                        <div
                          className="progress__fill"
                          style={{
                            width: c.confidence_display + '%',
                            background: c.confidence_display >= 70
                              ? 'var(--ok)'
                              : c.confidence_display >= 40
                                ? 'var(--warn)'
                                : 'var(--danger)',
                          }}
                        />
                      </div>
                      <span style={{
                        fontSize: 11,
                        fontWeight: 700,
                        fontFamily: 'var(--font-mono)',
                        color: c.confidence_display >= 70 ? 'var(--ok)' : 'var(--danger)',
                      }}>
                        {c.confidence_display}%
                      </span>
                    </div>
                  ) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
