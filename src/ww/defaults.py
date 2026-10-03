# SPDX-License-Identifier: GPL-3.0-or-later
"""Built-in project defaults created by ``ww-agentic-workflows init``."""

from importlib.resources import files

DEFAULT_WORKFLOWS_YAML = """task_format: TASK-{uuid}

modes: []
handlers: []
hooks: {}
workflows: []
"""

DEFAULT_PROJECT_CONFIG_JSON = """{
  "enabled": true,
  "loop_max_times": 3,
  "extensions": {}
}
"""

PROJECT_LAUNCHER = """#!/bin/sh
set -eu
project_root=$(CDPATH= cd "$(dirname "$0")" && pwd)
cd "$project_root"
exec ww-agentic-workflows "$@"
"""

# Windows cannot run the POSIX launcher above, but Git for Windows and MSYS2 ship
# an ``sh`` that can, so it is written on every platform and this one is added
# beside it for cmd.exe and PowerShell.
PROJECT_LAUNCHER_WINDOWS = """@echo off
rem Run ww for this project, whatever directory the caller is in.
cd /d "%~dp0"
ww-agentic-workflows %*
"""

AGENT_INSTRUCTIONS = (
    files("ww.assets").joinpath("agent_instructions.md").read_text(encoding="utf-8")
)
# The skills ``init`` offers to install into each agent directory, by name.
WW_SKILL_NAME = "ww"
SKILLS = {
    name: files("ww.assets").joinpath(f"{name}_skill.md").read_text(encoding="utf-8")
    for name in (WW_SKILL_NAME,)
}


def skill_location(directory: str, name: str) -> str:
    """Where a skill lives inside an agent directory."""
    return f"{directory}/skills/{name}/SKILL.md"
