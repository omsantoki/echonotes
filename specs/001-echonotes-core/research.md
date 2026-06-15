# Research & Decisions: EchoNotes Core

<!-- Spec Kit artifact: specs/001-echonotes-core/research.md
Captures the [NEEDS CLARIFICATION] resolutions and key technical decisions
with rationale and alternatives considered. -->

## Resolved clarifications (from spec §11)

| Question | Decision | Rationale |
|---|---|---|
| Demo audio source | Self-record one clean lecture (phone near professor) if no clean recording exists | Audio quality is the top demo risk (spec §9) |
| Slide format scope | PDF only for the event | Keeps extraction simple; PPTX/image support is post-event |
| Accounts / multi-user | Lightweight single-user for the demo | Simplicity (Art. IX); auth is not the value |

## Decision log

### D-1 — Alignment via embedding similarity (top-3 near-tie), not timing
**Decision:** Match transcript segments to slide sections by semantic similarity. Attach each segment to its best section **plus up to 2 near-tie runner-ups** (top-3, `align_top_k`), so an explanation that spans slides reaches every relevant section instead of being forced into one. Runner-ups attach only when at least ~85% as similar as the best.
**Alternatives:** strict top-1 (misplaces sentences that span slides → lost context); slide-timing alignment (fragile without reliable timestamps); manual alignment (defeats the point).
**Rationale:** more faithful placement and more context per section without scattering a sentence across unrelated slides; timing cues remain an optional later refinement (Art. I, VII).

### D-2 — Vector store as single persistence layer
**Decision:** Chroma locally during build; swap to a hosted store only if the deploy needs it.
**Alternatives:** Postgres + pgvector (more setup); plain files (no similarity search).
**Rationale:** zero-setup, embeddings-first matches the data model; metadata attaches to vectors.

### D-3 — One embedding model for align + retrieve
**Decision:** A single embedding model/version used everywhere.
**Rationale:** Constitution Art. VI; mixing spaces breaks similarity comparisons.

### D-4 — LLM does composition, not retrieval-of-truth
**Decision:** The LLM composes/merges already-aligned material and frames continuity; it does not invent facts.
**Rationale:** Honest AI (Art. II); grounding stays in the source material.

### D-5 — Discard audio post-processing
**Decision:** Audio lives only in temp/memory and is deleted after transcription.
**Rationale:** Privacy + leanness (Art. IV); also a strong pitch point.

### D-6 — Image filtering before description
**Decision:** Skip tiny, repeated, or template images before any vision description.
**Rationale:** avoids clutter and wasted vision calls (FR-4).

### D-7 — Union merge (one-pass dedupe); optional refine
**Decision:** The merge pass synthesizes the UNION of the slide text and the spoken transcript for each topic into one clean, de-duplicated, reconstructed explanation in a single LLM call (completeness + dedupe + rewrite in the model's own words). Provenance is preserved in per-segment labels and spoken-only content stays flagged/emphasized; the prose itself does not call out slides-vs-speech. A second "refine" pass exists but is OFF by default — redundant once merge unifies and de-duplicates; enable it for an extra cleanup.
**Alternatives:** always running a second pass (extra latency + re-compression risk → detail loss, which users reported); dropping source labels from the output entirely (rejected — violates Art. III).
**Rationale:** one clean union reconstruction matches the goal and avoids a second summarizer dropping detail. Best-effort: merge (and refine, if on) fall back to the raw material if a model/parse fails.

## Open research tasks (do before Day 2)

- Confirm current versions / availability of: Whisper (or chosen STT), PyMuPDF, chosen embedding model, chosen vision+LLM provider, Chroma, and the deploy platform's Python support and free-tier limits.
- Confirm the vision model can describe the diagram types in the demo subject.
- Sanity-check transcription quality on a sample of the demo audio.
