# Graph Report - .  (2026-06-17)

## Corpus Check
- 146 files · ~50,782 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1005 nodes · 1923 edges · 82 communities (58 shown, 24 thin omitted)
- Extraction: 74% EXTRACTED · 26% INFERRED · 0% AMBIGUOUS · INFERRED: 507 edges (avg confidence: 0.55)
- Token cost: 0 input · 46,468 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Domain Data Models|Domain Data Models]]
- [[_COMMUNITY_Spoken-Slide Alignment|Spoken-Slide Alignment]]
- [[_COMMUNITY_Test Fixtures & Harness|Test Fixtures & Harness]]
- [[_COMMUNITY_Storage Facade|Storage Facade]]
- [[_COMMUNITY_Course API Endpoints|Course API Endpoints]]
- [[_COMMUNITY_Postgres Registry Backend|Postgres Registry Backend]]
- [[_COMMUNITY_Frontend Dependencies|Frontend Dependencies]]
- [[_COMMUNITY_JSON Registry Backend|JSON Registry Backend]]
- [[_COMMUNITY_Build, CI & Project Docs|Build, CI & Project Docs]]
- [[_COMMUNITY_Auth Service Logic|Auth Service Logic]]
- [[_COMMUNITY_Auth API Endpoints|Auth API Endpoints]]
- [[_COMMUNITY_Note Document UI|Note Document UI]]
- [[_COMMUNITY_TS App Config|TS App Config]]
- [[_COMMUNITY_Auth Crypto & Security|Auth Crypto & Security]]
- [[_COMMUNITY_API Type Definitions|API Type Definitions]]
- [[_COMMUNITY_TS Node Config|TS Node Config]]
- [[_COMMUNITY_Frontend HTTP Client|Frontend HTTP Client]]
- [[_COMMUNITY_Course UI & Hooks|Course UI & Hooks]]
- [[_COMMUNITY_Server-Rendered Web UI|Server-Rendered Web UI]]
- [[_COMMUNITY_Auth Guard & Landing|Auth Guard & Landing]]
- [[_COMMUNITY_Qdrant Vector Store|Qdrant Vector Store]]
- [[_COMMUNITY_Shared UI Components|Shared UI Components]]
- [[_COMMUNITY_Lecture API Endpoints|Lecture API Endpoints]]
- [[_COMMUNITY_Config & Settings|Config & Settings]]
- [[_COMMUNITY_Document Rendering|Document Rendering]]
- [[_COMMUNITY_Auth & Email Unit Tests|Auth & Email Unit Tests]]
- [[_COMMUNITY_Storage Resolver & Health|Storage Resolver & Health]]
- [[_COMMUNITY_Transactional Email|Transactional Email]]
- [[_COMMUNITY_Chroma Vector Store|Chroma Vector Store]]
- [[_COMMUNITY_Google Auth Tests|Google Auth Tests]]
- [[_COMMUNITY_LLM Refinement Pass|LLM Refinement Pass]]
- [[_COMMUNITY_Lecture Reading UI|Lecture Reading UI]]
- [[_COMMUNITY_UI Primitives|UI Primitives]]
- [[_COMMUNITY_Lecture Ingestion|Lecture Ingestion]]
- [[_COMMUNITY_Lecture Upload UI|Lecture Upload UI]]
- [[_COMMUNITY_S3R2 Object Storage|S3/R2 Object Storage]]
- [[_COMMUNITY_Diagram Description (Vision)|Diagram Description (Vision)]]
- [[_COMMUNITY_Cross-Lecture Retrieval|Cross-Lecture Retrieval]]
- [[_COMMUNITY_Google Sign-In UI|Google Sign-In UI]]
- [[_COMMUNITY_Upload API Client|Upload API Client]]
- [[_COMMUNITY_Theme System|Theme System]]
- [[_COMMUNITY_Auth Context|Auth Context]]
- [[_COMMUNITY_Auth Context Tests|Auth Context Tests]]
- [[_COMMUNITY_Theme Toggle|Theme Toggle]]
- [[_COMMUNITY_Processing Tracker UI|Processing Tracker UI]]
- [[_COMMUNITY_Search Results UI|Search Results UI]]
- [[_COMMUNITY_Auth Guard Tests|Auth Guard Tests]]
- [[_COMMUNITY_TS Root Config|TS Root Config]]
- [[_COMMUNITY_Vercel Config|Vercel Config]]
- [[_COMMUNITY_Lecture Hook Tests|Lecture Hook Tests]]
- [[_COMMUNITY_HTTP Client Tests|HTTP Client Tests]]
- [[_COMMUNITY_Sign-Up Page|Sign-Up Page]]
- [[_COMMUNITY_Owner Migration Script|Owner Migration Script]]
- [[_COMMUNITY_TopNav Tests|TopNav Tests]]
- [[_COMMUNITY_Vite Env Types|Vite Env Types]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]

## God Nodes (most connected - your core abstractions)
1. `get_settings()` - 51 edges
2. `LectureStatus` - 51 edges
3. `Course` - 50 edges
4. `Lecture` - 49 edges
5. `JsonRegistry` - 47 edges
6. `User` - 46 edges
7. `AuthToken` - 43 edges
8. `DiagramAsset` - 43 edges
9. `PostgresRegistry` - 43 edges
10. `TokenKind` - 40 edges

## Surprising Connections (you probably didn't know these)
- `Render Blueprint (echonotes-api)` --implements--> `Stateless Deploy (managed state)`  [INFERRED]
  render.yaml → README.md
- `main()` --calls--> `ensure_bootstrap_admin()`  [INFERRED]
  backend/scripts/migrate_add_owner.py → backend/app/auth/service.py
- `StarletteHTTPException` --uses--> `LectureStatus`  [INFERRED]
  backend/app/main.py → backend/app/models.py
- `RequestValidationError` --uses--> `LectureStatus`  [INFERRED]
  backend/app/main.py → backend/app/models.py
- `BackgroundTasks` --uses--> `Course`  [INFERRED]
  backend/app/web.py → backend/app/models.py

## Import Cycles
- 1-file cycle: `backend/app/transcribe.py -> backend/app/transcribe.py`
- 1-file cycle: `backend/app/merge.py -> backend/app/merge.py`
- 1-file cycle: `backend/app/main.py -> backend/app/main.py`
- 1-file cycle: `backend/app/diagrams.py -> backend/app/diagrams.py`
- 1-file cycle: `backend/app/refine.py -> backend/app/refine.py`

## Hyperedges (group relationships)
- **EchoNotes Multimodal Pipeline Flow** — readme_pipeline, readme_alignment_cosine, readme_raw_audio_never_persisted, readme_one_embedding_model, readme_source_labeling [EXTRACTED 1.00]
- **Layered Requirements (prod base extended by local & test)** — requirements_prod, requirements_local_local, requirements_test_test [EXTRACTED 1.00]
- **Stateless Deploy with Managed State + Pre-Deploy Migrations** — render_blueprint, readme_stateless_deploy, render_predeploy_migrations, render_auth_multitenancy [INFERRED 0.85]

## Communities (82 total, 24 thin omitted)

### Community 0 - "Domain Data Models"
Cohesion: 0.05
Nodes (93): AuthProvider, AuthToken, Course, DiagramAsset, Lecture, LectureStatus, NoteChunk, _now() (+85 more)

### Community 1 - "Spoken-Slide Alignment"
Cohesion: 0.06
Nodes (63): align(), AlignedSegment, Alignment (task T015): match spoken segments to slide sections.  Uses the ONE em, Group spoken segments under the slide section each best corresponds to., SectionAlignment, _unit(), Return the configured OpenAI key, or fail with an actionable message.      Used, require_openai_key() (+55 more)

### Community 2 - "Test Fixtures & Harness"
Cohesion: 0.06
Nodes (36): auth_headers(), client(), _isolate(), outbox(), Test fixtures for the auth + multi-tenancy suite (feature 002).  CRITICAL: the r, Reset settings cache + registry before every test so each starts hermetic and, A fresh TestClient with an empty registry (clean tenant slate per test)., Capture OTP codes + reset links instead of sending email (service emails the (+28 more)

### Community 3 - "Storage Facade"
Cohesion: 0.07
Nodes (47): add_chunks(), assemble_document(), bump_auth_token(), create_auth_token(), create_course(), create_diagram(), create_lecture(), create_user() (+39 more)

### Community 4 - "Course API Endpoints"
Cohesion: 0.07
Nodes (34): CourseIn, create_course(), delete_course(), get_course(), Course endpoints (contracts/api.md; backs the T021 library).  Feature 002 (Art., Cross-lecture search within a course (Strong, T031/FR-10), owner-scoped., Delete a course and cascade-delete all of its lectures and notes (owner only)., _require_owned_course() (+26 more)

### Community 5 - "Postgres Registry Backend"
Cohesion: 0.13
Nodes (9): _course(), _diagram(), _iso(), _lecture(), _pool(), PostgresRegistry, Managed Postgres registry backend (production).  Replaces registry.json for mult, _token() (+1 more)

### Community 6 - "Frontend Dependencies"
Cohesion: 0.06
Nodes (34): dependencies, lucide-react, @radix-ui/react-popover, react, react-dom, react-router-dom, @tanstack/react-query, devDependencies (+26 more)

### Community 7 - "JSON Registry Backend"
Cohesion: 0.13
Nodes (3): JsonRegistry, JSON-file registry backend (local dev).  A tiny JSON index of users/courses/lect, Remove the lecture record + its diagram rows. Returns False if absent or not own

### Community 8 - "Build, CI & Project Docs"
Cohesion: 0.08
Nodes (32): CI Backend Job (pytest), CI Frontend Job (vitest + tsc), Hermetic Test Suite (no secrets, local backends, mocked I/O), OpenSpec Config (spec-driven), No-Flash Theme Bootstrap Script, SPA HTML Entry (index.html), Spoken-to-Slide Alignment via Cosine Similarity, EchoNotes JSON API Contract (+24 more)

### Community 9 - "Auth Service Logic"
Cohesion: 0.13
Nodes (27): ensure_bootstrap_admin(), forgot_password(), google_auth(), _issue_token(), login(), _normalize_email(), _public_user(), Auth business logic (feature 002): signup → OTP → set-password → login, Google s (+19 more)

### Community 10 - "Auth API Endpoints"
Cohesion: 0.23
Nodes (24): forgot_password(), google(), login(), Auth endpoints: /api/auth/* — see the `auth` capability in openspec/specs/.  Thi, reset_password(), set_password(), signup(), verify_otp() (+16 more)

### Community 11 - "Note Document UI"
Cohesion: 0.10
Nodes (15): LectureCard(), BuildsOnLink(), DiagramFigure(), SourceLegend(), SpokenOnly(), Block, isSpokenOnly(), SegmentInline() (+7 more)

### Community 12 - "TS App Config"
Cohesion: 0.08
Nodes (23): compilerOptions, allowImportingTsExtensions, composite, jsx, lib, module, moduleDetection, moduleResolution (+15 more)

### Community 13 - "Auth Crypto & Security"
Cohesion: 0.14
Nodes (20): create_session_token(), decode_session_token(), expires_in(), generate_otp(), generate_token(), hash_password(), hash_secret(), is_expired() (+12 more)

### Community 14 - "API Type Definitions"
Cohesion: 0.10
Nodes (20): ApiError, AuthProvider, BuildsOn, CourseCreated, CourseDetail, CourseSummary, LectureDocument, LectureResponse (+12 more)

### Community 15 - "TS Node Config"
Cohesion: 0.10
Nodes (19): compilerOptions, allowImportingTsExtensions, composite, lib, module, moduleDetection, moduleResolution, noEmit (+11 more)

### Community 16 - "Frontend HTTP Client"
Cohesion: 0.16
Nodes (14): resolveAssetUrl(), ApiRequestError, apiUrl(), authHeaders(), BASE, del(), getJson(), guard() (+6 more)

### Community 17 - "Course UI & Hooks"
Cohesion: 0.11
Nodes (11): CourseCard(), useCourse(), useCourses(), useCreateCourse(), useDeleteCourse(), useCourseSearch(), useDebounce(), CourseDetailPage() (+3 more)

### Community 18 - "Server-Rendered Web UI"
Cohesion: 0.22
Nodes (14): document_to_html(), page(), course_page(), home(), lecture_page(), _owner_id(), Minimal server-rendered UI (tasks T019, T021).  The document is the star (Art. I, The single owner this server-rendered console operates as (feature 002, Art. X). (+6 more)

### Community 19 - "Auth Guard & Landing"
Cohesion: 0.15
Nodes (5): RequireAuth(), useAuth(), LandingPage(), LoginPage(), TopNav()

### Community 20 - "Qdrant Vector Store"
Cohesion: 0.24
Nodes (5): NoteChunk, QdrantClient, _client(), QdrantVectors, Qdrant vector backend (managed/cloud, production).  Implements the same VectorBa

### Community 21 - "Shared UI Components"
Cohesion: 0.18
Nodes (9): ExportMenu(), NotFoundPage(), Button(), buttonClasses(), ButtonSize, ButtonVariant, Props, SIZES (+1 more)

### Community 22 - "Lecture API Endpoints"
Cohesion: 0.24
Nodes (10): create_lecture(), delete_lecture(), export_lecture(), get_lecture(), Lecture endpoints (contracts/api.md): ingest (T010), status/document, export (T0, Delete a lecture along with its notes and preserved diagram images (owner only)., _require_lecture(), _safe_filename() (+2 more)

### Community 23 - "Config & Settings"
Cohesion: 0.18
Nodes (8): active_embedding_model(), Configuration & secrets (task T002).  Single source of truth for API keys, model, The one embedding model in force for this provider (Art. VI)., Settings, BaseSettings, main(), Create the Postgres schema for the EchoNotes registry (idempotent).  Run once ag, Local-disk object backend for preserved diagram images (dev).  Writes under DATA

### Community 24 - "Document Rendering"
Cohesion: 0.33
Nodes (10): _builds_on_html(), document_to_markdown(), _image_ref(), _is_spoken_only(), _md_inline(), Render the merged document (tasks T019, T020).  Renders the (refined) document a, Escape HTML, then convert a tiny markdown subset (no dependency)., Cross-lecture 'builds on' line for a topic (Stretch, T041), shown with its     s (+2 more)

### Community 26 - "Storage Resolver & Health"
Cohesion: 0.22
Nodes (6): active_storage(), get_settings(), Cached settings accessor — import this, don't instantiate Settings directly., Which storage backend each subsystem resolves to (surfaced by /api/health,     s, health(), Liveness + config sanity (reveals whether a key is set, never the key).

### Community 27 - "Transactional Email"
Cohesion: 0.27
Nodes (9): Transactional email (feature 002): OTP codes and password-reset links.  Mirrors, SMTP counts as configured only when host + user + password are ALL set.      A h, Send a plain-text email; on any failure (or when SMTP isn't fully configured), Email the 6-digit signup verification code., Email the password-reset link., send_email(), send_otp_email(), send_reset_email() (+1 more)

### Community 29 - "Google Auth Tests"
Cohesion: 0.31
Nodes (7): _configure(), _FakeJWK, _FakeKey, Direct unit tests for Google ID-token verification (auth/google.py). The JWKS cl, test_verify_rejects_bad_issuer(), test_verify_rejects_missing_email(), test_verify_success_normalizes_email()

### Community 30 - "LLM Refinement Pass"
Cohesion: 0.36
Nodes (8): _client(), _model(), _parse(), Refinement pass (task T016, polish): a second LLM rewrites the merged segments f, Rewrite a topic's merged segments into a clean, de-duplicated narrative., refine_section(), OpenAI, Block

### Community 31 - "Lecture Reading UI"
Cohesion: 0.25
Nodes (6): useDeleteLecture(), useLecture(), DeleteLectureButton(), countSpokenOnly(), LectureReadingPage(), ReadyView()

### Community 32 - "UI Primitives"
Cohesion: 0.22
Nodes (5): cn(), Logo(), Spinner(), StatusBadge(), STYLES

### Community 33 - "Lecture Ingestion"
Cohesion: 0.50
Nodes (7): create_and_launch_lecture(), _ext(), Ingestion (task T010): accept + validate uploads, then launch the pipeline.  Aud, _require_ext(), _save(), Path, UploadFile

### Community 34 - "Lecture Upload UI"
Cohesion: 0.29
Nodes (4): useUploadLecture(), FileDropZone(), AUDIO_EXTS, UploadForm()

### Community 35 - "S3/R2 Object Storage"
Cohesion: 0.36
Nodes (4): _client(), _content_type(), _key(), Object-storage backend for preserved diagram images (Cloudflare R2 / AWS S3).  U

### Community 36 - "Diagram Description (Vision)"
Cohesion: 0.43
Nodes (6): _client(), describe_image(), _model(), Diagram description via a vision model (task T030, FR-9 — Strong).  For each mea, Return a concise description of a diagram image, or None (best-effort)., OpenAI

### Community 37 - "Cross-Lecture Retrieval"
Cohesion: 0.33
Nodes (5): find_links(), Cross-lecture retrieval / search (task T031, FR-10 — Strong).  Embeds the query, Top matching note segments across a course's lectures for a text query., Link each current topic to the most similar EARLIER lecture (Stretch, T040/T041), search()

### Community 38 - "Google Sign-In UI"
Cohesion: 0.33
Nodes (3): googleEnabled, GoogleId, Window

### Community 39 - "Upload API Client"
Cohesion: 0.40
Nodes (3): api, auth, UploadInput

### Community 40 - "Theme System"
Cohesion: 0.50
Nodes (3): getStoredTheme(), resolveTheme(), Theme

### Community 45 - "Processing Tracker UI"
Cohesion: 0.67
Nodes (3): activeIndex(), ProcessingTracker(), STAGES

## Knowledge Gaps
- **139 isolated node(s):** `BackgroundTasks`, `UploadFile`, `PyJWKClient`, `name`, `private` (+134 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **24 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_settings()` connect `Storage Resolver & Health` to `Spoken-Slide Alignment`, `Storage Facade`, `Diagram Description (Vision)`, `Cross-Lecture Retrieval`, `Course API Endpoints`, `S3/R2 Object Storage`, `JSON Registry Backend`, `Auth Service Logic`, `Postgres Registry Backend`, `Auth Crypto & Security`, `Qdrant Vector Store`, `Config & Settings`, `Transactional Email`, `Chroma Vector Store`, `LLM Refinement Pass`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Why does `JsonRegistry` connect `JSON Registry Backend` to `Domain Data Models`, `Storage Facade`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Why does `User` connect `Domain Data Models` to `Auth Service Logic`, `Auth API Endpoints`, `Postgres Registry Backend`, `JSON Registry Backend`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Are the 48 inferred relationships involving `LectureStatus` (e.g. with `BackgroundTasks` and `Lecture`) actually correct?**
  _`LectureStatus` has 48 INFERRED edges - model-reasoned connections that need verification._
- **Are the 40 inferred relationships involving `Course` (e.g. with `CourseIn` and `AuthToken`) actually correct?**
  _`Course` has 40 INFERRED edges - model-reasoned connections that need verification._
- **Are the 41 inferred relationships involving `Lecture` (e.g. with `BackgroundTasks` and `Lecture`) actually correct?**
  _`Lecture` has 41 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `JsonRegistry` (e.g. with `_registry()` and `AuthToken`) actually correct?**
  _`JsonRegistry` has 16 INFERRED edges - model-reasoned connections that need verification._