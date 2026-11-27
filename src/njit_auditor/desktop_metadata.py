"""Desktop version and build provenance, with no update/network requests."""

from __future__ import annotations

import json
import re
from typing import Any

from njit_auditor.resource_paths import resource_path

DESKTOP_VERSION = "0.2.0-rc.4"
FILE_VERSION = (0, 2, 0, 4)


def candidate_version(commit: str) -> str:
    """Identify unpublished artifacts separately from an approved release."""
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Expected an exact Git commit SHA")
    return f"{DESKTOP_VERSION}+g{commit[:12]}"


def desktop_build_info() -> dict[str, Any]:
    path = resource_path("desktop-build-info.json")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"version": DESKTOP_VERSION}
    return value if isinstance(value, dict) else {"version": DESKTOP_VERSION}
