import { BrowserRouter, Routes, Route } from 'react-router-dom'
import AppShell from './components/AppShell'
import Caller from './pages/Caller'
import Agent from './pages/Agent'
import { NavProvider } from './context/NavContext'

export default function App() {
  return (
    <BrowserRouter>
      <NavProvider>
        <Routes>
          <Route element={<AppShell />}>
            <Route path="/" element={<Caller />} />
            <Route path="/agent" element={<Agent />} />
          </Route>
        </Routes>
      </NavProvider>
    </BrowserRouter>
  )
}
