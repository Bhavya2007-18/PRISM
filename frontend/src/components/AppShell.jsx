import { useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import Sidebar, { BottomNav } from './Sidebar'
import TopBar from './TopBar'
import { useNavContext } from '../context/NavContext'

export default function AppShell({ sidebarBadges, pageTitle, connectionStatus }) {
  const [sidebarExpanded, setSidebarExpanded] = useState(true)
  const location = useLocation()
  const navCtx   = useNavContext()

  const titleMap = {
    '/': 'Live Session',
    '/agent': 'Dashboard',
  }
  const derivedTitle = titleMap[location.pathname] || 'PRISM'

  function toggleSidebar() {
    setSidebarExpanded(prev => !prev)
  }

  return (
    <div
      className="app-shell"
      style={{ '--sidebar-width': sidebarExpanded ? '232px' : '72px' }}
    >
      <Sidebar
        expanded={sidebarExpanded}
        onToggle={toggleSidebar}
        badges={sidebarBadges}
        activeRoute={location.pathname}
        activeIntraNav={navCtx?.activeIntraNav}
      />
      <TopBar
        title={pageTitle || derivedTitle}
        onToggleSidebar={toggleSidebar}
        connectionStatus={connectionStatus}
      />
      <main className="app-main">
        <Outlet />
      </main>
      <BottomNav
        activeRoute={location.pathname}
        badges={sidebarBadges}
        activeIntraNav={navCtx?.activeIntraNav}
      />
    </div>
  )
}
