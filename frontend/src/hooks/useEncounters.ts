import { useQuery } from '@tanstack/react-query'
import { encountersApi, EncounterWithPatientListResponse } from '../api/encounters'

interface UseEncountersParams {
  status?: string
  encounter_type?: string
  service_line?: string
  skip?: number
  limit?: number
}

export function useEncounters(params?: UseEncountersParams) {
  return useQuery<EncounterWithPatientListResponse>({
    queryKey: ['encounters', params],
    queryFn: () => encountersApi.listEncountersWithPatient(params),
  })
}
