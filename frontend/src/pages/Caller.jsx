import VoiceInterface from '../components/VoiceInterface'

export default function Caller() {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '1fr 420px',
      height: '100%',
      overflow: 'hidden',
    }}>
      {/* Center: Voice interface (orb + transcript + chat) */}
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'flex-start',
        padding: '32px 24px',
        overflow: 'hidden',
        borderRight: '1px solid var(--border)',
      }}>
        <div style={{ width: '100%', maxWidth: 520 }}>
          <VoiceInterface />
        </div>
        <div style={{ marginTop: 'auto', paddingTop: 20, fontSize: 11, color: 'var(--text-muted)' }}>
          <a href="/agent" style={{ color: 'var(--text-muted)', textDecoration: 'none', transition: 'color 0.15s ease' }}
            onMouseEnter={e => e.currentTarget.style.color = 'var(--text-secondary)'}
            onMouseLeave={e => e.currentTarget.style.color = 'var(--text-muted)'}>
            Agent Dashboard →
          </a>
        </div>
      </div>

      {/* Right: Status info panel */}
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        background: 'var(--surface-1)',
      }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
          <span className="t-label" style={{ color: 'var(--text-tertiary)' }}>SESSION INFO</span>
        </div>
        <div style={{ flex: 1, padding: '20px', overflowY: 'auto' }}>
          <div style={{ fontSize: 13, color: 'var(--text-muted)', textAlign: 'center', paddingTop: 40 }}>
            Connect a session to see live AI state and case context.
          </div>
        </div>
      </div>
    </div>
  )
}
