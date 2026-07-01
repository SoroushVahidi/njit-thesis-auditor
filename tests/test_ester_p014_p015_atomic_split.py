"""Atomic split tests for P014 and P015 (Ester YES/NO audit matrix, PR 2).

Covers:
1. P014 — each named heading finding includes source_q_rule_id
   Q013=Approval Page, Q021=Biographical Sketch, Q036=Acknowledgements,
   Q047=TOC, Q061=List of Tables, Q070=List of Figures
2. P015 — body-text-only scope: no longer fires on Abstract or Acknowledgements pages
   (Q002/Q003 handled atomically by P044; Q044/Q045 handled atomically by P043)
3. P043 — Q044/Q045 already atomic; regression guard
4. P044 — Q002/Q003 already atomic; regression guard
5. Rule catalog entries reflect narrowed scope
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
from njit_auditor.rules.pdf_headings import check_named_frontmatter_headings
from njit_auditor.rules.pdf_indentation import (
    _P015_EXCLUDED_HEADINGS,
    _find_excluded_page_numbers,
    check_pdf_indentation,
)

# ---------------------------------------------------------------------------
# Synthetic PDF builder helpers
# ---------------------------------------------------------------------------

_ZERO_BBOX = BBox(x0=0.0, y0=0.0, x1=0.0, y1=0.0)


def _span(text: str, *, bold: bool = False, x0: float = 108.0, x1: float = 504.0,
          y0: float = 50.0, y1: float = 62.0) -> PdfTextSpan:
    return PdfTextSpan(
        text=text,
        font="TimesNewRomanPSMT-Bold" if bold else "TimesNewRomanPSMT",
        size=12.0,
        bold=bold,
        italic=False,
        bbox=BBox(x0=x0, y0=y0, x1=x1, y1=y1),
    )


def _line(text: str, *, x0: float = 108.0, x1: float = 504.0, y0: float = 50.0,
          y1: float = 62.0, bold: bool = False) -> PdfTextLine:
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
    combined_text = " ".join(ln.text for ln in lines)
    return PdfTextBlock(
        bbox=BBox(x0=all_x0, y0=all_y0, x1=all_x1, y1=all_y1),
        lines=list(lines),
        text=combined_text,
    )


def _page(page_number: int, *blocks: PdfTextBlock, width: float = 612.0,
          height: float = 792.0) -> PdfPage:
    return PdfPage(
        page_number=page_number,
        width=width,
        height=height,
        text_blocks=list(blocks),
    )


def _doc(*pages: PdfPage) -> PdfDocument:
    return PdfDocument(path="synthetic", pages=list(pages))


# ---------------------------------------------------------------------------
# 1. P014 — source_q_rule_id present in findings
# ---------------------------------------------------------------------------

_HEADING_Q_RULE_CASES: list[tuple[str, str]] = [
    ("APPROVAL PAGE", "Q013"),
    ("BIOGRAPHICAL SKETCH", "Q021"),
    ("ACKNOWLEDGEMENTS", "Q036"),
    ("TABLE OF CONTENTS", "Q047"),
    ("LIST OF TABLES", "Q061"),
    ("LIST OF FIGURES", "Q070"),
]


@pytest.mark.parametrize("heading,expected_q_rule_id", _HEADING_Q_RULE_CASES)
def test_p014_finding_includes_source_q_rule_id(
    heading: str, expected_q_rule_id: str
) -> None:
    """P014 finding details must include source_q_rule_id for each heading."""
    # Place heading far from center so it triggers a finding (not centered).
    heading_line = _line(heading, x0=450.0, x1=550.0, y0=50.0, y1=62.0, bold=True)
    doc = _doc(_page(1, _block(heading_line)))
    findings = check_named_frontmatter_headings(doc)
    p014 = [f for f in findings if f.rule_id == "P014" and f.details.get("heading") == heading]
    assert p014, f"Expected a P014 finding for {heading!r}"
    assert p014[0].details.get("source_q_rule_id") == expected_q_rule_id, (
        f"Expected source_q_rule_id={expected_q_rule_id!r} for {heading!r}, "
        f"got {p014[0].details.get('source_q_rule_id')!r}"
    )


def test_p014_abstract_finding_has_empty_q_rule_id() -> None:
    """ABSTRACT heading has no Q-rule in P014; source_q_rule_id should be empty string."""
    heading_line = _line("ABSTRACT", x0=450.0, x1=540.0, y0=50.0, y1=62.0, bold=True)
    doc = _doc(_page(1, _block(heading_line)))
    findings = check_named_frontmatter_headings(doc)
    p014 = [f for f in findings if f.rule_id == "P014" and f.details.get("heading") == "ABSTRACT"]
    if p014:
        assert p014[0].details.get("source_q_rule_id") == "", (
            "ABSTRACT P014 finding should have empty source_q_rule_id"
        )


def test_p014_no_finding_for_correct_heading() -> None:
    """No P014 finding when heading is centered, bold, near top, all caps."""
    # Text area x0=108 (1.5 in), x1=540 (612-72). Center = 324.
    # Line from 279 to 369 → center = 324.
    heading_line = _line(
        "APPROVAL PAGE", x0=279.0, x1=369.0, y0=50.0, y1=62.0, bold=True
    )
    doc = _doc(_page(1, _block(heading_line)))
    findings = check_named_frontmatter_headings(doc)
    p014 = [f for f in findings if f.rule_id == "P014"]
    assert not p014, f"Unexpected P014 findings for correct heading: {p014}"


def test_p014_all_headings_in_q_rule_map_have_distinct_q_ids() -> None:
    """Each heading in _HEADING_Q_RULE_CASES has a unique Q-rule ID."""
    q_ids = [q for _, q in _HEADING_Q_RULE_CASES]
    assert len(q_ids) == len(set(q_ids)), "Duplicate Q-rule IDs in heading map"


# ---------------------------------------------------------------------------
# 2. P015 — excluded headings constant
# ---------------------------------------------------------------------------

def test_p015_excluded_headings_contains_abstract() -> None:
    assert "ABSTRACT" in _P015_EXCLUDED_HEADINGS


def test_p015_excluded_headings_contains_acknowledgements() -> None:
    assert "ACKNOWLEDGEMENTS" in _P015_EXCLUDED_HEADINGS


# ---------------------------------------------------------------------------
# 3. P015 — does not fire on Abstract pages
# ---------------------------------------------------------------------------

_BODY_TEXT = "Lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod."


def _body_line(y0: float, *, indent: bool, left_margin: float = 108.0) -> PdfTextLine:
    x0 = left_margin + (36.0 if indent else 0.0)
    return _line(_BODY_TEXT, x0=x0, x1=504.0, y0=y0, y1=y0 + 12.0)


def _make_abstract_page() -> PdfPage:
    """Abstract page with indented first paragraph (Q002 violation) and indented second."""
    heading = _line("ABSTRACT", x0=261.0, x1=351.0, y0=50.0, y1=62.0, bold=True)
    # First paragraph indented (violates Q002 — should be caught by P044 not P015)
    para1 = [_body_line(80.0 + i * 14.0, indent=(i == 0)) for i in range(4)]
    # Second paragraph indented (correct for Q003)
    para2 = [_body_line(150.0 + i * 14.0, indent=(i == 0)) for i in range(4)]
    return _page(3, _block(heading), _block(*para1), _block(*para2))


def test_p015_does_not_fire_on_abstract_page() -> None:
    """P015 must not emit findings on the Abstract page; P044 handles Q002/Q003."""
    doc = _doc(_make_abstract_page())
    findings = check_pdf_indentation(doc)
    p015 = [f for f in findings if f.rule_id == "P015"]
    assert not p015, (
        f"P015 should not fire on Abstract page; P044 handles Q002/Q003. Got: {p015}"
    )


def test_p015_find_excluded_pages_includes_abstract_page() -> None:
    doc = _doc(_make_abstract_page())
    excluded = _find_excluded_page_numbers(doc)
    assert 3 in excluded


# ---------------------------------------------------------------------------
# 4. P015 — does not fire on Acknowledgements pages
# ---------------------------------------------------------------------------

def _make_ack_page() -> PdfPage:
    """Acknowledgements page with a later paragraph missing indent (Q045 violation)."""
    heading = _line(
        "ACKNOWLEDGEMENTS", x0=220.0, x1=392.0, y0=50.0, y1=62.0, bold=True
    )
    # First paragraph flush-left (correct for Q044)
    para1 = [_body_line(80.0 + i * 14.0, indent=False) for i in range(4)]
    # Second paragraph indented (correct for Q045)
    para2 = [_body_line(150.0 + i * 14.0, indent=(i == 0)) for i in range(4)]
    # Third paragraph NOT indented (violates Q045 — should be caught by P043)
    para3 = [_body_line(220.0 + i * 14.0, indent=False) for i in range(4)]
    return _page(5, _block(heading), _block(*para1), _block(*para2), _block(*para3))


def test_p015_does_not_fire_on_acknowledgements_page() -> None:
    """P015 must not emit findings on the Acknowledgements page; P043 handles Q044/Q045."""
    doc = _doc(_make_ack_page())
    findings = check_pdf_indentation(doc)
    p015 = [f for f in findings if f.rule_id == "P015"]
    assert not p015, (
        f"P015 should not fire on Acknowledgements page; P043 handles Q044/Q045. Got: {p015}"
    )


def test_p015_find_excluded_pages_includes_ack_page() -> None:
    doc = _doc(_make_ack_page())
    excluded = _find_excluded_page_numbers(doc)
    assert 5 in excluded


# ---------------------------------------------------------------------------
# 5. P015 — still fires on body-text pages
# ---------------------------------------------------------------------------

def _make_body_page(page_number: int) -> PdfPage:
    """Body page: 2 indented paragraphs + 1 flush-left anomaly → missing_later_indent."""
    para1 = [_body_line(80.0 + i * 14.0, indent=(i == 0)) for i in range(4)]
    para2 = [_body_line(150.0 + i * 14.0, indent=(i == 0)) for i in range(4)]
    # Third paragraph flush-left (anomaly on a page with established indent style)
    para3 = [_body_line(220.0 + i * 14.0, indent=False) for i in range(4)]
    return _page(page_number, _block(*para1), _block(*para2), _block(*para3))


def test_p015_still_fires_on_body_text_page() -> None:
    """P015 must still emit missing_later_indent on body text pages."""
    doc = _doc(_make_body_page(page_number=10))
    findings = check_pdf_indentation(doc)
    p015 = [f for f in findings if f.rule_id == "P015"]
    assert p015, "P015 should emit missing_later_indent on body text pages"
    assert all(f.details.get("issue_type") == "missing_later_indent" for f in p015)


def test_p015_body_page_not_in_excluded_pages() -> None:
    doc = _doc(_make_body_page(page_number=10))
    excluded = _find_excluded_page_numbers(doc)
    assert 10 not in excluded


# ---------------------------------------------------------------------------
# 6. P015 — multi-page: fires on body pages, skips abstract/ack pages
# ---------------------------------------------------------------------------

def test_p015_multi_page_skips_excluded_fires_on_body() -> None:
    doc = _doc(_make_abstract_page(), _make_ack_page(), _make_body_page(page_number=20))
    findings = check_pdf_indentation(doc)
    p015 = [f for f in findings if f.rule_id == "P015"]
    assert not any(f.page in {3, 5} for f in p015), (
        f"P015 must not fire on abstract (p3) or ack (p5). Got pages: {[f.page for f in p015]}"
    )
    assert any(f.page == 20 for f in p015), "P015 should fire on body page 20"


# ---------------------------------------------------------------------------
# 7. Rule catalog — P014 question references Q-rule IDs
# ---------------------------------------------------------------------------

def _load_rule_catalog() -> list[dict]:
    path = Path(__file__).parents[1] / "data/processed/rules/project_added_rules.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_p014_catalog_notes_references_q_rule_ids() -> None:
    """Q-rule IDs must appear in P014 notes (not the question, which must stay concise)."""
    rules = _load_rule_catalog()
    p014 = next(r for r in rules if r["id"] == "P014")
    searchable = p014.get("notes", "") + p014.get("rule_definition", "")
    for q_id in ("Q013", "Q021", "Q036", "Q047", "Q061", "Q070"):
        assert q_id in searchable, f"P014 notes/rule_definition should reference {q_id}"


def test_p014_catalog_remediation_references_heading_names() -> None:
    rules = _load_rule_catalog()
    p014 = next(r for r in rules if r["id"] == "P014")
    rem = p014["remediation"]
    for heading in ("APPROVAL PAGE", "ACKNOWLEDGEMENTS", "TABLE OF CONTENTS"):
        assert heading in rem, f"P014 remediation should mention '{heading}'"


# ---------------------------------------------------------------------------
# 8. Rule catalog — P015 scoped to body text
# ---------------------------------------------------------------------------

def test_p015_catalog_question_scoped_to_body_text() -> None:
    rules = _load_rule_catalog()
    p015 = next(r for r in rules if r["id"] == "P015")
    q = p015["question"].lower()
    assert "body" in q, "P015 question should scope to body text"


def test_p015_catalog_remediation_references_p043_p044() -> None:
    rules = _load_rule_catalog()
    p015 = next(r for r in rules if r["id"] == "P015")
    rem = p015["remediation"]
    assert "P044" in rem, "P015 remediation should point to P044 for Abstract indentation"
    assert "P043" in rem, "P015 remediation should point to P043 for Acknowledgements indentation"


# ---------------------------------------------------------------------------
# 9. P043 regression guard — Q044/Q045 are atomic
# ---------------------------------------------------------------------------

def test_p043_catalog_references_q044_q045() -> None:
    rules = _load_rule_catalog()
    p043 = next(r for r in rules if r["id"] == "P043")
    notes = p043.get("notes", "") + p043.get("rule_definition", "")
    assert "Q044" in notes, "P043 should reference Q044"
    assert "Q045" in notes, "P043 should reference Q045"


# ---------------------------------------------------------------------------
# 10. P044 regression guard — Q002/Q003 are atomic
# ---------------------------------------------------------------------------

def test_p044_catalog_references_q002_q003() -> None:
    rules = _load_rule_catalog()
    p044 = next(r for r in rules if r["id"] == "P044")
    notes = p044.get("notes", "") + p044.get("rule_definition", "")
    assert "Q002" in notes, "P044 should reference Q002"
    assert "Q003" in notes, "P044 should reference Q003"


# ---------------------------------------------------------------------------
# 11. Rule quality contract — P014/P015 only (Ester binary yes/no enforcement)
# ---------------------------------------------------------------------------

_BINARY_STARTERS = ("Is ", "Are ", "Does ", "Do ")


def _starts_binary(question: str) -> bool:
    return any(question.startswith(s) for s in _BINARY_STARTERS)


@pytest.mark.parametrize("rule_id", ["P014", "P015"])
def test_rule_question_ends_with_question_mark(rule_id: str) -> None:
    """P014/P015 catalog questions must end with '?' (binary yes/no form)."""
    rules = _load_rule_catalog()
    rule = next(r for r in rules if r["id"] == rule_id)
    q = rule["question"]
    assert q.endswith("?"), (
        f"{rule_id} question must end with '?', got: {q!r}"
    )


@pytest.mark.parametrize("rule_id", ["P014", "P015"])
def test_rule_question_starts_with_binary_form(rule_id: str) -> None:
    """P014/P015 catalog questions must start with Is/Are/Does/Do."""
    rules = _load_rule_catalog()
    rule = next(r for r in rules if r["id"] == rule_id)
    q = rule["question"]
    assert _starts_binary(q), (
        f"{rule_id} question must start with Is/Are/Does/Do, got: {q!r}"
    )


@pytest.mark.parametrize("rule_id", ["P014", "P015"])
def test_rule_remediation_is_present(rule_id: str) -> None:
    """P014/P015 must have a non-empty remediation."""
    rules = _load_rule_catalog()
    rule = next(r for r in rules if r["id"] == rule_id)
    rem = rule.get("remediation", "").strip()
    assert rem, f"{rule_id} remediation must not be empty"


# ---------------------------------------------------------------------------
# 12. Anti-regression — broad vague wording must never appear in P014/P015
# ---------------------------------------------------------------------------

_BROAD_P014_PATTERNS = (
    "expected layout/style checks",
    "follow expected layout",
    "layout/style heuristics",
    "named front-matter headings follow expected",
)

_BROAD_P015_PATTERNS = (
    "front-matter/body paragraphs",
    "show likely indentation issues",
    "front-matter or body paragraphs",
)


@pytest.mark.parametrize("pattern", _BROAD_P014_PATTERNS)
def test_p014_question_does_not_use_broad_wording(pattern: str) -> None:
    """P014 catalog must not revert to the original broad vague question wording."""
    rules = _load_rule_catalog()
    p014 = next(r for r in rules if r["id"] == "P014")
    question = p014["question"].lower()
    assert pattern.lower() not in question, (
        f"P014 question contains broad/vague pattern {pattern!r}: {p014['question']!r}"
    )


@pytest.mark.parametrize("pattern", _BROAD_P015_PATTERNS)
def test_p015_question_does_not_use_broad_wording(pattern: str) -> None:
    """P015 catalog must not revert to the original vague indentation wording."""
    rules = _load_rule_catalog()
    p015 = next(r for r in rules if r["id"] == "P015")
    question = p015["question"].lower()
    assert pattern.lower() not in question, (
        f"P015 question contains broad/vague pattern {pattern!r}: {p015['question']!r}"
    )


# ---------------------------------------------------------------------------
# 13. P014 individual findings carry Q-rule reference or heading-specific detail
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("heading,expected_q_rule_id", _HEADING_Q_RULE_CASES)
def test_p014_finding_details_identify_atomic_check(
    heading: str, expected_q_rule_id: str
) -> None:
    """Each P014 finding must carry source_q_rule_id so the atomic check is identifiable."""
    heading_line = _line(heading, x0=450.0, x1=550.0, y0=50.0, y1=62.0, bold=True)
    doc = _doc(_page(1, _block(heading_line)))
    findings = check_named_frontmatter_headings(doc)
    p014 = [f for f in findings if f.rule_id == "P014" and f.details.get("heading") == heading]
    assert p014, f"Expected a P014 finding for {heading!r}"
    q_rule_id = p014[0].details.get("source_q_rule_id")
    assert q_rule_id, (
        f"P014 finding for {heading!r} must have non-empty source_q_rule_id "
        f"to identify the atomic check; got {q_rule_id!r}"
    )
    assert q_rule_id == expected_q_rule_id


# ---------------------------------------------------------------------------
# 14. P015 body-text findings address paragraph indentation (issue_type present)
# ---------------------------------------------------------------------------

def test_p015_body_finding_issue_type_is_indentation() -> None:
    """P015 body-text findings must carry a paragraph-indentation issue_type."""
    doc = _doc(_make_body_page(page_number=10))
    findings = check_pdf_indentation(doc)
    p015 = [f for f in findings if f.rule_id == "P015"]
    assert p015, "Expected at least one P015 finding on body page"
    for f in p015:
        it = f.details.get("issue_type", "")
        assert it, f"P015 finding must have non-empty issue_type; got {f.details!r}"
        assert "indent" in it.lower(), (
            f"P015 issue_type should reference indentation; got {it!r}"
        )
