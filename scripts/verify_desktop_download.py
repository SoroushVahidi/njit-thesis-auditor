"""Verify an already approved-for-upload public asset anonymously; never publish or enable it."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from njit_auditor.desktop_download import valid_asset_url


class HTTPSOnlyRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urlsplit(newurl)
        if (
            target.scheme != "https"
            or target.hostname
            not in {
                "github.com",
                "release-assets.githubusercontent.com",
                "objects.githubusercontent.com",
            }
            or target.username
            or target.password
        ):
            raise ValueError("Unexpected download redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def verify_public_download(record: dict) -> dict:
    version, url = str(record.get("version", "")), str(record.get("url", ""))
    digest, size = str(record.get("sha256", "")), record.get("size_bytes", 0)
    if (
        not valid_asset_url(version, url)
        or not re.fullmatch(r"[a-f0-9]{64}", digest)
        or type(size) is not int
        or not 0 < size <= 2 * 1024**3
    ):
        raise ValueError("A versioned URL, expected SHA-256, and package size are required")
    # No account cookies or Authorization header: a private/nonexistent asset fails.
    opener = urllib.request.build_opener(HTTPSOnlyRedirect())
    actual = hashlib.sha256()
    count = 0
    with opener.open(url, timeout=30) as response:
        if response.status != 200:
            raise ValueError("Public download is unavailable")
        while chunk := response.read(1024 * 1024):
            count += len(chunk)
            if count > size:
                raise ValueError("Public package exceeds the expected size")
            actual.update(chunk)
    if count != size or actual.hexdigest() != digest:
        raise ValueError("Public package checksum or size does not match")
    # Produce a review receipt, not a production configuration or approval.
    return {
        **record,
        "enabled": False,
        "approved_for_distribution": False,
        "public_download_verified": True,
        "verified_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_manifest", type=Path)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    receipt = verify_public_download(json.loads(args.candidate_manifest.read_text("utf-8")))
    with args.receipt.open("x", encoding="utf-8") as file:
        json.dump(receipt, file, indent=2)
        file.write("\n")
    print("Anonymous HTTPS package checksum verified; download remains disabled.")


if __name__ == "__main__":
    main()
