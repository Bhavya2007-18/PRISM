export default function TopBar({ title = 'PRISM', demoMode = false, connectionStatus = 'ok', lastUpdated = null, onToggleSidebar }) {
  const isOk = connectionStatus === 'ok'
  const isWarn = connectionStatus === 'warn'
  const statusDotClass = isOk ? 'status-dot--ok' : isWarn ? 'status-dot--warn' : 'status-dot--danger'
  const connectionLabel = connectionStatus === 'offline' ? 'Offline' : 'Connected'

  return (
    <header className="app-topbar">
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 10 }}>
        {onToggleSidebar && (
          <button onClick={onToggleSidebar}
            style={{ background: 'transparent', border: 'none', cursor: 'pointer', padding: '6px', borderRadius: 'var(--r-md)', color: 'var(--text-tertiary)', display: 'flex', alignItems: 'center', transition: 'background var(--t-micro)' }}
            onMouseEnter={e => e.currentTarget.style.background = 'var(--surface-2)'}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            aria-label="Toggle sidebar">
            <svg width="15" height="15" viewBox="0 0 16 16" fill="none">
              <rect x="1" y="3.5" width="14" height="1.2" rx="0.6" fill="currentColor" />
              <rect x="1" y="7.4" width="14" height="1.2" rx="0.6" fill="currentColor" />
              <rect x="1" y="11.3" width="14" height="1.2" rx="0.6" fill="currentColor" />
            </svg>
          </button>
        )}
        {/* Display font for page title — editorial identity */}
        <span style={{ fontFamily: 'var(--font-display)', fontSize: '18px', fontWeight: 400, color: 'var(--text-primary)', letterSpacing: '-0.01em', lineHeight: 1 }}>
          {title}
        </span>
        {demoMode && (
          <span className="t-label-sm" style={{ padding: '2px 7px', background: 'var(--surface-2)', border: '1px solid var(--border)', borderRadius: 'var(--r-full)', color: 'var(--text-muted)' }}>
            DEMO
          </span>
        )}
      </div>

      <div style={{ flexShrink: 0, display: 'flex', gap: 12, alignItems: 'center' }}>
        {/* Agora connection indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '5px 11px', background: 'var(--surface-1)', border: '1px solid var(--border)', borderRadius: 'var(--r-full)' }}>
          <span className={`status-dot ${statusDotClass}${isOk ? ' status-dot--breathe' : ''}`} />
          <span style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 400, letterSpacing: '0.01em' }}>
            Agora · {connectionLabel}
          </span>
        </div>

        {/* Notification */}
        <button style={{ background: 'transparent', border: 'none', cursor: 'pointer', padding: '6px', borderRadius: 'var(--r-md)', fontSize: 14, lineHeight: 1, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', transition: 'background var(--t-micro)' }}
          onMouseEnter={e => e.currentTarget.style.background = 'var(--surface-2)'}
          onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
          aria-label="Notifications">
          🔔
        </button>

        {/* User chip */}
        <div style={{ width: 28, height: 28, borderRadius: '50%', background: 'var(--dark-3)', color: 'var(--dark-text-primary)', fontSize: 11, fontWeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          A
        </div>
      </div>
    </header>
  )
}
