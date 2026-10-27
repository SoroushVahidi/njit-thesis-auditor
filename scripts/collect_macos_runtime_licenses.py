"""Collect notices for the actual Tcl/Tk runtime selected by PyInstaller on a Mac."""

from __future__ import annotations

import json
import os
from pathlib import Path


def collect(destination: Path) -> None:
    from PyInstaller.utils.hooks.tcl_tk import tcltk_info

    if not tcltk_info.available or tcltk_info.is_macos_system_framework:
        raise RuntimeError("Use a CPython distribution with bundled, non-system Tcl/Tk")
    records = []
    for name in ("tcl", "tk"):
        explicit = os.environ.get(f"NJIT_MACOS_{name.upper()}_LICENSE")
        candidates = [Path(explicit)] if explicit else []
        for location in (
            getattr(tcltk_info, f"{name}_data_dir"),
            getattr(tcltk_info, f"{name}_shared_library"),
        ):
            if not location:
                continue
            path = Path(location).resolve()
            for parent in (path, path.parent, path.parent.parent):
                candidates.extend(
                    parent / filename
                    for filename in (
                        "license.terms",
                        "LICENSE",
                        "license.txt",
                        "Resources/license.terms",
                        "Resources/LICENSE",
                    )
                )
        notice = next((path for path in candidates if path.is_file()), None)
        if notice is None:
            raise RuntimeError(
                f"Missing {name} notice: provide the matching runtime's license file through "
                f"NJIT_MACOS_{name.upper()}_LICENSE; do not substitute unrelated version notices"
            )
        output = destination / f"{name}-LICENSE.txt"
        output.write_bytes(notice.read_bytes())
        records.append(
            {
                "name": name,
                "version": list(getattr(tcltk_info, f"{name}_version")),
                "license_family": "Tcl/Tk BSD-style; inspect the bundled notice",
                "notice": output.name,
            }
        )
    (destination / "NATIVE-RUNTIME-NOTICES.json").write_text(
        json.dumps(records, indent=2) + "\n", encoding="utf-8"
    )
