"""Body figure-number structure and succession checks (P088 / Ester F08).

Detects genuinely malformed body figure labels such as concatenated
``Figure 4.204.1`` (three or more numeric segments) and per-chapter duplicate or
out-of-order well-formed ``chapter.sequence`` labels.

Scope: body figure captions only (page-local detection plus bounded continuation
association, retaining the original figure anchor). List of Figures
entries, table captions, in-text cross-references, and panel letters are out of
scope. Malformed tokens can occur within a single bold caption span; this rule
flags their structure without inventing separator repairs.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, format_bbox_detail
from njit_auditor.rules.pdf_captions import (
    CAPTION_START_RE,
    CaptionLine,
    detect_caption_lines,
    normalize_caption_candidate_text,
)
from njit_auditor.toc_list_student_preview import sanitize_toc_list_entry_preview

RULE_ID = "P088"

_ARABIC_SEGMENT_RE = re.compile(r"^\d+$")
_MAX_WELL_FORMED_SEGMENTS = 2


@dataclass(frozen=True)
class _ParsedFigureNumber:
    caption: CaptionLine
    number_token: str
    segments: tuple[str, ...]
    arabic_parts: tuple[int, ...] | None


def _parse_figure_number(caption: CaptionLine) -> _ParsedFigureNumber | None:
    if caption.caption_type != "figure" or caption.context != "body":
        return None
    match = CAPTION_START_RE.match(normalize_caption_candidate_text(caption.raw_text))
    if match is None:
        return None
    token = match.group("number")
    segments = tuple(part for part in re.split(r"[.\-]", token) if part)
    if not segments:
        return None
    if all(_ARABIC_SEGMENT_RE.fullmatch(part) for part in segments):
        arabic = tuple(int(part) for part in segments)
    else:
        arabic = None
    return _ParsedFigureNumber(
        caption=caption,
        number_token=token,
        segments=segments,
        arabic_parts=arabic,
    )


def _malformed_finding(parsed: _ParsedFigureNumber) -> AuditFinding:
    caption = parsed.caption
    preview = sanitize_toc_list_entry_preview(
        f"Figure {parsed.number_token}"
    )
    return AuditFinding(
        rule_id=RULE_ID,
        severity=Severity.WARNING,
        page=caption.page_number,
        message=(
            f"Figure caption numbering “{parsed.number_token}” appears malformed. "
            "NJIT figure numbers use a chapter.sequence form such as 4.20, not "
            "extra concatenated segments."
        ),
        details={
            "issue_type": "figure_number_malformed",
            "page": str(caption.page_number),
            "page_type": "body",
            "section_type": "figure_caption",
            "float_type": "figure",
            "number_token": parsed.number_token,
            "segment_count": str(len(parsed.segments)),
            "bbox": format_bbox_detail(caption.bbox) if caption.bbox else "",
            "triage_tier": "high",
            "confidence": "high",
            "suggested_fix": (
                f"Correct the figure label “Figure {parsed.number_token}” to a "
                "simple chapter.sequence number (for example, 4.20). Check that "
                "Word/LaTeX caption numbering did not concatenate two auto-numbers, "
                "and make the body caption match the List of Figures entry."
            ),
            "affected_entry_preview": preview,
            "line_preview": sanitize_toc_list_entry_preview(caption.raw_text[:80]),
        },
    )


def _duplicate_finding(
    parsed: _ParsedFigureNumber,
    prior: _ParsedFigureNumber,
) -> AuditFinding:
    caption = parsed.caption
    return AuditFinding(
        rule_id=RULE_ID,
        severity=Severity.WARNING,
        page=caption.page_number,
        message=(
            f"Figure number “{parsed.number_token}” is repeated in chapter "
            f"{parsed.arabic_parts[0] if parsed.arabic_parts else '?'}. "
            "Figure numbers must be unique within each chapter."
        ),
        details={
            "issue_type": "figure_number_duplicate",
            "page": str(caption.page_number),
            "page_type": "body",
            "section_type": "figure_caption",
            "float_type": "figure",
            "number_token": parsed.number_token,
            "prior_page": str(prior.caption.page_number),
            "bbox": format_bbox_detail(caption.bbox) if caption.bbox else "",
            "triage_tier": "high",
            "confidence": "high",
            "suggested_fix": (
                f"Renumber the duplicate “Figure {parsed.number_token}” so each "
                "figure in the chapter has a unique sequence number, and update "
                "the List of Figures to match."
            ),
            "affected_entry_preview": sanitize_toc_list_entry_preview(
                f"Figure {parsed.number_token}"
            ),
        },
    )


def _out_of_order_finding(
    parsed: _ParsedFigureNumber,
    prior: _ParsedFigureNumber,
) -> AuditFinding:
    caption = parsed.caption
    return AuditFinding(
        rule_id=RULE_ID,
        severity=Severity.WARNING,
        page=caption.page_number,
        message=(
            f"Figure number “{parsed.number_token}” appears after "
            f"“{prior.number_token}” in the same chapter. Body figure numbers "
            "should increase in reading order within each chapter."
        ),
        details={
            "issue_type": "figure_number_out_of_order",
            "page": str(caption.page_number),
            "page_type": "body",
            "section_type": "figure_caption",
            "float_type": "figure",
            "number_token": parsed.number_token,
            "prior_number_token": prior.number_token,
            "prior_page": str(prior.caption.page_number),
            "bbox": format_bbox_detail(caption.bbox) if caption.bbox else "",
            "triage_tier": "review",
            "confidence": "medium",
            "suggested_fix": (
                f"Reorder or renumber so “Figure {parsed.number_token}” follows "
                f"earlier figures such as “Figure {prior.number_token}” in "
                "increasing sequence within the chapter."
            ),
            "affected_entry_preview": sanitize_toc_list_entry_preview(
                f"Figure {parsed.number_token}"
            ),
        },
    )


def _malformed_findings(parsed_list: list[_ParsedFigureNumber]) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for parsed in parsed_list:
        if len(parsed.segments) <= _MAX_WELL_FORMED_SEGMENTS:
            continue
        # Require arabic segments so Roman/appendix hybrids are not over-flagged.
        if parsed.arabic_parts is None:
            continue
        findings.append(_malformed_finding(parsed))
    return findings


def _succession_findings(parsed_list: list[_ParsedFigureNumber]) -> list[AuditFinding]:
    """Flag duplicates and decreases among well-formed chapter.sequence labels."""
    by_chapter: dict[int, list[_ParsedFigureNumber]] = defaultdict(list)
    for parsed in parsed_list:
        if parsed.arabic_parts is None:
            continue
        if len(parsed.arabic_parts) != _MAX_WELL_FORMED_SEGMENTS:
            continue
        chapter, _seq = parsed.arabic_parts
        by_chapter[chapter].append(parsed)

    findings: list[AuditFinding] = []
    for chapter in sorted(by_chapter):
        seen: dict[int, _ParsedFigureNumber] = {}
        last: _ParsedFigureNumber | None = None
        # PDF blocks retain extraction order, which can differ from the
        # visible caption order used by the shared caption parser.
        ordered = sorted(
            by_chapter[chapter],
            key=lambda item: (
                item.caption.page_number,
                item.caption.bbox.y0 if item.caption.bbox else float("inf"),
                item.caption.bbox.x0 if item.caption.bbox else float("inf"),
            ),
        )
        for parsed in ordered:
            seq = parsed.arabic_parts[1]  # type: ignore[index]
            prior_same = seen.get(seq)
            if prior_same is not None:
                findings.append(_duplicate_finding(parsed, prior_same))
                continue
            seen[seq] = parsed
            if caption_box := parsed.caption.bbox:
                reliable_geometry = caption_box.width > 0 and caption_box.height > 0
            else:
                reliable_geometry = False
            if not reliable_geometry:
                # Duplicates do not require ordering evidence; a decrease does.
                last = None
                continue
            if (
                last is not None
                and parsed.arabic_parts is not None
                and last.arabic_parts is not None
                and parsed.arabic_parts[1] < last.arabic_parts[1]
            ):
                findings.append(_out_of_order_finding(parsed, last))
            last = parsed
    return findings


def check_pdf_figure_number_structure(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P088 findings for malformed or non-sequential body figure numbers."""
    from njit_auditor.rules.pdf_caption_continuations import detect_logical_caption_lines

    captions = detect_logical_caption_lines(
        pdf_document, page_captions=detect_caption_lines(pdf_document),
    )
    parsed = [
        item
        for item in (_parse_figure_number(caption) for caption in captions)
        if item is not None
    ]
    if not parsed:
        return []
    return _malformed_findings(parsed) + _succession_findings(parsed)
