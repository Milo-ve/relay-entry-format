"""Loopback-only, server-rendered Relay interface. No shell execution or external assets."""
from __future__ import annotations

from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import secrets
from urllib.parse import parse_qs, urlparse

from .storage import ContextError, atomic_write, identifier, json_text, lock
from .tasks import EXPERIENCE, PRINCIPLE

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
"""


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
        def log_message(self, fmt, *args):
            pass  # Do not log task contents or token-bearing form data.

        def host(self):
            return f"127.0.0.1:{self.server.server_port}"

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
            self.response(f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} · Relay</title><style nonce="{nonce}">{CSS}</style></head>'
                          f'<body><a class="skip" href="#main">Skip to content</a><header><a href="/">Relay Method<span class="muted"> / local workspace</span></a><span class="tag">Portable context.<br>Proportional effort.</span></header><main id="main">{content}'
                          '<footer>Local trusted-user prototype. Reviewer identities are self-recorded. Assistant compute settings are advisory. No organization authentication or remote sharing.</footer></main></body></html>', status)

        def form(self, action, content, revision=None):
            hidden = f'<input type="hidden" name="csrf" value="{csrf}">'
            if revision is not None:
                hidden += f'<input type="hidden" name="revision" value="{revision}">'
            return f'<form method="post" action="{action}">{hidden}{content}</form>'

        def do_GET(self):
            if self.headers.get("Host") != self.host():
                self.response("Invalid host", 403, "text/plain")
                return
            try:
                path = urlparse(self.path).path.strip("/")
                if not path:
                    rows = "".join(f'<a class="card" href="/tasks/{esc(t["id"])}"><strong>{esc(t["goal"])}</strong><span class="badge">{esc(t["status"])}</span><span class="muted">{esc(t["route"]["profile"])} effort · {esc(t["owner"])}</span></a>' for t in tasks.list())
                    create = (field("id", "Task ID", "") + field("goal", "What should this task achieve?", textarea=True)
                              + field("acceptance", "What will make the result acceptable? One criterion per line.", textarea=True)
                              + field("sources", "Source paths, one per line", textarea=True, required=False)
                              + '<p class="muted">Use paths relative to this project. Only selected sources and project controls enter the packet.</p>'
                              + '<label for="kind">Kind of work</label><select id="kind" name="kind"><option value="auto">Let the rules assess it</option><option value="transform">Specified transformation</option><option value="draft">Draft or synthesis</option><option value="diagnose">Diagnosis</option><option value="design">Open-ended design</option></select>'
                              + '<label for="risk">Consequences</label><select id="risk" name="risk"><option value="standard">Standard</option><option value="low">Low and reversible</option><option value="high">High / consequential</option></select>'
                              + field("owner", "Task owner", "local-operator") + field("reviewer", "Reviewer", "local-reviewer")
                              + '<button type="submit">Open task</button>')
                    self.page("Your work", f'<p class="steps">OPEN → UNDERSTAND → CONTINUE → RETURN</p><h1>Pick up where work left off.</h1><p class="intro">{esc(EXPERIENCE)}</p><p class="intro">{esc(PRINCIPLE)}</p><div class="grid"><section class="panel"><h2>Your work</h2>{rows or "<p>No tasks yet. Open a task to prepare its first handoff.</p>"}</section><section class="panel"><h2>Start with an outcome</h2>{self.form("/start", create)}</section></div>')
                elif path.startswith("packet/"):
                    task = identifier(path.split("/", 1)[1])
                    self.response(tasks.context(task), content_type="text/markdown; charset=utf-8", download=True)
                elif path.startswith("tasks/"):
                    task = identifier(path.split("/", 1)[1])
                    s = tasks.status(task)
                    rev = s["revision"]
                    source_items = "".join(f'<li>{esc(x["path"])} <span class="muted">({esc(x["role"])})</span></li>' for x in tasks.packet(tasks.load(task))["files"])
                    acceptance = "".join(f'<li>{esc(x)}</li>' for x in s["acceptance"])
                    changed = f'<div class="error" role="alert">Review needed: {esc(", ".join(s["changed"]))}. Refresh the context and reassess affected work.</div>' if s["changed"] else ""
                    submit = field("result", "Your deliverable", textarea=True) + field("evidence", "Actual evidence / observed results", textarea=True) + field("checks", "What did you check?", textarea=True) + field("questions", "Open questions", textarea=True, required=False) + field("next", "Next action", "Review this submission against the acceptance criteria.") + '<button>Return reviewable work</button>'
                    review = '<p>Return a result before recording a review.</p>'
                    if s["submission"]:
                        review = self.form(f"/review/{task}", f'<input type="hidden" name="submission" value="{esc(s["submission"]["submission_id"])}">' + field("actor", "Reviewer (self-recorded)", s["reviewer"]) + field("note", "Review rationale", textarea=True) + '<label for="decision">Decision</label><select name="decision" id="decision"><option value="accept">Accept this version</option><option value="request_changes">Request changes</option></select><button>Record review</button>', rev)
                    operations = self.form(f"/refresh/{task}", field("note", "What changed or was resolved?", textarea=True) + '<label><input type="checkbox" name="resolve" value="yes"> I resolved the listed prerequisites</label><button>Refresh context</button>', rev)
                    escalation = self.form(f"/escalate/{task}", field("note", "Evidence requiring more effort", textarea=True) + '<button>Escalate effort</button>', rev)
                    self.page(s["goal"], f'<a href="/">← All tasks</a><h1>{esc(s["goal"])}</h1>{changed}<span class="badge">{esc(s["status"])}</span><span class="badge">{esc(s["route"]["profile"])} effort</span><span class="badge">Sources: {esc(s["freshness"])}</span><div class="grid"><section class="panel"><h2>Understand the boundaries</h2><p>{esc(s["boundaries"])}</p><p>Owner: {esc(s["owner"])} · Reviewer: {esc(s["reviewer"])}</p><h3>Acceptance</h3><ul>{acceptance}</ul><h3>Selected sources</h3><ul>{source_items}</ul><p>Blockers: {esc("; ".join(s["blockers"]) or "None recorded")}</p><a class="button" href="/packet/{task}">Download assistant context</a><details><summary>Effort decision</summary><pre>{esc(json_text(s["route"]))}</pre></details></section><section class="panel"><h2>Return reviewable work</h2><p class="muted">The text below is saved as versioned result and evidence files. Describe checks you actually performed.</p>{self.form(f"/submit/{task}", submit, rev)}</section><section class="panel"><h2>Review this version</h2>{review}<details><summary>Submission and review record</summary><pre>{esc(json_text({"submission":s["submission"],"review":s["review"]}))}</pre></details></section><section class="panel"><h2>Adapt to new evidence</h2>{operations}<details><summary>Need more effort?</summary>{escalation}</details></section></div>')
                else:
                    self.page("Not found", '<h1>Page not found</h1><a href="/">Return to tasks</a>', 404)
            except (ContextError, OSError, ValueError, KeyError, TypeError) as exc:
                self.page("Action unavailable", f'<h1>Action unavailable</h1><p class="error" role="alert">{esc(exc)}</p><a href="/">Return to tasks</a>', 400)

        def do_POST(self):
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
                with lock(tasks.ws.home):
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
                            tasks.submit(task, [paths[0]], [paths[1]], data["checks"], data.get("questions", ""), data["next"], revision)
                        elif action == "review":
                            tasks.review(task, data["submission"], data["decision"], data["actor"], data["note"], revision)
                        elif action in {"refresh", "escalate"}:
                            tasks.refresh(task, data["note"], revision, resolve=data.get("resolve") == "yes", escalate=action == "escalate")
                        else:
                            raise ContextError("Unknown operation.")
                self.send_response(303)
                self.send_header("Location", f"/tasks/{task}")
                self.send_header("Content-Length", "0")
                self.end_headers()
            except (ContextError, OSError, ValueError, KeyError, TypeError) as exc:
                self.page("Could not save", f'<h1>Could not save this action</h1><p class="error" role="alert">{esc(exc)}</p><p>Go back to retain your form, or reload the task to use its current version.</p><a href="/">Return to tasks</a>', 400)

    return Handler


def serve(tasks, port=8765):
    with ThreadingHTTPServer(("127.0.0.1", port), handler(tasks)) as server:
        print(f"Relay Method running at http://127.0.0.1:{server.server_port} — Ctrl+C to stop.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
