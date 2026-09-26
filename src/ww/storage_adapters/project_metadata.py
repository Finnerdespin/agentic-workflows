# SPDX-License-Identifier: GPL-3.0-or-later
"""Project-scoped metadata storage adapters."""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path

from ww.errors import StateError
from ww.locking import FileLocks
from ww.storage_adapters.base import (
    ProjectMetadata,
    ProjectMetadataStorage,
    flatten_metadata,
)


def _decode_project_metadata(raw: object) -> ProjectMetadata:
    return ProjectMetadata(flatten_metadata(raw, "project metadata"))


class FileProjectMetadataStorageAdapter(ProjectMetadataStorage):
    """Store project metadata in ``.ww/metadata.json``."""

    def __init__(self, root: Path) -> None:
        self.path = root / ".ww" / "metadata.json"
        self.locks = FileLocks(root)

    def lock_project_metadata(self) -> AbstractContextManager[None]:
        return self.locks.lock(self.path, purpose="project metadata")

    def read_project_metadata(self) -> ProjectMetadata | None:
        if not self.path.exists():
            return None
        try:
            return _decode_project_metadata(
                json.loads(self.path.read_text(encoding="utf-8"))
            )
        except (OSError, json.JSONDecodeError, ValueError) as error:
            raise StateError(
                f"invalid project metadata {self.path}: {error}"
            ) from error

    def write_project_metadata(self, metadata: ProjectMetadata) -> None:
        self.locks.atomic_write(
            self.path, json.dumps(metadata.to_dict(), indent=2) + "\n"
        )


class MemoryProjectMetadataStorageAdapter(ProjectMetadataStorage):
    """Keep project metadata in memory for tests and embedded callers."""

    def __init__(self) -> None:
        self.metadata: ProjectMetadata | None = None
        self._lock = threading.RLock()

    @contextmanager
    def lock_project_metadata(self) -> Iterator[None]:
        with self._lock:
            yield

    def read_project_metadata(self) -> ProjectMetadata | None:
        return self.metadata

    def write_project_metadata(self, metadata: ProjectMetadata) -> None:
        self.metadata = metadata
