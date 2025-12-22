import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { encountersApi, UploadResult } from '../api/encounters'

export function useUploadHL7() {
  const queryClient = useQueryClient()
  const [uploadProgress, setUploadProgress] = useState<number>(0)

  const mutation = useMutation({
    mutationFn: async (files: File[]) => {
      setUploadProgress(0)
      // Since we can't track actual upload progress with our current setup,
      // we'll simulate progress for UX
      setUploadProgress(30)
      const result = await encountersApi.uploadHL7Files(files)
      setUploadProgress(100)
      return result
    },
    onSuccess: () => {
      // Invalidate relevant queries to refresh data
      queryClient.invalidateQueries({ queryKey: ['encounters'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
    onSettled: () => {
      // Reset progress after a short delay
      setTimeout(() => setUploadProgress(0), 1000)
    },
  })

  return {
    upload: mutation.mutate,
    uploadAsync: mutation.mutateAsync,
    isUploading: mutation.isPending,
    uploadResult: mutation.data as UploadResult | undefined,
    uploadError: mutation.error,
    uploadProgress,
    reset: mutation.reset,
  }
}
