"""Native interactive installer + packaged parity + reopen + standard uninstall.

Hosted Windows Server results are recorded as such, never Windows 11 qualification.
Run on an interactive Windows 11 x64 desktop for client-OS qualification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

from validate_desktop_parity import validate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installer", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != "win32" or platform.machine().lower() not in {"amd64", "x86_64"}:
        raise RuntimeError("This test requires native Windows x64")
    from pywinauto import Application
    from win32com.shell import shell, shellcon

    args.output.mkdir(parents=True, exist_ok=True)
    directory = args.output.resolve() / "Custom Install Résumé" / "NJIT Thesis Auditor"
    assert not directory.exists(), "Use a fresh install directory"
    installer = args.installer.resolve()
    ui = Application(backend="uia").start(
        f'"{installer}" /DIR="{directory}" /TASKS="desktopicon" /LANG=english'
    )
    deadline = time.monotonic() + 180
    finished = False
    while time.monotonic() < deadline:
        window = ui.top_window()
        window.wait("visible", timeout=15)
        window.capture_as_image().save(str(args.output / "installer.png"))
        for checkbox in window.descendants(control_type="CheckBox"):
            if (
                "Launch NJIT Thesis Auditor" in checkbox.window_text()
                and checkbox.get_toggle_state()
            ):
                checkbox.toggle()
        finish = window.child_window(title_re=".*Finish.*", control_type="Button")
        if finish.exists(timeout=0.2) and finish.is_enabled():
            finish.click_input()
            finished = True
            break
        for label in [".*Next.*", "^Install$"]:
            button = window.child_window(title_re=label, control_type="Button")
            if button.exists(timeout=0.2) and button.is_enabled():
                button.click_input()
                break
        time.sleep(0.5)
    assert finished, "Graphical installer did not finish"
    exe = directory / "NJIT Thesis Auditor.exe"
    assert exe.is_file()
    programs = Path(shell.SHGetFolderPath(0, shellcon.CSIDL_PROGRAMS, None, 0))
    desktop = Path(shell.SHGetFolderPath(0, shellcon.CSIDL_DESKTOPDIRECTORY, None, 0))
    shortcuts = [programs / "NJIT Thesis Auditor.lnk", desktop / "NJIT Thesis Auditor.lnk"]
    assert all(path.is_file() for path in shortcuts), "Missing installed shortcuts"
    # App-specific firewall rule: retain runner connectivity and OS security controls.
    rule = "NJIT Auditor validation " + str(os.getpid())
    firewall_env = {**os.environ, "NJIT_TEST_RULE": rule, "NJIT_TEST_EXE": str(exe)}
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "New-NetFirewallRule -DisplayName $env:NJIT_TEST_RULE "
            "-Direction Outbound -Program $env:NJIT_TEST_EXE -Action Block | Out-Null",
        ],
        check=True,
        env=firewall_env,
    )
    try:
        validate(exe, args.reference, args.output / "first-launch", args.output / "shared-profile")
        validate(exe, args.reference, args.output / "reopened", args.output / "shared-profile")
    finally:
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Remove-NetFirewallRule -DisplayName $env:NJIT_TEST_RULE",
            ],
            check=True,
            env=firewall_env,
        )
    # Standard registered uninstaller, automated silently after interactive install.
    sentinel = directory.parent / "student-export.txt"
    sentinel.write_text("Preserve user exports", encoding="utf-8")
    subprocess.run(
        [str(directory / "unins000.exe"), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
        check=True,
        timeout=120,
    )
    assert not exe.exists() and all(not path.exists() for path in shortcuts)
    assert sentinel.read_text(encoding="utf-8") == "Preserve user exports"
    workstation = sys.getwindowsversion().product_type == 1
    result = {
        "platform": platform.platform(),
        "windows_edition": platform.win32_edition(),
        "windows11_candidate": workstation and sys.getwindowsversion().build >= 22000,
        "installer_sha256": hashlib.sha256(installer.read_bytes()).hexdigest(),
        "graphical_install": "passed",
        "custom_path": "passed",
        "shortcuts": "passed",
        "first_launch_parity": "passed",
        "reopen_parity": "passed",
        "uninstall_silent": "passed",
        "user_export_preserved": "passed",
        "application_outbound_firewall": "blocked during testing",
        "os_disconnected_test": "manual qualification still required",
        "clean_machine_without_python": "manual qualification still required",
    }
    (args.output / "windows-result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
