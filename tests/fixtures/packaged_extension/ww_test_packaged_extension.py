# SPDX-License-Identifier: GPL-3.0-or-later
from ww.extensions.api import Extension, ExtensionHandler, ExtensionResult


def _record(context):
    context.store.write_text("installed.txt", context.operation_id or "missing")
    return ExtensionResult(True, output="installed extension ran")


EXTENSION = Extension(
    vendor="acme",
    name="packaged",
    version="1.2.3",
    description="A separately installed test extension.",
    handlers=(ExtensionHandler("record", _record),),
)
