import pathlib

JSX = r"""
import { useState, useEffect, useRef } from 'react'
import AgoraRTC from 'agora-rtc-sdk-ng'
import EscalationPanel from '../components/EscalationPanel'
import CasePanel from '../components/CasePanel'
import AIActionPanel from '../components/AIActionPanel'
import ThinkingPanel from '../components/ThinkingPanel'
import { getApiUrl } from '../lib/api'

const DEMO_CASES = [
  {
    case_id:'PRISM-1042', created_at:new Date(Date.now()-180000).toISOString(), status:'ESCALATED',
    escalated:true, taken_over:false, intent:'Payment Issue',
    issue:'Payment deducted but order not confirmed',
    issue_summary:'Paise kat gaye but order confirm nahi hua',
    language:['Hindi','English'], transaction_id:'TX48291', amount:1499,
    payment_status:'SUCCESS', order_status:'NOT_CONFIRMED',
    confidence_display:41, confidence_label:'CRITICAL_UNKNOWN',
    confidence_fields:{ transaction_id:'HIGH', amount:'HIGH', payment_status:'HIGH', order_status:'HIGH', duplicate_charge:'CRITICAL_UNKNOWN' },
    summary:'Customer reports successful payment of Rs1,499 (TX48291) but order not confirmed. AI verified via API but could not rule out duplicate charge.',
    reason_for_escalation:'Unable to determine whether customer was charged twice. Duplicate charge CRITICAL_UNKNOWN.',
    unverified:['duplicate_charge'],
  },
  {
    case_id:'PRISM-1041', created_at:new Date(Date.now()-600000).toISOString(), status:'LIVE',
    escalated:false, taken_over:false, intent:'Order Issue',
    issue:'Order tracking not updating', language:['English'],
    confidence_display:78, confidence_label:'MEDIUM',
  },
  {
    case_id:'PRISM-1039', created_at:new Date(Date.now()-1800000).toISOString(), status:'RESOLVED',
    escalated:true, taken_over:true, intent:'Refund Request',
    issue:'Refund not received after 7 days', language:['Hinglish'],
    confidence_display:92, confidence_label:'HIGH',
  },
]

const DEMO_CONV = [
  { role:'user',      content:'Bhai mera payment ka issue hai. Paise kat gaye but order confirm nahi hua.', time:'2:31 PM', delay:500 },
  { role:'assistant', content:'I can help with that. Do you have your transaction ID?', time:'2:31 PM', delay:2000 },
  { role:'user',      content:'Haan, TX48291 hai.', time:'2:32 PM', delay:4500 },
  { role:'assistant', content:'Let me check that transaction for you.', time:'2:32 PM', delay:6500, thinking:true },
  { role:'tool-action', time:'2:32 PM', delay:8000 },
  { role:'assistant', content:'Found Rs1,499 transaction — payment successful but order not confirmed. Not confident about duplicate charge, connecting specialist.', time:'2:33 PM', delay:13000 },
  { role:'escalation', delay:16000 },
]

const NAV = [
  { id:'overview', label:'Overview' },
  { id:'cases',    label:'Live Cases' },
  { id:'history',  label:'History' },
]

const SYS_STATUS = [
  { id:'agora',      label:'Agora' },
  { id:'ai-agent',   label:'AI Agent' },
  { id:'tools',      label:'Tools' },
  { id:'escalation', label:'Escalation' },
]

export default function Agent() {
  const [cases, setCases]             = useState([])
  const [activeCaseId, setActiveCaseId] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [backendError, setBackendError] = useState(null)
  const [demoMessages, setDemoMessages] = useState([])
  const [showToolAction, setShowToolAction] = useState(false)
  const [showEscalation, setShowEscalation] = useState(false)
  const [demoMode, setDemoMode]       = useState(true)
  const [agentAudioConnected, setAgentAudioConnected] = useState(false)
  const [agentMuted, setAgentMuted]   = useState(false)
  const [liveVoiceState, setLiveVoiceState] = useState('IDLE')
  const [liveAiState, setLiveAiState] = useState(null)
  const [activeNav, setActiveNav]     = useState('cases')
  const agentClientRef = useRef(null)
  const agentMicRef    = useRef(null)
  const convEndRef     = useRef(null)

  const handleAgentAgoraJoin = async (targetChannel = 'prism-demo') => {
    try {
      const AGENT_UID = 88888
      const tr = await fetch(getApiUrl('/token?channel='+targetChannel+'&uid='+AGENT_UID))
      if (!tr.ok) return
      const ct = tr.headers.get('content-type')||''
      if (!ct.includes('application/json')) return
      const td = await tr.json()
      const client = AgoraRTC.createClient({ mode:'rtc', codec:'vp8' }); agentClientRef.current = client
      client.on('user-published', async (u,mt) => { await client.subscribe(u,mt); if(mt==='audio') u.audioTrack?.play() })
      await client.join(td.app_id, targetChannel, td.token, AGENT_UID)
      try {
        const mic = await AgoraRTC.createMicrophoneAudioTrack({ encoderConfig:'speech_standard' })
        agentMicRef.current = mic; await client.publish([mic])
      } catch {}
      setAgentAudioConnected(true)
    } catch (e) { console.warn('[Agent] Agora error:', e) }
  }

  const disconnectAgentAudio = async () => {
    try { agentMicRef.current?.close(); await agentClientRef.current?.leave() } catch {}
    agentClientRef.current = null; agentMicRef.current = null; setAgentAudioConnected(false)
  }

  const toggleAgentMute = () => {
    if (agentMicRef.current) { const m = !agentMuted; agentMicRef.current.setEnabled(!m); setAgentMuted(m) }
  }

  useEffect(() => {
    let mounted = true
    async function poll() {
      try {
        const r = await fetch(getApiUrl('/cases'))
        if (!r.ok) throw new Error(r.status)
        const ct = r.headers.get('content-type')||''
        if (!ct.includes('application/json')) throw new Error('non-json')
        const d = await r.json()
        if (mounted) {
          const all = d.cases||[]
          setCases(all); setDemoMode(all.length===0)
          if (!activeCaseId && all.length>0) setActiveCaseId((all.find(c=>!c.taken_over)||all[0]).case_id)
          setLastUpdated(new Date()); setBackendError(null)
        }
      } catch {
        if (mounted) { setDemoMode(true); setCases(DEMO_CASES); if(!activeCaseId) setActiveCaseId('PRISM-1042'); setLastUpdated(new Date()) }
      }
    }
    poll(); const iv = setInterval(poll, 3000); return () => { mounted=false; clearInterval(iv) }
  }, [activeCaseId])

  useEffect(() => {
    if (!activeCaseId || demoMode) return
    let mounted = true
    const pollState = async () => {
      try {
        const r = await fetch(getApiUrl('/active-state'))
        if (!r.ok) return
        const ct = r.headers.get('content-type')||''
        if (!ct.includes('application/json')) return
        const d = await r.json()
        if (mounted) { setLiveVoiceState(d.voice_state||'IDLE'); setLiveAiState(d.ai_state||null) }
      } catch {}
    }
    pollState(); const si = setInterval(pollState, 2000); return () => { mounted=false; clearInterval(si) }
  }, [activeCaseId, demoMode])

  useEffect(() => {
    if (!demoMode) return
    setDemoMessages([]); setShowToolAction(false); setShowEscalation(false)
    const timers = DEMO_CONV.map(msg => setTimeout(() => {
      if (msg.role==='tool-action') setShowToolAction(true)
      else if (msg.role==='escalation') setShowEscalation(true)
      else setDemoMessages(p => [...p, msg])
    }, msg.delay))
    return () => timers.forEach(clearTimeout)
  }, [demoMode, activeCaseId])

  useEffect(() => { convEndRef.current?.scrollIntoView({ behavior:'smooth' }) }, [demoMessages])

  const displayCases = cases.length>0 ? cases : DEMO_CASES
  const activeCase   = displayCases.find(c=>c.case_id===activeCaseId) || displayCases[0]
  const activeCases  = displayCases.filter(c=>!c.taken_over && c.escalated)
  const resolvedCases = displayCases.filter(c=>c.taken_over)
  const liveCases    = displayCases.filter(c=>!c.taken_over)

  const caseStatusColor = c => c.taken_over?'var(--ok)':c.escalated?'var(--danger)':c.status==='LIVE'?'var(--warn)':'var(--text-muted)'
  const caseStatusLabel = c => c.taken_over?'Resolved':c.escalated?'Escalated':c.status||'Live'

  // Sidebar
  const Sidebar = () => (
    <aside style={{ background:'var(--dark-1)', borderRight:'1px solid var(--dark-border)', display:'flex', flexDirection:'column', height:'100%', overflow:'hidden' }}>
      <div style={{ padding:'20px 18px 16px', borderBottom:'1px solid var(--dark-border)' }}>
        <div style={{ fontSize:20, fontWeight:700, letterSpacing:'-0.03em', color:'var(--dark-text-primary)', marginBottom:6 }}>PRISM</div>
        <div style={{ display:'flex', alignItems:'center', gap:6 }}>
          <span className="status-dot status-dot--ok" />
          <span style={{ fontSize:10, color:'var(--ok)', fontWeight:600, letterSpacing:'0.05em', textTransform:'uppercase' }}>ONLINE</span>
        </div>
      </div>

      <div style={{ padding:'16px 10px', flex:1, overflowY:'auto' }}>
        <div style={{ fontSize:9, fontWeight:600, letterSpacing:'0.1em', textTransform:'uppercase', color:'var(--dark-text-muted)', padding:'0 8px 8px' }}>Menu</div>
        {NAV.map(item => (
          <button key={item.id} onClick={()=>setActiveNav(item.id)}
            className={'nav-item' + (activeNav===item.id?' nav-item--active':'')}>
            <span style={{ width:6, height:6, borderRadius:'50%', background: activeNav===item.id?'var(--dark-text-primary)':'var(--dark-text-muted)', display:'inline-block', flexShrink:0 }} />
            {item.label}
            {item.id==='cases' && activeCases.length>0 && <span className="nav-item__badge">{activeCases.length}</span>}
          </button>
        ))}

        <div style={{ margin:'16px 0 8px', borderTop:'1px solid var(--dark-border)' }} />
        <div style={{ fontSize:9, fontWeight:600, letterSpacing:'0.1em', textTransform:'uppercase', color:'var(--dark-text-muted)', padding:'8px 8px 8px' }}>System</div>
        {SYS_STATUS.map(s => (
          <div key={s.id} style={{ display:'flex', alignItems:'center', gap:8, padding:'6px 10px' }}>
            <span className="status-dot status-dot--ok" />
            <span style={{ fontSize:12, color:'var(--dark-text-secondary)', fontWeight:500 }}>{s.label}</span>
          </div>
        ))}
      </div>

      <div style={{ padding:'12px 18px', borderTop:'1px solid var(--dark-border)' }}>
        <a href="/" style={{ fontSize:11, color:'var(--dark-text-muted)', textDecoration:'none', display:'block', transition:'color 0.15s ease' }}
          onMouseEnter={e=>e.currentTarget.style.color='var(--dark-text-secondary)'}
          onMouseLeave={e=>e.currentTarget.style.color='var(--dark-text-muted)'}>
          &larr; Caller UI
        </a>
      </div>
    </aside>
  )

  // Top bar
  const TopBar = () => (
    <header style={{ background:'var(--surface-0)', borderBottom:'1px solid var(--border)', display:'flex', alignItems:'center', padding:'0 24px', gap:16 }}>
      <div style={{ flex:1 }}>
        <span style={{ fontSize:15, fontWeight:600, color:'var(--text-primary)', letterSpacing:'-0.01em' }}>
          {activeNav==='overview'&&'Overview'}
          {activeNav==='cases'&&'Live Cases'}
          {activeNav==='history'&&'Case History'}
        </span>
        {demoMode && <span style={{ marginLeft:10, fontSize:11, color:'var(--text-muted)', fontWeight:400 }}>Demo mode</span>}
      </div>
      <div style={{ display:'flex', alignItems:'center', gap:20 }}>
        <div style={{ display:'flex', gap:16 }}>
          {[
            { label:'Active', value:activeCases.length, color:'var(--danger)' },
            { label:'Resolved', value:resolvedCases.length, color:'var(--ok)' },
          ].map(s => (
            <div key={s.label} style={{ textAlign:'right' }}>
              <div style={{ fontSize:16, fontWeight:700, color:s.color, lineHeight:1, letterSpacing:'-0.02em' }}>{s.value}</div>
              <div style={{ fontSize:10, color:'var(--text-muted)', marginTop:2, fontWeight:600, letterSpacing:'0.04em', textTransform:'uppercase' }}>{s.label}</div>
            </div>
          ))}
        </div>
        <div style={{ display:'flex', alignItems:'center', gap:7, padding:'6px 12px', background:'var(--surface-1)', border:'1px solid var(--border)', borderRadius:'var(--r-md)' }}>
          <span className={'status-dot status-dot--' + (backendError?'danger':'ok')} />
          <span style={{ fontSize:11, color:'var(--text-tertiary)', fontWeight:500 }}>
            {backendError ? 'Backend offline' : lastUpdated ? lastUpdated.toLocaleTimeString() : 'Connecting...'}
          </span>
        </div>
      </div>
    </header>
  )

  // Overview page
  const OverviewPage = () => (
    <div style={{ padding:28, display:'flex', flexDirection:'column', gap:20 }}>
      <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:16 }}>
        {[
          { label:'Total Cases', value:displayCases.length },
          { label:'Escalated', value:activeCases.length, danger:true },
          { label:'Resolved', value:resolvedCases.length, ok:true },
          { label:'Avg Confidence', value: Math.round(displayCases.reduce((a,c)=>a+(c.confidence_display||0),0)/(displayCases.length||1))+'%' },
        ].map(s => (
          <div key={s.label} className="metric-card">
            <div className="metric-card__label">{s.label}</div>
            <div className="metric-card__value" style={{ color:s.danger?'var(--danger)':s.ok?'var(--ok)':'var(--text-primary)' }}>{s.value}</div>
          </div>
        ))}
      </div>
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:20 }}>
        <div className="card" style={{ padding:'20px 24px' }}>
          <div className="t-label" style={{ color:'var(--text-tertiary)', marginBottom:16 }}>System Health</div>
          {SYS_STATUS.map(s => (
            <div key={s.id} style={{ display:'flex', justifyContent:'space-between', padding:'9px 0', borderBottom:'1px solid var(--border-subtle)' }}>
              <span style={{ fontSize:13, color:'var(--text-secondary)' }}>{s.label}</span>
              <div style={{ display:'flex', alignItems:'center', gap:6 }}>
                <span className="status-dot status-dot--ok" />
                <span style={{ fontSize:11, color:'var(--ok)', fontWeight:600 }}>Online</span>
              </div>
            </div>
          ))}
        </div>
        <div className="card" style={{ padding:'20px 24px' }}>
          <div className="t-label" style={{ color:'var(--text-tertiary)', marginBottom:16 }}>Recent Activity</div>
          {displayCases.slice(0,5).map(c => (
            <div key={c.case_id} onClick={()=>{ setActiveNav('cases'); setActiveCaseId(c.case_id) }}
              style={{ display:'flex', alignItems:'center', gap:12, padding:'9px 0', borderBottom:'1px solid var(--border-subtle)', cursor:'pointer' }}
              onMouseEnter={e=>e.currentTarget.style.opacity='0.7'}
              onMouseLeave={e=>e.currentTarget.style.opacity='1'}>
              <span style={{ width:7, height:7, borderRadius:'50%', background:caseStatusColor(c), flexShrink:0 }} />
              <div style={{ flex:1, minWidth:0 }}>
                <div style={{ fontSize:12, fontWeight:600, color:'var(--text-primary)', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{c.issue||c.intent}</div>
                <div style={{ fontSize:10, color:'var(--text-muted)', fontFamily:'var(--font-mono)' }}>{c.case_id}</div>
              </div>
              {typeof c.confidence_display==='number' && <span style={{ fontSize:11, fontWeight:700, color:c.confidence_display>=60?'var(--ok)':'var(--danger)', fontFamily:'var(--font-mono)' }}>{c.confidence_display}%</span>}
            </div>
          ))}
        </div>
      </div>
    </div>
  )

  // History page
  const HistoryPage = () => (
    <div style={{ padding:28 }}>
      <div style={{ marginBottom:20, display:'flex', alignItems:'center', gap:12 }}>
        <h2 style={{ fontSize:16, fontWeight:700, color:'var(--text-primary)', margin:0 }}>Case History</h2>
        <span style={{ fontSize:12, color:'var(--text-muted)', padding:'3px 10px', background:'var(--surface-2)', border:'1px solid var(--border)', borderRadius:'var(--r-full)' }}>{displayCases.length} total</span>
      </div>
      <div className="card" style={{ overflow:'hidden', padding:0 }}>
        <table className="data-table">
          <thead>
            <tr>
              {['Case ID','Issue','Intent','Amount','Status','Confidence','Language','Time'].map(h => <th key={h}>{h}</th>)}
            </tr>
          </thead>
          <tbody>
            {displayCases.map(c => (
              <tr key={c.case_id} onClick={()=>{ setActiveNav('cases'); setActiveCaseId(c.case_id) }} style={{ cursor:'pointer' }}>
                <td style={{ fontFamily:'var(--font-mono)', fontSize:12, fontWeight:600, color:c.escalated&&!c.taken_over?'var(--danger)':'var(--text-tertiary)' }}>{c.case_id}</td>
                <td>{c.issue||c.issue_summary||'—'}</td>
                <td style={{ color:'var(--text-tertiary)' }}>{c.intent||'—'}</td>
                <td style={{ fontFamily:'var(--font-mono)' }}>{c.amount?'Rs'+c.amount.toLocaleString():'—'}</td>
                <td>
                  <span className={'status-pill status-pill--' + (c.taken_over?'ok':c.escalated?'danger':'warn')}>
                    {caseStatusLabel(c)}
                  </span>
                </td>
                <td>
                  {typeof c.confidence_display==='number' ? (
                    <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                      <div className="progress" style={{ flex:1, maxWidth:48 }}>
                        <div className={'progress__fill progress__fill--'+(c.confidence_display>=60?'ok':'danger')} style={{ width:c.confidence_display+'%' }} />
                      </div>
                      <span style={{ fontSize:11, fontWeight:700, fontFamily:'var(--font-mono)', color:c.confidence_display>=60?'var(--ok)':'var(--danger)' }}>{c.confidence_display}%</span>
                    </div>
                  ) : '—'}
                </td>
                <td style={{ color:'var(--text-tertiary)' }}>{c.language?.join(' / ')||'—'}</td>
                <td style={{ color:'var(--text-muted)', fontFamily:'var(--font-mono)', fontSize:11 }}>{c.created_at?new Date(c.created_at).toLocaleTimeString():'—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )

  // Cases 3-col
  const CasesPage = () => (
    <div style={{ display:'grid', gridTemplateColumns:'260px minmax(0,1fr) 300px', gap:0, height:'100%', overflow:'hidden' }}>

      {/* Col 1: Cases list */}
      <div style={{ borderRight:'1px solid var(--border)', display:'flex', flexDirection:'column', overflow:'hidden' }}>
        <div style={{ padding:'16px 16px 10px', borderBottom:'1px solid var(--border-subtle)', display:'flex', alignItems:'center', justifyContent:'space-between' }}>
          <span className="t-label" style={{ color:'var(--text-tertiary)' }}>Cases</span>
          <span style={{ fontSize:11, color:'var(--text-muted)' }}>{displayCases.length}</span>
        </div>
        <div style={{ flex:1, overflowY:'auto', padding:'8px 10px' }}>
          {displayCases.map(c => {
            const isActive = c.case_id === activeCaseId
            return (
              <button key={c.case_id} onClick={()=>setActiveCaseId(c.case_id)}
                style={{ width:'100%', padding:'10px 12px', marginBottom:4, borderRadius:'var(--r-md)', border:`1px solid ${isActive?'var(--border-strong)':'transparent'}`, background:isActive?'var(--surface-2)':'transparent', cursor:'pointer', textAlign:'left', fontFamily:'inherit', transition:'all 0.12s ease', opacity:c.taken_over?0.6:1 }}
                onMouseEnter={e=>{ if(!isActive) e.currentTarget.style.background='var(--surface-2)' }}
                onMouseLeave={e=>{ if(!isActive) e.currentTarget.style.background='transparent' }}>
                <div style={{ display:'flex', alignItems:'center', gap:7, marginBottom:4 }}>
                  <span style={{ width:6, height:6, borderRadius:'50%', background:caseStatusColor(c), flexShrink:0 }} />
                  <span style={{ fontSize:11, fontFamily:'var(--font-mono)', fontWeight:600, color:'var(--text-tertiary)' }}>{c.case_id}</span>
                </div>
                <div style={{ fontSize:12.5, fontWeight:500, color:'var(--text-primary)', lineHeight:1.3, marginBottom:4 }}>{c.issue_summary||c.issue||c.intent||'Case'}</div>
                <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
                  <span style={{ fontSize:10, color:'var(--text-muted)' }}>{c.language?.join(' + ')||'Unknown'}</span>
                  {typeof c.confidence_display==='number' && <span style={{ fontSize:10, fontWeight:700, fontFamily:'var(--font-mono)', color:c.confidence_display>=60?'var(--ok)':'var(--danger)' }}>{c.confidence_display}%</span>}
                </div>
              </button>
            )
          })}
        </div>
      </div>

      {/* Col 2: Conversation */}
      <div style={{ display:'flex', flexDirection:'column', overflow:'hidden', borderRight:'1px solid var(--border)' }}>
        <div style={{ padding:'12px 20px', borderBottom:'1px solid var(--border)', display:'flex', alignItems:'center', justifyContent:'space-between', flexShrink:0 }}>
          <div style={{ display:'flex', alignItems:'center', gap:12 }}>
            <span className="t-label" style={{ color:'var(--text-tertiary)' }}>Live Conversation</span>
            {activeCase && (
              <span className={'status-pill status-pill--'+(activeCase.taken_over?'ok':activeCase.escalated?'danger':'warn')}>
                {caseStatusLabel(activeCase)}
              </span>
            )}
          </div>
          <div style={{ display:'flex', alignItems:'center', gap:7 }}>
            <span className="status-dot status-dot--ok" />
            <span style={{ fontSize:11, color:'var(--text-tertiary)' }}>{activeCase?activeCase.case_id.toLowerCase():'monitoring'}</span>
          </div>
        </div>

        <div style={{ flex:1, overflowY:'auto', padding:'16px 20px' }}>
          {(() => {
            const liveHist = (!demoMode && activeCase?.conversation_history) ? activeCase.conversation_history : []
            const msgs = demoMode ? demoMessages : liveHist
            if (msgs.length===0) return (
              <div style={{ display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', height:'100%', gap:10, color:'var(--text-muted)', padding:'40px 20px', textAlign:'center' }}>
                <div style={{ width:48, height:48, borderRadius:'50%', background:'var(--surface-2)', border:'1px solid var(--border)', display:'flex', alignItems:'center', justifyContent:'center', fontSize:18 }}>&#128172;</div>
                <div style={{ fontSize:13, fontWeight:500, color:'var(--text-secondary)' }}>{demoMode?'Demo will play shortly...':'No transcript yet'}</div>
              </div>
            )
            return (
              <div className="transcript">
                {msgs.filter(m=>m.content&&typeof m.content==='string'&&m.content.trim().length>0&&m.role!=='tool'&&m.role!=='system').map((msg,i) => (
                  <div key={i} className={'transcript-line transcript-line--'+(msg.role==='user'?'user':'agent')}>
                    <div className="transcript-line__meta">
                      {msg.role==='user'?<span>USER</span>:<span>PRISM</span>}
                      {msg.time && <span style={{ color:'var(--border-strong)', fontWeight:400 }}>{msg.time}</span>}
                    </div>
                    <div className="transcript-line__bubble">
                      {msg.content}
                      {msg.thinking && <div style={{ marginTop:6, paddingTop:6, borderTop:'1px solid var(--border-subtle)', fontSize:11, color:'var(--text-tertiary)', fontStyle:'italic' }}>Checking transaction...</div>}
                    </div>
                  </div>
                ))}
                {showToolAction && (
                  <div className="slide-up" style={{ marginBottom:8 }}>
                    <AIActionPanel compact />
                  </div>
                )}
                <div ref={convEndRef} />
              </div>
            )
          })()}
        </div>

        {(showEscalation || (!demoMode && activeCase?.escalated && !activeCase?.taken_over)) && activeCase && (
          <div style={{ padding:'12px 20px', borderTop:'1px solid var(--border)', flexShrink:0 }}>
            <EscalationPanel caseData={activeCase} compact
              onTakeOver={async id => {
                try { await fetch(getApiUrl('/cases/'+id+'/takeover'),{method:'POST'}) } catch {}
                setCases(p=>p.map(c=>c.case_id===id?{...c,taken_over:true,status:'TAKEN_OVER'}:c))
                handleAgentAgoraJoin(activeCase?.channel||'prism-demo')
              }} />
          </div>
        )}

        <div style={{ padding:'12px 20px', borderTop:'1px solid var(--border)', flexShrink:0 }}>
          <div style={{ display:'flex', gap:8, alignItems:'center' }}>
            <div style={{ flex:1, padding:'8px 12px', background:agentAudioConnected?'var(--ok-bg)':'var(--surface-1)', border:'1px solid '+(agentAudioConnected?'var(--ok-border)':'var(--border)'), borderRadius:'var(--r-md)', fontSize:12, color:agentAudioConnected?'var(--ok)':'var(--text-muted)', display:'flex', alignItems:'center', gap:7 }}>
              <span className={'status-dot status-dot--'+(agentAudioConnected?'ok':'muted')} />
              <span>{agentAudioConnected?'Agora connected — '+( activeCase?.channel||'prism-demo'):activeCase?.taken_over?'Connected':'PRISM AI active'}</span>
            </div>
            {agentAudioConnected && (
              <div style={{ display:'flex', gap:6 }}>
                <button onClick={toggleAgentMute} className="btn btn--secondary btn--sm">{agentMuted?'Unmute':'Mute'}</button>
                <button onClick={disconnectAgentAudio} className="btn btn--danger btn--sm">Disconnect</button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Col 3: Case intel */}
      <div style={{ display:'flex', flexDirection:'column', overflow:'hidden' }}>
        <div style={{ padding:'12px 16px', borderBottom:'1px solid var(--border)', flexShrink:0 }}>
          <span className="t-label" style={{ color:'var(--text-tertiary)' }}>Case Intelligence</span>
        </div>

        <div style={{ flex:1, overflowY:'auto', display:'flex', flexDirection:'column' }}>
          {/* Active case header */}
          {activeCase && (
            <div style={{ padding:'14px 16px', borderBottom:'1px solid var(--border)', background:activeCase.escalated&&!activeCase.taken_over?'var(--danger-bg)':'var(--surface-1)' }}>
              <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:6 }}>
                <span className="t-label" style={{ color:'var(--text-muted)' }}>Active Case</span>
                <span style={{ width:8, height:8, borderRadius:'50%', background:caseStatusColor(activeCase), display:'inline-block' }} />
              </div>
              <div style={{ fontSize:14, fontWeight:600, color:'var(--text-primary)', lineHeight:1.3, marginBottom:4 }}>{activeCase.issue||activeCase.intent||'Case'}</div>
              <div style={{ fontSize:11, fontFamily:'var(--font-mono)', color:'var(--text-muted)' }}>{activeCase.case_id}</div>
            </div>
          )}

          {/* Live AI state */}
          {(liveVoiceState!=='IDLE'||liveAiState) && (
            <div style={{ borderBottom:'1px solid var(--border)' }}>
              <div style={{ padding:'10px 16px', borderBottom:'1px solid var(--border-subtle)', display:'flex', alignItems:'center', justifyContent:'space-between', background:'var(--surface-1)' }}>
                <span className="t-label" style={{ color:'var(--text-muted)' }}>Live AI State</span>
                <span style={{ fontSize:10, fontWeight:600, color:liveVoiceState==='ESCALATING'?'var(--danger)':liveVoiceState==='ACTING'?'var(--warn)':'var(--ok)', letterSpacing:'0.05em', textTransform:'uppercase' }}>{liveVoiceState}</span>
              </div>
              <div style={{ maxHeight:280, overflowY:'auto' }}>
                <ThinkingPanel voiceState={liveVoiceState} aiState={liveAiState} />
              </div>
            </div>
          )}

          {/* CasePanel */}
          <div style={{ padding:'16px', flex:1 }}>
            {activeCase ? <CasePanel caseData={activeCase} /> : <div style={{ color:'var(--text-muted)', fontSize:13, padding:'24px 0', textAlign:'center' }}>Select a case</div>}
          </div>
        </div>
      </div>
    </div>
  )

  return (
    <div className="app-shell">
      <Sidebar />
      <TopBar />
      <main className="app-main">
        {activeNav==='overview' && <OverviewPage />}
        {activeNav==='history'  && <HistoryPage />}
        {activeNav==='cases'    && <CasesPage />}
      </main>
    </div>
  )
}
""".strip()

import pathlib
pathlib.Path(r'd:/WORK AND STUDY/PRISM/frontend/src/pages/Agent.jsx').write_text(JSX, encoding='utf-8')
print('Agent.jsx written', len(JSX), 'chars')