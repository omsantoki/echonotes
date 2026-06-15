import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export function useCourseSearch(courseId: string | undefined, query: string) {
  const q = query.trim()
  return useQuery({
    queryKey: ['search', courseId, q],
    queryFn: () => api.searchCourse(courseId as string, q),
    enabled: Boolean(courseId) && q.length > 1,
    staleTime: 60_000,
  })
}
