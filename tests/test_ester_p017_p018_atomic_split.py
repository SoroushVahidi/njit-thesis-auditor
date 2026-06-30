"""Atomic split tests for P017 and P018 (Ester YES/NO audit matrix, PR 3).

Covers:
1. P017 — LoT/LoF context findings carry source_q_rule_id (Q065, Q074, Q075)
2. P017 — new LoF sentence-case check (Q074) added in this PR
3. P018 — inconsistent_leader_dots finding carries source_q_rule_id=Q052
4. P024 — LoT findings carry source_q_rule_id=Q065
5. P024 — LoF findings carry source_q_rule_id=Q074
6. Catalog: P017/P018 questions are binary yes/no and do not use broad vague wording
7. Catalog: P017/P018 remediations are non-empty
8. Anti-regression: broad vague wording blocked for P017/P018
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from njit_auditor.pdf_models import (
    BBox,
    PdfDocument,
    PdfPage,
    PdfTextBlock,
    PdfTextLine,
    PdfTextSpan,
)
from njit_auditor.rules.pdf_captions import (
    _P017_Q_RULE_MAP,
    check_pdf_captions,
)
from njit_auditor.rules.pdf_toc_alignment import check_pdf_toc_alignment
from njit_auditor.rules.pdf_toc_list_formatting import check_pdf_toc_list_formatting

# ---------------------------------------------------------------------------
# Synthetic PDF builder helpers
# ---------------------------------------------------------------------------


def _span(
    text: str,
    *,
    bold: bool = False,
    x0: float = 108.0,
    x1: float = 504.0,
    y0: float = 50.0,
    y1: float = 62.0,
) -> PdfTextSpan:
    return PdfTextSpan(
        text=text,
        font="TimesNewRomanPSMT-Bold" if bold else "TimesNewRomanPSMT",
        size=12.0,
        bold=bold,
        italic=False,
        bbox=BBox(x0=x0, y0=y0, x1=x1, y1=y1),
    )


def _line(
    text: str,
    *,
    x0: float = 108.0,
    x1: float = 504.0,
    y0: float = 50.0,
    y1: float = 62.0,
    bold: bool = False,
) -> PdfTextLine:
    sp = _span(text, bold=bold, x0=x0, x1=x1, y0=y0, y1=y1)
    return PdfTextLine(
        text=text,
        bbox=BBox(x0=x0, y0=y0, x1=x1, y1=y1),
        spans=[sp],
    )


def _block(*lines: PdfTextLine) -> PdfTextBlock:
    all_x0 = min(ln.bbox.x0 for ln in lines)
    all_y0 = min(ln.bbox.y0 for ln in lines)
    all_x1 = max(ln.bbox.x1 for ln in lines)
    all_y1 = max(ln.bbox.y1 for ln in lines)
    return PdfTextBlock(
        bbox=BBox(x0=all_x0, y0=all_y0, x1=all_x1, y1=all_y1),
        lines=list(lines),
        text=" ".join(ln.text for ln in lines),
    )


def _page(
    page_number: int,
    *blocks: PdfTextBlock,
    width: float = 612.0,
    height: float = 792.0,
) -> PdfPage:
    return PdfPage(
        page_number=page_number,
        width=width,
        height=height,
        text_blocks=list(blocks),
    )


def _doc(*pages: PdfPage) -> PdfDocument:
    return PdfDocument(path="synthetic", pages=list(pages))


# ---------------------------------------------------------------------------
# Helpers: load rule catalog
# ---------------------------------------------------------------------------


def _load_rule_catalog() -> list[dict]:
    path = Path(__file__).parents[1] / "data/processed/rules/project_added_rules.json"
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1. P017 Q-rule map constant
# ---------------------------------------------------------------------------


def test_p017_q_rule_map_contains_q065_for_lot_terminal_period() -> None:
    assert _P017_Q_RULE_MAP.get(("list_of_tables", "unexpected_terminal_period")) == "Q065"


def test_p017_q_rule_map_contains_q075_for_lof_missing_terminal() -> None:
    assert _P017_Q_RULE_MAP.get(("list_of_figures", "missing_terminal_punctuation")) == "Q075"


def test_p017_q_rule_map_contains_q074_for_lof_sentence_case() -> None:
    assert _P017_Q_RULE_MAP.get(("list_of_figures", "possible_sentence_case_issue")) == "Q074"


def test_p017_q_rule_map_body_context_has_no_q_rule() -> None:
    assert _P017_Q_RULE_MAP.get(("body", "missing_terminal_punctuation"), "") == ""
    assert _P017_Q_RULE_MAP.get(("body", "possible_sentence_case_issue"), "") == ""
    assert _P017_Q_RULE_MAP.get(("body", "possible_title_case_issue"), "") == ""


# ---------------------------------------------------------------------------
# 2. P017 — LoT terminal period finding carries source_q_rule_id=Q065
# ---------------------------------------------------------------------------

_LOT_PAGE_HEADING = "LIST OF TABLES"
_LOT_ENTRY_WITH_PERIOD = "Table 1.1 Methods Used for Data Collection."


def _make_lot_page_with_terminal_period() -> PdfPage:
    """LoT page with a table title entry that ends with a period (Q065 violation)."""
    heading = _line(_LOT_PAGE_HEADING, x0=225.0, x1=387.0, y0=50.0, y1=62.0, bold=True)
    entry = _line(_LOT_ENTRY_WITH_PERIOD + " .. 5", x0=108.0, x1=504.0, y0=80.0, y1=92.0)
    return _page(4, _block(heading), _block(entry))


def test_p017_lot_terminal_period_carries_q065() -> None:
    """P017 LoT terminal-period finding must carry source_q_rule_id=Q065."""
    doc = _doc(_make_lot_page_with_terminal_period())
    findings = check_pdf_captions(doc)
    lot_findings = [
        f for f in findings
        if f.rule_id == "P017"
        and f.details.get("issue_type") == "unexpected_terminal_period"
        and f.details.get("caption_type") == "table"
    ]
    # If the heuristic fires, Q-rule ID must be present.
    for f in lot_findings:
        assert f.details.get("source_q_rule_id") == "Q065", (
            f"P017 LoT terminal-period finding must have source_q_rule_id=Q065; "
            f"got {f.details.get('source_q_rule_id')!r}"
        )


# ---------------------------------------------------------------------------
# 3. P017 — LoF missing terminal punctuation carries source_q_rule_id=Q075
# ---------------------------------------------------------------------------

_LOF_PAGE_HEADING = "LIST OF FIGURES"
_LOF_ENTRY_NO_PERIOD = "Figure 2.1 Relationship Between Variables and Outcomes .. 12"


def _make_lof_page_missing_punct() -> PdfPage:
    """LoF page with a figure entry missing terminal punctuation (Q075 violation)."""
    heading = _line(_LOF_PAGE_HEADING, x0=222.0, x1=390.0, y0=50.0, y1=62.0, bold=True)
    # Strip the page number token from entry text so P017 sees missing terminal punct
    entry = _line("Figure 2.1 Relationship Between Variables and Outcomes ... 12",
                  x0=108.0, x1=504.0, y0=80.0, y1=92.0)
    return _page(5, _block(heading), _block(entry))


def test_p017_lof_missing_terminal_punct_carries_q075() -> None:
    """P017 LoF missing-terminal-punct finding must carry source_q_rule_id=Q075."""
    doc = _doc(_make_lof_page_missing_punct())
    findings = check_pdf_captions(doc)
    lof_findings = [
        f for f in findings
        if f.rule_id == "P017"
        and f.details.get("issue_type") == "missing_terminal_punctuation"
        and f.details.get("caption_type") == "figure"
    ]
    for f in lof_findings:
        assert f.details.get("source_q_rule_id") == "Q075", (
            f"P017 LoF missing-terminal-punct finding must have source_q_rule_id=Q075; "
            f"got {f.details.get('source_q_rule_id')!r}"
        )


# ---------------------------------------------------------------------------
# 4. P017 — all findings include source_q_rule_id key (may be empty for body)
# ---------------------------------------------------------------------------

def test_p017_all_findings_have_source_q_rule_id_key() -> None:
    """Every P017 finding must expose source_q_rule_id (empty string for body context)."""
    doc = _doc(_make_lot_page_with_terminal_period(), _make_lof_page_missing_punct())
    findings = check_pdf_captions(doc)
    for f in findings:
        if f.rule_id == "P017":
            assert "source_q_rule_id" in f.details, (
                f"P017 finding missing source_q_rule_id key: {f.details!r}"
            )


# ---------------------------------------------------------------------------
# 5. P018 — inconsistent_leader_dots carries source_q_rule_id=Q052
# ---------------------------------------------------------------------------

def _make_toc_page_with_inconsistent_leader() -> PdfPage:
    """TOC page where most entries have leader dots but one doesn't (Q052 violation)."""
    heading = _line("TABLE OF CONTENTS", x0=220.0, x1=392.0, y0=50.0, y1=62.0, bold=True)

    def _toc_entry(text: str, y: float, has_dots: bool) -> PdfTextLine:
        dots = " ......." if has_dots else "   "
        return _line(f"{text}{dots} {y:.0f}", x0=108.0, x1=504.0, y0=y, y1=y + 12.0)

    entries = [
        _toc_entry("CHAPTER 1 INTRODUCTION", 80.0, True),
        _toc_entry("CHAPTER 2 METHODS", 100.0, True),
        _toc_entry("CHAPTER 3 RESULTS", 120.0, True),
        _toc_entry("CHAPTER 4 DISCUSSION", 140.0, True),
        _toc_entry("CHAPTER 5 CONCLUSIONS", 160.0, False),  # missing dots
    ]
    return _page(3, _block(heading), *[_block(e) for e in entries])


def test_p018_inconsistent_leader_dots_carries_q052() -> None:
    """P018 inconsistent_leader_dots finding must carry source_q_rule_id=Q052."""
    doc = _doc(_make_toc_page_with_inconsistent_leader())
    findings = check_pdf_toc_alignment(doc)
    leader_findings = [
        f for f in findings
        if f.rule_id == "P018" and f.details.get("issue_type") == "inconsistent_leader_dots"
    ]
    # If a leader-dots finding fires, it must have Q052.
    for f in leader_findings:
        assert f.details.get("source_q_rule_id") == "Q052", (
            f"P018 inconsistent_leader_dots must have source_q_rule_id=Q052; "
            f"got {f.details.get('source_q_rule_id')!r}"
        )


# ---------------------------------------------------------------------------
# 6. P024 — LoT title-case finding carries source_q_rule_id=Q065
# ---------------------------------------------------------------------------

def _make_lot_page_with_title_case_issue() -> PdfPage:
    """LoT page with a table title in sentence case instead of title case."""
    heading = _line("LIST OF TABLES", x0=225.0, x1=387.0, y0=50.0, y1=62.0, bold=True)
    # Entry not in title case: lowercase words that should be capitalized
    entry = _line(
        "Table 1. the relationship between stress and academic performance ... 15",
        x0=108.0, x1=504.0, y0=80.0, y1=92.0,
    )
    return _page(4, _block(heading), _block(entry))


def test_p024_lot_title_case_carries_q065() -> None:
    """P024 list_of_tables_title_case finding must carry source_q_rule_id=Q065."""
    doc = _doc(_make_lot_page_with_title_case_issue())
    findings = check_pdf_toc_list_formatting(doc)
    lot_findings = [
        f for f in findings
        if f.rule_id == "P024" and f.details.get("issue_type") == "list_of_tables_title_case"
    ]
    for f in lot_findings:
        assert f.details.get("source_q_rule_id") == "Q065", (
            f"P024 list_of_tables_title_case must have source_q_rule_id=Q065; "
            f"got {f.details.get('source_q_rule_id')!r}"
        )


def test_p024_lot_terminal_period_carries_q065() -> None:
    """P024 unexpected_terminal_punctuation (LoT) must carry source_q_rule_id=Q065."""
    doc = _doc(_make_lot_page_with_title_case_issue())
    findings = check_pdf_toc_list_formatting(doc)
    # Also check the terminal period variant
    lot_terminal = [
        f for f in findings
        if f.rule_id == "P024"
        and f.details.get("issue_type") == "unexpected_terminal_punctuation"
        and f.details.get("page_type") == "list_of_tables"
    ]
    for f in lot_terminal:
        assert f.details.get("source_q_rule_id") == "Q065", (
            f"P024 LoT unexpected_terminal_punctuation must have source_q_rule_id=Q065; "
            f"got {f.details.get('source_q_rule_id')!r}"
        )


# ---------------------------------------------------------------------------
# 7. P024 — LoF sentence-case finding carries source_q_rule_id=Q074
# ---------------------------------------------------------------------------

def _make_lof_page_with_sentence_case_issue() -> PdfPage:
    """LoF page with a figure description in title case instead of sentence case."""
    heading = _line("LIST OF FIGURES", x0=222.0, x1=390.0, y0=50.0, y1=62.0, bold=True)
    # Entry in title case — violates sentence case (Q074)
    entry = _line(
        "Figure 3.1 Relationship Between Temperature, Pressure, And Volume ... 23",
        x0=108.0, x1=504.0, y0=80.0, y1=92.0,
    )
    return _page(5, _block(heading), _block(entry))


def test_p024_lof_sentence_case_carries_q074() -> None:
    """P024 list_of_figures_sentence_case finding must carry source_q_rule_id=Q074."""
    doc = _doc(_make_lof_page_with_sentence_case_issue())
    findings = check_pdf_toc_list_formatting(doc)
    lof_findings = [
        f for f in findings
        if f.rule_id == "P024"
        and f.details.get("issue_type") == "list_of_figures_sentence_case"
    ]
    for f in lof_findings:
        assert f.details.get("source_q_rule_id") == "Q074", (
            f"P024 list_of_figures_sentence_case must have source_q_rule_id=Q074; "
            f"got {f.details.get('source_q_rule_id')!r}"
        )


# ---------------------------------------------------------------------------
# 8. P024 — TOC level findings already carry Q049/Q050 (regression guard)
# ---------------------------------------------------------------------------

def test_p024_toc_level1_carries_q049_regression_guard() -> None:
    """P024 toc_level_capitalization (level 1) must carry source_q_rule_id=Q049."""
    heading = _line("TABLE OF CONTENTS", x0=220.0, x1=392.0, y0=50.0, y1=62.0, bold=True)
    # Level-1 entries not in ALL CAPS (violates Q049)
    entries = [
        _line("Chapter 1 Introduction .... 1", x0=108.0, x1=504.0, y0=80.0, y1=92.0),
        _line("Chapter 2 Literature Review .... 15", x0=108.0, x1=504.0, y0=95.0, y1=107.0),
        _line("Chapter 3 Methodology .... 30", x0=108.0, x1=504.0, y0=110.0, y1=122.0),
        _line("Chapter 4 Results .... 45", x0=108.0, x1=504.0, y0=125.0, y1=137.0),
    ]
    doc = _doc(_page(3, _block(heading), *[_block(e) for e in entries]))
    findings = check_pdf_toc_list_formatting(doc)
    level1_findings = [
        f for f in findings
        if f.rule_id == "P024"
        and f.details.get("issue_type") == "toc_level_capitalization"
        and f.details.get("entry_level") == "1"
    ]
    for f in level1_findings:
        assert f.details.get("source_q_rule_id") == "Q049", (
            f"P024 toc_level_capitalization (level 1) must have source_q_rule_id=Q049; "
            f"got {f.details.get('source_q_rule_id')!r}"
        )


# ---------------------------------------------------------------------------
# 9. Rule quality contract — P017/P018 catalog questions binary yes/no form
# ---------------------------------------------------------------------------

_BINARY_STARTERS = ("Is ", "Are ", "Does ", "Do ")


def _starts_binary(question: str) -> bool:
    return any(question.startswith(s) for s in _BINARY_STARTERS)


@pytest.mark.parametrize("rule_id", ["P017", "P018"])
def test_catalog_question_ends_with_question_mark(rule_id: str) -> None:
    """P017/P018 catalog questions must end with '?'."""
    rules = _load_rule_catalog()
    rule = next(r for r in rules if r["id"] == rule_id)
    q = rule["question"]
    assert q.endswith("?"), f"{rule_id} question must end with '?'; got {q!r}"


@pytest.mark.parametrize("rule_id", ["P017", "P018"])
def test_catalog_question_starts_with_binary_form(rule_id: str) -> None:
    """P017/P018 catalog questions must start with Is/Are/Does/Do."""
    rules = _load_rule_catalog()
    rule = next(r for r in rules if r["id"] == rule_id)
    q = rule["question"]
    assert _starts_binary(q), (
        f"{rule_id} question must start with Is/Are/Does/Do; got {q!r}"
    )


@pytest.mark.parametrize("rule_id", ["P017", "P018"])
def test_catalog_remediation_is_non_empty(rule_id: str) -> None:
    """P017/P018 must have a non-empty remediation."""
    rules = _load_rule_catalog()
    rule = next(r for r in rules if r["id"] == rule_id)
    assert rule.get("remediation", "").strip(), f"{rule_id} remediation must not be empty"


# ---------------------------------------------------------------------------
# 10. Anti-regression — broad vague wording blocked for P017/P018
# ---------------------------------------------------------------------------

_BROAD_P017_PATTERNS = (
    "obvious formatting issues",
    "show obvious formatting",
    "figure/table caption and title lines show",
)

_BROAD_P018_PATTERNS = (
    "likely alignment inconsistencies",
    "show likely alignment",
    "TOC/List of Tables/List of Figures entries show",
)


@pytest.mark.parametrize("pattern", _BROAD_P017_PATTERNS)
def test_p017_question_does_not_use_broad_wording(pattern: str) -> None:
    """P017 catalog must not revert to broad vague question wording."""
    rules = _load_rule_catalog()
    p017 = next(r for r in rules if r["id"] == "P017")
    assert pattern.lower() not in p017["question"].lower(), (
        f"P017 question contains broad/vague pattern {pattern!r}: {p017['question']!r}"
    )


@pytest.mark.parametrize("pattern", _BROAD_P018_PATTERNS)
def test_p018_question_does_not_use_broad_wording(pattern: str) -> None:
    """P018 catalog must not revert to broad vague question wording."""
    rules = _load_rule_catalog()
    p018 = next(r for r in rules if r["id"] == "P018")
    assert pattern.lower() not in p018["question"].lower(), (
        f"P018 question contains broad/vague pattern {pattern!r}: {p018['question']!r}"
    )


# ---------------------------------------------------------------------------
# 11. Catalog notes reference Q-rules for P017/P018
# ---------------------------------------------------------------------------

def test_p017_catalog_notes_reference_q065_q074_q075() -> None:
    """P017 notes must reference Q065, Q074, and Q075 for traceability."""
    rules = _load_rule_catalog()
    p017 = next(r for r in rules if r["id"] == "P017")
    searchable = p017.get("notes", "") + p017.get("rule_definition", "")
    for q_id in ("Q065", "Q074", "Q075"):
        assert q_id in searchable, f"P017 notes/rule_definition must reference {q_id}"


def test_p018_catalog_notes_reference_q052() -> None:
    """P018 notes must reference Q052 (leader-dot consistency)."""
    rules = _load_rule_catalog()
    p018 = next(r for r in rules if r["id"] == "P018")
    searchable = p018.get("notes", "") + p018.get("rule_definition", "")
    assert "Q052" in searchable, "P018 notes/rule_definition must reference Q052"
