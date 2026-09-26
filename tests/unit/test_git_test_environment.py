# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression coverage for the test suite's Git isolation."""

from __future__ import annotations

import subprocess


def test_git_processes_do_not_inherit_commit_signing() -> None:
    result = subprocess.run(
        ("git", "config", "--global", "--get", "--bool", "commit.gpgsign"),
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == "false"
