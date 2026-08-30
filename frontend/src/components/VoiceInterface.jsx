import { useState, useRef, useEffect } from 'react'
import AgoraRTC from 'agora-rtc-sdk-ng'

const CHANNEL = 'prism-demo'
const TEXT_CHANNEL = 'prism-text'
const AGENT_UID = 12345

AgoraRTC.setLogLevel(3)

const DEMO_MESSAGES = [
  { role: 'user', content: 'Mera payment kat gaya but order confirm nahi hua.', delay: 2000 },
  { role: 'assistant', content: 'I can help with that. Do you have your transaction ID?', delay: 3500 },
  { role: 'user', content: 'Haan, TX48291 hai.', delay: 5500 },
  { role: 'assistant', content: 'Let me check that transaction for you.', delay: 7000 },
  { role: 'assistant', content: 'I found your ₹1,499 transaction — payment was successful but the order was not confirmed. I want to be careful about whether there was a duplicate charge, so let me connect you with a specialist.', delay: 10000 },
]

const QUICK_PHRASES = [
  'Mera payment kat gaya',
  'TX48291',
  'Order confirm nahi hua',
  'Human se baat karni hai',
]

export default function VoiceInterface() {
  const [mode, setMode] = useState('voice') // 'voice' | 'chat'
  const [status, setStatus] = useState('idle')
  const [agentActive, setAgentActive] = useState(false)
  const [error, setError] = useState(null)
  const [escalated, setEscalated] = useState(false)
  const [takenOver, setTakenOver] = useState(false)
  const [escalatedCaseId, setEscalatedCaseId] = useState(null)
  const [messages, setMessages] = useState([])
  const [chatInput, setChatInput] = useState('')
  const [chatSending, setChatSending] = useState(false)
  const [demoMode, setDemoMode] = useState(false)
  const [waveformBars, setWaveformBars] = useState(Array(24).fill(0.2))

  const clientRef = useRef(null)
  const micTrackRef = useRef(null)
  const sessionRef = useRef(null)
  const userUidRef = useRef(Math.floor(Math.random() * 90000) + 10000)
  const chatEndRef = useRef(null)

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, mode])

  // Poll /debug/case when escalated (but not yet taken over) to detect agent takeover
  useEffect(() => {
    if (!escalated || takenOver || demoMode) return
    const channel = mode === 'chat' ? TEXT_CHANNEL : CHANNEL
    let mounted = true
    const pollTakeover = async () => {
      try {
        const res = await fetch(`/debug/case/${channel}`)
        if (res.ok) {
          const data = await res.json()
          if (data.case?.taken_over && mounted) {
            setTakenOver(true)
            setMessages(prev => [...prev, {
              role: 'system',
              content: 'A human agent has taken over this conversation. You are now connected with a live support specialist.',
            }])
          }
        }
      } catch {}
    }
    const interval = setInterval(pollTakeover, 3000)
    return () => { mounted = false; clearInterval(interval) }
  }, [escalated, takenOver, demoMode, mode])

  useEffect(() => {
    let animationId
    function animate() {
      setWaveformBars(prev =>
        prev.map(() => {
          if (status !== 'connected') return 0.2
          return 0.2 + Math.random() * 0.8
        })
      )
      animationId = requestAnimationFrame(() => setTimeout(animate, 120))
    }
    animate()
    return () => cancelAnimationFrame(animationId)
  }, [status])

  useEffect(() => {
    if (!demoMode || status !== 'connected' || mode !== 'voice') return

    const timers = DEMO_MESSAGES.map(msg =>
      setTimeout(() => {
        setMessages(prev => [...prev, { role: msg.role, content: msg.content }])
        if (msg.role === 'assistant') setAgentActive(true)
        setTimeout(() => setAgentActive(false), 2000)
        if (msg === DEMO_MESSAGES[DEMO_MESSAGES.length - 1]) {
          setTimeout(() => setEscalated(true), 1500)
        }
      }, msg.delay)
    )
    return () => timers.forEach(clearTimeout)
  }, [demoMode, status, mode])

  async function connect() {
    setStatus('connecting')
    setError(null)
    setMessages(mode === 'chat' ? [
      { role: 'assistant', content: 'Namaste! Main PRISM hoon. Aap kaise help kar sakta hoon?' }
    ] : [])
    setEscalated(false)
    setTakenOver(false)
    setEscalatedCaseId(null)

    try {
      const uid = userUidRef.current
      let tokenData = { token: 'demo-token-no-credentials', app_id: 'demo', warning: 'Running in demo mode' }
      try {
        const tokenResp = await fetch(`/token?channel=${CHANNEL}&uid=${uid}`)
        if (tokenResp.ok) tokenData = await tokenResp.json()
      } catch (e) {}
      if (tokenData.warning) console.warn('[PRISM]', tokenData.warning)

      const isDemo = !tokenData.app_id || tokenData.app_id === 'demo' || tokenData.token === 'demo-token-no-credentials'
      setDemoMode(isDemo)

      if (!isDemo && mode === 'voice') {
        const client = AgoraRTC.createClient({ mode: 'rtc', codec: 'vp8' })
        clientRef.current = client
        client.on('user-published', async (user, mediaType) => {
          await client.subscribe(user, mediaType)
          if (mediaType === 'audio') {
            user.audioTrack?.play()
            if (user.uid === AGENT_UID) setAgentActive(true)
          }
        })
        client.on('user-unpublished', (user) => { if (user.uid === AGENT_UID) setAgentActive(false) })
        client.on('user-left', (user) => { if (user.uid === AGENT_UID) setAgentActive(false) })
        client.on('connection-state-change', (s) => { if (s === 'DISCONNECTED') setStatus('idle') })
        await client.join(tokenData.app_id, CHANNEL, tokenData.token, uid)
        const micTrack = await AgoraRTC.createMicrophoneAudioTrack({ encoderConfig: 'speech_standard' })
        micTrackRef.current = micTrack
        await client.publish([micTrack])
      }

      try {
        const sessionResp = await fetch('/session/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ channel: mode === 'chat' ? TEXT_CHANNEL : CHANNEL, user_uid: uid }),
        })
        if (sessionResp.ok) sessionRef.current = await sessionResp.json()
      } catch (e) {}

      setStatus('connected')
    } catch (err) {
      setError(err.message || 'Connection failed')
      setStatus('error')
      micTrackRef.current?.close()
      await clientRef.current?.leave().catch(() => {})
      clientRef.current = null
      micTrackRef.current = null
    }
  }

  async function disconnect() {
    setStatus('idle')
    setAgentActive(false)
    setEscalated(false)
    setTakenOver(false)
    setEscalatedCaseId(null)
    setMessages([])
    try {
      if (sessionRef.current?.agent_id) {
        await fetch('/session/stop', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ agent_id: sessionRef.current.agent_id, channel: mode === 'chat' ? TEXT_CHANNEL : CHANNEL }),
        }).catch(() => {})
      }
      micTrackRef.current?.close()
      await clientRef.current?.leave().catch(() => {})
    } catch (e) {
      console.warn(e)
    } finally {
      clientRef.current = null
      micTrackRef.current = null
      sessionRef.current = null
    }
  }

  function getDemoReply(text) {
    const t = text.toLowerCase()

    if (/(human|agent|insaan|aap sa|baat karni|representative|aadmi)/i.test(t)) {
      return {
        reply: 'Theek hai, main abhi aapko ek human agent se connect kar raha hoon. Please thoda wait karein.',
        escalate: true,
      }
    }

    if (/(tx|transaction|ref|receipt|id)[\s_-]*[a-z0-9]{3,}|tx\d|tx\s*\d/i.test(t)) {
      return {
        reply: 'Dhanyavaad! Main is transaction ko abhi verify karta hoon. Ek minute please...',
      }
    }

    if (/(hi|hello|namaste|namaskar|suno|hlo|hey)/i.test(t)) {
      return {
        reply: 'Namaste! Main PRISM hoon. Bataiye, kaise help kar sakta hoon aapki?',
      }
    }

    if (/(payment|paise?|kat|cut|deduct|charge|debit|\brupee|rs\b|₹|inr)/i.test(t)) {
      if (/(nahi|ni|nhi|not|without)/i.test(t) || /(confirm|order|mil|receive|receive|show|hona|hua)/i.test(t)) {
        return {
          reply: 'Samajh gaya — payment kat gaya but order confirm nahi hua, right? Kya aapke paas transaction ID hai? (jaise TX48291)',
        }
      }
      return {
        reply: 'Payment ke baare mein batayein — amount kitna tha aur kis order ke liye? Kya aapke paas transaction ID hai?',
      }
    }

    if (/(order|booking|product|item|delivery|deliver|ship|track|status)/i.test(t)) {
      return {
        reply: 'Order issue, samajh gaya. Order ID ya transaction ID share karein, main abhi check karta hoon.',
      }
    }

    if (/(refund|wapas|wapas|return|cancel|cancellation)/i.test(t)) {
      return {
        reply: 'Refund ya return ke liye order ID ya transaction ID dijiye, main process karne ki koshish karta hoon.',
      }
    }

    if (/(thanks|thank|shukriya|dhanyavaad|theek|ok|okay|thik|accha)/i.test(t)) {
      return {
        reply: 'Koi baat nahi! Aur kuch help chahiye to batayega.',
      }
    }

    return {
      reply: 'Samajh raha hoon. Thoda aur detail bataiye — kis chiz ki problem hai? Payment, Order, ya kuch aur?',
    }
  }

  async function sendChatMessage() {
    const text = chatInput.trim()
    if (!text || chatSending) return

    setChatInput('')
    setChatSending(true)
    const userMsg = { role: 'user', content: text }
    setMessages(prev => [...prev, userMsg])

    let backendReply = null
    let backendEscalate = false
    let backendCaseId = null
    let usedBackend = false

    try {
      const res = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify({ message: text, channel: TEXT_CHANNEL }),
      })
      if (res.ok) {
        const contentType = res.headers.get('content-type') || ''
        if (contentType.includes('application/json')) {
          const data = await res.json()
          const replyText = typeof data.reply === 'string' ? data.reply.trim() : ''
          // Filter out LLM error strings that leaked into response
          const isErrorReply = /(llm error|api key|openai|groq|authentication|unauthorized|invalid_api_key)/i.test(replyText)
          if (replyText && !isErrorReply) {
            backendReply = replyText
            backendEscalate = !!data.escalated
            backendCaseId = data.case_id
            usedBackend = true
          } else if (replyText) {
            console.warn('[PRISM] Backend reply contained error text, falling back to demo reply:', replyText.slice(0, 100))
          }
        }
      }
    } catch (e) {}

    setTimeout(() => {
      let reply
      let escalate
      let caseId
      if (usedBackend && backendReply) {
        reply = backendReply
        escalate = backendEscalate
        caseId = backendCaseId
      } else {
        const demo = getDemoReply(text)
        reply = demo.reply
        escalate = demo.escalate
      }

      setMessages(prev => [...prev, { role: 'assistant', content: reply }])

      if (escalate) {
        const finalCaseId = caseId || 'PRISM-' + Math.floor(1040 + Math.random() * 50)
        setTimeout(() => {
          setEscalated(true)
          setEscalatedCaseId(finalCaseId)
          setMessages(prev => [...prev, {
            role: 'system',
            content: `Case escalated (${finalCaseId}). Tap "Dashboard" for agent view.`,
          }])
        }, 1000)
      }

      setChatSending(false)
    }, usedBackend ? 100 : 800)
  }

  function handleChatKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendChatMessage()
    }
  }

  const isConnected = status === 'connected'
  const isConnecting = status === 'connecting'
  const lastMessage = messages[messages.length - 1]

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'space-between',
      width: 520,
      minHeight: 720,
      padding: '36px 32px 32px',
      position: 'relative',
    }}>
      {/* Top bar - Status + mode toggle */}
      <div style={{
        width: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 8,
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '6px 18px',
          background: isConnected ? 'rgba(52,211,153,0.08)' : 'var(--bg-card)',
          border: `1px solid ${isConnected ? 'rgba(52,211,153,0.2)' : 'var(--border)'}`,
          borderRadius: 20,
        }}>
          <span className={`status-dot status-dot--${isConnected ? 'connected' : status === 'error' ? 'danger' : 'idle'}`} />
          <span style={{
            fontSize: 12,
            fontWeight: 600,
            color: isConnected ? 'var(--success)' : status === 'error' ? 'var(--danger)' : 'var(--text-secondary)',
            letterSpacing: 0.3,
          }}>
            {status === 'idle' && 'PRISM • IDLE'}
            {status === 'connecting' && 'PRISM • CONNECTING...'}
            {status === 'connected' && 'PRISM • CONNECTED'}
            {status === 'error' && 'PRISM • ERROR'}
          </span>
        </div>

        {/* Mode toggle */}
        <div style={{
          display: 'flex',
          background: 'var(--bg-card)',
          borderRadius: 10,
          padding: 3,
          border: '1px solid var(--border)',
        }}>
          {[
            { id: 'voice', label: '🎙️' },
            { id: 'chat', label: '⌨️' },
          ].map(m => (
            <button
              key={m.id}
              onClick={() => {
                if (isConnected) return
                setMode(m.id)
              }}
              disabled={isConnected}
              title={m.id === 'voice' ? 'Voice mode' : 'Chat mode'}
              style={{
                width: 36,
                height: 28,
                padding: 0,
                borderRadius: 8,
                border: 'none',
                background: mode === m.id ? 'var(--accent)' : 'transparent',
                color: mode === m.id ? '#fff' : 'var(--text-secondary)',
                fontSize: 13,
                cursor: isConnected ? 'not-allowed' : 'pointer',
                opacity: isConnected && mode !== m.id ? 0.35 : 1,
                transition: 'all 0.2s ease',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      {/* ════════════ VOICE MODE ════════════ */}
      {mode === 'voice' && (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 32,
          flex: 1,
          justifyContent: 'center',
          width: '100%',
        }}>
          {/* Logo + subtitle */}
          <div style={{ textAlign: 'center', userSelect: 'none' }}>
            <div style={{
              fontSize: 64,
              fontWeight: 800,
              letterSpacing: -3,
              background: 'var(--gradient-accent)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
              lineHeight: 1,
            }}>
              PRISM
            </div>
            <div style={{
              fontSize: 13,
              color: 'var(--text-secondary)',
              marginTop: 12,
              fontWeight: 400,
              letterSpacing: 0.5,
            }}>
              Multilingual AI Assistant
            </div>
          </div>

          {/* Conversation display */}
          {isConnected && messages.length > 0 && (
            <div className="fade-in" style={{
              width: '100%',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 20,
              maxWidth: 440,
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
              }}>
                <div style={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  background: agentActive ? 'var(--accent)' : 'var(--success)',
                  boxShadow: agentActive ? '0 0 12px var(--accent-glow)' : '0 0 8px var(--success-glow)',
                }} />
                <span style={{ fontSize: 12, color: 'var(--text-secondary)', fontWeight: 500 }}>
                  {agentActive ? 'PRISM speaking...' : 'Listening...'}
                </span>
              </div>

              {lastMessage && (
                <div className="slide-up" key={messages.length} style={{
                  padding: '20px 28px',
                  background: lastMessage.role === 'user'
                    ? 'linear-gradient(135deg, rgba(124,111,255,0.12) 0%, rgba(124,111,255,0.04) 100%)'
                    : 'var(--bg-card)',
                  border: `1px solid ${lastMessage.role === 'user' ? 'var(--border-accent)' : 'var(--border)'}`,
                  borderRadius: 16,
                  textAlign: 'center',
                  width: '100%',
                }}>
                  <div style={{
                    fontSize: 10,
                    fontWeight: 700,
                    letterSpacing: 2,
                    color: lastMessage.role === 'user' ? 'var(--accent-soft)' : 'var(--text-muted)',
                    marginBottom: 8,
                  }}>
                    {lastMessage.role === 'user' ? 'YOU' : 'PRISM'}
                  </div>
                  <div style={{
                    fontSize: 16,
                    lineHeight: 1.6,
                    color: 'var(--text-primary)',
                    fontWeight: lastMessage.role === 'assistant' ? 500 : 400,
                  }}>
                    "{lastMessage.content}"
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Idle / Listening wave */}
          {(!isConnected || messages.length === 0) && (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 20,
            }}>
              {/* Mic orb */}
              <div className={isConnected ? 'pulse-ring' : ''} style={{
                width: 120,
                height: 120,
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: isConnected
                  ? 'radial-gradient(circle, var(--accent-glow) 0%, rgba(124,111,255,0.05) 70%)'
                  : 'var(--bg-card)',
                border: `2px solid ${isConnected ? 'var(--accent)' : 'var(--border-strong)'}`,
                transition: 'all 0.4s ease',
              }}>
                <div style={{
                  width: 64,
                  height: 64,
                  borderRadius: '50%',
                  background: isConnected ? 'var(--gradient-accent)' : 'var(--bg-elevated)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 28,
                  opacity: isConnecting ? 0.5 : 1,
                }}>
                  {isConnecting ? '⟳' : isConnected ? '◉' : '◯'}
                </div>
              </div>

              {isConnected && (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
                  <span style={{ fontSize: 13, color: 'var(--text-secondary)', fontWeight: 500 }}>
                    Listening...
                  </span>
                  <div style={{
                    display: 'flex',
                    alignItems: 'flex-end',
                    gap: 2,
                    height: 32,
                  }}>
                    {waveformBars.map((h, i) => (
                      <div key={i} style={{
                        width: 3,
                        height: `${Math.max(4, h * 32)}px`,
                        borderRadius: 2,
                        background: 'linear-gradient(180deg, var(--accent) 0%, var(--accent-soft) 100%)',
                        opacity: 0.6 + h * 0.4,
                        transition: 'height 0.12s ease',
                      }} />
                    ))}
                  </div>
                  <div style={{
                    fontSize: 14,
                    color: 'var(--text-secondary)',
                    fontStyle: 'italic',
                    opacity: 0.7,
                  }}>
                    "Tell me what happened."
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ════════════ CHAT MODE ════════════ */}
      {mode === 'chat' && (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 16,
          flex: 1,
          width: '100%',
          minHeight: 0,
        }}>
          {/* Logo (smaller) */}
          <div style={{ textAlign: 'center', userSelect: 'none', padding: '4px 0 0' }}>
            <div style={{
              fontSize: 32,
              fontWeight: 800,
              letterSpacing: -1.5,
              background: 'var(--gradient-accent)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
              lineHeight: 1,
            }}>
              PRISM
            </div>
            <div style={{
              fontSize: 11,
              color: 'var(--text-secondary)',
              marginTop: 6,
              fontWeight: 400,
              letterSpacing: 0.5,
            }}>
              Type in Hindi, English, or Hinglish
            </div>
          </div>

          {/* Message area */}
          <div className="glass-panel" style={{
            flex: 1,
            minHeight: 340,
            padding: '16px 16px 8px',
            display: 'flex',
            flexDirection: 'column',
            gap: 12,
            overflowY: 'auto',
          }}>
            {!isConnected ? (
              <div style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 12,
                color: 'var(--text-muted)',
                padding: '20px',
              }}>
                <div style={{
                  width: 52,
                  height: 52,
                  borderRadius: '50%',
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 22,
                }}>
                  💬
                </div>
                <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-secondary)' }}>
                  Connect to start chatting
                </div>
                <div style={{
                  fontSize: 11,
                  textAlign: 'center',
                  maxWidth: 260,
                  lineHeight: 1.6,
                }}>
                  PRISM understands natural Hindi, English, and Hinglish — no language selection needed.
                </div>
              </div>
            ) : (
              <>
                {messages.map((msg, i) => (
                  <div key={i} className={i === messages.length - 1 ? 'fade-in' : ''} style={{
                    display: 'flex',
                    justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  }}>
                    {msg.role === 'system' ? (
                      <div style={{
                        width: '100%',
                        padding: '10px 14px',
                        background: 'rgba(248,113,113,0.08)',
                        borderRadius: 10,
                        border: '1px solid rgba(248,113,113,0.25)',
                        fontSize: 12,
                        color: 'var(--danger)',
                        textAlign: 'center',
                        fontWeight: 500,
                      }}>
                        🔴 {msg.content}
                      </div>
                    ) : (
                      <div style={{
                        maxWidth: '80%',
                        padding: '10px 14px',
                        borderRadius: msg.role === 'user' ? '14px 14px 4px 14px' : '14px 14px 14px 4px',
                        background: msg.role === 'user'
                          ? 'linear-gradient(135deg, rgba(124,111,255,0.22) 0%, rgba(124,111,255,0.08) 100%)'
                          : 'var(--bg-elevated)',
                        border: `1px solid ${msg.role === 'user' ? 'var(--border-accent)' : 'var(--border)'}`,
                        color: 'var(--text-primary)',
                        fontSize: 13,
                        lineHeight: 1.6,
                      }}>
                        {msg.role === 'assistant' && (
                          <div style={{
                            fontSize: 9,
                            fontWeight: 700,
                            letterSpacing: 1.5,
                            color: 'var(--accent-soft)',
                            marginBottom: 4,
                          }}>
                            PRISM
                          </div>
                        )}
                        {msg.content}
                      </div>
                    )}
                  </div>
                ))}

                {chatSending && (
                  <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
                    <div style={{
                      padding: '10px 16px',
                      background: 'var(--bg-elevated)',
                      borderRadius: '14px 14px 14px 4px',
                      border: '1px solid var(--border)',
                      fontSize: 18,
                      color: 'var(--text-secondary)',
                      display: 'flex',
                      alignItems: 'center',
                      height: 40,
                    }}>
                      <span className="typing-dots">
                        <span /><span /><span />
                      </span>
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </>
            )}
          </div>

          {/* Quick phrases */}
          {isConnected && (
            <div style={{
              display: 'flex',
              gap: 6,
              flexWrap: 'wrap',
            }}>
              {QUICK_PHRASES.map(phrase => (
                <button
                  key={phrase}
                  onClick={() => setChatInput(phrase)}
                  style={{
                    padding: '5px 12px',
                    borderRadius: 20,
                    border: '1px solid var(--border)',
                    background: 'var(--bg-card)',
                    color: 'var(--text-secondary)',
                    fontSize: 11,
                    cursor: 'pointer',
                    fontFamily: 'inherit',
                    transition: 'all 0.2s ease',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'var(--bg-elevated)'
                    e.currentTarget.style.color = 'var(--text-primary)'
                    e.currentTarget.style.borderColor = 'var(--border-strong)'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'var(--bg-card)'
                    e.currentTarget.style.color = 'var(--text-secondary)'
                    e.currentTarget.style.borderColor = 'var(--border)'
                  }}
                >
                  {phrase}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Bottom section */}
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 20,
        width: '100%',
        marginTop: mode === 'chat' ? 0 : 0,
      }}>
        {/* Escalation banner */}
        {escalated && (
          <div className="slide-up" style={{
            width: '100%',
            padding: '14px 20px',
            background: takenOver
              ? 'linear-gradient(135deg, rgba(52,211,153,0.12) 0%, rgba(52,211,153,0.04) 100%)'
              : 'linear-gradient(135deg, rgba(248,113,113,0.12) 0%, rgba(248,113,113,0.04) 100%)',
            border: takenOver
              ? '1px solid rgba(52,211,153,0.3)'
              : '1px solid rgba(248,113,113,0.3)',
            borderRadius: 12,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontSize: 14 }}>{takenOver ? '🟢' : '🔴'}</span>
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: takenOver ? 'var(--success)' : 'var(--danger)' }}>
                  {takenOver ? 'Human agent connected' : 'Connecting to human agent...'}
                </div>
                {escalatedCaseId && (
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2, fontFamily: 'monospace' }}>
                    Case: {escalatedCaseId}
                  </div>
                )}
              </div>
            </div>
            <a href="/agent" style={{
              fontSize: 12,
              color: 'var(--accent-soft)',
              textDecoration: 'none',
              fontWeight: 600,
            }}>
              Dashboard →
            </a>
          </div>
        )}

        {/* Error */}
        {error && (
          <div style={{
            padding: '10px 16px',
            background: 'rgba(248,113,113,0.08)',
            border: '1px solid rgba(248,113,113,0.2)',
            borderRadius: 10,
            fontSize: 12,
            color: 'var(--danger)',
            width: '100%',
            textAlign: 'center',
          }}>
            {error}
          </div>
        )}

        {/* Chat input (chat mode only) */}
        {mode === 'chat' && isConnected && (
          <div style={{
            width: '100%',
            display: 'flex',
            gap: 8,
            alignItems: 'flex-end',
          }}>
            <textarea
              value={chatInput}
              onChange={e => setChatInput(e.target.value)}
              onKeyDown={handleChatKeyDown}
              placeholder="Type your message..."
              rows={1}
              disabled={chatSending}
              style={{
                flex: 1,
                padding: '11px 16px',
                background: 'var(--bg-card)',
                border: '1px solid var(--border)',
                borderRadius: 12,
                color: 'var(--text-primary)',
                fontSize: 13,
                resize: 'none',
                outline: 'none',
                fontFamily: 'inherit',
                lineHeight: 1.5,
                maxHeight: 100,
                overflowY: 'auto',
                transition: 'border-color 0.2s ease',
              }}
              onFocus={(e) => e.currentTarget.style.borderColor = 'var(--border-accent)'}
              onBlur={(e) => e.currentTarget.style.borderColor = 'var(--border)'}
            />
            <button
              onClick={sendChatMessage}
              disabled={!chatInput.trim() || chatSending}
              aria-label="Send message"
              style={{
                width: 44,
                height: 44,
                borderRadius: 12,
                border: 'none',
                background: chatInput.trim() && !chatSending ? 'var(--gradient-accent)' : 'var(--bg-card)',
                color: chatInput.trim() && !chatSending ? '#fff' : 'var(--text-muted)',
                fontSize: 18,
                fontWeight: 700,
                cursor: chatInput.trim() && !chatSending ? 'pointer' : 'default',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.2s ease',
                flexShrink: 0,
                boxShadow: chatInput.trim() && !chatSending ? '0 4px 16px var(--accent-glow)' : 'none',
              }}
            >
              ↑
            </button>
          </div>
        )}

        {/* Main action button */}
        {mode === 'voice' ? (
          <button
            onClick={isConnected ? disconnect : connect}
            disabled={isConnecting}
            aria-label={isConnected ? 'Disconnect from PRISM' : 'Connect to PRISM'}
            style={{
              width: '100%',
              padding: '20px 32px',
              background: isConnected
                ? 'transparent'
                : 'var(--gradient-accent)',
              border: `2px solid ${isConnected ? 'var(--border-strong)' : 'transparent'}`,
              borderRadius: 16,
              color: '#fff',
              fontSize: 15,
              fontWeight: 600,
              cursor: isConnecting ? 'not-allowed' : 'pointer',
              opacity: isConnecting ? 0.6 : 1,
              transition: 'all 0.3s ease',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 12,
              letterSpacing: 0.3,
              boxShadow: !isConnected && !isConnecting ? '0 8px 32px var(--accent-glow)' : 'none',
            }}
            onMouseEnter={(e) => {
              if (!isConnected && !isConnecting) {
                e.currentTarget.style.transform = 'translateY(-2px)'
                e.currentTarget.style.boxShadow = '0 12px 40px var(--accent-glow-strong)'
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = !isConnected && !isConnecting ? '0 8px 32px var(--accent-glow)' : 'none'
            }}
          >
            <span style={{ fontSize: 20 }}>🎙️</span>
            <span>
              {status === 'idle' && 'Hold to speak / Speak naturally'}
              {status === 'connecting' && 'Connecting to PRISM...'}
              {status === 'connected' && 'End conversation'}
              {status === 'error' && 'Try again'}
            </span>
          </button>
        ) : (
          <button
            onClick={isConnected ? disconnect : connect}
            disabled={isConnecting}
            aria-label={isConnected ? 'End chat' : 'Start chat'}
            style={{
              width: '100%',
              padding: !isConnected ? '16px 32px' : '10px 24px',
              background: isConnected
                ? 'transparent'
                : 'var(--gradient-accent)',
              border: `2px solid ${isConnected ? 'var(--border-strong)' : 'transparent'}`,
              borderRadius: 14,
              color: isConnected ? 'var(--text-secondary)' : '#fff',
              fontSize: !isConnected ? 14 : 12,
              fontWeight: 600,
              cursor: isConnecting ? 'not-allowed' : 'pointer',
              opacity: isConnecting ? 0.6 : 1,
              transition: 'all 0.3s ease',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 10,
              letterSpacing: 0.3,
              boxShadow: !isConnected && !isConnecting ? '0 8px 32px var(--accent-glow)' : 'none',
              fontFamily: 'inherit',
            }}
          >
            <span style={{ fontSize: isConnected ? 14 : 18 }}>
              {isConnected ? '⏻' : '💬'}
            </span>
            <span>
              {status === 'idle' && 'Start conversation with PRISM'}
              {status === 'connecting' && 'Connecting...'}
              {status === 'connected' && 'End conversation'}
              {status === 'error' && 'Try again'}
            </span>
          </button>
        )}

        {/* Language note */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 12,
        }}>
          {['Hindi', 'English', 'Hinglish'].map((lang, i, arr) => (
            <span key={lang} style={{
              fontSize: 12,
              color: 'var(--text-muted)',
              fontWeight: 500,
              display: 'flex',
              alignItems: 'center',
              gap: 12,
            }}>
              {lang}
              {i < arr.length - 1 && (
                <span style={{ color: 'var(--border-strong)' }}>•</span>
              )}
            </span>
          ))}
        </div>

        {demoMode && isConnected && (
          <div style={{
            fontSize: 10,
            color: 'var(--text-muted)',
            opacity: 0.6,
            textAlign: 'center',
          }}>
            {mode === 'voice'
              ? 'Demo mode — conversation will auto-play'
              : 'Demo mode — type a message to begin'}
          </div>
        )}
      </div>
    </div>
  )
}
