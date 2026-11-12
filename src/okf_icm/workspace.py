"""Versioned project state and dependency-aware stage receipts."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile

from . import scaffold
from .storage import ContextError, atomic_write, contained, digest, identifier, json_text, now, read_json, read_text


def initialize(root: Path, name: str, minimal: bool = False) -> dict:
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    destination = root / ".context"
    if destination.exists() or destination.is_symlink():
        raise ContextError(".context already exists; initialization never overwrites an existing workspace.")
    temp = Path(tempfile.mkdtemp(prefix=".context-init-", dir=root))
    try:
        for path, content in scaffold.files(name, minimal).items():
            atomic_write(temp / path, content)
        atomic_write(temp / "config.json", json_text(scaffold.config(name, minimal)))
        (temp / "runs").mkdir()
        temp.rename(destination)
    finally:
        if temp.exists():
            shutil.rmtree(temp)
    return {"workspace": str(destination), "name": name, **({"minimal": True} if minimal else {})}


class Workspace:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.home = contained(self.root, ".context")
        self.config = read_json(contained(self.root, ".context/config.json"))
        if self.config.get("schema_version") != 1:
            raise ContextError("Unsupported workspace schema_version.")
        self.stages = self.config.get("stages", [])
        seen = set()
        if not isinstance(self.stages, list) or not self.stages:
            raise ContextError("A workflow needs at least one stage.")
        for stage in self.stages:
            sid = identifier(stage["id"])
            if sid in seen or not set(stage.get("needs", [])).issubset(seen):
                raise ContextError("Stages must be unique and topologically ordered; dependencies must precede consumers.")
            contained(self.root, stage["contract"])
            seen.add(sid)

    def path(self, relative: str) -> Path:
        return contained(self.root, relative)

    def run_home(self, run: str) -> Path:
        return self.path(f".context/runs/{identifier(run)}")

    def state(self, run: str) -> dict:
        state = read_json(self.path(f".context/runs/{identifier(run)}/state.json"))
        if state.get("schema_version") != 1 or state.get("run_id") != run:
            raise ContextError("Invalid run state identity or version.")
        if set(state.get("stages", {})) != {s["id"] for s in self.stages}:
            raise ContextError("Workflow stages changed; migrate this run explicitly before continuing.")
        return state

    def save(self, run: str, state: dict) -> None:
        state["updated_at"] = now()
        atomic_write(self.run_home(run) / "state.json", json_text(state))

    def event(self, run: str, action: str, **details) -> None:
        path = self.run_home(run) / "events.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"at": now(), "action": action, **details}, ensure_ascii=False) + "\n")

    def start(self, run: str, goal: str, acceptance: list[str]) -> dict:
        home = self.run_home(run)
        if not goal.strip() or not acceptance or any(not x.strip() for x in acceptance):
            raise ContextError("A run needs a goal and at least one nonempty acceptance criterion.")
        # mkdir is exclusive: a second caller cannot replace a run.
        home.mkdir()
        for directory in ("outputs", "packets", "inputs"):
            (home / directory).mkdir()
        atomic_write(home / "brief.md", f"# Goal\n{goal}\n\n# Acceptance\n" + "".join(f"- {x}\n" for x in acceptance))
        atomic_write(home / "handoff.md", "# Handoff\nNew run. No work completed yet.\n")
        state = {"schema_version": 1, "run_id": run, "goal": goal,
                 "stages": {s["id"]: {"status": "pending"} for s in self.stages}}
        self.save(run, state)
        self.event(run, "start", goal=goal)
        return self.status(run)

    def stage(self, sid: str) -> dict:
        for stage in self.stages:
            if stage["id"] == sid:
                return stage
        raise ContextError(f"Unknown stage: {sid}")

    def changes(self, records: list[dict]) -> list[str]:
        changes = []
        for item in records:
            path = self.path(item["path"])
            if not path.is_file() or digest(path) != item["sha256"]:
                changes.append(item["path"])
        return changes

    def status(self, run: str) -> dict:
        state = self.state(run)
        effective = {}
        for stage in self.stages:
            sid = stage["id"]
            saved = state["stages"][sid]
            status = saved["status"]
            if status not in {"pending", "complete", "skipped"}:
                raise ContextError(f"Invalid saved stage status: {status}")
            changed = []
            if status == "complete":
                receipt = saved.get("receipt")
                if not receipt:
                    raise ContextError(f"Complete stage lacks receipt: {sid}")
                changed = self.changes(receipt["inputs"] + receipt["outputs"] + receipt["evidence"])
                if changed:
                    status = "needs_review"
            upstream = [d for d in stage.get("needs", []) if effective[d]["status"] not in {"complete", "skipped"}]
            if upstream and status in {"complete", "skipped"}:
                status = "needs_review"
            effective[sid] = {"status": status, "saved_status": saved["status"],
                              "changed": changed, "unresolved_dependencies": upstream,
                              "reason": saved.get("reason")}
        current = next((sid for sid, value in effective.items() if value["status"] not in {"complete", "skipped"}), None)
        return {"schema_version": 1, "run_id": run, "goal": state["goal"],
                "run_status": "complete" if current is None else "in_progress",
                "current_stage": current, "stages": effective}

    def ready(self, run: str, sid: str) -> None:
        report = self.status(run)
        for dep in self.stage(sid).get("needs", []):
            if report["stages"][dep]["status"] not in {"complete", "skipped"}:
                raise ContextError(f"Dependency {dep} is not current and complete. Resolve or explicitly skip it first.")

    def records(self, paths: list[str]) -> list[dict]:
        values = []
        for path in dict.fromkeys(paths):
            content = read_text(self.root, path)
            if not content.strip():
                raise ContextError(f"Empty output/evidence: {path}")
            values.append({"path": path, "sha256": digest(self.path(path))})
        return values

    def checkpoint(self, run: str, sid: str, packet_id: str, outputs: list[str], evidence: list[str]) -> dict:
        self.ready(run, sid)
        if not outputs:
            raise ContextError("Checkpoint requires at least one output.")
        if self.stage(sid).get("requires_evidence") and not evidence:
            raise ContextError("This stage requires evidence; a file alone does not establish validation.")
        from .packets import load_packet
        packet = load_packet(self, run, packet_id)
        if packet["stage"] != sid:
            raise ContextError("Packet belongs to a different stage.")
        inputs = [{"path": f["path"], "sha256": f["sha256"]} for f in packet["files"] if f["role"] != "continuity"]
        # A produce stage may intentionally edit selected source files. Those
        # paths must be explicitly declared as outputs; all other inputs freeze.
        mutated = set(outputs)
        changed = self.changes([item for item in inputs if item["path"] not in mutated])
        if changed:
            raise ContextError("Packet inputs changed; generate fresh context: " + ", ".join(changed))
        output_records = self.records(outputs)
        evidence_records = self.records(evidence)
        output_hashes = {x["path"]: x["sha256"] for x in output_records}
        for item in inputs:
            if item["path"] in output_hashes:
                item["sha256"] = output_hashes[item["path"]]
        state = self.state(run)
        state["stages"][sid] = {"status": "complete", "receipt": {
            "at": now(), "packet_id": packet_id, "inputs": inputs,
            "outputs": output_records, "evidence": evidence_records,
            "mutated_inputs": sorted({f["path"] for f in packet["files"]} & mutated)}}
        self.save(run, state)
        self.event(run, "checkpoint", stage=sid, packet_id=packet_id)
        return self.status(run)

    def skip(self, run: str, sid: str, reason: str) -> dict:
        self.ready(run, sid)
        if not reason.strip():
            raise ContextError("Skipping requires a reason.")
        state = self.state(run)
        if state["stages"][sid]["status"] == "complete":
            raise ContextError("Do not replace a completed receipt with a skip.")
        state["stages"][sid] = {"status": "skipped", "reason": reason, "at": now()}
        self.save(run, state)
        self.event(run, "skip", stage=sid, reason=reason)
        return self.status(run)
