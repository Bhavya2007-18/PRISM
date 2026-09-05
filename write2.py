import pathlib, textwrap

base = pathlib.Path(r'd:/WORK AND STUDY/PRISM/frontend/src')

# ─── EscalationPanel.jsx ─────────────────────────────────────────
ep = r'''
import { useState } from 'react'
import { getApiUrl } from '../lib/api'

export default function EscalationPanel({ caseData, onTakeOver, compact = false }) {
  const [taking, setTaking] = useState(false)
  const [taken, setTaken] = useState(caseData?.taken_over || caseData?.status === 'TAKEN_OVER')
  if (!caseData) return null

  const conf = caseData.confidence_display ?? 0
  const cc = conf>=70?'var(--ok)':conf>=40?'var(--warn)':'var(--danger)'

  async function handleTakeOver() {
    if (taken||taking) return
    setTaking(true)
    try {
      await fetch(getApiUrl(/cases//takeover), { method:'POST' })
      setTaken(true)
      onTakeOver?.(caseData.case_id)
    } catch(e) { console.error(e) }
    setTaking(false)
  }

  const vi = []
  if (caseData.transaction_id) vi.push({ label:'Transaction', value:caseData.transaction_id })
  if (caseData.amount!=null)   vi.push({ label:'Amount', value:\u20b9 })
  if (caseData.payment_status) vi.push({ label:'Payment', value:caseData.payment_status })
  if (caseData.order_status)   vi.push({ label:'Order', value:caseData.order_status })
  const ui = caseData.unverified || []

  if (compact) {
    return (
      <div style={{padding:'14px 16px',background:taken?'var(--ok-bg)':'var(--danger-bg)',border:1px solid ,borderRadius:'var(--r-lg)',display:'flex',flexDirection:'column',gap:12}}>
        <div style={{display:'flex',alignItems:'center',justifyContent:'space-between'}}>
          <div>
            <div style={{fontSize:12,fontWeight:700,color:taken?'var(--ok)':'var(--danger)',letterSpacing:'0.04em',textTransform:'uppercase',marginBottom:2}}>{taken?'Resolved':'Human required'}</div>
            <div style={{fontSize:12,color:'var(--text-secondary)'}}>{caseData.issue||caseData.intent||'Escalated case'}</div>
          </div>
          <span style={{fontSize:11,fontFamily:'var(--font-mono)',color:'var(--text-tertiary)'}}>{caseData.case_id}</span>
        </div>
        {caseData.reason_for_escalation && <p style={{fontSize:12,color:'var(--text-secondary)',margin:0,lineHeight:1.5}}>{caseData.reason_for_escalation}</p>}
        {!taken && <button onClick={handleTakeOver} disabled={taking} className="btn btn--primary btn--sm" style={{alignSelf:'flex-end'}}>{taking?'Connecting\u2026':'Take over conversation'}</button>}
        {taken && <div style={{fontSize:12,color:'var(--ok)',fontWeight:500}}>\u2713 Human agent connected</div>}
      </div>
    )
  }

  return (
    <div style={{background:'var(--surface-0)',border:1px solid ,borderRadius:'var(--r-lg)',overflow:'hidden',transition:'border-color 0.3s ease'}}>
      <div style={{padding:'13px 20px',background:taken?'var(--surface-1)':'var(--danger-bg)',borderBottom:'1px solid var(--border)',display:'flex',alignItems:'center',justifyContent:'space-between'}}>
        <div style={{display:'flex',alignItems:'center',gap:9}}>
          <span style={{width:7,height:7,borderRadius:'50%',display:'inline-block',background:taken?'var(--ok)':'var(--danger)',flexShrink:0}} />
          <span style={{fontSize:11,fontWeight:700,letterSpacing:'0.06em',textTransform:'uppercase',color:taken?'var(--text-tertiary)':'var(--danger)'}}>{taken?'Resolved':'Escalation'}</span>
        </div>
        <span style={{fontSize:11,fontFamily:'var(--font-mono)',color:'var(--text-tertiary)'}}>{caseData.case_id}</span>
      </div>

      <div style={{display:'grid',gridTemplateColumns:'1fr 1fr'}}>
        <div style={{padding:'16px 20px',borderRight:'1px solid var(--border)',display:'flex',flexDirection:'column',gap:14}}>
          <div>
            <div className="t-label" style={{color:'var(--text-muted)',marginBottom:5}}>Issue</div>
            <div style={{fontSize:14,fontWeight:600,lineHeight:1.3}}>{caseData.issue||'Payment issue'}</div>
          </div>
          <div>
            <div className="t-label" style={{color:'var(--text-muted)',marginBottom:6}}>Language</div>
            <div style={{display:'flex',gap:5,flexWrap:'wrap'}}>
              {(caseData.language?.length?caseData.language:['Unknown']).map(l=>(
                <span key={l} style={{padding:'2px 9px',borderRadius:'var(--r-full)',background:'var(--surface-2)',border:'1px solid var(--border)',fontSize:11,fontWeight:500,color:'var(--text-secondary)'}}>{l}</span>
              ))}
            </div>
          </div>
          {vi.length>0&&(
            <div>
              <div className="t-label" style={{color:'var(--text-muted)',marginBottom:6}}>Verified</div>
              {vi.map(item=>(
                <div key={item.label} style={{display:'flex',justifyContent:'space-between',padding:'3px 0',gap:8}}>
                  <span style={{fontSize:12,color:'var(--ok)'}}>&#x2713; {item.label}</span>
                  <span style={{fontSize:12,fontWeight:600}}>{item.value}</span>
                </div>
              ))}
            </div>
          )}
          {ui.length>0&&(
            <div>
              <div className="t-label" style={{color:'var(--text-muted)',marginBottom:6}}>Uncertain</div>
              {ui.map(f=><div key={f} style={{fontSize:12,color:'var(--warn)',padding:'2px 0'}}>&ndash; {f.replace(/_/g,' ')}</div>)}
            </div>
          )}
        </div>

        <div style={{padding:'16px 20px',display:'flex',flexDirection:'column',gap:14}}>
          <div>
            <div style={{display:'flex',justifyContent:'space-between',alignItems:'baseline',marginBottom:8}}>
              <span className="t-label" style={{color:'var(--text-muted)'}}>Confidence</span>
              <span style={{fontSize:24,fontWeight:700,letterSpacing:'-0.03em',color:cc}}>{conf}%</span>
            </div>
            <div className="progress" style={{marginBottom:6}}>
              <div style={{height:'100%',width:${conf}%,background:cc,borderRadius:3,transition:'width 0.6s ease'}} />
            </div>
            <div style={{fontSize:10,fontWeight:600,letterSpacing:'0.04em',textTransform:'uppercase',color:cc}}>{caseData.confidence_label||'Uncertain'}</div>
          </div>
          {caseData.summary&&(
            <div>
              <div className="t-label" style={{color:'var(--text-muted)',marginBottom:5}}>Summary</div>
              <p style={{fontSize:12.5,color:'var(--text-secondary)',margin:0,lineHeight:1.55}}>{caseData.summary}</p>
            </div>
          )}
          {caseData.reason_for_escalation&&(
            <div>
              <div className="t-label" style={{color:'var(--danger)',marginBottom:5}}>Reason</div>
              <p style={{fontSize:12.5,color:'var(--text-secondary)',margin:0,lineHeight:1.5}}>{caseData.reason_for_escalation}</p>
            </div>
          )}
        </div>
      </div>

      <div style={{padding:'12px 20px',borderTop:'1px solid var(--border)',display:'flex',justifyContent:'flex-end',alignItems:'center',gap:12,background:'var(--surface-1)'}}>
        {taken&&<span style={{fontSize:12,color:'var(--text-tertiary)'}}>Handled by human agent</span>}
        <button onClick={handleTakeOver} disabled={taken||taking} className="btn btn--primary btn--sm">
          {taking?'Connecting\u2026':taken?'\u2713 Taken over':'Take over conversation'}
        </button>
      </div>
    </div>
  )
}
'''.strip()

# ─── AIActionPanel.jsx ────────────────────────────────────────────
aip = r'''
import { useState, useEffect } from 'react'

const DEFAULT_STEPS = [
  { id:1, label:'Transaction ID received',   detail:'TX48291',              status:'done',   delay:0 },
  { id:2, label:'Calling check_transaction', detail:'mock transaction API', status:'active', delay:600 },
  { id:3, label:'Amount verified',           detail:'\u20b91,499',               status:'done',   delay:1200 },
  { id:4, label:'Payment status',            detail:'SUCCESS',              status:'done',   delay:1800 },
  { id:5, label:'Order status',              detail:'NOT_CONFIRMED',        status:'warn',   delay:2200 },
  { id:6, label:'Duplicate charge',          detail:'Cannot determine',     status:'danger', delay:2800 },
]

const StepIcon = ({ status }) => {
  const m = { done:{c:'var(--ok)',s:'\u2713'}, active:{c:'var(--text-primary)',s:'\u2192'}, warn:{c:'var(--warn)',s:'\u2013'}, danger:{c:'var(--danger)',s:'!'} }
  const d = m[status]||{c:'var(--text-muted)',s:'\u25cb'}
  return <span style={{fontSize:11,color:d.c,fontWeight:700}}>{d.s}</span>
}

export default function AIActionPanel({ steps:propSteps, compact=false }) {
  const steps = propSteps || DEFAULT_STEPS
  const [vis, setVis] = useState([])
  useEffect(()=>{ const t=steps.map((s,i)=>setTimeout(()=>setVis(p=>[...p,s.id]),s.delay||i*400)); return()=>t.forEach(clearTimeout) },[])

  if (compact) {
    const count = steps.filter(s=>vis.includes(s.id)).length
    const last  = [...steps].reverse().find(s=>vis.includes(s.id))
    return (
      <div style={{padding:'10px 14px',background:'var(--surface-1)',border:'1px solid var(--border)',borderRadius:'var(--r-md)',display:'flex',alignItems:'center',gap:10}}>
        <div style={{flex:1}}>
          <div style={{display:'flex',alignItems:'center',gap:6,marginBottom:2}}>
            <span className="t-label" style={{color:'var(--text-tertiary)'}}>Tool execution</span>
            <span style={{fontSize:10,color:'var(--text-muted)'}}>{count}/{steps.length}</span>
          </div>
          {last&&<div style={{fontSize:12.5,fontWeight:500}}>{last.label}</div>}
        </div>
        <div style={{display:'flex',gap:3}}>
          {steps.map(s=><div key={s.id} style={{width:4,height:4,borderRadius:'50%',background:!vis.includes(s.id)?'var(--surface-3)':s.status==='done'?'var(--ok)':s.status==='danger'?'var(--danger)':s.status==='warn'?'var(--warn)':'var(--text-primary)',transition:'background 0.3s ease'}} />)}
        </div>
      </div>
    )
  }

  return (
    <div style={{background:'var(--surface-0)',border:'1px solid var(--border)',borderRadius:'var(--r-lg)',overflow:'hidden'}}>
      <div style={{padding:'11px 16px',borderBottom:'1px solid var(--border)',background:'var(--surface-1)',display:'flex',alignItems:'center',justifyContent:'space-between'}}>
        <span className="t-label" style={{color:'var(--text-tertiary)'}}>Tool Execution</span>
        <span style={{fontSize:11,color:'var(--text-muted)',fontFamily:'var(--font-mono)'}}>check_transaction</span>
      </div>
      <div style={{padding:'14px 16px'}}>
        {steps.map((step,idx)=>(
          <div key={step.id} className={vis.includes(step.id)?'fade-in':''} style={{display:vis.includes(step.id)?'flex':'none',alignItems:'flex-start',gap:12}}>
            <div style={{display:'flex',flexDirection:'column',alignItems:'center',paddingTop:2}}>
              <div style={{width:16,height:16,display:'flex',alignItems:'center',justifyContent:'center'}}><StepIcon status={step.status} /></div>
              {idx<steps.length-1&&vis.includes(steps[idx+1]?.id)&&<div style={{width:1,flex:1,background:'var(--border)',minHeight:8,marginTop:2}} />}
            </div>
            <div style={{flex:1,paddingBottom:idx<steps.length-1?10:0}}>
              <div style={{fontSize:13,fontWeight:500,lineHeight:1.3}}>{step.label}</div>
              {step.detail&&<div style={{fontSize:11.5,color:'var(--text-tertiary)',marginTop:2,fontFamily:'var(--font-mono)'}}>{step.detail}</div>}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
'''.strip()

files = {
  'components/EscalationPanel.jsx': ep,
  'components/AIActionPanel.jsx':   aip,
}

for path, content in files.items():
    p = base / path
    p.write_text(content, encoding='utf-8')
    print(f'wrote {path} ({len(content)} chars)')

print('done')
