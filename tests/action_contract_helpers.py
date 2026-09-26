# SPDX-License-Identifier: GPL-3.0-or-later
"""Reusable checks for internal actions; capability behavior needs its own tests."""

from __future__ import annotations

import json
from typing import TypeVar

from ww.actions import Action, ActionRegistry, InstructionContext, ResolutionContext

DefinitionT = TypeVar("DefinitionT")
PlannedT = TypeVar("PlannedT")


def assert_action_contract(
    action: Action[DefinitionT, PlannedT],
    source: dict[str, object],
    resolution: ResolutionContext,
    instruction: InstructionContext,
) -> PlannedT:
    """Check registration and phase/JSON boundaries with real action contexts.

    The caller asserts the returned payload's intended meaning and exercises
    invalid input, real-system execution, and any optional capabilities.
    """
    registry = ActionRegistry()
    registry.register(action)
    definition = action.parse(source, instruction.name, instruction.description, "test")
    action.validate(definition, "test")
    assert all(isinstance(template, str) for template in action.templates(definition))
    planned = action.plan(definition, resolution)
    assert isinstance(planned, action.planned_type)
    encoded = action.encode(planned)
    decoded = action.decode(json.loads(json.dumps(encoded)))
    assert isinstance(decoded, action.planned_type)
    assert action.encode(decoded) == encoded
    assert action.instruction(decoded, instruction) == action.instruction(
        planned, instruction
    )
    return decoded
