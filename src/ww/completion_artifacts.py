# SPDX-License-Identifier: GPL-3.0-or-later
"""Persist agent completion artifacts without changing workflow state."""

from __future__ import annotations

from ww.actions import PlannedAction, actions
from ww.artifacts import render_step_artifact
from ww.execution_models import ExecutionState, PlanSnapshot
from ww.plan import PlanItem
from ww.storage_adapters.base import ArtifactAddress, TaskArtifactStorage


def write_completion_artifacts(
    storage: TaskArtifactStorage,
    task_id: str,
    state: ExecutionState,
    snapshot: PlanSnapshot,
    item: PlanItem,
    loop_entry: PlanItem | None,
    artifact: str | None,
) -> tuple[str | None, str | None]:
    """Write the completed item and optional enclosing-loop artifacts."""
    if artifact is None:
        return None, None

    def attribution(plan_item: PlanItem) -> str:
        if not isinstance(plan_item.operation, PlannedAction):
            return "auto"
        action = actions.get(plan_item.kind)
        return action.traits(plan_item.operation.payload).artifact_attribution

    step_paths = tuple(
        dict.fromkeys(
            plan_item.step
            for plan_item in snapshot.plan.items
            if plan_item.phase == "step"
        )
    )

    def rendered(plan_item: PlanItem) -> str:
        return render_step_artifact(
            task_id=task_id,
            workflow=state.workflow,
            step=plan_item.step,
            step_number=step_paths.index(plan_item.step) + 1,
            step_total=len(step_paths),
            skill=attribution(plan_item),
            result=artifact,
        )

    def write(plan_item: PlanItem, content: str) -> str:
        return storage.write_execution_artifact(
            ArtifactAddress(
                task_id,
                state.workflow,
                plan_item.step,
                plan_item.position,
                plan_item.name,
                plan_item.phase,
                run_id=state.run_id,
                step_ordinals=plan_item.step_ordinals,
                loop_iterations=tuple(
                    (loop_id, iteration)
                    for loop_id, iteration in state.loop_iterations
                    if loop_id in plan_item.ancestors
                ),
            ),
            content,
        )

    artifact_reference = None
    if item.artifact:
        artifact_reference = write(
            item, rendered(item) if item.phase == "step" else artifact
        )
    wrapper_artifact_reference = None
    if loop_entry is not None and loop_entry.artifact:
        wrapper_artifact_reference = write(loop_entry, rendered(loop_entry))
    return artifact_reference, wrapper_artifact_reference
