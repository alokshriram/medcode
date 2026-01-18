import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  codingQueueApi,
  ListQueueParams,
  CodingQueueListResponse,
  CodingQueueItemDetail,
  CodingQueueItem,
  SaveCodingResultsRequest,
  CodingResultsResponse,
} from '../api/codingQueue'

/**
 * Hook to fetch the coding queue list with optional filters
 */
export function useCodingQueue(params?: ListQueueParams) {
  return useQuery<CodingQueueListResponse>({
    queryKey: ['codingQueue', params],
    queryFn: () => codingQueueApi.listQueueItems(params),
  })
}

/**
 * Hook to fetch a single queue item with its snapshot
 */
export function useCodingQueueItem(itemId: string | undefined) {
  return useQuery<CodingQueueItemDetail>({
    queryKey: ['codingQueueItem', itemId],
    queryFn: () => codingQueueApi.getQueueItem(itemId!),
    enabled: !!itemId,
  })
}

/**
 * Hook to assign a queue item to a user
 */
export function useAssignQueueItem() {
  const queryClient = useQueryClient()

  return useMutation<CodingQueueItem, Error, { itemId: string; userId?: string }>({
    mutationFn: ({ itemId, userId }) => codingQueueApi.assignQueueItem(itemId, userId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['codingQueue'] })
      queryClient.invalidateQueries({ queryKey: ['codingQueueItem', variables.itemId] })
    },
  })
}

/**
 * Hook to mark a queue item as completed
 */
export function useCompleteQueueItem() {
  const queryClient = useQueryClient()

  return useMutation<CodingQueueItem, Error, string>({
    mutationFn: (itemId) => codingQueueApi.completeQueueItem(itemId),
    onSuccess: (_, itemId) => {
      queryClient.invalidateQueries({ queryKey: ['codingQueue'] })
      queryClient.invalidateQueries({ queryKey: ['codingQueueItem', itemId] })
    },
  })
}

/**
 * Hook to refresh the snapshot for a queue item
 */
export function useRefreshSnapshot() {
  const queryClient = useQueryClient()

  return useMutation<CodingQueueItemDetail, Error, string>({
    mutationFn: (itemId) => codingQueueApi.refreshSnapshot(itemId),
    onSuccess: (data, itemId) => {
      queryClient.setQueryData(['codingQueueItem', itemId], data)
    },
  })
}

/**
 * Hook to get saved coding results for a queue item
 */
export function useCodingResults(itemId: string | undefined) {
  return useQuery<CodingResultsResponse>({
    queryKey: ['codingResults', itemId],
    queryFn: () => codingQueueApi.getCodingResults(itemId!),
    enabled: !!itemId,
  })
}

/**
 * Hook to save coding results for a queue item
 */
export function useSaveCodingResults() {
  const queryClient = useQueryClient()

  return useMutation<
    CodingResultsResponse,
    Error,
    { itemId: string; request: SaveCodingResultsRequest }
  >({
    mutationFn: ({ itemId, request }) => codingQueueApi.saveCodingResults(itemId, request),
    onSuccess: (data, variables) => {
      queryClient.setQueryData(['codingResults', variables.itemId], data)
    },
  })
}
