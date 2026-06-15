# EchoNotes — Frontend

A standalone React + Vite + TypeScript + Tailwind v4 SPA that consumes the
EchoNotes FastAPI backend (in `../backend`). Backend and frontend are intentionally
separate folders; the SPA talks to the JSON API only.

## Stack
- **Vite 8** + **React 19** + **TypeScript 6**
- **Tailwind CSS v4** (CSS-first config via `@tailwindcss/vite`; tokens live in `src/index.css`)
- **TanStack Query** (data fetching, polling, cache) + **React Router 7**
- **lucide-react** icons, **@radix-ui/react-popover** for the "why" reveal

## Run it locally
The dev server proxies `/api` and `/assets` to the backend on `:8000`, so there's
no CORS to deal with in development.

```bash
# 1) Backend (from the backend/ folder)
cd ../backend
python -m uvicorn app.main:app --reload --port 8000

# 2) Frontend (from this folder)
npm install
npm run dev          # http://localhost:5173
```

Optional: seed a ready-to-read demo course (no Whisper/Ollama needed — embedding
model only) so you can browse the reading view immediately:

```bash
# from the backend/ folder
cd ../backend
PYTHONPATH=. python scripts/seed_demo_lecture.py
```

## Scripts
- `npm run dev` — dev server with HMR
- `npm run build` — typecheck (`tsc -b`) + production build to `dist/`
- `npm run preview` — serve the production build locally
- `npm run typecheck` — types only

## Production
Build `dist/` and host it as static files (Vercel / Netlify / Cloudflare Pages),
with the backend deployed separately. Set the API origin at build time and allow
that frontend origin on the backend:

```bash
# frontend/.env.production
VITE_API_BASE=https://your-backend-host

# backend env
CORS_ORIGINS=https://your-frontend-host
```

Configure an SPA fallback on the static host (rewrite all routes to `index.html`)
so deep links and refreshes work with client-side routing.

## Layout
```
src/
  lib/          API client (api.ts), fetch wrapper (http.ts), helpers
  types/        API contract types (mirror specs/.../contracts/api.md)
  hooks/        TanStack Query hooks (courses, lecture polling, upload, search)
  components/
    shell/      AppShell, TopNav, ThemeToggle, Footer
    document/   NoteDocument + SegmentRenderer, SpokenOnly, DiagramFigure, …
    processing/ ProcessingTracker (staged upload→ready progress)
    upload/     UploadForm + FileDropZone (client-side validation)
    search/     SearchBar + SearchResults
    cards/      CourseCard, LectureCard
    ui/         Button, StatusBadge, Modal, Spinner, Empty/ErrorState
  pages/        Landing, Home, CourseDetail, Upload, LectureReading, NotFound
```

The document colors (slides=blue, spoken=amber, diagram=purple) are kept in sync
with `backend/app/render.py` so the on-screen reading view matches the Markdown/HTML export.
