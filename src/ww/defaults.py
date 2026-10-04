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
# an ``sh`` that can, so it is written on every platform and these two are added
# beside it, one per Windows shell.
PROJECT_LAUNCHER_WINDOWS = """@echo off
rem Run ww for this project, whatever directory the caller is in.
where ww-agentic-workflows >nul 2>&1 || (
    echo ww-agentic-workflows is not on PATH. Activate the virtual environment 1>&2
    echo that installed it, then run this again. 1>&2
    exit /b 127
)
cd /d "%~dp0"
ww-agentic-workflows %*
"""

# cmd.exe ends a command at a line break before it applies any quoting, so no
# launcher of its own can carry an argument spanning lines: a multi-line
# artifact or summary arrives as two commands, and the failure surfaces as a
# message about a missing --summary-for-next-step. PowerShell reaches the
# executable without cmd.exe in between, so this one is the way to pass one.
PROJECT_LAUNCHER_POWERSHELL = """#!/usr/bin/env pwsh
# Run ww for this project, whatever directory the caller is in.
# Prefer this over ww.cmd in PowerShell: cmd.exe ends a command at a line
# break, so a multi-line --artifact or --variable cannot pass through it.
$ErrorActionPreference = "Stop"
if (-not (Get-Command ww-agentic-workflows -ErrorAction SilentlyContinue)) {
    $message = "ww-agentic-workflows is not on PATH." +
        " Activate the virtual environment that installed it," +
        " then run this again."
    [Console]::Error.WriteLine($message)
    exit 127
}
Push-Location -LiteralPath $PSScriptRoot
try {
    ww-agentic-workflows @args
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
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
