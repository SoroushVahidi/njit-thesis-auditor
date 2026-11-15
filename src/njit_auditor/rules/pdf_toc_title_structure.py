"""TOC title-structure review for Abstract entries and repeated generic titles (P087).

Batch A coverage for Ester Flaim November 2026 feedback:

* F03 — A dissertation has one front-matter Abstract. Abstract must not appear as a
  Table of Contents entry (including chapter Abstract sections in article-style
  dissertations).
* F02 — Repeated generic TOC titles (Introduction, Methods, Conclusion, …) make
  navigation ambiguous. Emit a conservative review finding with section-number
  context; do not invent replacement titles or ban article-based structures.

Scope: TABLE OF CONTENTS pages only (``detect_toc_like_pages``). LoT/LoF excluded.
Findings carry structural metadata and allowlisted generic labels only — no
dissertation-specific prose beyond the generic title vocabulary.
"""

from __future__ import annotations

import re
from collections import defaultdict

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import BBox, PdfDocument, format_bbox_detail
from njit_auditor.rules.pdf_toc_alignment import (
    TocEntryLine,
    detect_toc_like_pages,
    extract_toc_logical_entry_lines,
)
from njit_auditor.toc_list_student_preview import sanitize_toc_list_entry_preview

RULE_ID = "P087"

# Exact normalized title cores drawn from Ester's November feedback. Abstract is
# handled only by F03 so F02 does not double-warn the same entries.
_GENERIC_TITLE_CORES: frozenset[str] = frozenset(
    {
        "introduction",
        "materials and methods",
        "methods",
        "results and discussion",
        "results",
        "discussion",
        "conclusion",
        "conclusions",
    }
)

_SECTION_NUM_RE = re.compile(r"^(\d+(?:\.\d+)*)(?:\s+|$)")
_CHAPTER_PREFIX_RE = re.compile(
    r"^(?:chapter|appendix)\s+[a-z0-9ivxlcdm]+\s+",
    re.IGNORECASE,
)
_LEADER_TAIL_RE = re.compile(r"(?:\s*[.·…‧⋅•]){2,}.*$")
_ABSTRACT_CORE_RE = re.compile(r"^abstracts?$")


def _strip_page_token(cleaned_text: str, page_token: str | None) -> str:
    text = cleaned_text.strip()
    if page_token:
        text = re.sub(
            rf"(?:\s|{re.escape(page_token)})*{re.escape(page_token)}\s*$",
            "",
            text,
            flags=re.IGNORECASE,
        )
    return text.strip()


def _title_core(cleaned_text: str, page_token: str | None) -> str:
    """Return a normalized TOC title core after number/leader/folio removal."""
    text = _strip_page_token(cleaned_text, page_token)
    text = _LEADER_TAIL_RE.sub("", text).strip()
    text = _CHAPTER_PREFIX_RE.sub("", text).strip()
    text = _SECTION_NUM_RE.sub("", text).strip()
    # Collapse whitespace and case; keep only letters/digits/spaces for matching.
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def _section_number(cleaned_text: str) -> str | None:
    match = _SECTION_NUM_RE.match(cleaned_text.strip())
    if match:
        return match.group(1)
    chapter = re.match(
        r"^(?:chapter|appendix)\s+([a-z0-9ivxlcdm]+)\b",
        cleaned_text.strip(),
        re.IGNORECASE,
    )
    if chapter:
        return chapter.group(1).upper()
    return None


def _is_reliable_toc_entry(entry: TocEntryLine) -> bool:
    """Require a trailing folio so wrapped/non-entry fragments are skipped."""
    return bool(entry.page_number_token) and len(entry.cleaned_text.strip()) >= 8


def _display_title(core: str) -> str:
    if core == "materials and methods":
        return "Materials and Methods"
    if core == "results and discussion":
        return "Results and Discussion"
    return core[:1].upper() + core[1:] if core else core


def _union_bbox(boxes: list[BBox]) -> BBox:
    return BBox(
        x0=min(b.x0 for b in boxes),
        y0=min(b.y0 for b in boxes),
        x1=max(b.x1 for b in boxes),
        y1=max(b.y1 for b in boxes),
    )


def _collect_toc_entries(
    pdf_document: PdfDocument,
) -> list[tuple[int, int, TocEntryLine, str, str | None]]:
    """Return (page, entry_index, entry, title_core, section_number) for TOC pages."""
    collected: list[tuple[int, int, TocEntryLine, str, str | None]] = []
    for context in detect_toc_like_pages(pdf_document):
        if context.page_type != "table_of_contents":
            continue
        entries = extract_toc_logical_entry_lines(context)
        for index, entry in enumerate(entries):
            if not _is_reliable_toc_entry(entry):
                continue
            core = _title_core(entry.cleaned_text, entry.page_number_token)
            if not core:
                continue
            collected.append(
                (
                    context.page.page_number,
                    index,
                    entry,
                    core,
                    _section_number(entry.cleaned_text),
                )
            )
    return collected


def _abstract_findings(
    entries: list[tuple[int, int, TocEntryLine, str, str | None]],
) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for page, index, entry, core, section_number in entries:
        if not _ABSTRACT_CORE_RE.fullmatch(core):
            continue
        section_label = section_number or "this"
        findings.append(
            AuditFinding(
                rule_id=RULE_ID,
                severity=Severity.WARNING,
                page=page,
                message=(
                    "A Table of Contents entry appears to be titled Abstract. "
                    "NJIT dissertations include the Abstract only in the front matter; "
                    "do not list Abstract again in the TOC."
                ),
                details={
                    "issue_type": "toc_abstract_entry_present",
                    "page": str(page),
                    "page_type": "table_of_contents",
                    "section_type": "table_of_contents",
                    "entry_index": str(index),
                    "section_number": section_number or "",
                    "normalized_title": "abstract",
                    "bbox": format_bbox_detail(entry.line.bbox),
                    "triage_tier": "high",
                    "confidence": "high",
                    "suggested_fix": (
                        f"Remove the Abstract TOC entry"
                        f"{f' for section {section_label}' if section_number else ''}. "
                        "Keep only the front-matter Abstract; do not list Abstract in "
                        "the Table of Contents."
                    ),
                    # Structural preview only: sanitized generic label + number.
                    "affected_entry_preview": sanitize_toc_list_entry_preview(
                        f"{section_number + ' ' if section_number else ''}Abstract"
                    ),
                },
            )
        )
    return findings


def _repeated_generic_findings(
    entries: list[tuple[int, int, TocEntryLine, str, str | None]],
) -> list[AuditFinding]:
    by_core: dict[str, list[tuple[int, int, TocEntryLine, str | None]]] = defaultdict(list)
    for page, index, entry, core, section_number in entries:
        if core not in _GENERIC_TITLE_CORES:
            continue
        by_core[core].append((page, index, entry, section_number))

    findings: list[AuditFinding] = []
    for core, occurrences in sorted(by_core.items()):
        if len(occurrences) < 2:
            continue
        # Require at least two distinct section numbers or pages so a single
        # wrapped duplicate of the same entry does not warn.
        section_numbers = [num for _, _, _, num in occurrences if num]
        pages = sorted({page for page, _, _, _ in occurrences})
        if len(set(section_numbers)) < 2 and len(pages) < 2:
            continue

        boxes = [entry.line.bbox for _, _, entry, _ in occurrences]
        first_page, first_index, first_entry, _ = occurrences[0]
        display = _display_title(core)
        number_list = ", ".join(section_numbers) if section_numbers else "multiple sections"
        findings.append(
            AuditFinding(
                rule_id=RULE_ID,
                severity=Severity.WARNING,
                page=first_page,
                message=(
                    f"The Table of Contents repeats the generic heading “{display}” "
                    f"across {len(occurrences)} entries. Repeated article-style titles "
                    "make the TOC hard to navigate because readers cannot tell the "
                    "sections apart."
                ),
                details={
                    "issue_type": "toc_generic_title_repeated",
                    "page": str(first_page),
                    "page_type": "table_of_contents",
                    "section_type": "table_of_contents",
                    "entry_index": str(first_index),
                    "normalized_title": core,
                    "occurrence_count": str(len(occurrences)),
                    "section_numbers": number_list,
                    "occurrence_pages": ",".join(str(p) for p in pages),
                    "bbox": format_bbox_detail(first_entry.line.bbox),
                    "highlight_bboxes": " | ".join(format_bbox_detail(b) for b in boxes),
                    "union_bbox": format_bbox_detail(_union_bbox(boxes)),
                    "triage_tier": "review",
                    "confidence": "medium",
                    "suggested_fix": (
                        f"Review the repeated “{display}” TOC headings"
                        f" ({number_list}). Qualify each with the chapter topic or "
                        "another distinctive title so readers can tell them apart. "
                        "Do not remove legitimate chapter structure; improve the "
                        "heading labels in the TOC."
                    ),
                    "affected_entry_preview": sanitize_toc_list_entry_preview(display),
                },
            )
        )
    return findings


def check_pdf_toc_title_structure(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P087 findings for TOC Abstract entries and repeated generic titles."""
    entries = _collect_toc_entries(pdf_document)
    if not entries:
        return []
    # F03 first; F02 excludes Abstract via allowlist.
    return _abstract_findings(entries) + _repeated_generic_findings(entries)
