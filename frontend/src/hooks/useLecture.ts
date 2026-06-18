import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { ApiRequestError } from '@/lib/http'

/**
 * Fetches a lecture, polling every 2s while it is still processing and stopping the
 * moment it reaches a terminal state (ready / failed) OR errors (e.g. 404 not-found /
 * not-owned). Terminal client errors (4xx) are not retried — only transient failures.
 */
export function useLecture(lectureId: string | undefined) {
  return useQuery({
    queryKey: ['lecture', lectureId],
    queryFn: () => api.getLecture(lectureId as string),
    enabled: Boolean(lectureId),
    retry: (failureCount, err) => {
      // A 404/403/401 is terminal — don't retry it; only retry transient (network/5xx) errors once.
      if (err instanceof ApiRequestError && err.status >= 400 && err.status < 500) return false
      return failureCount < 1
    },
    refetchInterval: (query) => {
      if (query.state.status === 'error') return false // stop polling once it errors (e.g. 404)
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
