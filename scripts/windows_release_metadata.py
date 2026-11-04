"""Record exact candidate installer bytes; never infer qualification from a build."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
from pathlib import Path

from njit_auditor.desktop_metadata import DESKTOP_VERSION


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installer", type=Path, required=True)
    args = parser.parse_args()
    installer = args.installer
    if installer.name != f"NJIT-Thesis-Auditor-Setup-{DESKTOP_VERSION}.exe":
        raise ValueError("Installer filename/version mismatch")
    if installer.read_bytes()[:2] != b"MZ":
        raise ValueError("Expected Windows executable")
    with installer.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    data = {
        "application": "NJIT Thesis Auditor",
        "edition": "njit",
        "version": DESKTOP_VERSION,
        "filename": installer.name,
        "size_bytes": installer.stat().st_size,
        "sha256": digest,
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "architecture": "x64",
        "build_os": platform.platform(),
        "native_tested": False,
        "windows11_qualified": False,
        "approved": False,
    }
    installer.with_suffix(".json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    (installer.parent / "SHA256SUMS.txt").write_text(
        f"{digest}  {installer.name}\n", encoding="ascii"
    )


if __name__ == "__main__":
    main()
