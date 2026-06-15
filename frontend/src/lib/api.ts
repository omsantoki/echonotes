import { apiUrl, ApiRequestError, del, getJson, postJson } from '@/lib/http'
import type {
  CourseCreated,
  CourseDetail,
  CourseSummary,
  LectureResponse,
  SearchResponse,
  UploadAccepted,
} from '@/types/api'

export interface UploadInput {
  course_id: string
  title: string
  audio: File
  slides: File
}

/**
 * Multipart upload via XHR (not fetch) so we can report transfer progress.
 * Returns the 202 body; the pipeline then runs in the background.
 */
export function uploadLecture(
  input: UploadInput,
  onProgress?: (fraction: number) => void,
): Promise<UploadAccepted> {
  const form = new FormData()
  form.append('course_id', input.course_id)
  form.append('title', input.title)
  form.append('audio', input.audio)
  form.append('slides', input.slides)

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', apiUrl('/api/lectures'))
    xhr.responseType = 'json'
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) onProgress(e.loaded / e.total)
    }
    xhr.onload = () => {
      const body = xhr.response
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(body as UploadAccepted)
      } else {
        const err = body?.error
        reject(
          new ApiRequestError(err?.message ?? 'Upload failed', err?.code ?? 'error', xhr.status),
        )
      }
    }
    xhr.onerror = () =>
      reject(new ApiRequestError('Network error during upload', 'network_error', 0))
    xhr.send(form)
  })
}

export const api = {
  listCourses: () => getJson<CourseSummary[]>('/api/courses'),
  createCourse: (name: string) => postJson<CourseCreated>('/api/courses', { name }),
  getCourse: (id: string) => getJson<CourseDetail>(`/api/courses/${id}`),
  searchCourse: (id: string, q: string) =>
    getJson<SearchResponse>(`/api/courses/${id}/search?q=${encodeURIComponent(q)}`),
  getLecture: (id: string) => getJson<LectureResponse>(`/api/lectures/${id}`),
  exportLectureUrl: (id: string, format: 'md' | 'html') =>
    apiUrl(`/api/lectures/${id}/export?format=${format}`),
  uploadLecture,
  deleteCourse: (id: string) => del(`/api/courses/${id}`),
  deleteLecture: (id: string) => del(`/api/lectures/${id}`),
}
