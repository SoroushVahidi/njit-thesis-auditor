"""Paths to read-only runtime data in source, wheel, and frozen installations."""

from __future__ import annotations

import sys
from pathlib import Path


def resource_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS"))
    package_root = Path(__file__).resolve().parent
    source_root = package_root.parents[1]
    if (source_root / "pyproject.toml").is_file() and package_root.parent.name == "src":
        return source_root
    return package_root


def resource_path(*parts: str) -> Path:
    return resource_root().joinpath(*parts)
