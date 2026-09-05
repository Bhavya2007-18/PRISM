import { PRISM_STATE_CONFIG as PHASE_CONFIG } from '../config/prismState'

const ACTION_LABELS = {
  ASK_CLARIFICATION:   'Asking for information',
  CONFIRM_INFORMATION: 'Confirming details',
  VERIFY_TRANSACTION:  'Verifying transaction',
  CHECK_ORDER:         'Checking order status',
  RESOLVE_CASE:        'Resolving case',
  ESCALATE_TO_HUMAN:   'Escalating to specialist',
  UNDERSTAND_REQUEST:  'Understanding request',
  NO_ACTION:           'Processing',
}

const PIPELINE = ['LISTENING','UNDERSTANDING','THINKING','ACTING','SPEAKING','ESCALATING']

function PipelineDot({ active, done }) {
  return (
    <span style={{
      display:'inline-block', width:8, height:8, borderRadius:'50%', flexShrink:0,
      background: done ? 'var(--ok)' : active ? 'var(--text-primary)' : 'var(--surface-3)',
      border: `1.5px solid ${done ? 'var(--ok)' : active ? 'var(--text-primary)' : 'var(--border-strong)'}`,
      boxShadow: active ? '0 0 0 3px rgba(0,0,0,0.07)' : 'none',
      transition: 'all 0.25s ease',
    }} />
  )
}

export default function ThinkingPanel({ voiceState = 'IDLE', aiState = null, compact = false }) {
  const cfg = PHASE_CONFIG[voiceState] || PHASE_CONFIG.IDLE
  const sc = voiceState === 'ESCALATING' || voiceState === 'ERROR' ? 'var(--danger)'
           : voiceState === 'HUMAN_CONNECTED' ? 'var(--ok)'
           : voiceState === 'ACTING' ? 'var(--warn)'
           : 'var(--text-primary)'
  const activeIdx = PIPELINE.indexOf(voiceState)

  if (compact) {
    return (
      <div style={{
        display:'flex', alignItems:'center', gap:8, padding:'7px 12px',
        background: voiceState==='ESCALATING' ? 'var(--danger-bg)' : voiceState==='HUMAN_CONNECTED' ? 'var(--ok-bg)' : 'var(--surface-1)',
        border:`1px solid ${voiceState==='ESCALATING' ? 'var(--danger-border)' : voiceState==='HUMAN_CONNECTED' ? 'var(--ok-border)' : 'var(--border)'}`,
        borderRadius:'var(--r-md)',
      }}>
        <span style={{width:7,height:7,borderRadius:'50%',display:'inline-block',background:sc,flexShrink:0}} />
        <span style={{fontSize:11,fontWeight:600,color:sc,letterSpacing:'0.04em',textTransform:'uppercase'}}>{cfg.label}</span>
        {aiState?.intent && <span style={{fontSize:11,color:'var(--text-tertiary)',marginLeft:2}}>— {aiState.intent.replace(/_/g,' ')}</span>}
        {aiState?.confidence!=null && <span style={{marginLeft:'auto',fontSize:12,fontWeight:600,color:'var(--text-primary)',fontFamily:'var(--font-mono)'}}>{aiState.confidence}%</span>}
      </div>
    )
  }

  return (
    <div style={{display:'flex',flexDirection:'column',height:'100%',overflowY:'auto'}}>
      <div style={{padding:'14px 16px',borderBottom:'1px solid var(--border-subtle)',background:'var(--surface-1)'}}>
        <div className="t-label" style={{color:'var(--text-muted)',marginBottom:6}}>AI State</div>
        <div style={{display:'flex',alignItems:'center',gap:8}}>
          <span style={{fontSize:14}}>{cfg.icon}</span>
          <span style={{fontSize:14,fontWeight:600,color:sc,letterSpacing:'-0.01em'}}>{cfg.label}</span>
          <span style={{marginLeft:'auto',width:7,height:7,borderRadius:'50%',background:sc,flexShrink:0}} />
        </div>
      </div>

      <div style={{padding:'14px 16px',display:'flex',flexDirection:'column',gap:18}}>
        <div>
          <div className="t-label" style={{color:'var(--text-muted)',marginBottom:10}}>Pipeline</div>
          {PIPELINE.map((state,idx) => {
            const pcfg = PHASE_CONFIG[state] || {}
            const isActive = state === voiceState
            const isDone   = idx < activeIdx
            return (
              <div key={state} style={{display:'flex',alignItems:'flex-start',gap:10}}>
                <div style={{display:'flex',flexDirection:'column',alignItems:'center',width:8,marginTop:2}}>
                  <PipelineDot active={isActive} done={isDone} />
                  {idx < PIPELINE.length-1 && <div style={{width:1,flex:1,background:isDone?'var(--ok)':'var(--border)',minHeight:14,marginTop:2,transition:'background 0.3s ease'}} />}
                </div>
                <div style={{paddingBottom:idx<PIPELINE.length-1?10:0}}>
                  <span style={{fontSize:12.5,fontWeight:isActive?600:400,color:isActive?'var(--text-primary)':isDone?'var(--text-muted)':'var(--text-tertiary)',transition:'color 0.2s ease'}}>
                    {pcfg.label||state}
                  </span>
                </div>
              </div>
            )
          })}
        </div>

        {aiState && (<>
          {(aiState.intent||aiState.language?.length>0) && (
            <div style={{display:'flex',flexDirection:'column',gap:7}}>
              {aiState.intent && (
                <div style={{display:'flex',justifyContent:'space-between'}}>
                  <span className="t-label" style={{color:'var(--text-muted)'}}>Intent</span>
                  <span style={{fontSize:12.5,fontWeight:500}}>{aiState.intent.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase())}</span>
                </div>
              )}
              {aiState.language?.length>0 && (
                <div style={{display:'flex',justifyContent:'space-between'}}>
                  <span className="t-label" style={{color:'var(--text-muted)'}}>Language</span>
                  <span style={{fontSize:12.5,fontWeight:500}}>{aiState.language.join(' + ')}</span>
                </div>
              )}
            </div>
          )}

          {aiState.confidence!=null && (
            <div>
              <div style={{display:'flex',justifyContent:'space-between',alignItems:'baseline',marginBottom:8}}>
                <span className="t-label" style={{color:'var(--text-muted)'}}>Confidence</span>
                <span style={{fontSize:20,fontWeight:700,letterSpacing:'-0.03em',color:aiState.confidence>=70?'var(--ok)':aiState.confidence>=40?'var(--warn)':'var(--danger)'}}>{aiState.confidence}%</span>
              </div>
              <div className="progress">
                <div className="progress__fill" style={{width:`${aiState.confidence}%`,background:aiState.confidence>=70?'var(--ok)':aiState.confidence>=40?'var(--warn)':'var(--danger)'}} />
              </div>
              {aiState.confidence_fields && (
                <div style={{marginTop:10,display:'flex',flexDirection:'column',gap:4}}>
                  {Object.entries(aiState.confidence_fields).map(([f,l])=>(
                    <div key={f} style={{display:'flex',justifyContent:'space-between'}}>
                      <span style={{fontSize:11,color:'var(--text-tertiary)'}}>{f.replace(/_/g,' ')}</span>
                      <span style={{fontSize:10,fontWeight:700,letterSpacing:'0.03em',color:l==='HIGH'?'var(--ok)':l==='LOW'?'var(--warn)':'var(--danger)'}}>{l}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {aiState.verified?.length>0 && (
            <div>
              <div className="t-label" style={{color:'var(--text-muted)',marginBottom:7}}>Verified</div>
              {aiState.verified.map(f=>(
                <div key={f} style={{display:'flex',alignItems:'center',gap:7,padding:'3px 0'}}>
                  <span style={{fontSize:11,color:'var(--ok)',fontWeight:700}}>✓</span>
                  <span style={{fontSize:12,color:'var(--text-secondary)'}}>{f.replace(/_/g,' ')}</span>
                </div>
              ))}
            </div>
          )}

          {aiState.unverified?.length>0 && (
            <div>
              <div className="t-label" style={{color:'var(--text-muted)',marginBottom:7}}>Uncertain</div>
              {aiState.unverified.map(f=>(
                <div key={f} style={{display:'flex',alignItems:'center',gap:7,padding:'3px 0'}}>
                  <span style={{fontSize:11,color:'var(--warn)',fontWeight:600}}>–</span>
                  <span style={{fontSize:12,color:'var(--text-secondary)'}}>{f.replace(/_/g,' ')}</span>
                </div>
              ))}
            </div>
          )}

          {aiState.action && aiState.action!=='UNDERSTAND_REQUEST' && (
            <div style={{padding:'10px 12px',background:'var(--surface-1)',border:'1px solid var(--border)',borderRadius:'var(--r-md)'}}>
              <div className="t-label" style={{color:'var(--text-muted)',marginBottom:5}}>{voiceState==='ACTING'?'Current action':'Next action'}</div>
              <div style={{fontSize:12.5,fontWeight:500}}>
                {aiState.tool_status==='completed'?'✓ ':aiState.tool_status==='running'?'→ ':''}
                {ACTION_LABELS[aiState.action]||aiState.action.replace(/_/g,' ')}
              </div>
              {aiState.tool && <div style={{fontSize:11,color:'var(--text-tertiary)',marginTop:3,fontFamily:'var(--font-mono)'}}>{aiState.tool}{aiState.tool_status&&<span style={{marginLeft:6,color:aiState.tool_status==='completed'?'var(--ok)':aiState.tool_status==='failed'?'var(--danger)':'var(--warn)'}}>[{aiState.tool_status}]</span>}</div>}
            </div>
          )}

          {aiState.tool_result && (
            <div style={{padding:'10px 12px',background:'var(--ok-bg)',border:'1px solid var(--ok-border)',borderRadius:'var(--r-md)'}}>
              <div className="t-label" style={{color:'var(--ok)',marginBottom:5}}>Tool result</div>
              {aiState.tool_result.amount && <div style={{fontSize:12}}>✓ Amount: ₹{Number(aiState.tool_result.amount).toLocaleString('en-IN')}</div>}
              {aiState.tool_result.status && <div style={{fontSize:12,marginTop:2}}>✓ Payment: {aiState.tool_result.status}</div>}
              {aiState.tool_result.order_status && <div style={{fontSize:12,color:aiState.tool_result.order_status==='CONFIRMED'?'var(--ok)':'var(--warn)',marginTop:2}}>{aiState.tool_result.order_status==='CONFIRMED'?'✓':'–'} Order: {aiState.tool_result.order_status}</div>}
            </div>
          )}
        </>)}

        {!aiState && voiceState==='IDLE' && <div style={{fontSize:12,color:'var(--text-muted)',textAlign:'center',padding:'12px 0'}}>Start a conversation to see live AI state</div>}
      </div>
    </div>
  )
}
