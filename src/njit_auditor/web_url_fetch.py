"""Safe public PDF URL downloader for the web audit UI (SSRF-safe)."""

from __future__ import annotations

import http.client
import ipaddress
import socket
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from njit_auditor.web_fetch_error import FetchError

FETCH_TIMEOUT_SEC: int = 15

_ALLOWED_SCHEMES: frozenset[str] = frozenset({"http", "https"})

_PRIVATE_NETS_V4: tuple[ipaddress.IPv4Network, ...] = (
    ipaddress.IPv4Network("0.0.0.0/8"),
    ipaddress.IPv4Network("10.0.0.0/8"),
    ipaddress.IPv4Network("100.64.0.0/10"),  # carrier-grade NAT
    ipaddress.IPv4Network("127.0.0.0/8"),
    ipaddress.IPv4Network("169.254.0.0/16"),
    ipaddress.IPv4Network("172.16.0.0/12"),
    ipaddress.IPv4Network("192.168.0.0/16"),
)

_PRIVATE_NETS_V6: tuple[ipaddress.IPv6Network, ...] = (
    ipaddress.IPv6Network("::1/128"),
    ipaddress.IPv6Network("fc00::/7"),
    ipaddress.IPv6Network("fe80::/10"),
)


def _ip_is_private(addr: str) -> bool:
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv4Address):
        return any(ip in net for net in _PRIVATE_NETS_V4)
    return any(ip in net for net in _PRIVATE_NETS_V6)


def _check_host(hostname: str) -> None:
    """Resolve hostname and raise FetchError if it maps to a private/internal address."""
    h = hostname.lower()
    if h in {"localhost", "localhost.localdomain", "0.0.0.0"}:
        raise FetchError("Private or localhost URLs are not allowed.")
    try:
        addrinfo = socket.getaddrinfo(h, None)
    except OSError as exc:
        raise FetchError("Cannot resolve host. Check the link or upload the PDF.") from exc
    for entry in addrinfo:
        addr = str(entry[4][0])
        if _ip_is_private(addr):
            raise FetchError("URLs resolving to private or internal addresses are not allowed.")


def _validate_url(url: str) -> str:
    """Parse and validate URL scheme and host. Return stripped URL or raise FetchError."""
    stripped = url.strip()
    try:
        parsed = urllib.parse.urlparse(stripped)
        _ = parsed.port  # Reject malformed ports before DNS or HTTP access.
    except Exception as exc:
        raise FetchError("Invalid URL. Check the link or upload the PDF.") from exc
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise FetchError(f"Only http:// and https:// URLs are supported. Got: {parsed.scheme!r}")
    host = parsed.hostname or ""
    if not host:
        raise FetchError("URL has no host. Paste a complete public PDF link.")
    _check_host(host)
    return stripped


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Redirect handler that blocks redirects to private or internal hosts."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        _validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_pdf_url(url: str, dest_path: Path, max_bytes: int) -> None:
    """Download a public PDF URL safely into dest_path.

    Performs scheme validation, private-IP rejection, hostname resolution checks,
    redirect safety checks, PDF magic-byte validation, and size enforcement.
    Streams the download; does not load the full file into memory.

    Raises FetchError with a user-facing message on any failure.
    """
    validated_url = _validate_url(url)
    opener = urllib.request.build_opener(_SafeRedirectHandler())
    req = urllib.request.Request(validated_url)
    try:
        with opener.open(req, timeout=FETCH_TIMEOUT_SEC) as resp:
            ct_raw = resp.headers.get("Content-Type", "")
            ct = ct_raw.split(";")[0].strip().lower()
            if ct and ct not in {"application/pdf", "application/octet-stream", ""}:
                raise FetchError(
                    "The link returned a web page or another file instead of a PDF. "
                    "Use a direct PDF link or download the PDF and upload it here."
                )
            # Read first 8 bytes to validate PDF magic header
            header = resp.read(8)
            if len(header) < 5 or not header.startswith(b"%PDF"):
                raise FetchError("The URL does not point to a valid PDF file. Upload a valid PDF.")
            # Stream the remainder; enforce size limit
            with dest_path.open("wb") as f:
                f.write(header)
                downloaded = len(header)
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    downloaded += len(chunk)
                    if downloaded > max_bytes:
                        raise FetchError(
                            f"The PDF exceeds the {max_bytes / (1024 * 1024):g} MB limit. "
                            "Use a smaller PDF."
                        )
                    f.write(chunk)
    except FetchError:
        raise
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            response_headers: Any = exc.headers
            refusal = (
                "The source website requires a security check."
                if response_headers is not None
                and str(response_headers.get("cf-mitigated", "")).lower() == "challenge"
                else "The source website blocked the request."
            )
            message = f"{refusal} Download the PDF yourself and upload it here."
        elif exc.code == 404:
            message = "The PDF wasn't found (HTTP 404). Check the link or upload the PDF."
        elif exc.code >= 500:
            message = (
                f"The source website is unavailable (HTTP {exc.code}). Try later or upload the PDF."
            )
        else:
            message = (
                f"The source website couldn't provide the PDF (HTTP {exc.code}). "
                "Check the link or upload the PDF."
            )
        raise FetchError(message) from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, TimeoutError):
            raise FetchError("The download timed out. Try again or upload the PDF.") from exc
        raise FetchError("Couldn't reach the source website. Try later or upload the PDF.") from exc
    except (ValueError, http.client.InvalidURL) as exc:
        raise FetchError("Invalid PDF URL. Check the link or upload the PDF.") from exc
    except TimeoutError as exc:
        raise FetchError("The download timed out. Try again or upload the PDF.") from exc
    except OSError as exc:
        raise FetchError("Couldn't download the PDF. Try again or upload the PDF.") from exc
