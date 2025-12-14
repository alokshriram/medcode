import { useState, useEffect, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { authApi } from '../api/auth'

export function useAuth() {
  const queryClient = useQueryClient()
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('access_token'))

  const { data: user, isLoading } = useQuery({
    queryKey: ['currentUser'],
    queryFn: authApi.getCurrentUser,
    enabled: !!token,
    retry: false,
  })

  const loginMutation = useMutation({
    mutationFn: authApi.googleLogin,
    onSuccess: (data) => {
      localStorage.setItem('access_token', data.access_token)
      setToken(data.access_token)
      queryClient.invalidateQueries({ queryKey: ['currentUser'] })
    },
  })

  const logout = useCallback(() => {
    localStorage.removeItem('access_token')
    setToken(null)
    queryClient.clear()
  }, [queryClient])

  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'access_token') {
        setToken(e.newValue)
      }
    }
    window.addEventListener('storage', handleStorageChange)
    return () => window.removeEventListener('storage', handleStorageChange)
  }, [])

  return {
    user,
    isLoading,
    isAuthenticated: !!token && !!user,
    login: loginMutation.mutate,
    loginError: loginMutation.error,
    isLoggingIn: loginMutation.isPending,
    logout,
  }
}
