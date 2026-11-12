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

from . import i18n
from .storage import ContextError
from .viz import VIZ_CSS, _EXPORT_CSS, csp_for, esc, states

FORMATS = ("md", "html")
CARD_CSS = ".pre{white-space:pre-wrap;margin:4px 0}dl.facts{display:grid;grid-template-columns:max-content 1fr;gap:6px 16px}dl.facts dt{color:var(--muted);font-size:14px}dl.facts dd{margin:0;overflow-wrap:anywhere}code{font:13px ui-monospace,monospace;overflow-wrap:anywhere}"


def model(tasks, task: str, lang: str | None = None) -> dict:
    """Everything the card shows, read from existing state. Never writes."""
    lang = lang or tasks.language()
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
    sources_state, work_state, acceptance_state = states(status, lang)
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


def _where(item: dict, t) -> str:
    text = _code(item["path"])
    if item.get("source_path"):
        text += " " + t("card.copy_of", path=_code(item["source_path"]))
    return text + f" · sha256 {item['hash']}…" + ("" if item["current"] else f" · **{t('card.changed_since')}**")


def markdown(card: dict, generated: str | None = None, lang: str = "en") -> str:
    t = i18n.translator(lang)
    generated = generated or datetime.now(timezone.utc).isoformat(timespec="seconds")
    work, review = card["work"], card["review"]
    out = ["# " + t("card.title", goal=_md(card["goal"])), "",
           t("card.line", id=_code(card["id"]), revision=card["revision"], effort=_md(i18n.effort(lang, card["effort"])), generated=generated), "",
           f"## {t('card.h_status')}", "",
           f"- **{t('card.sources')}:** {_md(card['states']['sources'])}",
           f"- **{t('card.work')}:** {_md(card['states']['work'])}",
           f"- **{t('card.acceptance')}:** {_md(card['states']['acceptance'])}", "",
           f"## {t('card.h_goal')}", "", _quote(card["goal"]), ""]
    out += [f"- {_md(x)}" for x in card["acceptance"]]
    out += ["", t("card.boundaries", text=_md(card["boundaries"])), "",
            f"## {t('card.h_people')}", "", f"- {t('card.owner')}: {_md(card['owner'])}", f"- {t('card.reviewer')}: {_md(card['reviewer'])}", "",
            f"## {t('card.h_sources')}", ""]
    if card["sources"]:
        out += [f"| {t('card.t_source')} | {t('card.t_section')} | {t('card.t_role')} | sha256 | {t('card.t_snapshot')} | {t('card.t_now')} |", "|---|---|---|---|---|---|"]
        for s in card["sources"]:
            path = _code(s["path"]).replace("|", "\\|")
            now = t("card.current") if s["current"] else f"**{t('card.changed')}**"
            out.append(f"| {path} | {_md(s['section'] or t('card.whole_file'))} | {s['role']} | {s['hash']}… | {s['snapshot']} | {now} |")
    else:
        out.append(t("card.no_sources"))
    out += ["", t("card.controls", n=card["controls"]), "", f"## {t('card.h_work')}", ""]
    if work:
        out += [f"{t('card.outputs')}:", *[f"- {_where(x, t)}" for x in work["outputs"]], "", f"{t('card.evidence')}:", *[f"- {_where(x, t)}" for x in work["evidence"]], "",
                f"{t('card.checks')}:", "", _quote(work["checks"]), "",
                f"{t('card.questions')}:", "", _quote(work["open_questions"] or t("card.none_recorded")), "",
                f"{t('card.next')}: {_md(work['next_action'])}"]
    else:
        out.append(t("card.nothing_returned"))
    if card["blockers"]:
        out += ["", t("card.blockers", blockers="; ".join(_md(x) for x in card["blockers"]))]
    out += ["", f"## {t('card.h_review')}", ""]
    if review:
        key = "card.accepted_by" if review["decision"] == "accept" else "card.changes_by"
        out.append(t(key, actor=_md(review["actor"]), at=review["at"]))
        if review.get("external_ref"):
            out.append(t("card.reference", ref=_md(review["external_ref"])))
        out += ["", _quote(review["note"])]
    else:
        out.append(t("card.no_review"))
    out += ["", f"## {t('card.h_ids')}", "",
            f"- {t('card.packet')}: {_code(card['packet_id'])}",
            f"- {t('card.submission')}: {_code(work['submission_id']) if work else t('card.none')}", "", f"_{t('card.note')}_", ""]
    return "\n".join(out)


# ----------------------------------------------------------------------- html

def _list(items) -> str:
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


def _html_where(item: dict, t) -> str:
    text = f"<code>{esc(item['path'])}</code>"
    if item.get("source_path"):
        text += " " + t("card.copy_of", path=f"<code>{esc(item['source_path'])}</code>")
    return text + f" · sha256 {esc(item['hash'])}…" + ("" if item["current"] else f' · <strong class="error">{esc(t("card.changed_since"))}</strong>')


def html(card: dict, generated: str | None = None, lang: str = "en") -> str:
    """One self-contained page with no scripts, no network and a style pinned by hash."""
    t = i18n.translator(lang)
    generated = generated or datetime.now(timezone.utc).isoformat(timespec="seconds")
    css = _EXPORT_CSS + VIZ_CSS + CARD_CSS
    work, review = card["work"], card["review"]
    st = card["states"]
    changed = f'<strong class="error">{esc(t("card.changed"))}</strong>'
    rows = "".join(f"<tr><td><code>{esc(s['path'])}</code></td><td>{esc(s['section'] or t('card.whole_file'))}</td><td>{esc(s['role'])}</td>"
                   f"<td>{esc(s['hash'])}…</td><td>{esc(s['snapshot'])}</td><td>{esc(t('card.current')) if s['current'] else changed}</td></tr>"
                   for s in card["sources"])
    heads = "".join(f"<th>{esc(h)}</th>" for h in (t("card.t_source"), t("card.t_section"), t("card.t_role"), "sha256", t("card.t_snapshot"), t("card.t_now")))
    sources = (f'<div class="scroll"><table class="data"><thead><tr>{heads}</tr></thead><tbody>{rows}</tbody></table></div>'
               if rows else f"<p>{esc(t('card.no_sources'))}</p>")
    if work:
        returned = (f"<h3>{esc(t('card.outputs'))}</h3>" + _list(_html_where(x, t) for x in work["outputs"])
                    + f"<h3>{esc(t('card.evidence'))}</h3>" + _list(_html_where(x, t) for x in work["evidence"])
                    + f'<h3>{esc(t("card.checks"))}</h3><p class="pre">{esc(work["checks"])}</p>'
                    f'<h3>{esc(t("card.questions"))}</h3><p class="pre">{esc(work["open_questions"] or t("card.none_recorded"))}</p>'
                    f'<h3>{esc(t("card.next"))}</h3><p>{esc(work["next_action"])}</p>')
    else:
        returned = f"<p>{esc(t('card.nothing_returned'))}</p>"
    blockers = f"<p>{t('card.blockers', blockers=esc('; '.join(card['blockers'])))}</p>" if card["blockers"] else ""
    if review:
        key = "card.accepted_by" if review["decision"] == "accept" else "card.changes_by"
        ref = f"<p>{t('card.reference', ref=esc(review['external_ref']))}</p>" if review.get("external_ref") else ""
        reviewed = f'<p>{t(key, actor=esc(review["actor"]), at=esc(review["at"]))}</p>{ref}<p class="pre">{esc(review["note"])}</p>'
    else:
        reviewed = f"<p>{esc(t('card.no_review'))}</p>"
    submission = f"<code>{esc(work['submission_id'])}</code>" if work else esc(t("card.none"))
    line = t("card.line", id=f"<code>{esc(card['id'])}</code>", revision=card["revision"],
             effort=esc(i18n.effort(lang, card["effort"])), generated=esc(generated))
    return (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<meta http-equiv="Content-Security-Policy" content="{esc(csp_for(css))}"><meta name="robots" content="noindex">'
            f'<title>{esc(t("card.html_title", id=card["id"]))}</title><style>{css}</style></head><body><main>'
            f'<h1>{esc(card["goal"])}</h1><p class="muted">{line}</p>'
            f'<section><h2>{esc(t("card.h_status"))}</h2><dl class="strip">'
            f'<div><dt>{esc(t("card.sources"))}</dt><dd>{esc(st["sources"])}</dd></div><div><dt>{esc(t("card.work"))}</dt><dd>{esc(st["work"])}</dd></div>'
            f'<div><dt>{esc(t("card.acceptance"))}</dt><dd>{esc(st["acceptance"])}</dd></div></dl></section>'
            f'<section><h2>{esc(t("card.h_criteria"))}</h2>{_list(esc(x) for x in card["acceptance"])}<p class="muted">{t("card.boundaries", text=esc(card["boundaries"]))}</p>'
            f'<dl class="facts"><dt>{esc(t("card.owner_sr"))}</dt><dd>{esc(card["owner"])}</dd><dt>{esc(t("card.reviewer_sr"))}</dt><dd>{esc(card["reviewer"])}</dd></dl></section>'
            f'<section><h2>{esc(t("card.h_sources"))}</h2>{sources}<p class="muted">{t("card.controls", n=card["controls"])}</p></section>'
            f'<section><h2>{esc(t("card.h_work"))}</h2>{returned}{blockers}</section>'
            f'<section><h2>{esc(t("card.h_review"))}</h2>{reviewed}</section>'
            f'<section><h2>{esc(t("card.h_ids"))}</h2><dl class="facts"><dt>{esc(t("card.packet"))}</dt><dd><code>{esc(card["packet_id"])}</code></dd><dt>{esc(t("card.submission"))}</dt><dd>{submission}</dd></dl>'
            f'<p class="muted">{esc(t("card.note"))}</p></section></main></body></html>')


def render(tasks, task: str, fmt: str = "md", lang: str | None = None) -> str:
    if fmt not in FORMATS:
        raise ContextError("Card format must be md or html.")
    lang = lang or tasks.language()
    card = model(tasks, task, lang)
    return markdown(card, lang=lang) if fmt == "md" else html(card, lang=lang)
