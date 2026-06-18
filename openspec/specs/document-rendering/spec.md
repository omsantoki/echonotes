# document-rendering

## Purpose

Render an assembled merged study document (topics with source-labeled segments,
diagrams, and cross-lecture "builds on" links) into HTML and Markdown. The HTML
powers the server-rendered console and the JSON API export; the Markdown is a
flowing export. Per the constitution, the unified prose reads as one narrative,
but spoken-only content (said in the lecture, absent from the slides) stays
visually emphasized.

## Requirements

### Requirement: Render the document to HTML

The system SHALL render an assembled document to HTML by emitting one `<section class="topic">`
per topic (with an `<h2>` topic heading), preceded by a legend. The system SHALL support a
`standalone` flag: when true it MUST wrap the body in a full HTML page (doctype, head with
embedded CSS, title suffixed with " · EchoNotes"); when false it MUST return only the body
fragment.

#### Scenario: Document with topics rendered as a fragment

- **WHEN** `document_to_html(title, doc)` is called with a document containing at least one topic and `standalone` defaulting to false
- **THEN** the output begins with the legend HTML and contains one `<section class="topic">` with an `<h2>` heading per topic
- **AND** the output is a body fragment, not wrapped in `<!doctype html>`

#### Scenario: Empty document

- **WHEN** `document_to_html` is called with a document that has no topics
- **THEN** the body is `<p class="muted">No content.</p>`

#### Scenario: Standalone page requested

- **WHEN** `document_to_html(title, doc, standalone=True)` is called
- **THEN** the output is a complete HTML page including `<!doctype html>`, an embedded `<style>` block, and a `<title>` ending in " · EchoNotes"

### Requirement: Render the document to Markdown

The system SHALL render an assembled document to flowing Markdown beginning with an `# {title}`
heading and a Legend line, then one `## {topic}` heading per topic, with segment text emitted as
paragraphs, `- ` bullets, or diagram figures.

#### Scenario: Markdown export of a topic

- **WHEN** `document_to_markdown(title, doc)` is called with a document containing topics
- **THEN** the output's first line is `# {title}` followed by a `_Legend: ..._` line
- **AND** each topic produces a `## {topic}` heading followed by its segment text

### Requirement: Keep spoken-only content visually emphasized

The system SHALL detect spoken-only segments (where `spoken_only` is truthy, or `source_type`
is `"spoken"` and the segment `reason` contains the marker `★ Spoken-only`) and emphasize them
distinctly from unified prose. In HTML the segment MUST be wrapped in `<mark class="spoken-only">`
with a trailing `★` star and a `title` tooltip carrying its reason. In Markdown the segment text
MUST be wrapped as `**🎙 ... ★**`. Non-spoken-only segments MUST render as plain, unlabeled prose.

#### Scenario: Spoken-only segment in HTML

- **WHEN** a topic segment is spoken-only and the document is rendered to HTML
- **THEN** that segment is wrapped in `<mark class="spoken-only" title="...">` containing the text and a `<span class="star"> ★</span>`
- **AND** the `title` attribute carries the segment's reason (or a default label) for an on-hover "why"

#### Scenario: Spoken-only segment in Markdown

- **WHEN** a spoken-only segment is rendered to Markdown
- **THEN** its text is emitted as `**🎙 {text} ★**`

#### Scenario: Ordinary segment is unlabeled

- **WHEN** a segment is not spoken-only
- **THEN** it renders as plain prose with no `mark`, star, or source label in HTML and Markdown

### Requirement: Render diagrams as figures

The system SHALL render diagram segments (`source_type == "diagram"`) as figures, resolving the
image via `store.get_diagram` on the segment's `diagram_ref`. In HTML it MUST emit a `<figure>`
with the image (when an `image_ref` is resolved) and a `<figcaption>` always showing the
description/caption. In Markdown it MUST emit `![diagram](img)` when an image is resolved and the
caption as `*{text}*`.

#### Scenario: Diagram with a resolvable image in HTML

- **WHEN** a diagram segment whose `diagram_ref` resolves to an `image_ref` is rendered to HTML
- **THEN** a `<figure>` is emitted containing an `<img class="diagram">` and a `<figcaption>` with the caption

#### Scenario: Diagram without an image still shows its caption

- **WHEN** a diagram segment cannot resolve an image
- **THEN** the HTML `<figure>` omits the `<img>` but still emits the `<figcaption>` description

### Requirement: Render cross-lecture builds-on links

The system SHALL render a topic's `builds_on` link when present, in both HTML and Markdown. The
link MUST show the referenced lecture title and, when present, the related topic and a similarity
percentage. In HTML the lecture title MUST be an anchor to `/lectures/{lecture_id}`.

#### Scenario: Topic with a builds-on link in HTML

- **WHEN** a topic carries a `builds_on` link with a `lecture_id`, `lecture_title`, and numeric `similarity`
- **THEN** the HTML emits a `<p class="builds-on">` with `↳ Builds on <a href="/lectures/{lecture_id}">{lecture_title}</a>`
- **AND** the similarity is shown formatted as a percentage

#### Scenario: Topic with no builds-on link

- **WHEN** a topic has no `builds_on` link
- **THEN** no builds-on line is emitted for that topic

### Requirement: Export a ready lecture as a downloadable file

The system SHALL expose a server-rendered lecture page and a JSON API export endpoint that produce
the rendered document for download. The export endpoint MUST render `format=html` as standalone HTML
(`text/html`) and `format=md` as Markdown (`text/markdown`), return any other format as a 400
`bad_format` error, and reject a lecture that is not `ready` with a 409 `not_ready` error. The
response MUST set a `Content-Disposition: attachment` header with a filename derived from the
lecture title.

#### Scenario: Markdown export of a ready lecture

- **WHEN** `GET /api/lectures/{id}/export?format=md` is called for a ready lecture by its owner
- **THEN** the response is the Markdown document with media type `text/markdown`
- **AND** a `Content-Disposition: attachment; filename="...md"` header is set

#### Scenario: HTML export of a ready lecture

- **WHEN** `GET /api/lectures/{id}/export?format=html` is called for a ready lecture
- **THEN** the response is a standalone HTML page with media type `text/html`

#### Scenario: Unsupported format rejected

- **WHEN** the export endpoint is called with a format other than `md` or `html`
- **THEN** the response is HTTP 400 with code `bad_format`

#### Scenario: Lecture not yet ready

- **WHEN** the export endpoint is called for a lecture whose status is not `ready`
- **THEN** the response is HTTP 409 with code `not_ready`

### Requirement: Render the lecture page reflecting processing state

The system SHALL render the server-rendered lecture page according to status: for a `ready` lecture
it MUST assemble the document and render it as an HTML fragment with Markdown and HTML export
buttons; for a non-ready lecture it MUST show the status and progress text, auto-refresh every 3
seconds while `processing`, and show a failure notice when `failed`.

#### Scenario: Ready lecture page shows the document and export links

- **WHEN** the lecture page is requested for a `ready` lecture
- **THEN** the page renders the merged document HTML and includes Markdown and HTML export links to `/api/lectures/{id}/export`

#### Scenario: Processing lecture page auto-refreshes

- **WHEN** the lecture page is requested for a lecture whose status is `processing`
- **THEN** the page includes a `<meta http-equiv="refresh" content="3">` tag and shows the progress text

#### Scenario: Failed lecture page shows a failure notice

- **WHEN** the lecture page is requested for a lecture whose status is `failed`
- **THEN** the page shows a `Processing failed.` notice and does not auto-refresh

## Known deviations

- The renderer supports only a tiny inline Markdown subset by regex in `_md_inline` (`**bold**`,
  `*italic*`, `` `code` ``) after HTML-escaping; it is not a real Markdown parser and other
  constructs are passed through escaped.
- Source labels are not shown as per-segment tags in the rendered document: by design only
  spoken-only content is marked (with a highlight/star and a hover tooltip), while slide and spoken
  content render as one unlabeled unified prose. Full per-block provenance lives in the stored data
  and JSON API, not in the rendered HTML/Markdown. The `_SRC_TAG` source-label map (📄/🎙/📊) is used
  only on cross-lecture search result badges in `web.py`, not in the rendered study document.
- The export endpoint (`/api/lectures/{id}/export`) and its `_safe_filename` helper live in
  `app/api/lectures.py`, not in `render.py`; `render.py` provides only the `document_to_html` /
  `document_to_markdown` rendering functions that the endpoint calls.
- The Markdown legend wording (`🎙 = said in lecture · ★ = spoken-only`) and the HTML legend
  wording differ slightly in phrasing.
- The server-rendered console is single-tenant: all `/web` and page routes operate as the bootstrap
  admin (`_owner_id`) rather than a per-request user session; multi-tenant access is via the React
  SPA + JSON API.
