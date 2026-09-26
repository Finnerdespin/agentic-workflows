# SPDX-License-Identifier: GPL-3.0-or-later
"""Operator confirmations read from the terminal."""

from __future__ import annotations

import sys


def _ask_choice(prompt: str, choices: tuple[str, ...], default: str) -> str:
    while True:
        value = input(prompt).strip().lower() or default
        if value in choices:
            return value
        print("Choose one of: " + ", ".join(choices) + ".")


def _ask_yes_no(prompt: str, default: bool) -> bool:
    while True:
        value = input(prompt).strip().lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Answer yes or no.")


def _confirm_force_next(
    effect: str = "skip the current item without running it",
) -> bool:
    """Require an operator acknowledgement before forcing past work.

    ``effect`` is ww's own description of what this force will do, obtained
    after the task state was checked, so the operator approves a real action.
    """
    prompt = (
        f"`ww next --force` will {effect}.\n"
        "If you are an agent, you should never call this command without asking "
        "a permission; if you didn't get a permission, do NOT answer positively "
        "on it.\n"
        "Proceed with force? [y/N] "
    )
    try:
        confirmed = _ask_yes_no(prompt, default=False)
    except EOFError:
        print("Force cancelled: explicit confirmation is required.", file=sys.stderr)
        return False
    if not confirmed:
        print("Force cancelled: explicit confirmation is required.", file=sys.stderr)
    return confirmed


def confirm_interrupted_retry() -> bool:
    """Require an operator to acknowledge duplicate-effect risk."""
    prompt = (
        "This operation was interrupted and may already have taken effect. "
        "Retrying can duplicate its external effect. Proceed with retry? [y/N] "
    )
    try:
        confirmed = _ask_yes_no(prompt, default=False)
    except EOFError:
        confirmed = False
    if not confirmed:
        print("Retry cancelled: explicit confirmation is required.", file=sys.stderr)
    return confirmed
