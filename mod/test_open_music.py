"""Tests for the open-music download step of build_sounds.py: python -I mod/test_open_music.py"""
import hashlib
import os
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_sounds as bs  # noqa: E402


def sha(data):
    return hashlib.sha256(data).hexdigest()


class FetchOpen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = pathlib.Path(self.tmp.name)
        self.src = root / "src"
        self.src.mkdir()
        self.cache = str(root / "cache")
        self.base = self.src.as_uri() + "/"
        self.name = "Ossuary 7 - Resolve.mp3"
        (self.src / self.name).write_bytes(b"abc")

    def test_downloads_and_verifies(self):
        path = bs.fetch_open(self.name, {self.name: sha(b"abc")}, self.base, self.cache)
        self.assertEqual(path, os.path.join(self.cache, self.name))
        self.assertEqual(open(path, "rb").read(), b"abc")

    def test_cached_file_needs_no_network(self):
        hashes = {self.name: sha(b"abc")}
        first = bs.fetch_open(self.name, hashes, self.base, self.cache)
        second = bs.fetch_open(self.name, hashes, "file:///does/not/exist/", self.cache)
        self.assertEqual(first, second)

    def test_hash_mismatch_fails_and_leaves_no_cache(self):
        with self.assertRaises(RuntimeError) as ctx:
            bs.fetch_open(self.name, {self.name: sha(b"other")}, self.base, self.cache)
        self.assertIn(self.name, str(ctx.exception))
        self.assertEqual(os.listdir(self.cache), [])

    def test_unpinned_file_fails(self):
        with self.assertRaises(RuntimeError) as ctx:
            bs.fetch_open("X.mp3", {}, self.base, self.cache)
        self.assertIn("--pin-music", str(ctx.exception))

    def test_read_hashes(self):
        path = os.path.join(self.tmp.name, "hashes")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"{sha(b'a')}  Intrepid.mp3\n{sha(b'b')}  Ossuary 7 - Resolve.mp3\n")
        self.assertEqual(bs.read_hashes(path), {"Intrepid.mp3": sha(b"a"), "Ossuary 7 - Resolve.mp3": sha(b"b")})
        self.assertEqual(bs.read_hashes(os.path.join(self.tmp.name, "missing")), {})


if __name__ == "__main__":
    unittest.main()
