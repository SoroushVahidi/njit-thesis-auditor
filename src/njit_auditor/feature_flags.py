"""Deployment-controlled features. Students cannot override these via requests."""

from __future__ import annotations

import os


def pdf_url_auditing_enabled() -> bool:
    """Temporarily disabled; reactivation requires the explicit server value `1`."""
    return os.environ.get("NJIT_AUDITOR_ENABLE_PDF_URL_AUDITING", "") == "1"
