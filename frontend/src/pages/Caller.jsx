import VoiceInterface from '../components/VoiceInterface'

export default function Caller() {
  return (
    <div style={{
      minHeight: 'calc(100vh - 53px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--bg-primary)'
    }}>
      <VoiceInterface />
    </div>
  )
}
