import VoiceInterface from '../components/VoiceInterface'

export default function Caller() {
  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '40px 20px',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Ambient background glow */}
      <div style={{
        position: 'absolute',
        top: '-10%',
        left: '50%',
        transform: 'translateX(-50%)',
        width: '800px',
        height: '600px',
        background: 'radial-gradient(ellipse, var(--accent-glow) 0%, transparent 60%)',
        opacity: 0.5,
        pointerEvents: 'none',
        zIndex: 0,
      }} />

      {/* Main card */}
      <div
        className="glass-panel-accent"
        style={{
          position: 'relative',
          zIndex: 1,
        }}
      >
        <VoiceInterface />
      </div>

      {/* Bottom corner links */}
      <div style={{
        position: 'absolute',
        bottom: 24,
        right: 32,
        display: 'flex',
        gap: 20,
        zIndex: 2,
      }}>
        <a href="/agent" style={{
          fontSize: 11,
          color: 'var(--text-muted)',
          textDecoration: 'none',
          fontWeight: 500,
          letterSpacing: 0.5,
          transition: 'color 0.2s ease',
        }}
        onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent-soft)'}
        onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
        >
          Human agent? Open dashboard →
        </a>
      </div>
    </div>
  )
}
