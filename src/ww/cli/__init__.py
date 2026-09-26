# SPDX-License-Identifier: GPL-3.0-or-later
"""Public command-line entry points for ww."""

from .main import main
from .parser import build_parser

__all__ = ["build_parser", "main"]
