"""Tests for P075 — TOC leader-style consistency (Q052).

Synthetic PDF only; no real dissertation text reproduced.

Coverage:
A. All dot leaders → no warning
B. All hyphen leaders → no warning
C. Mixed dot + hyphen leaders → toc_mixed_leader_styles warning
D. Some entries missing leaders while others have leaders → toc_missing_leader_style
E. Fewer than MIN_ENTRIES entries → no warning (insufficient data)
F. Non-TOC page (body text) does not trigger P075
G. Catalog entry: P075 has correct Q052 reference, question, and remediation
H. Issue-type label and explanation exist for both P075 issue types
"""

from __future__ import annotations

import json
from pathlib import Path

from njit_auditor.pdf_models import (
    BBox,
    PdfDocument,
    PdfPage,
    PdfTextBlock,
    PdfTextLine,
    PdfTextSpan,
)
from njit_auditor.rules.pdf_toc_leader_consistency import check_pdf_toc_leader_consistency

_REPO_ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Synthetic PDF builder helpers
# ---------------------------------------------------------------------------


def _span(text: str, *, x0: float = 108.0, x1: float = 504.0,
          y0: float = 50.0, y1: float = 62.0, bold: bool = False) -> PdfTextSpan:
    return PdfTextSpan(
        text=text,
        font="TimesNewRomanPSMT-Bold" if bold else "TimesNewRomanPSMT",
        size=12.0,
        bold=bold,
        italic=False,
        bbox=BBox(x0=x0, y0=y0, x1=x1, y1=y1),
    )


def _line(text: str, *, x0: float = 108.0, x1: float = 504.0,
          y0: float = 50.0, y1: float = 62.0, bold: bool = False) -> PdfTextLine:
    sp = _span(text, x0=x0, x1=x1, y0=y0, y1=y1, bold=bold)
    return PdfTextLine(text=text, bbox=BBox(x0=x0, y0=y0, x1=x1, y1=y1), spans=[sp])


def _block(*lines: PdfTextLine) -> PdfTextBlock:
    x0 = min(ln.bbox.x0 for ln in lines)
    y0 = min(ln.bbox.y0 for ln in lines)
    x1 = max(ln.bbox.x1 for ln in lines)
    y1 = max(ln.bbox.y1 for ln in lines)
    return PdfTextBlock(
        bbox=BBox(x0=x0, y0=y0, x1=x1, y1=y1),
        lines=list(lines),
        text=" ".join(ln.text for ln in lines),
    )


def _page(*blocks: PdfTextBlock, page_number: int = 3,
          width: float = 612.0, height: float = 792.0) -> PdfPage:
    return PdfPage(
        page_number=page_number,
        width=width,
        height=height,
        text_blocks=list(blocks),
    )


def _doc(*pages: PdfPage) -> PdfDocument:
    return PdfDocument(path="synthetic", pages=list(pages))


def _toc_heading() -> PdfTextLine:
    return _line("TABLE OF CONTENTS", x0=220.0, x1=392.0, y0=50.0, y1=62.0, bold=True)


def _entry_dot(title: str, y: float) -> PdfTextLine:
    """TOC entry with dot leaders, e.g. 'CHAPTER 1 INTRO ....... 10'."""
    return _line(f"{title} ....... {int(y)}", x0=108.0, x1=504.0, y0=y, y1=y + 12.0)


def _entry_hyphen(title: str, y: float) -> PdfTextLine:
    """TOC entry with hyphen leaders, e.g. 'CHAPTER 1 INTRO ----- 10'."""
    return _line(f"{title} ----- {int(y)}", x0=108.0, x1=504.0, y0=y, y1=y + 12.0)


def _entry_none(title: str, y: float) -> PdfTextLine:
    """TOC entry with no leader."""
    return _line(f"{title}   {int(y)}", x0=108.0, x1=504.0, y0=y, y1=y + 12.0)


# ---------------------------------------------------------------------------
# A. All dot leaders → no warning
# ---------------------------------------------------------------------------


def test_all_dot_leaders_no_warning() -> None:
    """Consistent dot leaders throughout TOC should not trigger P075."""
    heading = _toc_heading()
    entries = [
        _entry_dot("CHAPTER 1 INTRODUCTION", 80.0),
        _entry_dot("CHAPTER 2 BACKGROUND", 100.0),
        _entry_dot("CHAPTER 3 METHODS", 120.0),
        _entry_dot("CHAPTER 4 RESULTS", 140.0),
    ]
    doc = _doc(_page(_block(heading), *[_block(e) for e in entries]))
    findings = check_pdf_toc_leader_consistency(doc)
    p075 = [f for f in findings if f.rule_id == "P075"]
    assert p075 == [], f"Expected no P075 for all-dot TOC, got: {p075}"


# ---------------------------------------------------------------------------
# B. All hyphen leaders → no warning
# ---------------------------------------------------------------------------


def test_all_hyphen_leaders_no_warning() -> None:
    """Consistent hyphen leaders throughout TOC should not trigger P075."""
    heading = _toc_heading()
    entries = [
        _entry_hyphen("CHAPTER 1 INTRODUCTION", 80.0),
        _entry_hyphen("CHAPTER 2 BACKGROUND", 100.0),
        _entry_hyphen("CHAPTER 3 METHODS", 120.0),
    ]
    doc = _doc(_page(_block(heading), *[_block(e) for e in entries]))
    findings = check_pdf_toc_leader_consistency(doc)
    p075 = [f for f in findings if f.rule_id == "P075"]
    assert p075 == [], f"Expected no P075 for all-hyphen TOC, got: {p075}"


# ---------------------------------------------------------------------------
# C. Mixed dot + hyphen leaders → toc_mixed_leader_styles
# ---------------------------------------------------------------------------


def test_mixed_dot_and_hyphen_warns() -> None:
    """TOC with both dot and hyphen leaders must trigger toc_mixed_leader_styles."""
    heading = _toc_heading()
    entries = [
        _entry_dot("CHAPTER 1 INTRODUCTION", 80.0),
        _entry_dot("CHAPTER 2 BACKGROUND", 100.0),
        _entry_dot("CHAPTER 3 METHODS", 120.0),
        _entry_hyphen("CHAPTER 4 RESULTS", 140.0),  # breaks consistency
    ]
    doc = _doc(_page(_block(heading), *[_block(e) for e in entries]))
    findings = check_pdf_toc_leader_consistency(doc)
    p075 = [f for f in findings if f.rule_id == "P075"]
    assert len(p075) == 1, f"Expected exactly 1 P075 finding, got: {p075}"
    assert p075[0].details.get("issue_type") == "toc_mixed_leader_styles"
    assert p075[0].details.get("source_q_rule_id") == "Q052"
    assert p075[0].details.get("page_number") == "3"
    assert p075[0].details.get("confidence") == "medium"
    assert p075[0].details.get("suggested_fix") == (
        "Right-align page numbers and use one consistent leader style (dots or hyphens)."
    )
    assert p075[0].details.get("dot_leader_count") == "3"
    assert p075[0].details.get("hyphen_leader_count") == "1"


def test_mixed_leaders_message_mentions_both_styles() -> None:
    """Warning message for mixed leaders must name both dot and hyphen."""
    heading = _toc_heading()
    entries = [
        _entry_dot("CHAPTER 1 INTRODUCTION", 80.0),
        _entry_hyphen("CHAPTER 2 METHODS", 100.0),
        _entry_dot("CHAPTER 3 RESULTS", 120.0),
    ]
    doc = _doc(_page(_block(heading), *[_block(e) for e in entries]))
    findings = check_pdf_toc_leader_consistency(doc)
    p075 = [f for f in findings if f.rule_id == "P075"]
    assert p075, "Expected a P075 finding for mixed leaders"
    msg = p075[0].message.lower()
    assert "dot" in msg and "hyphen" in msg, (
        f"Mixed-leader message should name both styles; got: {p075[0].message!r}"
    )
    assert "dot leaders: 2 entries" in msg
    assert "hyphen leaders: 1 entry" in msg


def test_mixed_leaders_message_uses_singular_plural_correctly() -> None:
    """Mixed-leader warning should use count labels instead of awkward singular/plural grammar."""
    heading = _toc_heading()
    entries = [
        _entry_dot("CHAPTER 1 INTRODUCTION", 80.0),
        _entry_dot("CHAPTER 2 METHODS", 100.0),
        _entry_hyphen("CHAPTER 3 RESULTS", 120.0),
    ]
    doc = _doc(_page(_block(heading), *[_block(e) for e in entries]))
    findings = check_pdf_toc_leader_consistency(doc)
    message = [f for f in findings if f.rule_id == "P075"][0].message
    assert "1 use hyphen leaders" not in message
    assert "dot leaders: 2 entries; hyphen leaders: 1 entry" in message


# ---------------------------------------------------------------------------
# D. Some entries missing leaders while others have → toc_missing_leader_style
# ---------------------------------------------------------------------------


def test_some_missing_leaders_warns() -> None:
    """TOC with dominant dot style but some entries missing leaders triggers warning."""
    heading = _toc_heading()
    entries = [
        _entry_dot("CHAPTER 1 INTRODUCTION", 80.0),
        _entry_dot("CHAPTER 2 BACKGROUND", 100.0),
        _entry_dot("CHAPTER 3 METHODS", 120.0),
        _entry_none("CHAPTER 4 RESULTS", 140.0),  # no leader
    ]
    doc = _doc(_page(_block(heading), *[_block(e) for e in entries]))
    findings = check_pdf_toc_leader_consistency(doc)
    p075 = [f for f in findings if f.rule_id == "P075"]
    assert len(p075) == 1, f"Expected exactly 1 P075 finding, got: {p075}"
    assert p075[0].details.get("issue_type") == "toc_missing_leader_style"
    assert p075[0].details.get("source_q_rule_id") == "Q052"
    assert p075[0].details.get("page_number") == "3"
    assert p075[0].details.get("confidence") == "medium"
    assert p075[0].details.get("suggested_fix") == (
        "Right-align page numbers and use one consistent leader style (dots or hyphens)."
    )
    assert p075[0].details.get("dominant_style") == "dot"
    assert p075[0].details.get("entries_without_leader") == "1"


def test_missing_leaders_with_hyphen_dominant() -> None:
    """Missing-leader detection works when the dominant style is hyphen."""
    heading = _toc_heading()
    entries = [
        _entry_hyphen("CHAPTER 1 INTRODUCTION", 80.0),
        _entry_hyphen("CHAPTER 2 BACKGROUND", 100.0),
        _entry_none("CHAPTER 3 METHODS", 120.0),  # no leader
        _entry_hyphen("CHAPTER 4 RESULTS", 140.0),
    ]
    doc = _doc(_page(_block(heading), *[_block(e) for e in entries]))
    findings = check_pdf_toc_leader_consistency(doc)
    p075 = [f for f in findings if f.rule_id == "P075"]
    assert len(p075) == 1
    assert p075[0].details.get("issue_type") == "toc_missing_leader_style"
    assert p075[0].details.get("dominant_style") == "hyphen"


# ---------------------------------------------------------------------------
# E. Fewer than MIN_ENTRIES → no warning (insufficient data)
# ---------------------------------------------------------------------------


def test_too_few_entries_no_warning() -> None:
    """Fewer than 3 paged entries should not produce any P075 finding."""
    heading = _toc_heading()
    entries = [
        _entry_dot("CHAPTER 1 INTRODUCTION", 80.0),
        _entry_hyphen("CHAPTER 2 METHODS", 100.0),
    ]
    doc = _doc(_page(_block(heading), *[_block(e) for e in entries]))
    findings = check_pdf_toc_leader_consistency(doc)
    p075 = [f for f in findings if f.rule_id == "P075"]
    assert p075 == [], "Expected no P075 with fewer than 3 entries"


# ---------------------------------------------------------------------------
# F. Non-TOC page (body text) does not trigger P075
# ---------------------------------------------------------------------------


def test_body_page_with_dot_sequences_not_triggered() -> None:
    """A body text page with dot-like sequences must not produce any P075 finding."""
    body_line = _line(
        "See Table 3.1 ....... for details and refer to p. 45 for figures.",
        x0=108.0, x1=504.0, y0=80.0, y1=92.0,
    )
    body_line2 = _line(
        "The results --------- confirm the hypothesis stated on page 12.",
        x0=108.0, x1=504.0, y0=100.0, y1=112.0,
    )
    doc = _doc(_page(_block(body_line, body_line2), page_number=15))
    findings = check_pdf_toc_leader_consistency(doc)
    p075 = [f for f in findings if f.rule_id == "P075"]
    assert p075 == [], "Body text pages must not trigger P075"


# ---------------------------------------------------------------------------
# G. Catalog integrity
# ---------------------------------------------------------------------------


def test_p075_catalog_entry_exists() -> None:
    """P075 must be present in the rules catalog."""
    catalog_path = _REPO_ROOT / "data" / "processed" / "rules" / "project_added_rules.json"
    rules = json.loads(catalog_path.read_text(encoding="utf-8"))
    ids = {r["id"] for r in rules}
    assert "P075" in ids, "P075 missing from project_added_rules.json"


def test_p075_catalog_references_q052() -> None:
    """P075 catalog entry must reference Q052 so the coverage system sees it."""
    catalog_path = _REPO_ROOT / "data" / "processed" / "rules" / "project_added_rules.json"
    rules = json.loads(catalog_path.read_text(encoding="utf-8"))
    p075 = next(r for r in rules if r["id"] == "P075")
    combined = " ".join([
        p075.get("notes", ""),
        " ".join(p075.get("source_q_rule_ids", [])),
    ])
    assert "Q052" in combined, (
        "P075 catalog entry must reference Q052 in notes or source_q_rule_ids"
    )


def test_p075_catalog_question_mentions_leader() -> None:
    """P075 question must mention leader style (Q052 requirement)."""
    catalog_path = _REPO_ROOT / "data" / "processed" / "rules" / "project_added_rules.json"
    rules = json.loads(catalog_path.read_text(encoding="utf-8"))
    p075 = next(r for r in rules if r["id"] == "P075")
    q = p075.get("question", "").lower()
    assert "leader" in q, f"P075 question should mention 'leader'; got: {p075.get('question')!r}"
    assert p075.get("question") == (
        "Is each Table of Contents entry connected to its page number by one "
        "consistent leader style (dots or hyphens) throughout the TOC?"
    )


def test_p075_catalog_remediation_nonempty() -> None:
    """P075 remediation must be non-empty."""
    catalog_path = _REPO_ROOT / "data" / "processed" / "rules" / "project_added_rules.json"
    rules = json.loads(catalog_path.read_text(encoding="utf-8"))
    p075 = next(r for r in rules if r["id"] == "P075")
    assert p075.get("remediation"), "P075 remediation must not be empty"
    assert p075.get("remediation") == (
        "Right-align page numbers and use one consistent leader style "
        "(dots or hyphens) throughout the entire Table of Contents."
    )


# ---------------------------------------------------------------------------
# H. Issue-type label and explanation
# ---------------------------------------------------------------------------


def test_issue_type_labels_exist() -> None:
    """Both P075 issue types must produce humanized labels (not raw underscore strings)."""
    from njit_auditor.issue_type_explanations import humanize_issue_type
    mixed_label = humanize_issue_type("toc_mixed_leader_styles")
    missing_label = humanize_issue_type("toc_missing_leader_style")
    assert mixed_label and mixed_label != "toc_mixed_leader_styles", (
        f"toc_mixed_leader_styles has no explicit label; got {mixed_label!r}"
    )
    assert missing_label and missing_label != "toc_missing_leader_style", (
        f"toc_missing_leader_style has no explicit label; got {missing_label!r}"
    )


def test_issue_type_explanations_exist() -> None:
    """Both P075 (rule_id, issue_type) pairs must have explanation text."""
    from njit_auditor.issue_type_explanations import explain_issue_type
    mixed_exp = explain_issue_type("P075", "toc_mixed_leader_styles")
    missing_exp = explain_issue_type("P075", "toc_missing_leader_style")
    assert mixed_exp, "No explanation for (P075, toc_mixed_leader_styles)"
    assert missing_exp, "No explanation for (P075, toc_missing_leader_style)"
    assert "dot" in mixed_exp.lower() or "leader" in mixed_exp.lower()
    assert "leader" in missing_exp.lower()


# ---------------------------------------------------------------------------
# I. Q052 snapshot: details retain source Q-rule traceability
# ---------------------------------------------------------------------------


def test_mixed_leaders_finding_text_confirms_q052() -> None:
    """P075 finding details should confirm Q052 without exposing it in the message."""
    heading = _toc_heading()
    entries = [
        _entry_dot("CHAPTER 1 INTRODUCTION", 80.0),
        _entry_dot("CHAPTER 2 BACKGROUND", 100.0),
        _entry_hyphen("CHAPTER 3 METHODS", 120.0),
    ]
    doc = _doc(_page(_block(heading), *[_block(e) for e in entries]))
    findings = check_pdf_toc_leader_consistency(doc)
    p075 = [f for f in findings if f.rule_id == "P075"]
    assert p075, "Expected a P075 finding"
    assert p075[0].details.get("source_q_rule_id") == "Q052"
    assert "Q052" not in p075[0].message
