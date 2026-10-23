"""Bounded, read-only snapshot of an operator-selected Markdown folder."""
import hashlib
import os
import re
from pathlib import Path
from types import MappingProxyType

MAX_NOTE_BYTES = 64 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024
MAX_FILES = 200
MAX_ENTRIES = 2000


class NotesStore:
    def __init__(self, root):
        root = Path(root)
        if root.is_symlink() or not root.is_dir():
            raise ValueError("La carpeta debe existir y no ser un enlace simbólico")
        root = root.resolve()
        notes, total, entries = {}, 0, 0

        def walk_error(error):
            raise ValueError("No se puede recorrer la carpeta de notas") from error

        for directory, dirs, names in os.walk(root, followlinks=False, onerror=walk_error):
            entries += len(dirs) + len(names)
            if entries > MAX_ENTRIES:
                raise ValueError("Demasiadas entradas: máximo 2000")
            dirs[:] = sorted(d for d in dirs if not d.startswith(".")
                             and not (Path(directory) / d).is_symlink())
            for name in sorted(names):
                path = Path(directory) / name
                if name.startswith(".") or path.suffix.lower() != ".md" or path.is_symlink():
                    continue
                resolved = path.resolve()
                if not resolved.is_relative_to(root) or not resolved.is_file():
                    continue
                key = path.relative_to(root).as_posix()
                with resolved.open("rb") as stream:
                    raw = stream.read(MAX_NOTE_BYTES + 1)
                if len(raw) > MAX_NOTE_BYTES:
                    raise ValueError(f"Nota demasiado grande: {key}")
                total += len(raw)
                if total > MAX_TOTAL_BYTES or len(notes) >= MAX_FILES:
                    raise ValueError("Colección demasiado grande: máximo 200 notas y 2 MiB")
                notes[key] = raw.decode("utf-8")
        self.notes = MappingProxyType(dict(sorted(notes.items())))

    def list_notes(self):
        return {"notes": [{"path": key, "characters": len(text)}
                          for key, text in self.notes.items()],
                "count": len(self.notes), "snapshot": True}

    def read_note(self, path):
        # Exact snapshot key lookup: no client-supplied path is opened.
        if path not in self.notes:
            raise ValueError("Nota desconocida; usa una ruta exacta de list_notes")
        text = self.notes[path]
        return {"path": path, "text": text,
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "untrusted_content": True}

    def search_notes(self, query, limit=5):
        if not isinstance(query, str) or not 1 <= len(query) <= 200:
            raise ValueError("La consulta debe tener entre 1 y 200 caracteres")
        if type(limit) is not int or not 1 <= limit <= 20:
            raise ValueError("limit debe estar entre 1 y 20")
        terms = set(re.findall(r"\w+", query.casefold()))
        if not terms:
            raise ValueError("La consulta necesita palabras")
        matches = []
        for path, text in self.notes.items():
            for number, line in enumerate(text.splitlines(), 1):
                words = set(re.findall(r"\w+", line.casefold()))
                overlap = len(terms & words)
                if overlap:
                    matches.append({"path": path, "line": number,
                                    "snippet": line[:240], "matched_terms": overlap,
                                    "snippet_truncated": len(line) > 240})
        matches.sort(key=lambda m: (-m["matched_terms"], m["path"], m["line"]))
        return {"matches": matches[:limit], "total_matches": len(matches),
                "truncated": len(matches) > limit, "untrusted_content": True}
