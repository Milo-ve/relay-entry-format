"""ICM workspace layer on synthetic folders: exclusions, scaffold, budget headings and the request."""
from pathlib import Path
import tempfile
import unittest

from okf_icm.environment import Environment


class IcmBase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = Environment(self.root)

    def write(self, relative, text="# Title\n\nBody.\n"):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}


class ExclusionTests(IcmBase):
    def test_folder_scans_skip_working_and_outputs_but_explicit_paths_do_not(self):
        for name in ("docs/a.md", "docs/working/draft.md", "docs/outputs/final.md", "outputs/top.md"):
            self.write(name)
        items, _ = self.env.scan(["docs"])
        self.assertEqual([i["path"] for i in items], ["docs/a.md"])
        items, _ = self.env.scan(["outputs"])
        self.assertEqual([i["path"] for i in items], ["outputs/top.md"])


if __name__ == "__main__":
    unittest.main()
