import { useQuery } from '@tanstack/react-query'
import { catalogsApi } from '../api/catalogs'

export function useCatalogSearch(query: string, enabled = true) {
  return useQuery({
    queryKey: ['catalogSearch', query],
    queryFn: () => catalogsApi.searchCodes(query),
    enabled: enabled && query.length >= 2,
    staleTime: 10 * 60 * 1000,
  })
}
