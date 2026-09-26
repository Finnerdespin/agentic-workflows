# SPDX-License-Identifier: GPL-3.0-or-later
"""Strict loading for the normalized ``workflows.yaml`` schema."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml

from ww.errors import ConfigurationError
from ww.extensions import ExtensionRegistry
from ww.runtimes import RUNTIME_INSTRUCTIONS
from ww.task_ids import EXPLICIT_TASK_FORMAT
from ww.workflow_config import (
    DocumentDefinition,
    HandlerDefinition,
    MetadataScope,
    ModeDefinition,
    ProfileDefinition,
    WorkflowConfiguration,
    WorkflowDefinition,
)
from ww.workflow_validation import validate_configuration

from .actions import _parse_hooks
from .steps import _parse_handlers, _parse_step
from .values import (
    _NAME,
    _description,
    _description_items,
    _mapping,
    _name,
    _named_entry,
    _only,
    _optional_agent,
    _optional_string,
    _profile,
    _required_list,
    _string_list,
    _unique,
)


@dataclass(frozen=True)
class YamlConfigurationLoader:
    """The built-in ``workflows.yaml`` notation frontend."""

    path: Path

    def __call__(self) -> WorkflowConfiguration:
        return parse_yaml_configuration(self.path)


def parse_yaml_configuration(path: Path) -> WorkflowConfiguration:
    """Load a normalized configuration without deriving execution behavior.

    Parsing checks the YAML notation's shape. Cross-definition semantics are
    deliberately checked by :func:`validate_configuration` after any frontend
    has produced this same normalized model.
    """
    if not path.is_file():
        raise ConfigurationError(f"workflow configuration not found: {path}")
    return parse_yaml_text(path.read_text(encoding="utf-8"), str(path))


def parse_yaml_text(text: str, source: str = "<string>") -> WorkflowConfiguration:
    """Parse ``workflows.yaml`` notation held in memory, named ``source``."""
    raw = _raw_from_text(text, source)
    if "tasks" in raw:
        raise ConfigurationError("configuration uses legacy 'tasks'; use 'handlers'")
    modes = _parse_modes(raw.get("modes", []))
    profiles = _parse_profiles(raw.get("profiles", {}))
    handlers = _parse_handlers(raw.get("handlers", []))
    workflows_raw = _required_list(raw, "workflows", "configuration")
    global_hooks = _parse_hooks(raw.get("hooks", {}), "global", "hooks")
    handlers_by_name = {handler.name: handler for handler in handlers}
    workflows = tuple(
        _parse_workflow(item, f"workflows[{index}]", handlers_by_name)
        for index, item in enumerate(workflows_raw)
    )
    return WorkflowConfiguration(
        modes,
        profiles,
        handlers,
        global_hooks,
        workflows,
        task_format=_parse_task_format(raw.get("task_format")),
        documents=_parse_documents(raw.get("documents", [])),
    )


def load_configuration(
    path: Path, extensions: ExtensionRegistry | None = None
) -> WorkflowConfiguration:
    """Load and semantically validate the built-in YAML notation."""
    return validate_configuration(YamlConfigurationLoader(path)(), extensions)


def load_modes(
    path: Path, extensions: ExtensionRegistry | None = None
) -> dict[str, ModeDefinition]:
    return {mode.name: mode for mode in load_configuration(path, extensions).modes}


def _raw_from_text(text: str, source: str) -> dict[str, Any]:
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as error:
        raise ConfigurationError(f"invalid YAML in {source}: {error}") from error
    if not isinstance(raw, dict):
        raise ConfigurationError("workflow configuration must be a mapping")
    allowed = {
        "modes",
        "profiles",
        "documents",
        "handlers",
        "hooks",
        "workflows",
        "task_format",
        "tasks",
    }
    unknown = set(raw) - allowed
    if unknown:
        raise ConfigurationError(
            f"configuration has unknown key(s): {', '.join(sorted(unknown))}"
        )
    return raw


def _parse_modes(data: Any) -> tuple[ModeDefinition, ...]:
    if not isinstance(data, list):
        raise ConfigurationError("modes must be a list")
    result = []
    for index, item in enumerate(data):
        mapping = _named_entry(_mapping(item, f"modes[{index}]"), f"modes[{index}]")
        _only(mapping, {"name", "description"}, f"modes[{index}]")
        name = _name(mapping, f"modes[{index}]")
        result.append(
            ModeDefinition(
                name,
                _description_items(mapping.get("description"), f"mode {name!r}"),
            )
        )
    return tuple(result)


def _parse_documents(data: Any) -> tuple[DocumentDefinition, ...]:
    """Parse root ``documents``: named entries with a description and scope."""
    if data is None:
        return ()
    if not isinstance(data, list):
        raise ConfigurationError("documents must be a list")
    result = []
    for index, item in enumerate(data):
        path = f"documents[{index}]"
        mapping = _named_entry(_mapping(item, path), path)
        _only(mapping, {"name", "description", "scope", "path"}, path)
        scope = mapping.get("scope", "task")
        if scope not in {"task", "project"}:
            raise ConfigurationError(f"{path}.scope must be 'task' or 'project'")
        try:
            result.append(
                DocumentDefinition(
                    _name(mapping, path),
                    _description(mapping.get("description"), path),
                    cast(MetadataScope, scope),
                    path=_optional_string(mapping, "path", path),
                )
            )
        except ValueError as error:
            raise ConfigurationError(f"{path}: {error}") from error
    _unique((item.name for item in result), "document")
    return tuple(result)


def _parse_profiles(data: Any) -> tuple[ProfileDefinition, ...]:
    if data is None:
        return ()
    if not isinstance(data, dict):
        raise ConfigurationError("profiles must be a mapping")
    result = []
    for name, description in data.items():
        if not isinstance(name, str) or not _NAME.fullmatch(name):
            raise ConfigurationError("profiles keys must be normalized names")
        if description is not None and (
            not isinstance(description, str) or not description.strip()
        ):
            raise ConfigurationError(f"profiles.{name} must be a string or null")
        result.append(ProfileDefinition(name, description))
    return tuple(result)


def _parse_workflow(
    data: Any, path: str, handlers_by_name: dict[str, HandlerDefinition]
) -> WorkflowDefinition:
    workflow_keys = {
        "name",
        "description",
        "steps",
        "hooks",
        "modes",
        "agent",
        "model",
        "reasoning",
        "handoff",
        "profile",
        "runtime",
        "restartable",
    }
    mapping = _named_entry(
        _mapping(data, path),
        path,
        allowed=workflow_keys,
        ignored={"steps"},
    )
    if "workflows" in mapping:
        raise ConfigurationError(
            f"{path}.workflows defines nested workflows, which are not supported"
        )
    _only(mapping, workflow_keys, path)
    name = _name(mapping, path)
    handoff = mapping.get("handoff", False)
    if not isinstance(handoff, bool):
        raise ConfigurationError(f"{path}.handoff must be true or omitted")
    runtime = mapping.get("runtime")
    if runtime is not None and runtime not in RUNTIME_INSTRUCTIONS:
        raise ConfigurationError(
            f"{path}.runtime must be one of: " + ", ".join(RUNTIME_INSTRUCTIONS)
        )
    restartable = mapping.get("restartable", False)
    if not isinstance(restartable, bool):
        raise ConfigurationError(f"{path}.restartable must be true or false")
    steps_data = _required_list(mapping, "steps", f"workflow {name!r}")
    steps = tuple(
        _parse_step(item, f"{path}.steps[{index}]", handlers_by_name)
        for index, item in enumerate(steps_data)
    )
    return WorkflowDefinition(
        name=name,
        description=_description(mapping.get("description"), f"workflow {name!r}"),
        steps=steps,
        hooks=_parse_hooks(
            mapping.get("hooks", {}), "workflow", f"workflow {name!r} hooks"
        ),
        modes=_string_list(mapping.get("modes", []), f"workflow {name!r} modes"),
        agent=_optional_agent(mapping, "agent", f"workflow {name!r}"),
        model=_optional_string(mapping, "model", f"workflow {name!r}"),
        reasoning=_optional_string(mapping, "reasoning", f"workflow {name!r}"),
        **_profile(mapping, f"workflow {name!r}"),
        handoff=handoff,
        runtime=runtime,
        restartable=restartable,
    )


def _parse_task_format(data: Any) -> str | None:
    if data is None:
        return None
    if not isinstance(data, str) or not data:
        raise ConfigurationError("task_format must be a non-empty string")
    if data == EXPLICIT_TASK_FORMAT:
        return data
    tokens = re.findall(r"\{[^{}]*\}", data)
    if data.count("{") != len(tokens) or data.count("}") != len(tokens):
        raise ConfigurationError("task_format has invalid placeholders")
    unknown = set(tokens) - {"{digit}", "{timestamp}", "{uuid}"}
    if unknown:
        raise ConfigurationError(
            "task_format has unknown placeholder(s): " + ", ".join(sorted(unknown))
        )
    return data

