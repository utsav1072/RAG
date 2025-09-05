import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { AuthAPI, getTokens } from './api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [isLoading, setIsLoading] = useState(true)

  const loadUser = useCallback(async () => {
    try {
      if (!getTokens()) {
        setUser(null)
        return
      }
      const me = await AuthAPI.me()
      setUser(me)
    } catch {
      setUser(null)
    }
  }, [])

  useEffect(() => {
    ;(async () => {
      await loadUser()
      setIsLoading(false)
    })()
  }, [loadUser])

  const login = async (username, password) => {
    await AuthAPI.login(username, password)
    await loadUser()
  }

  const register = async (payload) => {
    await AuthAPI.register(payload)
  }

  const logout = () => {
    AuthAPI.logout()
    setUser(null)
  }

  const value = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    register,
    logout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}


