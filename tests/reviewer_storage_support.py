"""Provision disposable private reviewer storage for cross-platform test fixtures."""

import os
from pathlib import Path


def private_reviewer_directory(path: Path) -> Path:
    path.mkdir(mode=0o700, exist_ok=True)
    if os.name == "nt":
        import ntsecuritycon
        import win32api
        import win32con
        import win32security

        token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY)
        try:
            sid, _ = win32security.GetTokenInformation(token, win32security.TokenUser)
        finally:
            token.Close()
        acl = win32security.ACL()
        acl.AddAccessAllowedAceEx(
            win32security.ACL_REVISION,
            win32security.OBJECT_INHERIT_ACE | win32security.CONTAINER_INHERIT_ACE,
            ntsecuritycon.FILE_ALL_ACCESS,
            sid,
        )
        win32security.SetNamedSecurityInfo(
            str(path),
            win32security.SE_FILE_OBJECT,
            win32security.DACL_SECURITY_INFORMATION
            | win32security.PROTECTED_DACL_SECURITY_INFORMATION,
            None,
            None,
            acl,
            None,
        )
    return path
