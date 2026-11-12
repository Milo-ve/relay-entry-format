"""Loopback-only, server-rendered Relay interface. No shell execution or external assets."""
from __future__ import annotations

from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import secrets
from urllib.parse import parse_qs, urlparse

from . import i18n
from .storage import ContextError, atomic_write, identifier, json_text
from .viz import VIZ_CSS, bundle_section, timeline_section

CSS = """
:root{--ink:#172d29;--muted:#53635e;--paper:#f6f7f2;--line:#d6ded6;--accent:#145b48;--white:#fff;--error:#943a2b}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.55 system-ui,sans-serif}
a{color:var(--accent)}header{padding:24px 5vw;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center}
header a{text-decoration:none;font-weight:750;font-size:22px}.tag{font-size:13px;color:var(--muted)}main{max-width:1150px;margin:40px auto;padding:0 24px}
h1{font-size:clamp(30px,5vw,46px);line-height:1.15;letter-spacing:-.035em;margin:8px 0 20px}h2{font-size:21px;margin:0 0 14px}h3{font-size:17px}
.intro{max-width:760px;color:var(--muted)}.grid{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-top:30px}.panel{padding:24px;border:1px solid var(--line);border-radius:12px;background:var(--white);min-width:0}
.card{display:block;border-top:1px solid var(--line);padding:18px 0;text-decoration:none}.card strong{display:block}.badge{display:inline-block;padding:4px 10px;background:#e7eee7;border-radius:20px;font-size:13px;margin:0 6px 8px 0}
.muted{color:var(--muted);font-size:14px}label{display:block;font-weight:650;margin:16px 0 6px}input,select,textarea{width:100%;padding:12px;border:1px solid #82988b;border-radius:6px;font:inherit;background:var(--white);color:var(--ink);min-height:46px}
textarea{min-height:100px;resize:vertical}button,.button{display:inline-block;min-height:46px;padding:12px 18px;background:var(--accent);color:white;border:0;border-radius:6px;text-decoration:none;font:650 15px/1.5 system-ui;cursor:pointer;margin-top:16px}button:hover,.button:hover{background:#0b4436}
input[type=checkbox]{width:auto;min-height:0;margin-right:8px}
a:focus-visible,button:focus-visible,input:focus-visible,textarea:focus-visible,select:focus-visible,summary:focus-visible{outline:3px solid #bd581e;outline-offset:3px}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:var(--paper);padding:16px;border-radius:6px;font-size:13px}details{margin-top:18px}summary{cursor:pointer;min-height:44px;padding:10px 0}.error{color:var(--error);border-left:4px solid var(--error);padding:16px;background:#fff3ed}
.wide{grid-column:1/-1}.skip{position:absolute;left:-999px}.skip:focus{left:12px;top:12px;background:white;padding:12px}footer{padding:28px 0;color:var(--muted);font-size:13px}.steps{font-size:14px;word-spacing:2px;color:var(--accent)}
@media(max-width:760px){.grid{grid-template-columns:1fr}header{padding:18px 24px}main{margin-top:28px}.panel{padding:20px}.tag{max-width:140px;text-align:right}}
""" + VIZ_CSS


def esc(value):
    return escape(str(value), quote=True)


def field(name, title, value="", textarea=False, required=True):
    attr = " required" if required else ""
    control = (f'<textarea id="{name}" name="{name}"{attr}>{esc(value)}</textarea>' if textarea else
               f'<input id="{name}" name="{name}" value="{esc(value)}"{attr}>')
    return f'<label for="{name}">{esc(title)}</label>{control}'


def handler(tasks):
    csrf = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(18)

    class Handler(BaseHTTPRequestHandler):
        lang = "en"

        def log_message(self, fmt, *args):
            pass  # Do not log task contents or token-bearing form data.

        def host(self):
            return f"127.0.0.1:{self.server.server_port}"

        def choose_language(self):
            """Read the `language` setting for this request. A broken settings file is reported by the page itself, in English."""
            try:
                self.lang = tasks.language()
            except ContextError:
                self.lang = "en"
            self.t = i18n.translator(self.lang)

        def response(self, body, status=200, content_type="text/html; charset=utf-8", download=False):
            data = body.encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", f"default-src 'none'; style-src 'nonce-{nonce}'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
            if download:
                self.send_header("Content-Disposition", 'attachment; filename="relay-context.md"')
            self.end_headers()
            self.wfile.write(data)

        def page(self, title, content, status=200):
            t = self.t
            self.response(f'<!doctype html><html lang="{self.lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} · Relay</title><style nonce="{nonce}">{CSS}</style></head>'
                          f'<body><a class="skip" href="#main">{esc(t("web.skip"))}</a><header><a href="/">Relay Method<span class="muted">{esc(t("web.brand_suffix"))}</span></a><nav><a href="/map">{esc(t("web.nav_map"))}</a></nav>'
                          f'<span class="tag">{esc(t("web.tag1"))}<br>{esc(t("web.tag2"))}</span></header><main id="main">{content}'
                          f'<footer>{esc(t("web.footer"))}</footer></main></body></html>', status)

        def form(self, action, content, revision=None):
            hidden = f'<input type="hidden" name="csrf" value="{csrf}">'
            if revision is not None:
                hidden += f'<input type="hidden" name="revision" value="{revision}">'
            return f'<form method="post" action="{action}">{hidden}{content}</form>'

        def option(self, value, key):
            return f'<option value="{value}">{esc(self.t(key))}</option>'

        def home(self):
            t, lang = self.t, self.lang
            rows = "".join(f'<a class="card" href="/tasks/{esc(x["id"])}"><strong>{esc(x["goal"])}</strong><span class="badge">{esc(i18n.status_label(lang, x["status"]))}</span>'
                           f'<span class="muted">{esc(i18n.effort(lang, x["route"]["profile"]))} · {esc(x["owner"])}</span></a>' for x in tasks.list())
            kinds = "".join(self.option(v, "web.kind_" + v) for v in ("auto", "transform", "draft", "diagnose", "design"))
            risks = "".join(self.option(v, "web.risk_" + v) for v in ("standard", "low", "high"))
            create = (field("id", t("web.f_id"), "") + field("goal", t("web.f_goal"), textarea=True)
                      + field("acceptance", t("web.f_acceptance"), textarea=True)
                      + field("sources", t("web.f_sources"), textarea=True, required=False)
                      + f'<p class="muted">{esc(t("web.sources_hint"))}</p>'
                      + f'<label for="kind">{esc(t("web.f_kind"))}</label><select id="kind" name="kind">{kinds}</select>'
                      + f'<label for="risk">{esc(t("web.f_risk"))}</label><select id="risk" name="risk">{risks}</select>'
                      + field("owner", t("web.f_owner"), "local-operator") + field("reviewer", t("web.f_reviewer"), "local-reviewer")
                      + f'<button type="submit">{esc(t("web.open_task"))}</button>')
            empty = "<p>" + esc(t("web.no_tasks")) + "</p>"
            self.page(t("web.home_title"),
                      f'<p class="steps">{esc(t("web.steps"))}</p><h1>{esc(t("web.home_h1"))}</h1><p class="intro">{esc(t("web.experience"))}</p>'
                      f'<p class="intro">{esc(t("web.principle"))}</p><div class="grid"><section class="panel"><h2>{esc(t("web.home_title"))}</h2>{rows or empty}</section>'
                      f'<section class="panel"><h2>{esc(t("web.start_h2"))}</h2>{self.form("/start", create)}</section></div>')

        def task_page(self, task):
            t, lang = self.t, self.lang
            s = tasks.status(task)
            rev = s["revision"]
            source_items = "".join(f'<li>{esc(x["path"])} <span class="muted">({esc(x["role"])})</span></li>' for x in tasks.packet(tasks.load(task))["files"])
            acceptance = "".join(f'<li>{esc(x)}</li>' for x in s["acceptance"])
            changed = (f'<div class="error" role="alert">{t("web.changed_alert", paths=esc(", ".join(s["changed"])))}</div>') if s["changed"] else ""
            submit = (field("result", t("web.f_result"), textarea=True) + field("evidence", t("web.f_evidence"), textarea=True)
                      + field("checks", t("web.f_checks"), textarea=True) + field("questions", t("web.f_questions"), textarea=True, required=False)
                      + field("next", t("web.f_next"), t("web.f_next_default")) + field("actor", t("web.f_actor"), required=False)
                      + f'<button>{esc(t("web.b_return"))}</button>')
            review = f'<p>{esc(t("web.review_first"))}</p>'
            if s["submission"]:
                review = self.form(f"/review/{task}", f'<input type="hidden" name="submission" value="{esc(s["submission"]["submission_id"])}">'
                                   + field("actor", t("web.f_reviewer_actor"), s["reviewer"]) + field("external_ref", t("web.f_external_ref"), required=False)
                                   + field("note", t("web.f_review_note"), textarea=True)
                                   + f'<label for="decision">{esc(t("web.f_decision"))}</label><select name="decision" id="decision">{self.option("accept", "web.accept_option")}{self.option("request_changes", "web.changes_option")}</select>'
                                   + f'<button>{esc(t("web.b_review"))}</button>', rev)
            operations = self.form(f"/refresh/{task}", field("note", t("web.f_refresh_note"), textarea=True)
                                   + f'<label><input type="checkbox" name="resolve" value="yes"> {esc(t("web.f_resolved"))}</label>'
                                   + field("actor", t("web.f_actor"), required=False) + f'<button>{esc(t("web.b_refresh"))}</button>', rev)
            escalation = self.form(f"/escalate/{task}", field("note", t("web.f_escalate_note"), textarea=True)
                                   + field("actor", t("web.f_actor"), required=False) + f'<button>{esc(t("web.b_escalate"))}</button>', rev)
            blockers = esc("; ".join(s["blockers"]) or t("web.no_blockers"))
            record = esc(json_text({"submission": s["submission"], "review": s["review"]}))
            people = t("web.people", owner=esc(s["owner"]), reviewer=esc(s["reviewer"]))
            self.page(s["goal"],
                      f'<a href="/">{esc(t("web.all_tasks"))}</a><h1>{esc(s["goal"])}</h1>{changed}'
                      f'<span class="badge">{esc(i18n.status_label(lang, s["status"]))}</span><span class="badge">{esc(i18n.effort(lang, s["route"]["profile"]))}</span>'
                      f'<span class="badge">{esc(t("web.sources_state", freshness=t("freshness." + s["freshness"])))}</span>'
                      f'<div class="grid"><section class="panel"><h2>{esc(t("web.h_boundaries"))}</h2><p>{esc(s["boundaries"])}</p><p>{people}</p>'
                      f'<h3>{esc(t("web.h_acceptance"))}</h3><ul>{acceptance}</ul><h3>{esc(t("web.h_sources"))}</h3><ul>{source_items}</ul>'
                      f'<p>{t("web.blockers", blockers=blockers)}</p><a class="button" href="/packet/{task}">{esc(t("web.download"))}</a>'
                      f'<details><summary>{esc(t("web.s_effort"))}</summary><pre>{esc(json_text(s["route"]))}</pre></details></section>'
                      f'<section class="panel"><h2>{esc(t("web.h_return"))}</h2><p class="muted">{esc(t("web.return_hint"))}</p>{self.form(f"/submit/{task}", submit, rev)}</section>'
                      f'<section class="panel"><h2>{esc(t("web.h_review"))}</h2>{review}<details><summary>{esc(t("web.s_record"))}</summary><pre>{record}</pre></details></section>'
                      f'<section class="panel"><h2>{esc(t("web.h_adapt"))}</h2>{operations}<details><summary>{esc(t("web.s_more_effort"))}</summary>{escalation}</details></section>'
                      f'<section class="panel wide"><h2>{esc(t("web.h_history"))}</h2>{timeline_section(tasks, task, lang)}</section></div>')

        def do_GET(self):
            self.choose_language()
            t = self.t
            if self.headers.get("Host") != self.host():
                self.response("Invalid host", 403, "text/plain")
                return
            try:
                path = urlparse(self.path).path.strip("/")
                if not path:
                    self.home()
                elif path == "map":
                    intro = t("web.map_intro", code="<code>.context/knowledge</code>")
                    self.page(t("web.map_title"), f'<a href="/">{esc(t("web.all_tasks"))}</a><h1>{esc(t("web.map_title"))}</h1><p class="intro">{intro}</p>'
                                                  f'<section class="panel">{bundle_section(tasks.ws, self.lang)}</section>')
                elif path.startswith("packet/"):
                    task = identifier(path.split("/", 1)[1])
                    self.response(tasks.context(task), content_type="text/markdown; charset=utf-8", download=True)
                elif path.startswith("tasks/"):
                    self.task_page(identifier(path.split("/", 1)[1]))
                else:
                    self.page(t("web.not_found"), f'<h1>{esc(t("web.not_found"))}</h1><a href="/">{esc(t("web.to_tasks"))}</a>', 404)
            except (ContextError, OSError, ValueError, KeyError, TypeError) as exc:
                self.page(t("web.unavailable"), f'<h1>{esc(t("web.unavailable"))}</h1><p class="error" role="alert">{esc(exc)}</p><a href="/">{esc(t("web.to_tasks"))}</a>', 400)

        def do_POST(self):
            self.choose_language()
            t = self.t
            try:
                if self.headers.get("Host") != self.host() or self.headers.get("Origin") not in {None, f"http://{self.host()}"}:
                    raise ContextError("Request origin not allowed.")
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 200000 or self.headers.get("Content-Type", "").split(";")[0] != "application/x-www-form-urlencoded":
                    raise ContextError("Expected a form under 200 KB.")
                raw = parse_qs(self.rfile.read(size).decode(), keep_blank_values=True)
                data = {k: v[0] for k, v in raw.items()}
                if not secrets.compare_digest(data.get("csrf", ""), csrf):
                    raise ContextError("Form expired or invalid. Reload the page.")
                path = urlparse(self.path).path.strip("/")
                with tasks.writer():
                    if path == "start":
                        task = identifier(data["id"])
                        tasks.start(task, data["goal"], data["acceptance"].splitlines(),
                                    [x.strip() for x in data["sources"].splitlines() if x.strip()], data["kind"], data["risk"], data["owner"], data["reviewer"])
                    else:
                        action, task = path.split("/", 1)
                        task = identifier(task)
                        revision = int(data["revision"])
                        if action == "submit":
                            state = tasks.load(task)
                            tasks.check_revision(state, revision)
                            if tasks.status(task)["changed"] or state["blockers"]:
                                raise ContextError("Refresh inputs and resolve prerequisites before submitting.")
                            paths = [f"deliverables/{task}/r{revision}-{kind}.md" for kind in ("result", "evidence")]
                            if not data["result"].strip() or not data["evidence"].strip() or not data["checks"].strip() or not data["next"].strip():
                                raise ContextError("Result, evidence, checks, and next action are required.")
                            for relative in paths:
                                target = tasks.ws.path(relative)
                                if target.exists() or target.is_symlink():
                                    raise ContextError("Result path exists. Use CLI with new output paths or refresh the task.")
                            for relative, value in zip(paths, (data["result"], data["evidence"])):
                                atomic_write(tasks.ws.path(relative), value, exclusive=True)
                            tasks.submit(task, [paths[0]], [paths[1]], data["checks"], data.get("questions", ""), data["next"], revision,
                                         actor=data.get("actor", "").strip() or None)
                        elif action == "review":
                            tasks.review(task, data["submission"], data["decision"], data["actor"], data["note"], revision,
                                         external_ref=data.get("external_ref", "").strip() or None)
                        elif action in {"refresh", "escalate"}:
                            tasks.refresh(task, data["note"], revision, resolve=data.get("resolve") == "yes", escalate=action == "escalate",
                                         actor=data.get("actor", "").strip() or None)
                        else:
                            raise ContextError("Unknown operation.")
                self.send_response(303)
                self.send_header("Location", f"/tasks/{task}")
                self.send_header("Content-Length", "0")
                self.end_headers()
            except (ContextError, OSError, ValueError, KeyError, TypeError) as exc:
                self.page(t("web.not_saved"), f'<h1>{esc(t("web.not_saved_h1"))}</h1><p class="error" role="alert">{esc(exc)}</p><p>{esc(t("web.not_saved_hint"))}</p><a href="/">{esc(t("web.to_tasks"))}</a>', 400)

    return Handler


def serve(tasks, port=8765):
    with ThreadingHTTPServer(("127.0.0.1", port), handler(tasks)) as server:
        print(f"Relay Method running at http://127.0.0.1:{server.server_port} — Ctrl+C to stop.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
