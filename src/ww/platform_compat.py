# SPDX-License-Identifier: GPL-3.0-or-later
"""The POSIX-only primitives ww needs, provided on Windows as well.

ww is developed and supported on POSIX. Three of its primitives have no
Windows equivalent at all, and this module supplies them so the CLI can run
natively instead of requiring WSL:

* ``lock_descriptor`` replaces ``fcntl.flock``. POSIX takes an advisory
  whole-file lock; Windows has no ``flock``, so this uses ``LockFileEx`` over a
  byte range covering the file, which does give true shared *and* exclusive
  locks. ``LockFileEx`` locks are enforced by the OS rather than advisory, but
  ww only ever locks dedicated sidecar files it never reads, so nothing else is
  affected. A handle that is closed releases its lock, which is the property
  ``locking.py`` depends on.

* ``restrict_to_owner`` replaces ``os.fchmod``. POSIX modes have no Windows
  counterpart, so the audit log's owner-only guarantee is expressed as an ACL
  instead. See that function for the exact difference.

* ``raw_terminal`` replaces ``termios``/``tty``, for the redrawing checklist
  prompt. Windows has no termios, and emulating it would mean rewriting the
  key handling, so ``SUPPORTS_RAW_TERMINAL`` is False there and callers fall
  back to the plain-text questions the prompts already implement.

Locks are always taken non-blocking, raising ``BlockingIOError`` when
contended, because ``locking._acquire`` owns the retry loop and its timeout.
"""

from __future__ import annotations

import contextlib
import errno
import importlib
import os
import shutil
import subprocess
import sys
from collections.abc import Iterator, Sequence
from types import ModuleType

WINDOWS = os.name == "nt"

LOCK_SHARED = "shared"
LOCK_EXCLUSIVE = "exclusive"

SUPPORTS_RAW_TERMINAL = not WINDOWS


def posix_module(name: str) -> ModuleType:
    """Import a POSIX-only stdlib module.

    Imported by name rather than with an ``import`` statement so that type
    checking passes on Windows too, where ``fcntl``, ``termios``, ``tty`` and
    ``os.fchmod`` do not exist and mypy resolves their attributes against the
    running platform.
    """
    return importlib.import_module(name)


if WINDOWS:
    import ctypes
    import msvcrt
    from ctypes import wintypes

    _LOCKFILE_FAIL_IMMEDIATELY = 0x00000001
    _LOCKFILE_EXCLUSIVE_LOCK = 0x00000002
    _ERROR_LOCK_VIOLATION = 33
    _ERROR_IO_PENDING = 997
    # Lock from offset zero to the end of the 32-bit length field, so the whole
    # file is covered regardless of how large it grows.
    _WHOLE_FILE = 0xFFFFFFFF

    class _Overlapped(ctypes.Structure):
        """The ``OVERLAPPED`` ``LockFileEx`` needs to identify a byte range.

        ``Internal`` and ``InternalHigh`` are ``ULONG_PTR``, so they are
        pointer-sized rather than ``DWORD``.
        """

        _fields_ = [
            ("Internal", ctypes.c_size_t),
            ("InternalHigh", ctypes.c_size_t),
            ("Offset", wintypes.DWORD),
            ("OffsetHigh", wintypes.DWORD),
            ("Event", wintypes.HANDLE),
        ]

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _lock_file_ex = _kernel32.LockFileEx
    _lock_file_ex.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(_Overlapped),
    ]
    _lock_file_ex.restype = wintypes.BOOL
    _unlock_file_ex = _kernel32.UnlockFileEx
    _unlock_file_ex.argtypes = _lock_file_ex.argtypes
    _unlock_file_ex.restype = wintypes.BOOL


def lock_descriptor(descriptor: int, mode: str) -> None:
    """Take a whole-file lock on ``descriptor``, or raise ``BlockingIOError``."""
    if not WINDOWS:
        fcntl = posix_module("fcntl")

        operation = fcntl.LOCK_EX if mode == LOCK_EXCLUSIVE else fcntl.LOCK_SH
        fcntl.flock(descriptor, operation | fcntl.LOCK_NB)
        return

    handle = msvcrt.get_osfhandle(descriptor)
    if handle == -1:
        raise OSError(errno.EBADF, "bad file descriptor")
    flags = _LOCKFILE_FAIL_IMMEDIATELY
    if mode == LOCK_EXCLUSIVE:
        flags |= _LOCKFILE_EXCLUSIVE_LOCK
    overlapped = _Overlapped()
    locked = _lock_file_ex(
        handle, flags, 0, _WHOLE_FILE, _WHOLE_FILE, ctypes.byref(overlapped)
    )
    if not locked:
        code = ctypes.get_last_error()
        if code in {_ERROR_LOCK_VIOLATION, _ERROR_IO_PENDING}:
            raise BlockingIOError(
                code, os.strerror(errno.EAGAIN), None, errno.EAGAIN
            )
        raise OSError(code, ctypes.FormatError(code))


def configure_console_encoding() -> None:
    """Make stdout and stderr UTF-8 so ww's own output cannot fail to encode.

    A Windows terminal that is not UTF-8 reports a legacy code page such as
    cp1252, and ww's output contains characters that code page cannot encode --
    an em dash, the box-drawing characters in the init banner -- which raises
    UnicodeEncodeError before the command has done any work. This bites hardest
    when output is redirected to a file or a pipe, because that path encodes
    with the locale code page and strict errors, where an interactive console
    would have rendered the characters directly.

    Errors fall back to replacement rather than raising, so an unencodable
    character degrades to ``?`` instead of aborting the command. Only Windows is
    touched: POSIX output is already UTF-8 in practice, and reconfiguring there
    would change the bytes written to a redirected file.
    """
    if not WINDOWS:
        return
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            continue


_POSIX_SHELL_WARNING = (
    "ww: no POSIX shell on PATH, so this shell step ran under cmd.exe.\n"
    "ww: Workflows are written in POSIX shell syntax, which cmd.exe does not\n"
    "ww: understand. Quoting, redirection and && chains will not behave, and\n"
    "ww: a command that should have failed can appear to succeed. Install Git\n"
    "ww: for Windows or MSYS2, which put sh on PATH."
)

_warned_missing_shell = False


def shell_invocation(script: str, args: Sequence[str]) -> list[str]:
    """The argv that runs ``script`` in a shell, with ``args`` as $1, $2, ...

    POSIX uses ``/bin/sh``. Windows has no ``/bin/sh``, and workflows are
    written in POSIX shell syntax, so a POSIX shell found on PATH -- Git for
    Windows or MSYS2, both common on a developer machine -- is used in
    preference to cmd.exe.

    Without one, cmd.exe runs the script. That is only safe for simple
    commands: it cannot pass ``args`` as positional parameters, and it reads
    POSIX syntax as something else. The failure is not reliably visible,
    because a step like ``test -s build && echo ok || echo empty`` runs ``test``
    as an unknown command, takes the ``||`` branch, and still exits zero. So the
    fallback warns once per process rather than pretending the step ran as
    written.
    """
    global _warned_missing_shell
    if not WINDOWS:
        return ["/bin/sh", "-c", script, "ww-command", *args]
    posix = shutil.which("sh")
    if posix is not None:
        return [posix, "-c", script, "ww-command", *args]
    if not _warned_missing_shell:
        _warned_missing_shell = True
        print(_POSIX_SHELL_WARNING, file=sys.stderr)
    return [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/s", "/c", script, *args]


def sync_directory(path: os.PathLike[str] | str) -> None:
    """Flush a directory's entries so a rename into it survives a crash.

    POSIX can ``fsync`` a directory opened read-only. Windows cannot open a
    directory as a file descriptor at all, and has no write-through rename to
    substitute, so this is a no-op there. The property callers actually depend
    on -- a reader never sees a half-written file -- comes from the atomic
    replace itself and is unaffected.
    """
    if WINDOWS:
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


_acl_repaired: set[str] = set()


def restrict_to_owner(descriptor: int, path: os.PathLike[str] | str) -> None:
    """Make ``descriptor``'s file readable and writable by its owner alone.

    POSIX records this as mode ``0o600`` on every append, which also repairs a
    file an older release created under a looser umask.

    Windows has no POSIX modes. The file instead gets an explicit ACL with
    inheritance removed, granting full control only to the current user,
    ``SYSTEM`` and ``Administrators`` -- the Windows equivalent of ``0o600``.
    Rewriting an ACL means spawning ``icacls``, so unlike the POSIX path this
    runs once per file per process rather than on every append. A failure is
    not fatal: ww keeps working, on the directory's inherited ACL.
    """
    if not WINDOWS:
        posix_module("os").fchmod(descriptor, 0o600)
        return

    resolved = os.fspath(path)
    if resolved in _acl_repaired:
        return
    account = os.environ.get("USERNAME")
    if not account:
        return
    grants = [f"{account}:F", "*S-1-5-18:F", "*S-1-5-32-544:F"]
    try:
        subprocess.run(
            ["icacls", resolved, "/inheritance:r", "/grant:r", *grants],
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        print(
            f"ww: could not restrict {resolved} to its owner ({error})",
            file=sys.stderr,
        )
        return
    _acl_repaired.add(resolved)


@contextlib.contextmanager
def raw_terminal(descriptor: int) -> Iterator[None]:
    """Put ``descriptor`` into raw mode for the duration of the block."""
    if not SUPPORTS_RAW_TERMINAL:
        raise OSError("raw terminal mode is not available on this platform")
    termios = posix_module("termios")
    tty = posix_module("tty")

    settings = termios.tcgetattr(descriptor)
    try:
        tty.setraw(descriptor)
        yield
    finally:
        termios.tcsetattr(descriptor, termios.TCSADRAIN, settings)