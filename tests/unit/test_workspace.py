# SPDX-License-Identifier: GPL-3.0-or-later
"""Working directories persist relative to the root and resolve anywhere."""

from pathlib import Path

from ww.workspace import relative_workspace, resolve_workspace


def test_working_directory_round_trips_through_a_moved_root(tmp_path: Path) -> None:
    root = tmp_path / "checkout"
    worktree = root / "trees" / "TASK-1"
    worktree.mkdir(parents=True)

    stored = relative_workspace(root, worktree)
    assert stored == "trees/TASK-1"

    mounted = tmp_path / "mounted-elsewhere"
    assert resolve_workspace(mounted, stored) == (mounted / "trees/TASK-1").resolve()
    assert resolve_workspace(root, None) is None


def test_directories_outside_the_root_and_legacy_absolute_values_resolve(
    tmp_path: Path,
) -> None:
    root = tmp_path / "checkout"
    sibling = tmp_path / "worktrees" / "TASK-1"
    sibling.mkdir(parents=True)
    root.mkdir()

    assert relative_workspace(root, sibling) == "../worktrees/TASK-1"
    assert resolve_workspace(root, "../worktrees/TASK-1") == sibling.resolve()
    # State written by a release that stored absolute paths still resolves.
    assert resolve_workspace(root, str(sibling)) == sibling.resolve()
    assert relative_workspace(root, root) == "."
    assert resolve_workspace(root, ".") == root.resolve()
