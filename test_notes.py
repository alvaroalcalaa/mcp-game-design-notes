import asyncio
import tempfile
import unittest
from pathlib import Path
from mcp import Client
from notes_store import NotesStore, MAX_NOTE_BYTES
from server import create_server
from smoke import check

ROOT = Path(__file__).parent


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.store = NotesStore(ROOT / "example_notes")

    def test_catalog_and_read(self):
        self.assertEqual(self.store.list_notes()["count"], 3)
        note = self.store.read_note("combat.md")
        self.assertIn("20 puntos", note["text"])
        self.assertEqual(len(note["sha256"]), 64)

    def test_search_has_source_line(self):
        match = self.store.search_notes("RESISTENCIA")["matches"][0]
        self.assertEqual((match["path"], match["line"]), ("combat.md", 3))

    def test_no_match(self):
        self.assertEqual(self.store.search_notes("dinosaurio")["total_matches"], 0)

    def test_limit_is_explicit(self):
        r = self.store.search_notes("la", 1)
        self.assertEqual(len(r["matches"]), 1)
        self.assertTrue(r["truncated"])

    def test_unknown_and_traversal_paths(self):
        for path in ["../README.md", "/etc/passwd", "missing.md", "./combat.md"]:
            with self.assertRaises(ValueError):
                self.store.read_note(path)

    def test_invalid_search_inputs(self):
        for query, limit in [("", 5), ("!!!", 5), ("a" * 201, 5), ("a", 0), ("a", 21)]:
            with self.assertRaises(ValueError):
                self.store.search_notes(query, limit)

    def test_snapshot_does_not_change_or_write(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "note.md"
            path.write_text("Original", encoding="utf-8")
            store = NotesStore(directory)
            path.write_text("Modificado", encoding="utf-8")
            self.assertEqual(store.read_note("note.md")["text"], "Original")
            self.assertEqual(path.read_text(), "Modificado")

    def test_ignores_hidden_non_markdown_and_symlinks(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            (root / "good.md").write_text("ok")
            (root / ".private.md").write_text("oculto")
            (root / "secret.txt").write_text("no markdown")
            external = Path(outside) / "out.md"
            external.write_text("fuera")
            try:
                (root / "link.md").symlink_to(external)
                (root / "linked_dir").symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest("Este sistema no permite crear enlaces simbólicos")
            self.assertEqual(NotesStore(root).list_notes()["count"], 1)

    def test_large_note_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "large.md").write_bytes(b"x" * (MAX_NOTE_BYTES + 1))
            with self.assertRaisesRegex(ValueError, "grande"):
                NotesStore(directory)

    def test_invalid_utf8_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "bad.md").write_bytes(b"\xff")
            with self.assertRaises(UnicodeDecodeError):
                NotesStore(directory)


class ProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_in_memory_protocol(self):
        async with asyncio.timeout(10):
            async with Client(create_server(ROOT / "example_notes")) as client:
                result = await client.call_tool("search_notes", {"query": "faro"})
                self.assertEqual(result.structured_content["matches"][0]["path"], "exploration.md")

    async def test_real_stdio_subprocess(self):
        report = await check()
        self.assertTrue(report["read_ok"])
        self.assertEqual(report["transport"], "stdio")


if __name__ == "__main__":
    unittest.main()
