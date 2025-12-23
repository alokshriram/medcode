import { apiClient } from './client'

export interface UploadResult {
  files_received: number
  messages_found: number
  messages_processed: number
  messages_failed: number
  encounters_created: number
  encounters_updated: number
  errors: string[]
}

export interface Encounter {
  id: string
  patient_id: string
  visit_number: string
  encounter_type: string | null
  service_line: string | null
  status: string
  admit_datetime: string | null
  discharge_datetime: string | null
  ready_to_code_at: string | null
  ready_to_code_reason: string | null
  created_at: string
  updated_at: string
}

export interface EncounterListResponse {
  items: Encounter[]
  total: number
  skip: number
  limit: number
}

export const encountersApi = {
  /**
   * Upload HL7 files for processing
   */
  uploadHL7Files: async (files: File[]): Promise<UploadResult> => {
    const formData = new FormData()
    files.forEach((file) => {
      formData.append('files', file)
    })

    const response = await apiClient.post<UploadResult>('/encounters/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  /**
   * List encounters with optional filters
   */
  listEncounters: async (params?: {
    status?: string
    encounter_type?: string
    service_line?: string
    skip?: number
    limit?: number
  }): Promise<EncounterListResponse> => {
    const response = await apiClient.get<EncounterListResponse>('/encounters', { params })
    return response.data
  },

  /**
   * Get a single encounter by ID
   */
  getEncounter: async (encounterId: string): Promise<Encounter> => {
    const response = await apiClient.get<Encounter>(`/encounters/${encounterId}`)
    return response.data
  },

  /**
   * Mark an encounter as ready to code
   */
  markReadyToCode: async (encounterId: string): Promise<Encounter> => {
    const response = await apiClient.post<Encounter>(`/encounters/${encounterId}/ready-to-code`)
    return response.data
  },
}
