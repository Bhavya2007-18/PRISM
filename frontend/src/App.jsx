import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import Caller from './pages/Caller'
import Agent from './pages/Agent'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Caller />} />
        <Route path="/agent" element={<Agent />} />
      </Routes>
    </BrowserRouter>
  )
}
