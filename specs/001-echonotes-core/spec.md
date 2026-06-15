# Feature Specification: EchoNotes Core

<!--
Spec Kit artifact: specs/001-echonotes-core/spec.md
Output of the /speckit.specify step. Focuses on WHAT and WHY — no tech stack,
no implementation detail (those live in plan.md). Written to satisfy the
constitution in .specify/memory/constitution.md.
-->

**Feature branch:** `001-echonotes-core`
**Status:** Draft → Ready for `/speckit.plan`
**Owner:** Om Santoki (202301019)

---

## 1. Summary

EchoNotes ingests a single lecture's **audio recording** and its **slides/notes PDF**, and produces one **merged, source-labeled, topic-organized study document** in which the professor's spoken explanations are woven together with the written slide content. Diagrams from the slides are preserved and explained. Each lecture's resulting notes are stored per course so that future lectures can be built on them.

## 2. Problem Statement

In a lecture, two information streams run in parallel: what the professor **writes** (slides/PDF — structured but incomplete) and what the professor **says** (verbal explanation, emphasis, exam hints — rich but unrecorded). Students reliably lose the spoken stream: they zone out, can't write fast enough, or miss the moment. Slides don't contain it, their notes don't contain it, and a raw transcript is an unusable wall of text. The spoken content is frequently what appears on exams.

No existing tool merges the two streams. Messaging apps, slide repositories, and transcription tools each handle only one part; none align and merge.

## 3. Goals

- Capture the spoken stream and merge it with the written stream into one document.
- Label the provenance of every piece (slides / spoken / diagram); make spoken-only content prominent.
- Preserve and (Strong tier) describe diagrams.
- Persist notes per course; (Strong) search across them; (Stretch) link concepts across lectures.
- Deploy to a public URL and demonstrate on real lectures.

## 4. Non-Goals

- Not a live/real-time transcription tool.
- Not a generic Q&A chatbot.
- Not a deep diagram parser (won't read circuit values, solve the diagram, etc.).
- Not a multi-subject, any-format, any-audio-quality system within the event.
- Does not retain raw audio after processing.

## 5. User Personas

- **Aarav, the distracted student (primary):** attends lectures but loses focus; wants notes that include what was said, not just the slides.
- **Diya, the absentee (secondary):** missed a lecture; wants to recover both streams after the fact.
- **Course rep / department (tertiary, adoption):** wants a living, shared, per-course note base the institution could own.

## 6. User Stories & Acceptance Criteria

### US-1 (Core) — Merge one lecture
*As a student, I upload a lecture's audio and its slides PDF, and I receive one merged document organized by topic.*

**Acceptance:**
- GIVEN a valid audio file and a slides PDF, WHEN I submit them, THEN the system produces a document organized into topic sections.
- AND each section contains the relevant slide content and the professor's spoken explanation for that topic.
- AND processing completes and shows progress states (not a frozen screen).

### US-2 (Core) — See where everything came from
*As a student, I can tell at a glance which content came from the slides versus what was said aloud.*

**Acceptance:**
- GIVEN a merged document, WHEN I read a topic, THEN it flows as one woven narrative and every passage is labeled inline as **from slides**, **said in lecture**, or **from a diagram**.
- AND spoken-only content (absent from slides) is highlighted inline.
- AND each passage can show *why* it was placed/labeled there (explainability, e.g. on hover).

### US-3 (Core) — Keep the diagrams
*As a student, I see the slide's diagrams in my notes, next to the explanation of them.*

**Acceptance:**
- GIVEN slides containing diagrams, WHEN the document is produced, THEN diagrams appear in the correct section.
- AND decorative images (logos, repeated banners) are excluded.

### US-4 (Core) — A growing per-course library
*As a student, my processed lectures are saved and listed together under their course.*

**Acceptance:**
- GIVEN I have processed multiple lectures for a course, WHEN I open the course, THEN I see all its lectures listed and can reopen any merged document.
- AND raw audio is NOT retained — only the notes.

### US-5 (Strong) — Describe diagrams
*As a student, each diagram has a short text description so I understand it and can search it.*

**Acceptance:** GIVEN a meaningful diagram, THEN a concise description is generated, displayed with it, and indexed for search.

### US-6 (Strong) — Search across lectures
*As a student, I search a concept and see every lecture that covered it.*

**Acceptance:** GIVEN stored lectures, WHEN I search a term, THEN matching sections across all lectures are returned with their source labels.

### US-7 (Stretch) — Cross-lecture links
*As a student, today's notes point back to the earlier lecture they build on.*

**Acceptance:** GIVEN a concept introduced earlier, WHEN a later lecture references it, THEN the note links to the earlier source. (Demo needs this working on one curated example.)

## 7. Functional Requirements

- **FR-1:** Accept an audio file (single lecture) and a slides PDF as input.
- **FR-2:** Transcribe audio to timestamped text.
- **FR-3:** Extract text AND images from the slides PDF, preserving section structure.
- **FR-4:** Filter out non-meaningful images (small/repeated/decorative).
- **FR-5:** Align spoken segments to the slide sections (and diagrams) they correspond to.
- **FR-6:** Generate a merged, topic-organized document that reads as one flowing, woven narrative (slide + spoken interleaved), with inline per-segment source labels.
- **FR-7:** Emphasize spoken-only content inline; expose per-segment explainability (inline / on hover).
- **FR-8:** Persist final notes (text + embeddings + metadata) per course; never persist raw audio.
- **FR-9 (Strong):** Generate and store a description for each meaningful diagram.
- **FR-10 (Strong):** Provide search across all stored notes for a course.
- **FR-11 (Stretch):** Retrieve relevant prior-lecture notes as context and surface cross-lecture links.
- **FR-12:** Render the document on screen and allow export/download.
- **FR-13:** Deploy to a public URL.

## 8. Non-Functional Requirements

- **Explainability:** every merge/label/link is accompanied by a reason (Constitution Art. II).
- **Privacy:** raw audio discarded post-processing (Art. IV).
- **Reliability:** must run end-to-end on the team's chosen demo lecture without manual patching mid-demo.
- **Simplicity:** minimal UI; the document is the focus (Art. IX).
- **Performance:** retrieved cross-lecture context limited to the few most relevant chunks (Art. VI rationale).

## 9. Key Edge Cases & Risks

- Noisy classroom audio degrades transcription → demo on the cleanest available recording.
- Vague alignment producing a jumbled merge → alignment is the highest-effort area (see plan).
- Decorative images cluttering output → image filter (FR-4).
- Weak notes poisoning future lectures → core merge quality gates continuity.
- Over-large cross-lecture context → cap retrieved chunks.

## 10. Success Metrics (for the demo & judging)

- Merged document for one real lecture that a student confirms is more useful than slides alone.
- A visible spoken-only item captured that the slides omitted (the "wow").
- Continuity shown: lecture 3 references lectures 1–2.
- Public URL live; 1–2 classmates validate they'd use it.

## 11. [NEEDS CLARIFICATION]

- Audio source for the demo lecture: self-recorded vs. provided? (decide Day 1)
- Are slides always PDF, or also PPTX/images for the demo? (scope to PDF unless decided otherwise)
- Single-user demo or multi-user accounts? (default: lightweight single-user for the event)
