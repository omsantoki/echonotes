import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { UploadInput } from '@/lib/api'
import type { LectureResponse } from '@/types/api'

export function useUploadLecture(courseId: string) {
  const qc = useQueryClient()
  const [progress, setProgress] = useState(0)

  const mutation = useMutation({
    mutationFn: (input: UploadInput) => {
      setProgress(0)
      return api.uploadLecture(input, setProgress)
    },
    onSuccess: (data) => {
      // Seed the lecture cache so the reading page shows the tracker with no flash.
      const seed: LectureResponse = {
        id: data.lecture_id,
        status: 'processing',
        progress: 'Queued…',
      }
      qc.setQueryData(['lecture', data.lecture_id], seed)
      qc.invalidateQueries({ queryKey: ['course', courseId] })
      qc.invalidateQueries({ queryKey: ['courses'] })
    },
  })

  return { ...mutation, progress }
}
