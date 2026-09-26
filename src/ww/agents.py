# SPDX-License-Identifier: GPL-3.0-or-later
"""What each agent integration can do for the operator, beyond plain text.

A workflow declares operator ``choices`` abstractly; how the agent presents
them so the operator can pick with the keyboard depends on the agent.  This
table is core knowledge, not an extension point: an unknown agent gets the
plain-text fallback, which every agent can honour.
"""

from __future__ import annotations

from dataclasses import dataclass

from ww.discovery import normalize_agent
from ww.errors import ConfigurationError


@dataclass(frozen=True)
class ChoiceMechanism:
    """How one agent presents a set of choices to the operator."""

    name: str
    instruction: str


PLAIN_TEXT = ChoiceMechanism(
    "plain text",
    "Present the choices as a numbered list in your reply, exactly in this "
    "order, and ask the operator to answer with the number or the label.",
)

CHOICE_MECHANISMS: dict[str, ChoiceMechanism] = {
    "claudecode": ChoiceMechanism(
        "AskUserQuestion",
        "Present the matter in your reply first, then ask with the "
        "`AskUserQuestion` tool: one short question of a line or two, never the "
        "matter itself, these options in this order with their descriptions, "
        "single select. The operator picks with the keyboard; a free-form "
        'answer through "Other" is a comment, not a choice.',
    ),
    "codex": ChoiceMechanism(
        "request_user_input",
        "Present the matter in your reply first, then ask with "
        "`request_user_input`: one short question of a line or two, never the "
        "matter itself, these options in this order with their descriptions. "
        "The operator picks a number; a free-form answer is a comment, not a "
        "choice.",
    ),
}


@dataclass(frozen=True)
class WaitMechanism:
    """How one agent runs a command that waits for the operator.

    An agent with a background shell keeps its session free while the wait
    runs and hears the result when the command returns; such a wait may be
    long.  Any other agent blocks on the command, so the wait stays under
    its shell timeout.
    """

    background: bool
    wait_seconds: int | None
    instruction: str


FOREGROUND = WaitMechanism(
    False,
    None,
    "The command blocks until it returns; run nothing else while it waits, "
    "and run it again while items remain.",
)

# The environment variable that bounds one wait, and the bound a background
# wait gets: half an hour, long enough for a real session of manual testing,
# short enough that a forgotten wait ends on its own.
WAIT_VARIABLE = "WW_OPERATOR_WAIT"
BACKGROUND_WAIT_SECONDS = 1800

WAIT_MECHANISMS: dict[str, WaitMechanism] = {
    "claudecode": WaitMechanism(
        True,
        BACKGROUND_WAIT_SECONDS,
        "Run the command in the background with your shell tool's "
        "`run_in_background` option and go on with the conversation; its "
        "output reaches you when it returns. While it runs, do not run "
        "commands that change this task, because the wait applies the answers "
        "the moment it ends; `status` and `instruction` are fine. Run it again "
        "while items remain.",
    ),
}


def wait_mechanism(agent: str) -> WaitMechanism:
    """The mechanism for ``agent``; a blocking wait when it has no background."""
    try:
        name = normalize_agent(agent)
    except ConfigurationError:
        # An unknown spelling still gets the fallback every agent can honour.
        return FOREGROUND
    return WAIT_MECHANISMS.get(name, FOREGROUND)


def choice_mechanism(agent: str) -> ChoiceMechanism:
    """The mechanism for ``agent``; plain text when it has no structured one."""
    try:
        name = normalize_agent(agent)
    except ConfigurationError:
        # An unknown spelling still gets the fallback every agent can honour.
        return PLAIN_TEXT
    return CHOICE_MECHANISMS.get(name, PLAIN_TEXT)
