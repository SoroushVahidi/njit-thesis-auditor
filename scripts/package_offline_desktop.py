"""Create a Windows portable ZIP and disabled release record after a native build."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import struct
import zipfile
from pathlib import Path

from njit_auditor.desktop_metadata import DESKTOP_VERSION


def package_windows(bundle: Path, output: Path) -> dict[str, object]:
    if platform.system() != "Windows" or platform.machine().lower() not in {"amd64", "x86_64"}:
        raise RuntimeError("A native Windows x64 build host is required; no cross-packaging")
    exe = bundle / "NJIT Thesis Auditor.exe"
    header = exe.read_bytes()
    if header[:2] != b"MZ" or len(header) < 64:
        raise ValueError("The launcher is not a Windows executable")
    offset = struct.unpack_from("<I", header, 0x3C)[0]
    if (
        header[offset : offset + 4] != b"PE\0\0"
        or struct.unpack_from("<H", header, offset + 4)[0] != 0x8664
    ):
        raise ValueError("The launcher is not a Windows x64 PE executable")
    info = json.loads((bundle / "_internal/desktop-build-info.json").read_text("utf-8"))
    if info.get("system") != "Windows" or info.get("version") != DESKTOP_VERSION:
        raise ValueError("Build provenance does not match the Windows candidate")
    files = sorted(bundle.rglob("*"))
    for path in files:
        relative = path.relative_to(bundle)
        if path.is_symlink() or any(
            p in {".git", "notes", "raw", "private"} for p in relative.parts
        ):
            raise ValueError("Bundle contains a link or excluded data directory")
        if path.suffix.lower() in {".pdf", ".docx", ".xlsx", ".log", ".env"}:
            raise ValueError("Bundle contains an excluded document or log")
    if not (bundle / "READ-ME-FIRST.txt").is_file():
        raise ValueError("Student installation instructions are missing")
    output.mkdir(parents=True, exist_ok=True)
    filename = f"NJIT-Thesis-Auditor-{DESKTOP_VERSION}-windows-x64.zip"
    archive = output / filename
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as zipped:
        for path in files:
            if path.is_file():
                zipped.write(path, Path("NJIT Thesis Auditor") / path.relative_to(bundle))
    with archive.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    # The build tool intentionally cannot certify native smoke tests or approval.
    record = {
        "enabled": False,
        "preview": False,
        "version": DESKTOP_VERSION,
        "filename": filename,
        "size_bytes": archive.stat().st_size,
        "sha256": digest,
        "url": "",
        "source_commit": info.get("commit"),
        "windows_versions": ["Windows 10", "Windows 11"],
        "native_windows_build_verified": True,
        "native_tested_windows_versions": [],
        "public_download_verified": False,
        "verified_at": "",
        "approved_for_distribution": False,
        "licensing_reviewed": False,
        "license_basis": "",
    }
    (output / (filename + ".sha256")).write_text(f"{digest}  {filename}\n", encoding="ascii")
    (output / (filename + ".json")).write_text(json.dumps(record, indent=2) + "\n", "utf-8")
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(package_windows(args.bundle, args.output), indent=2))


if __name__ == "__main__":
    main()
