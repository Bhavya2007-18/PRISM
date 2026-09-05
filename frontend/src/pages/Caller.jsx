import VoiceInterface from '../components/VoiceInterface'
import IntelligencePanel from '../components/IntelligencePanel'
import { useState } from 'react'

export default function Caller() {
  // Right panel shows placeholder — IntelligencePanel state flows through VoiceInterface
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '1fr 380px',
      height: '100%',
      overflow: 'hidden',
      background: 'var(--surface-1)',
    }}>
      {/* Center — PRISM Core + voice interface */}
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '32px 24px',
        overflow: 'hidden',
        borderRight: '1px solid var(--border)',
        background: 'var(--surface-0)',
        position: 'relative',
      }}>
        {/* Subtle editorial background texture — thin ruled lines */}
        <div style={{
          position: 'absolute', inset: 0, pointerEvents: 'none',
          backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 39px, var(--border-subtle) 40px)',
          opacity: 0.4,
        }} />

        <div style={{ width: '100%', maxWidth: 500, position: 'relative', zIndex: 1 }}>
          <VoiceInterface />
        </div>

        <div style={{ position: 'absolute', bottom: 20, right: 24, zIndex: 2 }}>
          <a href="/agent"
            style={{ fontSize: 11, color: 'var(--text-faint)', textDecoration: 'none', fontWeight: 400, letterSpacing: '0.02em', transition: 'color 0.15s ease' }}
            onMouseEnter={e => e.currentTarget.style.color = 'var(--text-muted)'}
            onMouseLeave={e => e.currentTarget.style.color = 'var(--text-faint)'}>
            Agent Dashboard →
          </a>
        </div>
      </div>

      {/* Right — editorial information panel */}
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        background: 'var(--surface-1)',
      }}>
        {/* Panel header */}
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', flexShrink: 0, display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
          <span className="t-label">Session</span>
        </div>

        {/* Editorial idle state */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '28px 24px', display: 'flex', flexDirection: 'column', gap: 24 }}>

          {/* Tagline — display typography */}
          <div>
            <div className="d-section" style={{ color: 'var(--text-primary)', lineHeight: 1.2 }}>
              AI that listens,
            </div>
            <div className="d-section d-italic" style={{ color: 'var(--text-muted)', lineHeight: 1.2 }}>
              reasons, resolves.
            </div>
          </div>

          {/* Capability pills */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 8 }}>
            {[
              { label: 'Multilingual', detail: 'Hindi · English · Hinglish' },
              { label: 'Real-time AI', detail: 'Listens and responds live' },
              { label: 'Smart escalation', detail: 'Human handoff when needed' },
            ].map(item => (
              <div key={item.label} style={{ display: 'flex', alignItems: 'baseline', gap: 10, padding: '8px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-primary)', minWidth: 110 }}>{item.label}</span>
                <span style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 400 }}>{item.detail}</span>
              </div>
            ))}
          </div>

          {/* AI identification */}
          <div style={{ marginTop: 'auto', paddingTop: 24, borderTop: '1px solid var(--border-subtle)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span className="status-dot status-dot--ok status-dot--breathe" />
              <span style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 400 }}>PRISM AI · Voice Engine Active</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
