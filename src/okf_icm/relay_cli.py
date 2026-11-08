"""Relay Method: proportional work, portable context, and version-specific review."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from . import __version__
from .routing import KINDS
from .storage import ContextError, atomic_write, json_text, lock
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
    sub.add_parser("list", help="List tasks with current freshness and acceptance")
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
        if command == "refresh":
            item.add_argument("--resolve", action="store_true", help="Record that the operator resolved listed prerequisites")
    submit = sub.add_parser("submit")
    submit.add_argument("task")
    submit.add_argument("--output", action="append", required=True)
    submit.add_argument("--evidence", action="append", required=True)
    submit.add_argument("--checks", required=True)
    submit.add_argument("--questions", default="")
    submit.add_argument("--next", required=True)
    submit.add_argument("--expected-revision", type=int)
    review = sub.add_parser("review", help="Record a local, self-attributed decision about an exact submission")
    review.add_argument("task")
    review.add_argument("--submission", required=True)
    review.add_argument("--decision", choices=("accept", "request_changes"), required=True)
    review.add_argument("--actor", required=True)
    review.add_argument("--note", required=True)
    review.add_argument("--expected-revision", type=int)
    serve = sub.add_parser("serve", help="Open a loopback-only local interface; no organizational authentication")
    serve.add_argument("--port", type=int, default=8765)
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "init":
            result = initialize(args.path or args.root, args.name)
        else:
            tasks = Tasks(args.root)
            if args.command == "serve":
                from .web import serve
                serve(tasks, args.port)
                return 0
            if args.command == "list":
                result = tasks.list()
            elif args.command == "show":
                result = tasks.status(args.task)
            elif args.command == "context":
                text = tasks.context(args.task)
                if args.out:
                    atomic_write(args.out, text, exclusive=True)
                    result = {"written": str(args.out)}
                else:
                    print(text, end="")
                    return 0
            else:
                with lock(tasks.ws.home):
                    if args.command == "start":
                        result = tasks.start(args.task, args.goal, args.accept, args.select, args.kind, args.risk,
                                             args.owner, args.reviewer, args.blocker, args.boundaries,
                                             jev_mode=args.jev, max_chars=args.max_chars)
                    elif args.command in {"refresh", "escalate"}:
                        result = tasks.refresh(args.task, args.note, args.expected_revision,
                                               resolve=getattr(args, "resolve", False), escalate=args.command == "escalate")
                    elif args.command == "submit":
                        result = tasks.submit(args.task, args.output, args.evidence, args.checks, args.questions,
                                              args.next, args.expected_revision)
                    elif args.command == "review":
                        result = tasks.review(args.task, args.submission, args.decision, args.actor, args.note, args.expected_revision)
                    else:
                        raise ContextError("Unknown operation.")
        print(json_text(result), end="")
        return 0
    except (ContextError, OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"relay: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
