import pathlib

JSX = r"""
import { useState, useRef, useEffect } from 'react'
import AgoraRTC from 'agora-rtc-sdk-ng'
import { getApiUrl } from '../lib/api'
import { LANGUAGES, DEFAULT_LANGUAGE, getLanguageConfig } from '../config/languages'
import { ttsManager } from '../lib/tts'
import ThinkingPanel from './ThinkingPanel'
import { PRISM_STATE_CONFIG } from '../config/prismState'

const CHANNEL = 'prism-demo'
const TEXT_CHANNEL = 'prism-text'
const AGENT_UID = 12345
AgoraRTC.setLogLevel(3)

const DEMO_MESSAGES = [
  { role:'user',      content:'Mera payment kat gaya but order confirm nahi hua.', delay:2000 },
  { role:'assistant', content:'I can help with that. Do you have your transaction ID?', delay:3500 },
  { role:'user',      content:'Haan, TX48291 hai.', delay:5500 },
  { role:'assistant', content:'Let me check that.', delay:7000 },
  { role:'assistant', content:'Found Rs1499 transaction - payment success, order not confirmed. Connecting specialist.', delay:10000 },
]

const QUICK_PHRASES = [
  'Mera payment kat gaya',
  'TX48291',
  'Order confirm nahi hua',
  'Human se baat karni hai',
]

export default function VoiceInterface() {
  const [mode, setMode]               = useState('voice')
  const [status, setStatus]           = useState('idle')
  const [agentActive, setAgentActive] = useState(false)
  const [prismSpeaking, setPrismSpeaking] = useState(false)
  const [error, setError]             = useState(null)
  const [escalated, setEscalated]     = useState(false)
  const [takenOver, setTakenOver]     = useState(false)
  const [escalatedCaseId, setEscalatedCaseId] = useState(null)
  const [messages, setMessages]       = useState([])
  const [chatInput, setChatInput]     = useState('')
  const [chatSending, setChatSending] = useState(false)
  const [demoMode, setDemoMode]       = useState(false)
  const [waveformBars, setWaveformBars] = useState(Array(20).fill(0.2))
  const [voiceState, setVoiceState]   = useState('IDLE')
  const [aiState, setAiState]         = useState(null)
  const [turnId, setTurnId]           = useState(null)
  const [micRecording, setMicRecording] = useState(false)
  const [asrTranscript, setAsrTranscript] = useState('')
  const mediaRecorderRef = useRef(null)
  const audioChunksRef   = useRef([])
  const [selectedLanguage, setSelectedLanguage] = useState(() => {
    if (typeof window !== 'undefined') return sessionStorage.getItem('prism_language') || DEFAULT_LANGUAGE
    return DEFAULT_LANGUAGE
  })
  const clientRef         = useRef(null)
  const micTrackRef       = useRef(null)
  const sessionRef        = useRef(null)
  const userUidRef        = useRef(Math.floor(Math.random() * 90000) + 10000)
  const chatEndRef        = useRef(null)
  const greetingPlayedRef = useRef(false)

  useEffect(() => {
    ttsManager._getVoicesReady().then(v => console.info('[PRISM TTS] voices:', v.length))
    return () => cancelSpeech()
  }, [])

  const cancelSpeech = () => { ttsManager.cancel(); setPrismSpeaking(false) }
  const speakGreeting = langKey => {
    const c = getLanguageConfig(langKey)
    ttsManager.speak(c.greeting, langKey, { onStart:()=>setPrismSpeaking(true), onEnd:()=>setPrismSpeaking(false), onError:()=>setPrismSpeaking(false) })
  }
  const handleLanguageChange = langKey => {
    if (status === 'connected' || status === 'connecting') return
    setSelectedLanguage(langKey)
    if (typeof window !== 'undefined') sessionStorage.setItem('prism_language', langKey)
    cancelSpeech()
  }

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, mode])

  useEffect(() => {
    if (!escalated || takenOver || demoMode || mode !== 'chat') return
    let mounted = true
    const poll = async () => {
      try {
        const r = await fetch(getApiUrl('/debug/case/' + TEXT_CHANNEL))
        const ct = r.headers.get('content-type') || ''
        if (r.ok && ct.includes('application/json')) {
          const d = await r.json()
          if (d.case?.taken_over && mounted) { setTakenOver(true); setMessages(p => [...p, { role:'system', content:'A human agent has taken over.' }]) }
        }
      } catch {}
    }
    const iv = setInterval(poll, 3000)
    return () => { mounted = false; clearInterval(iv) }
  }, [escalated, takenOver, demoMode, mode])

  useEffect(() => {
    if (mode !== 'voice' || status !== 'connected' || demoMode) return
    let mounted = true
    const poll = async () => {
      try {
        const r = await fetch(getApiUrl('/state/' + CHANNEL))
        const ct = r.headers.get('content-type') || ''
        if (!r.ok || !ct.includes('application/json')) return
        const d = await r.json(); if (!mounted) return
        if (Array.isArray(d.transcript)) {
          const nxt = d.transcript.filter(m => m && m.content).map(m => ({ role:m.role, content:m.content }))
          if (d.taken_over) nxt.push({ role:'system', content:'A human agent has taken over.' })
          setMessages(nxt)
        }
        if (d.voice_state) setVoiceState(d.voice_state)
        if (d.ai_state)    setAiState(d.ai_state)
        if (d.escalated)   { setEscalated(true); if (d.case_id) setEscalatedCaseId(d.case_id) }
        if (d.taken_over)  setTakenOver(true)
      } catch {}
    }
    poll(); const iv = setInterval(poll, 1500); return () => { mounted = false; clearInterval(iv) }
  }, [mode, status, demoMode])

  useEffect(() => {
    let id
    function animate() {
      setWaveformBars(p => p.map(() => status !== 'connected' && !prismSpeaking ? 0.2 : 0.15 + Math.random() * 0.85))
      id = requestAnimationFrame(() => setTimeout(animate, 110))
    }
    animate(); return () => cancelAnimationFrame(id)
  }, [status, prismSpeaking])

  useEffect(() => {
    if (!demoMode || status !== 'connected' || mode !== 'voice') return
    const t = DEMO_MESSAGES.map(msg => setTimeout(() => {
      setMessages(p => [...p, { role:msg.role, content:msg.content }])
      if (msg.role === 'assistant') { setAgentActive(true); setTimeout(() => setAgentActive(false), 2000) }
      if (msg === DEMO_MESSAGES[DEMO_MESSAGES.length-1]) setTimeout(() => setEscalated(true), 1500)
    }, msg.delay))
    return () => t.forEach(clearTimeout)
  }, [demoMode, status, mode])

  async function connect() {
    setError(null); setStatus('connecting')
    if (!greetingPlayedRef.current) { greetingPlayedRef.current = true; speakGreeting(selectedLanguage) }
    if (demoMode) {
      setVoiceState('CONNECTING')
      setTimeout(() => { setStatus('connected'); setVoiceState('LISTENING'); setMessages([{ role:'assistant', content:'Namaste! How can I help you today?' }]) }, 1000)
      return
    }
    try {
      const uid = userUidRef.current
      const client = AgoraRTC.createClient({ mode:'rtc', codec:'vp8' }); clientRef.current = client
      client.on('user-published', async (u,mt) => { await client.subscribe(u,mt); if (mt==='audio') { u.audioTrack?.play(); setAgentActive(true) } })
      client.on('user-unpublished', (u,mt) => { if (mt==='audio') setAgentActive(false) })
      if (mode === 'voice') {
        const tr = await fetch(getApiUrl('/token?channel=' + CHANNEL + '&uid=' + uid))
        if (!tr.ok) throw new Error('Token fetch failed')
        const ct = tr.headers.get('content-type') || ''
        if (!ct.includes('application/json')) throw new Error('Backend offline — start it first')
        const td = await tr.json()
        await client.join(td.app_id, CHANNEL, td.token, uid)
        const mic = await AgoraRTC.createMicrophoneAudioTrack({ encoderConfig:'speech_standard' })
        micTrackRef.current = mic; await client.publish([mic])
      }
      try {
        const lc = getLanguageConfig(selectedLanguage)
        const sr = await fetch(getApiUrl('/session/start'), {
          method:'POST', headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ channel: mode==='chat' ? TEXT_CHANNEL : CHANNEL, user_uid:uid, language:lc.name, locale:lc.locale }),
        })
        if (sr.ok) sessionRef.current = await sr.json()
      } catch {}
      setStatus('connected'); setVoiceState('LISTENING')
    } catch (err) {
      setError(err.message || 'Connection failed'); setStatus('error'); cancelSpeech()
      micTrackRef.current?.close(); await clientRef.current?.leave().catch(()=>{})
      clientRef.current = null; micTrackRef.current = null
    }
  }

  async function disconnect() {
    cancelSpeech(); greetingPlayedRef.current = false
    setStatus('idle'); setVoiceState('IDLE'); setAiState(null); setAgentActive(false)
    setEscalated(false); setTakenOver(false); setEscalatedCaseId(null); setMessages([])
    try {
      if (sessionRef.current?.agent_id) await fetch(getApiUrl('/session/stop'), {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ agent_id:sessionRef.current.agent_id, channel: mode==='chat' ? TEXT_CHANNEL : CHANNEL }),
      }).catch(()=>{})
      micTrackRef.current?.close(); await clientRef.current?.leave().catch(()=>{})
    } catch {} finally { clientRef.current=null; micTrackRef.current=null; sessionRef.current=null }
  }

  function getDemoReply(text) {
    if (/(human|agent|baat karni)/i.test(text)) return { reply:'Theek hai, connecting human agent.', escalate:true }
    if (/(tx48291|48291)/i.test(text)) return { reply:'TX48291 verified: Rs1499 success, order not confirmed. Escalating.', escalate:true }
    if (/(kat gaya|payment|paise|deducted)/i.test(text)) return { reply:'Samajh gaya. Transaction ID share karein? (e.g. TX48291)', escalate:false }
    return { reply:'Samajh gaya. Transaction ID share karein?', escalate:false }
  }

  async function sendChatMessage(overrideText) {
    const text = (overrideText || chatInput).trim(); if (!text || chatSending) return
    setChatInput(''); setChatSending(true); setVoiceState('UNDERSTANDING')
    setMessages(p => [...p, { role:'user', content:text }])
    let bReply=null, bEsc=false, bCaseId=null, bAiState=null, bTurnId=null, usedBackend=false
    try {
      setVoiceState('THINKING')
      const r = await fetch(getApiUrl('/chat'), {
        method:'POST', headers:{'Content-Type':'application/json', Accept:'application/json'},
        body: JSON.stringify({ message:text, channel:TEXT_CHANNEL, language:selectedLanguage }),
      })
      if (r.ok) {
        const ct = r.headers.get('content-type') || ''
        if (ct.includes('application/json')) {
          const d = await r.json()
          const rt = typeof d.reply === 'string' ? d.reply.trim() : ''
          const isErr = /(llm error|api key|openai|groq|authentication|unauthorized|invalid_api_key)/i.test(rt)
          if (rt && !isErr) { bReply=rt; bEsc=!!d.escalated; bCaseId=d.case_id; bAiState=d.ai_state||null; bTurnId=d.turn_id||null; usedBackend=true }
          else if (rt) console.warn('[PRISM] error reply')
        }
      }
    } catch (e) { console.warn('[PRISM]', e.message); setVoiceState('LISTENING') }
    const { reply, escalate } = usedBackend && bReply ? { reply:bReply, escalate:bEsc } : getDemoReply(text)
    setMessages(p => [...p, { role:'assistant', content:reply }])
    if (bAiState) { setAiState(bAiState); setVoiceState(bAiState.phase||'SPEAKING') } else setVoiceState('SPEAKING')
    if (bTurnId) setTurnId(bTurnId)
    if (escalate) {
      const fid = bCaseId || 'PRISM-' + Math.floor(1040 + Math.random()*50)
      setVoiceState('ESCALATING')
      setTimeout(() => { setEscalated(true); setEscalatedCaseId(fid); setMessages(p=>[...p,{role:'system',content:'Case escalated ('+fid+'). Open dashboard.'}]) }, 900)
    }
    setTimeout(() => { if (!escalate) setVoiceState('LISTENING') }, Math.min(3000, Math.max(800, (reply?.length||50)*45)))
    setChatSending(false)
  }

  function handleChatKeyDown(e) { if (e.key==='Enter' && !e.shiftKey) { e.preventDefault(); sendChatMessage() } }

  async function startMicRecording() {
    if (micRecording) return
    try {
      const s = await navigator.mediaDevices.getUserMedia({ audio:true })
      const rec = new MediaRecorder(s, { mimeType:'audio/webm' })
      audioChunksRef.current = []
      rec.ondataavailable = e => { if (e.data.size>0) audioChunksRef.current.push(e.data) }
      rec.onstop = async () => { s.getTracks().forEach(t=>t.stop()); await sendToASR(new Blob(audioChunksRef.current,{type:'audio/webm'})) }
      rec.start(); mediaRecorderRef.current = rec; setMicRecording(true); setAsrTranscript('')
    } catch (e) { console.warn('[ASR]', e.message) }
  }
  function stopMicRecording() {
    if (!micRecording || !mediaRecorderRef.current) return
    mediaRecorderRef.current.stop(); mediaRecorderRef.current = null; setMicRecording(false)
  }
  async function sendToASR(blob) {
    try {
      const fd = new FormData(); fd.append('audio', blob, 'r.webm'); fd.append('language', selectedLanguage==='hi'?'hi':'en')
      const r = await fetch(getApiUrl('/asr'), { method:'POST', body:fd })
      if (r.ok) { const d = await r.json(); if (d.text && !d.error) { setChatInput(p=>(p?p+' '+d.text:d.text).trim()); setAsrTranscript(d.text) } }
    } catch (e) { console.warn('[ASR]', e.message) }
  }

  const isConnected  = status === 'connected'
  const isConnecting = status === 'connecting'
  const lastMsg = messages.filter(m => m.role !== 'system').slice(-1)[0]
  const scfg = PRISM_STATE_CONFIG[voiceState] || PRISM_STATE_CONFIG.IDLE
  const orbClass = 'voice-orb voice-orb--' + voiceState.toLowerCase()
  const sc = voiceState==='ESCALATING'?'var(--danger)':voiceState==='HUMAN_CONNECTED'?'var(--ok)':voiceState==='ACTING'?'var(--warn)':'var(--text-primary)'

  return (
    <div style={{ background:'var(--surface-0)', border:'1px solid var(--border)', borderRadius:'var(--r-xl)', boxShadow:'var(--shadow-md)', overflow:'hidden', width:'100%' }}>

      {/* Top bar */}
      <div style={{ padding:'14px 20px', borderBottom:'1px solid var(--border)', display:'flex', alignItems:'center', justifyContent:'space-between', gap:12 }}>
        <div style={{ display:'flex', alignItems:'center', gap:8 }}>
          <span style={{ width:7, height:7, borderRadius:'50%', display:'inline-block', background:isConnected?sc:'var(--text-muted)', flexShrink:0 }} />
          <span style={{ fontSize:12, fontWeight:600, color:isConnected?sc:'var(--text-tertiary)', letterSpacing:'0.04em', textTransform:'uppercase' }}>
            {isConnecting ? 'Connecting...' : isConnected ? scfg.label : 'PRISM'}
          </span>
        </div>
        <div style={{ display:'flex', alignItems:'center', gap:8 }}>
          <div style={{ padding:'4px 10px', background:'var(--surface-1)', border:'1px solid var(--border)', borderRadius:'var(--r-md)' }}>
            <select value={selectedLanguage} onChange={e=>handleLanguageChange(e.target.value)} disabled={isConnected||isConnecting}
              style={{ background:'transparent', border:'none', color:'var(--text-primary)', fontSize:12, fontWeight:500, outline:'none', cursor:isConnected||isConnecting?'not-allowed':'pointer', fontFamily:'inherit' }}>
              {Object.entries(LANGUAGES).map(([k,l]) => (
                <option key={k} value={k} style={{ background:'#fff' }}>{l.name}</option>
              ))}
            </select>
          </div>
          <div style={{ display:'flex', background:'var(--surface-1)', borderRadius:'var(--r-md)', padding:2, border:'1px solid var(--border)' }}>
            {[{id:'voice',icon:'Voice'},{id:'chat',icon:'Text'}].map(m => (
              <button key={m.id} onClick={()=>{ if(!isConnected) setMode(m.id) }} disabled={isConnected}
                style={{ padding:'4px 10px', borderRadius:'var(--r-sm)', border:'none', background:mode===m.id?'var(--text-primary)':'transparent', color:mode===m.id?'white':'var(--text-tertiary)', fontSize:11, fontWeight:600, cursor:isConnected?'not-allowed':'pointer', opacity:isConnected&&mode!==m.id?0.3:1, transition:'all 0.15s ease', fontFamily:'inherit' }}>
                {m.icon}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Voice mode */}
      {mode === 'voice' && (
        <div style={{ padding:'36px 24px', display:'flex', flexDirection:'column', alignItems:'center', gap:28, minHeight:440 }}>
          <div style={{ textAlign:'center', userSelect:'none' }}>
            <div style={{ fontSize:44, fontWeight:700, letterSpacing:'-0.04em', color:'var(--text-primary)', lineHeight:1 }}>PRISM</div>
            <div style={{ fontSize:12, color:'var(--text-tertiary)', marginTop:6 }}>Multilingual AI Support</div>
          </div>
          <div style={{ display:'flex', flexDirection:'column', alignItems:'center', gap:16 }}>
            <div className={orbClass} style={{ width:120, height:120 }} onClick={isConnected ? disconnect : connect} role="button" aria-label={isConnected?'Disconnect':'Connect'}>
              <span style={{ fontSize:20, color:'var(--text-secondary)', userSelect:'none' }}>
                {voiceState==='IDLE'&&'\uD83C\uDFA4'}
                {voiceState==='LISTENING'&&'\u25CF'}
                {voiceState==='THINKING'&&'\u25CB'}
                {voiceState==='ACTING'&&'\u2192'}
                {voiceState==='SPEAKING'&&'\u25C9'}
                {voiceState==='ESCALATING'&&'!'}
                {voiceState==='HUMAN_CONNECTED'&&'\u2713'}
              </span>
            </div>
            <div className="waveform">
              {waveformBars.map((h,i) => (
                <div key={i} className={'waveform__bar' + (isConnected?' waveform__bar--active':'')} style={{ height: Math.max(3,h*100)+'%' }} />
              ))}
            </div>
          </div>
          {isConnected && lastMsg && (
            <div className="slide-up" key={messages.length} style={{ width:'100%', maxWidth:400, padding:'16px 20px', background:'var(--surface-1)', border:'1px solid var(--border)', borderRadius:'var(--r-lg)', textAlign:'center' }}>
              <div className="t-label" style={{ color:'var(--text-muted)', marginBottom:8 }}>{lastMsg.role==='user'?'YOU':'PRISM'}</div>
              <div style={{ fontSize:15, lineHeight:1.6, color:'var(--text-primary)', fontWeight:lastMsg.role==='assistant'?500:400 }}>"{lastMsg.content}"</div>
            </div>
          )}
          <div style={{ fontSize:13, color:'var(--text-tertiary)', textAlign:'center', minHeight:18 }}>
            {prismSpeaking && 'Speaking...'}
            {!prismSpeaking && status==='idle' && 'Click the orb to connect'}
            {!prismSpeaking && status==='connecting' && 'Establishing connection...'}
            {!prismSpeaking && status==='connected' && 'Speak naturally — Hindi, English or Hinglish'}
            {!prismSpeaking && status==='error' && <span style={{ color:'var(--danger)' }}>{error}</span>}
          </div>
        </div>
      )}

      {/* Chat mode */}
      {mode === 'chat' && (
        <div style={{ display:'flex', flexDirection:'column', minHeight:480 }}>
          <div style={{ padding:'12px 16px 8px', display:'flex', gap:6, flexWrap:'wrap', borderBottom:'1px solid var(--border-subtle)' }}>
            {QUICK_PHRASES.map(p => (
              <button key={p} onClick={()=>{ if(!isConnected) connect(); sendChatMessage(p) }}
                style={{ padding:'4px 10px', borderRadius:'var(--r-full)', border:'1px solid var(--border)', background:'var(--surface-0)', color:'var(--text-secondary)', fontSize:11, fontWeight:500, cursor:'pointer', whiteSpace:'nowrap', fontFamily:'inherit', transition:'all 0.15s ease' }}
                onMouseEnter={e=>{ e.currentTarget.style.borderColor='var(--border-strong)'; e.currentTarget.style.color='var(--text-primary)' }}
                onMouseLeave={e=>{ e.currentTarget.style.borderColor='var(--border)'; e.currentTarget.style.color='var(--text-secondary)' }}>
                {p}
              </button>
            ))}
          </div>
          <div style={{ flex:1, overflowY:'auto', padding:'16px', maxHeight:320 }}>
            {!isConnected ? (
              <div style={{ display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', gap:10, padding:'32px 20px', textAlign:'center', height:'100%' }}>
                <div style={{ width:44, height:44, borderRadius:'50%', background:'var(--surface-2)', border:'1px solid var(--border)', display:'flex', alignItems:'center', justifyContent:'center', fontSize:18 }}>&#128172;</div>
                <div style={{ fontSize:13, fontWeight:500, color:'var(--text-secondary)' }}>Connect to start chatting</div>
                <div style={{ fontSize:11, color:'var(--text-muted)', maxWidth:240, lineHeight:1.6 }}>Hindi, English, and Hinglish supported</div>
              </div>
            ) : (
              <div className="transcript">
                {messages.map((msg,i) => {
                  if (msg.role==='system') return (
                    <div key={i} className="fade-in" style={{ padding:'8px 12px', background:'var(--danger-bg)', border:'1px solid var(--danger-border)', borderRadius:'var(--r-md)', fontSize:12, color:'var(--danger)', textAlign:'center', marginBottom:8 }}>
                      {msg.content}
                    </div>
                  )
                  return (
                    <div key={i} className={'transcript-line transcript-line--' + (msg.role==='user'?'user':'agent') + (i===messages.length-1?' fade-in':'')}>
                      <div className="transcript-line__meta">{msg.role==='user'?<span>YOU</span>:<span>PRISM</span>}</div>
                      <div className="transcript-line__bubble">{msg.content}</div>
                    </div>
                  )
                })}
                {chatSending && (
                  <div style={{ display:'flex', alignItems:'center', gap:8, padding:'4px 0' }}>
                    <span className="status-dot status-dot--muted status-dot--pulse" />
                    <span style={{ fontSize:12, color:'var(--text-muted)' }}>Thinking...</span>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>
            )}
          </div>
          {isConnected && voiceState !== 'IDLE' && (
            <div style={{ borderTop:'1px solid var(--border-subtle)', maxHeight:220, overflowY:'auto' }}>
              <ThinkingPanel voiceState={voiceState} aiState={aiState} compact />
            </div>
          )}
        </div>
      )}

      {escalated && (
        <div className="slide-up" style={{ margin:'0 16px 8px', padding:'12px 16px', background:takenOver?'var(--ok-bg)':'var(--danger-bg)', border:'1px solid '+(takenOver?'var(--ok-border)':'var(--danger-border)'), borderRadius:'var(--r-lg)', display:'flex', alignItems:'center', justifyContent:'space-between' }}>
          <div style={{ display:'flex', alignItems:'center', gap:10 }}>
            <span style={{ width:7, height:7, borderRadius:'50%', display:'inline-block', background:takenOver?'var(--ok)':'var(--danger)', flexShrink:0 }} />
            <div>
              <div style={{ fontSize:13, fontWeight:600, color:takenOver?'var(--ok)':'var(--danger)' }}>{takenOver?'Human agent connected':'Connecting to human agent...'}</div>
              {escalatedCaseId && <div style={{ fontSize:11, color:'var(--text-tertiary)', marginTop:1, fontFamily:'var(--font-mono)' }}>{escalatedCaseId}</div>}
            </div>
          </div>
          <a href="/agent" style={{ fontSize:12, color:'var(--text-secondary)', textDecoration:'none', fontWeight:500 }}
            onMouseEnter={e=>e.currentTarget.style.color='var(--text-primary)'}
            onMouseLeave={e=>e.currentTarget.style.color='var(--text-secondary)'}>Dashboard &rarr;</a>
        </div>
      )}

      {error && !isConnected && (
        <div style={{ margin:'0 16px 8px', padding:'10px 14px', background:'var(--danger-bg)', border:'1px solid var(--danger-border)', borderRadius:'var(--r-md)', fontSize:12, color:'var(--danger)', textAlign:'center' }}>{error}</div>
      )}

      <div style={{ padding:'12px 16px 16px', display:'flex', flexDirection:'column', gap:8, borderTop:'1px solid var(--border-subtle)' }}>
        {mode==='chat' && isConnected && (
          <div style={{ display:'flex', gap:6, alignItems:'flex-end' }}>
            <button onMouseDown={startMicRecording} onMouseUp={stopMicRecording} onTouchStart={startMicRecording} onTouchEnd={stopMicRecording}
              style={{ width:36, height:36, borderRadius:'var(--r-md)', border:'1px solid '+(micRecording?'var(--danger-border)':'var(--border)'), background:micRecording?'var(--danger-bg)':'var(--surface-1)', color:micRecording?'var(--danger)':'var(--text-tertiary)', fontSize:14, cursor:'pointer', display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }}>
              {micRecording?'REC':'\uD83C\uDFA4'}
            </button>
            <textarea value={chatInput} onChange={e=>setChatInput(e.target.value)} onKeyDown={handleChatKeyDown}
              placeholder="Type your message..." rows={1} disabled={chatSending}
              style={{ flex:1, padding:'9px 14px', background:'var(--surface-1)', border:'1px solid var(--border)', borderRadius:'var(--r-md)', color:'var(--text-primary)', fontSize:13, resize:'none', outline:'none', fontFamily:'inherit', lineHeight:1.5, maxHeight:90, overflowY:'auto' }}
              onFocus={e=>e.currentTarget.style.borderColor='var(--border-strong)'}
              onBlur={e=>e.currentTarget.style.borderColor='var(--border)'} />
            <button onClick={()=>sendChatMessage()} disabled={!chatInput.trim()||chatSending}
              style={{ width:36, height:36, borderRadius:'var(--r-md)', border:'none', background:chatInput.trim()&&!chatSending?'var(--text-primary)':'var(--surface-2)', color:chatInput.trim()&&!chatSending?'white':'var(--text-muted)', fontSize:14, fontWeight:700, cursor:chatInput.trim()&&!chatSending?'pointer':'default', display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }}>
              &#8593;
            </button>
          </div>
        )}
        <button onClick={isConnected?disconnect:connect} disabled={isConnecting}
          className={isConnected?'btn btn--secondary btn--lg':'btn btn--primary btn--lg'}
          style={{ width:'100%', justifyContent:'center', gap:10 }}>
          <span>
            {status==='idle'&&(mode==='voice'?'Connect Voice':'Start Chat')}
            {status==='connecting'&&'Connecting...'}
            {status==='connected'&&'End Conversation'}
            {status==='error'&&'Try Again'}
          </span>
        </button>
        <div style={{ textAlign:'center', fontSize:11, color:'var(--text-muted)' }}>Hindi &bull; English &bull; Hinglish</div>
      </div>
    </div>
  )
}
""".strip()

import pathlib
pathlib.Path(r'd:/WORK AND STUDY/PRISM/frontend/src/components/VoiceInterface.jsx').write_text(JSX, encoding='utf-8')
print('VoiceInterface.jsx written', len(JSX), 'chars')