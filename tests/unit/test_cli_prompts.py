# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for operator confirmations read from the terminal."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from ww.cli.prompts import _confirm_force_next, confirm_interrupted_retry


def _closed_stdin(_prompt: str) -> str:
    raise EOFError


@pytest.mark.parametrize(
    ("confirm", "message"),
    [
        (confirm_interrupted_retry, "Retry cancelled"),
        (_confirm_force_next, "Force cancelled"),
    ],
)
def test_closed_stdin_declines_instead_of_crashing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    confirm: Callable[[], bool],
    message: str,
) -> None:
    monkeypatch.setattr("builtins.input", _closed_stdin)

    assert confirm() is False
    assert f"{message}: explicit confirmation is required." in capsys.readouterr().err
