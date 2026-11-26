"""Annotation/comment extraction from PDF pages."""

from __future__ import annotations

import pymupdf as fitz

from njit_auditor.models import AuditFinding, Severity


def run_pdf_annotation_rule(
    pdf_path: str,
    *,
    skip_pages: set[int] | None = None,
) -> list[AuditFinding]:
    """Extract annotations/comments and emit P012 findings."""

    findings: list[AuditFinding] = []
    skipped = skip_pages or set()
    try:
        with fitz.open(pdf_path) as doc:
            for page_number, page in enumerate(doc, start=1):
                if page_number in skipped:
                    continue
                for annot in page.annots() or []:
                    content = (annot.info or {}).get("content") or ""
                    subtype = annot.type[1] if annot.type else "Unknown"
                    rect = annot.rect
                    findings.append(
                        AuditFinding(
                            rule_id="P012",
                            severity=Severity.WARNING,
                            page=page_number,
                            message=f"PDF annotation/comment detected ({subtype}).",
                            details={
                                "issue_type": "pdf_annotation_detected",
                                "annotation_type": subtype,
                                "content": content.strip()[:200],
                                "rect": (
                                    f"{rect.x0:.1f},{rect.y0:.1f},{rect.x1:.1f},{rect.y1:.1f}"
                                ),
                                "suggested_fix": (
                                    "Resolve/remove reviewer comments before final submission."
                                ),
                                "triage_tier": "informational",
                            },
                        )
                    )
    except Exception:
        # Keep audit resilient; annotation extraction is best-effort in foundation phase.
        return []

    return findings
