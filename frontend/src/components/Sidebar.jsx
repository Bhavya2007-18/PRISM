import { useNavigate } from 'react-router-dom'
import { useNavContext } from '../context/NavContext'

const PRIMARY_NAV = [
  { id: 'live-session',  label: 'Live Session',  icon: '◉', route: '/' },
  { id: 'overview',      label: 'Overview',      icon: '○', intraNav: 'overview' },
  { id: 'live-sessions', label: 'Live Sessions', icon: '▣', intraNav: 'cases' },
  { id: 'cases',         label: 'Cases',         icon: '☰', intraNav: 'history' },
  { id: 'escalations',   label: 'Escalations',   icon: '⚠', intraNav: 'escalations', badgeKey: 'escalations' },
  { id: 'agents',        label: 'Agents',        icon: '◎', intraNav: 'agents' },
  { id: 'analytics',     label: 'Analytics',     icon: '▦', intraNav: 'analytics' },
]

const SECONDARY_NAV = [
  { id: 'integrations', label: 'Integrations', icon: '⊕' },
  { id: 'settings',     label: 'Settings',     icon: '⊙' },
]

const SYS_STATUS = [
  { id: 'agora',    label: 'Agora' },
  { id: 'ai-agent', label: 'AI Agent' },
  { id: 'tools',    label: 'Tools' },
]

export default function Sidebar({ expanded, onToggle, badges, activeRoute, activeIntraNav }) {
  const navigate   = useNavigate()
  const navCtx     = useNavContext()

  const isItemActive = (item) => {
    if (item.route === '/' && !item.intraNav) return activeRoute === '/'
    if (item.intraNav) return activeIntraNav === item.intraNav
    return false
  }

  const handleNavClick = (item) => {
    if (item.route === '/') {
      navigate('/')
    } else if (item.intraNav) {
      if (activeRoute !== '/agent') navigate('/agent')
      navCtx?.navigate(item.intraNav)
    }
  }

  const labelStyle = {
    overflow: 'hidden',
    whiteSpace: 'nowrap',
    opacity: expanded ? 1 : 0,
    width: expanded ? 'auto' : 0,
    maxWidth: expanded ? 160 : 0,
    transition: 'opacity 200ms ease, width 200ms ease, max-width 200ms ease',
    pointerEvents: 'none',
    flexShrink: 0,
  }

  return (
    <aside className="app-sidebar" style={{ transition: 'all 200ms ease' }}>
      {/* Branding */}
      <div style={{ padding: '20px 18px 16px', borderBottom: '1px solid var(--dark-border)', flexShrink: 0 }}>
        <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.03em', color: 'var(--dark-text-primary)', overflow: 'hidden', whiteSpace: 'nowrap', lineHeight: 1.2 }}>
          {expanded ? 'PRISM' : 'P'}
        </div>
        {expanded && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 6 }}>
            <span className="status-dot status-dot--ok" />
            <span style={{ fontSize: 10, color: 'var(--ok)', fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase' }}>ONLINE</span>
          </div>
        )}
      </div>

      {/* Primary Nav */}
      <div style={{ padding: '12px 10px 0', flex: 1, overflowY: 'auto', overflowX: 'hidden' }}>
        {expanded && (
          <div className="t-label" style={{ color: 'var(--dark-text-muted)', padding: '0 8px 8px', fontSize: 9, letterSpacing: '0.1em' }}>
            WORKSPACE
          </div>
        )}

        {PRIMARY_NAV.map(item => {
          const active     = isItemActive(item)
          const badgeCount = item.badgeKey ? (badges?.[item.badgeKey] ?? 0) : 0
          return (
            <button
              key={item.id}
              onClick={() => handleNavClick(item)}
              className={'nav-item' + (active ? ' nav-item--active' : '')}
              title={!expanded ? item.label : undefined}
              style={{ justifyContent: expanded ? 'flex-start' : 'center', padding: expanded ? '8px 12px' : '8px' }}
            >
              <span style={{ fontSize: 14, flexShrink: 0, lineHeight: 1 }}>{item.icon}</span>
              <span style={labelStyle}>{item.label}</span>
              {badgeCount > 0 && expanded && <span className="nav-item__badge">{badgeCount}</span>}
              {badgeCount > 0 && !expanded && (
                <span style={{ position: 'absolute', top: 4, right: 4, width: 8, height: 8, borderRadius: '50%', background: 'var(--danger)', flexShrink: 0 }} />
              )}
            </button>
          )
        })}

        {/* Divider + Secondary Nav */}
        <div style={{ margin: '12px 0 8px', borderTop: '1px solid var(--dark-border)' }} />
        {expanded && (
          <div className="t-label" style={{ color: 'var(--dark-text-muted)', padding: '0 8px 8px', fontSize: 9, letterSpacing: '0.1em' }}>SETTINGS</div>
        )}
        {SECONDARY_NAV.map(item => (
          <button key={item.id} className="nav-item" title={!expanded ? item.label : undefined}
            style={{ justifyContent: expanded ? 'flex-start' : 'center', padding: expanded ? '8px 12px' : '8px', opacity: 0.7 }}>
            <span style={{ fontSize: 14, flexShrink: 0, lineHeight: 1 }}>{item.icon}</span>
            <span style={labelStyle}>{item.label}</span>
          </button>
        ))}

        {/* System Status */}
        {expanded && (
          <>
            <div style={{ margin: '12px 0 8px', borderTop: '1px solid var(--dark-border)' }} />
            <div className="t-label" style={{ color: 'var(--dark-text-muted)', padding: '0 8px 8px', fontSize: 9, letterSpacing: '0.1em' }}>SYSTEM</div>
            {SYS_STATUS.map(s => (
              <div key={s.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 10px' }}>
                <span className="status-dot status-dot--ok" />
                <span style={{ fontSize: 12, color: 'var(--dark-text-secondary)', fontWeight: 500 }}>{s.label}</span>
              </div>
            ))}
          </>
        )}

        {/* Collapse toggle */}
        <div style={{ margin: '12px 0 4px', borderTop: '1px solid var(--dark-border)' }} />
        <button onClick={onToggle} className="nav-item" title={expanded ? 'Collapse sidebar' : 'Expand sidebar'}
          style={{ justifyContent: expanded ? 'flex-start' : 'center', padding: expanded ? '8px 12px' : '8px', opacity: 0.6 }}>
          <span style={{ fontSize: 12, flexShrink: 0, lineHeight: 1 }}>{expanded ? '←' : '→'}</span>
          <span style={labelStyle}>Collapse</span>
        </button>
      </div>

      {/* User profile */}
      <div style={{ padding: expanded ? '12px 16px' : '12px 10px', borderTop: '1px solid var(--dark-border)', display: 'flex', alignItems: 'center', gap: expanded ? 10 : 0, justifyContent: expanded ? 'flex-start' : 'center', flexShrink: 0 }}>
        <div style={{ width: 28, height: 28, borderRadius: '50%', background: 'var(--dark-3)', border: '1px solid var(--dark-border-strong)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 700, color: 'var(--dark-text-primary)', flexShrink: 0 }}>
          A
        </div>
        {expanded && (
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--dark-text-primary)', lineHeight: 1.2 }}>Agent</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginTop: 2 }}>
              <span className="status-dot status-dot--ok" />
              <span style={{ fontSize: 10, color: 'var(--ok)', fontWeight: 600 }}>Online</span>
            </div>
          </div>
        )}
      </div>
    </aside>
  )
}

export function BottomNav({ activeRoute, activeIntraNav, badges }) {
  const navigate = useNavigate()
  const navCtx   = useNavContext()

  const BOTTOM_NAV_ITEMS = [
    { id: 'live-session', label: 'Session',      icon: '◉', route: '/' },
    { id: 'overview',     label: 'Overview',     icon: '○', intraNav: 'overview' },
    { id: 'cases',        label: 'Live',         icon: '▣', intraNav: 'cases' },
    { id: 'escalations',  label: 'Escalations',  icon: '⚠', intraNav: 'escalations', badgeKey: 'escalations' },
    { id: 'agents',       label: 'Agents',       icon: '◎', intraNav: 'agents' },
  ]

  const isItemActive = (item) => {
    if (item.route === '/' && !item.intraNav) return activeRoute === '/'
    if (item.intraNav) return activeIntraNav === item.intraNav
    return false
  }

  const handleClick = (item) => {
    if (item.route === '/') {
      navigate('/')
    } else if (item.intraNav) {
      if (activeRoute !== '/agent') navigate('/agent')
      navCtx?.navigate(item.intraNav)
    }
  }

  return (
    <nav className="bottom-nav" aria-label="Mobile navigation">
      {BOTTOM_NAV_ITEMS.map(item => {
        const active     = isItemActive(item)
        const badgeCount = item.badgeKey ? (badges?.[item.badgeKey] ?? 0) : 0
        return (
          <button key={item.id} className={'bottom-nav-item' + (active ? ' bottom-nav-item--active' : '')}
            onClick={() => handleClick(item)} aria-label={item.label}>
            <span className="bottom-nav-icon" style={{ position: 'relative' }}>
              {item.icon}
              {badgeCount > 0 && (
                <span style={{ position: 'absolute', top: -4, right: -6, width: 8, height: 8, borderRadius: '50%', background: 'var(--danger)' }} />
              )}
            </span>
            <span>{item.label}</span>
          </button>
        )
      })}
    </nav>
  )
}
