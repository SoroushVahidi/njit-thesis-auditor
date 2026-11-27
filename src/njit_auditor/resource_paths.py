"""Paths to read-only resources in source, installed, and frozen builds."""

from __future__ import annotations

import sys
from pathlib import Path


def resource_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    package = Path(__file__).resolve().parent
    installed = package / "_runtime"
    source = package.parent.parent
    if package.parent.name == "src" and (source / "pyproject.toml").is_file():
        return installed if installed.is_dir() else source
    return installed


def resource_path(*parts: str) -> Path:
    return resource_root().joinpath(*parts)


def package_path(*parts: str) -> Path:
    """Locate resources shipped beside the package, including its templates."""
    if getattr(sys, "frozen", False):
        return resource_path("src", "njit_auditor", *parts)
    return Path(__file__).resolve().parent.joinpath(*parts)
