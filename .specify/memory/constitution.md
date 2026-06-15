# EchoNotes Constitution

<!--
Spec Kit artifact: .specify/memory/constitution.md
This is the foundational, non-negotiable rules file. Every spec, plan, and
task generated for this project MUST adhere to it. When the /speckit.plan and
/speckit.tasks steps run, they reference this document as the source of truth.
-->

**Project:** EchoNotes — merged lecture notes that capture what the professor *said*, not just what was on the slides.
**Owner:** Om Santoki (ID 202301019)
**Context:** 7-Day AI Buildathon · Theme: Academic Life
**Version:** 1.0.0 · **Ratified:** Day 0

---

## Preamble

EchoNotes exists to solve one problem: the spoken stream of a lecture — explanations, emphasis, worked examples, "this will be on the exam" — is lost, while only the written stream (slides/PDF) survives. EchoNotes fuses the two into a single, source-labeled, topic-organized study document, and builds each lecture on the distilled notes of the ones before it.

Every decision in this project is judged against this preamble. If a feature does not help capture, merge, or preserve the spoken-and-written streams, it is out of scope.

---

## Article I — Problem Fidelity Over Feature Count

The product must always do the core job well before doing anything else. The core job is: **take a lecture's audio + slides, and produce merged, source-labeled notes.** No secondary feature (search, cross-lecture linking, fancy UI) may be built until the core merge produces notes a real student would study from.

- A working core on one real lecture outranks a half-built system that handles "any" lecture.
- When time is short, cut scope from the edges (Article VII tiers), never from the core.

## Article II — Honest AI, No Theater

The "AI" must do real work and be explainable. We do not fake intelligence.

- Every merge decision and every cross-lecture link must be **explainable** — the UI shows *why* a spoken segment was attached to a section, and *why* content is labeled as it is.
- We do not claim a trained/validated model we did not build. Embedding similarity + sensible heuristics + an LLM for generation is legitimate and is described honestly.
- No "chatbot wrapper" framing. The value is in alignment and merging, not in a chat box.

## Article III — Source Labeling Is Sacred

Every piece of content in the output MUST carry its provenance: **from slides**, **said in lecture**, or **from a diagram**. This labeling is the product's core differentiator and may never be dropped, blurred, or made optional. Spoken-only content (not present in slides) must be made visually prominent.

## Article IV — Privacy: Store Notes, Not Audio

Raw audio is processed once and then discarded. Only the distilled notes (and their embeddings + metadata) persist. No lecture recording is retained in storage. This keeps the system lean, respects the privacy of professors and students, and is a deliberate, stated design choice.

## Article V — Continuity By Design

The data model must, from day one, support notes accumulating per course over time, so each new lecture can be built on the foundation of earlier ones. Even if cross-lecture *linking* is a stretch feature, persistence and per-course grouping are built in from the start so no rebuild is ever required.

## Article VI — One Embedding Model, Reused

A single embedding model serves both jobs: within-lecture alignment (spoken↔slide) and cross-lecture retrieval. Consistency is mandatory — mixing embedding spaces is forbidden. This keeps the system simple and the technical story clean.

## Article VII — Tiered Scope (Build Bottom-Up)

Features are tiered. Build strictly bottom-up; never start a higher tier until the one below genuinely works.

- **Core (must ship):** per-lecture merge (audio + slide text, aligned & source-labeled); diagrams preserved in output; notes persisted and shown as a growing per-course library.
- **Strong (high value):** diagram descriptions via a vision model; search across all stored lectures.
- **Stretch (only if core is solid):** automatic cross-lecture concept linking.
- **Out of scope:** deep diagram content parsing (reading circuit values, etc.); multi-subject / any-format / any-audio robustness; real-time/live transcription.

## Article VIII — Demoable On Real Data

Everything built must be demonstrable on a real lecture. The team obtains/records one clean lecture (audio + its slides) on Day 1. The demo runs 2–3 lectures in sequence to show continuity. A feature that cannot be shown working on real data does not count as done.

## Article IX — Ship Public, Ship Simple

The product must deploy to a public URL within the event. Prefer the simplest tool that gets there (Article governs: simplicity beats cleverness). The output document — clean, readable, source-labeled — is the star; the UI stays minimal and serves the document.

---

## Governance

- This constitution supersedes feature requests, sprint enthusiasm, and last-minute "wouldn't it be cool if" ideas.
- Any change to scope must be checked against Articles I and VII before adoption.
- Amendments require updating the version (semantic: MAJOR for principle changes, MINOR for additions, PATCH for clarifications) and noting the date.
- The `/speckit.plan` and `/speckit.tasks` outputs MUST include a "Constitution Check" confirming compliance with these articles.

**Amendment log**
- v1.0.0 (Day 0): Initial ratification.
