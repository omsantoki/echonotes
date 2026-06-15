# API Contracts: EchoNotes Core

<!-- Spec Kit artifact: specs/001-echonotes-core/contracts/api.md
Endpoint contracts derived from plan.md. Shapes are indicative; lock exact
schemas during T010+. -->

## Conventions
- Base path: `/api`
- JSON responses unless noted. Multipart for uploads.
- Errors: `{ "error": { "code": string, "message": string } }`

---

### POST /api/courses
Create a course.
**Body:** `{ "name": string }`
**201:** `{ "id": string, "name": string, "created_at": string }`

### GET /api/courses
**200:** `[{ "id", "name", "lecture_count": int }]`

### GET /api/courses/{course_id}
**200:** `{ "id", "name", "lectures": [{ "id", "title", "date", "status" }] }`

### DELETE /api/courses/{course_id}
Delete a course and **cascade-delete** all of its lectures (their notes, vectors,
and preserved diagram images).
**204:** no content.
**404:** `{ "error": { "code": "course_not_found", "message": string } }`

---

### POST /api/lectures
Start processing a lecture. **Multipart:**
- `course_id`: string
- `title`: string
- `audio`: file
- `slides`: file (PDF)

**202:** `{ "lecture_id": string, "status": "processing" }`
*Side effect:* audio processed then deleted (Constitution Art. IV).

### GET /api/lectures/{lecture_id}
Poll status / fetch the merged document.
**200 (processing):** `{ "id", "status": "processing", "progress": string }`
**200 (ready):**
```json
{
  "id": "string",
  "status": "ready",
  "title": "string",
  "document": {
    "topics": [
      {
        "topic": "string",
        "segments": [
          {
            "source_type": "slides|spoken|diagram",
            "text": "string",
            "reason": "string",
            "confidence": 0.0,
            "spoken_only": false,
            "diagram_ref": "string|null",
            "image_ref": "string|null"
          }
        ],
        "builds_on": { "lecture_id": "string", "lecture_title": "string",
                       "topic": "string", "similarity": 0.0 }
      }
    ]
  }
}
```

### GET /api/lectures/{lecture_id}/export?format=md|html
**200:** file download (Markdown or HTML).

### DELETE /api/lectures/{lecture_id}
Delete a lecture along with its notes (vectors) and preserved diagram images.
**204:** no content.
**404:** `{ "error": { "code": "lecture_not_found", "message": string } }`

---

### GET /api/courses/{course_id}/search?q={query}   *(Strong)*
**200:**
```json
{
  "query": "string",
  "results": [
    { "lecture_id": "string", "lecture_title": "string",
      "topic": "string", "text": "string", "source_type": "string" }
  ]
}
```

---

## Contract notes
- `topics[].segments[]` are ordered and render as ONE flowing, woven narrative (slide + spoken interleaved), not standalone cards.
- Every returned segment MUST include `source_type` and `reason` (Art. II, III). `spoken_only=true` marks spoken content absent from the slides and is emphasized inline (Art. III).
- `diagram` segments carry a `diagram_ref` (the asset id) and `image_ref`, the resolvable `/assets/{lecture_id}/{asset_id}.{ext}` path to the preserved image (served from the `/assets` mount). `image_ref` is `null` when no image was preserved; the caption (`text`) is always present. Non-diagram segments omit `image_ref` / leave it `null`.
- A topic MAY include `builds_on` (Stretch, T041): the earlier lecture/topic it most resembles, with the cosine `similarity` as evidence (Art. II). Omitted when no prior lecture clears the threshold.
- Search spans all lectures within the course (Art. V).
