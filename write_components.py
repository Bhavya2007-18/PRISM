import pathlib

base = pathlib.Path(r'd:/WORK AND STUDY/PRISM/frontend/src')

files = {}

files['components/CasePanel.jsx'] = r"""
export default function CasePanel({ caseData }) {
  if (!caseData) return <div style={{padding:'32px 0',textAlign:'center',color:'var(--text-muted)',fontSize:13}}>No case selected</div>
  const conf = typeof caseData.confidence_display === 'number' ? caseData.confidence_display : null
  const cc = conf==null?'var(--text-muted)':conf>=70?'var(--ok)':conf>=40?'var(--warn)':'var(--danger)'
  const Row = ({label,value,mono,color}) => value==null?null:(
    <div style={{display:'flex',justifyContent:'space-between',padding:'9px 0',borderBottom:'1px solid var(--border-subtle)',gap:12}}>
      <span style={{fontSize:12,color:'var(--text-tertiary)',fontWeight:500,flexShrink:0}}>{label}</span>
      <span style={{fontSize:12.5,color:color||'var(--text-primary)',fontWeight:500,textAlign:'right',fontFamily:mono?'var(--font-mono)':'inherit'}}>{value}</span>
    </div>
  )
  return (
    <div style={{display:'flex',flexDirection:'column',gap:18}}>
      <div>
        <div className="t-label" style={{color:'var(--text-muted)',marginBottom:8}}>Case</div>
        <Row label="ID" value={caseData.case_id} mono />
        <Row label="Intent" value={caseData.intent?.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase())} />
        <Row label="Language" value={caseData.language?.join(' + ')} />
        <Row label="Opened" value={caseData.created_at?new Date(caseData.created_at).toLocaleTimeString():null} mono />
      </div>
      {(caseData.transaction_id||caseData.amount!=null||caseData.payment_status)&&(
        <div>
          <div className="t-label" style={{color:'var(--text-muted)',marginBottom:8}}>Transaction</div>
          <Row label="ID" value={caseData.transaction_id} mono />
          <Row label="Amount" value={caseData.amount!=null?\u20b9:null} mono />
          <Row label="Payment" value={caseData.payment_status} color={caseData.payment_status==='SUCCESS'?'var(--ok)':'var(--danger)'} />
          <Row label="Order" value={caseData.order_status} color={caseData.order_status==='CONFIRMED'?'var(--ok)':'var(--warn)'} />
        </div>
      )}
      {(caseData.verified?.length>0||caseData.unverified?.length>0)&&(
        <div>
          <div className="t-label" style={{color:'var(--text-muted)',marginBottom:8}}>Verification</div>
          {(caseData.verified||[]).map(f=>(
            <div key={f} style={{display:'flex',alignItems:'center',gap:8,padding:'4px 0'}}>
              <span style={{fontSize:11,color:'var(--ok)',fontWeight:700}}>&#x2713;</span>
              <span style={{fontSize:12.5,color:'var(--text-secondary)',flex:1}}>{f.replace(/_/g,' ')}</span>
              <span style={{fontSize:10,fontWeight:600,color:'var(--ok)',letterSpacing:'0.03em'}}>VERIFIED</span>
            </div>
          ))}
          {(caseData.unverified||[]).map(f=>(
            <div key={f} style={{display:'flex',alignItems:'center',gap:8,padding:'4px 0'}}>
              <span style={{fontSize:11,color:'var(--warn)',fontWeight:700}}>&ndash;</span>
              <span style={{fontSize:12.5,color:'var(--text-secondary)',flex:1}}>{f.replace(/_/g,' ')}</span>
              <span style={{fontSize:10,fontWeight:600,color:'var(--warn)',letterSpacing:'0.03em'}}>UNCERTAIN</span>
            </div>
          ))}
        </div>
      )}
      {conf!=null&&(
        <div>
          <div style={{display:'flex',justifyContent:'space-between',alignItems:'baseline',marginBottom:8}}>
            <span className="t-label" style={{color:'var(--text-muted)'}}>Confidence</span>
            <span style={{fontSize:20,fontWeight:700,letterSpacing:'-0.03em',color:cc}}>{conf}%</span>
          </div>
          <div className="progress"><div className="confidence-bar__fill" style={{width:${conf}%,background:cc}} /></div>
          {caseData.confidence_fields&&Object.entries(caseData.confidence_fields).map(([f,l])=>(
            <div key={f} style={{display:'flex',justifyContent:'space-between',padding:'3px 0',marginTop:8}}>
              <span style={{fontSize:11,color:'var(--text-tertiary)'}}>{f.replace(/_/g,' ')}</span>
              <span style={{fontSize:10,fontWeight:700,color:l==='HIGH'?'var(--ok)':l==='LOW'?'var(--warn)':'var(--danger)'}}>{l}</span>
            </div>
          ))}
        </div>
      )}
      {caseData.summary&&(
        <div>
          <div className="t-label" style={{color:'var(--text-muted)',marginBottom:7}}>Summary</div>
          <p style={{fontSize:12.5,color:'var(--text-secondary)',lineHeight:1.6,margin:0}}>{caseData.summary}</p>
        </div>
      )}
      {caseData.reason_for_escalation&&(
        <div style={{padding:'10px 12px',background:'var(--danger-bg)',border:'1px solid var(--danger-border)',borderRadius:'var(--r-md)'}}>
          <div className="t-label" style={{color:'var(--danger)',marginBottom:5}}>Escalation reason</div>
          <p style={{fontSize:12.5,color:'var(--text-primary)',margin:0,lineHeight:1.5}}>{caseData.reason_for_escalation}</p>
        </div>
      )}
    </div>
  )
}
""".strip()

for path, content in files.items():
    p = base / path
    p.write_text(content, encoding='utf-8')
    print(f'wrote {path} ({len(content)} chars)')

print('done')
