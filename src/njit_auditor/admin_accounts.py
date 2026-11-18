"""Local operator-only administrator account management.

Passwords are accepted only from a TTY prompt by the command-line interface.
"""

from __future__ import annotations

import argparse
import getpass
import hmac
import secrets
import sqlite3
import sys
from collections.abc import Sequence
from typing import Any

from argon2 import PasswordHasher
from argon2.low_level import Type

from njit_auditor.admin_feedback import _connection, _now, normalize_username

_HASHER = PasswordHasher(type=Type.ID)


def _validated_password(password: str) -> str:
    if not 12 <= len(password) <= 1024:
        raise ValueError("Password must contain 12 to 1024 characters.")
    return password


def _display_name(value: str) -> str | None:
    name = value.strip()
    if len(name) > 100 or any(ord(char) < 32 for char in name):
        raise ValueError("Display name must be at most 100 printable characters.")
    return name or None


def create_account(username: str, password: str, display_name: str = "") -> str:
    """Create one account from an operator-supplied password held only in memory."""
    canonical = normalize_username(username)
    name = _display_name(display_name)
    password_hash = _HASHER.hash(_validated_password(password))
    admin_id = secrets.token_urlsafe(16)
    with _connection() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("""INSERT INTO admins(id,username,password_hash,active,created_at,display_name)
            VALUES (?,?,?,1,?,?)""", (admin_id, canonical, password_hash, _now(), name))
    return admin_id


def set_active(username: str, active: bool) -> None:
    canonical = normalize_username(username)
    with _connection() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT id FROM admins WHERE username=?", (canonical,)).fetchone()
        if row is None:
            raise LookupError("Administrator account not found.")
        db.execute("UPDATE admins SET active=? WHERE id=?", (int(active), row["id"]))
        if not active:
            db.execute("DELETE FROM sessions WHERE admin_id=?", (row["id"],))


def reset_password(username: str, password: str) -> None:
    canonical = normalize_username(username)
    password_hash = _HASHER.hash(_validated_password(password))
    with _connection() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT id FROM admins WHERE username=?", (canonical,)).fetchone()
        if row is None:
            raise LookupError("Administrator account not found.")
        db.execute("UPDATE admins SET password_hash=? WHERE id=?", (password_hash, row["id"]))
        db.execute("DELETE FROM sessions WHERE admin_id=?", (row["id"],))


def list_accounts() -> list[dict[str, Any]]:
    with _connection() as db:
        return [dict(row) for row in db.execute(
            "SELECT id,username,active,created_at,display_name FROM admins ORDER BY username"
        )]


def _prompt_password() -> str:
    if not sys.stdin.isatty() or not sys.stderr.isatty():
        raise ValueError("An interactive terminal is required to enter a password.")
    first = getpass.getpass("New administrator password: ")
    second = getpass.getpass("Repeat administrator password: ")
    if not hmac.compare_digest(first, second):
        raise ValueError("Passwords do not match.")
    return _validated_password(first)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="njit-admin", description="Manage local reviewer accounts"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create")
    create.add_argument("username")
    create.add_argument("--display-name", default="")
    for command in ("disable", "enable", "reset"):
        commands.add_parser(command).add_argument("username")
    commands.add_parser("list")
    args = parser.parse_args(argv)
    try:
        if args.command == "create":
            create_account(args.username, _prompt_password(), args.display_name)
            print("Administrator account created.")
        elif args.command == "disable":
            set_active(args.username, False)
            print("Administrator account disabled.")
        elif args.command == "enable":
            set_active(args.username, True)
            print("Administrator account enabled.")
        elif args.command == "reset":
            reset_password(args.username, _prompt_password())
            print("Administrator password reset.")
        else:
            for account in list_accounts():
                state = "active" if account["active"] else "disabled"
                display = account["display_name"] or ""
                print(f"{account['username']}\t{state}\t{account['created_at']}\t{display}")
    except (ValueError, LookupError, sqlite3.IntegrityError, OSError, RuntimeError) as exc:
        if isinstance(exc, sqlite3.IntegrityError):
            print("Administrator account already exists.", file=sys.stderr)
        else:
            print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
