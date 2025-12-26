import { useState, useEffect, useCallback, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { authApi, parseJwtPayload, Tenant } from '../api/auth'

export function useAuth() {
  const queryClient = useQueryClient()
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('access_token'))

  // Parse tenant info from JWT token
  const tokenPayload = useMemo(() => {
    if (!token) return null
    return parseJwtPayload(token)
  }, [token])

  // Current tenant from token
  const currentTenant = useMemo((): Tenant | null => {
    if (!tokenPayload?.tenant_id || !tokenPayload?.available_tenants) return null
    return tokenPayload.available_tenants.find(t => t.id === tokenPayload.tenant_id) ?? null
  }, [tokenPayload])

  // Available tenants from token
  const availableTenants = useMemo((): Tenant[] => {
    return tokenPayload?.available_tenants ?? []
  }, [tokenPayload])

  // Tenant roles (preferred) or legacy user roles
  const effectiveRoles = useMemo((): string[] => {
    if (tokenPayload?.tenant_roles?.length) return tokenPayload.tenant_roles
    return tokenPayload?.roles ?? []
  }, [tokenPayload])

  // Is currently impersonating
  const isImpersonating = useMemo((): boolean => {
    return !!tokenPayload?.impersonating
  }, [tokenPayload])

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

  const switchTenantMutation = useMutation({
    mutationFn: authApi.switchTenant,
    onSuccess: (data) => {
      localStorage.setItem('access_token', data.access_token)
      setToken(data.access_token)
      queryClient.invalidateQueries({ queryKey: ['currentUser'] })
      // Invalidate all data queries when switching tenants
      queryClient.invalidateQueries({ queryKey: ['encounters'] })
    },
  })

  const impersonateMutation = useMutation({
    mutationFn: authApi.impersonate,
    onSuccess: (data) => {
      localStorage.setItem('access_token', data.access_token)
      setToken(data.access_token)
      queryClient.invalidateQueries({ queryKey: ['currentUser'] })
      queryClient.clear()
    },
  })

  const stopImpersonationMutation = useMutation({
    mutationFn: authApi.stopImpersonation,
    onSuccess: (data) => {
      localStorage.setItem('access_token', data.access_token)
      setToken(data.access_token)
      queryClient.invalidateQueries({ queryKey: ['currentUser'] })
      queryClient.clear()
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
    // Tenant context
    currentTenant,
    availableTenants,
    effectiveRoles,
    switchTenant: switchTenantMutation.mutate,
    isSwitchingTenant: switchTenantMutation.isPending,
    // Impersonation
    isImpersonating,
    impersonate: impersonateMutation.mutate,
    stopImpersonation: stopImpersonationMutation.mutate,
  }
}
