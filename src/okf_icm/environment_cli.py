"""Small CLI adapter for the knowledge-first path; no task-layer imports."""
from .environment import Environment
from .storage import ContextError, atomic_write, json_text


def add_commands(sub):
    prepare = sub.add_parser("prepare", help="Preview or generate a navigable knowledge environment from text folders")
    prepare.add_argument("--path", action="append", required=True, help="Source folder or text file relative to --root (repeatable)")
    prepare.add_argument("--name")
    prepare.add_argument("--apply", action="store_true", help="Write the previewed maps and draft references; preserve original files")
    browse = sub.add_parser("browse", help="List current sources, headings and changes without opening a task")
    browse.add_argument("--format", choices=("markdown", "json"), default="markdown")
    find = sub.add_parser("find", help="Search source text; matches are candidates, not verified answers")
    find.add_argument("query")
    find.add_argument("--limit", type=int, default=8)
    find.add_argument("--format", choices=("markdown", "json"), default="markdown")
    read = sub.add_parser("read", help="Read one source or exact Markdown heading")
    read.add_argument("selection")
    read.add_argument("--format", choices=("markdown", "json"), default="markdown")


def dispatch_environment(args):
    commands = {"prepare", "browse", "find", "read"}
    context = args.command == "context" and not args.run
    if args.command not in commands and not context:
        return None
    env = Environment(args.root)
    if args.command == "prepare":
        result = env.prepare(args.path, apply=args.apply, name=args.name)
    elif args.command == "browse":
        result = env.browse()
    elif args.command == "find":
        result = env.find(args.query, args.limit)
    elif args.command == "read":
        result = env.read(args.selection)
    else:
        if args.stage:
            raise ContextError("--stage requires --run; omit both for knowledge context.")
        _, text = env.context(args.select, fmt=args.format, max_chars=args.max_chars)
        if args.out:
            if args.out.resolve().is_relative_to(env.home):
                raise ContextError("Write exported context outside .context, which holds the environment.")
            atomic_write(args.out, text, exclusive=True)
            print(json_text({"written": str(args.out), "note": "No run, receipt or acceptance was created."}), end="")
        else:
            print(text, end="")
        return 0
    if args.command == "prepare" or args.format == "json":
        print(json_text(result), end="")
    elif args.command == "read":
        print(f"Source: {result['path']}\nSHA-256: {result['sha256']}\n\n{result['content']}", end="")
    elif args.command == "browse":
        print(f"# Knowledge sources\n\nEntry: {result['entry']}\nMap: {result['map']}\n")
        for item in result["sources"]:
            changed = " [changed since preparation]" if item["changed_since_prepare"] else ""
            print(f"- {item['title']} — {item['path']}{changed}")
            if item["headings"]:
                print("  Sections: " + ", ".join(item["headings"]))
        for path in result["removed_sources"]:
            print(f"- No longer selected: {path}")
        for item in result["skipped"]:
            print(f"- Skipped {item['path']}: {item['reason']}")
        print("\n" + result["note"])
    else:
        print("# Source candidates\n")
        if not result["matches"]:
            print("No lexical matches. Try another term or inspect the source map.\n")
        for item in result["matches"]:
            changed = " [changed since preparation]" if item["changed_since_prepare"] else ""
            print(f"- {item['path']}:{item['line']}{changed}\n  {item['excerpt']}")
        if result["unmatched_terms"]:
            print("\nUnmatched terms: " + ", ".join(result["unmatched_terms"]))
        if result["omitted_matches"]:
            print(f"\n{result['omitted_matches']} additional candidates omitted; increase --limit to inspect more.")
        for item in result["skipped"]:
            print(f"- Skipped {item['path']}: {item['reason']}")
        print("\n" + result["note"])
    return 0
