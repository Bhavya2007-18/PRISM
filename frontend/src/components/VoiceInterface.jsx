import { useState, useRef, useEffect } from 'react'
import AgoraRTC from 'agora-rtc-sdk-ng'

const CHANNEL = 'prism-demo'
const AGENT_UID = 12345

// Keep Agora SDK logs minimal
AgoraRTC.setLogLevel(3)

export default function VoiceInterface() {
  const [status, setStatus] = useState('idle')   // idle | connecting | connected | error
  const [agentActive, setAgentActive] = useState(false)
  const [error, setError] = useState(null)
  const [hint, setHint] = useState('')

  const clientRef = useRef(null)
  const micTrackRef = useRef(null)
  const sessionRef = useRef(null)
  const userUidRef = useRef(Math.floor(Math.random() * 90000) + 10000)

  // Pulse animation for mic button when connected
  useEffect(() => {
    if (status === 'connected') {
      const hints = [
        'Bhai mera payment kat gaya but order confirm nahi hua',
        'My payment was deducted but order not confirmed',
        'Transaction ID hai TX48291',
      ]
      let i = 0
      const t = setInterval(() => {
        setHint(hints[i % hints.length])
        i++
      }, 4000)
      setHint(hints[0])
      return () => clearInterval(t)
    }
  }, [status])

  async function connect() {
    setStatus('connecting')
    setError(null)

    try {
      // Step 1: Get RTC token from backend
      const uid = userUidRef.current
      const tokenResp = await fetch(`/token?channel=${CHANNEL}&uid=${uid}`)
      if (!tokenResp.ok) throw new Error(`Token fetch failed: ${tokenResp.status}`)
      const tokenData = await tokenResp.json()

      const { token, app_id, warning } = tokenData
      if (warning) console.warn('[PRISM]', warning)

      const demoMode = !app_id || app_id === 'demo' || token === 'demo-token-no-credentials'

      if (!demoMode) {
        // Step 2: Create Agora client and join channel
        const client = AgoraRTC.createClient({ mode: 'rtc', codec: 'vp8' })
        clientRef.current = client

        // Listen for the AI agent's audio
        client.on('user-published', async (user, mediaType) => {
          await client.subscribe(user, mediaType)
          if (mediaType === 'audio') {
            user.audioTrack?.play()
            if (user.uid === AGENT_UID) setAgentActive(true)
          }
        })

        client.on('user-unpublished', (user) => {
          if (user.uid === AGENT_UID) setAgentActive(false)
        })

        client.on('user-left', (user) => {
          if (user.uid === AGENT_UID) setAgentActive(false)
        })

        client.on('connection-state-change', (state) => {
          console.log('[PRISM] Agora connection state:', state)
          if (state === 'DISCONNECTED') setStatus('idle')
        })

        await client.join(app_id, CHANNEL, token, uid)
        console.log(`[PRISM] Joined channel "${CHANNEL}" as UID ${uid}`)

        // Step 3: Publish microphone
        const micTrack = await AgoraRTC.createMicrophoneAudioTrack({
          encoderConfig: 'speech_standard',
        })
        micTrackRef.current = micTrack
        await client.publish([micTrack])
        console.log('[PRISM] Microphone published')
      } else {
        console.log('[PRISM] Demo mode — Agora channel join skipped (no credentials)')
      }

      // Step 4: Start the PRISM AI agent via backend
      const sessionResp = await fetch('/session/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ channel: CHANNEL, user_uid: uid }),
      })

      if (sessionResp.ok) {
        const sessionData = await sessionResp.json()
        sessionRef.current = sessionData
        console.log('[PRISM] Agent started:', sessionData)
      } else {
        const errText = await sessionResp.text()
        console.warn('[PRISM] Agent start failed:', errText)
        // Don't hard-fail — user can still see the UI
      }

      setStatus('connected')
    } catch (err) {
      console.error('[PRISM] Connect error:', err)
      setError(err.message || 'Connection failed')
      setStatus('error')
      // Clean up partial state
      micTrackRef.current?.close()
      await clientRef.current?.leave().catch(() => {})
      clientRef.current = null
      micTrackRef.current = null
    }
  }

  async function disconnect() {
    setStatus('idle')
    setAgentActive(false)

    try {
      // Stop the PRISM agent
      if (sessionRef.current?.agent_id) {
        await fetch('/session/stop', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            agent_id: sessionRef.current.agent_id,
            channel: CHANNEL,
          }),
        }).catch(() => {})
      }

      // Leave Agora channel
      micTrackRef.current?.close()
      await clientRef.current?.leave().catch(() => {})
    } catch (err) {
      console.warn('[PRISM] Disconnect error:', err)
    } finally {
      clientRef.current = null
      micTrackRef.current = null
      sessionRef.current = null
    }
  }

  // ── Render ──────────────────────────────────────────────────────────

  const isConnected = status === 'connected'
  const isConnecting = status === 'connecting'

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: 28,
      padding: '48px 40px',
      background: 'var(--bg-card)',
      borderRadius: 24,
      border: `1px solid ${isConnected ? 'rgba(108,99,255,0.4)' : 'var(--border)'}`,
      minWidth: 420,
      maxWidth: 480,
      boxShadow: isConnected ? '0 0 60px rgba(108,99,255,0.1)' : 'none',
      transition: 'all 0.3s ease',
    }}>

      {/* Logo */}
      <div style={{ textAlign: 'center', userSelect: 'none' }}>
        <div style={{
          fontSize: 52, fontWeight: 800, letterSpacing: -2,
          background: 'linear-gradient(135deg, #6c63ff, #a78bfa)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          backgroundClip: 'text',
          lineHeight: 1,
        }}>
          PRISM
        </div>
        <div style={{
          fontSize: 10, letterSpacing: 4, color: 'var(--text-secondary)',
          marginTop: 6, textTransform: 'uppercase'
        }}>
          Payment Support
        </div>
      </div>

      {/* Status pill */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '6px 16px',
        background: 'var(--bg-elevated)',
        borderRadius: 20,
        border: '1px solid var(--border)',
      }}>
        <span style={{
          width: 7, height: 7, borderRadius: '50%',
          background: status === 'connected' ? '#2ecc71'
                    : status === 'connecting' ? '#f39c12'
                    : status === 'error' ? '#e74c3c'
                    : '#444466',
          boxShadow: status === 'connected' ? '0 0 6px #2ecc71' : 'none',
          display: 'inline-block',
        }} />
        <span style={{
          fontSize: 12,
          color: status === 'connected' ? '#2ecc71'
               : status === 'connecting' ? '#f39c12'
               : status === 'error' ? '#e74c3c'
               : 'var(--text-secondary)'
        }}>
          {status === 'idle' && 'Ready to connect'}
          {status === 'connecting' && 'Starting session…'}
          {status === 'connected' && (agentActive ? '● PRISM speaking' : '● Listening')}
          {status === 'error' && 'Connection error'}
        </span>
      </div>

      {/* Mic button */}
      <button
        onClick={isConnected ? disconnect : connect}
        disabled={isConnecting}
        aria-label={isConnected ? 'Disconnect from PRISM' : 'Connect to PRISM'}
        style={{
          width: 100, height: 100,
          borderRadius: '50%',
          border: `2px solid ${isConnected ? '#6c63ff' : 'var(--border)'}`,
          background: isConnected
            ? 'radial-gradient(circle, rgba(108,99,255,0.25), rgba(108,99,255,0.05))'
            : 'var(--bg-elevated)',
          color: 'white',
          fontSize: 38,
          cursor: isConnecting ? 'not-allowed' : 'pointer',
          opacity: isConnecting ? 0.6 : 1,
          transition: 'all 0.25s ease',
          boxShadow: isConnected ? '0 0 32px rgba(108,99,255,0.4)' : 'none',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {isConnected ? '🎙️' : isConnecting ? '⟳' : '🔇'}
      </button>

      {/* CTA text */}
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 6 }}>
          {status === 'idle' && 'Click the mic to connect'}
          {status === 'connecting' && 'Please wait…'}
          {status === 'connected' && 'Speak naturally — Hindi, English, or Hinglish'}
          {status === 'error' && (
            <span style={{ color: '#e74c3c' }}>{error}</span>
          )}
        </div>
      </div>

      {/* Demo hint — rotates through example phrases */}
      {isConnected && hint && (
        <div style={{
          width: '100%',
          padding: '12px 16px',
          background: 'var(--bg-elevated)',
          borderRadius: 10,
          borderLeft: '3px solid var(--accent)',
        }}>
          <div style={{ fontSize: 10, color: 'var(--accent)', letterSpacing: 1, marginBottom: 5 }}>
            TRY SAYING
          </div>
          <div style={{
            fontSize: 13, color: 'var(--text-secondary)',
            fontStyle: 'italic', lineHeight: 1.5,
          }}>
            "{hint}"
          </div>
        </div>
      )}

      {/* Agent dashboard link */}
      <div style={{ fontSize: 12, color: '#333355' }}>
        Human agent?{' '}
        <a href="/agent" style={{ color: 'var(--accent)', textDecoration: 'none' }}>
          Open dashboard →
        </a>
      </div>
    </div>
  )
}
