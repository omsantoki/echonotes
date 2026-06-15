# Implementation Plan: EchoNotes Core

<!--
Spec Kit artifact: specs/001-echonotes-core/plan.md
Output of the /speckit.plan step. The technical "HOW". Must pass the
Constitution Check before tasks are generated.
-->

**Feature branch:** `001-echonotes-core`
**Input:** spec.md · **Governs:** constitution.md

---

## Technical Context

A pipeline application: audio + slides PDF in → merged, source-labeled notes out, persisted as embeddings per course. A single embedding model serves alignment and retrieval. Raw audio is discarded after processing.

**Note on stack:** versions and API availability change. Confirm current versions of every library/API below before Day 2 (Constitution does not mandate specific versions, only the architecture).

| Concern | Choice | Rationale |
|---|---|---|
| Language / backend | Python + FastAPI | Audio/PDF/ML libraries are Python-native |
| Transcription | Whisper (open-source) or hosted STT | Accurate; use clean audio for demo |
| PDF text + image extraction | PyMuPDF | Pulls text and embedded images with positions |
| OCR (fallback) | Tesseract or vision model | Only if slides are images |
| Diagram description (Strong) | Vision-capable LLM | Same provider as merge — no new infra |
| Embeddings | One model, reused everywhere | Constitution Art. VI |
| Vector store | Chroma (local, zero-setup) for build; hosted (Pinecone/Qdrant) if needed for deploy | Simplicity (Art. IX) |
| Merge / generation | LLM API | Produces source-labeled, topic-organized notes |
| Frontend | Minimal React (or server-rendered) | Document is the star (Art. IX) |
| Output | Rendered Markdown/HTML + export | LLM emits structured Markdown |
| Deploy | Render / Railway (backend); Vercel if split | Fastest path to public URL |

## Constitution Check

| Article | Compliance |
|---|---|
| I — Problem fidelity | Plan sequences core merge first; everything else gated behind it |
| II — Honest AI | Embedding + heuristic + LLM, all explainable; reasons surfaced per segment (inline / hover) |
| III — Source labeling | Every output block carries provenance metadata end-to-end |
| IV — Store notes not audio | Audio held only in-memory/temp during processing, then deleted |
| V — Continuity by design | Per-course storage schema from the first commit |
| VI — One embedding model | Single embedding model constant used for align + retrieve |
| VII — Tiered scope | Tasks grouped Core → Strong → Stretch |
| VIII — Demoable | Demo lecture obtained Day 1; pipeline validated on it |
| IX — Ship public & simple | Public deploy task included; minimal UI |

✅ No violations. Proceed to `/speckit.tasks`.

## Architecture Overview

```
audio ─▶ Transcribe ─▶ timestamped segments ┐
                                              ├▶ Align (embeddings) ─▶ Merge (LLM) ─▶ Document
slides PDF ─▶ Extract text + images ─▶ Filter ┘            ▲                  │
                                  Describe diagrams ───────┘                  ├▶ Render + Export
                                                                              └▶ Embed + Store (per course)
                                            Retrieve prior-lecture context ◀──┘  (vector store)
```

## Module Breakdown (library-first, per Constitution intent)

1. **ingest** — accept + validate audio and PDF; temp storage; guarantees audio deletion after pipeline.
2. **transcribe** — audio → timestamped text segments.
3. **slides** — PDF → ordered sections with text + extracted images; image filter.
4. **diagrams** (Strong) — vision description of meaningful images.
5. **embed** — single wrapper around the one embedding model (used by align + store + search).
6. **align** — match transcript segments to slide sections / diagrams via similarity; emit alignment with confidence + reason.
7. **merge** — LLM synthesizes the UNION of slide text + spoken transcript per topic into one clean, de-duplicated, reconstructed explanation (ordered, source-labeled segments; spoken-only flagged). An optional refine pass (off by default) can run a second cleanup; provenance labels are preserved either way.
8. **store** — persist note chunks (text + embedding + metadata: course, lecture, date, topic, source-type) to vector store; per-course grouping.
9. **retrieve** (Strong/Stretch) — query store for related prior notes; cross-lecture linking.
10. **api** — FastAPI endpoints orchestrating the pipeline.
11. **web** — minimal UI: upload, progress, document view, course library, search, export.

## Data Model (summary; full detail in data-model.md)

- **Course** (id, name)
- **Lecture** (id, course_id, title, date, status)
- **NoteChunk** (id, lecture_id, topic, text, source_type[slides|spoken|diagram], reason, embedding, order, diagram_ref?)
- **DiagramAsset** (id, lecture_id, image_ref, description?)
- No Audio entity persisted (Art. IV).

## API Contracts (summary; full detail in contracts/)

- `POST /courses` · `GET /courses` · `GET /courses/{id}`
- `POST /lectures` (multipart: audio + pdf + course_id, title) → starts pipeline, returns lecture_id + job status
- `GET /lectures/{id}` → status + merged document (chunks with labels + reasons)
- `GET /lectures/{id}/export` → downloadable Markdown/HTML
- `GET /courses/{id}/search?q=` (Strong) → matching chunks across lectures

## Phasing

- **Phase A (Core):** ingest → transcribe → slides(text+images, filter) → embed → align → merge → store → render → export → deploy. Validated on the demo lecture.
- **Phase B (Strong):** diagram descriptions; cross-lecture search.
- **Phase C (Stretch):** cross-lecture linking surfaced in the document.

## Risks & Mitigations (from spec §9)

- Alignment quality → spend most effort here; start with simple top-1 similarity, add timing cues only if time allows.
- Audio noise → curated clean demo recording.
- Scope creep → tiers enforced by Constitution Art. VII; analyze step before implement.

## Quickstart

See `quickstart.md` for environment setup, running the pipeline on the demo lecture, and deploying.
