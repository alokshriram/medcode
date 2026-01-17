import { apiClient } from './client'

// --- Types ---

export interface CodingQueueItem {
  id: string
  tenant_id: string | null
  encounter_id: string
  billing_component: 'facility' | 'professional'
  queue_type: string | null
  service_line: string | null
  payer_identifier: string | null
  priority: number
  status: string
  assigned_to: string | null
  assigned_at: string | null
  completed_at: string | null
  completed_by: string | null
  created_at: string
  updated_at: string
}

export interface CodingQueueItemWithPatient extends CodingQueueItem {
  patient_name: string | null
  patient_mrn: string | null
  visit_number: string
  encounter_type: string | null
}

export interface CodingQueueListResponse {
  items: CodingQueueItemWithPatient[]
  total: number
  skip: number
  limit: number
}

export interface SnapshotPatient {
  id: string | null
  mrn: string | null
  name_family: string | null
  name_given: string | null
  date_of_birth: string | null
  gender: string | null
}

export interface SnapshotEncounter {
  id: string
  visit_number: string | null
  encounter_type: string | null
  service_line: string | null
  payer_identifier: string | null
  admit_datetime: string | null
  discharge_datetime: string | null
  admitting_diagnosis: string | null
  discharge_disposition: string | null
  status: string | null
  ready_to_code_at: string | null
  ready_to_code_reason: string | null
}

export interface SnapshotDiagnosis {
  id: string
  set_id?: number | null
  diagnosis_code: string | null
  diagnosis_description: string | null
  diagnosis_type: string | null
  coding_method: string | null
}

export interface SnapshotProcedure {
  id: string
  set_id?: number | null
  procedure_code: string | null
  procedure_description: string | null
  procedure_datetime: string | null
  performing_physician: string | null
  performing_physician_id: string | null
}

export interface SnapshotObservation {
  id: string
  set_id?: number | null
  observation_identifier: string | null
  observation_value: string | null
  units: string | null
  reference_range: string | null
  abnormal_flags: string | null
  observation_datetime: string | null
  result_status: string | null
}

export interface SnapshotOrder {
  id: string
  order_control: string | null
  placer_order_number: string | null
  filler_order_number: string | null
  order_status: string | null
  order_datetime: string | null
  ordering_provider: string | null
  order_type: string | null
  diagnostic_service_section: string | null
}

export interface SnapshotDocument {
  id: string
  document_type: string | null
  document_status: string | null
  origination_datetime: string | null
  author: string | null
  content: string | null
}

export interface SnapshotData {
  snapshot_created_at: string
  patient: SnapshotPatient
  encounter: SnapshotEncounter
  diagnoses: SnapshotDiagnosis[]
  procedures: SnapshotProcedure[]
  observations: SnapshotObservation[]
  orders: SnapshotOrder[]
  documents: SnapshotDocument[]
}

export interface CodingQueueItemDetail extends CodingQueueItem {
  snapshot: SnapshotData | null
  snapshot_version: number | null
}

export interface ListQueueParams {
  status?: string
  billing_component?: 'facility' | 'professional'
  service_line?: string
  assigned_to_me?: boolean
  skip?: number
  limit?: number
}

export interface DiagnosisCodeEntry {
  code: string
  description: string
  is_principal: boolean
  poa_indicator: string | null
  sequence: number
}

export interface ProcedureCodeEntry {
  code: string
  description: string
  code_type: string
  is_principal: boolean
  sequence: number
  procedure_date: string | null
}

export interface SaveCodingResultsRequest {
  diagnosis_codes: DiagnosisCodeEntry[]
  procedure_codes: ProcedureCodeEntry[]
}

export interface CodingResultResponse {
  id: string
  queue_item_id: string
  code: string
  code_type: string
  description: string
  code_category: string
  is_principal: boolean
  poa_indicator: string | null
  sequence: number
  procedure_date: string | null
  coded_by: string
  coded_at: string
}

export interface CodingResultsResponse {
  queue_item_id: string
  diagnosis_codes: CodingResultResponse[]
  procedure_codes: CodingResultResponse[]
}

// --- API Functions ---

export const codingQueueApi = {
  /**
   * List coding queue items with optional filters
   */
  listQueueItems: async (params?: ListQueueParams): Promise<CodingQueueListResponse> => {
    const response = await apiClient.get<CodingQueueListResponse>('/workflow/queue', { params })
    return response.data
  },

  /**
   * Get a single queue item with its snapshot for coding
   */
  getQueueItem: async (itemId: string): Promise<CodingQueueItemDetail> => {
    const response = await apiClient.get<CodingQueueItemDetail>(`/workflow/queue/${itemId}`)
    return response.data
  },

  /**
   * Assign a queue item to a user (defaults to current user)
   */
  assignQueueItem: async (itemId: string, userId?: string): Promise<CodingQueueItem> => {
    const response = await apiClient.post<CodingQueueItem>(`/workflow/queue/${itemId}/assign`, {
      user_id: userId,
    })
    return response.data
  },

  /**
   * Mark a queue item as completed
   */
  completeQueueItem: async (itemId: string): Promise<CodingQueueItem> => {
    const response = await apiClient.post<CodingQueueItem>(`/workflow/queue/${itemId}/complete`)
    return response.data
  },

  /**
   * Refresh the snapshot with latest encounter data
   */
  refreshSnapshot: async (itemId: string): Promise<CodingQueueItemDetail> => {
    const response = await apiClient.post<CodingQueueItemDetail>(
      `/workflow/queue/${itemId}/refresh-snapshot`
    )
    return response.data
  },

  /**
   * Get saved coding results for a queue item
   */
  getCodingResults: async (itemId: string): Promise<CodingResultsResponse> => {
    const response = await apiClient.get<CodingResultsResponse>(
      `/workflow/queue/${itemId}/codes`
    )
    return response.data
  },

  /**
   * Save coding results for a queue item
   */
  saveCodingResults: async (
    itemId: string,
    request: SaveCodingResultsRequest
  ): Promise<CodingResultsResponse> => {
    const response = await apiClient.post<CodingResultsResponse>(
      `/workflow/queue/${itemId}/codes`,
      request
    )
    return response.data
  },
}
