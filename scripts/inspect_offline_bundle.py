"""Check the explicit application-resource allowlist in a one-folder build."""

from __future__ import annotations

import argparse
from pathlib import Path

EXPECTED = {
    "src/njit_auditor/offline_templates/index.html",
    "src/njit_auditor/templates/_macros.html",
    "src/njit_auditor/templates/base.html",
    "src/njit_auditor/templates/help.html",
    "src/njit_auditor/templates/job.html",
    "src/njit_auditor/templates/problem_group.html",
    "src/njit_auditor/templates/rules.html",
    "data/processed/rules/project_added_rules.json",
    "data/specs/ester_warning_wording_map.json",
    "assets/fonts/DejaVuSans.ttf",
    "assets/fonts/DejaVu-LICENSE.txt",
}
PRIVATE_EXTENSIONS = {".pdf", ".docx", ".tex", ".bib", ".csv", ".xlsx", ".pem", ".key"}
PRIVATE_PARTS = {
    "private",
    "evaluation",
    "review_ledger",
    "notes",
    "dissertations",
    "credentials",
    "secrets",
}


def inspect_bundle(folder: Path) -> tuple[set[str], set[str], set[str]]:
    internal = folder / "_internal"
    actual: set[str] = set()
    for name in ("src/njit_auditor", "data", "assets"):
        root = internal / name
        if root.exists():
            actual.update(
                path.relative_to(internal).as_posix() for path in root.rglob("*") if path.is_file()
            )
    suspicious = {
        path.relative_to(folder).as_posix()
        for path in folder.rglob("*")
        if path.is_file()
        and (
            path.suffix.lower() in PRIVATE_EXTENSIONS
            or any(part.lower() in PRIVATE_PARTS for part in path.relative_to(folder).parts)
        )
    }
    return EXPECTED - actual, actual - EXPECTED, suspicious


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", type=Path)
    args = parser.parse_args()
    missing, extra, suspicious = inspect_bundle(args.folder)
    if missing or extra or suspicious:
        raise SystemExit(
            f"Bundle resource mismatch: missing={sorted(missing)} "
            f"extra={sorted(extra)} suspicious={sorted(suspicious)}"
        )
    print(f"PASS: {len(EXPECTED)} allowed project resources; no extras or private-file indicators")


if __name__ == "__main__":
    main()
