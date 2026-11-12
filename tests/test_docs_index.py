"""Keep the agent entry small, the documentation index complete and local links valid."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
# Characters after newline normalization. The entry is read by every session,
# so growth here is paid on each one.
BUDGETS = {ROOT / "AGENTS.md": 2000, DOCS / "INDEX.md": 3000}
LINK = re.compile(r"\]\(([^)\s]+)\)")
EXTERNAL = re.compile(r"(https?:|mailto:|#)")


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def targets(path: Path) -> list[str]:
    return [value for value in LINK.findall(text(path)) if not EXTERNAL.match(value)]


class DocsIndexTest(unittest.TestCase):
    def test_entry_files_stay_within_budget(self):
        for path, budget in BUDGETS.items():
            with self.subTest(path=path.name):
                self.assertLessEqual(len(text(path)), budget)

    def test_entry_points_to_the_index_and_not_to_whole_documents(self):
        entry = text(ROOT / "AGENTS.md")
        self.assertIn("docs/INDEX.md", entry)
        self.assertNotRegex(entry, r"(?im)^read readme\.md")

    def test_every_current_document_is_indexed(self):
        indexed = {value.split("#")[0] for value in targets(DOCS / "INDEX.md")}
        current = {path.name for path in DOCS.glob("*.md")} - {"INDEX.md"}
        self.assertEqual(current - indexed, set(), "Add a line to docs/INDEX.md or move the file to docs/archive/")
        self.assertIn("archive/", indexed)

    def test_relative_links_resolve(self):
        broken = []
        for path in [ROOT / "README.md", ROOT / "AGENTS.md", *sorted(DOCS.rglob("*.md"))]:
            for value in targets(path):
                target = (path.parent / value.split("#")[0]).resolve()
                if not target.exists():
                    broken.append(f"{path.relative_to(ROOT).as_posix()} -> {value}")
        self.assertEqual(broken, [])

    def test_tidy_finds_no_duplicate_orphan_or_broken_link_in_docs(self):
        from okf_icm import tidy
        blocking = {"duplicate-file", "orphan", "broken-link"}
        found = [item for item in tidy.scan(ROOT, ["docs"])["findings"] if item["kind"] in blocking]
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
