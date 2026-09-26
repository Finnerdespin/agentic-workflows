# SPDX-License-Identifier: GPL-3.0-or-later
"""Behavioral contract for project metadata storage adapters."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from ww.errors import StateError
from ww.storage_adapters import (
    FileProjectMetadataStorageAdapter,
    MemoryProjectMetadataStorageAdapter,
    ProjectMetadata,
    ProjectMetadataStorage,
)


@pytest.fixture(params=("memory", "filesystem"))
def adapter(request: pytest.FixtureRequest, tmp_path: Path) -> ProjectMetadataStorage:
    factories: dict[str, Callable[[], ProjectMetadataStorage]] = {
        "memory": MemoryProjectMetadataStorageAdapter,
        "filesystem": lambda: FileProjectMetadataStorageAdapter(tmp_path),
    }
    return factories[request.param]()


def test_project_metadata_round_trips(
    adapter: ProjectMetadataStorage,
) -> None:
    metadata = ProjectMetadata((("environments.staging.url", "https://example.com"),))

    assert adapter.read_project_metadata() is None
    adapter.write_project_metadata(metadata)

    assert adapter.read_project_metadata() == metadata


def test_filesystem_project_metadata_uses_nested_json(tmp_path: Path) -> None:
    adapter = FileProjectMetadataStorageAdapter(tmp_path)
    adapter.write_project_metadata(ProjectMetadata((("github.owner", "openai"),)))

    assert (tmp_path / ".ww" / "metadata.json").read_text(encoding="utf-8") == (
        '{\n  "github": {\n    "owner": "openai"\n  }\n}\n'
    )


def test_corrupt_project_metadata_raises_state_error(tmp_path: Path) -> None:
    path = tmp_path / ".ww" / "metadata.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"github": {}}', encoding="utf-8")

    with pytest.raises(StateError, match="project metadata mappings cannot be empty"):
        FileProjectMetadataStorageAdapter(tmp_path).read_project_metadata()
