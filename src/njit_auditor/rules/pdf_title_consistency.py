"""Conservative cross-page dissertation title consistency checks (P033).

Compares normalized title-like text on Title Page, Abstract page, and Approval Page
when at least two candidates are confidently extracted from the PDF text layer.
Does not quote title text in findings.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, PdfPage, PdfTextLine
from njit_auditor.rules.pdf_frontmatter_structure import (
    _DEGREE_RE,
    _INSTITUTION_RE,
)
from njit_auditor.rules.pdf_headings import (
    find_named_frontmatter_headings,
    normalize_heading_text,
)

_ABSTRACT_HEADING = "ABSTRACT"
_APPROVAL_HEADING = "APPROVAL PAGE"
_MIN_DOC_PAGES = 3
_TITLE_ZONE_MAX_Y_RATIO = 0.68
_MIN_CONFIDENT_NORMALIZED_LEN = 12
_MIN_CONFIDENT_WORDS = 3
_MATERIAL_MISMATCH_SIMILARITY = 0.92

_NAMED_HEADINGS = frozenset(
    {
        "ABSTRACT",
        "APPROVAL PAGE",
        "TABLE OF CONTENTS",
        "LIST OF TABLES",
        "LIST OF FIGURES",
        "DEDICATION",
        "COPYRIGHT PAGE",
        "BIOGRAPHICAL SKETCH",
        "ACKNOWLEDGEMENTS",
        "ACKNOWLEDGMENTS",
    }
)

_STOP_TITLE_LINE_RE = re.compile(
    r"^(by|submitted|a dissertation|a thesis|in partial fulfillment|"
    r"dissertation committee|date:)\b",
    re.IGNORECASE,
)
_MONTH_YEAR_RE = re.compile(
    r"^(january|february|march|april|may|june|july|august|september|"
    r"october|november|december)\s+\d{4}$",
    re.IGNORECASE,
)
_AUTHOR_LIKE_RE = re.compile(r"^dr\.?\s", re.IGNORECASE)


@dataclass(frozen=True)
class TitleCandidate:
    page_number: int
    page_role: str
    normalized: str
    title_hash: str
    confidence: str
    raw_word_count: int


def _stable_title_hash(normalized: str) -> str:
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def normalize_title_for_comparison(text: str) -> str:
    """Lowercase, collapse whitespace, strip punctuation, normalize dash variants."""

    lowered = text.lower().replace("\u00a0", " ")
    lowered = re.sub(r"[\u2010\u2011\u2012\u2013\u2014\u2212-]+", " ", lowered)
    lowered = re.sub(r"[^\w\s]", "", lowered)
    return " ".join(lowered.split())


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def _is_metadata_or_noise_line(cleaned: str) -> bool:
    if not cleaned:
        return True
    upper = cleaned.upper()
    if upper in _NAMED_HEADINGS:
        return True
    if _STOP_TITLE_LINE_RE.match(cleaned):
        return True
    if _DEGREE_RE.search(cleaned) or _INSTITUTION_RE.search(cleaned):
        return True
    if _MONTH_YEAR_RE.match(cleaned):
        return True
    if _AUTHOR_LIKE_RE.match(cleaned):
        return True
    if re.fullmatch(r"\d{4}", cleaned):
        return True
    if len(cleaned) <= 2:
        return True
    return False


def _confidence_for_title_text(text: str, normalized: str) -> str:
    words = normalized.split()
    if len(normalized) < _MIN_CONFIDENT_NORMALIZED_LEN or len(words) < _MIN_CONFIDENT_WORDS:
        return "low"
    return "high"


def _sorted_lines(page: PdfPage) -> list[PdfTextLine]:
    lines = [line for block in page.text_blocks for line in block.lines]
    return sorted(lines, key=lambda line: (line.bbox.y0, line.bbox.x0))


def _join_title_lines(parts: list[str]) -> str | None:
    if not parts:
        return None
    combined = " ".join(parts).strip()
    if not combined:
        return None
    normalized = normalize_title_for_comparison(combined)
    if not normalized:
        return None
    confidence = _confidence_for_title_text(combined, normalized)
    if confidence == "low":
        return None
    return combined


def _extract_title_page_candidate(page: PdfPage) -> str | None:
    parts: list[str] = []
    y_limit = page.height * _TITLE_ZONE_MAX_Y_RATIO
    for line in _sorted_lines(page):
        if line.bbox.y0 > y_limit:
            break
        cleaned = normalize_heading_text(line.text)
        if _is_metadata_or_noise_line(cleaned):
            if _STOP_TITLE_LINE_RE.match(cleaned) or _DEGREE_RE.search(cleaned):
                break
            continue
        parts.append(cleaned)
    return _join_title_lines(parts)


def _extract_above_heading_candidate(page: PdfPage, heading: str) -> str | None:
    lines = _sorted_lines(page)
    heading_y: float | None = None
    for line in lines:
        if normalize_heading_text(line.text).upper() == heading:
            heading_y = line.bbox.y0
            break
    if heading_y is None:
        return None

    parts: list[str] = []
    for line in lines:
        if line.bbox.y0 >= heading_y - 2:
            continue
        cleaned = normalize_heading_text(line.text)
        if _is_metadata_or_noise_line(cleaned):
            continue
        parts.append(cleaned)
    return _join_title_lines(parts)


def _build_candidate(page_number: int, page_role: str, raw_title: str) -> TitleCandidate:
    normalized = normalize_title_for_comparison(raw_title)
    return TitleCandidate(
        page_number=page_number,
        page_role=page_role,
        normalized=normalized,
        title_hash=_stable_title_hash(normalized),
        confidence=_confidence_for_title_text(raw_title, normalized),
        raw_word_count=len(normalized.split()),
    )


def _collect_title_candidates(pdf_document: PdfDocument) -> list[TitleCandidate]:
    if len(pdf_document.pages) < _MIN_DOC_PAGES:
        return []

    headings = find_named_frontmatter_headings(pdf_document)
    if not headings:
        return []

    heading_pages = {match.heading: match.page_number for match in headings}
    pages_by_number = {page.page_number: page for page in pdf_document.pages}
    candidates: list[TitleCandidate] = []

    title_page = pdf_document.pages[0]
    title_raw = _extract_title_page_candidate(title_page)
    if title_raw:
        candidates.append(_build_candidate(title_page.page_number, "title_page", title_raw))

    abstract_page_num = heading_pages.get(_ABSTRACT_HEADING)
    if abstract_page_num is not None:
        page = pages_by_number.get(abstract_page_num)
        if page is not None:
            abstract_raw = _extract_above_heading_candidate(page, _ABSTRACT_HEADING)
            if abstract_raw:
                candidates.append(
                    _build_candidate(page.page_number, "abstract", abstract_raw)
                )

    approval_page_num = heading_pages.get(_APPROVAL_HEADING)
    if approval_page_num is not None:
        page = pages_by_number.get(approval_page_num)
        if page is not None:
            approval_raw = _extract_above_heading_candidate(page, _APPROVAL_HEADING)
            if approval_raw:
                candidates.append(
                    _build_candidate(page.page_number, "approval_page", approval_raw)
                )

    return [c for c in candidates if c.confidence == "high"]


def check_pdf_title_consistency(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P033 warnings when front-matter title candidates differ materially."""

    candidates = _collect_title_candidates(pdf_document)
    if len(candidates) < 2:
        return []

    reference = candidates[0]
    mismatched: list[TitleCandidate] = []
    pages_compared: list[int] = []
    hashes_by_role: dict[str, str] = {}
    similarities: list[str] = []

    for candidate in candidates:
        pages_compared.append(candidate.page_number)
        hashes_by_role[candidate.page_role] = candidate.title_hash
        sim = _similarity(reference.normalized, candidate.normalized)
        similarities.append(f"{candidate.page_role}:{sim:.3f}")
        if (
            candidate.page_role != reference.page_role
            and candidate.normalized != reference.normalized
            and sim < _MATERIAL_MISMATCH_SIMILARITY
        ):
            mismatched.append(candidate)

    if not mismatched:
        return []

    mismatch_pages = sorted({c.page_number for c in mismatched})
    min_sim = min(
        _similarity(reference.normalized, c.normalized) for c in mismatched
    )

    return [
        AuditFinding(
            rule_id="P033",
            severity=Severity.WARNING,
            page=mismatch_pages[0],
            message=(
                "Dissertation title text on front-matter pages may be inconsistent "
                "(normalized comparison across title, abstract, and/or approval pages)."
            ),
            details={
                "issue_type": "frontmatter_title_mismatch",
                "pages_compared": ",".join(str(p) for p in sorted(set(pages_compared))),
                "mismatch_pages": ",".join(str(p) for p in mismatch_pages),
                "candidate_count": str(len(candidates)),
                "comparison_basis": "normalized_text_hash_and_sequence_similarity",
                "reference_page_role": reference.page_role,
                "reference_title_hash": reference.title_hash,
                "title_hashes_by_role": ",".join(
                    f"{role}={digest}" for role, digest in sorted(hashes_by_role.items())
                ),
                "similarity_scores": ",".join(similarities),
                "min_similarity_to_reference": f"{min_sim:.3f}",
                "confidence": "high",
            },
        )
    ]
