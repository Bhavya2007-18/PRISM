import { useRef, useEffect } from 'react'
import AIActionPanel from './AIActionPanel'

export default function TranscriptConsole({
  messages = [],
  showToolAction = false,
  toolSteps,
  emptyLabel,
}) {
  const scrollRef = useRef(null)
  const bottomRef = useRef(null)
  const userScrolled = useRef(false)
  const prevCountRef = useRef(0)

  // Determine which messages are "new" for animation
  const prevCount = prevCountRef.current

  // Filter renderable messages (keep user, assistant, system; skip tool and empty)
  const renderable = messages
    .map((msg, i) => ({ ...msg, originalIndex: i }))
    .filter(msg => msg.content && msg.role !== 'tool')

  const handleScroll = () => {
    const el = scrollRef.current
    if (!el) return
    if (el.scrollTop + el.clientHeight < el.scrollHeight - 20) {
      userScrolled.current = true
    } else {
      userScrolled.current = false
    }
  }

  useEffect(() => {
    if (!userScrolled.current) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
    prevCountRef.current = messages.length
  })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{
        padding: '12px 20px',
        borderBottom: '1px solid var(--border)',
        flexShrink: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <span className="t-label" style={{ color: 'var(--text-tertiary)' }}>TRANSCRIPT</span>
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{messages.length} messages</span>
      </div>

      {/* Scrollable body */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        style={{ flex: 1, overflowY: 'auto', padding: '16px 20px' }}
      >
        {renderable.length === 0 ? (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            gap: 10,
            padding: '40px 20px',
            textAlign: 'center',
          }}>
            <div style={{
              width: 48,
              height: 48,
              borderRadius: '50%',
              background: 'var(--surface-2)',
              border: '1px solid var(--border)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 18,
            }}>○</div>
            <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-secondary)' }}>
              {emptyLabel || 'No messages yet'}
            </div>
          </div>
        ) : (
          <>
            {renderable.map((msg, i) => {
              const isNew = msg.originalIndex >= prevCount
              const { role, content, time, partial, thinking } = msg

              if (role === 'system') {
                return (
                  <div key={i} className="tx-row tx-row--system">
                    <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{content}</span>
                  </div>
                )
              }

              return (
                <div
                  key={i}
                  className="tx-row"
                  style={{
                    animationName: isNew ? 'tx-enter' : 'none',
                    animationDuration: '0.22s',
                    animationTimingFunction: 'ease-out',
                  }}
                >
                  <div className="tx-meta">
                    <span className="t-label" style={{ color: 'var(--text-muted)', fontSize: 10 }}>
                      {role === 'user' ? 'USER' : 'PRISM'}
                    </span>
                    {time && <span className="tx-time">{time}</span>}
                  </div>
                  <div className="tx-body">
                    {content}
                    {partial && <span className="tx-cursor" />}
                    {thinking && (
                      <div style={{ marginTop: 4, fontSize: 11, color: 'var(--text-muted)', fontStyle: 'italic' }}>
                        Checking transaction...
                      </div>
                    )}
                  </div>
                </div>
              )
            })}

            {showToolAction && (
              <div style={{ marginTop: 12 }}>
                <AIActionPanel compact steps={toolSteps} />
              </div>
            )}
          </>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  )
}
