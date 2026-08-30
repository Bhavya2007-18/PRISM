import { useState, useEffect, useRef } from 'react'
import AgoraRTC from 'agora-rtc-sdk-ng'
import EscalationPanel from '../components/EscalationPanel'
import CasePanel from '../components/CasePanel'
import AIActionPanel from '../components/AIActionPanel'
import { getApiUrl } from '../lib/api'
import ThinkingPanel from '../components/ThinkingPanel'

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
  const [agentAudioConnected, setAgentAudioConnected] = useState(false)
  const [agentMuted, setAgentMuted] = useState(false)
  const agentClientRef = useRef(null)
  const agentMicRef = useRef(null)
  const [liveVoiceState, setLiveVoiceState] = useState('IDLE')
  const [liveAiState, setLiveAiState] = useState(null)

  const handleAgentAgoraJoin = async (targetChannel = 'prism-demo') => {
    try {
      const AGENT_UID = 88888
      const tokenResp = await fetch(getApiUrl(`/token?channel=${targetChannel}&uid=${AGENT_UID}`))
      if (!tokenResp.ok) return
      const contentType = tokenResp.headers.get('content-type') || ''
      if (!contentType.includes('application/json')) return
      const tokenData = await tokenResp.json()

      const client = AgoraRTC.createClient({ mode: 'rtc', codec: 'vp8' })
      agentClientRef.current = client

      client.on('user-published', async (user, mediaType) => {
        await client.subscribe(user, mediaType)
        if (mediaType === 'audio') {
          user.audioTrack?.play()
        }
      })

      await client.join(tokenData.app_id, targetChannel, tokenData.token, AGENT_UID)
      
      try {
        const micTrack = await AgoraRTC.createMicrophoneAudioTrack({ encoderConfig: 'speech_standard' })
        agentMicRef.current = micTrack
        await client.publish([micTrack])
      } catch (e) {
        console.warn('[Agent Dashboard] Optional mic error:', e)
      }

      setAgentAudioConnected(true)
    } catch (e) {
      console.warn('[Agent Dashboard] Agora takeover join error:', e)
    }
  }

  const disconnectAgentAudio = async () => {
    try {
      agentMicRef.current?.close()
      await agentClientRef.current?.leave()
    } catch (e) {}
    agentClientRef.current = null
    agentMicRef.current = null
    setAgentAudioConnected(false)
  }

  const toggleAgentMute = () => {
    if (agentMicRef.current) {
      const newMuted = !agentMuted
      agentMicRef.current.setEnabled(!newMuted)
      setAgentMuted(newMuted)
    }
  }

  useEffect(() => {
    let mounted = true

    async function poll() {
      try {
        const res = await fetch(getApiUrl('/cases'))
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const contentType = res.headers.get('content-type') || ''
        if (!contentType.includes('application/json')) throw new Error('Non-JSON response from backend')
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

  // Poll /state/{channel} for live AI state when a case is active
  useEffect(() => {
    if (!activeCaseId || demoMode) return
    let mounted = true
    // Derive channel from case_id: use prism-text as default for text cases
    const channel = 'prism-text'
    const pollState = async () => {
      try {
        const res = await fetch(getApiUrl(`/state/${channel}`))
        if (!res.ok) return
        const ct = res.headers.get('content-type') || ''
        if (!ct.includes('application/json')) return
        const data = await res.json()
        if (mounted) {
          setLiveVoiceState(data.voice_state || 'IDLE')
          setLiveAiState(data.ai_state || null)
        }
      } catch {}
    }
    pollState()
    const si = setInterval(pollState, 2000)
    return () => { mounted = false; clearInterval(si) }
  }, [activeCaseId, demoMode])

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

  const [activeNav, setActiveNav] = useState('cases')

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
                onClick={() => setActiveNav(item.id)}
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

        {/* ──── OVERVIEW PAGE ──── */}
        {activeNav === 'overview' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
              {[
                { label: 'Total Cases Today', value: displayCases.length, icon: '📋', color: 'var(--accent)' },
                { label: 'Escalated', value: activeCases.length, icon: '🔴', color: 'var(--danger)' },
                { label: 'Resolved', value: resolvedCases.length, icon: '✅', color: 'var(--success)' },
                { label: 'Avg Confidence', value: `${Math.round(displayCases.reduce((a, c) => a + (c.confidence_display || 0), 0) / (displayCases.length || 1))}%`, icon: '📊', color: 'var(--warning)' },
              ].map(stat => (
                <div key={stat.label} className="glass-panel" style={{ padding: '20px 24px' }}>
                  <div style={{ fontSize: 28, marginBottom: 8 }}>{stat.icon}</div>
                  <div style={{ fontSize: 28, fontWeight: 800, color: stat.color, lineHeight: 1 }}>{stat.value}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6, letterSpacing: 0.5 }}>{stat.label.toUpperCase()}</div>
                </div>
              ))}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
              <div className="glass-panel" style={{ padding: '20px 24px' }}>
                <div className="label-text" style={{ marginBottom: 16 }}>System Health</div>
                {SYSTEM_STATUSES.map(s => (
                  <div key={s.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
                    <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{s.label}</span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span className="status-dot status-dot--connected" />
                      <span style={{ fontSize: 11, color: 'var(--success)', fontWeight: 600 }}>ONLINE</span>
                    </div>
                  </div>
                ))}
              </div>
              <div className="glass-panel" style={{ padding: '20px 24px' }}>
                <div className="label-text" style={{ marginBottom: 16 }}>Recent Activity</div>
                {displayCases.slice(0, 5).map(c => (
                  <div key={c.case_id}
                    onClick={() => { setActiveNav('cases'); setActiveCaseId(c.case_id) }}
                    style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 0', borderBottom: '1px solid var(--border)', cursor: 'pointer' }}
                    onMouseEnter={e => e.currentTarget.style.opacity = '0.75'}
                    onMouseLeave={e => e.currentTarget.style.opacity = '1'}>
                    <span style={{ fontSize: 14 }}>{c.taken_over ? '🟢' : c.escalated ? '🔴' : '🟡'}</span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{c.issue_summary || c.issue || c.intent}</div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'monospace' }}>{c.case_id}</div>
                    </div>
                    {typeof c.confidence_display === 'number' && (
                      <span style={{ fontSize: 11, fontWeight: 700, color: c.confidence_display >= 60 ? 'var(--success)' : 'var(--danger)', fontFamily: 'monospace' }}>{c.confidence_display}%</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ──── HISTORY PAGE ──── */}
        {activeNav === 'history' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: 'var(--text-primary)' }}>Case History</h2>
              <span style={{ fontSize: 12, color: 'var(--text-muted)', padding: '3px 10px', background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 20 }}>{displayCases.length} total</span>
            </div>
            <div className="glass-panel" style={{ padding: 0, overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border)', background: 'var(--bg-elevated)' }}>
                    {['Case ID', 'Issue', 'Intent', 'Amount', 'Status', 'Confidence', 'Language', 'Time'].map(h => (
                      <th key={h} style={{ padding: '12px 16px', textAlign: 'left', fontSize: 10, fontWeight: 700, letterSpacing: 1.5, color: 'var(--text-muted)', textTransform: 'uppercase', whiteSpace: 'nowrap' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {displayCases.map(c => (
                    <tr key={c.case_id}
                      onClick={() => { setActiveNav('cases'); setActiveCaseId(c.case_id) }}
                      style={{ borderBottom: '1px solid var(--border)', cursor: 'pointer', transition: 'background 0.15s' }}
                      onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-card-hover, rgba(255,255,255,0.03))'}
                      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                      <td style={{ padding: '14px 16px' }}>
                        <span style={{ fontFamily: 'monospace', fontSize: 12, fontWeight: 600, color: c.escalated && !c.taken_over ? 'var(--danger)' : 'var(--text-secondary)' }}>{c.case_id}</span>
                      </td>
                      <td style={{ padding: '14px 16px', fontSize: 13, color: 'var(--text-primary)', maxWidth: 200 }}>
                        <div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{c.issue || c.issue_summary || '—'}</div>
                      </td>
                      <td style={{ padding: '14px 16px', fontSize: 12, color: 'var(--text-secondary)' }}>{c.intent || '—'}</td>
                      <td style={{ padding: '14px 16px', fontSize: 12, fontFamily: 'monospace', color: 'var(--text-primary)' }}>{c.amount ? `₹${c.amount.toLocaleString()}` : '—'}</td>
                      <td style={{ padding: '14px 16px' }}>
                        <span style={{
                          fontSize: 10, fontWeight: 700, padding: '3px 8px', borderRadius: 6,
                          background: c.taken_over ? 'rgba(52,211,153,0.12)' : c.escalated ? 'rgba(248,113,113,0.12)' : 'rgba(251,191,36,0.12)',
                          color: c.taken_over ? 'var(--success)' : c.escalated ? 'var(--danger)' : 'var(--warning)',
                        }}>
                          {c.taken_over ? 'RESOLVED' : c.escalated ? 'ESCALATED' : c.status || 'LIVE'}
                        </span>
                      </td>
                      <td style={{ padding: '14px 16px' }}>
                        {typeof c.confidence_display === 'number' ? (
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <div style={{ flex: 1, height: 4, background: 'var(--bg-elevated)', borderRadius: 2, overflow: 'hidden', maxWidth: 60 }}>
                              <div style={{ width: `${c.confidence_display}%`, height: '100%', background: c.confidence_display >= 60 ? 'var(--success)' : 'var(--danger)', borderRadius: 2 }} />
                            </div>
                            <span style={{ fontSize: 11, fontFamily: 'monospace', fontWeight: 700, color: c.confidence_display >= 60 ? 'var(--success)' : 'var(--danger)' }}>{c.confidence_display}%</span>
                          </div>
                        ) : '—'}
                      </td>
                      <td style={{ padding: '14px 16px', fontSize: 11, color: 'var(--text-muted)' }}>{c.language?.join(' / ') || '—'}</td>
                      <td style={{ padding: '14px 16px', fontSize: 11, color: 'var(--text-muted)', fontFamily: 'monospace', whiteSpace: 'nowrap' }}>
                        {c.created_at ? new Date(c.created_at).toLocaleTimeString() : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ──── CASES PAGE (3-column layout) ──── */}
        {activeNav === 'cases' && <div style={{
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
              {/* Compute messages to display: demo mode uses animated messages, live mode uses case history */}
              {(() => {
                const liveHistory = (!demoMode && activeCase?.conversation_history) ? activeCase.conversation_history : []
                const displayMessages = demoMode ? demoMessages : liveHistory
                return (
                  <>
                    {displayMessages.length === 0 && (
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
                    {displayMessages.filter(msg =>
                      msg.content &&
                      typeof msg.content === 'string' &&
                      msg.content.trim().length > 0 &&
                      msg.role !== 'tool' &&
                      msg.role !== 'system'
                    ).map((msg, i) => (
                      <div key={i} className="fade-in" style={{
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 6,
                        alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                        maxWidth: '82%',
                      }}>
                        <div style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 8,
                          alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                        }}>
                          <span style={{ fontSize: msg.role === 'assistant' ? 14 : 16 }}>
                            {msg.role === 'user' ? '👤' : '🤖'}
                          </span>
                          <span style={{
                            fontSize: 10, fontWeight: 700, letterSpacing: 1.5,
                            color: msg.role === 'user' ? 'var(--text-muted)' : 'var(--accent-soft)',
                          }}>
                            {msg.role === 'user' ? 'USER' : 'PRISM'}
                          </span>
                          <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                            {msg.time || (msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString() : '')}
                          </span>
                        </div>
                        <div style={{
                          padding: '12px 16px',
                          borderRadius: msg.role === 'user' ? '14px 14px 4px 14px' : '14px 14px 14px 4px',
                          background: msg.role === 'user'
                            ? 'linear-gradient(135deg, rgba(124,111,255,0.18) 0%, rgba(124,111,255,0.06) 100%)'
                            : 'var(--bg-elevated)',
                          border: `1px solid ${msg.role === 'user' ? 'var(--border-accent)' : 'var(--border)'}`,
                        }}>
                          <p style={{
                            margin: 0, fontSize: 14, lineHeight: 1.65,
                            color: 'var(--text-primary)',
                            fontWeight: msg.role === 'assistant' ? 500 : 400,
                          }}>
                            {msg.content || ''}
                          </p>
                          {msg.thinking && (
                            <div style={{
                              marginTop: 8, paddingTop: 8,
                              borderTop: '1px solid var(--border)',
                              display: 'flex', alignItems: 'center', gap: 6,
                            }}>
                              <span style={{ fontSize: 11 }}>🔧</span>
                              <span style={{ fontSize: 11, color: 'var(--accent-soft)', fontWeight: 500, fontStyle: 'italic' }}>
                                Checking transaction...
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </>
                )
              })()}

              {/* Tool action card */}
              {showToolAction && (
                <div className="slide-up" style={{ alignSelf: 'stretch', padding: '4px 0' }}>
                  <AIActionPanel compact />
                </div>
              )}
            </div>

            {/* Escalation panel inline — show in demo mode based on animation, or in live mode if case is escalated */}
            {(showEscalation || (!demoMode && activeCase?.escalated && !activeCase?.taken_over)) && activeCase && (
              <div className="slide-up" style={{
                paddingTop: 8,
                borderTop: '1px solid var(--border)',
              }}>
                <EscalationPanel
                  caseData={activeCase}
                  compact
                  onTakeOver={async (id) => {
                    try {
                      await fetch(getApiUrl(`/cases/${id}/takeover`), { method: 'POST' })
                    } catch {}
                    setCases(prev => prev.map(p =>
                      p.case_id === id ? { ...p, taken_over: true, status: 'TAKEN_OVER' } : p
                    ))
                    handleAgentAgoraJoin(activeCase?.channel || 'prism-demo')
                  }}
                />
              </div>
            )}

            {/* Bottom input bar & Live Agora controls */}
            <div style={{
              padding: '12px 0 0',
              borderTop: showEscalation ? 'none' : '1px solid var(--border)',
              display: 'flex',
              flexDirection: 'column',
              gap: 10,
            }}>
              <div style={{
                display: 'flex',
                gap: 10,
                alignItems: 'center',
              }}>
                <div style={{
                  flex: 1,
                  padding: '10px 14px',
                  background: agentAudioConnected ? 'rgba(52,211,153,0.08)' : 'var(--bg-elevated)',
                  border: `1px solid ${agentAudioConnected ? 'rgba(52,211,153,0.25)' : 'var(--border)'}`,
                  borderRadius: 10,
                  fontSize: 12,
                  color: agentAudioConnected ? 'var(--success)' : 'var(--text-muted)',
                  fontWeight: agentAudioConnected ? 600 : 400,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                }}>
                  <span>{agentAudioConnected ? '🟢' : '🎙️'}</span>
                  <span>
                    {agentAudioConnected
                      ? `AGORA REALTIME AUDIO CONNECTED (Channel: ${activeCase?.channel || 'prism-demo'})`
                      : activeCase?.taken_over
                        ? 'Connected with customer'
                        : showEscalation
                          ? 'Click "TAKE OVER" above to join the live call'
                          : 'PRISM AI active'}
                  </span>
                </div>

                {agentAudioConnected && (
                  <div style={{ display: 'flex', gap: 6 }}>
                    <button
                      onClick={toggleAgentMute}
                      className="btn-secondary"
                      style={{ padding: '8px 12px', fontSize: 11 }}
                    >
                      {agentMuted ? 'Unmute Mic' : 'Mute Mic'}
                    </button>
                    <button
                      onClick={disconnectAgentAudio}
                      className="btn-danger"
                      style={{ padding: '8px 12px', fontSize: 11 }}
                    >
                      Disconnect Call
                    </button>
                  </div>
                )}
              </div>
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

            {/* Live AI State panel */}
            {(liveVoiceState !== 'IDLE' || liveAiState) && (
              <div className="glass-panel" style={{ padding: 0, overflow: 'hidden' }}>
                <div style={{ padding: '10px 16px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span className="label-text" style={{ margin: 0 }}>Live AI State</span>
                  <span style={{ marginLeft: 'auto', fontSize: 9, fontWeight: 700, letterSpacing: 1.5, color: liveVoiceState === 'ESCALATING' ? 'var(--danger)' : liveVoiceState === 'ACTING' ? '#fbbf24' : 'var(--success)', textTransform: 'uppercase' }}>{liveVoiceState}</span>
                </div>
                <div style={{ maxHeight: 320, overflowY: 'auto' }}>
                  <ThinkingPanel voiceState={liveVoiceState} aiState={liveAiState} />
                </div>
              </div>
            )}

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
        </div>}
      </main>
    </div>
  )
}
