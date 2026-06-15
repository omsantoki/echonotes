/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Origin of the FastAPI backend; blank in dev (Vite proxy). */
  readonly VITE_API_BASE?: string
  /** Google OAuth Web client id; blank hides the "Continue with Google" button. */
  readonly VITE_GOOGLE_CLIENT_ID?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
