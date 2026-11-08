"""End-to-end installed Relay CLI check with synthetic data; no model is called."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from relay_demo import prepare


def run(root, *args):
    result = subprocess.run([sys.executable, "-m", "okf_icm.relay_cli", "--root", str(root), *args], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"{args[0]} failed: {result.stderr}")
    return json.loads(result.stdout)


def smoke():
    with tempfile.TemporaryDirectory() as temp:
        root = prepare(Path(temp) / "project")
        run(root, "context", "pricing-faq", "--out", str(root / "handoff.md"))
        (root / "faq.md").write_text("149 MXN monthly; see inputs/pricing-current.md.\n")
        (root / "checks.md").write_text("Compared source price, users, and support with FAQ fixture: matches.\n")
        s = run(root, "submit", "pricing-faq", "--output", "faq.md", "--evidence", "checks.md", "--checks", "Compared fixture strings", "--next", "Review FAQ")
        sid = s["submission"]["submission_id"]
        assert run(root, "review", "pricing-faq", "--submission", sid, "--actor", "milo", "--decision", "accept", "--note", "Synthetic review assertion")["status"] == "accepted"
        source = root / "inputs/pricing-current.md"
        source.write_text(source.read_text().replace("149", "179"))
        assert run(root, "show", "pricing-faq")["status"] == "needs_review"
        s = run(root, "refresh", "pricing-faq", "--note", "Price changed; rework required")
        assert s["status"] == "ready" and s["review"] is None
        assert len(list((root / ".context/relay/tasks/pricing-faq/packets").glob("*.json"))) == 2
        print("PASS: Relay context, submission, exact-version review, changed source, and refreshed handoff. No model called.")


if __name__ == "__main__":
    smoke()
