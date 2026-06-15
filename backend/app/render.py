"""Render the merged document (tasks T019, T020).

Renders the (refined) document as ONE clean, unified study narrative per topic, with
rich formatting (headings, bullets, bold terms). The prose does NOT call out slides
vs. speech; the single provenance cue kept visible is that **spoken-only** insights
(said in the lecture but absent from the slides) are highlighted with a ★ and reveal
their "why" on hover — honoring the constitution's requirement that spoken-only content
stay prominent (Art. III). Full provenance still lives in the stored data + API.
Diagrams render as figures in place. Also emits a flowing Markdown export.
"""

from __future__ import annotations

import html
import re

from app import store


def _image_ref(diagram_ref: str | None) -> str | None:
    if not diagram_ref:
        return None
    asset = store.get_diagram(diagram_ref)
    return asset.get("image_ref") if asset else None


def _is_spoken_only(seg: dict) -> bool:
    if seg.get("spoken_only"):
        return True
    return seg.get("source_type") == "spoken" and "★ Spoken-only" in (seg.get("reason") or "")


def _md_inline(text: str) -> str:
    """Escape HTML, then convert a tiny markdown subset (no dependency)."""
    out = html.escape(text)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"\*(.+?)\*", r"<em>\1</em>", out)
    out = re.sub(r"`(.+?)`", r"<code>\1</code>", out)
    return out


# --------------------------------- HTML --------------------------------- #

_LEGEND = ('<div class="legend"><mark class="spoken-only">🎙 highlighted ★</mark> = '
           'said in the lecture but not on the slides · 📊 diagram · '
           '<span class="muted">hover a highlight for “why”</span></div>')


def document_to_html(title: str, doc: dict, standalone: bool = False) -> str:
    topics = doc.get("topics", [])
    body = (_LEGEND + "\n" + "\n".join(_topic_html(t) for t in topics)) if topics \
        else '<p class="muted">No content.</p>'
    return page(title, body) if standalone else body


def _topic_html(topic: dict) -> str:
    parts: list[str] = []
    para: list[str] = []
    bullets: list[str] = []

    def flush_para():
        if para:
            parts.append(f'<p>{"".join(para)}</p>')
            para.clear()

    def flush_bullets():
        if bullets:
            parts.append(f'<ul>{"".join(bullets)}</ul>')
            bullets.clear()

    for seg in topic.get("segments", []):
        if seg.get("source_type") == "diagram":
            flush_bullets(); flush_para()
            cap = _md_inline((seg.get("text") or "Diagram").strip())
            img = _image_ref(seg.get("diagram_ref"))
            img_html = (f'<img class="diagram" src="{html.escape(img)}" alt="preserved diagram"/>'
                        if img else "")
            # always show the description/caption (US-5), with the image when available
            parts.append(f'<figure>{img_html}<figcaption>{cap}</figcaption></figure>')
            continue
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        if text.startswith("- "):
            flush_para()
            bullets.append(f'<li>{_segment_inline(seg, strip_bullet=True)}</li>')
        else:
            flush_bullets()
            para.append(_segment_inline(seg) + " ")
    flush_bullets(); flush_para()
    inner = "".join(parts) or '<p class="muted">No content.</p>'
    title = html.escape(topic.get("topic", "Notes"))
    builds = _builds_on_html(topic.get("builds_on"))
    return f'<section class="topic"><h2>{title}</h2>{builds}<div class="notes">{inner}</div></section>'


def _builds_on_html(link: dict | None) -> str:
    """Cross-lecture 'builds on' line for a topic (Stretch, T041), shown with its
    similarity as evidence (Art. II)."""
    if not link:
        return ""
    lt = html.escape(link.get("lecture_title") or "an earlier lecture")
    tp = html.escape(link.get("topic") or "")
    lid = html.escape(link.get("lecture_id") or "")
    sim = link.get("similarity")
    sim_txt = f" · {sim:.0%} similar" if isinstance(sim, (int, float)) else ""
    tail = f" — {tp}" if tp else ""
    return (f'<p class="builds-on">↳ Builds on <a href="/lectures/{lid}">{lt}</a>{tail}'
            f'<span class="muted">{sim_txt}</span></p>')


def _segment_inline(seg: dict, strip_bullet: bool = False) -> str:
    text = (seg.get("text") or "").strip()
    if strip_bullet and text.startswith("- "):
        text = text[2:].strip()
    inner = _md_inline(text)
    if not _is_spoken_only(seg):
        # unified prose: slide + spoken content read as one explanation, unlabeled
        return inner
    reason = (seg.get("reason") or "").strip()
    label = "Said in the lecture — not on the slides"
    title = html.escape(f"{label} · {reason}" if reason else label, quote=True)
    return f'<mark class="spoken-only" title="{title}">{inner}<span class="star"> ★</span></mark>'


def page(title: str, body: str) -> str:
    return _PAGE.format(title=html.escape(title), css=_CSS, body=body)


# ------------------------------- Markdown ------------------------------- #

def document_to_markdown(title: str, doc: dict) -> str:
    out = [f"# {title}", "",
           "_Legend: 🎙 = said in lecture · ★ = spoken-only (not on the slides)_", ""]
    para: list[str] = []

    def flush():
        if para:
            out.append(" ".join(para))
            out.append("")
            para.clear()

    for topic in doc.get("topics", []):
        flush()
        out += [f"## {topic.get('topic', 'Notes')}", ""]
        link = topic.get("builds_on")
        if link:
            sim = link.get("similarity")
            sim_txt = f" ({sim:.0%} similar)" if isinstance(sim, (int, float)) else ""
            tp = f" — {link.get('topic')}" if link.get("topic") else ""
            out += [f"> ↳ Builds on {link.get('lecture_title', 'an earlier lecture')}{tp}{sim_txt}", ""]
        for seg in topic.get("segments", []):
            st = seg.get("source_type", "slides")
            text = (seg.get("text") or "").strip()
            if st == "diagram":
                flush()
                img = _image_ref(seg.get("diagram_ref"))
                if img:
                    out.append(f"![diagram]({img})")
                if text:  # the diagram's description/caption (US-5) — keep it in export
                    out.append(f"*{text}*")
                out.append("")
                continue
            if not text:
                continue
            bullet = text.startswith("- ")
            body = text[2:].strip() if bullet else text
            if _is_spoken_only(seg):
                body = f"**🎙 {body} ★**"   # only spoken-only is marked; rest is plain prose
            if bullet:
                flush()
                out.append(f"- {body}")
            else:
                para.append(body)
        flush()
    return "\n".join(out)


# ----------------------------- Shell + styles ----------------------------- #
# Minimal — the flowing document is the star (Art. IX).

_CSS = """
:root { --line:#e3e3e8; --muted:#6b7280; --slides:#2563eb; --spoken:#b45309; --diagram:#7c3aed; }
* { box-sizing: border-box; }
body { font: 16px/1.6 -apple-system, Segoe UI, Roboto, sans-serif; color:#111827;
       max-width: 820px; margin: 0 auto; padding: 24px; background:#fafafa; }
h1 { margin: .2em 0; } h2 { margin-top: 1.5em; border-bottom:1px solid var(--line); padding-bottom:.2em; }
a { color: var(--slides); } .muted { color: var(--muted); }
.card { background:#fff; border:1px solid var(--line); border-radius:12px; padding:16px; margin:16px 0; }
.row { display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin:.5em 0; }
form label { display:block; margin:.5em 0; } input, select, button { font:inherit; padding:.45em .6em; }
button, .button { background:var(--slides); color:#fff; border:0; border-radius:8px; cursor:pointer;
                  text-decoration:none; display:inline-block; }
.legend { font-size:.8em; color:var(--muted); background:#f8f9fb; border:1px solid var(--line);
          border-radius:8px; padding:7px 11px; margin:10px 0 18px; }
.notes { font-size:1.02rem; }
.notes p { margin: 0 0 .9em; }
.notes ul { margin:.2em 0 1em 1.2em; } .notes li { margin:.25em 0; }
.builds-on { font-size:.85em; color:var(--diagram); margin:.1em 0 .7em; }
/* slide + spoken content render as one unified, unlabeled prose; only spoken-only is marked */
mark.spoken-only { background:#fff3cd; padding:.04em .18em; border-radius:3px;
                   box-shadow: inset 0 -0.5em 0 #fde68a; }
mark.spoken-only .star { color:var(--spoken); font-weight:700; }
.notes [title] { cursor: help; }
figure { margin: 1.1em 0; text-align:center; }
figure img.diagram { max-width:100%; border:1px solid var(--line); border-radius:6px; }
figcaption { font-size:.85em; color:var(--muted); margin-top:.3em; }
.progress { font-size:1.1em; padding:14px; background:#eef2ff; border-radius:8px; }
.fail { color:#b91c1c; }
.badge { font-size:.72em; font-weight:600; color:#fff; background:var(--muted); border-radius:999px; padding:2px 8px; }
.status-ready{background:#16a34a;} .status-processing{background:var(--spoken);} .status-failed{background:#b91c1c;}
"""

_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{title} · EchoNotes</title><style>{css}</style></head>
<body>{body}</body></html>"""
