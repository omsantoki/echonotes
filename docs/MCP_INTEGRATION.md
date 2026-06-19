# Integrating EchoNotes with Your AI (MCP Guide)

Connect **any AI assistant that speaks MCP** (Claude Code, Claude Desktop, Cursor) to
**EchoNotes**, so the assistant can read your lecture notes and answer questions grounded in
them — no copy‑pasting, no leaving the chat.

> **What is MCP?** The [Model Context Protocol](https://modelcontextprotocol.io) is an open
> standard for letting an AI client call into an external app. EchoNotes ships a hosted MCP
> **server**; your AI is the MCP **client**.

---

## The two addresses (read this first)

EchoNotes has **two separate URLs**, and they are not interchangeable:

| Use it for | URL |
|---|---|
| **The app** (sign up, upload lectures, browse notes) | `https://echonotes-sooty.vercel.app` |
| **The API + MCP** (login + the `/mcp` endpoint your AI connects to) | `https://echonotes-api.onrender.com` |

The app (Vercel) is just the website; it does **not** serve `/mcp`. Your AI always connects to
the **backend**: `https://echonotes-api.onrender.com/mcp`.

> Throughout this guide: **`APP`** = `https://echonotes-sooty.vercel.app`,
> **`API`** = `https://echonotes-api.onrender.com`.

---

## What you get

EchoNotes exposes five **read‑only** MCP tools. Once connected, your AI calls them on its own
while you just chat:

| Tool | What it does |
|---|---|
| `list_courses` | List your courses |
| `search_notes` | Semantic search across one course's merged lecture notes |
| `ask_course` | A grounded RAG answer from one course's notes (with sources) |
| `get_lecture` | One lecture's merged study document (or its processing status) |
| `export_lecture` | Export a ready lecture as Markdown or HTML |

The notes are EchoNotes' signature output: a lecture's **audio + slides merged** into one
source‑labelled, topic‑organised document — so answers include spoken‑only insights, not just
slide text.

```
┌──────────────┐   MCP over HTTP    ┌──────────────────────────┐     ┌──────────────┐
│  Your AI     │ ───────────────►   │  API /mcp  (5 tools)     │ ──► │  Your notes  │
│ (MCP client) │  Authorization:    │  echonotes-api.onrender  │     │ (your data,  │
│              │ ◄───────────────   │  owner‑scoped by token   │ ◄── │  course-only)│
└──────────────┘   JSON results     └──────────────────────────┘     └──────────────┘
```

---

## Part 1 — Operator: turn MCP on in production (one‑time)

> **Do this once.** As shipped, `ENABLE_MCP=false` in `render.yaml`, so
> `API/mcp` currently returns **404** and no one can connect. You only do this once for the
> whole deployment — not per person.

1. In the **Render dashboard** → service **`echonotes-api`** → **Environment**, set:
   - `ENABLE_MCP=true`
   - `ENABLE_QA=true` (needed for the `ask_course` tool)
2. **Redeploy** the service.
3. Verify:
   ```bash
   curl -s -o /dev/null -w "%{http_code}\n" https://echonotes-api.onrender.com/mcp
   ```
   `307` = MCP is live (the mount redirects `/mcp` → `/mcp/`; clients follow it).
   `404` = still off / not redeployed.

**Tuning flags (optional):**

| Variable | Default | Purpose |
|---|---|---|
| `ENABLE_MCP` | `false` | Master switch. `true` mounts `/mcp`. |
| `ENABLE_QA` | `true` | Required for `ask_course` (the LLM Q&A). |
| `MCP_ASK_RATE_LIMIT` | `30` | Max `ask_course` calls per user per window (LLM spend). |
| `MCP_ASK_RATE_WINDOW` | `60` | Rate‑limit window, seconds. |

Once this is on, the **same deployment serves every user** — each is isolated by their own
login token. Nothing more to configure per person.

---

## Part 2 — End user: the whole flow

This is what **each person** does to talk to **their own** EchoNotes notes from **their own**
Claude. (They never touch Render, `.env`, or any server setup.)

```
Sign up  →  Upload a lecture  →  Get your token  →  Connect your Claude  →  Chat
```

### Step 1 — Sign up (in a browser)
Go to **`https://echonotes-sooty.vercel.app`**, sign up with your email → enter the code sent
to your inbox → set a password. (Or use "Continue with Google.") You now have your own private
space.

### Step 2 — Upload a lecture
In the app, upload a lecture's **audio** + **slides (PDF)** and wait a minute while EchoNotes
transcribes the audio, reads the slides, and merges them into notes. Now there's something to
query.

### Step 3 — Get your token (your "login key")
In a terminal, log in against the **API** with your email + password:
```bash
curl -s -X POST https://echonotes-api.onrender.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"YOU@example.com","password":"YOUR_PASSWORD"}'
```
The response contains a long `session_token` — copy it. (It's a temporary key for your account;
default lifetime ~24h.)

### Step 4 — Connect your Claude

**Claude Code** (one line — don't split it):
```bash
claude mcp add --transport http echonotes https://echonotes-api.onrender.com/mcp \
  --header "Authorization: Bearer YOUR_TOKEN"
```

**Claude Desktop / Cursor** — add to the MCP config (`claude_desktop_config.json` /
`.cursor/mcp.json`) using the [`mcp-remote`](https://www.npmjs.com/package/mcp-remote) bridge:
```json
{
  "mcpServers": {
    "echonotes": {
      "command": "npx",
      "args": [
        "-y", "mcp-remote",
        "https://echonotes-api.onrender.com/mcp",
        "--header", "Authorization: Bearer YOUR_TOKEN"
      ]
    }
  }
}
```
Restart the client.

### Step 5 — Just chat
In your Claude, type normally:
> "List my EchoNotes courses."
> "Search my Biology course for photosynthesis."
> "Using my Biology notes, explain the light reactions and cite the lecture."

Claude reaches into **your** EchoNotes, pulls **your** notes, and answers. You only ever see
your own data; other users never see yours.

> The only slightly technical bit is Step 3 (copying a token). A future **v2 OAuth** "Connect
> EchoNotes" button would collapse Steps 3–4 into one click — no terminal.

---

## Tool reference

All tools are **owner‑scoped**: the user is derived from the token, never from an argument. A
course/lecture you don't own returns the **same "not found"** as one that doesn't exist
(existence is never leaked).

### `list_courses()`
```json
[ { "id": "…", "name": "Biology", "lecture_count": 3 } ]
```

### `search_notes(course_id: str, query: str)`
```json
{ "query": "light reactions",
  "results": [ { "lecture_id": "…", "lecture_title": "Week 3", "topic": "Light Reactions",
                 "text": "…", "source_type": "merged" } ] }
```

### `ask_course(course_id: str, question: str)`
Grounded RAG answer using **only** that course's notes. Needs `ENABLE_QA=true`; rate‑limited.
```json
{ "query": "what is entropy?", "answer": "…", "sources": [ … ], "cached": false }
```

### `get_lecture(lecture_id: str)`
```json
// ready:    { "id": "…", "status": "ready", "title": "Week 3", "document": { "topics": [ … ] } }
// not ready:{ "id": "…", "status": "processing", "progress": "Transcribing…" }
```

### `export_lecture(lecture_id: str, format: str = "md")`
```json
{ "id": "…", "title": "Week 3", "format": "md", "content_type": "text/markdown", "content": "# Week 3\n…" }
```

---

## Example conversations

> "List my EchoNotes courses."
> "Search my **Biology** course for the Calvin cycle."
> "Make a 10‑question quiz from my **Biology** course, hardest topics first."
> "Pull my Week 3 lecture and turn it into a one‑page cheat sheet."
> "What did my notes say about X? Answer in Spanish." *(grounded retrieval + translation)*

The power is **composition**: EchoNotes provides the grounded content; your AI provides the
writing, quiz‑making, translation, or formatting on top.

---

## Security model

- **Per‑user isolation.** A token identifies exactly one user; tools never accept an
  `owner_id`/`user_id`, so one user's AI can't reach another user's notes.
- **No leakage.** Not‑owned and non‑existent ids are indistinguishable ("not found").
- **Read‑only (v1).** No tool creates, edits, or deletes data — connecting an AI cannot mutate
  a user's notes.
- **Cost control.** `ask_course` is gated by `ENABLE_QA` and rate‑limited per user.
- **Token hygiene.** Tokens are short‑lived (~24h) and should be handled like passwords. Rotate
  by logging in again.
- **Off by default.** The surface only exists when `ENABLE_MCP=true`.

---

## Limits & roadmap

**v1 (today):** read‑only tools; static bearer token pasted into the client (Claude Code &
Desktop). **Planned v2:** OAuth one‑click connector; **sharing** (so a user can let *another*
person query *their* notes — today strict isolation prevents cross‑user access by design);
**write tools** (upload/annotate from the assistant).

---

## Troubleshooting

| Symptom | Cause → Fix |
|---|---|
| `404` on `https://echonotes-api.onrender.com/mcp` | `ENABLE_MCP` still `false` in production. Do **Part 1** (set it `true` on Render, redeploy). |
| Pointed Claude at `echonotes-sooty.vercel.app/mcp` and it fails | That's the **app**, not the API. Use `https://echonotes-api.onrender.com/mcp`. |
| `Invalid header format: "Bearer"` | The `--header` value got mangled (often by pasting the command twice). Run `claude mcp add` **once**, as a single line. |
| "Authentication required" from every tool | Missing/expired/invalid token. Log in again (Step 3) and update the client's header. |
| `ask_course` says "Q&A is not enabled" | `ENABLE_QA=false`. Set it `true` and redeploy. |
| "Rate limit exceeded for ask_course" | The per‑user window is full. Wait, or raise `MCP_ASK_RATE_LIMIT`. |
| "No course …" for a course you expect | The token's user doesn't own it (tokens are per‑user), or the id is wrong. |

---

## Quick reference

```bash
# Operator (once): enable on Render echonotes-api → ENABLE_MCP=true, ENABLE_QA=true → redeploy
curl -s -o /dev/null -w "%{http_code}\n" https://echonotes-api.onrender.com/mcp   # want 307

# User: 1) sign up + upload at  https://echonotes-sooty.vercel.app
#       2) get a token
curl -s -X POST https://echonotes-api.onrender.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"YOU@example.com","password":"PASSWORD"}'        # → session_token

#       3) connect Claude Code
claude mcp add --transport http echonotes https://echonotes-api.onrender.com/mcp \
  --header "Authorization: Bearer YOUR_TOKEN"

#       4) ask Claude: "List my EchoNotes courses."
```

**App:** `https://echonotes-sooty.vercel.app` · **API + MCP:** `https://echonotes-api.onrender.com/mcp` ·
**Auth:** `Authorization: Bearer <session_token>` ·
**Tools:** `list_courses`, `search_notes`, `ask_course`, `get_lecture`, `export_lecture`

---

### Local development (alternative)
Running the backend yourself? Use `http://localhost:8000` instead of the `API` URL above
(set `ENABLE_MCP=true` in `backend/.env`, restart `uvicorn app.main:app`). Note: a localhost
server is only reachable from your own machine — others can't connect to it.

*For the formal capability spec, see [`openspec/specs/mcp-server/spec.md`](../openspec/specs/mcp-server/spec.md).*
