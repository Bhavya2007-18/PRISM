import { useState, useEffect } from 'react'
import EscalationPanel from '../components/EscalationPanel'

export default function Agent() {
  const [cases, setCases] = useState([])
  const [lastUpdated, setLastUpdated] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let mounted = true

    async function poll() {
      try {
        const res = await fetch('/cases')
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        if (mounted) {
          setCases(data.cases || [])
          setLastUpdated(new Date())
          setError(null)
        }
      } catch (e) {
        if (mounted) setError(e.message)
      }
    }

    poll()
    const interval = setInterval(poll, 2000)
    return () => {
      mounted = false
      clearInterval(interval)
    }
  }, [])

  const activeCases = cases.filter(c => !c.taken_over)
  const resolvedCases = cases.filter(c => c.taken_over)

  return (
    <div style={{ padding: '32px 40px', maxWidth: 960, margin: '0 auto' }}>

      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'flex-start',
        justifyContent: 'space-between', marginBottom: 32
      }}>
        <div>
          <div style={{
            fontSize: 11, fontWeight: 700, letterSpacing: 3,
            color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: 6
          }}>
            PRISM • Human Assistance
          </div>
          <h1 style={{
            fontSize: 24, fontWeight: 700, color: 'var(--text-primary)', margin: 0
          }}>
            Agent Dashboard
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: 13, marginTop: 4 }}>
            Cases escalated by the AI that require human intervention
          </p>
        </div>

        <div style={{ textAlign: 'right' }}>
          {/* Live indicator */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'flex-end' }}>
            <span style={{
              width: 6, height: 6, borderRadius: '50%',
              background: error ? '#e74c3c' : '#2ecc71',
              boxShadow: error ? 'none' : '0 0 6px #2ecc71',
              display: 'inline-block',
            }} />
            <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
              {error ? `Error: ${error}` : 'Live · updates every 2s'}
            </span>
          </div>
          {lastUpdated && (
            <div style={{ fontSize: 11, color: '#333355', marginTop: 4 }}>
              Last updated {lastUpdated.toLocaleTimeString()}
            </div>
          )}
        </div>
      </div>

      {/* Stats bar */}
      <div style={{
        display: 'flex', gap: 16, marginBottom: 32
      }}>
        {[
          { label: 'Active Escalations', value: activeCases.length, color: activeCases.length > 0 ? '#e74c3c' : 'var(--text-secondary)' },
          { label: 'Taken Over', value: resolvedCases.length, color: '#2ecc71' },
          { label: 'Total', value: cases.length, color: 'var(--text-secondary)' },
        ].map(stat => (
          <div key={stat.label} style={{
            flex: 1, padding: '16px 20px',
            background: 'var(--bg-card)',
            border: '1px solid var(--border)',
            borderRadius: 12,
          }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: stat.color }}>
              {stat.value}
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
              {stat.label}
            </div>
          </div>
        ))}
      </div>

      {/* Empty state */}
      {cases.length === 0 && (
        <div style={{
          padding: '60px 40px', textAlign: 'center',
          border: '1px dashed var(--border)', borderRadius: 16,
        }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>✓</div>
          <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 6 }}>
            All clear
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
            PRISM is handling all cases. Escalations will appear here automatically.
          </div>
        </div>
      )}

      {/* Active escalations */}
      {activeCases.length > 0 && (
        <div style={{ marginBottom: 32 }}>
          <div style={{
            fontSize: 11, fontWeight: 700, letterSpacing: 2,
            color: '#e74c3c', textTransform: 'uppercase', marginBottom: 16
          }}>
            Requires Attention — {activeCases.length}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {activeCases.map(c => (
              <EscalationPanel
                key={c.case_id}
                caseData={c}
                onTakeOver={(id) => {
                  setCases(prev => prev.map(p =>
                    p.case_id === id ? { ...p, taken_over: true, status: 'TAKEN_OVER' } : p
                  ))
                }}
              />
            ))}
          </div>
        </div>
      )}

      {/* Taken over cases */}
      {resolvedCases.length > 0 && (
        <div>
          <div style={{
            fontSize: 11, fontWeight: 700, letterSpacing: 2,
            color: '#2ecc71', textTransform: 'uppercase', marginBottom: 16
          }}>
            Taken Over — {resolvedCases.length}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {resolvedCases.map(c => (
              <EscalationPanel
                key={c.case_id}
                caseData={c}
                onTakeOver={() => {}}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
