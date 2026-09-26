# SPDX-License-Identifier: GPL-3.0-or-later
"""Domain errors exposed as clear CLI failures."""


class WwError(Exception):
    """Base error for expected workflow failures."""


class ConfigurationError(WwError):
    """A workflow definition is missing or invalid."""


class StateError(WwError):
    """A task state is missing, invalid, or cannot transition."""


class LockError(WwError):
    """A file lock could not be acquired within the configured wait bound."""
