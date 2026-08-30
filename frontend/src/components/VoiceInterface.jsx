import { useState, useRef, useEffect } from 'react'
import AgoraRTC from 'agora-rtc-sdk-ng'
import { getApiUrl } from '../lib/api'
import { LANGUAGES, DEFAULT_LANGUAGE, getLanguageConfig } from '../config/languages'
import { ttsManager } from '../lib/tts'
import ThinkingPanel from './ThinkingPanel'

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
  const [prismSpeaking, setPrismSpeaking] = useState(false)
  const [error, setError] = useState(null)
  const [escalated, setEscalated] = useState(false)
  const [takenOver, setTakenOver] = useState(false)
  const [escalatedCaseId, setEscalatedCaseId] = useState(null)
  const [messages, setMessages] = useState([])
  const [chatInput, setChatInput] = useState('')
  const [chatSending, setChatSending] = useState(false)
  const [demoMode, setDemoMode] = useState(false)
  const [waveformBars, setWaveformBars] = useState(Array(24).fill(0.2))
  const [voiceState, setVoiceState] = useState('IDLE')
  const [aiState, setAiState] = useState(null)
  const [turnId, setTurnId] = useState(null)
  const [micRecording, setMicRecording] = useState(false)
  const [asrTranscript, setAsrTranscript] = useState('')
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])

  const [selectedLanguage, setSelectedLanguage] = useState(() => {
    if (typeof window !== 'undefined') {
      return sessionStorage.getItem('prism_language') || DEFAULT_LANGUAGE
    }
    return DEFAULT_LANGUAGE
  })

  const clientRef = useRef(null)
  const micTrackRef = useRef(null)
  const sessionRef = useRef(null)
  const userUidRef = useRef(Math.floor(Math.random() * 90000) + 10000)
  const chatEndRef = useRef(null)
  const greetingPlayedRef = useRef(false)

  // Pre-warm TTS voices on mount so they are ready before first click.
  // Chrome/Edge load voices asynchronously — without this, the first
  // speak() call on page load finds an empty voice list and falls back
  // to the browser default (English), ignoring the selected locale.
  useEffect(() => {
    ttsManager._getVoicesReady().then(voices => {
      console.info(`[PRISM TTS] Pre-warmed: ${voices.length} voices available`)
    })
    return () => {
      cancelSpeech()
    }
  }, [])

  const cancelSpeech = () => {
    ttsManager.cancel()
    setPrismSpeaking(false)
  }

  const speakGreeting = (langKey) => {
    const config = getLanguageConfig(langKey)
    ttsManager.speak(config.greeting, langKey, {
      onStart: () => setPrismSpeaking(true),
      onEnd: () => setPrismSpeaking(false),
      onError: () => setPrismSpeaking(false),
    })
  }

  const handleLanguageChange = (langKey) => {
    if (status === 'connected' || status === 'connecting') return
    setSelectedLanguage(langKey)
    if (typeof window !== 'undefined') {
      sessionStorage.setItem('prism_language', langKey)
    }
    cancelSpeech()
  }

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
        const res = await fetch(getApiUrl(`/debug/case/${channel}`))
        const contentType = res.headers.get('content-type') || ''
        if (res.ok && contentType.includes('application/json')) {
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
          if (status !== 'connected' && !prismSpeaking) return 0.2
          return 0.2 + Math.random() * 0.8
        })
      )
      animationId = requestAnimationFrame(() => setTimeout(animate, 120))
    }
    animate()
    return () => cancelAnimationFrame(animationId)
  }, [status, prismSpeaking])

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
    setError(null)
    setStatus('connecting')

    // Trigger non-blocking spoken greeting on initial connect for this session
    if (!greetingPlayedRef.current) {
      greetingPlayedRef.current = true
      speakGreeting(selectedLanguage)
    }

    if (demoMode) {
      setVoiceState('CONNECTING')
      setTimeout(() => {
        setStatus('connected')
        setVoiceState('LISTENING')
        setMessages([{ role: 'assistant', content: 'Namaste! How can I help you today?' }])
      }, 1000)
      return
    }

    try {
      const uid = userUidRef.current
      const client = AgoraRTC.createClient({ mode: 'rtc', codec: 'vp8' })
      clientRef.current = client

      client.on('user-published', async (user, mediaType) => {
        await client.subscribe(user, mediaType)
        if (mediaType === 'audio') {
          user.audioTrack?.play()
          setAgentActive(true)
        }
      })
      client.on('user-unpublished', (user, mediaType) => {
        if (mediaType === 'audio') setAgentActive(false)
      })

      if (mode === 'voice') {
        const tokenResp = await fetch(getApiUrl(`/token?channel=${CHANNEL}&uid=${uid}`))
        if (!tokenResp.ok) throw new Error('Failed to fetch Agora token')
        const contentType = tokenResp.headers.get('content-type') || ''
        if (!contentType.includes('application/json')) {
          throw new Error('Backend server is offline or returned HTML page. Please ensure Python backend is running on port 8001.')
        }
        const tokenData = await tokenResp.json()

        await client.join(tokenData.app_id, CHANNEL, tokenData.token, uid)
        const micTrack = await AgoraRTC.createMicrophoneAudioTrack({ encoderConfig: 'speech_standard' })
        micTrackRef.current = micTrack
        await client.publish([micTrack])
      }

      try {
        const langConfig = getLanguageConfig(selectedLanguage)
        const sessionResp = await fetch(getApiUrl('/session/start'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            channel: mode === 'chat' ? TEXT_CHANNEL : CHANNEL,
            user_uid: uid,
            language: langConfig.name,
            locale: langConfig.locale,
          }),
        })
        if (sessionResp.ok) sessionRef.current = await sessionResp.json()
      } catch (e) {}

      setStatus('connected')
      setVoiceState('LISTENING')
    } catch (err) {
      setError(err.message || 'Connection failed')
      setStatus('error')
      cancelSpeech()
      micTrackRef.current?.close()
      await clientRef.current?.leave().catch(() => {})
      clientRef.current = null
      micTrackRef.current = null
    }
  }

  async function disconnect() {
    cancelSpeech()
    greetingPlayedRef.current = false
    setStatus('idle')
    setVoiceState('IDLE')
    setAiState(null)
    setAgentActive(false)
    setEscalated(false)
    setTakenOver(false)
    setEscalatedCaseId(null)
    setMessages([])
    try {
      if (sessionRef.current?.agent_id) {
        await fetch(getApiUrl('/session/stop'), {
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
    if (/(tx48291|48291)/i.test(t)) {
      return {
        reply: 'Maine TX48291 check kar liya hai. Payment ₹1,499 successful raha lekin order confirm nahi hua. Duplicate charge ki wajah se main ise human specialist ko escalate kar raha hoon.',
        escalate: true,
      }
    }
    if (/(kat gaya|payment|paise|deducted|paisa)/i.test(t)) {
      return {
        reply: 'Main aapki madad kar sakta hoon. Kya aapke paas aapka Transaction ID hai? (e.g. TX48291)',
        escalate: false,
      }
    }
    return {
      reply: `Samajh gaya. Aapne kaha: "${text}". Kya aap detail bta sakte hain ya Transaction ID share kar sakte hain?`,
      escalate: false,
    }
  }

  async function sendChatMessage(overrideText) {
    const text = (overrideText || chatInput).trim()
    if (!text || chatSending) return

    setChatInput('')
    setChatSending(true)
    setVoiceState('UNDERSTANDING')
    const userMsg = { role: 'user', content: text }
    setMessages(prev => [...prev, userMsg])

    let backendReply = null
    let backendEscalate = false
    let backendCaseId = null
    let backendAiState = null
    let backendTurnId = null
    let usedBackend = false

    try {
      setVoiceState('THINKING')
      const res = await fetch(getApiUrl('/chat'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify({
          message: text,
          channel: TEXT_CHANNEL,
          language: selectedLanguage,
        }),
      })
      if (res.ok) {
        const contentType = res.headers.get('content-type') || ''
        if (contentType.includes('application/json')) {
          const data = await res.json()
          const replyText = typeof data.reply === 'string' ? data.reply.trim() : ''
          const isErrorReply = /(llm error|api key|openai|groq|authentication|unauthorized|invalid_api_key)/i.test(replyText)
          if (replyText && !isErrorReply) {
            backendReply = replyText
            backendEscalate = !!data.escalated
            backendCaseId = data.case_id
            backendAiState = data.ai_state || null
            backendTurnId = data.turn_id || null
            usedBackend = true
          } else if (replyText) {
            console.warn('[PRISM] Backend reply contained error text, falling back to demo reply:', replyText.slice(0, 100))
          }
        }
      }
    } catch (e) {
      console.warn('[PRISM] Chat fetch error:', e.message)
      setVoiceState('LISTENING')
    }

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

    if (backendAiState) {
      setAiState(backendAiState)
      setVoiceState(backendAiState.phase || 'SPEAKING')
    } else {
      setVoiceState('SPEAKING')
    }
    if (backendTurnId) setTurnId(backendTurnId)

    if (escalate) {
      const finalCaseId = caseId || 'PRISM-' + Math.floor(1040 + Math.random() * 50)
      setVoiceState('ESCALATING')
      setTimeout(() => {
        setEscalated(true)
        setEscalatedCaseId(finalCaseId)
        setMessages(prev => [...prev, {
          role: 'system',
          content: `Case escalated (${finalCaseId}). Tap "Dashboard" for agent view.`,
        }])
      }, 1000)
    }

    // Transition back to LISTENING after speaking duration (content-length based, not fixed)
    const speakDuration = Math.min(3000, Math.max(800, (reply?.length || 50) * 45))
    setTimeout(() => {
      if (!escalate) setVoiceState('LISTENING')
    }, speakDuration)

    setChatSending(false)
  }

  function handleChatKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendChatMessage()
    }
  }

  // ── Mic-to-text via Faster Whisper ASR ─────────────────────────────
  async function startMicRecording() {
    if (micRecording) return
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      audioChunksRef.current = []
      recorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunksRef.current.push(e.data) }
      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop())
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        await sendToASR(blob)
      }
      recorder.start()
      mediaRecorderRef.current = recorder
      setMicRecording(true)
      setAsrTranscript('')
    } catch (e) {
      console.warn('[PRISM ASR] Mic access error:', e.message)
    }
  }

  function stopMicRecording() {
    if (!micRecording || !mediaRecorderRef.current) return
    mediaRecorderRef.current.stop()
    mediaRecorderRef.current = null
    setMicRecording(false)
  }

  async function sendToASR(audioBlob) {
    try {
      const formData = new FormData()
      formData.append('audio', audioBlob, 'recording.webm')
      formData.append('language', selectedLanguage === 'hi' ? 'hi' : 'en')
      const res = await fetch(getApiUrl('/asr'), { method: 'POST', body: formData })
      if (res.ok) {
        const data = await res.json()
        if (data.text && !data.error) {
          setChatInput(prev => (prev ? prev + ' ' + data.text : data.text).trim())
          setAsrTranscript(data.text)
        }
      }
    } catch (e) {
      console.warn('[PRISM ASR] Error:', e.message)
    }
  }

  const isConnected = status === 'connected'
  const isConnecting = status === 'connecting'
  const lastMessage = messages.filter(m => m.role !== 'system').slice(-1)[0]

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
      {/* Top bar - Status + Language Dropdown + Mode toggle */}
      <div style={{
        width: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 8,
        gap: 10,
      }}>
        {/* Status pill */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '6px 14px',
          background: isConnected ? 'rgba(52,211,153,0.08)' : 'var(--bg-card)',
          border: `1px solid ${isConnected ? 'rgba(52,211,153,0.2)' : 'var(--border)'}`,
          borderRadius: 20,
        }}>
          <span className={`status-dot status-dot--${prismSpeaking ? 'connecting' : isConnected ? 'connected' : status === 'error' ? 'danger' : 'idle'}`} />
          <span style={{
            fontSize: 12,
            fontWeight: 600,
            color: prismSpeaking ? 'var(--accent)' : isConnected ? 'var(--success)' : status === 'error' ? 'var(--danger)' : 'var(--text-secondary)',
            letterSpacing: 0.3,
          }}>
            {prismSpeaking && 'PRISM • SPEAKING'}
            {!prismSpeaking && status === 'idle' && 'PRISM • IDLE'}
            {!prismSpeaking && status === 'connecting' && 'PRISM • CONNECTING...'}
            {!prismSpeaking && status === 'connected' && 'PRISM • CONNECTED'}
            {!prismSpeaking && status === 'error' && 'PRISM • ERROR'}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {/* Language selector dropdown */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '4px 10px',
            background: 'var(--bg-card)',
            border: '1px solid var(--border)',
            borderRadius: 10,
          }}>
            <span style={{ fontSize: 13 }}>🌐</span>
            <select
              value={selectedLanguage}
              onChange={(e) => handleLanguageChange(e.target.value)}
              disabled={isConnected || isConnecting}
              aria-label="Select preferred language"
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-primary)',
                fontSize: 12,
                fontWeight: 600,
                outline: 'none',
                cursor: isConnected || isConnecting ? 'not-allowed' : 'pointer',
                fontFamily: 'inherit',
              }}
            >
              {Object.entries(LANGUAGES).map(([key, lang]) => (
                <option key={key} value={key} style={{ background: 'var(--bg-secondary)', color: 'var(--text-primary)' }}>
                  {lang.name} ({lang.locale})
                </option>
              ))}
            </select>
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
                  width: 34,
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
              Multilingual AI Support Engine
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
                  background: prismSpeaking ? 'var(--accent)' : agentActive ? 'var(--accent)' : 'var(--success)',
                  boxShadow: prismSpeaking ? '0 0 12px var(--accent-glow)' : agentActive ? '0 0 12px var(--accent-glow)' : '0 0 8px var(--success-glow)',
                }} />
                <span style={{ fontSize: 12, color: 'var(--text-secondary)', fontWeight: 500 }}>
                  {prismSpeaking ? 'PRISM speaking greeting...' : agentActive ? 'PRISM speaking...' : 'Listening...'}
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
              <div className={isConnected || prismSpeaking ? 'pulse-ring' : ''} style={{
                width: 140,
                height: 140,
                borderRadius: '50%',
                background: isConnected || prismSpeaking ? 'var(--gradient-accent)' : 'var(--bg-elevated)',
                border: `2px solid ${isConnected || prismSpeaking ? 'var(--border-accent)' : 'var(--border-strong)'}`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: isConnected || prismSpeaking
                  ? '0 0 60px var(--accent-glow-strong), inset 0 0 30px rgba(255,255,255,0.1)'
                  : '0 8px 32px rgba(0,0,0,0.3)',
                transition: 'all 0.5s cubic-bezier(0.4, 0, 0.2, 1)',
                cursor: isConnecting ? 'not-allowed' : 'pointer',
              }}
              onClick={isConnected ? disconnect : connect}
              >
                <div style={{
                  fontSize: 48,
                  filter: isConnected || prismSpeaking ? 'drop-shadow(0 2px 8px rgba(0,0,0,0.3))' : 'none',
                  transition: 'transform 0.3s ease',
                }}>
                  {status === 'connecting' ? '⏳' : isConnected ? '🎙️' : '🎙️'}
                </div>
              </div>

              {/* Status text */}
              <div style={{
                fontSize: 13,
                color: isConnected ? 'var(--success)' : 'var(--text-muted)',
                fontWeight: 500,
                letterSpacing: 0.5,
              }}>
                {prismSpeaking && 'PRISM ● Speaking initial greeting...'}
                {!prismSpeaking && status === 'idle' && 'Click microphone to connect'}
                {!prismSpeaking && status === 'connecting' && 'Establishing secure connection...'}
                {!prismSpeaking && status === 'connected' && 'PRISM is listening — speak naturally'}
                {!prismSpeaking && status === 'error' && 'Connection error — click to retry'}
              </div>

              {/* Realtime Waveform bars */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 4,
                height: 36,
              }}>
                {waveformBars.map((height, i) => (
                  <div
                    key={i}
                    style={{
                      width: 3,
                      height: `${Math.max(15, height * 100)}%`,
                      background: isConnected || prismSpeaking
                        ? `linear-gradient(180deg, var(--accent) 0%, var(--accent-soft) 100%)`
                        : 'var(--border-strong)',
                      borderRadius: 2,
                      transition: 'height 0.12s ease',
                      opacity: isConnected || prismSpeaking ? 0.4 + height * 0.6 : 0.3,
                    }}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ════════════ CHAT MODE ════════════ */}
      {mode === 'chat' && (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          width: '100%',
          flex: 1,
          gap: 16,
          minHeight: 0,
        }}>
          {/* Header */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            paddingBottom: 12,
            borderBottom: '1px solid var(--border)',
          }}>
            <div>
              <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>
                Text Support Chat
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                Direct text interface with PRISM engine
              </div>
            </div>

            <div style={{ display: 'flex', gap: 8 }}>
              {!demoMode && (
                <button
                  onClick={() => setDemoMode(true)}
                  style={{
                    padding: '5px 10px',
                    fontSize: 10,
                    fontWeight: 600,
                    borderRadius: 6,
                    border: '1px solid var(--border)',
                    background: 'var(--bg-elevated)',
                    color: 'var(--text-muted)',
                    cursor: 'pointer',
                  }}
                >
                  Enable Demo Mode
                </button>
              )}
            </div>
          </div>

          {/* Quick phrase chips */}
          <div style={{
            display: 'flex',
            gap: 6,
            flexWrap: 'wrap',
          }}>
            {QUICK_PHRASES.map(phrase => (
              <button
                key={phrase}
                onClick={() => {
                  if (!isConnected) connect()
                  sendChatMessage(phrase)
                }}
                style={{
                  padding: '5px 10px',
                  borderRadius: 16,
                  border: '1px solid var(--border)',
                  background: 'var(--bg-card)',
                  color: 'var(--text-secondary)',
                  fontSize: 11,
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  whiteSpace: 'nowrap',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = 'var(--border-accent)'
                  e.currentTarget.style.color = 'var(--accent-soft)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'var(--border)'
                  e.currentTarget.style.color = 'var(--text-secondary)'
                }}
              >
                {phrase}
              </button>
            ))}
          </div>

          {/* Messages list */}
          <div style={{
            flex: 1,
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: 12,
            paddingRight: 4,
            minHeight: 280,
            maxHeight: 380,
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
                  maxWidth: 280,
                  lineHeight: 1.6,
                }}>
                  PRISM supports all 22 Eighth Schedule Indian languages + English. Select your preferred language above.
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
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    fontSize: 12,
                    color: 'var(--text-muted)',
                  }}>
                    <span className="status-dot status-dot--connecting" />
                    PRISM is thinking...
                  </div>
                )}
                <div ref={chatEndRef} />
              </>
            )}
          </div>
        </div>
      )}

      {/* ThinkingPanel - live AI state (chat mode only, when not idle) */}
      {mode === 'chat' && voiceState !== 'IDLE' && (
        <div style={{ marginTop: 8, borderRadius: 12, border: '1px solid var(--border)', background: 'var(--bg-card)', overflow: 'hidden', maxHeight: 280, overflowY: 'auto' }}>
          <div style={{ padding: '8px 14px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: 2, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Live AI State</span>
          </div>
          <ThinkingPanel voiceState={voiceState} aiState={aiState} />
        </div>
      )}

      {/* Bottom controls & escalation banner */}
      <div style={{
        width: '100%',
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
        marginTop: 16,
      }}>
        {/* Escalation banner */}
        {escalated && (
          <div className="slide-up" style={{
            padding: '12px 16px',
            background: takenOver ? 'rgba(52,211,153,0.08)' : 'rgba(248,113,113,0.08)',
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
            <button
              onMouseDown={startMicRecording}
              onMouseUp={stopMicRecording}
              onTouchStart={startMicRecording}
              onTouchEnd={stopMicRecording}
              title="Hold to speak — transcribes Hindi/English to text"
              style={{
                width: 44, height: 44, borderRadius: 12, flexShrink: 0,
                border: `1px solid ${micRecording ? 'rgba(248,113,113,0.5)' : 'var(--border)'}`,
                background: micRecording ? 'rgba(248,113,113,0.15)' : 'var(--bg-card)',
                color: micRecording ? 'var(--danger)' : 'var(--text-secondary)',
                fontSize: 18, cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                transition: 'all 0.2s ease',
              }}
            >
              {micRecording ? '🔴' : '🎤'}
            </button>
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
              onClick={() => sendChatMessage()}
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
              {status === 'idle' && 'Click to Speak / Connect'}
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
          justifyContent: 'center',
          gap: 6,
        }}>
          <span style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 500 }}>
            Supports 22 Eighth Schedule Indian Languages + English
          </span>
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
