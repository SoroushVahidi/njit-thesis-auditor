"""Static, fail-closed website release configuration. Never fetches a URL."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import unquote, urlsplit

from njit_auditor.resource_paths import resource_path


@dataclass(frozen=True)
class DesktopRelease:
    preview: bool = False
    available: bool = False
    version: str = ""
    filename: str = ""
    url: str = ""
    sha256: str = ""
    size_bytes: int = 0
    windows_versions: tuple[str, ...] = ()

    @property
    def size_label(self) -> str:
        return f"{self.size_bytes / (1024 * 1024):.1f} MiB"


def valid_asset_url(version: str, url: str) -> bool:
    """Allow only the versioned binary-only distribution repository."""
    filename = f"NJIT-Thesis-Auditor-{version}-windows-x64.zip"
    try:
        parsed = urlsplit(url)
        # Keep the website destination in the separate distribution repository.
        expected = (
            "/SoroushVahidi/njit-thesis-auditor-desktop/releases/download/"
            f"desktop-v{version}/{filename}"
        )
        return (
            parsed.scheme == "https"
            and parsed.netloc == "github.com"
            and unquote(parsed.path) == expected
            and not parsed.query
            and not parsed.fragment
        )
    except ValueError:
        return False


def parse_release(value: object) -> DesktopRelease:
    """Only a complete, approved verification record can produce a link."""
    if not isinstance(value, dict):
        return DesktopRelease()
    preview = value.get("preview") is True
    version = value.get("version", "")
    filename = f"NJIT-Thesis-Auditor-{version}-windows-x64.zip"
    url = value.get("url", "")
    sha256 = value.get("sha256", "")
    size = value.get("size_bytes", 0)
    versions = value.get("windows_versions", [])
    verified = value.get("native_tested_windows_versions", [])
    if not all(isinstance(s, str) for s in (version, url, sha256)):
        return DesktopRelease(preview=preview)
    valid = (
        bool(re.fullmatch(r"\d+\.\d+\.\d+(?:-[a-z0-9.]+)?", version))
        and valid_asset_url(version, url)
        and bool(re.fullmatch(r"[a-f0-9]{64}", sha256))
        and type(size) is int
        and 0 < size <= 2 * 1024**3
        and isinstance(versions, list)
        and bool(versions)
        and all(v in ("Windows 10", "Windows 11") for v in versions)
        and isinstance(verified, list)
        and all(v in verified for v in versions)
        and value.get("native_windows_build_verified") is True
        and value.get("public_download_verified") is True
        and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}T.+Z", str(value.get("verified_at", ""))))
        and value.get("licensing_reviewed") is True
        and value.get("license_basis") in ("commercial", "agpl-compliant")
        and value.get("approved_for_distribution") is True
        and value.get("enabled") is True
    )
    if not valid:
        return DesktopRelease(preview=preview)
    return DesktopRelease(
        preview=preview,
        available=True,
        version=version,
        filename=filename,
        url=url,
        sha256=sha256,
        size_bytes=size,
        windows_versions=tuple(versions),
    )


@lru_cache(maxsize=1)
def desktop_release() -> DesktopRelease:
    try:
        value = json.loads(resource_path("config", "desktop-release.json").read_text("utf-8"))
    except (OSError, ValueError):
        return DesktopRelease()
    return parse_release(value)
