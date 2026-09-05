export default function AgentsPage({ cases = [], demoMode }) {
  const agents = [
    {
      id: 'agent-a',
      name: 'Sarah Chen',
      status: 'online',
      role: 'Senior Agent',
      activeCases: cases.filter(c => c.escalated && !c.taken_over).length,
      resolvedToday: cases.filter(c => c.taken_over).length,
      avgResponseTime: '0:48',
    },
    {
      id: 'agent-b',
      name: 'Raj Patel',
      status: 'online',
      role: 'Support Agent',
      activeCases: 0,
      resolvedToday: 2,
      avgResponseTime: '1:12',
    },
  ]

  return (
    <div style={{ padding: 28, display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>Agents</h2>
        <span className="t-label" style={{ color: 'var(--text-muted)' }}>DEMO DATA</span>
      </div>

      {/* Agent cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {agents.map(agent => (
          <div key={agent.id} className="card" style={{ padding: '20px 24px', display: 'flex', alignItems: 'center', gap: 24 }}>
            {/* Avatar */}
            <div style={{
              width: 44,
              height: 44,
              borderRadius: '50%',
              background: 'var(--dark-3)',
              color: 'var(--dark-text-primary)',
              fontSize: 16,
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}>
              {agent.name.charAt(0)}
            </div>

            {/* Info */}
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 }}>{agent.name}</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span className={'status-dot status-dot--' + (agent.status === 'online' ? 'ok' : 'muted')} />
                <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>{agent.role}</span>
              </div>
            </div>

            {/* Stats */}
            <div style={{ display: 'flex', gap: 32, flexShrink: 0 }}>
              {[
                { label: 'Active Cases', value: agent.activeCases },
                { label: 'Resolved Today', value: agent.resolvedToday },
                { label: 'Avg Response', value: agent.avgResponseTime },
              ].map(stat => (
                <div key={stat.label} style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.03em', color: 'var(--text-primary)', lineHeight: 1 }}>
                    {stat.value}
                  </div>
                  <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase', color: 'var(--text-muted)', marginTop: 4 }}>
                    {stat.label}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
