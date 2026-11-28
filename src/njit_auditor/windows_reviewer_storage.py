"""Validate pre-provisioned, local NTFS storage for the Windows reviewer service."""

from __future__ import annotations

import sqlite3
import stat
from contextlib import ExitStack
from pathlib import Path

import ntsecuritycon
import pywintypes
import win32api
import win32con
import win32file
import win32security


def _principal() -> str:
    token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY)
    try:
        sid, _ = win32security.GetTokenInformation(token, win32security.TokenUser)
        return win32security.ConvertSidToStringSid(sid)
    finally:
        token.Close()


def _check_dacl(path: Path, principal: str, *, directory: bool) -> None:
    sd = win32security.GetNamedSecurityInfo(
        str(path),
        win32security.SE_FILE_OBJECT,
        win32security.OWNER_SECURITY_INFORMATION | win32security.DACL_SECURITY_INFORMATION,
    )
    owner = win32security.ConvertSidToStringSid(sd.GetSecurityDescriptorOwner())
    control, _ = sd.GetSecurityDescriptorControl()
    dacl = sd.GetSecurityDescriptorDacl()
    if (
        owner != principal
        or dacl is None
        or (directory and not control & win32security.SE_DACL_PROTECTED)
    ):
        raise ValueError("Reviewer storage needs a service-owned, protected Windows DACL")
    inherited_by_files = False
    owner_access = False
    for index in range(dacl.GetAceCount()):
        header, *data = dacl.GetAce(index)
        kind, flags = header
        if kind != win32security.ACCESS_ALLOWED_ACE_TYPE or len(data) != 2:
            raise ValueError("Reviewer storage needs a simple owner-only Windows DACL")
        mask, sid = data
        if win32security.ConvertSidToStringSid(sid) != principal:
            raise ValueError("Reviewer storage Windows DACL grants access to another identity")
        if mask & ntsecuritycon.FILE_ALL_ACCESS == ntsecuritycon.FILE_ALL_ACCESS:
            owner_access |= not bool(flags & win32security.INHERIT_ONLY_ACE)
            inherited_by_files |= bool(flags & win32security.OBJECT_INHERIT_ACE)
    if not owner_access or (directory and not inherited_by_files):
        raise ValueError("Reviewer storage Windows DACL must grant the owner inheritable access")


def _check_file(path: Path, principal: str) -> None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return
    if (
        not stat.S_ISREG(info.st_mode)
        or getattr(info, "st_file_attributes") & stat.FILE_ATTRIBUTE_REPARSE_POINT
        or info.st_nlink != 1
    ):
        raise ValueError("Reviewer storage files must be regular unlinked files")
    _check_dacl(path, principal, directory=False)


def validate_storage(path: Path) -> None:
    """Require a local, private directory whose ordinary SQLite children inherit its DACL."""
    try:
        if (
            not path.drive.endswith(":")
            or win32file.GetDriveType(path.anchor) != win32con.DRIVE_FIXED
        ):
            raise ValueError("Reviewer storage requires a local fixed Windows drive")
        if win32api.GetVolumeInformation(path.anchor)[-1] != "NTFS":
            raise ValueError("Reviewer storage requires NTFS")
        for parent in path.parents:
            attributes = getattr(parent.lstat(), "st_file_attributes")
            if attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                raise ValueError("Reviewer storage may not traverse Windows reparse points")
        principal = _principal()
        _check_dacl(path.parent, principal, directory=True)
        for suffix in ("", "-journal", "-wal", "-shm"):
            _check_file(path.with_name(path.name + suffix), principal)
    except (OSError, pywintypes.error) as exc:
        raise ValueError("Could not verify private Windows reviewer storage") from exc


class _PinnedConnection(sqlite3.Connection):
    directory_handles: ExitStack

    def close(self) -> None:
        try:
            super().close()
        finally:
            self.directory_handles.close()


def connect_private(path: Path) -> sqlite3.Connection:
    """Hold the directory chain against rename while SQLite can open sidecars by name."""
    if ".." in path.parts or ":" in path.name:
        raise ValueError("Reviewer storage requires a canonical file path")
    with ExitStack() as stack:
        try:
            for parent in reversed(path.parents):
                handle = win32file.CreateFile(
                    str(parent), ntsecuritycon.FILE_READ_ATTRIBUTES,
                    win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
                    None, win32con.OPEN_EXISTING,
                    win32file.FILE_FLAG_BACKUP_SEMANTICS | win32file.FILE_FLAG_OPEN_REPARSE_POINT,
                    None,
                )
                stack.callback(handle.Close)
                attributes = win32file.GetFileInformationByHandle(handle)[0]
                if attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                    raise ValueError("Reviewer storage may not traverse Windows reparse points")
            validate_storage(path)
        except (OSError, pywintypes.error) as exc:
            raise ValueError("Could not pin private Windows reviewer storage") from exc
        db = sqlite3.connect(path, timeout=10, isolation_level=None, factory=_PinnedConnection)
        db.directory_handles = stack.pop_all()
        return db
