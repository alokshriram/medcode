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
}
