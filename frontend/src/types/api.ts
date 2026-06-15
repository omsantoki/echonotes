// Mirrors the EchoNotes FastAPI JSON contract (specs/001-echonotes-core/contracts/api.md).

export type SourceType = 'slides' | 'spoken' | 'diagram'
export type LectureStatus = 'uploaded' | 'processing' | 'ready' | 'failed'

export interface CourseSummary {
  id: string
  name: string
  lecture_count: number
}

export interface CourseCreated {
  id: string
  name: string
  created_at: string
}

export interface LectureSummary {
  id: string
  title: string
  date: string | null
  status: LectureStatus
}

export interface CourseDetail {
  id: string
  name: string
  lectures: LectureSummary[]
}

export interface BuildsOn {
  lecture_id: string
  lecture_title: string
  topic: string
  similarity: number
}

export interface Segment {
  source_type: SourceType
  text: string
  reason: string
  confidence: number
  spoken_only: boolean
  diagram_ref: string | null
  /** "/assets/…" path to the preserved diagram image (diagram segments only). */
  image_ref?: string | null
}

export interface Topic {
  topic: string
  segments: Segment[]
  builds_on?: BuildsOn
}

export interface LectureDocument {
  topics: Topic[]
}

/** GET /api/lectures/{id} — discriminated on `status`. */
export type LectureResponse =
  | { id: string; status: 'uploaded' | 'processing' | 'failed'; progress: string }
  | { id: string; status: 'ready'; title: string; document: LectureDocument }

export interface UploadAccepted {
  lecture_id: string
  status: 'processing'
}

export interface SearchResult {
  lecture_id: string
  lecture_title: string
  topic: string
  text: string
  source_type: SourceType
}

export interface SearchResponse {
  query: string
  results: SearchResult[]
}

export interface ApiError {
  error: { code: string; message: string }
}

// --- Auth & accounts (feature 002, specs/002-accounts-multitenancy/contracts/api.md) ---

export type AuthProvider = 'local' | 'google'

export interface User {
  id: string
  email: string
  auth_provider: AuthProvider
  email_verified: boolean
  created_at?: string
}

/** POST /api/auth/{set-password,login,google} */
export interface SessionResponse {
  session_token: string
  user: User
}

/** POST /api/auth/signup and /forgot-password */
export interface OkMessage {
  ok: boolean
  message: string
}

/** POST /api/auth/verify-otp */
export interface VerifyOtpResponse {
  set_password_token: string
}
