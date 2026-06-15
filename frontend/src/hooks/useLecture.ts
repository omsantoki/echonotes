import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'

/**
 * Fetches a lecture, polling every 2s while it is still processing and stopping
 * the moment it reaches a terminal state (ready / failed).
 */
export function useLecture(lectureId: string | undefined) {
  return useQuery({
    queryKey: ['lecture', lectureId],
    queryFn: () => api.getLecture(lectureId as string),
    enabled: Boolean(lectureId),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'ready' || status === 'failed' ? false : 2000
    },
  })
}

export function useDeleteLecture() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.deleteLecture(id),
    onSuccess: (_data, id) => {
      qc.removeQueries({ queryKey: ['lecture', id] })
      // Refresh any affected course view + the library lecture counts.
      qc.invalidateQueries({ queryKey: ['course'] })
      qc.invalidateQueries({ queryKey: ['courses'] })
    },
  })
}
