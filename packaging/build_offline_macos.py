"""Build one native macOS architecture for private testing. Never uploads artifacts."""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require_native_mac(architecture: str) -> None:
    if platform.system() != "Darwin" or platform.machine() != architecture:
        raise RuntimeError("Build on a native Mac running the requested Python architecture")
    translated = subprocess.run(
        ["/usr/sbin/sysctl", "-in", "sysctl.proc_translated"],
        capture_output=True,
        text=True,
        check=False,
    )
    if translated.stdout.strip() == "1":
        raise RuntimeError("Use native hardware/Python; Rosetta builds are not qualified")
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("The pinned builder requires CPython 3.12 with Tcl/Tk")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arch", choices=("arm64", "x86_64"), required=True)
    parser.add_argument("--dmg", action="store_true", help="Also create a local private-test DMG")
    args = parser.parse_args()
    require_native_mac(args.arch)
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip():
        raise RuntimeError("Build from a clean committed worktree")
    environment = ROOT / f".venv-macos-{args.arch}"
    output = ROOT / "dist" / f"macos-{args.arch}"
    if environment.exists() or output.exists():
        raise RuntimeError("Use a fresh build environment and output directory")

    def run(*command: str) -> None:
        subprocess.run(command, cwd=ROOT, check=True)

    run(sys.executable, "-m", "venv", str(environment))
    python = str(environment / "bin/python")
    run(
        python,
        "-m",
        "pip",
        "install",
        "-c",
        "packaging/offline-build-constraints.txt",
        "-e",
        ".",
        "pyinstaller",
    )
    # Fail before freezing if native extensions or Tcl/Tk cannot load.
    run(
        python,
        "-c",
        "import tkinter,pymupdf,pypdfium2; r=tkinter.Tk(); r.withdraw(); r.update(); r.destroy()",
    )
    run(python, "-m", "pip", "freeze", "--all")
    run(
        python,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        "--distpath",
        str(output),
        "--workpath",
        str(ROOT / "build" / f"macos-{args.arch}"),
        "packaging/offline_desktop.spec",
    )
    bundle = output / "NJIT Thesis Auditor.app"
    run(
        python,
        "scripts/inspect_macos_bundle.py",
        "--bundle",
        str(bundle),
        "--arch",
        args.arch,
        "--output",
        str(output / "bundle-inspection.json"),
    )
    freeze = subprocess.check_output([python, "-m", "pip", "freeze", "--all"], text=True)
    (output / "build-dependencies.txt").write_text(freeze, encoding="utf-8")
    if args.dmg:
        # ditto preserves framework symlinks and modes in the PyInstaller app.
        stage = ROOT / "build" / f"dmg-{args.arch}"
        stage.mkdir(exist_ok=False)
        run("/usr/bin/ditto", str(bundle), str(stage / bundle.name))
        (stage / "Applications").symlink_to("/Applications")
        (stage / "PRIVATE-TESTING.txt").write_text(
            "Private development candidate. Distribution is not approved.\n"
            "Copy the app to Applications. Do not disable Gatekeeper.\n"
            "See docs/implementation/macos_desktop.md in the private source checkout.\n",
            encoding="utf-8",
        )
        run(
            "/usr/bin/hdiutil",
            "create",
            "-volname",
            "NJIT Auditor Private Test",
            "-srcfolder",
            str(stage),
            "-format",
            "UDZO",
            "-ov",
            str(output / f"NJIT-Thesis-Auditor-macos-{args.arch}-private.dmg"),
        )
    print(
        json.dumps(
            {
                "bundle": str(bundle),
                "native_runtime_qualified": False,
                "distribution_approved": False,
            }
        )
    )


if __name__ == "__main__":
    main()
