"""Configuration & secrets (task T002).

Single source of truth for API keys, model ids, and storage paths. Loaded from
`.env` (see `.env.example`). Model ids are env-overridable so a stale default
never blocks the build — confirm current ids before Day 2 (research.md).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Provider for the three model stages (transcribe / embed / merge).
    #   "local"  — runs on this machine, no API/keys (faster-whisper +
    #              sentence-transformers + Ollama). Default.
    #   "openai" — hosted OpenAI (needs OPENAI_API_KEY + account credit).
    provider: str = "local"

    # --- OpenAI (provider="openai") ---
    openai_api_key: str = ""
    chat_model: str = "gpt-4o"                      # merge + diagram vision
    transcribe_model: str = "whisper-1"             # audio -> timestamped segments
    embedding_model: str = "text-embedding-3-small"  # OpenAI's embedding model

    # --- Local stack (provider="local") ---
    whisper_model: str = "small"                    # faster-whisper size: tiny|base|small|medium (bigger = more accurate, slower)
    local_embedding_model: str = "all-MiniLM-L6-v2"  # THE one embedding model (Art. VI)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"                  # any pulled Ollama chat model
    ollama_vision_model: str = "llava"              # any pulled Ollama vision model (llava, llama3.2-vision, ...)

    # Diagram descriptions via a vision model (Strong, T030/FR-9). Best-effort:
    # if no vision model is available the diagram is kept with a plain caption.
    describe_diagrams: bool = True

    # Optional refine pass (a second LLM cleanup). The merge already synthesizes the
    # UNION of slides + transcript and de-duplicates in one pass, so this is OFF by
    # default — turn it on for an extra cleanup. Kept provenance-preserving (Art. III).
    refine_notes: bool = False
    refine_model: str = ""   # blank = reuse the merge model (ollama_model / chat_model)

    # Storage. Chroma is the vector store / sole persistence layer for notes;
    # DATA_DIR holds the tiny course/lecture registry. No audio is ever stored.
    chroma_dir: str = "./.chroma"
    data_dir: str = "./data"

    # CORS — origins allowed to call the JSON API from a browser. The separate
    # React frontend uses the Vite dev proxy locally (so this is irrelevant in
    # dev), but production serves the SPA from another origin. Comma-separated.
    cors_origins: str = "http://localhost:5173,http://localhost:4173"

    # Server-rendered console (app/web.py). It is single-tenant — every page acts as
    # the bootstrap admin with NO login — so it must never be exposed publicly: an
    # anonymous visitor could otherwise create courses and upload lectures (spending
    # the OpenAI budget) and read the admin's data. The multi-tenant product surface
    # is the React SPA + JSON API (per-user auth). Default ON for zero-config local
    # dev; production (render.yaml) sets ENABLE_WEB_CONSOLE=false.
    enable_web_console: bool = True

    # --- Cloud storage backends (leave ALL blank for local dev: Chroma +
    # registry.json + on-disk images). Each subsystem switches to its managed
    # service the moment its env var is set — see app/store.py selectors. ---
    # Vectors: Qdrant if QDRANT_URL set; else remote Chroma if CHROMA_HTTP_URL set; else local Chroma.
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    qdrant_collection: str = "notechunks"
    qdrant_timeout: int = 60        # seconds; generous so cross-region upserts don't time out
    chroma_http_url: str = ""       # e.g. http://host:8000 (remote Chroma server)
    chroma_api_key: str = ""        # optional bearer token for a remote Chroma
    # Registry: managed Postgres if DATABASE_URL set; else local registry.json.
    database_url: str = ""          # postgresql://user:pass@host/db?sslmode=require
    # Diagram images: object storage (R2/S3) if S3_BUCKET set; else local disk + /assets mount.
    s3_bucket: str = ""
    s3_endpoint_url: str = ""       # R2 endpoint; blank = real AWS S3
    s3_region: str = "auto"         # "auto" for R2
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_public_base_url: str = ""    # public URL prefix returned in image_ref

    # Pipeline tuning.
    align_top_k: int = 3     # attach each spoken segment to its top-3 near-tie sections (decision D-1)
    retrieve_top_n: int = 5  # cap cross-lecture context (Art. VI rationale)

    # Cross-lecture linking (Stretch, T040/T041): link a topic to the most similar
    # EARLIER lecture in the same course, when similarity clears the threshold.
    link_lectures: bool = True
    link_min_similarity: float = 0.5

    # --- Auth & multi-tenancy (feature 002, Constitution Art. X) ---
    # ALL of these have safe blank/dev defaults so local dev runs with zero external
    # services: blank JWT_SECRET → a dev-only signing key; blank SMTP → OTP/reset links
    # print to the server log; blank GOOGLE_OAUTH_CLIENT_ID → the Google button is hidden.
    # NEVER ship a blank JWT_SECRET to production — set a strong random value there.
    jwt_secret: str = ""             # blank = dev-only fallback key (see auth/security.py)
    jwt_expiry: int = 86400          # session lifetime, seconds (24h)
    otp_ttl: int = 600               # OTP lifetime, seconds (~10 min)
    otp_max_attempts: int = 5        # failed OTP checks before the code is locked
    reset_token_ttl: int = 3600      # set-password / reset-link lifetime, seconds (1h)
    frontend_url: str = "http://localhost:5173"  # base for reset links emailed to users

    # SMTP (blank host = email prints to the server log; no mail server needed in dev).
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""          # Gmail: an App Password — never the real password
    smtp_from: str = ""              # defaults to smtp_user when blank

    # Google sign-in (blank = the "Continue with Google" button is hidden / endpoint 503s).
    google_oauth_client_id: str = ""

    # Bootstrap admin: legacy pre-002 ("common") courses are migrated to this owner.
    bootstrap_admin_email: str = "admin@echonotes.local"


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor — import this, don't instantiate Settings directly."""
    return Settings()


def require_openai_key() -> str:
    """Return the configured OpenAI key, or fail with an actionable message.

    Used by every OpenAI client factory so a missing key surfaces as clear
    guidance instead of the SDK's generic 'Missing credentials' error.
    """
    key = get_settings().openai_api_key
    if not key or key == "sk-...":  # unset or still the .env.example placeholder
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Edit the .env file's OPENAI_API_KEY line "
            "with your real key, then restart the server "
            "(uvicorn does not reload on .env changes)."
        )
    return key


def active_embedding_model() -> str:
    """The one embedding model in force for this provider (Art. VI)."""
    s = get_settings()
    return s.local_embedding_model if s.provider == "local" else s.embedding_model


def active_storage() -> dict:
    """Which storage backend each subsystem resolves to (surfaced by /api/health,
    so a deploy can be verified at a glance without leaking any credentials)."""
    s = get_settings()
    return {
        "vectors": "qdrant" if s.qdrant_url
        else ("chroma-remote" if s.chroma_http_url else "chroma-local"),
        "registry": "postgres" if s.database_url else "json",
        "objects": "s3" if s.s3_bucket else "local",
    }
