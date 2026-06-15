# Tasks: EchoNotes Core

<!--
Spec Kit artifact: specs/001-echonotes-core/tasks.md
Output of the /speckit.tasks step. Tasks are grouped by user story / phase,
ordered by dependency, with [P] marking tasks that can run in parallel.
Each task names the module/file it touches. Tiers follow Constitution Art. VII.
-->

**Feature:** `001-echonotes-core` · **Governs:** constitution.md, plan.md, spec.md

Legend: `[P]` = parallelizable · `[Core]/[Strong]/[Stretch]` = tier · IDs are stable references.

---

## Phase 0 — Setup & Foundations

- **T001** Initialize repo, Python env, FastAPI skeleton, project structure matching plan modules. (`/`)
- **T002** [P] Add config/secrets handling for model/API keys; `.env` template. (`config`)
- **T003** [P] Define the data model types/schemas (Course, Lecture, NoteChunk, DiagramAsset) per data-model.md. (`models`)
- **T004** Stand up the vector store wrapper (Chroma) with create/query/list + metadata. (`store`)
- **T005** [P] **Day-1 critical:** obtain/record the demo lecture (audio + slides PDF) and commit it to a `samples/` folder. (`samples`) — *blocks all validation*
- **T006** [P] Single embedding-model wrapper used everywhere (Art. VI). (`embed`)

## Phase 1 — [Core] US-1 Merge one lecture (the heart)

> Goal: audio + slides → merged, source-labeled, topic-organized document. Do NOT start later phases until this works on the demo lecture (Art. I).

- **T010** [Core] Ingest endpoint: accept audio + PDF + course/title; temp-store; guarantee audio deletion after pipeline (Art. IV). (`ingest`, `api`)
- **T011** [Core] Transcription module: audio → timestamped segments. (`transcribe`) — depends on T010
- **T012** [Core] [P] Slide extraction: PDF → ordered sections with text. (`slides`) — depends on T010
- **T013** [Core] [P] Slide image extraction: pull embedded images with positions/section. (`slides`) — depends on T010
- **T014** [Core] Image filter: drop tiny/repeated/template images (FR-4). (`slides`) — depends on T013
- **T015** [Core] Alignment: embed transcript segments + slide sections; match each segment to its best + near-tie sections (top-k, D-1); emit confidence + reason (Art. II). (`align`, `embed`) — depends on T011, T012, T006
- **T016** [Core] Merge composition (LLM): synthesize the UNION of slide text + spoken transcript per topic into one clean, de-duplicated, reconstructed explanation as ordered segments; each segment keeps its `slides`/`spoken`/`diagram` label + reason in the data; spoken-only stays emphasized inline (US-2, Art. III). An optional refine pass (off by default) can re-clean. (`merge`, `refine`) — depends on T015
- **T017** [Core] Place preserved diagrams into the correct section of the merged doc (US-3). (`merge`, `slides`) — depends on T014, T016
- **T018** [Core] Persist NoteChunks (text + embedding + metadata) per course/lecture (US-4, Art. V). (`store`) — depends on T016, T004
- **T019** [Core] Document render: on-screen flowing document with inline source cues + hover/disclosure "why" reasons. (`web`) — depends on T016
- **T020** [Core] Export endpoint: downloadable Markdown/HTML. (`api`, `web`) — depends on T016
- **T021** [Core] Course library view: list lectures under a course; reopen any document (US-4). (`web`, `api`) — depends on T018
- **T022** [Core] **Validation gate:** run full pipeline on the demo lecture (T005); confirm output reads like real study notes and a spoken-only item is captured. (`samples`) — depends on T016–T021

## Phase 2 — [Strong]

- **T030** [Strong] Diagram description via vision model for meaningful diagrams; store with DiagramAsset; index for search (US-5, FR-9). (`diagrams`, `store`) — depends on T014, T018
- **T031** [Strong] [P] Cross-lecture search endpoint + UI: query store, return matching chunks across lectures with labels (US-6, FR-10). (`retrieve`, `api`, `web`) — depends on T018

## Phase 3 — [Stretch]

- **T040** [Stretch] Retrieve relevant prior-lecture context during merge; cap to top-N chunks (Art. VI rationale). (`retrieve`, `merge`) — depends on T018
- **T041** [Stretch] Surface cross-lecture links in the document ("builds on L#"); ensure one curated demo example works (US-7, FR-11). (`merge`, `web`) — depends on T040

## Phase 4 — Ship & Demo

- **T050** Deploy to a public URL (backend + minimal frontend) (FR-13, Art. IX). (`/`) — depends on T022
- **T051** [P] Seed the deployed app with 2–3 real lectures to show continuity in the demo (Art. VIII). (`samples`) — depends on T050, T018
- **T052** [P] Prepare the demo script: inputs → merged doc → spotlight a spoken-only capture → show continuity → tell the personal story. (`docs`)
- **T053** [P] Write `blog.md` (the build story) per the submission requirement. (`docs`)

---

## Dependency Summary

```
Setup (T001–T006)
  └─▶ Core merge (T010 → T011/T012/T013 → T014 → T015 → T016 → T017/T018/T019/T020/T021)
        └─▶ Validation gate T022  ← MUST pass before Strong/Stretch
              ├─▶ Strong (T030, T031)
              ├─▶ Stretch (T040 → T041)
              └─▶ Ship & Demo (T050 → T051/T052/T053)
```

## Constitution Check (tasks level)

- Core phase fully precedes Strong/Stretch (Art. I, VII) ✅
- Audio deletion task explicit (T010, Art. IV) ✅
- Source labels + reasons in T016 (Art. II, III) ✅
- Per-course persistence from T018 (Art. V) ✅
- Single embedding wrapper T006 reused by T015/T018/T031 (Art. VI) ✅
- Validation-on-real-data gate T022 (Art. VIII) ✅
- Public deploy T050 (Art. IX) ✅

## Suggested mapping to the 7 days
- **Day 1:** T001–T006 (esp. T005 demo lecture)
- **Days 2–3:** T010–T021 (get end-to-end, ugly is fine)
- **Day 4 (Mid-Eval):** T022 validation gate; gather feedback
- **Days 5–6:** T030–T031 (Strong), T040–T041 only if core solid, T050 deploy
- **Day 7:** T051–T053 seed, demo, blog.md
