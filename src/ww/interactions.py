# SPDX-License-Identifier: GPL-3.0-or-later
"""The per-task record of conversations held with the operator.

An interactive step is a conversation the agent holds with the operator in
its own session; ww cannot hear it.  The agent records both sides with
``interact`` as the conversation goes, and ww appends each entry to one file
per task, ``interactions.md``, never rewriting it.  Every entry names the
run and step it belongs to, and the work item when the step is a per-item
stage, so the file reads as the task's whole history of operator involvement
and the conversation of one stage can be read back out of it.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from ww.storage import Storage

INTERACTIONS_FILE = "interactions.md"
_SEPARATOR = " · "
# A heading has time, run, step, and speaker; a per-item stage adds its item.
_FIELDS = 4


@dataclass(frozen=True)
class InteractionEntry:
    """One recorded entry: who said what, in which run, step, and item."""

    at: str
    run_id: str | None
    step: str
    item_id: str | None
    speaker: str
    text: str

    def to_dict(self) -> dict[str, object]:
        return {
            "at": self.at,
            "run_id": self.run_id,
            "step": self.step,
            "item_id": self.item_id,
            "speaker": self.speaker,
            "text": self.text,
        }


class InteractionLog:
    def __init__(self, storage: Storage) -> None:
        self.storage = storage

    def path(self, task_id: str) -> Path:
        return self.storage.runtime_path / "tasks" / task_id / INTERACTIONS_FILE

    def append(
        self,
        task_id: str,
        *,
        run_id: str | None,
        step: str,
        speaker: str,
        text: str,
        at: str,
        item_id: str | None = None,
    ) -> None:
        """Append one entry; the file is created with a title on first use."""
        path = self.path(task_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        fields = [at, run_id or "-", step]
        if item_id is not None:
            fields.append(item_id)
        fields.append(speaker)
        heading = f"## {_SEPARATOR.join(fields)}\n\n"
        body = text.strip() + "\n\n" if text.strip() else ""
        with path.open("a", encoding="utf-8") as handle:
            if handle.tell() == 0:
                handle.write(f"# {task_id} — interactions with the operator\n\n")
            handle.write(heading + body)

    def read(self, task_id: str) -> str:
        path = self.path(task_id)
        return path.read_text(encoding="utf-8") if path.is_file() else ""

    def entries(self, task_id: str) -> tuple[InteractionEntry, ...]:
        """Read the record back as entries, in the order they were appended."""
        result: list[InteractionEntry] = []
        heading: InteractionEntry | None = None
        body: list[str] = []
        for line in self.read(task_id).splitlines():
            parsed = _parse_heading(line)
            if parsed is None:
                body.append(line)
                continue
            if heading is not None:
                result.append(replace(heading, text="\n".join(body).strip()))
            heading, body = parsed, []
        if heading is not None:
            result.append(replace(heading, text="\n".join(body).strip()))
        return tuple(result)

    def remove(self, task_id: str) -> None:
        """Forget a task's record, as part of resetting the task."""
        self.path(task_id).unlink(missing_ok=True)


def _parse_heading(line: str) -> InteractionEntry | None:
    """An entry heading: time, run, step, an optional item, and the speaker."""
    if not line.startswith("## "):
        return None
    fields = line[3:].split(_SEPARATOR)
    if len(fields) not in (_FIELDS, _FIELDS + 1):
        return None
    at, run_id, step = fields[:3]
    item_id = fields[3] if len(fields) > _FIELDS else None
    return InteractionEntry(
        at, None if run_id == "-" else run_id, step, item_id, fields[-1], ""
    )
