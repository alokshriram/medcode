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

export interface Patient {
  id: string
  mrn: string
  name_given: string | null
  name_family: string | null
  date_of_birth: string | null
  gender: string | null
}

export interface EncounterWithPatient extends Encounter {
  patient: Patient
}

export interface EncounterListResponse {
  encounters: Encounter[]
  total: number
  skip: number
  limit: number
}

export interface EncounterWithPatientListResponse {
  encounters: EncounterWithPatient[]
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
    include_patient?: boolean
  }): Promise<EncounterListResponse | EncounterWithPatientListResponse> => {
    const response = await apiClient.get<EncounterListResponse | EncounterWithPatientListResponse>(
      '/encounters',
      { params }
    )
    return response.data
  },

  /**
   * List encounters with patient info included
   */
  listEncountersWithPatient: async (params?: {
    status?: string
    encounter_type?: string
    service_line?: string
    skip?: number
    limit?: number
  }): Promise<EncounterWithPatientListResponse> => {
    const response = await apiClient.get<EncounterWithPatientListResponse>('/encounters', {
      params: { ...params, include_patient: true },
    })
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
