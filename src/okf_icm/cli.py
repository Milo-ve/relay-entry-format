"""A provider-neutral CLI. Commands never invoke a model or execute packet text."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from . import __version__
from . import knowledge, settings
from .packets import export
from .storage import ContextError, atomic_write, json_text, lock, read_text
from .workspace import Workspace, initialize


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="okf-icm", description=__doc__)
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--root", type=Path, default=Path.cwd(), help="Project root (default: cwd). Place before the command.")
    sub = p.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Create .context without overwriting project files")
    init.add_argument("path", type=Path, nargs="?")
    init.add_argument("--name", default="My project")
    run = sub.add_parser("run", help="Start or checkpoint a task")
    actions = run.add_subparsers(dest="action", required=True)
    start = actions.add_parser("start")
    start.add_argument("id")
    start.add_argument("--goal", required=True)
    start.add_argument("--accept", action="append", required=True)
    checkpoint = actions.add_parser("checkpoint")
    checkpoint.add_argument("--run", required=True)
    checkpoint.add_argument("--stage", required=True)
    checkpoint.add_argument("--packet", required=True)
    checkpoint.add_argument("--output", action="append", required=True)
    checkpoint.add_argument("--evidence", action="append", default=[])
    skip = actions.add_parser("skip")
    skip.add_argument("--run", required=True)
    skip.add_argument("--stage", required=True)
    skip.add_argument("--reason", required=True)
    handoff = actions.add_parser("handoff")
    handoff.add_argument("--run", required=True)
    handoff.add_argument("--file", required=True, help="Project-relative handoff source")
    for name in ("status", "verify"):
        item = sub.add_parser(name, help="Read state and recompute freshness" if name == "status" else "Exit 1 if completed stages need review")
        item.add_argument("--run", required=True)
    context = sub.add_parser("context", help="Export a bounded context packet and persist its receipt")
    context.add_argument("--run", required=True)
    context.add_argument("--stage")
    context.add_argument("--select", action="append", default=[], help="Project-relative path, optionally #Exact Markdown Heading")
    context.add_argument("--format", choices=("markdown", "json"), default="markdown")
    context.add_argument("--max-chars", type=int, default=32000)
    context.add_argument("--out", type=Path, help="Write a new packet export; never overwrite")
    adapter = sub.add_parser("adapter", help="Print or save an optional entry snippet")
    adapter.add_argument("--kind", choices=("generic", "agents", "claude"), default="generic")
    adapter.add_argument("--out", type=Path)
    know = sub.add_parser("knowledge", help="Inspect or curate the OKF core profile")
    ops = know.add_subparsers(dest="action", required=True)
    for name in ("list", "validate", "index"):
        ops.add_parser(name)
    add = ops.add_parser("add")
    add.add_argument("id")
    add.add_argument("--title", required=True)
    add.add_argument("--type", default="Reference")
    add.add_argument("--body", required=True, help="Project-relative body file")
    add.add_argument("--source", action="append", default=[])
    promote = ops.add_parser("promote")
    promote.add_argument("id")
    promote.add_argument("--evidence", required=True)
    promote.add_argument("--reviewer", required=True)
    promote.add_argument("--note", required=True)
    promote.add_argument("--confirmed-content", action="store_true")
    return p


def dispatch(args) -> int:
    if args.command == "init":
        print(json_text(initialize(args.path or args.root, args.name)), end="")
        return 0
    ws = Workspace(args.root)
    if args.command in {"status", "verify"}:
        report = ws.status(args.run)
        print(json_text(report), end="")
        return int(args.command == "verify" and any(s["status"] == "needs_review" for s in report["stages"].values()))
    if args.command == "knowledge" and args.action in {"list", "validate"}:
        report = knowledge.inspect_bundle(ws)
        print(json_text(report), end="")
        return int(bool(report["errors"]))
    if args.command == "adapter":
        text = (f"# OKF + ICM entry ({args.kind})\n\n"
                "Read `.context/ENTRY.md`. Use the explicit run ID given by the user.\n"
                "Run `okf-icm status --run RUN` and export `okf-icm context --run RUN`.\n"
                "Follow the exported stage contract within the host's own instruction hierarchy.\n"
                "If tools are unavailable, ask the operator to paste the exported packet.\n")
        emit(text, args.out)
        return 0
    with lock(ws.home, wait=settings.load(ws.home)["lock_wait_seconds"]):
        if args.command == "context":
            # Check output first so an existing destination doesn't create an orphan export.
            if args.out and (args.out.exists() or args.out.is_symlink()):
                raise ContextError("Export destination exists. Choose a new --out path.")
            _, text = export(ws, args.run, args.stage, args.select, args.format, args.max_chars)
            emit(text, args.out)
            return 0
        if args.command == "run":
            if args.action == "start":
                report = ws.start(args.id, args.goal, args.accept)
            elif args.action == "checkpoint":
                report = ws.checkpoint(args.run, args.stage, args.packet, args.output, args.evidence)
            elif args.action == "skip":
                report = ws.skip(args.run, args.stage, args.reason)
            else:
                ws.state(args.run)
                text = read_text(ws.root, args.file)
                if not text.strip():
                    raise ContextError("Handoff cannot be empty.")
                atomic_write(ws.run_home(args.run) / "handoff.md", text)
                ws.event(args.run, "handoff")
                report = {"run_id": args.run, "handoff_updated": True}
        elif args.command == "knowledge":
            if args.action == "index":
                knowledge.reindex(ws)
                report = {"indexed": True}
            elif args.action == "add":
                report = knowledge.add(ws, args.id, args.title, args.type, args.body, args.source)
            else:
                report = knowledge.promote(ws, args.id, args.evidence, args.reviewer, args.note, args.confirmed_content)
        else:
            raise ContextError("Unknown command.")
        print(json_text(report), end="")
    return 0


def emit(text: str, output: Path | None):
    if output:
        atomic_write(output, text, exclusive=True)
        print(json_text({"written": str(output)}), end="")
    else:
        print(text, end="")


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        return dispatch(args)
    except (ContextError, OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"okf-icm: {exc}", file=sys.stderr)
        return 2
