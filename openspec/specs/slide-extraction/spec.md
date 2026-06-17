# slide-extraction

## Purpose

Turn a slides PDF into ordered text sections (one per page) and the embedded images those pages carry, using PyMuPDF (`fitz`). Decorative and template images (logos, repeated banners, tiny icons/bullets) are filtered out before any image is described or placed, so only meaningful diagrams reach the merged document (Constitution Art. on filtering decorative images).

## Requirements

### Requirement: Extract ordered text sections per page

The system SHALL open the slides PDF and produce one `SlideSection` per page, in page order, where each section carries a 0-based `index`, the page's plain-text content (stripped of leading/trailing whitespace), and a `title`.

#### Scenario: One section per page in order

- **WHEN** `extract_slides(pdf_path)` is called on a PDF with N pages
- **THEN** it returns a list of exactly N `SlideSection` objects whose `index` values run 0..N-1 in page order
- **AND** each section's `text` is the page's `get_text("text")` output with surrounding whitespace stripped

### Requirement: Derive section title from first non-empty line

The system SHALL set each section's `title` to the first non-empty line of the page text, truncated to 120 characters, and SHALL fall back to `"Slide {index+1}"` when the page has no non-empty text line.

#### Scenario: Title taken from first text line

- **WHEN** a page's text begins with a non-empty line
- **THEN** that line (whitespace-trimmed, truncated to 120 characters) becomes the section `title`

#### Scenario: Empty page falls back to numbered title

- **WHEN** a page has no non-empty line of text
- **THEN** the section `title` is `"Slide {index+1}"` (e.g. `"Slide 1"` for the first page)

### Requirement: Extract embedded images tagged by section

The system SHALL extract each embedded image from every page and emit a `SlideImage` carrying the originating page's `section_index`, the raw image `data` bytes, the image `ext`, its `width`/`height` in pixels, and a SHA-1 hex digest (`sha1`) of the image bytes.

#### Scenario: Image carries its source page index

- **WHEN** a page at index `i` contains an embedded image
- **THEN** a `SlideImage` is produced with `section_index == i`, the decoded `data`, `ext`, `width`, `height`, and `sha1 = sha1hex(data)`

#### Scenario: Undecodable or empty images are skipped

- **WHEN** `doc.extract_image(xref)` raises an exception, or returns no `image` bytes
- **THEN** that image is skipped and extraction continues with the remaining images (no error is raised)

### Requirement: Filter out undersized images

The system SHALL drop any image whose width or height is below 100 px, and any image whose pixel area (`width * height`) is below 10,000 px², treating these as icons/bullets rather than diagrams.

#### Scenario: Small image removed

- **WHEN** `filter_images` receives an image with width or height under 100 px (or area under 100x100 px²)
- **THEN** that image is excluded from the returned list

#### Scenario: Large enough image kept

- **WHEN** an image has width and height of at least 100 px and area at least 10,000 px², is not repeated, and is not a duplicate already kept
- **THEN** that image is included in the returned list

### Requirement: Filter out repeated template images

The system SHALL drop images that recur across many slides (logos/banners), where the repeat threshold is `max(2, int(0.3 * max(num_pages, 1)))` occurrences of the same SHA-1 digest, and SHALL also drop exact-duplicate images (same SHA-1) beyond the first kept copy.

#### Scenario: Logo on a third of the slides removed

- **WHEN** an identical image (by SHA-1) appears on at least `max(2, 0.3 * num_pages)` slides
- **THEN** every copy of that image is excluded from the returned list

#### Scenario: Duplicate copy collapsed to one

- **WHEN** an image's SHA-1 has already been kept once and the same SHA-1 appears again (below the repeat threshold)
- **THEN** only the first occurrence is kept and later copies are excluded

### Requirement: Empty image set yields empty result

The system SHALL return an empty list from `filter_images` when given no images, without computing thresholds.

#### Scenario: No images to filter

- **WHEN** `filter_images([], num_pages)` is called with an empty image list
- **THEN** it returns an empty list
