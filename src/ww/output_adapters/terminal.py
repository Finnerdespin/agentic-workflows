# SPDX-License-Identifier: GPL-3.0-or-later
"""Terminal presentation shared by init prompts and completion output."""

from __future__ import annotations

import os
import sys


def terminal_accent(text: str) -> str:
    if (
        sys.stdout.isatty()
        and "NO_COLOR" not in os.environ
        and os.environ.get("TERM") != "dumb"
    ):
        return f"\033[1;36m{text}\033[0m"
    return text


def initialization_progress(percent: int) -> str:
    return terminal_accent(f"[{str(percent).rjust(6, '.')}%]")
