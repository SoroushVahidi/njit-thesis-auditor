"""Native contract for private storage used by the reviewer browser fixture."""

import os
from pathlib import Path

import pytest
from reviewer_storage_support import private_reviewer_directory

from njit_auditor import admin_feedback


@pytest.fixture(autouse=True)
def opt_in_to_windows_storage(monkeypatch) -> None:
    monkeypatch.setenv("NJIT_AUDITOR_REVIEWER_WINDOWS_STORAGE", "1")


def test_reviewer_database_opens_with_private_storage(tmp_path: Path, monkeypatch) -> None:
    database = private_reviewer_directory(tmp_path / "private") / "reviewer.sqlite3"
    monkeypatch.setenv("NJIT_AUDITOR_ADMIN_DB_PATH", str(database))
    connection = admin_feedback._connect()
    connection.close()
    assert database.is_file()
    assert admin_feedback._db_path() == database


@pytest.mark.skipif(os.name != "nt", reason="requires a genuine Windows DACL")
@pytest.mark.parametrize(
    "object_name",
    ["directory", "reviewer.sqlite3", "reviewer.sqlite3-journal",
     "reviewer.sqlite3-wal", "reviewer.sqlite3-shm"],
)
def test_reviewer_database_refuses_an_explicit_non_owner_ace(
    tmp_path: Path,
    monkeypatch,
    object_name: str,
) -> None:
    import ntsecuritycon
    import win32security

    directory = private_reviewer_directory(tmp_path / "private")
    database = directory / "reviewer.sqlite3"
    monkeypatch.setenv("NJIT_AUDITOR_ADMIN_DB_PATH", str(database))
    target = directory if object_name == "directory" else directory / object_name
    if target != directory:
        target.touch()
    flags = win32security.DACL_SECURITY_INFORMATION
    dacl = win32security.GetNamedSecurityInfo(str(target), win32security.SE_FILE_OBJECT, flags)
    acl = dacl.GetSecurityDescriptorDacl()
    everyone = win32security.CreateWellKnownSid(win32security.WinWorldSid, None)
    acl.AddAccessAllowedAce(win32security.ACL_REVISION, ntsecuritycon.FILE_GENERIC_READ, everyone)
    win32security.SetNamedSecurityInfo(
        str(target),
        win32security.SE_FILE_OBJECT,
        flags | win32security.PROTECTED_DACL_SECURITY_INFORMATION,
        None,
        None,
        acl,
        None,
    )
    with pytest.raises(ValueError, match="grants access to another identity"):
        admin_feedback._connect()


@pytest.mark.skipif(os.name == "nt", reason="requires POSIX mode bits")
def test_reviewer_database_still_refuses_posix_group_access(tmp_path: Path, monkeypatch) -> None:
    directory = private_reviewer_directory(tmp_path / "private")
    monkeypatch.setenv("NJIT_AUDITOR_ADMIN_DB_PATH", str(directory / "reviewer.sqlite3"))
    directory.chmod(0o750)
    with pytest.raises(ValueError, match="owner-only"):
        admin_feedback._connect()


@pytest.mark.skipif(os.name != "nt", reason="requires Windows handle-sharing semantics")
def test_windows_reviewer_directory_stays_pinned_until_close(tmp_path: Path, monkeypatch) -> None:
    ancestor = tmp_path / "ancestor"
    ancestor.mkdir()
    directory = private_reviewer_directory(ancestor / "private")
    monkeypatch.setenv("NJIT_AUDITOR_ADMIN_DB_PATH", str(directory / "reviewer.sqlite3"))
    renamed = tmp_path / "renamed"
    db = admin_feedback._connect()
    try:
        assert db.execute("PRAGMA temp_store").fetchone()[0] == 2
        with pytest.raises(OSError):
            ancestor.rename(renamed)
    finally:
        db.close()
    ancestor.rename(renamed)
    assert renamed.is_dir()


@pytest.mark.skipif(os.name != "nt", reason="requires Windows storage")
def test_windows_reviewer_storage_is_explicitly_opt_in(tmp_path: Path, monkeypatch) -> None:
    directory = private_reviewer_directory(tmp_path / "private")
    monkeypatch.setenv("NJIT_AUDITOR_ADMIN_DB_PATH", str(directory / "reviewer.sqlite3"))
    monkeypatch.delenv("NJIT_AUDITOR_REVIEWER_WINDOWS_STORAGE")
    with pytest.raises(ValueError, match="disabled"):
        admin_feedback._connect()


@pytest.mark.skipif(os.name != "nt", reason="requires native DACL inheritance")
def test_windows_reviewer_rejects_unprotected_inherited_directory(
    tmp_path: Path, monkeypatch,
) -> None:
    parent = private_reviewer_directory(tmp_path / "protected")
    inherited = parent / "unprotected"
    inherited.mkdir()
    monkeypatch.setenv("NJIT_AUDITOR_ADMIN_DB_PATH", str(inherited / "reviewer.sqlite3"))
    with pytest.raises(ValueError, match="protected Windows DACL"):
        admin_feedback._connect()
