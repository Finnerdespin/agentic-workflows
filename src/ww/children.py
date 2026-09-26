# SPDX-License-Identifier: GPL-3.0-or-later
"""Run-local child-task records for one level of parent orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from ww.contracts import ChildStatus
from ww.validation import expect_literal


@dataclass(frozen=True)
class ChildTask:
    id: str
    description: str
    workflow: str
    task_id: str
    status: ChildStatus = "pending"
    run_id: str | None = None
    summary: str | None = None
    start_operation_id: str | None = None
    parent_task_id: str | None = None
    # The configured project the child works in; ``None`` means the root.
    project: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "id": self.id,
            "description": self.description,
            "workflow": self.workflow,
            "task_id": self.task_id,
            "status": self.status,
            "run_id": self.run_id,
            "summary": self.summary,
            "start_operation_id": self.start_operation_id,
            "parent_task_id": self.parent_task_id,
            "project": self.project,
        }

    @classmethod
    def from_dict(cls, data: object) -> ChildTask:
        if not isinstance(data, dict):
            raise ValueError("child task must be a mapping")
        required = ("id", "description", "task_id", "status")
        if not all(isinstance(data.get(key), str) and data[key] for key in required):
            raise ValueError("child task fields must be non-empty strings")
        if not isinstance(data.get("workflow"), str):
            raise ValueError("child task workflow must be a string")
        status = expect_literal(data["status"], ChildStatus, "child task status")
        run_id, summary = data.get("run_id"), data.get("summary")
        if run_id is not None and not isinstance(run_id, str):
            raise ValueError("child task run ID must be a string or null")
        if summary is not None and not isinstance(summary, str):
            raise ValueError("child task summary must be a string or null")
        for name in ("start_operation_id", "parent_task_id", "project"):
            if data.get(name) is not None and not isinstance(data[name], str):
                raise ValueError(f"child task {name} must be a string or null")
        return cls(
            id=data["id"],
            description=data["description"],
            workflow=data["workflow"],
            task_id=data["task_id"],
            status=status,
            run_id=run_id,
            summary=summary,
            start_operation_id=data.get("start_operation_id"),
            parent_task_id=data.get("parent_task_id"),
            project=data.get("project"),
        )
