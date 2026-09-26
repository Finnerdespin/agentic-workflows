# SPDX-License-Identifier: GPL-3.0-or-later
"""Names and values for workflow variables owned by ww core."""

from __future__ import annotations

from pathlib import Path

TASK_ID = "__task_id"
WORKFLOWS = "__workflows"
TASK_WORKSPACE_DIR = "__task_workspace_dir"
BRANCH_NAMING_STRATEGY = "__branch_naming_strategy"
# The configured project a task works in, its directory, and every configured
# project name.  ``__project_dir`` stays the project's own directory even when
# an extension moves the task workspace, for example into a Git worktree.
PROJECT = "__project"
PROJECT_DIR = "__project_dir"
PROJECTS = "__projects"

CORE_VARIABLE_NAMES = (
    TASK_ID,
    WORKFLOWS,
    TASK_WORKSPACE_DIR,
    PROJECT,
    PROJECT_DIR,
    PROJECTS,
)
OVERRIDABLE_CORE_VARIABLE_NAMES = (TASK_WORKSPACE_DIR,)


def compile_variable_values(
    workflow_names: tuple[str, ...], task_id: str | None
) -> dict[str, str]:
    """Return core values known while a workflow plan is compiled."""
    values = {WORKFLOWS: ",".join(workflow_names)}
    if task_id is not None:
        values[TASK_ID] = task_id
    return values


def runtime_variable_values(
    root: Path,
    task_id: str,
    workspace: str | None = None,
    project: str | None = None,
    projects: tuple[str, ...] = (),
    project_dir: str | None = None,
) -> dict[str, str]:
    """Return core values resolved from current task execution state."""
    directory = (root / workspace).resolve() if workspace else root.resolve()
    return {
        TASK_ID: task_id,
        TASK_WORKSPACE_DIR: str(directory),
        PROJECT: project or "",
        PROJECT_DIR: project_dir or "",
        PROJECTS: ",".join(projects),
    }
