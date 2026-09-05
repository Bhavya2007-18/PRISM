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
          {steps.map(s => (
            <span key={s.id} className={`status-dot ${
              !vis.includes(s.id) ? 'status-dot--muted' :
              s.status === 'done' ? 'status-dot--ok' :
              s.status === 'danger' ? 'status-dot--danger' :
              s.status === 'warn' ? 'status-dot--warn' :
              'status-dot--muted'
            }`} style={{ width: 5, height: 5 }} />
          ))}
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