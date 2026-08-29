import { useState, useEffect } from 'react'

export default function AIActionPanel({ steps = [], compact = false }) {
  const defaultSteps = [
    { label: 'Checking transaction TX48291...', status: 'pending', delay: 0 },
    { label: 'Transaction found', status: 'pending', delay: 600 },
    { label: 'Amount verified: ₹1,499', status: 'pending', delay: 1200 },
    { label: 'Payment status: SUCCESS', status: 'pending', delay: 1800 },
    { label: 'Order status: NOT_CONFIRMED', status: 'warning', delay: 2400 },
  ]

  const displaySteps = steps.length > 0 ? steps : defaultSteps
  const [visibleSteps, setVisibleSteps] = useState([])

  useEffect(() => {
    setVisibleSteps([])
    const timers = displaySteps.map((step, i) =>
      setTimeout(() => {
        setVisibleSteps(prev => [
          ...prev,
          { ...step, status: step.status || 'success' }
        ])
      }, step.delay || (i * 500))
    )
    return () => timers.forEach(clearTimeout)
  }, [displaySteps])

  const statusIcon = (status) => {
    if (status === 'success') return <span style={{ color: 'var(--success)' }}>✓</span>
    if (status === 'warning') return <span style={{ color: 'var(--warning)' }}>⚠</span>
    if (status === 'error') return <span style={{ color: 'var(--danger)' }}>✗</span>
    if (status === 'pending') return (
      <span className="typing-dots" style={{ display: 'inline-flex' }}>
        <span /><span /><span />
      </span>
    )
    return null
  }

  return (
    <div
      className="glass-panel"
      style={{
        padding: compact ? '14px 16px' : '18px 20px',
        border: '1px solid var(--border-accent)',
        background: 'linear-gradient(180deg, rgba(124,111,255,0.06) 0%, var(--bg-card) 100%)',
      }}
    >
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        marginBottom: compact ? 12 : 16,
      }}>
        <span style={{ fontSize: 14 }}>⚡</span>
        <span style={{
          fontSize: 11,
          fontWeight: 700,
          letterSpacing: 2,
          color: 'var(--accent-soft)',
          textTransform: 'uppercase',
        }}>
          PRISM ACTION
        </span>
      </div>

      {/* Steps */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: compact ? 6 : 8 }}>
        {visibleSteps.map((step, i) => (
          <div
            key={i}
            className="fade-in"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: compact ? '6px 0' : '8px 0',
              borderBottom: i < visibleSteps.length - 1 ? '1px solid rgba(255,255,255,0.03)' : 'none',
            }}
          >
            <div style={{
              width: 18,
              display: 'flex',
              justifyContent: 'center',
              fontSize: 12,
              flexShrink: 0,
            }}>
              {statusIcon(step.status)}
            </div>
            <span style={{
              fontSize: compact ? 12 : 13,
              color: step.status === 'warning' ? 'var(--warning)'
                : step.status === 'error' ? 'var(--danger)'
                : step.status === 'pending' ? 'var(--text-secondary)'
                : 'var(--text-primary)',
              fontWeight: step.status === 'pending' ? 400 : 500,
            }}>
              {step.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
