"""Exercise the installed CLI offline. This does not evaluate any LLM."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from prepare_demo import prepare


def run(root, *args, expected=0):
    result = subprocess.run([sys.executable, "-m", "okf_icm", "--root", str(root), *args],
                            text=True, capture_output=True, cwd=root)
    if result.returncode != expected:
        raise RuntimeError(f"Command failed ({result.returncode}): {args}\n{result.stderr}")
    return json.loads(result.stdout) if result.stdout.strip() else None


def smoke():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "project"
        prepare(root)
        run_id = "portability-test"
        current = root / "inputs/pricing-current.md"
        stages = json.loads((root / ".context/config.json").read_text())["stages"]
        for stage in stages:
            sid = stage["id"]
            packet = run(root, "context", "--run", run_id, "--stage", sid,
                         "--select", "inputs/pricing-current.md", "--format", "json", "--max-chars", "100000")
            output = f".context/runs/{run_id}/outputs/{sid}/report.md"
            path = root / output
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"# {sid}\nSynthetic fixture: 149 MXN, three users, email support.\n", encoding="utf-8")
            args = ["run", "checkpoint", "--run", run_id, "--stage", sid,
                    "--packet", packet["packet_id"], "--output", output]
            if stage.get("requires_evidence"):
                source = current.read_text(encoding="utf-8")
                checks = {"price": "149 MXN" in source, "users": "three users" in source,
                          "support": "email support" in source}
                if not all(checks.values()):
                    raise RuntimeError("Fixture validation failed")
                (root / "observed-checks.json").write_text(json.dumps(checks), encoding="utf-8")
                args += ["--evidence", "observed-checks.json"]
            run(root, *args)
        assert run(root, "status", "--run", run_id)["run_status"] == "complete"
        run(root, "knowledge", "add", "decisions/source-authority", "--title", "Designated fixture source",
            "--type", "Decision", "--body", ".context/project.md", "--source", "Synthetic exercise configuration")
        run(root, "knowledge", "promote", "decisions/source-authority", "--evidence", "observed-checks.json",
            "--reviewer", "process:smoke-test", "--note", "Checked fixture strings with Python assertions", "--confirmed-content")
        run(root, "knowledge", "index")
        assert run(root, "knowledge", "validate")["errors"] == []
        current.write_text(current.read_text(encoding="utf-8").replace("149", "179"), encoding="utf-8")
        report = run(root, "verify", "--run", run_id, expected=1)
        assert all(value["status"] == "needs_review" for value in report["stages"].values())
        print("PASS: installed CLI, six stages, evidence, knowledge promotion and source-change invalidation. No model invoked.")


if __name__ == "__main__":
    smoke()
