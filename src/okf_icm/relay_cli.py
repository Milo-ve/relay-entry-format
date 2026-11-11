"""Relay Method: proportional work, portable context, and version-specific review."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from . import __version__, guidance
from .routing import KINDS
from .storage import ContextError, atomic_write, json_text
from .tasks import Tasks
from .workspace import initialize


def parser():
    p = argparse.ArgumentParser(prog="relay", description=__doc__)
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--root", type=Path, default=Path.cwd())
    sub = p.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Initialize a project without overwriting existing state")
    init.add_argument("path", type=Path, nargs="?")
    init.add_argument("--name", default="Relay project")
    init.add_argument("--minimal", action="store_true",
                      help="One-stage workflow: a smaller config.json, so every packet is smaller. Default init is unchanged")
    skill = sub.add_parser("skill", help="Install or export a bundled skill without overwriting")
    from .skill_distribution import SKILLS
    skill.add_argument("--name", choices=SKILLS, default="relay-workspace")
    destination = skill.add_mutually_exclusive_group(required=True)
    destination.add_argument("--to", type=Path, help="Assistant skills directory")
    destination.add_argument("--zip", type=Path, help="New ZIP containing the complete skill folder")
    destination.add_argument("--manual", type=Path, help="New standalone manual handoff guide (--name ref)")
    setup = sub.add_parser("workspace", help="Preview workspace adaptation; --apply backs up before writing")
    setup.add_argument("--apply", action="store_true")
    setup.add_argument("--name", default="Relay project")
    setup.add_argument("--minimal", action="store_true", help="When this creates the workspace, use the one-stage workflow (as `init --minimal`)")
    setup.add_argument("--claude", action="store_true", help="Also back up and append a CLAUDE.md import of AGENTS.md")
    start = sub.add_parser("start", help="Create a task, choose effort, and snapshot selected inputs")
    start.add_argument("task")
    start.add_argument("--goal", required=True)
    start.add_argument("--accept", action="append", required=True)
    start.add_argument("--select", action="append", default=[])
    start.add_argument("--kind", choices=KINDS, default="auto")
    start.add_argument("--risk", choices=("low", "standard", "high"), default="standard")
    start.add_argument("--owner", default="local-operator")
    start.add_argument("--reviewer", default="local-reviewer")
    start.add_argument("--blocker", action="append", default=[])
    start.add_argument("--boundaries", default="Propose changes; no publishing or external actions.")
    start.add_argument("--jev", choices=("off", "shadow", "route"), default="off",
                       help="Explicitly send goal and selected non-control sources to TypeSafe; never enables tool execution")
    start.add_argument("--max-chars", type=int, default=32000)
    start.add_argument("--actor", help="Optional name recorded on the event; self-recorded, not authenticated")
    listing = sub.add_parser("list", help="List tasks with current freshness and acceptance")
    listing.add_argument("--brief", action="store_true",
                         help="Only id, status, freshness, owner, reviewer and revision; use `show` for detail")
    show = sub.add_parser("show")
    show.add_argument("task")
    ctx = sub.add_parser("context", help="Export the current portable work packet")
    ctx.add_argument("task")
    ctx.add_argument("--out", type=Path)
    for command in ("refresh", "escalate"):
        item = sub.add_parser(command)
        item.add_argument("task")
        item.add_argument("--note", required=True)
        item.add_argument("--expected-revision", type=int)
        item.add_argument("--actor", help="Optional name recorded on the event; self-recorded, not authenticated")
        if command == "refresh":
            item.add_argument("--resolve", action="store_true", help="Record that the operator resolved listed prerequisites")
    reassign = sub.add_parser("reassign", help="Change owner and/or reviewer; takes a new snapshot and clears the current submission and review")
    reassign.add_argument("task")
    reassign.add_argument("--owner")
    reassign.add_argument("--reviewer")
    reassign.add_argument("--note", required=True)
    reassign.add_argument("--expected-revision", type=int)
    reassign.add_argument("--actor", help="Optional name recorded on the event; self-recorded, not authenticated")
    submit = sub.add_parser("submit")
    submit.add_argument("task")
    submit.add_argument("--output", action="append", required=True)
    submit.add_argument("--evidence", action="append", required=True)
    submit.add_argument("--checks", required=True)
    submit.add_argument("--questions", default="")
    submit.add_argument("--next", required=True)
    submit.add_argument("--snapshot", action="store_true",
                        help="After validation, copy outputs and evidence byte for byte to deliverables/TASK/rREV/ and record the copies; "
                             "later edits to the originals then no longer change the submitted version")
    submit.add_argument("--expected-revision", type=int)
    submit.add_argument("--actor", help="Optional name recorded on the event; self-recorded, not authenticated")
    review = sub.add_parser("review", help="Record a local, self-attributed decision about an exact submission")
    review.add_argument("task")
    review.add_argument("--submission", required=True)
    review.add_argument("--decision", choices=("accept", "request_changes"), required=True)
    review.add_argument("--actor", required=True)
    review.add_argument("--note", required=True)
    review.add_argument("--external-ref", help="Optional pointer to an approval kept elsewhere; recorded text, never fetched or verified")
    review.add_argument("--expected-revision", type=int)
    card = sub.add_parser("card", help="Read-only delivery card: what was asked, what was used, what was returned, and what is accepted")
    card.add_argument("task")
    card.add_argument("--format", choices=("md", "html"), default="md")
    card.add_argument("--out", type=Path, help="New file outside .context; an existing file is never overwritten. Default: print to stdout")
    export = sub.add_parser("export-html", help="Write a self-contained, script-free snapshot of tasks and the knowledge map")
    export.add_argument("--out", type=Path, required=True, help="New file; an existing file is never overwritten")
    serve = sub.add_parser("serve", help="Open a loopback-only local interface; no organizational authentication")
    serve.add_argument("--port", type=int, default=8765)
    return p


def _failure_hint(args) -> None:
    """After a refused task command, say what the task needs next. Never masks the original error.

    Only when the task's state explains the refusal (changed inputs or open prerequisites);
    for other errors, such as a bad path or a wrong reviewer name, advice would be noise.
    """
    task = getattr(args, "task", None)
    if not task or args.command in {"start", "show", "list"}:
        return
    try:
        tasks = Tasks(args.root)
        status = tasks.status(task)
        step = guidance.next_step(status, guidance.command_prefix(tasks.root))
    except Exception:  # best effort: a corrupt task is reported by the original error
        return
    if step and status["status"] in {"needs_review", "blocked"}:
        print(f"relay: next: {step}", file=sys.stderr)


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "init":
            result = initialize(args.path or args.root, args.name, args.minimal)
        elif args.command == "skill":
            from .skill_distribution import export_skill, install_skill
            result = (install_skill(args.to, args.name) if args.to else
                      export_skill(args.manual or args.zip, args.name, manual=args.manual is not None))
        elif args.command == "workspace":
            from .onboarding import adapt_workspace
            result = adapt_workspace(args.root, args.name, apply=args.apply, claude=args.claude, minimal=args.minimal)
        else:
            tasks = Tasks(args.root)
            if args.command == "serve":
                from .web import serve
                serve(tasks, args.port)
                return 0
            if args.command == "export-html":
                from .viz import export_html
                atomic_write(args.out, export_html(tasks), exclusive=True)
                print(json_text({"written": str(args.out), "note": "Contains goals, acceptance state, owners, reviewers and recorded events; no source or packet contents."}), end="")
                return 0
            if args.command == "list":
                result = tasks.list()
                if args.brief:
                    result = tasks.brief(result)
            elif args.command == "show":
                result = tasks.status(args.task)
            elif args.command == "card":
                from .card import render
                text = render(tasks, args.task, args.format)
                if not args.out:
                    print(text, end="")
                    return 0
                if args.out.resolve().is_relative_to(tasks.ws.home):
                    raise ContextError("Write the card outside .context, which holds project controls and task state.")
                atomic_write(args.out, text, exclusive=True)
                result = {"written": str(args.out), "format": args.format,
                          "note": "Names are self-recorded and checks are as reported; no source or deliverable contents are included."}
            elif args.command == "context":
                text = tasks.context(args.task)
                hint = guidance.after_context(args.task, guidance.command_prefix(tasks.root))
                if args.out:
                    atomic_write(args.out, text, exclusive=True)
                    result = {"written": str(args.out), "next_step": hint}
                else:
                    print(text, end="")
                    # stderr keeps the packet on stdout clean for piping.
                    print(f"relay: next: {hint}", file=sys.stderr)
                    return 0
            else:
                with tasks.writer():
                    if args.command == "start":
                        result = tasks.start(args.task, args.goal, args.accept, args.select, args.kind, args.risk,
                                             args.owner, args.reviewer, args.blocker, args.boundaries,
                                             jev_mode=args.jev, max_chars=args.max_chars, actor=args.actor)
                    elif args.command in {"refresh", "escalate"}:
                        result = tasks.refresh(args.task, args.note, args.expected_revision,
                                               resolve=getattr(args, "resolve", False), escalate=args.command == "escalate",
                                               actor=args.actor)
                    elif args.command == "reassign":
                        result = tasks.reassign(args.task, args.note, args.owner, args.reviewer, args.expected_revision, args.actor)
                    elif args.command == "submit":
                        result = tasks.submit(args.task, args.output, args.evidence, args.checks, args.questions,
                                              args.next, args.expected_revision, args.actor, snapshot=args.snapshot)
                    elif args.command == "review":
                        result = tasks.review(args.task, args.submission, args.decision, args.actor, args.note, args.expected_revision,
                                              external_ref=args.external_ref)
                    else:
                        raise ContextError("Unknown operation.")
        print(json_text(result), end="")
        return 0
    except (ContextError, OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"relay: {exc}", file=sys.stderr)
        _failure_hint(args)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
