"""Run the ICM layer on synthetic files: scaffold, budget headings and a five-part request, no model calls."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile


def main():
    package = Path(__file__).resolve().parents[1]
    env = dict(os.environ, PYTHONPATH=str(package / "src"))
    with tempfile.TemporaryDirectory(prefix="okf-icm-layout-") as folder:
        root = Path(folder)
        (root / "docs").mkdir()
        (root / "docs/api.md").write_text("# API\n\n## Invoices\n\nPOST /invoices creates an invoice.\n", encoding="utf-8")

        def cli(*args, check=True):
            result = subprocess.run([sys.executable, "-m", "okf_icm", "--root", str(root), *args],
                                    env=env, capture_output=True, text=True)
            if check and result.returncode:
                raise RuntimeError(result.stderr)
            return result

        preview = json.loads(cli("prepare", "--layout", "icm").stdout)["layout"]
        assert not preview["applied"] and not (root / "CLAUDE.md").exists()
        cli("prepare", "--path", "docs", "--path", "sources", "--layout", "icm", "--apply")
        for name in ("CLAUDE.md", "CONTEXT.md", "sources", "examples", "working", "outputs"):
            assert (root / name).exists(), name
        assert "okf-icm context" in (root / ".context/ENTRY.md").read_text()
        assert "with-prompt" in (root / ".context/ENTRY.md").read_text()
        assert not json.loads(cli("prepare", "--layout", "icm", "--apply").stdout)["layout"]["applied"]
        (root / "examples/good.md").write_text("# Good\n\nA short patch with rationale.\n", encoding="utf-8")
        before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
        plain = cli("context", "--select", "docs/api.md#Invoices").stdout
        assert "Context budget" not in plain
        result = cli("context", "--select", "docs/api.md#Invoices", "--example", "examples/good.md",
                     "--with-prompt", "--task", "Add idempotency keys.")
        for text in ("# Request", "## 2. Task\nAdd idempotency keys.", "# Context budget", "## Standing instructions",
                     "## Material", "## Examples", "placed by --example", "policy.md wins"):
            assert text in result.stdout, text
        assert "Request parts still to fill" not in result.stderr
        assert before == {p: p.read_bytes() for p in before}
        assert not (root / ".context/runs").exists() and not (root / ".context/relay").exists()
        assert cli("context", "--select", "docs/api.md", "--with-prompt", "--format", "json", check=False).returncode == 2
    print("icm layer ok")


if __name__ == "__main__":
    main()
