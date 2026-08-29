import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import Caller from './pages/Caller'
import Agent from './pages/Agent'

function Nav() {
  return (
    <nav style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      padding: '12px 24px', borderBottom: '1px solid var(--border)',
      background: 'var(--bg-card)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ fontSize: 20, fontWeight: 700, color: 'var(--accent)' }}>PRISM</span>
        <span style={{ fontSize: 11, color: 'var(--text-secondary)', letterSpacing: 1 }}>
          POLYGLOT REAL-TIME INTELLIGENT SUPPORT MEDIATOR
        </span>
      </div>
      <div style={{ display: 'flex', gap: 24 }}>
        <Link to="/" style={{ color: 'var(--text-secondary)', textDecoration: 'none', fontSize: 14 }}>
          Caller
        </Link>
        <Link to="/agent" style={{ color: 'var(--text-secondary)', textDecoration: 'none', fontSize: 14 }}>
          Agent Dashboard
        </Link>
      </div>
    </nav>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Nav />
      <Routes>
        <Route path="/" element={<Caller />} />
        <Route path="/agent" element={<Agent />} />
      </Routes>
    </BrowserRouter>
  )
}
