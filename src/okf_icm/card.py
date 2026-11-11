"""Delivery card: a read-only, one-page summary of a task for someone who will not open Relay.

It shows what Relay recorded about the task: goal, criteria, owner and reviewer (self-recorded names),
the selected sources with section, short hash and snapshot date, the reported checks, open questions,
next action, and the identifiers of the exact packet and submission. Source, packet and deliverable
contents are never included. The three states (are the sources current, was work returned, was it
accepted) stay separate, and nothing here verifies a check or authenticates a name.

Generating a card changes no task state: it only reads.
"""
from __future__ import annotations

from datetime import datetime, timezone
import re

from .storage import ContextError
from .viz import VIZ_CSS, _EXPORT_CSS, csp_for, esc, states

FORMATS = ("md", "html")
CARD_CSS = ".pre{white-space:pre-wrap;margin:4px 0}dl.facts{display:grid;grid-template-columns:max-content 1fr;gap:6px 16px}dl.facts dt{color:var(--muted);font-size:14px}dl.facts dd{margin:0;overflow-wrap:anywhere}code{font:13px ui-monospace,monospace;overflow-wrap:anywhere}"
NOTE = ("Names are self-recorded; no organization authenticated them. Checks are as reported by the submitter and Relay does not verify them. "
        "This card lists what Relay recorded and contains no source, packet or deliverable contents.")


def model(tasks, task: str) -> dict:
    """Everything the card shows, read from existing state. Never writes."""
    state = tasks.load(task)
    status = tasks.status(task)
    packet = tasks.packet(state)
    changed = set(status["changed"])
    sources = [{"path": f["path"], "section": f["section"], "role": f["role"], "hash": f["sha256"][:12],
                "snapshot": packet["created_at"], "current": f["path"] not in changed}
               for f in packet["files"] if f["role"] != "control"]
    submission = status["submission"]
    work = None
    if submission:
        def record(item):
            return {"path": item["path"], "hash": item["sha256"][:12], "source_path": item.get("source_path"),
                    "current": item["path"] not in changed}
        work = {"outputs": [record(x) for x in submission["outputs"]], "evidence": [record(x) for x in submission["evidence"]],
                "snapshot": bool(submission.get("snapshot")), "checks": submission["checks"],
                "open_questions": submission["open_questions"], "next_action": submission["next_action"],
                "at": submission["at"], "submission_id": submission["submission_id"]}
    sources_state, work_state, acceptance_state = states(status)
    return {"id": task, "goal": status["goal"], "acceptance": status["acceptance"], "boundaries": status["boundaries"],
            "owner": status["owner"], "reviewer": status["reviewer"], "revision": status["revision"],
            "effort": status["route"]["profile"], "packet_id": status["packet_id"], "sources": sources,
            "controls": sum(1 for f in packet["files"] if f["role"] == "control"), "work": work,
            "blockers": status["blockers"], "review": status["review"],
            "states": {"sources": sources_state, "work": work_state, "acceptance": acceptance_state}}


# ------------------------------------------------------------------- markdown

def _md(text) -> str:
    """One line of user text that cannot start markup of its own, mid-line or at the start of a line."""
    text = " ".join(str(text).split())
    for char in "\\`*_[]<>|&":
        text = text.replace(char, "\\" + char)
    text = re.sub(r"^(\d+)([.)])", r"\1\\\2", text)  # "1." would start a list
    return re.sub(r"^([#+=~-])", r"\\\1", text)  # headings, bullets, rules, setext underlines, fences


def _code(text) -> str:
    return "`" + " ".join(str(text).split()).replace("`", "'") + "`"


def _quote(text) -> str:
    lines = [_md(line) if line.strip() else "" for line in str(text).strip().splitlines()]
    return "\n".join(("> " + line).rstrip() for line in lines) or "> (none)"


def _where(item: dict) -> str:
    text = _code(item["path"])
    if item.get("source_path"):
        text += f" (copy of {_code(item['source_path'])})"
    return text + f" · sha256 {item['hash']}…" + ("" if item["current"] else " · **changed since recorded**")


def markdown(card: dict, generated: str | None = None) -> str:
    generated = generated or datetime.now(timezone.utc).isoformat(timespec="seconds")
    work, review = card["work"], card["review"]
    out = [f"# Delivery card: {_md(card['goal'])}", "",
           f"Task {_code(card['id'])} · revision {card['revision']} · {_md(card['effort'])} effort · generated {generated}", "",
           "## Status, in three separate parts", "",
           f"- **Selected sources:** {_md(card['states']['sources'])}",
           f"- **Work returned:** {_md(card['states']['work'])}",
           f"- **Acceptance:** {_md(card['states']['acceptance'])}", "",
           "## Goal and acceptance criteria", "", _quote(card["goal"]), ""]
    out += [f"- {_md(x)}" for x in card["acceptance"]]
    out += ["", f"Boundaries: {_md(card['boundaries'])}", "",
            "## People (self-recorded)", "", f"- Owner: {_md(card['owner'])}", f"- Reviewer: {_md(card['reviewer'])}", "",
            "## Selected sources", ""]
    if card["sources"]:
        out += ["| Source | Section | Role | sha256 | Snapshot | Now |", "|---|---|---|---|---|---|"]
        for s in card["sources"]:
            path = _code(s["path"]).replace("|", "\\|")
            now = "current" if s["current"] else "**changed**"
            out.append(f"| {path} | {_md(s['section'] or 'whole file')} | {s['role']} | {s['hash']}… | {s['snapshot']} | {now} |")
    else:
        out.append("No sources were selected beyond the project controls.")
    out += ["", f"The packet also carries {card['controls']} project control file(s).", "", "## Work returned", ""]
    if work:
        out += ["Outputs:", *[f"- {_where(x)}" for x in work["outputs"]], "", "Evidence:", *[f"- {_where(x)}" for x in work["evidence"]], "",
                "Checks the submitter reported (not verified by Relay):", "", _quote(work["checks"]), "",
                "Open questions:", "", _quote(work["open_questions"] or "None recorded."), "",
                f"Next action (submitter): {_md(work['next_action'])}"]
    else:
        out.append("Nothing has been returned for this version.")
    if card["blockers"]:
        out += ["", "Open prerequisites: " + "; ".join(_md(x) for x in card["blockers"])]
    out += ["", "## Review", ""]
    if review:
        decision = "Accepted" if review["decision"] == "accept" else "Changes requested"
        out.append(f"{decision} by {_md(review['actor'])} (self-recorded) at {review['at']}.")
        if review.get("external_ref"):
            out.append(f"Reference: {_md(review['external_ref'])} (recorded, not verified).")
        out += ["", _quote(review["note"])]
    else:
        out.append("No review recorded for this version.")
    out += ["", "## Identifiers", "",
            f"- Packet: {_code(card['packet_id'])}",
            f"- Submission: {_code(work['submission_id']) if work else 'none'}", "", f"_{NOTE}_", ""]
    return "\n".join(out)


# ----------------------------------------------------------------------- html

def _list(items) -> str:
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


def _html_where(item: dict) -> str:
    text = f"<code>{esc(item['path'])}</code>"
    if item.get("source_path"):
        text += f" (copy of <code>{esc(item['source_path'])}</code>)"
    return text + f" · sha256 {esc(item['hash'])}…" + ("" if item["current"] else ' · <strong class="error">changed since recorded</strong>')


def html(card: dict, generated: str | None = None) -> str:
    """One self-contained page with no scripts, no network and a style pinned by hash."""
    generated = generated or datetime.now(timezone.utc).isoformat(timespec="seconds")
    css = _EXPORT_CSS + VIZ_CSS + CARD_CSS
    work, review = card["work"], card["review"]
    st = card["states"]
    changed = '<strong class="error">changed</strong>'
    rows = "".join(f"<tr><td><code>{esc(s['path'])}</code></td><td>{esc(s['section'] or 'whole file')}</td><td>{esc(s['role'])}</td>"
                   f"<td>{esc(s['hash'])}…</td><td>{esc(s['snapshot'])}</td><td>{'current' if s['current'] else changed}</td></tr>"
                   for s in card["sources"])
    sources = (f'<div class="scroll"><table class="data"><thead><tr><th>Source</th><th>Section</th><th>Role</th><th>sha256</th><th>Snapshot</th><th>Now</th></tr></thead><tbody>{rows}</tbody></table></div>'
               if rows else "<p>No sources were selected beyond the project controls.</p>")
    if work:
        returned = ("<h3>Outputs</h3>" + _list(_html_where(x) for x in work["outputs"]) + "<h3>Evidence</h3>" + _list(_html_where(x) for x in work["evidence"])
                    + f'<h3>Checks the submitter reported (not verified by Relay)</h3><p class="pre">{esc(work["checks"])}</p>'
                    f'<h3>Open questions</h3><p class="pre">{esc(work["open_questions"] or "None recorded.")}</p>'
                    f'<h3>Next action (submitter)</h3><p>{esc(work["next_action"])}</p>')
    else:
        returned = "<p>Nothing has been returned for this version.</p>"
    blockers = f"<p>Open prerequisites: {esc('; '.join(card['blockers']))}</p>" if card["blockers"] else ""
    if review:
        decision = "Accepted" if review["decision"] == "accept" else "Changes requested"
        ref = f"<p>Reference: {esc(review['external_ref'])} (recorded, not verified).</p>" if review.get("external_ref") else ""
        reviewed = (f'<p>{decision} by {esc(review["actor"])} (self-recorded) at {esc(review["at"])}.</p>{ref}<p class="pre">{esc(review["note"])}</p>')
    else:
        reviewed = "<p>No review recorded for this version.</p>"
    submission = f"<code>{esc(work['submission_id'])}</code>" if work else "none"
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<meta http-equiv="Content-Security-Policy" content="{esc(csp_for(css))}"><meta name="robots" content="noindex">'
            f'<title>Delivery card · {esc(card["id"])}</title><style>{css}</style></head><body><main>'
            f'<h1>{esc(card["goal"])}</h1><p class="muted">Task <code>{esc(card["id"])}</code> · revision {card["revision"]} · {esc(card["effort"])} effort · generated {esc(generated)}</p>'
            '<section><h2>Status, in three separate parts</h2><dl class="strip">'
            f'<div><dt>Selected sources</dt><dd>{esc(st["sources"])}</dd></div><div><dt>Work returned</dt><dd>{esc(st["work"])}</dd></div>'
            f'<div><dt>Acceptance</dt><dd>{esc(st["acceptance"])}</dd></div></dl></section>'
            f'<section><h2>Acceptance criteria</h2>{_list(esc(x) for x in card["acceptance"])}<p class="muted">Boundaries: {esc(card["boundaries"])}</p>'
            f'<dl class="facts"><dt>Owner (self-recorded)</dt><dd>{esc(card["owner"])}</dd><dt>Reviewer (self-recorded)</dt><dd>{esc(card["reviewer"])}</dd></dl></section>'
            f'<section><h2>Selected sources</h2>{sources}<p class="muted">The packet also carries {card["controls"]} project control file(s).</p></section>'
            f'<section><h2>Work returned</h2>{returned}{blockers}</section>'
            f'<section><h2>Review</h2>{reviewed}</section>'
            f'<section><h2>Identifiers</h2><dl class="facts"><dt>Packet</dt><dd><code>{esc(card["packet_id"])}</code></dd><dt>Submission</dt><dd>{submission}</dd></dl>'
            f'<p class="muted">{esc(NOTE)}</p></section></main></body></html>')


def render(tasks, task: str, fmt: str = "md") -> str:
    if fmt not in FORMATS:
        raise ContextError("Card format must be md or html.")
    card = model(tasks, task)
    return markdown(card) if fmt == "md" else html(card)
