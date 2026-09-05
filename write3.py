import pathlib

base = pathlib.Path(r'd:/WORK AND STUDY/PRISM/frontend/src')

# ─── Caller.jsx ───────────────────────────────────────────────────
caller = r'''
import VoiceInterface from '../components/VoiceInterface'

export default function Caller() {
  return (
    <div style={{
      minHeight:'100vh',
      display:'flex',
      alignItems:'center',
      justifyContent:'center',
      padding:'32px 20px',
      background:'var(--surface-1)',
      position:'relative',
    }}>
      {/* Subtle top highlight */}
      <div style={{position:'absolute',top:0,left:0,right:0,height:1,background:'var(--border-subtle)',pointerEvents:'none'}} />

      <div style={{position:'relative',zIndex:1,width:'100%',maxWidth:520}}>
        <VoiceInterface />
      </div>

      <div style={{position:'absolute',bottom:20,right:28,zIndex:2}}>
        <a href="/agent" style={{fontSize:11,color:'var(--text-muted)',textDecoration:'none',fontWeight:500,transition:'color 0.15s ease'}}
           onMouseEnter={e=>e.currentTarget.style.color='var(--text-secondary)'}
           onMouseLeave={e=>e.currentTarget.style.color='var(--text-muted)'}>
          Agent dashboard &rarr;
        </a>
      </div>
    </div>
  )
}
'''.strip()

(base / 'pages/Caller.jsx').write_text(caller, encoding='utf-8')
print(f'Caller.jsx written ({len(caller)} chars)')
print('done')
