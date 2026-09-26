# SPDX-License-Identifier: GPL-3.0-or-later
"""Storage adapters for task runs, artifacts, and metadata."""

from ww.storage_adapters.base import (
    ArtifactAddress,
    CommandOutputAddress,
    ProjectMetadata,
    ProjectMetadataStorage,
    TaskArtifactStorage,
    TaskMetadata,
    TaskMetadataStorage,
    TaskRunStorage,
    TaskStorageAdapter,
)
from ww.storage_adapters.filesystem import FileTaskStorageAdapter
from ww.storage_adapters.memory import MemoryTaskStorageAdapter
from ww.storage_adapters.project_metadata import (
    FileProjectMetadataStorageAdapter,
    MemoryProjectMetadataStorageAdapter,
)

__all__ = [
    "ArtifactAddress",
    "CommandOutputAddress",
    "FileProjectMetadataStorageAdapter",
    "FileTaskStorageAdapter",
    "MemoryProjectMetadataStorageAdapter",
    "MemoryTaskStorageAdapter",
    "ProjectMetadata",
    "ProjectMetadataStorage",
    "TaskArtifactStorage",
    "TaskMetadata",
    "TaskMetadataStorage",
    "TaskStorageAdapter",
    "TaskRunStorage",
]
