"""Heuristics for visible page number detection."""

from __future__ import annotations

import re
from dataclasses import dataclass

import pymupdf as fitz

from njit_auditor.models import AuditFinding, Severity

_PAGE_NUM_RE = re.compile(r"^\s*[\[(]?[ivxlcdm\d]{1,6}[\])]?[.]?\s*$", re.IGNORECASE)


@dataclass
class PageNumberCandidate:
    """Likely page number text with rough location."""

    page_index: int
    text: str
    location: str


def classify_vertical_location(
    y0: float,
    y1: float,
    page_height: float,
    margin_ratio: float = 0.15,
) -> str:
    """Classify block position into top/bottom/unknown zones."""
    top_limit = page_height * margin_ratio
    bottom_limit = page_height * (1 - margin_ratio)

    if y1 <= top_limit:
        return "top"
    if y0 >= bottom_limit:
        return "bottom"
    return "unknown"


def detect_page_number_candidates(pdf_path: str) -> list[PageNumberCandidate]:
    """Scan text blocks in top/bottom zones for simple page number-like strings."""
    candidates: list[PageNumberCandidate] = []

    with fitz.open(pdf_path) as doc:
        for page_index, page in enumerate(doc):
            for block in page.get_text("blocks"):
                x0, y0, x1, y1, text, *_ = block
                _ = x0, x1
                clean = " ".join(text.strip().split())
                if not clean:
                    continue
                if not _PAGE_NUM_RE.match(clean):
                    continue

                location = classify_vertical_location(float(y0), float(y1), float(page.rect.height))
                if location == "unknown":
                    continue

                candidates.append(
                    PageNumberCandidate(page_index=page_index, text=clean, location=location)
                )

    return candidates


def run_page_number_rule(pdf_path: str) -> list[AuditFinding]:
    """Emit a conservative summary finding and per-page candidates."""
    candidates = detect_page_number_candidates(pdf_path)
    findings: list[AuditFinding] = []

    if not candidates:
        return [
            AuditFinding(
                rule_id="page_numbers",
                severity=Severity.PASS,
                message="No obvious visible page numbers detected in top/bottom margin zones.",
            )
        ]

    findings.append(
        AuditFinding(
            rule_id="page_numbers",
            severity=Severity.WARNING,
            message=(
                "Detected likely visible page number candidates. "
                "Review manually against NJIT formatting requirements."
            ),
            details={"candidate_count": str(len(candidates))},
        )
    )

    for candidate in candidates:
        findings.append(
            AuditFinding(
                rule_id="page_numbers",
                severity=Severity.WARNING,
                page=candidate.page_index + 1,
                message=(
                    f"Candidate page number '{candidate.text}' "
                    f"detected at {candidate.location} margin."
                ),
                details={"location": candidate.location},
            )
        )

    return findings
