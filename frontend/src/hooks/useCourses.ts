import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'

export function useCourses() {
  return useQuery({ queryKey: ['courses'], queryFn: api.listCourses })
}

export function useCreateCourse() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (name: string) => api.createCourse(name),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['courses'] }),
  })
}

export function useDeleteCourse() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.deleteCourse(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ['courses'] })
      qc.removeQueries({ queryKey: ['course', id] })
    },
  })
}
