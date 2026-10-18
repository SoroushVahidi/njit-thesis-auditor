"""Synthetic-only fallback probe for AnonPDF at upstream commit 27889e5e.

Requires the upstream MIT-licensed ``anon_pdf.py`` as an external script. This
does not copy its source or certify its output as anonymous.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from scripts.experimental_pdf_engine_adapter import _planned_lines, _sanitize_metadata_and_id


def transform_with_anonpdf(source: Path, destination: Path, upstream_script: Path) -> None:
    """Run AnonPDF's fixed-character content-stream replacement on a synthetic PDF."""
    source, destination, upstream_script = Path(source), Path(destination), Path(upstream_script)
    if destination.exists() or source.resolve() == destination.resolve():
        raise FileExistsError("Destination must be a new path")
    if not upstream_script.is_file():
        raise FileNotFoundError("Pinned upstream AnonPDF script is unavailable")
    _planned_lines(source, "random")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="anonpdf-poc-", dir=destination.parent) as tmp:
        scratch = Path(tmp)
        edited = scratch / "edited.pdf"
        subprocess.run(
            [
                sys.executable,
                str(upstream_script),
                str(source),
                "--output",
                str(edited),
                "--regex",
                "[A-Za-z0-9]",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if not edited.is_file():
            raise RuntimeError("AnonPDF did not produce output")
        stage = scratch / "sanitized.pdf"
        _sanitize_metadata_and_id(edited, stage, "SYNTHETIC AnonPDF fallback experiment")
        os.link(stage, destination)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--upstream-script", type=Path, required=True)
    args = parser.parse_args()
    transform_with_anonpdf(args.source, args.destination, args.upstream_script)
    print("Synthetic fallback experiment only; output is not certified anonymous.")


if __name__ == "__main__":
    main()
