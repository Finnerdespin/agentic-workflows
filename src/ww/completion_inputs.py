# SPDX-License-Identifier: GPL-3.0-or-later
"""Validation for values supplied when completing workflow work."""

from __future__ import annotations

from ww.errors import StateError
from ww.workflow_config import ProvidedVariable


def validate_values(values: tuple[tuple[str, str], ...]) -> dict[str, str]:
    """Return supplied values, rejecting duplicate names."""
    result = dict(values)
    if len(result) != len(values):
        raise StateError("a completion variable can only be supplied once")
    return result


def group_metadata_values(
    values: tuple[tuple[str, str], ...],
) -> dict[str, tuple[str, ...]]:
    """Group ``--metadata`` values by name; an append key may repeat."""
    grouped: dict[str, tuple[str, ...]] = {}
    for name, value in values:
        grouped[name] = (*grouped.get(name, ()), value)
    return grouped


def validate_requested_values(
    values: dict[str, str], requested: tuple[ProvidedVariable, ...]
) -> None:
    """Require exactly the variables requested by a plan item."""
    expected = {item.name for item in requested}
    unknown, missing = set(values) - expected, expected - set(values)
    if unknown:
        raise StateError(
            "unexpected completion variable(s): " + ", ".join(sorted(unknown))
        )
    if missing:
        raise StateError("missing required variable(s): " + ", ".join(sorted(missing)))
