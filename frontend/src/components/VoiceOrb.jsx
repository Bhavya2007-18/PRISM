/**
 * VoiceOrb — presentational-only PRISM state visualizer.
 *
 * Renders a premium animated circular element that reflects the current
 * PRISM operational state. Zero business logic, zero API calls, zero
 * internal state management.
 *
 * Props:
 *   state      {string}   — one of PRISM_STATES (e.g. 'LISTENING')
 *   onClick    {Function} — called on click (connect or disconnect)
 *   size       {number}   — diameter in px, default 160
 *   audioLevel {number}   — 0–1, drives waveform ring pulse when SPEAKING
 */

const STATE_ICONS = {
  IDLE:            '○',
  CONNECTING:      '◌',
  LISTENING:       '●',
  UNDERSTANDING:   '◉',
  THINKING:        '◌',
  ACTING:          '→',
  SPEAKING:        '◉',
  ESCALATING:      '⚠',
  HUMAN_CONNECTED: '✓',
  ERROR:           '✕',
}

// SVG ring color per state (drives `currentColor` on the SVG element).
function getRingColor(state) {
  if (state === 'ESCALATING')      return '#dc2626' // var(--danger)
  if (state === 'HUMAN_CONNECTED') return '#16a34a' // var(--ok)
  return '#888888' // var(--text-tertiary)
}

export default function VoiceOrb({ state = 'IDLE', onClick, size = 160, audioLevel = 0 }) {
  const cx = size / 2
  const cy = size / 2
  const outerR = size * 0.45
  const innerR = size * 0.35

  const circumference      = 2 * Math.PI * outerR
  const innerCircumference = 2 * Math.PI * innerR

  const ringColor = getRingColor(state)

  // ── Outer ring: state-specific SVG animation ──────────────────────
  let outerCircleEl = null

  if (state === 'THINKING') {
    // Slowly orbiting ring
    outerCircleEl = (
      <g
        style={{
          transformOrigin: `${cx}px ${cy}px`,
          animation: 'orb-orbit 4s linear infinite',
        }}
      >
        <circle
          cx={cx}
          cy={cy}
          r={outerR}
          fill="none"
          strokeWidth="1.5"
          stroke="currentColor"
          strokeLinecap="round"
          opacity="0.6"
        />
      </g>
    )
  } else if (state === 'ACTING') {
    // Progress arc — animates dashoffset from full circumference to 0
    outerCircleEl = (
      <g>
        <circle
          cx={cx}
          cy={cy}
          r={outerR}
          fill="none"
          strokeWidth="1.5"
          stroke="currentColor"
          strokeLinecap="round"
          strokeDasharray={circumference}
          style={{ animation: 'orb-progress-arc 2s linear infinite' }}
        />
      </g>
    )
  } else if (state === 'UNDERSTANDING') {
    // Scanning partial-arc sweep
    outerCircleEl = (
      <g
        style={{
          transformOrigin: `${cx}px ${cy}px`,
          animation: 'orb-orbit 2s linear infinite',
        }}
      >
        <circle
          cx={cx}
          cy={cy}
          r={outerR}
          fill="none"
          strokeWidth="1.5"
          stroke="currentColor"
          strokeLinecap="round"
          strokeDasharray={`${circumference * 0.3} ${circumference * 0.7}`}
        />
      </g>
    )
  } else {
    // IDLE, CONNECTING, LISTENING, SPEAKING, ESCALATING, HUMAN_CONNECTED, ERROR
    // Low-opacity static ring — CSS class on the inner orb handles animation.
    outerCircleEl = (
      <g>
        <circle
          cx={cx}
          cy={cy}
          r={outerR}
          fill="none"
          strokeWidth="1.5"
          stroke="currentColor"
          strokeLinecap="round"
          opacity="0.2"
        />
      </g>
    )
  }

  // ── Inner ring: state-specific SVG animation ──────────────────────
  let innerCircleEl = null

  if (state === 'LISTENING') {
    // Breathing ring — opacity + scale oscillation
    innerCircleEl = (
      <g
        style={{
          transformOrigin: `${cx}px ${cy}px`,
          animation: 'orb-breathe-ring 3s ease-in-out infinite',
        }}
      >
        <circle
          cx={cx}
          cy={cy}
          r={innerR}
          fill="none"
          strokeWidth="2"
          stroke="currentColor"
          strokeLinecap="round"
          opacity="0.4"
        />
      </g>
    )
  } else if (state === 'SPEAKING') {
    // Audio-level driven arc — dashoffset tracks audioLevel in real time
    const dashOffset = innerCircumference * (1 - (audioLevel || 0.3))
    innerCircleEl = (
      <g>
        <circle
          cx={cx}
          cy={cy}
          r={innerR}
          fill="none"
          strokeWidth="2"
          stroke="currentColor"
          strokeLinecap="round"
          strokeDasharray={innerCircumference}
          strokeDashoffset={dashOffset}
          opacity="0.6"
        />
      </g>
    )
  } else {
    // Default: low-opacity static inner ring
    innerCircleEl = (
      <g>
        <circle
          cx={cx}
          cy={cy}
          r={innerR}
          fill="none"
          strokeWidth="2"
          stroke="currentColor"
          strokeLinecap="round"
          opacity="0.2"
        />
      </g>
    )
  }

  return (
    <div
      className="voice-orb-wrapper"
      style={{ width: size, height: size, cursor: 'pointer' }}
      onClick={onClick}
      role="button"
      aria-label={state}
    >
      {/* SVG ring layer — absolute, full size, pointer-events disabled */}
      <svg
        viewBox={`0 0 ${size} ${size}`}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          pointerEvents: 'none',
          overflow: 'visible',
          color: ringColor,
        }}
        aria-hidden="true"
      >
        {outerCircleEl}
        {innerCircleEl}
      </svg>

      {/* Inner CSS orb — driven by voice-orb--{state} class from index.css */}
      <div
        className={`voice-orb voice-orb--${state.toLowerCase()}`}
        style={{
          width: size * 0.75,
          height: size * 0.75,
          position: 'absolute',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <span className="voice-orb-icon">{STATE_ICONS[state] || '○'}</span>
      </div>
    </div>
  )
}
