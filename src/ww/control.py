# SPDX-License-Identifier: GPL-3.0-or-later
"""Core-owned workflow-control inspection helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ww.operations import ChildWorkflowRun, LoopBoundary, WorkflowHandoff

if TYPE_CHECKING:
    from ww.plan import PlanItem


def workflow_transition(item: PlanItem) -> WorkflowHandoff | None:
    return item.operation if isinstance(item.operation, WorkflowHandoff) else None


def child_workflow(item: PlanItem) -> ChildWorkflowRun | None:
    return item.operation if isinstance(item.operation, ChildWorkflowRun) else None


def loop_control(item: PlanItem) -> LoopBoundary | None:
    return item.operation if isinstance(item.operation, LoopBoundary) else None


def is_coordinator(item: PlanItem) -> bool:
    return isinstance(item.operation, (WorkflowHandoff, ChildWorkflowRun, LoopBoundary))
