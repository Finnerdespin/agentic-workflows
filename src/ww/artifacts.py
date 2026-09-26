# SPDX-License-Identifier: GPL-3.0-or-later
"""Rendering for durable agent-produced workflow step artifacts."""

from __future__ import annotations


def render_step_artifact(
    *,
    task_id: str,
    workflow: str,
    step: str,
    step_number: int,
    step_total: int,
    skill: str,
    result: str,
) -> str:
    """Wrap an agent result in the built-in, stable Markdown artifact format."""
    body = _normalize_result(result).rstrip()
    return (
        f"# {task_id} — {step}\n\n"
        "## Workflow context\n\n"
        f"- Workflow: {workflow}\n"
        f"- Step: {step_number} of {step_total}\n"
        f"- Skill: {skill}\n\n"
        "## Result\n\n"
        f"{body}\n"
    )


def _normalize_result(result: str) -> str:
    """Restore line endings when Markdown arrived as one escaped CLI argument."""
    if "\n" in result or "\r" in result:
        return result
    return result.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\r", "\n")
