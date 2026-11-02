"""Deployment-only Windows release configuration; never fetches remote resources."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass

# A separate, proposed distribution repository. Never accept the private source
# repository, arbitrary hosts, redirects, query parameters, or mutable latest assets.
_RELEASE_ROOT = "https://github.com/SoroushVahidi/njit-thesis-auditor-desktop/releases"
_ASSET_URL = re.compile(
    re.escape(_RELEASE_ROOT)
    + r"/download/desktop-v(?P<version>[0-9]+\.[0-9]+\.[0-9]+(?:-[a-z0-9]+(?:\.[a-z0-9]+)*)?)"
    + r"/NJIT-Thesis-Auditor-Setup-(?P=version)\.exe"
)


@dataclass(frozen=True)
class WindowsDownload:
    url: str = ""
    version: str = ""
    release_notes_url: str = ""
    sha256: str = ""
    size_bytes: int = 0
    windows_versions: str = ""
    architecture: str = ""

    @property
    def size_label(self) -> str:
        return f"{self.size_bytes / (1024 * 1024):.1f} MiB ({self.size_bytes:,} bytes)"


def windows_download(environ: Mapping[str, str] | None = None) -> WindowsDownload:
    """Fail closed unless an operator has approved a correctly formed release.

    Flags record release evidence, not proof of qualification or asset availability.
    Operators must complete the documented release gates first.
    No request parameters, cookies, credentials, or network calls are involved.
    """
    env = os.environ if environ is None else environ
    url = env.get("NJIT_AUDITOR_WINDOWS_DOWNLOAD_URL", "")
    if env.get("NJIT_AUDITOR_WINDOWS_DOWNLOAD_APPROVED") != "1" or len(url) > 512:
        return WindowsDownload()
    if any(
        env.get("NJIT_AUDITOR_WINDOWS_DOWNLOAD_" + key) != value
        for key, value in {
            "EDITION": "njit",
            "NATIVE_TESTED": "1",
            "CONFIDENTIALITY_REVIEWED": "1",
            "ARCHITECTURE": "x64",
        }.items()
    ):
        return WindowsDownload()
    match = _ASSET_URL.fullmatch(url)
    if match is None or len(match["version"]) > 64:
        return WindowsDownload()
    sha256 = env.get("NJIT_AUDITOR_WINDOWS_DOWNLOAD_SHA256", "")
    if re.fullmatch(r"[a-fA-F0-9]{64}", sha256) is None:
        return WindowsDownload()
    size = env.get("NJIT_AUDITOR_WINDOWS_DOWNLOAD_SIZE_BYTES", "")
    if re.fullmatch(r"[1-9][0-9]{0,11}", size) is None:
        return WindowsDownload()
    windows_versions = env.get("NJIT_AUDITOR_WINDOWS_DOWNLOAD_WINDOWS_VERSIONS", "")
    if windows_versions not in {"Windows 10", "Windows 11", "Windows 10 and Windows 11"}:
        return WindowsDownload()
    version = match["version"]
    return WindowsDownload(
        url=url,
        version=version,
        release_notes_url=f"{_RELEASE_ROOT}/tag/desktop-v{version}",
        sha256=sha256.lower(),
        size_bytes=int(size),
        windows_versions=windows_versions,
        architecture="x64",
    )
