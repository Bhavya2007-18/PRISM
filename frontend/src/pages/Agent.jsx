import { useState, useEffect } from 'react'
import EscalationPanel from '../components/EscalationPanel'
import CasePanel from '../components/CasePanel'
import AIActionPanel from '../components/AIActionPanel'

const DEMO_CASES = [
  {
    case_id: 'PRISM-1042',
    created_at: new Date(Date.now() - 180000).toISOString(),
    status: 'ESCALATED',
    escalated: true,
    taken_over: false,
    intent: 'Payment Issue',
    issue: 'Payment deducted but order not confirmed',
    issue_summary: 'Paise kat gaye but order confirm nahi hua',
    language: ['Hindi', 'English'],
    transaction_id: 'TX48291',
    amount: 1499,
    payment_status: 'SUCCESS',
    order_status: 'NOT_CONFIRMED',
    confidence_display: 41,
    confidence_label: 'CRITICAL_UNKNOWN',
    confidence_fields: {
      transaction_id: 'HIGH',
      amount: 'HIGH',
      payment_status: 'HIGH',
      order_status: 'HIGH',
      duplicate_charge: 'CRITICAL_UNKNOWN',
    },
    summary: 'Customer reports successful payment of ₹1,499 (TX48291) but the order was never confirmed. AI verified the transaction via API but could not confidently rule out a duplicate charge.',
    reason_for_escalation: 'Unable to confidently determine whether the customer was charged twice. Duplicate charge status is CRITICAL_UNKNOWN after all available verification steps.',
    unverified: ['duplicate_charge'],
  },
  {
    case_id: 'PRISM-1041',
    created_at: new Date(Date.now() - 600000).toISOString(),
    status: 'LIVE',
    escalated: false,
    taken_over: false,
    intent: 'Order Issue',
    issue: 'Order tracking not updating',
    issue_summary: 'Order status stuck on processing',
    language: ['English'],
    confidence_display: 78,
    confidence_label: 'MEDIUM',
  },
  {
    case_id: 'PRISM-1039',
    created_at: new Date(Date.now() - 1800000).toISOString(),
    status: 'RESOLVED',
    escalated: true,
    taken_over: true,
    intent: 'Refund Request',
    issue: 'Refund not received after 7 days',
    issue_summary: 'Refund pending for over a week',
    language: ['Hinglish'],
    confidence_display: 92,
    confidence_label: 'HIGH',
  },
]

const DEMO_CONVERSATION = [
  {
    role: 'user',
    content: 'Bhai mera payment ka issue hai. Paise kat gaye but order confirm nahi hua.',
    time: '2:31 PM',
    delay: 500,
  },
  {
    role: 'assistant',
    content: 'I can help with that. Do you have your transaction ID?',
    time: '2:31 PM',
    delay: 2000,
  },
  {
    role: 'user',
    content: 'Haan, TX48291 hai.',
    time: '2:32 PM',
    delay: 4500,
  },
  {
    role: 'assistant',
    content: 'Let me check that transaction for you.',
    time: '2:32 PM',
    delay: 6500,
    thinking: true,
  },
  {
    role: 'tool-action',
    time: '2:32 PM',
    delay: 8000,
  },
  {
    role: 'assistant',
    content: 'I found your ₹1,499 transaction — payment was successful but the order was not confirmed. I\'m not confident about whether there was a duplicate charge, so let me connect you with a specialist.',
    time: '2:33 PM',
    delay: 13000,
  },
  {
    role: 'escalation',
    delay: 16000,
  },
]

const NAV_ITEMS = [
  { id: 'overview', label: 'Overview', icon: '◉' },
  { id: 'cases', label: 'Live Cases', icon: '◉' },
  { id: 'history', label: 'History', icon: '◉' },
]

const SYSTEM_STATUSES = [
  { id: 'agora', label: 'Agora', status: 'online' },
  { id: 'ai-agent', label: 'AI Agent', status: 'online' },
  { id: 'tools', label: 'Tools', status: 'online' },
  { id: 'escalation', label: 'Escalation', status: 'online' },
]

export default function Agent() {
  const [cases, setCases] = useState([])
  const [activeCaseId, setActiveCaseId] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [backendError, setBackendError] = useState(null)
  const [demoMessages, setDemoMessages] = useState([])
  const [showToolAction, setShowToolAction] = useState(false)
  const [showEscalation, setShowEscalation] = useState(false)
  const [demoMode, setDemoMode] = useState(true)

  useEffect(() => {
    let mounted = true

    async function poll() {
      try {
        const res = await fetch('/cases')
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        if (mounted) {
          const allCases = data.cases || []
          setCases(allCases)
          setDemoMode(allCases.length === 0)
          if (!activeCaseId && allCases.length > 0) {
            const active = allCases.find(c => !c.taken_over) || allCases[0]
            setActiveCaseId(active.case_id)
          }
          setLastUpdated(new Date())
          setBackendError(null)
        }
      } catch (e) {
        if (mounted) {
          setDemoMode(true)
          setCases(DEMO_CASES)
          if (!activeCaseId) setActiveCaseId('PRISM-1042')
          setLastUpdated(new Date())
        }
      }
    }

    poll()
    const interval = setInterval(poll, 3000)
    return () => { mounted = false; clearInterval(interval) }
  }, [activeCaseId])

  useEffect(() => {
    if (!demoMode) return
    setDemoMessages([])
    setShowToolAction(false)
    setShowEscalation(false)

    const timers = DEMO_CONVERSATION.map(msg =>
      setTimeout(() => {
        if (msg.role === 'tool-action') {
          setShowToolAction(true)
        } else if (msg.role === 'escalation') {
          setShowEscalation(true)
        } else {
          setDemoMessages(prev => [...prev, msg])
        }
      }, msg.delay)
    )
    return () => timers.forEach(clearTimeout)
  }, [demoMode, activeCaseId])

  const displayCases = cases.length > 0 ? cases : DEMO_CASES
  const activeCase = displayCases.find(c => c.case_id === activeCaseId) || displayCases[0]
  const activeCases = displayCases.filter(c => !c.taken_over && c.escalated)
  const resolvedCases = displayCases.filter(c => c.taken_over)
  const liveCases = displayCases.filter(c => !c.taken_over)

  const activeNav = 'cases'

  const statusColor = (c) => {
    if (c.taken_over) return 'var(--text-muted)'
    if (c.escalated) return 'var(--danger)'
    if (c.status === 'LIVE') return 'var(--warning)'
    return 'var(--success)'
  }

  const statusIcon = (c) => {
    if (c.taken_over) return '🟢'
    if (c.escalated) return '🔴'
    if (c.status === 'LIVE') return '🟡'
    return '🟢'
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'grid',
      gridTemplateColumns: '220px 1fr',
      background: 'var(--bg-primary)',
    }}>
      {/* Ambient glows */}
      <div style={{
        position: 'fixed', top: '-10%', right: '-5%',
        width: '700px', height: '500px',
        background: 'radial-gradient(ellipse, rgba(124,111,255,0.06), transparent 60%)',
        pointerEvents: 'none', zIndex: 0,
      }} />
      <div style={{
        position: 'fixed', bottom: '-20%', left: '10%',
        width: '600px', height: '500px',
        background: 'radial-gradient(ellipse, rgba(96,165,250,0.04), transparent 60%)',
        pointerEvents: 'none', zIndex: 0,
      }} />

      {/* ──────────── LEFT SIDEBAR ──────────── */}
      <aside style={{
        background: 'linear-gradient(180deg, var(--bg-secondary) 0%, var(--bg-primary) 100%)',
        borderRight: '1px solid var(--border)',
        padding: '28px 0',
        display: 'flex',
        flexDirection: 'column',
        gap: 28,
        position: 'sticky',
        top: 0,
        height: '100vh',
        zIndex: 5,
      }}>
        {/* Logo */}
        <div style={{ padding: '0 24px' }}>
          <div style={{
            fontSize: 24,
            fontWeight: 800,
            letterSpacing: -1,
            background: 'var(--gradient-accent)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
            lineHeight: 1,
            marginBottom: 4,
          }}>
            PRISM
          </div>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}>
            <span className="status-dot status-dot--connected" />
            <span style={{ fontSize: 10, color: 'var(--success)', fontWeight: 600, letterSpacing: 1 }}>
              SYSTEM ONLINE
            </span>
          </div>
        </div>

        <div style={{ borderTop: '1px solid var(--border)' }} />

        {/* Navigation */}
        <div style={{ padding: '0 16px' }}>
          <div style={{
            fontSize: 9,
            fontWeight: 700,
            letterSpacing: 2.5,
            color: 'var(--text-muted)',
            padding: '0 8px 12px',
            textTransform: 'uppercase',
          }}>
            Navigation
          </div>
          <nav style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {NAV_ITEMS.map(item => (
              <button
                key={item.id}
                onClick={() => {}}
                style={{
                  padding: '10px 12px',
                  background: activeNav === item.id ? 'rgba(124,111,255,0.1)' : 'transparent',
                  border: activeNav === item.id ? '1px solid var(--border-accent)' : '1px solid transparent',
                  borderRadius: 8,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  cursor: 'pointer',
                  fontFamily: 'inherit',
                  transition: 'all 0.2s ease',
                }}
              >
                <span style={{
                  fontSize: 8,
                  color: activeNav === item.id ? 'var(--accent)' : 'var(--text-muted)',
                  lineHeight: 1,
                }}>
                  {item.icon}
                </span>
                <span style={{
                  fontSize: 13,
                  fontWeight: activeNav === item.id ? 600 : 400,
                  color: activeNav === item.id ? 'var(--text-primary)' : 'var(--text-secondary)',
                }}>
                  {item.label}
                </span>
                {activeCases.length > 0 && item.id === 'cases' && (
                  <span style={{
                    marginLeft: 'auto',
                    padding: '1px 7px',
                    fontSize: 10,
                    fontWeight: 700,
                    color: '#fff',
                    background: 'var(--danger)',
                    borderRadius: 10,
                  }}>
                    {activeCases.length}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>

        <div style={{ borderTop: '1px solid var(--border)' }} />

        {/* System Status */}
        <div style={{ padding: '0 16px', marginTop: 'auto' }}>
          <div style={{
            fontSize: 9,
            fontWeight: 700,
            letterSpacing: 2.5,
            color: 'var(--text-muted)',
            padding: '0 8px 12px',
            textTransform: 'uppercase',
          }}>
            System
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {SYSTEM_STATUSES.map(s => (
              <div key={s.id} style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '6px 12px',
                borderRadius: 6,
              }}>
                <span className={`status-dot status-dot--${s.status === 'online' ? 'connected' : 'danger'}`} />
                <span style={{
                  fontSize: 12,
                  color: s.status === 'online' ? 'var(--text-secondary)' : 'var(--danger)',
                  fontWeight: 500,
                }}>
                  {s.label}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Footer link */}
        <div style={{ padding: '0 24px 0' }}>
          <a href="/" style={{
            fontSize: 11,
            color: 'var(--text-muted)',
            textDecoration: 'none',
            display: 'block',
            padding: '8px 0',
            borderTop: '1px solid var(--border)',
          }}
          onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent-soft)'}
          onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
          >
            ← Open Caller UI
          </a>
        </div>
      </aside>

      {/* ──────────── MAIN CONTENT ──────────── */}
      <main style={{
        padding: '24px 28px 28px',
        display: 'flex',
        flexDirection: 'column',
        gap: 20,
        minWidth: 0,
        position: 'relative',
        zIndex: 1,
      }}>
        {/* Top header bar */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <div>
            <h1 style={{
              fontSize: 20,
              fontWeight: 700,
              color: 'var(--text-primary)',
              margin: 0,
              letterSpacing: -0.3,
            }}>
              Human Agent Dashboard
            </h1>
            <p style={{
              fontSize: 12,
              color: 'var(--text-secondary)',
              margin: '4px 0 0 0',
            }}>
              {demoMode
                ? 'Demo mode — showing sample cases. Connect backend for live data.'
                : 'Cases escalated by PRISM that require human attention.'}
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
            {/* Stats mini */}
            <div style={{ display: 'flex', gap: 20 }}>
              {[
                { label: 'Active', value: activeCases.length, color: 'var(--danger)', dot: true },
                { label: 'Live', value: liveCases.length, color: 'var(--warning)' },
                { label: 'Resolved', value: resolvedCases.length, color: 'var(--success)' },
              ].map(stat => (
                <div key={stat.label} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  {stat.dot && <span className="status-dot status-dot--danger" />}
                  <div style={{ textAlign: 'right' }}>
                    <div style={{
                      fontSize: 16,
                      fontWeight: 700,
                      color: stat.color,
                      lineHeight: 1,
                    }}>
                      {stat.value}
                    </div>
                    <div style={{
                      fontSize: 10,
                      color: 'var(--text-muted)',
                      marginTop: 2,
                      letterSpacing: 0.5,
                    }}>
                      {stat.label.toUpperCase()}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '8px 14px',
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: 10,
            }}>
              <span className={`status-dot status-dot--${backendError ? 'danger' : 'connected'}`} />
              <span style={{ fontSize: 11, color: 'var(--text-secondary)', fontWeight: 500 }}>
                {backendError ? 'Backend offline' : lastUpdated ? `Updated ${lastUpdated.toLocaleTimeString()}` : 'Connecting...'}
              </span>
            </div>
          </div>
        </div>

        {/* ──── 3-COLUMN LAYOUT ──── */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '280px minmax(0, 1fr) 340px',
          gap: 20,
          alignItems: 'start',
          flex: 1,
          minHeight: 0,
        }}>

          {/* ════════════ COLUMN 1: CASES LIST ════════════ */}
          <section className="glass-panel" style={{
            padding: '18px 16px',
            display: 'flex',
            flexDirection: 'column',
            gap: 12,
            position: 'sticky',
            top: 24,
            maxHeight: 'calc(100vh - 180px)',
            overflow: 'hidden',
          }}>
            <div style={{
              padding: '0 8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}>
              <div className="label-text">Cases</div>
              <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                {displayCases.length} total
              </span>
            </div>

            <div style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 6,
              overflowY: 'auto',
              paddingRight: 4,
            }}>
              {displayCases.map(c => {
                const isActive = c.case_id === activeCaseId
                return (
                  <button
                    key={c.case_id}
                    onClick={() => setActiveCaseId(c.case_id)}
                    style={{
                      padding: '12px 14px',
                      background: isActive
                        ? 'linear-gradient(135deg, rgba(124,111,255,0.12) 0%, rgba(124,111,255,0.04) 100%)'
                        : 'transparent',
                      border: `1px solid ${isActive ? 'var(--border-accent)' : 'var(--border)'}`,
                      borderRadius: 10,
                      cursor: 'pointer',
                      textAlign: 'left',
                      fontFamily: 'inherit',
                      transition: 'all 0.2s ease',
                      opacity: c.taken_over ? 0.7 : 1,
                    }}
                    onMouseEnter={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.background = 'var(--bg-card-hover)'
                        e.currentTarget.style.borderColor = 'var(--border-strong)'
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.background = 'transparent'
                        e.currentTarget.style.borderColor = 'var(--border)'
                      }
                    }}
                  >
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      marginBottom: 6,
                    }}>
                      <span style={{ fontSize: 10 }}>{statusIcon(c)}</span>
                      <span className="monospace" style={{
                        fontSize: 11,
                        fontWeight: 600,
                        color: statusColor(c),
                      }}>
                        {c.case_id}
                      </span>
                    </div>
                    <div style={{
                      fontSize: 13,
                      fontWeight: 500,
                      color: 'var(--text-primary)',
                      marginBottom: 3,
                      lineHeight: 1.4,
                    }}>
                      {c.issue_summary || c.issue || c.intent || 'Case'}
                    </div>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                    }}>
                      <span style={{
                        fontSize: 10,
                        color: 'var(--text-muted)',
                      }}>
                        {c.language?.join(' + ') || 'Unknown lang'}
                      </span>
                      {typeof c.confidence_display === 'number' && (
                        <span className="monospace" style={{
                          fontSize: 10,
                          fontWeight: 700,
                          color: c.confidence_display >= 60 ? 'var(--success)' : 'var(--danger)',
                        }}>
                          {c.confidence_display}%
                        </span>
                      )}
                    </div>
                  </button>
                )
              })}
            </div>
          </section>

          {/* ════════════ COLUMN 2: LIVE CONVERSATION ════════════ */}
          <section className="glass-panel" style={{
            padding: '24px 24px 20px',
            display: 'flex',
            flexDirection: 'column',
            gap: 20,
            maxHeight: 'calc(100vh - 180px)',
            overflow: 'hidden',
          }}>
            {/* Conversation header */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              paddingBottom: 16,
              borderBottom: '1px solid var(--border)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                <div className="label-text">Live Conversation</div>
                {activeCase && (
                  <span className="monospace" style={{
                    fontSize: 11,
                    padding: '3px 10px',
                    borderRadius: 20,
                    background: activeCase.taken_over
                      ? 'rgba(52,211,153,0.08)'
                      : activeCase.escalated
                        ? 'rgba(248,113,113,0.1)'
                        : 'rgba(251,191,36,0.1)',
                    color: activeCase.taken_over
                      ? 'var(--success)'
                      : activeCase.escalated
                        ? 'var(--danger)'
                        : 'var(--warning)',
                    fontWeight: 700,
                    letterSpacing: 0.5,
                  }}>
                    {activeCase.taken_over ? 'RESOLVED' : activeCase.escalated ? 'ESCALATED' : activeCase.status || 'LIVE'}
                  </span>
                )}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span className="status-dot status-dot--connected" />
                <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                  {activeCase ? `Channel: ${activeCase.case_id.toLowerCase()}` : 'Monitoring...'}
                </span>
              </div>
            </div>

            {/* Conversation messages */}
            <div style={{
              flex: 1,
              overflowY: 'auto',
              display: 'flex',
              flexDirection: 'column',
              gap: 18,
              paddingRight: 8,
            }}>
              {(demoMode ? demoMessages : []).length === 0 && (
                <div style={{
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: '60px 20px',
                  gap: 12,
                  color: 'var(--text-muted)',
                }}>
                  <div style={{
                    width: 56, height: 56,
                    borderRadius: '50%',
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--border)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 22,
                  }}>
                    🤖
                  </div>
                  <div style={{ fontSize: 13, fontWeight: 500 }}>
                    {demoMode ? 'Waiting for conversation to begin...' : 'No live transcript yet'}
                  </div>
                  <div style={{ fontSize: 11, textAlign: 'center', maxWidth: 320, lineHeight: 1.6 }}>
                    {demoMode
                      ? 'Demo conversation will play automatically in a few seconds.'
                      : 'Once PRISM transcribes the call, messages will appear here in real time.'}
                  </div>
                </div>
              )}

              {(demoMode ? demoMessages : []).map((msg, i) => (
                <div key={i} className="fade-in" style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 6,
                  alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  maxWidth: '82%',
                }}>
                  {/* Avatar + label */}
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  }}>
                    <span style={{
                      fontSize: msg.role === 'assistant' ? 14 : 16,
                    }}>
                      {msg.role === 'user' ? '👤' : '🤖'}
                    </span>
                    <span style={{
                      fontSize: 10,
                      fontWeight: 700,
                      letterSpacing: 1.5,
                      color: msg.role === 'user' ? 'var(--text-muted)' : 'var(--accent-soft)',
                    }}>
                      {msg.role === 'user' ? 'USER' : 'PRISM'}
                    </span>
                    <span style={{
                      fontSize: 10,
                      color: 'var(--text-muted)',
                    }}>
                      {msg.time}
                    </span>
                  </div>

                  {/* Message bubble */}
                  <div style={{
                    padding: '12px 16px',
                    borderRadius: msg.role === 'user' ? '14px 14px 4px 14px' : '14px 14px 14px 4px',
                    background: msg.role === 'user'
                      ? 'linear-gradient(135deg, rgba(124,111,255,0.18) 0%, rgba(124,111,255,0.06) 100%)'
                      : 'var(--bg-elevated)',
                    border: `1px solid ${msg.role === 'user' ? 'var(--border-accent)' : 'var(--border)'}`,
                  }}>
                    <p style={{
                      margin: 0,
                      fontSize: 14,
                      lineHeight: 1.65,
                      color: 'var(--text-primary)',
                      fontWeight: msg.role === 'assistant' ? 500 : 400,
                    }}>
                      {msg.content}
                    </p>
                    {msg.thinking && (
                      <div style={{
                        marginTop: 8,
                        paddingTop: 8,
                        borderTop: '1px solid var(--border)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                      }}>
                        <span style={{ fontSize: 11 }}>🔧</span>
                        <span style={{
                          fontSize: 11,
                          color: 'var(--accent-soft)',
                          fontWeight: 500,
                          fontStyle: 'italic',
                        }}>
                          Checking transaction...
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {/* Tool action card */}
              {showToolAction && (
                <div className="slide-up" style={{ alignSelf: 'stretch', padding: '4px 0' }}>
                  <AIActionPanel compact />
                </div>
              )}
            </div>

            {/* Escalation panel inline */}
            {showEscalation && activeCase && (
              <div className="slide-up" style={{
                paddingTop: 8,
                borderTop: '1px solid var(--border)',
              }}>
                <EscalationPanel
                  caseData={activeCase}
                  compact
                  onTakeOver={(id) => {
                    setCases(prev => prev.map(p =>
                      p.case_id === id ? { ...p, taken_over: true, status: 'TAKEN_OVER' } : p
                    ))
                  }}
                />
              </div>
            )}

            {/* Bottom input bar (visual only) */}
            <div style={{
              padding: '12px 0 0',
              borderTop: showEscalation ? 'none' : '1px solid var(--border)',
              display: 'flex',
              gap: 10,
              alignItems: 'center',
            }}>
              <div style={{
                flex: 1,
                padding: '10px 14px',
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border)',
                borderRadius: 10,
                fontSize: 12,
                color: 'var(--text-muted)',
              }}>
                {activeCase?.taken_over
                  ? 'You are now speaking with the customer...'
                  : showEscalation
                    ? 'Click "TAKE OVER" above to join the call'
                    : 'PRISM is handling this conversation'}
              </div>
              {activeCase?.taken_over && (
                <button
                  className="btn-primary"
                  style={{ padding: '10px 18px', fontSize: 12 }}
                  disabled
                >
                  🎙 On call
                </button>
              )}
            </div>
          </section>

          {/* ════════════ COLUMN 3: CASE INTEL ════════════ */}
          <section style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 20,
            position: 'sticky',
            top: 24,
            maxHeight: 'calc(100vh - 180px)',
            overflow: 'hidden',
          }}>
            {/* Active case header */}
            <div className={activeCase?.escalated && !activeCase?.taken_over ? 'glass-panel-danger' : 'glass-panel-accent'} style={{
              padding: '18px 20px',
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: 10,
              }}>
                <div className="label-text">Active Case</div>
                {activeCase && !activeCase.taken_over && (
                  <span style={{
                    fontSize: 20,
                    filter: activeCase.escalated ? 'none' : 'grayscale(0.3)',
                  }}>
                    {activeCase.escalated ? '🔴' : '🟡'}
                  </span>
                )}
              </div>
              {activeCase ? (
                <>
                  <div style={{
                    fontSize: 16,
                    fontWeight: 700,
                    color: 'var(--text-primary)',
                    marginBottom: 6,
                    letterSpacing: -0.2,
                  }}>
                    {activeCase.issue || activeCase.intent || 'Case Details'}
                  </div>
                  <div className="monospace" style={{
                    fontSize: 11,
                    color: 'var(--text-muted)',
                  }}>
                    {activeCase.case_id} · Opened {new Date(activeCase.created_at).toLocaleTimeString()}
                  </div>
                </>
              ) : (
                <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                  Select a case from the list
                </div>
              )}
            </div>

            {/* Structured case intel */}
            <div className="glass-panel" style={{
              padding: '20px 20px 24px',
              overflowY: 'auto',
              flex: 1,
            }}>
              <div className="label-text" style={{ marginBottom: 16 }}>Case Intelligence</div>
              {activeCase ? (
                <CasePanel caseData={activeCase} />
              ) : (
                <div style={{
                  padding: '40px 20px',
                  textAlign: 'center',
                  color: 'var(--text-muted)',
                  fontSize: 13,
                }}>
                  No case selected
                </div>
              )}
            </div>
          </section>
        </div>
      </main>
    </div>
  )
}
