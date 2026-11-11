"""Distribute bundled instructions, never project data or host configuration."""
from __future__ import annotations

from importlib.resources import files
from io import BytesIO
from pathlib import Path
import shutil
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED

from .storage import ContextError


SKILLS = ("relay-workspace", "ref")


def skill_files(name: str) -> dict[str, bytes]:
    if name not in SKILLS:
        raise ContextError(f"Unknown bundled skill: {name}")
    result = {}

    def collect(directory, prefix=""):
        for item in sorted(directory.iterdir(), key=lambda item: item.name):
            if item.name.startswith(".") or item.name == "__pycache__":
                continue
            relative = prefix + item.name
            if item.is_dir():
                collect(item, relative + "/")
            else:
                result[relative] = item.read_bytes()

    collect(files("okf_icm").joinpath("skills", name))
    if "SKILL.md" not in result:
        raise ContextError(f"Incomplete bundled skill: {name}")
    return result


def install_skill(destination: Path, name: str = "relay-workspace") -> dict:
    contents = skill_files(name)
    destination = destination.expanduser()
    target = destination / name
    if target.exists() or target.is_symlink():
        if target.is_dir() and not target.is_symlink():
            paths = list(target.rglob("*"))
            if not any(path.is_symlink() for path in paths):
                current = {p.relative_to(target).as_posix(): p.read_bytes() for p in paths if p.is_file()}
                if current == contents:
                    return {"skill": str(target / "SKILL.md"), "changed": False}
        raise ContextError("Skill already exists with different contents; preserve it before replacing it.")
    destination.mkdir(parents=True, exist_ok=True)
    staged = Path(tempfile.mkdtemp(prefix=f".{name}-", dir=destination))
    try:
        for relative, content in contents.items():
            path = staged / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        if target.exists() or target.is_symlink():
            raise ContextError("Skill appeared during installation; no existing installation was changed.")
        staged.rename(target)
    finally:
        if staged.exists():
            shutil.rmtree(staged)
    return {"skill": str(target / "SKILL.md"), "changed": True}


def export_skill(path: Path, name: str = "relay-workspace", *, manual: bool = False) -> dict:
    contents = skill_files(name)
    if manual:
        if name != "ref":
            raise ContextError("The manual handoff is available for --name ref only.")
        # One readable file, independent of relative links or an installed skill.
        sections = ["# REF manual handoff\n\nGive this guide and an exported REF packet to the assistant.\n"]
        for relative in ("SKILL.md", "references/workflow.md", "references/manual.md", "assets/return.md"):
            sections.append(f"\n---\n\n## {relative}\n\n" + contents[relative].decode("utf-8"))
        content = "\n".join(sections).encode("utf-8")
    else:
        buffer = BytesIO()
        with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
            for relative, data in contents.items():
                archive.writestr(f"{name}/{relative}", data)
        content = buffer.getvalue()
    path = path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(content)
    return {"written": str(path), "skill": name, "format": "manual" if manual else "zip"}
