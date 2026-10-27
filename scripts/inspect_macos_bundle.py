"""Inspect a native .app, all Mach-O architectures, resources, and ad-hoc signatures."""

from __future__ import annotations

import argparse
import json
import platform
import plistlib
import subprocess
from pathlib import Path

MACHO_MAGIC = {
    b"\xfe\xed\xfa\xce",
    b"\xce\xfa\xed\xfe",
    b"\xfe\xed\xfa\xcf",
    b"\xcf\xfa\xed\xfe",
    b"\xca\xfe\xba\xbe",
    b"\xbe\xba\xfe\xca",
    b"\xca\xfe\xba\xbf",
    b"\xbf\xba\xfe\xca",
}
REQUIRED = (
    "desktop-build-info.json",
    "third-party-licenses/DEPENDENCIES.json",
    "third-party-licenses/Python-LICENSE.txt",
    "third-party-licenses/tcl-LICENSE.txt",
    "third-party-licenses/tk-LICENSE.txt",
    "third-party-licenses/NATIVE-RUNTIME-NOTICES.json",
    "assets/fonts/DejaVuSans.ttf",
    "assets/fonts/DejaVu-LICENSE.txt",
    "data/processed/rules/project_added_rules.json",
    "data/specs/ester_warning_wording_map.json",
    "src/njit_auditor/offline_templates/index.html",
    *[
        "src/njit_auditor/templates/" + name + ".html"
        for name in ("_macros", "about", "base", "help", "job", "problem_group", "rules")
    ],
)


def inspect_bundle(bundle: Path, architecture: str) -> dict:
    if platform.system() != "Darwin":
        raise RuntimeError("Native macOS inspection is required")
    bundle = bundle.resolve(strict=True)
    resources = bundle / "Contents/Resources"
    info = plistlib.loads((bundle / "Contents/Info.plist").read_bytes())
    build = json.loads((resources / "desktop-build-info.json").read_text("utf-8"))
    if build["system"] != "Darwin" or build["architecture"] != architecture:
        raise ValueError("Build provenance differs from the requested architecture")
    if info.get("LSMinimumSystemVersion") != build["macos_build_version"]:
        raise ValueError("The conservative macOS build-host minimum is missing")
    for name in REQUIRED:
        if not (resources / name).is_file():
            raise ValueError(f"Required resource missing: {name}")
    executable = bundle / "Contents/MacOS" / info["CFBundleExecutable"]
    if not executable.is_file():
        raise ValueError("Application launcher missing")
    binaries = {}
    for path in bundle.rglob("*"):
        relative = path.relative_to(bundle)
        if path.is_symlink():
            # PyInstaller macOS bundles legitimately use internal framework links.
            if not path.resolve(strict=True).is_relative_to(bundle):
                raise ValueError("External bundle symlink")
            continue
        if any(p in {".git", "notes", "raw", "private"} for p in relative.parts):
            raise ValueError("Excluded data directory")
        if path.suffix.lower() in {".pdf", ".docx", ".xlsx", ".log", ".env"}:
            raise ValueError("Excluded document/log in application")
        if not path.is_file():
            continue
        with path.open("rb") as stream:
            magic = stream.read(4)
        if magic in MACHO_MAGIC:
            archs = subprocess.check_output(["/usr/bin/lipo", "-archs", str(path)], text=True)
            if architecture not in archs.split():
                raise ValueError(f"Incompatible native dependency: {relative}")
            binaries[str(relative)] = {
                "architectures": archs.split(),
                "load_commands": subprocess.check_output(
                    ["/usr/bin/otool", "-l", str(path)], text=True
                ),
            }
    if not binaries or not any("Python" in name for name in binaries):
        raise ValueError("Bundled CPython runtime missing")
    subprocess.run(
        ["/usr/bin/codesign", "--verify", "--deep", "--strict", str(bundle)],
        check=True,
        capture_output=True,
    )
    return {
        "build": build,
        "minimum_macos": info["LSMinimumSystemVersion"],
        "binaries": binaries,
        "signature_integrity": True,
        "developer_id_verified": False,
        "notarized": False,
        "native_runtime_qualified": False,
        "distribution_approved": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--arch", choices=("arm64", "x86_64"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(
        json.dumps(inspect_bundle(args.bundle, args.arch), indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
