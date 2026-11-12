"""Storage behavior that must be identical on every platform."""
import tempfile
import unittest
from pathlib import Path

from okf_icm.storage import atomic_write


class AtomicWriteCase(unittest.TestCase):
    def test_exclusive_refuses_dangling_symlink_without_creating_target(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "missing.md"
            link = Path(temp) / "link.md"
            try:
                link.symlink_to(target)
            except OSError:
                self.skipTest("Symlink creation unavailable")
            with self.assertRaises(FileExistsError):
                atomic_write(link, "must not reach the target\n", exclusive=True)
            self.assertTrue(link.is_symlink())
            self.assertFalse(target.exists())

    def test_writes_lf_bytes_on_every_platform(self):
        with tempfile.TemporaryDirectory() as temp:
            plain = Path(temp) / "plain.md"
            exclusive = Path(temp) / "exclusive.md"
            atomic_write(plain, "a\nb\n")
            atomic_write(exclusive, "a\nb\n", exclusive=True)
            self.assertEqual(plain.read_bytes(), b"a\nb\n")
            self.assertEqual(exclusive.read_bytes(), b"a\nb\n")


if __name__ == "__main__":
    unittest.main()
