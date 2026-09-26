# SPDX-License-Identifier: GPL-3.0-or-later
"""The sheet as seen against the plan: what each answer applies to.

A pending answer waits in the answer sheet.  The stage it applies to is the
plan item with ``ui`` set for that work item, and the answer counts as
applied once that stage's record is completed.  An applied answer is read
back from what the engine recorded: the stage's ``chosen`` field and the
operator's entries for that stage in the interactions file.  One item flow
may declare one ``ui`` stage, so the pairing is unambiguous.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ww.execution_models import ExecutionState, PlanItemExecution
from ww.interactions import InteractionEntry
from ww.items import WorkItem
from ww.plan import PlanItem, WorkflowPlan

from .sheet import Answer


@dataclass(frozen=True)
class SheetRow:
    """One work item on the sheet: its stage, that stage's record, the answer
    waiting for it, and the answer the engine already recorded."""

    work: WorkItem
    stage: PlanItem | None
    record: PlanItemExecution | None
    pending: Answer | None
    applied: Answer | None

    @property
    def processed(self) -> bool:
        return self.record is not None and self.record.status == "completed"

    @property
    def answered(self) -> bool:
        return self.processed or self.pending is not None

    @property
    def status(self) -> str:
        if self.processed:
            return "processed"
        return "answered" if self.pending is not None else "open"

    def to_dict(self) -> dict[str, object]:
        shown = self.applied if self.processed else self.pending
        return {
            **self.work.to_dict(),
            "status": self.status,
            "answer": shown.choice if shown else None,
            "answer_comment": shown.comment if shown else "",
            "answered_at": shown.at if shown else None,
        }


def ui_stage(plan: WorkflowPlan) -> PlanItem | None:
    """The stage whose choices the sheet offers: any ``ui`` stage of the plan."""
    return next((entry for entry in plan.items if entry.ui), None)


def sheet_rows(
    plan: WorkflowPlan,
    state: ExecutionState,
    items: tuple[WorkItem, ...],
    answers: Mapping[str, Answer],
    entries: tuple[InteractionEntry, ...],
) -> tuple[SheetRow, ...]:
    records = {
        record.plan_item_id: record
        for record in (*state.execution_history, *state.item_executions)
    }
    stages = {
        entry.item_id: entry for entry in plan.items if entry.ui and entry.item_id
    }
    rows = []
    for work in items:
        stage = stages.get(work.id)
        record = records.get(stage.id) if stage else None
        applied = (
            _applied(stage, record, state.run_id, entries)
            if stage and record and record.status == "completed"
            else None
        )
        rows.append(SheetRow(work, stage, record, answers.get(work.id), applied))
    return tuple(rows)


def _applied(
    stage: PlanItem,
    record: PlanItemExecution,
    run_id: str | None,
    entries: tuple[InteractionEntry, ...],
) -> Answer:
    """What the engine recorded for a completed stage, read back as an answer."""
    own = [
        entry
        for entry in entries
        if (entry.run_id, entry.step, entry.item_id, entry.speaker)
        == (run_id, stage.name, stage.item_id, "operator")
        and not entry.text.startswith("Choice: ")
    ]
    comment = own[-1].text if own else ""
    at = own[-1].at if own else (record.completed_at or "")
    return Answer(record.chosen, comment, at)
