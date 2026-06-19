# EchoNotes — Building the study tool I wished I had

> The lecture notes that remember what was *said*, not just what was *shown*.

🌐 [Live app](https://echonotes-sooty.vercel.app) · 💻 [GitHub](https://github.com/omsantoki/echonotes)

---

## The situation that started it

I kept walking out of lectures with two useless halves.

The **slides** had the *what* — bullet points, a diagram, a formula — but none of the *why*. The professor would say the important part out loud: "this only works because the data is sorted," "this is the bit everyone gets wrong on the exam." That context lived in the air for three seconds and then it was gone. Meanwhile I was still scribbling down the slide, so I missed half of what was actually said.

So after class I had: a PDF of slides with no context, and an audio recording I would *never* realistically scrub through. Two halves, neither one a real study note. And when revision came around, "what did we say about gradient descent back in week 3?" meant flipping through a semester of PDFs by hand.

I didn't want a transcription app, and I didn't want yet another notes app. I wanted the two halves **merged** — the spoken context dropped into the right place next to the slide it belonged to, organized by topic, searchable across the whole course.

That's EchoNotes.

---

## What it actually does

You upload a lecture's **audio** + its **slides (PDF)**. EchoNotes:

1. **Transcribes** the audio,
2. **Reads** the slides (text *and* diagrams),
3. **Aligns** what was said to the slide it belongs to,
4. **Merges** them into one clean, **source-labeled**, topic-organized study document — so you can see what came from the slides, what was *spoken only* (the gold), and which diagram it sat next to.

Then it remembers. Notes are stored per course, so lectures build on each other and you can **search or ask questions across the whole semester**, not just one file.

The feature I'm proudest of is the **"spoken-only" capture** — the sentences the professor said that never made it onto a slide. That's exactly the stuff I used to lose.

---

## Under the hood (where it got interesting)

This started as a weekend "merge two files" idea and turned into a genuine systems project. A few chapters were more fun (and more painful) than I expected.

### 1. It's a multimodal RAG pipeline, not a script

"Merge audio and slides" sounds like one function. It's actually five AI components in a line:

```
audio ──► Whisper (transcribe) ──┐
                                 ├──► align ──► merge (LLM) ──► embed ──► store
slides ─► PDF text + diagrams ───┘             (one doc)              (vector DB)
            + vision-LLM captions
```

The trick that makes the merge work is using **one embedding model** for *both* aligning spoken segments to slides *and* for later search. Same vector space everywhere — so "what was said" and "what was written" can actually be compared by meaning, not keywords.

### 2. Going async taught me what "durable" means

The first version ran the whole pipeline *inside the upload request*. Upload a 40-minute lecture and your browser just… spins for two minutes. Worse, if the server restarted mid-job, the work vanished and the lecture was stuck "processing" forever.

So I split it: the upload endpoint now enqueues the job to a **Celery + Redis worker pool** and returns `202 Accepted` immediately. A separate worker chews through transcribe → merge → embed in the background.

That introduced the real lesson — **what happens when a worker dies mid-job?** The answers became a checklist:

- **Late acknowledgment** (`acks_late`): the worker only marks a task "done" *after* it finishes, so a crash re-delivers the task instead of dropping it.
- **Idempotency**: a re-delivered job clears its old output first, so re-running never duplicates your notes.
- **Retries with backoff** for transient failures (a flaky API call shouldn't kill a lecture).

"Return fast, fail safe" turned out to be most of the work.

### 3. Making it multi-user, safely

Once other people could use it, isolation stopped being optional. EchoNotes is **multi-tenant**: one deployment, one database, but every user is walled off to their own data. Auth is a session **JWT** (plus email-OTP sign-up and sign-in); every course carries an `owner_id`, and — this is the part I'd do the same way again — **the owner filter lives in the storage layer, not just the route.**

The subtle bit: when you ask for a course you don't own, you get a **404, not a 403.** A 403 ("forbidden") quietly confirms the thing *exists*. A 404 makes "not yours" and "not real" indistinguishable, so the system never leaks whose data exists. Small detail, real security difference.

### 4. Cutting cost two ways

- **Dual-mode inference.** The same codebase runs **fully on-device** (Whisper + local embeddings + a local LLM via Ollama) for zero API cost, or flips to **cloud** (GPT-4o, hosted embeddings) for quality — just an env var. Great for developing for free and deploying for real.
- **A semantic cache.** "Ask your notes" hits an LLM, which costs money per question. So a Redis cache sits in front: if your new question is *semantically* near one you (or the cache) already answered (cosine ≥ 0.83), it returns the stored answer instantly — no retrieval, no model call.

---

## The newest chapter: giving my notes an API for AI agents

Here's the thought that wouldn't leave me alone: I increasingly *live* inside an AI assistant. So why am I opening a separate website to use my own notes? Why can't I just ask Claude, "what did my Bio course say about the Calvin cycle?" and have it pull from *my* lectures?

The answer is **MCP — the Model Context Protocol** — an open standard for letting an AI client call into an app. So I built EchoNotes an MCP server: five read-only tools (`list_courses`, `search_notes`, `ask_course`, `get_lecture`, `export_lecture`) that any MCP client (Claude Code, Claude Desktop) can use.

Two decisions I'm happy with:

- **One identity layer, two front doors.** The MCP tools reuse the *exact same* JWT auth function as the REST API. There's no second, parallel auth system to drift out of sync — and crucially, no tool accepts an `owner_id` argument, so the AI can never ask for someone else's data. Identity comes only from the token.
- **A cap on the bill.** The one LLM-backed tool is rate-limited per user via a Redis counter, so an agent in a loop can't quietly run up an inference bill.

And the obligatory war story: my tools kept getting "authentication required" even with a valid token. The MCP library's `get_http_headers()` helper **strips the `Authorization` header by default** (a sensible anti-footgun — you don't want to accidentally forward credentials downstream). The fix was one argument: `get_http_headers(include={"authorization"})`. An hour of confusion, one line of code. Confirming library behavior before trusting it earned its keep that day.

Now I can sit in a chat and say *"search my Biology course for photosynthesis"* and the assistant reaches into my real, merged lecture notes and answers — grounded, with sources, in whatever language I ask. That still feels a little magic.

---

## What I learned

- **The hard part is rarely the AI.** It's everything around it: returning fast, failing safe, isolating tenants, not leaking existence, capping cost.
- **"Return 202 and do it later"** quietly forces you to learn durability, idempotency, and retries — the actually-useful systems skills.
- **Reuse the seam, don't duplicate it.** Adding a whole new surface (MCP) on top of one shared auth function was almost boring to make safe — which is the point.
- **Verify your libraries.** The header that's silently stripped, the model id that's changed — assume your memory is stale and check.

## What's next

- **OAuth for MCP** — a one-click "Connect EchoNotes" instead of pasting a token.
- **Sharing** — let a classmate query a course you made, safely (revocable, read-only).
- **Ingest over MCP** — drop a PDF + audio into the chat and get notes back, with the files handed off out-of-band (you don't shove an audio file through a JSON tool call).

---

## Try it

- **App:** [echonotes-sooty.vercel.app](https://echonotes-sooty.vercel.app) — sign up, upload a lecture, get merged notes.
- **Code:** [github.com/omsantoki/echonotes](https://github.com/omsantoki/echonotes)
- **Connect your AI:** see [`docs/MCP_INTEGRATION.md`](docs/MCP_INTEGRATION.md).

I built EchoNotes because I was tired of leaving lectures with two useless halves. It turned into the most fun systems project I've done — and now my notes have an API that an AI can talk to. If you've ever lost the *why* the professor said out loud, I'd love for you to try it.

---

## AI & tools disclosure

In the interest of transparency, here's everything AI-related that went into EchoNotes — both inside the product and in building it.

**AI models used in the product (runtime).** EchoNotes runs in two modes — fully on-device (zero API cost) or cloud — so each role has two implementations:

| Role | Cloud | On-device |
|---|---|---|
| Transcription (speech → text) | OpenAI **Whisper** (`whisper-1`) | **faster-whisper** |
| Merge / composition LLM | OpenAI **GPT-4o** (`gpt-4o-mini` in prod) | **Llama 3.1** via Ollama |
| Vision LLM (diagram descriptions) | OpenAI **GPT-4o** (multimodal) | **LLaVA** via Ollama |
| Embeddings (alignment, search, cache) | OpenAI **text-embedding-3-small** | **sentence-transformers `all-MiniLM-L6-v2`** |

**APIs & services.** OpenAI API · Qdrant Cloud (vector DB) · Supabase / PostgreSQL (registry) · AWS S3 / Cloudflare R2 (diagram images) · Redis (task queue, semantic cache, rate limiting) · Brevo SMTP (email OTP) · Model Context Protocol / FastMCP (AI-agent access) · Render + Vercel (hosting).

**Datasets.** None. No model training or fine-tuning was done — every model is used as-is via API/inference. The only data is the user's own uploaded lectures, plus one sample lecture (`backend/samples/`) used for validation. Raw audio is deleted right after transcription, by design.

**AI tools used in development.** EchoNotes was built with the help of an AI coding assistant — **Claude Code (Anthropic)** — for implementation, refactoring, test-writing, debugging, and documentation, alongside a spec-driven workflow (OpenSpec) and a code-knowledge-graph tool (Graphify). All architectural decisions, integration, and validation were reviewed and owned by me.
