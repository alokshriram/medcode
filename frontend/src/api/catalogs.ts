import { apiClient } from './client'

interface ICD10Code {
  id: string
  code: string
  description: string
  category: string | null
  is_billable: boolean
}

interface CPTCode {
  id: string
  code: string
  description: string
  long_description: string | null
  category: string | null
}

interface CodeSearchResponse {
  icd10_codes: ICD10Code[]
  cpt_codes: CPTCode[]
}

export const catalogsApi = {
  searchCodes: async (query: string, limit = 25): Promise<CodeSearchResponse> => {
    const response = await apiClient.get<CodeSearchResponse>('/catalogs/search', {
      params: { q: query, limit },
    })
    return response.data
  },

  getICD10Codes: async (skip = 0, limit = 100): Promise<ICD10Code[]> => {
    const response = await apiClient.get<ICD10Code[]>('/catalogs/icd10', {
      params: { skip, limit },
    })
    return response.data
  },

  getCPTCodes: async (skip = 0, limit = 100): Promise<CPTCode[]> => {
    const response = await apiClient.get<CPTCode[]>('/catalogs/cpt', {
      params: { skip, limit },
    })
    return response.data
  },
}
