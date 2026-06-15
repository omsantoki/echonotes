import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export function useCourse(courseId: string | undefined) {
  return useQuery({
    queryKey: ['course', courseId],
    queryFn: () => api.getCourse(courseId as string),
    enabled: Boolean(courseId),
  })
}
