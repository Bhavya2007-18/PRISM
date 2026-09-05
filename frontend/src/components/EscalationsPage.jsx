import EscalationPanel from './EscalationPanel'

export default function EscalationsPage({ cases = [], onTakeOver, demoMode = false }) {
  const escalatedCases = cases.filter(c => c.escalated === true)

  if (escalatedCases.length === 0) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', padding: '60px 20px', textAlign: 'center', gap: 12 }}>
        <div style={{ width: 48, height: 48, borderRadius: '50%', background: 'var(--surface-2)', border: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18 }}>○</div>
        <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-secondary)' }}>No active escalations</div>
        <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>All cases are resolving without human intervention</div>
      </div>
    )
  }

  return (
    <div style={{ padding: 28, display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 4 }}>
        <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)', margin: 0, letterSpacing: '-0.01em' }}>Escalations</h2>
        <span className="status-pill status-pill--danger">{escalatedCases.length} active</span>
        {demoMode && <span className="t-label" style={{ color: 'var(--text-muted)', marginLeft: 'auto' }}>DEMO DATA</span>}
      </div>
      {/* Cards */}
      {escalatedCases.map(c => (
        <EscalationPanel
          key={c.case_id}
          caseData={c}
          onTakeOver={onTakeOver}
        />
      ))}
    </div>
  )
}
