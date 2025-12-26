import { apiClient } from './client'

interface TokenResponse {
  access_token: string
  token_type: string
}

interface User {
  id: string
  email: string
  full_name: string
  picture_url: string | null
  roles: string[]
  is_active: boolean
}

export interface Tenant {
  id: string
  name: string
  slug: string
}

export interface TokenPayload {
  sub: string
  email: string
  roles: string[]
  tenant_id?: string
  tenant_roles?: string[]
  available_tenants?: Tenant[]
  impersonating?: string
  exp: number
}

export function parseJwtPayload(token: string): TokenPayload | null {
  try {
    const base64Url = token.split('.')[1]
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    )
    return JSON.parse(jsonPayload)
  } catch {
    return null
  }
}

export const authApi = {
  googleLogin: async (credential: string): Promise<TokenResponse> => {
    const response = await apiClient.post<TokenResponse>('/users/auth/google', {
      credential,
    })
    return response.data
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await apiClient.get<User>('/users/me')
    return response.data
  },

  switchTenant: async (tenantId: string): Promise<TokenResponse> => {
    const response = await apiClient.post<TokenResponse>(
      `/users/auth/switch-tenant/${tenantId}`
    )
    return response.data
  },

  impersonate: async (email: string): Promise<TokenResponse> => {
    const response = await apiClient.post<TokenResponse>('/users/auth/impersonate', {
      email,
    })
    return response.data
  },

  stopImpersonation: async (): Promise<TokenResponse> => {
    const response = await apiClient.post<TokenResponse>('/users/auth/stop-impersonation')
    return response.data
  },
}
