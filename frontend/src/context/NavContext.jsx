import { createContext, useContext, useRef, useState } from 'react'

/**
 * NavContext — lets Agent.jsx register its setActiveNav callback
 * so Sidebar can call it directly across the Outlet boundary.
 * Also tracks activeIntraNav so Sidebar can highlight the active item.
 */
const NavContext = createContext(null)

export function NavProvider({ children }) {
  const setterRef = useRef(null)
  const [activeIntraNav, setActiveIntraNav] = useState('overview')

  // Agent.jsx calls this once on mount to wire up its setActiveNav
  const register = (setter) => { setterRef.current = setter }

  // Sidebar calls this when a nav item is clicked
  const navigate = (id) => {
    setActiveIntraNav(id)
    setterRef.current?.(id)
  }

  return (
    <NavContext.Provider value={{ register, navigate, activeIntraNav }}>
      {children}
    </NavContext.Provider>
  )
}

export function useNavContext() {
  return useContext(NavContext)
}
