"""Run the knowledge-first path on synthetic sources without model calls or task state."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile


def main():
    package = Path(__file__).resolve().parents[1]
    env = dict(os.environ, PYTHONPATH=str(package / "src"))
    with tempfile.TemporaryDirectory(prefix="okf-icm-environment-") as folder:
        root = Path(folder)
        (root / "sources").mkdir()
        source = root / "sources/offer.md"
        source.write_text("# Synthetic offer\n\nA process diagnosis.\n\n## Scope\n\nOne interview and a report. No price has been agreed.\n", encoding="utf-8")
        def cli(*args):
            result = subprocess.run([sys.executable, "-m", "okf_icm", "--root", str(root), *args],
                                    env=env, capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(result.stderr)
            return result.stdout
        assert json.loads(cli("prepare", "--path", "sources"))["applied"] is False
        assert not (root / ".context").exists()
        cli("prepare", "--path", "sources", "--apply")
        assert "offer.md" in cli("browse")
        assert json.loads(cli("find", "interview", "--format", "json"))["status"] == "candidates"
        assert "No price has been agreed" in cli("read", "sources/offer.md#Scope")
        before = {p: p.read_bytes() for p in (root / ".context").rglob("*") if p.is_file()}
        packet = json.loads(cli("context", "--select", "sources/offer.md#Scope", "--format", "json"))
        assert packet["schema_version"] == 2 and packet["kind"] == "knowledge-context"
        assert before == {p: p.read_bytes() for p in before}
        assert not (root / ".context/runs").exists()
        assert not (root / ".context/relay").exists()
        source.write_text(source.read_text() + "\nA workshop is now included.\n", encoding="utf-8")
        assert json.loads(cli("find", "workshop", "--format", "json"))["matches"][0]["changed_since_prepare"]
        cli("prepare", "--path", "sources", "--apply")
        assert not json.loads(cli("prepare", "--path", "sources", "--apply"))["applied"]
        assert json.loads(cli("knowledge", "validate"))["errors"] == []
    print("PASS: source maps, draft references, search, section reading, task-free context and source updates. No model called.")


if __name__ == "__main__":
    main()
