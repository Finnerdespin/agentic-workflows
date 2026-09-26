# SPDX-License-Identifier: GPL-3.0-or-later
"""Durable, namespaced state for one extension.

Every extension gets ``.ww/ext/<vendor>/<name>/`` and reaches it only through
this object. Two properties matter:

* **Data lives outside the extension's source.** A pip-installed extension
  cannot write next to its own module, and one vendored into ``ext/`` should not
  put runtime state in the working tree. ``.ww/`` is already gitignored.
* **Writes use a per-file project lock.** Writes to the same store file are
  serialized, and replacement writes are atomic for unlocked readers.
  ``update_text`` keeps the lock across a complete read–modify–write sequence;
  separate reads and writes do not form one transaction.

The surface is narrow on purpose: an extension that could name arbitrary paths
could write anywhere in the project.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from ww.errors import ConfigurationError
from ww.locking import FileLocks


class ExtensionStore:
    """Read and write files under one extension's private directory."""

    def __init__(self, root: Path, identifier: str) -> None:
        self.root = Path(root)
        self.identifier = identifier
        self.directory = self.root / ".ww" / "ext" / identifier
        self._locks = FileLocks(root)

    def path(self, name: str) -> Path:
        """Return the absolute path of ``name`` inside this extension's store."""
        if not name or name.startswith(".") or "/" in name or "\\" in name:
            raise ConfigurationError(
                f"extension store file name must be a plain file name: {name!r}"
            )
        return self.directory / name

    def append_line(self, name: str, line: str) -> None:
        self._locks.append_line(self.path(name), line)

    def write_text(self, name: str, content: str) -> None:
        path = self.path(name)
        purpose = f"extension store {self.identifier}/{name}"
        with self._locks.lock(path, purpose=purpose):
            self._locks.atomic_write(path, content)

    def update_text(self, name: str, update: Callable[[str | None], str]) -> str:
        """Atomically update one file while holding its lock across the read.

        ``write_text`` protects readers from partial files, but callers that
        derive new content from old content need this operation to avoid lost
        updates. If ``update`` raises or returns a non-string, the file is left
        unchanged.
        """
        path = self.path(name)
        purpose = f"extension store {self.identifier}/{name}"
        with self._locks.lock(path, purpose=purpose):
            current = path.read_text(encoding="utf-8") if path.is_file() else None
            content = update(current)
            if not isinstance(content, str):
                raise TypeError("extension store update must return a string")
            self._locks.atomic_write(path, content)
            return content

    def read_text(self, name: str) -> str | None:
        path = self.path(name)
        return path.read_text(encoding="utf-8") if path.is_file() else None

    def read_lines(self, name: str) -> tuple[str, ...]:
        content = self.read_text(name)
        return tuple(content.splitlines()) if content else ()
