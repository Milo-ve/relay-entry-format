"""Static views of a Relay project: knowledge map, task timeline and a shareable snapshot.

Everything is generated server-side as inline SVG and HTML. There is no JavaScript, no
external asset and no inline style attribute, so the restrictive CSP of the local UI is
unchanged. Views show metadata Relay actually recorded (hashes, freshness, trust signals,
events). They never include source or packet contents, and they do not turn a recorded
signal into verification: trust labels are the bundle's own claims, and "checks" are what
the submitter reported.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
from html import escape
import hashlib
import math

from .knowledge import inspect_bundle, local_links, parse_concept
from .storage import ContextError, read_text

MAX_NODES = 100

VIZ_CSS = """
svg.viz{display:block;width:100%;height:auto;max-width:100%}svg.viz.icon{width:26px;height:26px;flex:none}
.viz .edge{fill:none;stroke:#7f948b;stroke-width:1.2;opacity:.75}.viz .arrow{fill:#7f948b}
.viz .node{stroke-width:2}.viz .t-human{fill:#145b48;stroke:#0b4436}.viz .t-machine{fill:#cfe6dc;stroke:#145b48}.viz .t-none{fill:#fff;stroke:#53635e}
.viz .stale{stroke-dasharray:4 3}.viz text{font:12px system-ui,sans-serif;fill:#172d29}.viz .lane{stroke:#b7c4bb;stroke-width:2}
.viz .ev{fill:#fff;stroke:#145b48;stroke-width:2}.viz .ev-accept{fill:#145b48}.viz .ev-changes{fill:#fff;stroke:#943a2b}.viz .mark{fill:none;stroke:#fff;stroke-width:2}.viz .mark-dark{fill:none;stroke:#943a2b;stroke-width:2}
.viz .old{opacity:.45}.viz .sub{fill:#53635e;font-size:11px}
.legend{display:flex;flex-wrap:wrap;gap:6px 22px;list-style:none;padding:0;margin:12px 0}.legend li{display:flex;align-items:center;gap:6px;font-size:13px}
.strip{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin:14px 0}.strip div{border:1px solid var(--line);border-radius:8px;padding:12px;background:var(--white)}
.strip dt{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}.strip dd{margin:4px 0 0;font-weight:650}
table.data{border-collapse:collapse;width:100%;font-size:14px}table.data th,table.data td{text-align:left;padding:8px 10px;border-top:1px solid var(--line);overflow-wrap:anywhere}table.data th{font-size:12px;text-transform:uppercase;color:var(--muted)}
.scroll{overflow-x:auto}
"""

_SHAPE_NOTE = "Shape = lifecycle (circle stable, square draft, diamond deprecated). Fill = trust. Dashed outline = stale."


def esc(value) -> str:
    return escape(str(value), quote=True)


def _short(text: str, limit: int = 30) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _trust_class(trust: str) -> str:
    return {"human-reviewed": "t-human", "machine-confirmed": "t-machine"}.get(trust, "t-none")


def _shape(status: str, classes: str, x: float, y: float) -> str:
    if status == "draft":
        return f'<rect class="{classes}" x="{x - 8:.1f}" y="{y - 8:.1f}" width="16" height="16" rx="3"/>'
    if status == "deprecated":
        return f'<polygon class="{classes}" points="{x:.1f},{y - 11:.1f} {x + 11:.1f},{y:.1f} {x:.1f},{y + 11:.1f} {x - 11:.1f},{y:.1f}"/>'
    return f'<circle class="{classes}" cx="{x:.1f}" cy="{y:.1f}" r="9"/>'


# ---------------------------------------------------------------- knowledge map

def bundle_model(ws) -> dict:
    """Concepts and the links between them, from the same checks as `knowledge validate`."""
    report = inspect_bundle(ws)
    bundle = ws.path(".context/knowledge")
    ids = {c["id"] for c in report["concepts"]}
    edges, seen = [], set()
    for concept in report["concepts"]:
        path = bundle / (concept["id"] + ".md")
        try:
            _, body = parse_concept(read_text(ws.root, path.relative_to(ws.root).as_posix()))
        except (ValueError, OSError, UnicodeError):
            continue  # inspect_bundle already reports unreadable concepts
        for _, dest in local_links(bundle, path, body):
            try:
                rel = dest.resolve().relative_to(bundle.resolve()).as_posix()
            except ValueError:
                continue
            target = rel[:-3] if rel.endswith(".md") else None
            if target in ids and target != concept["id"] and (concept["id"], target) not in seen:
                seen.add((concept["id"], target))
                edges.append((concept["id"], target))
    return {"nodes": report["concepts"], "edges": edges, "errors": report["errors"], "warnings": report["warnings"],
            "profile": report["profile"]}


def bundle_svg(model: dict) -> str:
    nodes = model["nodes"][:MAX_NODES]
    if not nodes:
        return ""
    n = len(nodes)
    r = max(110, round(n * 22 / (2 * math.pi)))
    margin_x, margin_y = 250, 34
    width, height = 2 * (r + margin_x), 2 * (r + margin_y)
    cx, cy = width / 2, height / 2
    pos = {}
    for i, node in enumerate(nodes):
        angle = -math.pi / 2 + 2 * math.pi * i / n
        pos[node["id"]] = (cx + r * math.cos(angle), cy + r * math.sin(angle), angle)
    edges = []
    for src, dst in model["edges"]:
        if src not in pos or dst not in pos:
            continue
        (x1, y1, _), (x2, y2, _) = pos[src], pos[dst]
        qx, qy = cx + 0.25 * ((x1 + x2) / 2 - cx), cy + 0.25 * ((y1 + y2) / 2 - cy)
        dx, dy = x2 - qx, y2 - qy
        norm = math.hypot(dx, dy) or 1.0
        ex, ey = x2 - 13 * dx / norm, y2 - 13 * dy / norm
        edges.append(f'<path class="edge" d="M{x1:.1f},{y1:.1f} Q{qx:.1f},{qy:.1f} {ex:.1f},{ey:.1f}" marker-end="url(#arrow)"/>')
    marks = []
    for node in nodes:
        x, y, angle = pos[node["id"]]
        classes = "node " + _trust_class(node["trust"]) + (" stale" if node["freshness"] == "stale" else "")
        left = math.cos(angle) < -0.01
        lx = x + (-16 if left else 16)
        summary = f'{node["title"]} ({node["id"]}): {node["type"]}, {node["status"]}, {node["trust"]}, freshness {node["freshness"]}'
        marks.append(f'<g><title>{esc(summary)}</title>{_shape(node["status"], classes, x, y)}'
                     f'<text x="{lx:.1f}" y="{y + 4:.1f}" text-anchor="{"end" if left else "start"}">{esc(_short(node["title"]))}</text></g>')
    desc = f"{n} concepts and {len(edges)} links. " + _SHAPE_NOTE + " The table below lists every concept."
    return (f'<svg class="viz" role="img" aria-labelledby="map-t map-d" viewBox="0 0 {width:.0f} {height:.0f}" xmlns="http://www.w3.org/2000/svg">'
            f'<title id="map-t">Knowledge map</title><desc id="map-d">{esc(desc)}</desc>'
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="arrow" d="M0,0 L10,5 L0,10 z"/></marker></defs>'
            + "".join(edges) + "".join(marks) + "</svg>")


def legend() -> str:
    items = [("stable", "t-human node", "Stable, human-reviewed"), ("stable", "t-machine node", "Stable, machine-confirmed"),
             ("stable", "t-none node", "Stable, unverified"), ("draft", "t-none node", "Draft"),
             ("deprecated", "t-none node", "Deprecated"), ("stable", "t-none node stale", "Stale (dashed)")]
    return '<ul class="legend">' + "".join(
        f'<li><svg class="viz icon" width="26" height="26" viewBox="0 0 26 26" aria-hidden="true">{_shape(s, c, 13, 13)}</svg>{esc(t)}</li>'
        for s, c, t in items) + "</ul>"


def bundle_table(model: dict) -> str:
    out_deg, in_deg = {}, {}
    for src, dst in model["edges"]:
        out_deg[src] = out_deg.get(src, 0) + 1
        in_deg[dst] = in_deg.get(dst, 0) + 1
    rows = "".join(
        f'<tr><td>{esc(c["id"])}</td><td>{esc(c["title"])}</td><td>{esc(c["type"])}</td><td>{esc(c["status"])}</td>'
        f'<td>{esc(c["trust"])}</td><td>{esc(c["freshness"])}</td><td>{out_deg.get(c["id"], 0)} / {in_deg.get(c["id"], 0)}</td></tr>'
        for c in model["nodes"])
    return ('<div class="scroll"><table class="data"><caption class="muted">Links are out / in. Trust labels are the bundle\'s own recorded claims; Relay does not verify them.</caption>'
            '<thead><tr><th>Concept</th><th>Title</th><th>Type</th><th>Status</th><th>Trust</th><th>Freshness</th><th>Links</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>')


def bundle_section(ws) -> str:
    model = bundle_model(ws)
    if not model["nodes"] and not model["errors"]:
        return '<p>No knowledge concepts yet. Add one with <code>okf-icm knowledge add</code>.</p>'
    cut = len(model["nodes"]) - MAX_NODES
    notice = f'<p class="muted">The map draws the first {MAX_NODES} concepts; {cut} more appear only in the table.</p>' if cut > 0 else ""
    problems = ""
    if model["errors"]:
        items = "".join(f'<li>{esc(e["path"])}: {esc(e["message"])}</li>' for e in model["errors"])
        problems = f'<div class="error" role="alert"><strong>{len(model["errors"])} concept(s) are invalid and not drawn:</strong><ul>{items}</ul></div>'
    unresolved = sum(1 for w in model["warnings"] if w["message"].startswith("Unresolved link"))
    leaving = sum(1 for w in model["warnings"] if w["message"].startswith("Link leaves bundle"))
    extra = f'<p class="muted">{unresolved} unresolved link(s) (allowed by OKF) and {leaving} link(s) leaving the bundle are not drawn.</p>' if unresolved or leaving else ""
    return problems + notice + bundle_svg(model) + legend() + extra + bundle_table(model)


# --------------------------------------------------------------- task timeline

_LABELS = {"start": "Task opened", "refresh": "Context refreshed", "escalate": "Effort escalated", "submit": "Work returned",
           "reassign": "Owner or reviewer reassigned"}
_RESET = {"start", "refresh", "escalate", "reassign"}


def timeline_model(tasks, task: str) -> dict:
    state, status = tasks.load(task), tasks.status(task)
    events = state["events"]
    boundary = max((i for i, e in enumerate(events) if e.get("action") in _RESET), default=0)
    rows = []
    for i, event in enumerate(events):
        action = event.get("action", "?")
        label = _LABELS.get(action, str(action))
        kind = action
        if action == "review":
            decision = event.get("decision", "")
            label = "Accepted this version" if decision == "accept" else "Changes requested"
            kind = "accept" if decision == "accept" else "changes"
            actor = (event.get("review") or {}).get("actor")
            if actor:
                label += f" · {actor} (self-recorded)"
        if action == "start" and event.get("profile"):
            label += f" · {event['profile']} effort"
        if action == "reassign" and event.get("current"):
            label += f" · reviewer {event['current'].get('reviewer')}, owner {event['current'].get('owner')}"
        if event.get("actor") and action != "review":
            label += f" · {event['actor']} (self-recorded)"
        rows.append({"kind": kind, "label": label, "at": event.get("at", ""), "current": i >= boundary})
    return {"id": task, "goal": status["goal"], "status": status, "events": rows, "packets": len(state["packets"])}


def strip(model: dict) -> str:
    s = model["status"]
    sources = "Current" if not s["changed"] else "Changed since selected: " + ", ".join(s["changed"])
    work = "Returned for this version" if s["submission"] else "Not returned yet"
    review = s["review"]
    if review and review["decision"] == "accept":
        accepted = "Accepted by " + review["actor"] + " (self-recorded)" if not s["changed"] else "Earlier acceptance no longer applies: inputs changed"
    elif review:
        accepted = "Changes requested"
    elif s["blockers"]:
        accepted = "Blocked: " + "; ".join(s["blockers"])
    else:
        accepted = "Not accepted"
    return ('<dl class="strip">'
            f'<div><dt>Selected sources</dt><dd>{esc(sources)}</dd></div>'
            f'<div><dt>Work and reported checks</dt><dd>{esc(work)}</dd><span class="muted">Checks are as reported by the submitter; Relay does not verify them.</span></div>'
            f'<div><dt>Acceptance</dt><dd>{esc(accepted)}</dd></div></dl>')


def _marker(kind: str, x: float, y: float) -> str:
    if kind in {"refresh", "reassign"}:
        return f'<polygon class="ev" points="{x:.0f},{y - 10} {x + 10:.0f},{y} {x:.0f},{y + 10} {x - 10:.0f},{y}"/>'
    if kind == "escalate":
        return f'<polygon class="ev" points="{x:.0f},{y - 10} {x + 10:.0f},{y + 9} {x - 10:.0f},{y + 9}"/>'
    if kind == "submit":
        return f'<rect class="ev" x="{x - 9:.0f}" y="{y - 9}" width="18" height="18" rx="2"/>'
    if kind == "accept":
        return f'<circle class="ev ev-accept" cx="{x:.0f}" cy="{y}" r="10"/><path class="mark" d="M{x - 5:.0f},{y} l3.5,4 l6,-8"/>'
    if kind == "changes":
        return f'<circle class="ev ev-changes" cx="{x:.0f}" cy="{y}" r="10"/><path class="mark-dark" d="M{x - 4:.0f},{y - 4} l8,8 m0,-8 l-8,8"/>'
    return f'<circle class="ev" cx="{x:.0f}" cy="{y}" r="10"/>'


def timeline_svg(model: dict) -> str:
    events, step, top, x = model["events"], 54, 28, 34
    height = top * 2 + step * max(len(events) - 1, 0)
    parts = [f'<line class="lane" x1="{x}" y1="{top}" x2="{x}" y2="{top + step * max(len(events) - 1, 0)}"/>'] if len(events) > 1 else []
    for i, event in enumerate(events):
        y = top + step * i
        cls = "" if event["current"] else ' class="old"'
        note = "" if event["current"] else " · superseded by a later refresh"
        parts.append(f'<g{cls}>{_marker(event["kind"], x, y)}<text x="{x + 24}" y="{y - 2}">{esc(event["label"])}</text>'
                     f'<text class="sub" x="{x + 24}" y="{y + 13}">{esc(event["at"])}{esc(note)}</text></g>')
    desc = "; ".join(f'{e["label"]} at {e["at"]}' + ("" if e["current"] else " (superseded)") for e in events)
    return (f'<svg class="viz" role="img" aria-labelledby="tl-t-{esc(model["id"])} tl-d-{esc(model["id"])}" viewBox="0 0 640 {height}" xmlns="http://www.w3.org/2000/svg">'
            f'<title id="tl-t-{esc(model["id"])}">Task history</title><desc id="tl-d-{esc(model["id"])}">{esc(desc)}</desc>' + "".join(parts) + "</svg>")


def timeline_section(tasks, task: str) -> str:
    model = timeline_model(tasks, task)
    return (strip(model) + timeline_svg(model)
            + f'<p class="muted">{model["packets"]} context packet version(s) recorded. Faded events were superseded by a later refresh and no longer count toward the current version. '
              'Marks show recorded events, not proof that checks were correct.</p>')


# ------------------------------------------------------------------- snapshot

_EXPORT_CSS = """
:root{--ink:#172d29;--muted:#53635e;--paper:#f6f7f2;--line:#d6ded6;--accent:#145b48;--white:#fff;--error:#943a2b}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.55 system-ui,sans-serif}
main{max-width:1100px;margin:0 auto;padding:32px 24px}h1{font-size:clamp(28px,5vw,40px);line-height:1.15;margin:0 0 8px}h2{font-size:22px;margin:0 0 12px}h3{font-size:18px;margin:0 0 6px}
section{background:var(--white);border:1px solid var(--line);border-radius:12px;padding:24px;margin:24px 0}.muted{color:var(--muted);font-size:14px}
.badge{display:inline-block;padding:4px 10px;background:#e7eee7;border-radius:20px;font-size:13px;margin-right:6px}.error{color:var(--error);border-left:4px solid var(--error);padding:12px 16px;background:#fff3ed}
"""


def export_html(tasks) -> str:
    """One self-contained page: no scripts, no network, style pinned by hash."""
    css = _EXPORT_CSS + VIZ_CSS
    digest = base64.b64encode(hashlib.sha256(css.encode()).digest()).decode()
    csp = f"default-src 'none'; style-src 'sha256-{digest}'; base-uri 'none'; form-action 'none'"
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    cards = []
    folder = tasks.ws.path(".context/relay/tasks")
    names = sorted(p.parent.name for p in folder.glob("*/state.json")) if folder.exists() else []
    for name in names:
        try:
            model = timeline_model(tasks, name)
            s = model["status"]
            cards.append(f'<section><h3>{esc(s["goal"])}</h3><span class="badge">{esc(s["status"])}</span><span class="badge">{esc(s["route"]["profile"])} effort</span>'
                         f'<span class="badge">{esc(s["id"])}</span><p class="muted">Owner: {esc(s["owner"])} · Reviewer: {esc(s["reviewer"])} · Revision {s["revision"]}</p>'
                         + strip(model) + timeline_svg(model) + "</section>")
        except (ContextError, OSError, ValueError, KeyError, TypeError) as exc:
            cards.append(f'<section><h3>{esc(name)}</h3><p class="error" role="alert">This task could not be read and is not shown: {esc(exc)}</p></section>')
    project = tasks.ws.root.name
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<meta http-equiv="Content-Security-Policy" content="{esc(csp)}"><meta name="robots" content="noindex"><title>{esc(project)} · Relay snapshot</title>'
            f'<style>{css}</style></head><body><main><h1>{esc(project)}</h1>'
            f'<p class="muted">Relay snapshot generated {esc(stamp)}. It is a point-in-time copy, not a live view. It lists goals, acceptance state, '
            'owners, reviewers and recorded events; it contains no source, packet or deliverable contents. Names are self-recorded; no organization authenticated them.</p>'
            f'<section><h2>Knowledge map</h2>{bundle_section(tasks.ws)}</section>'
            f'<h2>Tasks ({len(names)})</h2>{"".join(cards) or "<p>No tasks yet.</p>"}</main></body></html>')
