import { useRef, useEffect } from 'react'

/**
 * PrismCore — PRISM's signature 3D AI object.
 *
 * A physical design object inside the interface.
 * Matte white / soft grey / graphite surfaces.
 * No neon. No glow. No sci-fi.
 * Each PRISM_STATE drives a distinct physical animation.
 *
 * Props:
 *   state      {string}   one of PRISM_STATES
 *   onClick    {Function} connect / disconnect
 *   size       {number}   diameter, default 180
 *   audioLevel {number}   0–1, affects SPEAKING animation
 */

const STATE_LABELS = {
  IDLE:            'Idle',
  CONNECTING:      'Connecting',
  LISTENING:       'Listening',
  UNDERSTANDING:   'Understanding',
  THINKING:        'Thinking',
  ACTING:          'Checking',
  SPEAKING:        'Speaking',
  ESCALATING:      'Escalating',
  HUMAN_CONNECTED: 'Human Active',
  ERROR:           'Error',
}

// Geometric shapes per state — minimal SVG fragments rendered inside the core
const STATE_MARKS = {
  IDLE:            null,
  CONNECTING:      'ring',
  LISTENING:       'dot',
  UNDERSTANDING:   'arc',
  THINKING:        'tri',
  ACTING:          'cross',
  SPEAKING:        'wave',
  ESCALATING:      'pulse',
  HUMAN_CONNECTED: 'check',
  ERROR:           'x',
}

export default function PrismCore({ state = 'IDLE', onClick, size = 180, audioLevel = 0 }) {
  const wrapperRef = useRef(null)
  const animFrameRef = useRef(null)

  // Pointer-tracking physical tilt — only when NOT in active AI state
  useEffect(() => {
    const el = wrapperRef.current
    if (!el) return
    const passiveStates = ['IDLE', 'LISTENING']
    if (!passiveStates.includes(state)) return

    const handleMove = (e) => {
      const rect = el.getBoundingClientRect()
      const cx = rect.left + rect.width / 2
      const cy = rect.top + rect.height / 2
      const dx = (e.clientX - cx) / (rect.width / 2)   // -1 to 1
      const dy = (e.clientY - cy) / (rect.height / 2)  // -1 to 1
      const maxTilt = 8
      const scene = el.querySelector('.prism-core__scene')
      if (scene) {
        scene.style.transform = `rotateY(${dx * maxTilt}deg) rotateX(${-dy * maxTilt}deg)`
      }
    }
    const handleLeave = () => {
      const scene = el.querySelector('.prism-core__scene')
      if (scene) scene.style.transform = 'rotateY(0deg) rotateX(0deg)'
    }
    el.addEventListener('mousemove', handleMove)
    el.addEventListener('mouseleave', handleLeave)
    return () => { el.removeEventListener('mousemove', handleMove); el.removeEventListener('mouseleave', handleLeave) }
  }, [state])

  const cx = size / 2
  const coreSize = size * 0.68
  const ringSize = size * 0.88
  const ring2Size = size * 0.78

  // Ring color
  const ringColor = state === 'ESCALATING' ? 'var(--danger-border)'
    : state === 'HUMAN_CONNECTED' ? 'var(--ok-border)'
    : 'var(--border-strong)'

  return (
    <div
      ref={wrapperRef}
      className={`prism-core prism-core--${state.toLowerCase()}`}
      style={{ width: size, height: size }}
      onClick={onClick}
      role="button"
      aria-label={`PRISM — ${STATE_LABELS[state] || state}`}
    >
      {/* Scene — receives 3D pointer tilt */}
      <div
        className="prism-core__scene"
        style={{
          width: size, height: size,
          position: 'relative',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          transition: 'transform 0.15s ease',
        }}
      >
        {/* Outer SVG ring(s) — geometric depth layers */}
        <svg
          viewBox={`0 0 ${size} ${size}`}
          style={{
            position: 'absolute', top: 0, left: 0, width: '100%', height: '100%',
            pointerEvents: 'none', overflow: 'visible',
            color: ringColor,
          }}
          aria-hidden="true"
        >
          {/* Outer ring — primary orbit */}
          <g style={{
            transformOrigin: `${cx}px ${cx}px`,
            animation: state === 'THINKING' ? 'orb-orbit 4s linear infinite'
              : state === 'ACTING'          ? 'orb-orbit 1.2s linear infinite'
              : state === 'UNDERSTANDING'   ? 'orb-orbit 3s linear infinite'
              : 'orb-orbit 24s linear infinite',
          }}>
            <circle
              cx={cx} cy={cx} r={ringSize / 2}
              fill="none" strokeWidth="1" stroke="currentColor"
              strokeLinecap="round"
              strokeDasharray={
                state === 'ACTING'        ? `${Math.PI * ringSize * 0.6} ${Math.PI * ringSize * 0.4}`
                : state === 'UNDERSTANDING' ? `${Math.PI * ringSize * 0.25} ${Math.PI * ringSize * 0.75}`
                : `${Math.PI * ringSize} 0`
              }
              opacity={
                state === 'IDLE' ? 0.12
                : state === 'LISTENING' ? 0.25
                : 0.45
              }
            />
          </g>

          {/* Inner ring — counter-rotate */}
          <g style={{
            transformOrigin: `${cx}px ${cx}px`,
            animation: state === 'THINKING' ? 'orb-orbit 7s linear infinite reverse'
              : state === 'ACTING'          ? 'orb-orbit 2s linear infinite reverse'
              : 'orb-orbit 36s linear infinite reverse',
          }}>
            <circle
              cx={cx} cy={cx} r={ring2Size / 2}
              fill="none" strokeWidth="0.75" stroke="currentColor"
              strokeLinecap="round"
              strokeDasharray={
                state === 'ACTING' ? `${Math.PI * ring2Size * 0.4} ${Math.PI * ring2Size * 0.6}`
                : `${Math.PI * ring2Size * 0.15} ${Math.PI * ring2Size * 0.85}`
              }
              opacity={state === 'IDLE' ? 0.08 : 0.25}
            />
          </g>

          {/* ACTING — progress arc fill */}
          {state === 'ACTING' && (
            <g style={{ transformOrigin: `${cx}px ${cx}px` }}>
              <circle
                cx={cx} cy={cx} r={ringSize / 2 - 6}
                fill="none" strokeWidth="1.5"
                stroke="currentColor"
                strokeLinecap="round"
                strokeDasharray={Math.PI * (ringSize - 12)}
                style={{ animation: 'orb-progress-arc 2s linear infinite' }}
                opacity="0.6"
              />
            </g>
          )}

          {/* LISTENING — breathing outer glow ring */}
          {state === 'LISTENING' && (
            <circle
              cx={cx} cy={cx} r={ringSize / 2 + 4}
              fill="none" strokeWidth="1"
              stroke="currentColor" opacity="0.12"
              style={{ animation: 'ring-breathe 2.8s ease-in-out infinite' }}
            />
          )}

          {/* SPEAKING — audioLevel arc */}
          {state === 'SPEAKING' && (
            <circle
              cx={cx} cy={cx} r={ring2Size / 2}
              fill="none" strokeWidth="2"
              stroke="currentColor"
              strokeLinecap="round"
              strokeDasharray={Math.PI * ring2Size}
              strokeDashoffset={Math.PI * ring2Size * (1 - Math.max(0.2, audioLevel || 0.35))}
              opacity="0.5"
            />
          )}
        </svg>

        {/* Core body — the physical sphere */}
        <div
          className="prism-core__body"
          style={{ width: coreSize, height: coreSize, position: 'relative' }}
        >
          {/* Surface facet texture */}
          <div className="prism-core__facet" />

          {/* State mark — minimal geometric symbol */}
          <CoreMark state={state} size={coreSize} audioLevel={audioLevel} />
        </div>
      </div>
    </div>
  )
}

function CoreMark({ state, size, audioLevel }) {
  const s = size * 0.22
  const color = state === 'ESCALATING' ? 'var(--danger)' : state === 'HUMAN_CONNECTED' ? 'var(--ok)' : 'var(--text-tertiary)'
  const style = { flexShrink: 0 }

  if (state === 'IDLE') return (
    <svg width={s} height={s} viewBox="0 0 24 24" fill="none" style={style}>
      <circle cx="12" cy="12" r="8" stroke={color} strokeWidth="1.2" opacity="0.5" />
    </svg>
  )
  if (state === 'CONNECTING') return (
    <svg width={s} height={s} viewBox="0 0 24 24" fill="none" style={style}>
      <circle cx="12" cy="12" r="8" stroke={color} strokeWidth="1.2" strokeDasharray="4 4"
        style={{ animation: 'orb-orbit 1.5s linear infinite', transformOrigin: '12px 12px' }} />
    </svg>
  )
  if (state === 'LISTENING') return (
    <svg width={s} height={s} viewBox="0 0 24 24" fill="none" style={style}>
      <circle cx="12" cy="12" r="3" fill={color} opacity="0.6" style={{ animation: 'dot-pulse 2.8s ease-in-out infinite' }} />
    </svg>
  )
  if (state === 'UNDERSTANDING') return (
    <svg width={s} height={s} viewBox="0 0 24 24" fill="none" style={style}>
      <path d="M12 4 L20 20 L4 20 Z" stroke={color} strokeWidth="1.2" fill="none" opacity="0.5"
        style={{ animation: 'timeline-pulse 2s ease-in-out infinite', transformOrigin: '12px 14px' }} />
    </svg>
  )
  if (state === 'THINKING') return (
    <svg width={s} height={s} viewBox="0 0 24 24" fill="none" style={style}>
      <circle cx="12" cy="12" r="3" stroke={color} strokeWidth="1.2" opacity="0.5" />
      <circle cx="12" cy="12" r="6" stroke={color} strokeWidth="0.8" strokeDasharray="2 4" opacity="0.3"
        style={{ animation: 'orb-orbit 3s linear infinite reverse', transformOrigin: '12px 12px' }} />
    </svg>
  )
  if (state === 'ACTING') return (
    <svg width={s} height={s} viewBox="0 0 24 24" fill="none" style={style}>
      <line x1="12" y1="4" x2="12" y2="20" stroke={color} strokeWidth="1.2" opacity="0.5" />
      <line x1="4" y1="12" x2="20" y2="12" stroke={color} strokeWidth="1.2" opacity="0.5" />
    </svg>
  )
  if (state === 'SPEAKING') return (
    <svg width={s} height={s} viewBox="0 0 24 24" fill="none" style={style}>
      <line x1="4"  y1="12" x2="4"  y2={12 - (audioLevel||0.3) * 8 - 4} stroke={color} strokeWidth="1.5" strokeLinecap="round" opacity="0.5" />
      <line x1="8"  y1="12" x2="8"  y2={12 - (audioLevel||0.5) * 10 - 4} stroke={color} strokeWidth="1.5" strokeLinecap="round" opacity="0.7" />
      <line x1="12" y1="12" x2="12" y2={12 - (audioLevel||0.8) * 12 - 4} stroke={color} strokeWidth="1.5" strokeLinecap="round" opacity="0.9" />
      <line x1="16" y1="12" x2="16" y2={12 - (audioLevel||0.5) * 10 - 4} stroke={color} strokeWidth="1.5" strokeLinecap="round" opacity="0.7" />
      <line x1="20" y1="12" x2="20" y2={12 - (audioLevel||0.3) * 8 - 4} stroke={color} strokeWidth="1.5" strokeLinecap="round" opacity="0.5" />
    </svg>
  )
  if (state === 'ESCALATING') return (
    <svg width={s} height={s} viewBox="0 0 24 24" fill="none" style={style}>
      <path d="M12 5 L19 18 L5 18 Z" stroke={color} strokeWidth="1.2" fill="none"
        style={{ animation: 'core-escalate 1.8s ease-in-out infinite', transformOrigin: '12px 12px' }} />
    </svg>
  )
  if (state === 'HUMAN_CONNECTED') return (
    <svg width={s} height={s} viewBox="0 0 24 24" fill="none" style={style}>
      <polyline points="4,13 9,18 20,7" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" opacity="0.8" />
    </svg>
  )
  if (state === 'ERROR') return (
    <svg width={s} height={s} viewBox="0 0 24 24" fill="none" style={style}>
      <line x1="6" y1="6" x2="18" y2="18" stroke={color} strokeWidth="1.5" strokeLinecap="round" opacity="0.6" />
      <line x1="6" y1="18" x2="18" y2="6" stroke={color} strokeWidth="1.5" strokeLinecap="round" opacity="0.6" />
    </svg>
  )
  return null
}
