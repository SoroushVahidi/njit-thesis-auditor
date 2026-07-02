"""Shared helpers for extracting audit PDF links from rendered HTML."""

from __future__ import annotations

import html
import re

AUDIT_PDF_HREF_RE = re.compile(
    r'href="(/audits/[^"]*?(?:'
    r'/highlighted-page\.pdf\?[^"]*|/pdf(?:[/?#][^"]*)?))"'
)


def extract_audit_pdf_links(text: str) -> set[str]:
    """Return de-fragmented audit PDF/highlighted-page href targets from HTML."""
    links = set(AUDIT_PDF_HREF_RE.findall(text))
    return {html.unescape(link).split("#")[0] for link in links}
