import { useQuery } from '@tanstack/react-query'
import { bffApi } from '../api/bff'

export function useDashboard() {
  return useQuery({
    queryKey: ['dashboard'],
    queryFn: bffApi.getDashboard,
    refetchInterval: 30 * 1000,
  })
}
