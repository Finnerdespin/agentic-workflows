# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path

import pytest

from ww.actions import DefinedAction, Prompt
from ww.errors import ConfigurationError
from ww.plan import compile_workflow_plan
from ww.workflow_config import (
    HandlerDefinition,
    HookDefinition,
    ModeDefinition,
    StepDefinition,
    WorkflowConfiguration,
    WorkflowDefinition,
)
from ww.workflow_validation import validate_configuration


def _configuration(**changes: object) -> WorkflowConfiguration:
    values = {
        "modes": (),
        "profiles": (),
        "handlers": (),
        "global_hooks": (),
        "workflows": (WorkflowDefinition("task", steps=(StepDefinition("work"),)),),
        **changes,
    }
    return WorkflowConfiguration(**values)  # type: ignore[arg-type]


def test_shared_validator_rejects_invalid_programmatic_definitions() -> None:
    configuration = _configuration(
        modes=(ModeDefinition("same"), ModeDefinition("same"))
    )

    with pytest.raises(ConfigurationError, match="duplicate mode"):
        validate_configuration(configuration)


def test_compiler_always_enforces_shared_semantic_validation(tmp_path: Path) -> None:
    configuration = _configuration(
        workflows=(
            WorkflowDefinition(
                "task",
                modes=("missing",),
                steps=(StepDefinition("work"),),
            ),
        )
    )

    with pytest.raises(ConfigurationError, match="unknown mode"):
        compile_workflow_plan(configuration, tmp_path, "task", "codex")


def test_init_is_a_reserved_step_name() -> None:
    configuration = _configuration(
        workflows=(
            WorkflowDefinition(
                "task",
                steps=(StepDefinition("init"), StepDefinition("work")),
            ),
        )
    )

    with pytest.raises(ConfigurationError, match="'init' is reserved"):
        validate_configuration(configuration)


def test_rejects_workflow_boundary_hook_filtered_by_step() -> None:
    configuration = _configuration(
        global_hooks=(
            HookDefinition(
                "before_start_workflow",
                HandlerDefinition(
                    "prepare", action=DefinedAction("prompt", Prompt("Prepare."))
                ),
                step_names=("develop",),
                path="hooks.before_start_workflow[0]",
            ),
        ),
        workflows=(
            WorkflowDefinition(
                "task",
                steps=(StepDefinition("fetch"), StepDefinition("develop")),
            ),
        ),
    )

    with pytest.raises(ConfigurationError, match="cannot filter.*boundary by step"):
        validate_configuration(configuration)


def test_global_workflow_boundary_hook_may_filter_by_workflow() -> None:
    configuration = _configuration(
        global_hooks=(
            HookDefinition(
                "before_start_workflow",
                HandlerDefinition(
                    "prepare", action=DefinedAction("prompt", Prompt("Prepare."))
                ),
                workflow_names=("delivery",),
            ),
        ),
        workflows=(
            WorkflowDefinition(
                "research", steps=(StepDefinition("fetch"), StepDefinition("develop"))
            ),
            WorkflowDefinition("delivery", steps=(StepDefinition("develop"),)),
        ),
    )

    assert validate_configuration(configuration) == configuration


def test_rejects_step_local_before_start_hook() -> None:
    configuration = _configuration(
        workflows=(
            WorkflowDefinition(
                "task",
                steps=(
                    StepDefinition(
                        "develop",
                        hooks=(
                            HookDefinition(
                                "before_start_workflow",
                                HandlerDefinition(
                                    "prepare",
                                    action=DefinedAction("prompt", Prompt("Prepare.")),
                                ),
                                scope="step",
                                path="workflows[0].steps[0].hooks.before_start_workflow[0]",
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )

    with pytest.raises(ConfigurationError, match="workflow boundary hooks belong"):
        validate_configuration(configuration)
