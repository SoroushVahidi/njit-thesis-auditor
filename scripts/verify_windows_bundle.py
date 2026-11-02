"""Verify complete rule modules and exact runtime resources in a Windows bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PyInstaller.archive.readers import CArchiveReader

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    archive = CArchiveReader(str(args.bundle / "NJIT Thesis Auditor.exe"))
    pyz_name = next(name for name in archive.toc if name.endswith(".pyz"))
    modules = archive.open_embedded_archive(pyz_name).toc
    required = {
        "njit_auditor.rules" if p.stem == "__init__" else "njit_auditor.rules." + p.stem
        for p in (ROOT / "src/njit_auditor/rules").glob("*.py")
    }
    assert required <= modules.keys(), sorted(required - modules.keys())
    assert not {"njit_auditor.web_samples", "njit_auditor.review_ledger"} & modules.keys()
    resources = [
        "data/processed/rules/project_added_rules.json",
        "data/specs/ester_warning_wording_map.json",
        "src/njit_auditor/templates/help.html",
        "src/njit_auditor/templates/rules.html",
        "assets/fonts/DejaVuSans.ttf",
        "assets/icons/njit-auditor.ico",
    ]
    for relative in resources:
        assert (args.bundle / "_internal" / relative).read_bytes() == (
            ROOT / relative
        ).read_bytes(), relative
    info = json.loads((args.bundle / "_internal/desktop-build-info.json").read_text())
    assert info["system"] == "Windows" and info["architecture"].lower() in {"amd64", "x86_64"}
    print(
        f"Complete Windows bundle: {len(required)} rule-module files and exact resources verified"
    )


if __name__ == "__main__":
    main()
