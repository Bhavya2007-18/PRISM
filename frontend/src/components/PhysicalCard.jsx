import { useRef } from 'react'

/**
 * PhysicalCard — a card that behaves like a physical object.
 * Inspired by the 3D Wooden Card reference.
 *
 * Subtle pointer-tracking perspective tilt.
 * Elevation on hover. Compression on press.
 * Use ONLY for important objects: transaction, case, escalation, metrics.
 *
 * Props:
 *   children
 *   style         additional inline styles
 *   className     additional CSS classes
 *   maxTilt       degrees of max tilt, default 6
 *   onClick
 */
export default function PhysicalCard({ children, style, className = '', maxTilt = 6, onClick }) {
  const cardRef = useRef(null)
  const rAF = useRef(null)

  const handleMove = (e) => {
    if (rAF.current) cancelAnimationFrame(rAF.current)
    rAF.current = requestAnimationFrame(() => {
      const el = cardRef.current
      if (!el) return
      const rect = el.getBoundingClientRect()
      const cx = rect.left + rect.width / 2
      const cy = rect.top + rect.height / 2
      const dx = (e.clientX - cx) / (rect.width / 2)
      const dy = (e.clientY - cy) / (rect.height / 2)
      // CSS variable approach — no React re-render on every mouse move
      el.style.setProperty('--rx', `${-dy * maxTilt}deg`)
      el.style.setProperty('--ry', `${dx * maxTilt}deg`)
      el.style.setProperty('--tz', '6px')
      el.style.setProperty('box-shadow', 'var(--card-hover)')
      el.style.transition = 'box-shadow 0.3s ease'
    })
  }

  const handleLeave = () => {
    if (rAF.current) cancelAnimationFrame(rAF.current)
    const el = cardRef.current
    if (!el) return
    el.style.setProperty('--rx', '0deg')
    el.style.setProperty('--ry', '0deg')
    el.style.setProperty('--tz', '0px')
    el.style.setProperty('box-shadow', 'var(--card-rest)')
    el.style.transition = 'box-shadow 0.4s ease, transform 0.4s var(--spring-settle)'
  }

  const handleDown = () => {
    const el = cardRef.current
    if (!el) return
    el.style.setProperty('--tz', '2px')
    el.style.setProperty('box-shadow', 'var(--card-press)')
    el.style.transition = 'transform 0.08s ease, box-shadow 0.08s ease'
  }
  const handleUp = () => {
    const el = cardRef.current
    if (!el) return
    el.style.setProperty('--tz', '6px')
    el.style.setProperty('box-shadow', 'var(--card-hover)')
    el.style.transition = 'transform 0.2s var(--spring-snappy), box-shadow 0.2s ease'
  }

  return (
    <div
      ref={cardRef}
      className={`card--tilt ${className}`}
      style={{
        '--rx': '0deg',
        '--ry': '0deg',
        '--tz': '0px',
        ...style
      }}
      onMouseMove={handleMove}
      onMouseLeave={handleLeave}
      onMouseDown={handleDown}
      onMouseUp={handleUp}
      onClick={onClick}
    >
      {children}
    </div>
  )
}
