# SPDX-License-Identifier: GPL-3.0-or-later
"""Durable task and project metadata publication.

A completing item declares metadata values.  They are validated while the item
is still in progress, recorded on the run as an intent together with the
completion, and only then projected into the metadata stores.  A crash between
the commit and the projection leaves a retriable intent rather than a metadata
value that claims a completion which did not happen.
"""

from __future__ import annotations

from dataclasses import replace

from ww.errors import StateError
from ww.execution_models import (
    ExecutionState,
    PlanSnapshot,
    ProjectMetadataPublication,
)
from ww.plan import PlanItem
from ww.run_coordination import RunLifecycle
from ww.storage_adapters import (
    ProjectMetadata,
    ProjectMetadataStorage,
    TaskMetadata,
    TaskStorageAdapter,
)
from ww.storage_adapters.base import MetadataLeaf, append_metadata_leaf
from ww.workflow_config import SavedMetadata


class MetadataPublisher:
    def __init__(
        self,
        tasks: TaskStorageAdapter,
        project_store: ProjectMetadataStorage,
        lifecycle: RunLifecycle,
    ) -> None:
        self.tasks = tasks
        self.project_store = project_store
        self.lifecycle = lifecycle

    def values(self, task_id: str) -> dict[str, str]:
        """Return task and project metadata as interpolation values."""
        task = self.tasks.read_task_metadata(task_id)
        project = self.project_store.read_project_metadata()
        return {
            **(task.interpolation_values if task is not None else {}),
            **(project.interpolation_values if project is not None else {}),
        }

    def prepare(
        self,
        task_id: str,
        state: ExecutionState,
        item: PlanItem,
        task_metadata: dict[str, MetadataLeaf],
        project_metadata: dict[str, MetadataLeaf],
    ) -> tuple[TaskMetadata | None, ProjectMetadataPublication | None]:
        """Validate metadata and build the durable intents for one completion."""
        updated_task_metadata = None
        if task_metadata:
            current = self.tasks.read_task_metadata(task_id) or TaskMetadata(task_id)
            merged = _merge_metadata(dict(current.values), task_metadata)
            try:
                updated_task_metadata = TaskMetadata(task_id, tuple(merged.items()))
            except ValueError as error:
                raise StateError(str(error)) from error
        if not project_metadata:
            return updated_task_metadata, None
        # This snapshot is a conflict precondition, not a lock held across the
        # task commit.  Holding the project lock would reintroduce an
        # early-publication window and block unrelated producers.
        current_project = (
            self.project_store.read_project_metadata() or ProjectMetadata()
        )
        project_values = tuple(project_metadata.items())
        try:
            # Reject an invalid shape while the producing item is still in
            # progress; malformed input must not become a durable intent that
            # no normal completion can correct.
            ProjectMetadata(
                tuple(
                    _merge_metadata(
                        dict(current_project.values), project_metadata
                    ).items()
                )
            )
        except ValueError as error:
            raise StateError(str(error)) from error
        existing_project = dict(current_project.values)
        return (
            updated_task_metadata,
            ProjectMetadataPublication(
                state.item_executions[state.cursor].operation_id or item.id,
                project_values,
                tuple(
                    # An append key merges onto whatever exists at publication
                    # time, so it records no snapshot to compare against.
                    (
                        key,
                        None
                        if isinstance(value, tuple)
                        else _scalar(existing_project.get(key)),
                    )
                    for key, value in project_values
                ),
            ),
        )

    def reconcile(
        self, state: ExecutionState, snapshot: PlanSnapshot
    ) -> tuple[ExecutionState, PlanSnapshot]:
        """Project committed metadata intents without exposing uncommitted data."""
        if state.pending_task_metadata:
            metadata = TaskMetadata(state.task_id, state.pending_task_metadata)
            self.tasks.write_task_metadata(metadata)
            state = replace(state, pending_task_metadata=())
            self.lifecycle.commit(state, snapshot)

        publication = state.pending_project_metadata
        if publication is None:
            return state, snapshot
        with self.project_store.lock_project_metadata():
            current = self.project_store.read_project_metadata() or ProjectMetadata()
            existing = dict(current.values)
            expected = dict(publication.expected_values)
            supplied = dict(publication.values)
            desired = {
                key: (
                    append_metadata_leaf(existing.get(key), value)
                    if isinstance(value, tuple)
                    else value
                )
                for key, value in supplied.items()
            }
            # An append key merges onto whatever is there, so it cannot conflict.
            conflicts = [
                key
                for key, value in desired.items()
                if not isinstance(supplied[key], tuple)
                and existing.get(key) != value
                and existing.get(key) != expected[key]
            ]
            if conflicts:
                raise StateError(
                    "project metadata publication conflict for operation "
                    f"{publication.operation_id}: " + ", ".join(sorted(conflicts))
                )
            if any(existing.get(key) != value for key, value in desired.items()):
                try:
                    self.project_store.write_project_metadata(
                        ProjectMetadata(tuple({**existing, **desired}.items()))
                    )
                except ValueError as error:
                    # The source operation is already durable, so a shape
                    # change made by another producer cannot be rolled back.
                    # Keep the intent for a retry after the conflicting
                    # project metadata has been resolved.
                    raise StateError(
                        "project metadata publication conflict for operation "
                        f"{publication.operation_id}: incompatible metadata shape; "
                        "resolve the conflicting project metadata and retry"
                    ) from error
        # A crash after the write but before this commit is harmless: the next
        # reconciliation recognizes the desired values and only clears intent.
        state = replace(state, pending_project_metadata=None)
        self.lifecycle.commit(state, snapshot)
        return state, snapshot


def validate_metadata_values(
    values: dict[str, tuple[str, ...]], requested: tuple[SavedMetadata, ...]
) -> tuple[dict[str, MetadataLeaf], dict[str, MetadataLeaf]]:
    """Split supplied metadata by scope after checking it against the request.

    A scalar key takes exactly one value.  An ``append`` key may be omitted
    or repeated; its values are appended to the stored list on publication.
    """
    by_name = {item.name: item for item in requested}
    required = {name for name, item in by_name.items() if not item.append}
    unknown, missing = set(values) - set(by_name), required - set(values)
    scopes = {item.scope for item in requested}
    if not scopes:
        label = "task metadata"
    elif len(scopes) == 1:
        label = f"{next(iter(scopes))} metadata"
    else:
        label = "metadata"
    if unknown:
        raise StateError(f"unexpected {label} value(s): " + ", ".join(sorted(unknown)))
    if missing:
        raise StateError(
            f"missing required {label} value(s): " + ", ".join(sorted(missing))
        )
    repeated = sorted(
        name
        for name, supplied in values.items()
        if len(supplied) > 1 and name in required
    )
    if repeated:
        raise StateError(
            f"{label} value(s) supplied more than once: " + ", ".join(repeated)
        )
    task: dict[str, MetadataLeaf] = {}
    project: dict[str, MetadataLeaf] = {}
    for name, supplied in values.items():
        declared = by_name[name]
        target = project if declared.scope == "project" else task
        target[declared.key] = supplied if declared.append else supplied[0]
    return task, project


def _merge_metadata(
    current: dict[str, MetadataLeaf], supplied: dict[str, MetadataLeaf]
) -> dict[str, MetadataLeaf]:
    """Replace scalar keys; append list keys onto what is stored."""
    merged = dict(current)
    for key, value in supplied.items():
        merged[key] = (
            append_metadata_leaf(current.get(key), value)
            if isinstance(value, tuple)
            else value
        )
    return merged


def _scalar(value: MetadataLeaf | None) -> str | None:
    return value if isinstance(value, str) else None
