"""Collect installed build-environment notices, without copying source or credentials."""

from __future__ import annotations

import argparse
import builtins
import json
import re
from importlib import metadata
from pathlib import Path


def collect(destination: Path) -> list[dict[str, object]]:
    destination.mkdir(parents=True, exist_ok=True)
    records = []
    for dist in sorted(metadata.distributions(), key=lambda d: d.metadata.get("Name", "")):
        name = dist.metadata.get("Name", "unknown")
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
        directory = destination / safe
        directory.mkdir(exist_ok=True)
        notices = []
        for entry in dist.files or []:
            filename = Path(entry).name
            in_license_directory = any(
                part.lower() in {"license", "licenses", "build_licenses"}
                for part in Path(entry).parts[:-1]
            )
            if not in_license_directory and not re.match(
                r"(?i)^(?:licen[cs]e|copying|notice)(?:[._-].*)?$", filename
            ):
                continue
            source = Path(dist.locate_file(entry))
            if not source.is_file() or source.is_symlink():
                continue
            output = directory / f"{len(notices):02d}-{filename}"
            output.write_bytes(source.read_bytes())
            notices.append(str(output.relative_to(destination)))
        records.append(
            {
                "name": name,
                "version": dist.version,
                "license_expression": dist.metadata.get("License-Expression", ""),
                "license_metadata": dist.metadata.get("License", ""),
                "license_classifiers": [
                    c for c in dist.metadata.get_all("Classifier", []) if c.startswith("License ::")
                ],
                "notices": notices,
            }
        )
    # CPython's own notice is separate from installed distribution metadata.
    printer = getattr(builtins, "license", None)
    if printer is not None:
        setup = getattr(printer, "_Printer__setup", None)
        if setup is not None:
            setup()
            text = "\n".join(getattr(printer, "_Printer__lines", []))
            if text:
                (destination / "Python-LICENSE.txt").write_text(text + "\n", encoding="utf-8")
    (destination / "DEPENDENCIES.json").write_text(
        json.dumps(records, indent=2) + "\n", encoding="utf-8"
    )
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(f"Collected notices for {len(collect(args.destination))} installed distributions.")


if __name__ == "__main__":
    main()
