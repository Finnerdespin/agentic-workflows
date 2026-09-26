# SPDX-License-Identifier: GPL-3.0-or-later
"""Contracts for rendering ww command results."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ww.instructions import Instruction
from ww.results import InitializationResult, ResetResult


class OutputAdapter(ABC):
    """Render workflow results for one output representation."""

    @abstractmethod
    def render_instruction(self, instruction: Instruction) -> str:
        """Render an instruction."""

    @abstractmethod
    def render_reset(self, result: ResetResult) -> str:
        """Render a reset outcome."""

    @abstractmethod
    def render_initialization(self, result: InitializationResult) -> str:
        """Render an initialization outcome."""
