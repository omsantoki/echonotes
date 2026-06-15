# Data Model: EchoNotes Core

<!-- Spec Kit artifact: specs/001-echonotes-core/data-model.md -->

Storage is embeddings-first: the **vector store is the single persistence layer**, with structured metadata attached to each stored chunk. No separate relational DB is required, though entities are described relationally for clarity. **Raw audio is never an entity** (Constitution Art. IV).

## Entities

### Course
| Field | Type | Notes |
|---|---|---|
| id | string (uuid) | PK |
| name | string | e.g. "Thermodynamics — Sem 4" |
| created_at | datetime | |

### Lecture
| Field | Type | Notes |
|---|---|---|
| id | string (uuid) | PK |
| course_id | string | FK → Course |
| title | string | e.g. "L05 — Entropy" |
| date | date | |
| status | enum | `uploaded` \| `processing` \| `ready` \| `failed` |
| created_at | datetime | |

### NoteChunk  *(the core unit — one labeled segment of the flowing notes; stored with its embedding)*
| Field | Type | Notes |
|---|---|---|
| id | string (uuid) | PK |
| lecture_id | string | FK → Lecture |
| course_id | string | denormalized for course-wide search |
| topic | string | section/topic heading |
| order | int | position within the lecture document (segment order in the flowing notes) |
| text | string | the note content |
| source_type | enum | `slides` \| `spoken` \| `diagram` (Constitution Art. III) |
| reason | string | explainability: *why* this was placed/labeled here (Art. II) |
| confidence | float | alignment confidence (0–1) |
| diagram_ref | string? | FK → DiagramAsset when source_type = diagram |
| embedding | float[] | from the single embedding model (Art. VI) |
| links_to | string[]? | (Stretch) ids/refs of earlier chunks this builds on |

### DiagramAsset
| Field | Type | Notes |
|---|---|---|
| id | string (uuid) | PK |
| lecture_id | string | FK → Lecture |
| image_ref | string | stored image location/key |
| description | string? | (Strong) vision-generated description |
| section_topic | string | which topic it belongs to |

## Relationships

```
Course 1───* Lecture 1───* NoteChunk
                   │
                   └───* DiagramAsset 1───* NoteChunk(diagram_ref)
NoteChunk *───* NoteChunk   (links_to, Stretch — cross-lecture)
```

## Metadata stored alongside each vector

`{ chunk_id, lecture_id, course_id, topic, source_type, order, confidence, diagram_ref? }`
— this metadata is what powers source labeling, per-course grouping, search filtering, and continuity. It is mandatory (Art. III, V).

## Cross-lecture links (Stretch)

`NoteChunk.links_to` expresses "builds on" relationships. Because vector-store metadata must be scalar (no lists), these links are realized **per topic on the Lecture registry** (`lecture.links = { topic: { lecture_id, lecture_title, topic, similarity } }`) and surfaced as `topics[].builds_on` in the API/document (T040/T041). Each link is the most similar earlier lecture for that topic — capped (retrieve_top_n) and similarity-thresholded — carrying its `similarity` as evidence (Art. II).

## Lifecycle of audio (explicit)

`audio uploaded → held in temp/in-memory only → transcribed → transcript used in pipeline → audio deleted`. Audio is never written to durable storage. (Art. IV)

## Validation rules

- Every NoteChunk MUST have a non-empty `source_type` and `reason`.
- A `diagram` chunk MUST have a `diagram_ref`.
- All embeddings in a course MUST come from the same model/version.
