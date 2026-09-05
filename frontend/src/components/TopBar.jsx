import React from 'react';

export default function TopBar({
  title = 'PRISM',
  demoMode = false,
  connectionStatus = 'ok',
  lastUpdated = null,
  onToggleSidebar,
}) {
  const statusDotClass =
    connectionStatus === 'ok'
      ? 'status-dot--ok'
      : connectionStatus === 'warn'
      ? 'status-dot--warn'
      : 'status-dot--danger';

  const connectionLabel =
    connectionStatus === 'offline' ? 'Agora ● Offline' : 'Agora ● Connected';

  return (
    <header className="app-topbar">
      {/* Left section */}
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 10 }}>
        {onToggleSidebar && (
          <button
            onClick={onToggleSidebar}
            style={{
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              padding: '6px',
              borderRadius: 'var(--r-md)',
              color: 'var(--text-secondary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'background var(--t-fast)',
              lineHeight: 1,
            }}
            onMouseEnter={e => (e.currentTarget.style.background = 'var(--surface-2)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
            aria-label="Toggle sidebar"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <rect x="1" y="3.5" width="14" height="1.5" rx="0.75" fill="currentColor" />
              <rect x="1" y="7.25" width="14" height="1.5" rx="0.75" fill="currentColor" />
              <rect x="1" y="11" width="14" height="1.5" rx="0.75" fill="currentColor" />
            </svg>
          </button>
        )}

        <span
          style={{
            fontSize: '15px',
            fontWeight: 600,
            color: 'var(--text-primary)',
            letterSpacing: '-0.01em',
          }}
        >
          {title}
        </span>

        {demoMode && (
          <span
            className="t-label"
            style={{ color: 'var(--text-muted)', marginLeft: '10px' }}
          >
            DEMO
          </span>
        )}
      </div>

      {/* Right section */}
      <div
        style={{
          flexShrink: 0,
          display: 'flex',
          gap: '16px',
          alignItems: 'center',
        }}
      >
        {/* Connection indicator */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '7px',
            padding: '6px 12px',
            background: 'var(--surface-1)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--r-md)',
          }}
        >
          <span className={`status-dot ${statusDotClass}`} />
          <span
            style={{
              fontSize: '11px',
              color: 'var(--text-tertiary)',
              fontWeight: 500,
            }}
          >
            {connectionLabel}
          </span>
        </div>

        {/* Notification bell */}
        <button
          style={{
            background: 'transparent',
            border: 'none',
            cursor: 'pointer',
            padding: '6px',
            borderRadius: 'var(--r-md)',
            fontSize: '16px',
            lineHeight: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'background var(--t-fast)',
          }}
          onMouseEnter={e => (e.currentTarget.style.background = 'var(--surface-2)')}
          onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
          aria-label="Notifications"
        >
          🔔
        </button>

        {/* User chip */}
        <div
          style={{
            width: '28px',
            height: '28px',
            borderRadius: '50%',
            background: 'var(--dark-3)',
            color: 'var(--dark-text-primary)',
            fontSize: '11px',
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          A
        </div>
      </div>
    </header>
  );
}
