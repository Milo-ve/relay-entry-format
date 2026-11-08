"""Storage behavior that must be identical on every platform."""
import tempfile
import unittest
from pathlib import Path

from okf_icm.storage import atomic_write


class AtomicWriteCase(unittest.TestCase):
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
