"""Paths to allowlisted, read-only runtime resources in source and frozen builds."""

from __future__ import annotations

import sys
from pathlib import Path


def resource_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[2]


def resource_path(*parts: str) -> Path:
    return resource_root().joinpath(*parts)
