"""Heuristic page-number candidate detection for layout-model pages."""

from __future__ import annotations

import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument

PAGE_NUM_RE = re.compile(r"^\s*[\[(]?(?:\d+|[ivxlcdm]+)[\])]?[.]?\s*$", re.IGNORECASE)


def _is_top_or_bottom_zone(
    y0: float, y1: float, page_height: float, zone_ratio: float = 0.15
) -> bool:
    top_limit = page_height * zone_ratio
    bottom_limit = page_height * (1.0 - zone_ratio)
    return y1 <= top_limit or y0 >= bottom_limit


def detect_page_number_candidates(pdf_doc: PdfDocument) -> list[tuple[int, str, str, str]]:
    """Return tuples of (page_number, text, location, line_number_like)."""

    candidates: list[tuple[int, str, str, str]] = []
    for page in pdf_doc.pages:
        for block in page.text_blocks:
            if not _is_top_or_bottom_zone(block.bbox.y0, block.bbox.y1, page.height):
                continue
            for line in block.lines:
                clean = " ".join(line.text.strip().split())
                if not clean or not PAGE_NUM_RE.match(clean):
                    continue
                location = "top" if line.bbox.y1 <= page.height * 0.15 else "bottom"
                candidates.append((page.page_number, clean, location, str(page.page_number)))
    return candidates


def run_pdf_page_number_candidates_rule(pdf_doc: PdfDocument) -> list[AuditFinding]:
    """Emit P013 findings for candidate page numbers."""

    candidates = detect_page_number_candidates(pdf_doc)
    if not candidates:
        return [
            AuditFinding(
                rule_id="P013",
                severity=Severity.PASS,
                message="No page-number candidates detected in top/bottom margin zones.",
            )
        ]

    findings: list[AuditFinding] = [
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            message="Detected possible page-number candidates for manual NJIT rule verification.",
            details={"candidate_count": str(len(candidates))},
        )
    ]
    for page_number, text, location, _line in candidates:
        findings.append(
            AuditFinding(
                rule_id="P013",
                severity=Severity.WARNING,
                page=page_number,
                message=f"Candidate page number '{text}' found near {location} margin.",
                details={
                    "location": location,
                    "suggested_fix": (
                        "Verify placement/format against NJIT page-number requirements."
                    ),
                },
            )
        )
    return findings
