# SPDX-License-Identifier: GPL-3.0-or-later
import json
import subprocess
from pathlib import Path
from stat import S_IMODE

import ww.storage as storage_module
from ww.platform_compat import WINDOWS
from ww.storage import Storage

# Groups that would let someone other than the owner read the log.
_SHARED_GROUPS = ("everyone", "users", "authenticated users", "guests")


def _acl(path: Path) -> list[str]:
    """The access control entries ``icacls`` reports for ``path``."""
    output = subprocess.run(
        ["icacls", str(path)], check=True, capture_output=True, text=True
    ).stdout
    return [line.strip() for line in output.splitlines()[1:] if line.strip()]


def _assert_owner_only(path: Path) -> None:
    """Assert nothing but the owner can read ``path``.

    POSIX records this as mode ``0o600``. Windows has no POSIX modes, so ww
    writes an explicit ACL instead, and the equivalent check is that nothing is
    inherited and no group beyond the owner is granted access.
    """
    if not WINDOWS:
        assert S_IMODE(path.stat().st_mode) == 0o600
        return
    entries = _acl(path)
    assert not [entry for entry in entries if "(I)" in entry], entries
    assert not [
        entry
        for entry in entries
        if any(group in entry.lower() for group in _SHARED_GROUPS)
    ], entries


def test_execution_log_rotation_retains_a_bounded_history(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(storage_module, "EXECUTION_LOG_MAX_BYTES", 80)
    monkeypatch.setattr(storage_module, "EXECUTION_LOG_RETENTION", 2)
    storage = Storage(tmp_path)

    for invocation in range(4):
        storage.append_log({"invocation_id": str(invocation), "detail": "x" * 40})

    logs = tmp_path / ".ww"
    assert json.loads((logs / "executions.jsonl").read_text())["invocation_id"] == "3"
    assert json.loads((logs / "executions.jsonl.1").read_text())["invocation_id"] == "2"
    assert json.loads((logs / "executions.jsonl.2").read_text())["invocation_id"] == "1"
    assert not (logs / "executions.jsonl.3").exists()


def test_execution_logs_are_owner_readable_even_when_an_older_log_is_not(
    tmp_path: Path,
) -> None:
    storage = Storage(tmp_path)
    log = tmp_path / ".ww" / "executions.jsonl"
    log.parent.mkdir(parents=True)
    log.write_text('{"legacy": true}\n', encoding="utf-8")
    log.chmod(0o644)

    storage.append_log({"invocation_id": "new"})

    _assert_owner_only(log)
