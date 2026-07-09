"""Conservative front-matter exact heading phrase and missing-section checks (P038)."""

from __future__ import annotations

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, format_bbox_detail
from njit_auditor.rules.pdf_frontmatter_heading_gate import FRONTMATTER_HEADING_VARIANTS
from njit_auditor.rules.pdf_headings import (
    EXPECTED_HEADINGS,
    find_named_frontmatter_headings,
    normalize_heading_text,
)
from njit_auditor.rules.pdf_page_numbering_regime import _classify_pages

# Required headings: must be present in every NJIT thesis/dissertation.
# Flagged as required_heading_missing when not detected.
_REQUIRED_HEADINGS: tuple[str, ...] = (
    "APPROVAL PAGE",
    "BIOGRAPHICAL SKETCH",
    "ACKNOWLEDGEMENTS",
    "TABLE OF CONTENTS",
)

# Optional headings: presence not required; only flagged for phrase mismatch.
# DEDICATION is always optional.
# LIST OF TABLES / LIST OF FIGURES: optional if document has no tables/figures.
_OPTIONAL_HEADINGS: tuple[str, ...] = (
    "DEDICATION",
    "LIST OF TABLES",
    "LIST OF FIGURES",
)

# Concatenated heading lines from PDF text extraction (no spaces between words).
# P038-only: do not add to FRONTMATTER_HEADING_VARIANTS — that map is shared with
# gate/TOC localization and would unlock broad TOC rules on Sample A.
_P038_CONCATENATED_HEADING_VARIANTS: dict[str, str] = {
    "ACKNOWLEDGMENT": "ACKNOWLEDGEMENTS",
    "APPROVALPAGE": "APPROVAL PAGE",
    "BIOGRAPHICALSKETCH": "BIOGRAPHICAL SKETCH",
    "TABLEOFCONTENTS": "TABLE OF CONTENTS",
}

# Known-wrong phrase variants worth flagging to the student as a mismatch from
# the NJIT-canonical heading (Check 2 below). Deliberately separate from
# FRONTMATTER_HEADING_VARIANTS (pdf_frontmatter_heading_gate.py): that map
# exists to tolerantly *locate* a section for other rules (P041, P044-P047,
# P065-P068, TOC/list detection) and includes spellings NJIT accepts as
# equivalent — e.g. "ACKNOWLEDGMENTS", the standard American spelling of
# "ACKNOWLEDGEMENTS" — which must never be reported to the student as an
# error. Ester's Sample B review confirmed flagging "ACKNOWLEDGMENTS" as a
# phrase mismatch was a false positive (see
# docs/status/ester_sample_b_p038_front_matter_headings.md). Empty for now:
# no curated variant is currently known to be a genuine phrasing defect worth
# flagging (a concatenated/no-space heading is a layout artifact, not a
# different phrase, and is already handled by
# _P038_CONCATENATED_HEADING_VARIANTS above for presence detection only).
_P038_FLAGGED_PHRASE_VARIANTS: dict[str, str] = {}


def _p038_detected_heading_set(pdf_doc: PdfDocument) -> set[str]:
    """Headings considered present for P038 missing-section checks only."""
    detected = {m.heading for m in find_named_frontmatter_headings(pdf_doc)}
    for page in pdf_doc.pages:
        for block in page.text_blocks:
            for line in block.lines:
                normalized_upper = normalize_heading_text(line.text).upper()
                if normalized_upper in EXPECTED_HEADINGS:
                    detected.add(normalized_upper)
                canonical = _P038_CONCATENATED_HEADING_VARIANTS.get(normalized_upper)
                if canonical is not None:
                    detected.add(canonical)
                canonical = FRONTMATTER_HEADING_VARIANTS.get(normalized_upper)
                if canonical is not None:
                    detected.add(canonical)
    return detected

_SECTION_KEYS: dict[str, str] = {
    "APPROVAL PAGE": "approval_page",
    "BIOGRAPHICAL SKETCH": "biographical_sketch",
    "ACKNOWLEDGEMENTS": "acknowledgements",
    "TABLE OF CONTENTS": "table_of_contents",
    "LIST OF TABLES": "list_of_tables",
    "LIST OF FIGURES": "list_of_figures",
}


def check_pdf_frontmatter_headings(pdf_doc: PdfDocument) -> list[AuditFinding]:
    """Emit P038 warnings for missing required front-matter headings or known phrase variants.

    Conservative gates:
    - No findings if no headings at all are detected (image-only / flattened PDFs).
    - required_heading_missing only for REQUIRED_HEADINGS not found anywhere — a heading
      detected under an NJIT-accepted equivalent spelling (FRONTMATTER_HEADING_VARIANTS)
      counts as present and is never also reported missing.
    - heading_phrase_not_exact only for curated variants that are genuine phrasing
      defects (_P038_FLAGGED_PHRASE_VARIANTS), never NJIT-accepted equivalent spellings
      and never arbitrary text.
    Does not duplicate P014 style checks or P025 structure checks.
    """
    if not pdf_doc.pages:
        return []

    regions, has_front = _classify_pages(pdf_doc)
    if not has_front:
        return []

    # Detect named headings for missing-section checks (strict + P038-local variants).
    detected_set = _p038_detected_heading_set(pdf_doc)

    # Gate: if no headings detected at all, the PDF is likely flattened/image-only.
    # Skip all checks to avoid false positives on every required section.
    if not detected_set:
        return []

    front_matter_pages = {pn for pn, r in regions.items() if r == "front_matter"}
    findings: list[AuditFinding] = []

    # --- Check 1: required_heading_missing ---
    for heading in _REQUIRED_HEADINGS:
        if heading in detected_set:
            continue
        section_key = _SECTION_KEYS[heading]
        findings.append(
            AuditFinding(
                rule_id="P038",
                severity=Severity.WARNING,
                message=(
                    f"Required front-matter heading '{heading}' was not detected "
                    f"in the front-matter region."
                ),
                details={
                    "issue_type": "required_heading_missing",
                    "section_key": section_key,
                    "expected_heading": heading,
                    "triage_tier": "check",
                    "confidence": "medium",
                },
            )
        )

    # --- Check 2: heading_phrase_not_exact (curated variants only) ---
    seen: set[tuple[int, str]] = set()
    for page in pdf_doc.pages:
        if page.page_number not in front_matter_pages:
            continue
        for block in page.text_blocks:
            for line in block.lines:
                normalized_upper = normalize_heading_text(line.text).upper()
                canonical = _P038_FLAGGED_PHRASE_VARIANTS.get(normalized_upper)
                if canonical is None:
                    continue
                # Avoid duplicates and skip if canonical is already correctly detected.
                key = (page.page_number, canonical)
                if key in seen:
                    continue
                seen.add(key)
                findings.append(
                    AuditFinding(
                        rule_id="P038",
                        severity=Severity.WARNING,
                        page=page.page_number,
                        message=(
                            f"Front-matter heading on page {page.page_number} uses variant "
                            f"'{normalized_upper}'; expected canonical '{canonical}'."
                        ),
                        details={
                            "issue_type": "heading_phrase_not_exact",
                            "section_key": _SECTION_KEYS.get(
                                canonical, canonical.lower().replace(" ", "_")
                            ),
                            "expected_heading": canonical,
                            "observed_heading_normalized": normalized_upper,
                            "triage_tier": "check",
                            "confidence": "medium",
                            "bbox": format_bbox_detail(line.bbox),
                        },
                    )
                )

    return findings
