# SPDX-License-Identifier: GPL-3.0-or-later
"""The interaction record reads back as the entries that were appended."""

from pathlib import Path

from ww.interactions import InteractionEntry, InteractionLog
from ww.storage import Storage


def test_entries_round_trip_with_and_without_an_item(tmp_path: Path) -> None:
    log = InteractionLog(Storage(tmp_path))
    log.append(
        "TASK-1",
        run_id="01-task",
        step="discuss",
        speaker="agent",
        text="Proposed:\n\n- a queue\n- a listener",
        at="2026-09-25T10:00:00Z",
    )
    log.append(
        "TASK-1",
        run_id=None,
        step="verify",
        item_id="case-1",
        speaker="operator",
        text="Choice: pass",
        at="2026-09-25T10:01:00Z",
    )
    log.append(
        "TASK-1",
        run_id="01-task",
        step="verify",
        item_id="case-1",
        speaker="end",
        text="",
        at="2026-09-25T10:02:00Z",
    )

    assert log.entries("TASK-1") == (
        InteractionEntry(
            "2026-09-25T10:00:00Z",
            "01-task",
            "discuss",
            None,
            "agent",
            "Proposed:\n\n- a queue\n- a listener",
        ),
        InteractionEntry(
            "2026-09-25T10:01:00Z",
            None,
            "verify",
            "case-1",
            "operator",
            "Choice: pass",
        ),
        InteractionEntry(
            "2026-09-25T10:02:00Z", "01-task", "verify", "case-1", "end", ""
        ),
    )
    text = log.read("TASK-1")
    assert "## 2026-09-25T10:01:00Z · - · verify · case-1 · operator\n" in text


def test_a_missing_record_has_no_entries(tmp_path: Path) -> None:
    assert InteractionLog(Storage(tmp_path)).entries("TASK-9") == ()
