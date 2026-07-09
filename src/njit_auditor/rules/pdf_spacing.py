"""Heuristic spacing and blank-line checks for layout-aware PDF text lines."""

from __future__ import annotations

import re
from statistics import median

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, PdfPage, PdfTextLine
from njit_auditor.rules.pdf_headings import EXPECTED_HEADINGS, normalize_heading_text
from njit_auditor.rules.pdf_page_numbers import PAGE_NUM_RE

TOC_LIKE_HEADINGS = {
    "TABLE OF CONTENTS",
    "LIST OF TABLES",
    "LIST OF FIGURES",
}
REFERENCES_LIKE_HEADINGS = {
    "REFERENCES",
    "BIBLIOGRAPHY",
    "WORKS CITED",
}
# Front-matter template pages whose layout intentionally contains large blank
# gaps (centered author/degree/date and committee-signature blocks). These are
# not ordinary chapter/body pages, so their intentional spacing must not be
# treated as an accidental blank-line problem.
SPECIAL_LAYOUT_HEADINGS = {
    "BIOGRAPHICAL SKETCH",
    "APPROVAL PAGE",
}
CAPTION_PREFIX_RE = re.compile(r"^(figure|table)\s+[\divxlcdm]+[.:)]?\s+", re.IGNORECASE)
MIN_TEXT_LEN = 12
CAPTION_HEAVY_PAGE_RATIO = 0.35
MIN_EXCESSIVE_GAP_COUNT_FOR_WARNING = 2


def _is_page_number_line(line: PdfTextLine) -> bool:
    clean = " ".join(line.text.strip().split())
    return bool(clean and PAGE_NUM_RE.match(clean))


def _normalized_heading(line: PdfTextLine) -> str:
    return normalize_heading_text(line.text).upper()


def _is_named_heading_line(line: PdfTextLine) -> bool:
    return _normalized_heading(line) in EXPECTED_HEADINGS


def _is_caption_line(line: PdfTextLine) -> bool:
    clean = " ".join(line.text.strip().split())
    return bool(clean and CAPTION_PREFIX_RE.match(clean))


def _is_usable_text_line(line: PdfTextLine) -> bool:
    clean = " ".join(line.text.strip().split())
    if len(clean) < MIN_TEXT_LEN:
        return False
    if _is_page_number_line(line) or _is_named_heading_line(line) or _is_caption_line(line):
        return False
    alpha_count = sum(ch.isalpha() for ch in clean)
    if alpha_count < 4:
        return False
    return (alpha_count / max(len(clean), 1)) >= 0.35


def _collect_page_lines(page: PdfPage) -> list[PdfTextLine]:
    lines: list[PdfTextLine] = []
    for block in page.text_blocks:
        lines.extend(block.lines)
    return lines


def _page_has_heading_in(page: PdfPage, headings: set[str]) -> bool:
    for line in _collect_page_lines(page):
        if _normalized_heading(line) in headings:
            return True
    return False


def _front_matter_page(page: PdfPage) -> bool:
    return _page_has_heading_in(page, set(EXPECTED_HEADINGS))


def _line_height(line: PdfTextLine) -> float:
    return max(1.0, line.bbox.height)


def _line_gap_pt(upper: PdfTextLine, lower: PdfTextLine) -> float:
    return lower.bbox.y0 - upper.bbox.y1


def check_pdf_spacing(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P016 warnings for strong likely spacing/blank-line issues."""

    findings: list[AuditFinding] = []

    for page in pdf_document.pages:
        if _page_has_heading_in(page, TOC_LIKE_HEADINGS):
            continue
        if _page_has_heading_in(page, REFERENCES_LIKE_HEADINGS):
            continue
        # Biographical Sketch / Approval Page are special front-matter templates
        # whose large blank areas (before the author/degree/date or committee
        # blocks) are intentional layout, not accidental blank lines. Skip them
        # so ordinary heading-blank-gap and paragraph-gap warnings do not fire.
        if _page_has_heading_in(page, SPECIAL_LAYOUT_HEADINGS):
            continue
        if not _front_matter_page(page):
            continue

        all_lines = _collect_page_lines(page)
        if not all_lines:
            continue

        text_lines = [line for line in all_lines if _is_usable_text_line(line)]
        if len(text_lines) < 2:
            continue

        caption_count = sum(1 for line in all_lines if _is_caption_line(line))
        if caption_count / max(len(all_lines), 1) >= CAPTION_HEAVY_PAGE_RATIO:
            continue

        text_lines.sort(key=lambda line: (line.bbox.y0, line.bbox.x0))
        line_heights = [_line_height(line) for line in text_lines]
        median_line_height = median(line_heights)

        excessive_gap_threshold = max(30.0, 3.0 * median_line_height)
        paragraph_gap_threshold = max(42.0, 4.0 * median_line_height)
        heading_gap_threshold = max(42.0, 3.5 * median_line_height)

        page_issue_findings: dict[str, AuditFinding] = {}

        excessive_gaps: list[float] = []
        paragraph_gaps: list[float] = []
        for upper, lower in zip(text_lines, text_lines[1:]):
            gap_pt = _line_gap_pt(upper, lower)
            if gap_pt > excessive_gap_threshold:
                excessive_gaps.append(gap_pt)
            if gap_pt > paragraph_gap_threshold:
                paragraph_gaps.append(gap_pt)

        context = "front_matter"

        if len(excessive_gaps) >= MIN_EXCESSIVE_GAP_COUNT_FOR_WARNING:
            page_issue_findings["excessive_line_gap"] = AuditFinding(
                rule_id="P016",
                severity=Severity.WARNING,
                page=page.page_number,
                message="Detected excessive vertical spacing between adjacent text lines.",
                details={
                    "page_number": str(page.page_number),
                    "issue_type": "excessive_line_gap",
                    "largest_gap_pt": f"{max(excessive_gaps):.1f}",
                    "affected_gap_count": str(len(excessive_gaps)),
                    "context": context,
                },
            )

        if paragraph_gaps:
            page_issue_findings["excessive_paragraph_gap"] = AuditFinding(
                rule_id="P016",
                severity=Severity.WARNING,
                page=page.page_number,
                message="Detected excessive blank space likely between paragraph groups.",
                details={
                    "page_number": str(page.page_number),
                    "issue_type": "excessive_paragraph_gap",
                    "largest_gap_pt": f"{max(paragraph_gaps):.1f}",
                    "affected_gap_count": str(len(paragraph_gaps)),
                    "context": context,
                },
            )

        heading_lines = [line for line in all_lines if _is_named_heading_line(line)]
        if heading_lines:
            heading_lines.sort(key=lambda line: (line.bbox.y0, line.bbox.x0))
            last_heading = heading_lines[-1]
            first_content_after_heading = next(
                (line for line in text_lines if line.bbox.y0 >= last_heading.bbox.y1),
                None,
            )
            if first_content_after_heading is not None:
                heading_gap = _line_gap_pt(last_heading, first_content_after_heading)
                if heading_gap > heading_gap_threshold:
                    page_issue_findings["suspicious_heading_blank_gap"] = AuditFinding(
                        rule_id="P016",
                        severity=Severity.WARNING,
                        page=page.page_number,
                        message=(
                            "Detected suspiciously large blank gap after a front-matter heading."
                        ),
                        details={
                            "page_number": str(page.page_number),
                            "issue_type": "suspicious_heading_blank_gap",
                            "largest_gap_pt": f"{heading_gap:.1f}",
                            "affected_gap_count": "1",
                            "context": "front_matter",
                            # The measured gap is between the heading and the first
                            # content line below it, i.e. AFTER the heading.
                            "heading_gap_position": "after",
                        },
                    )

        # paragraph_gap_threshold is always stricter than excessive_gap_threshold, so
        # any gap that qualifies as a paragraph gap also qualifies as a line gap and
        # is already counted in excessive_gaps. When both fire on the same page they
        # are anchored on the same largest gap (Sample B page 1: Ester's reported
        # duplicate "Spacing / blank lines" card). Keep only the more specific
        # paragraph-gap finding rather than showing the same evidence twice.
        if "excessive_paragraph_gap" in page_issue_findings:
            page_issue_findings.pop("excessive_line_gap", None)

        for issue_type in (
            "suspicious_heading_blank_gap",
            "excessive_paragraph_gap",
            "excessive_line_gap",
        ):
            finding = page_issue_findings.get(issue_type)
            if finding is not None:
                findings.append(finding)

    return findings
