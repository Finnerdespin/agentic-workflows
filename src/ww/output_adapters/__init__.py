# SPDX-License-Identifier: GPL-3.0-or-later
"""Output adapters bundled with ww."""

from ww.output_adapters.base import OutputAdapter
from ww.output_adapters.json_adapter import JsonOutputAdapter
from ww.output_adapters.markdown import MarkdownOutputAdapter

__all__ = [
    "JsonOutputAdapter",
    "MarkdownOutputAdapter",
    "OutputAdapter",
]
