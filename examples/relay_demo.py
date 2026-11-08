"""Prepare a fresh, synthetic Relay workspace. Never overwrite a destination."""
from pathlib import Path
import sys

from okf_icm.storage import atomic_write
from okf_icm.tasks import Tasks
from okf_icm.workspace import initialize


def prepare(destination):
    root = Path(destination).resolve()
    if root.exists():
        raise ValueError("Destination exists; choose a new directory.")
    initialize(root, "Relay synthetic pricing project")
    atomic_write(root / ".context/project.md", "# Project authority\n\n`inputs/pricing-current.md` is the designated current policy.\nProduce proposals only. No publishing or purchases.\n")
    atomic_write(root / "inputs/pricing-current.md", "# Current synthetic policy\n\n149 MXN per month, applicable taxes included in this fictitious exercise.\nThree users. Email support. Phone support excluded. No annual plan approved.\n")
    tasks = Tasks(root)
    tasks.start("pricing-faq", "Draft a source-backed pricing FAQ", ["Every commercial answer cites the current policy", "Unknown commercial terms remain explicit"],
                ["inputs/pricing-current.md"], kind="draft", owner="collaborator", reviewer="milo")
    return root


if __name__ == "__main__":
    try:
        target = prepare(sys.argv[1])
        print(f"Prepared {target}\nRun: relay --root {target} serve")
    except (IndexError, ValueError, OSError) as exc:
        raise SystemExit(f"Usage: python examples/relay_demo.py NEW_DIRECTORY\n{exc}")
