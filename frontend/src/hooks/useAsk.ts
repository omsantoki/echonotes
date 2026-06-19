import { useMutation } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { AskResponse } from '@/types/api'

/**
 * "Ask your notes" — a grounded LLM answer over a course's notes. A mutation (not a
 * query) because asking is an explicit submit; the backend's semantic cache makes a
 * repeated/near-duplicate question return instantly (`cached: true`).
 */
export function useAsk(courseId: string | undefined) {
  return useMutation<AskResponse, Error, string>({
    mutationFn: (question: string) => api.askCourse(courseId as string, question.trim()),
  })
}
