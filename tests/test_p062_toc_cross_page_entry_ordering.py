"""Synthetic tests for P062 — TOC cross-page section-number ordering."""

from __future__ import annotations

from pathlib import Path

import fitz

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.rules.pdf_toc_cross_page_entry_ordering import (
    check_pdf_toc_cross_page_entry_ordering,
)
from njit_auditor.rules.pdf_toc_entry_number_ordering import (
    check_pdf_toc_entry_number_ordering,
)


def _make_cross_page_toc_pdf(
    path: Path,
    pages: list[list[tuple[str, str | None]]],
    heading: str = "TABLE OF CONTENTS",
) -> None:
    """Create a synthetic multi-page TOC PDF."""
    doc = fitz.open()
    for page_entries in pages:
        page = doc.new_page(width=612, height=792)
        page.insert_text((190, 90), heading, fontsize=16, fontname="Times-Bold")
        y = 140.0
        for text, pg_num in page_entries:
            page.insert_text((72.0, y), text, fontsize=12)
            if pg_num is not None:
                page.insert_text((500, y), pg_num, fontsize=12)
            y += 22.0
    doc.save(path)
    doc.close()


def _make_lot_pdf(path: Path, entries: list[tuple[str, str | None]]) -> None:
    """Create a synthetic single-page LoT PDF (not TOC)."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), "LIST OF TABLES", fontsize=16, fontname="Times-Bold")
    y = 140.0
    for text, pg_num in entries:
        page.insert_text((72.0, y), text, fontsize=12)
        if pg_num is not None:
            page.insert_text((500, y), pg_num, fontsize=12)
        y += 22.0
    doc.save(path)
    doc.close()


def _p062_findings(pdf_path: Path) -> list:
    model = load_pdf_layout(str(pdf_path))
    return [f for f in check_pdf_toc_cross_page_entry_ordering(model) if f.rule_id == "P062"]


def test_p062_single_page_toc_no_finding(tmp_path: Path) -> None:
    """Single TOC page → no P062 finding (P060 scope)."""
    pdf_path = tmp_path / "p062_single_toc.pdf"
    _make_cross_page_toc_pdf(pdf_path, [[
        ("1 Overview Survey", "5"),
        ("5 Analysis Report", "45"),
        ("2 Results Study", "15"),
        ("4 Evaluation Survey", "35"),
        ("3 Discussion Report", "25"),
    ]])
    assert not _p062_findings(pdf_path)


def test_p062_two_page_toc_ascending_no_finding(tmp_path: Path) -> None:
    """Two TOC pages, combined section numbers non-decreasing → no finding."""
    pdf_path = tmp_path / "p062_toc_asc.pdf"
    _make_cross_page_toc_pdf(pdf_path, [
        [
            ("1 Overview Survey", "5"),
            ("2 Analysis Report", "15"),
            ("3 Results Study", "25"),
        ],
        [
            ("4 Evaluation Survey", "35"),
            ("5 Discussion Report", "45"),
            ("6 Summary Report", "55"),
        ],
    ])
    assert not _p062_findings(pdf_path)


def test_p062_two_page_toc_one_inversion_no_finding(tmp_path: Path) -> None:
    """Two TOC pages, 1 cross-page inversion → no finding (gate requires >= 2)."""
    pdf_path = tmp_path / "p062_toc_one_inv.pdf"
    _make_cross_page_toc_pdf(pdf_path, [
        [
            ("1 Overview Survey", "5"),
            ("2 Analysis Report", "15"),
            ("5 Results Study", "45"),
        ],
        [
            ("3 Evaluation Survey", "25"),
            ("4 Discussion Report", "35"),
            ("6 Summary Report", "55"),
        ],
    ])
    assert not _p062_findings(pdf_path)


def test_p062_two_page_toc_two_inversions_warns(tmp_path: Path) -> None:
    """Multi-page TOC with >= 2 combined inversions → finding."""
    pdf_path = tmp_path / "p062_toc_two_inv.pdf"
    _make_cross_page_toc_pdf(pdf_path, [
        [
            ("1 Overview Survey", "5"),
            ("4 Analysis Report", "35"),
            ("7 Results Study", "65"),
        ],
        [
            ("2 Evaluation Survey", "15"),
            ("5 Discussion Report", "45"),
            ("8 Summary Report", "75"),
        ],
        [
            ("3 Summary Survey", "25"),
            ("6 Closing Report", "55"),
            ("9 Final Report", "85"),
        ],
    ])
    findings = _p062_findings(pdf_path)
    assert len(findings) == 1
    assert findings[0].details.get("issue_type") == "toc_cross_page_entry_numbers_not_nondecreasing"
    assert findings[0].details.get("section_type") == "table_of_contents"
    assert int(findings[0].details.get("page_count", "0")) == 3
    assert int(findings[0].details.get("inversion_count", "0")) >= 2


def test_p062_lot_unaffected(tmp_path: Path) -> None:
    """LoT page → P062 does not fire (only TABLE OF CONTENTS pages checked)."""
    pdf_path = tmp_path / "p062_lot.pdf"
    _make_lot_pdf(pdf_path, [
        ("Table 5 Overview Survey", "45"),
        ("Table 1 Analysis Report", "5"),
        ("Table 3 Results Study", "25"),
        ("Table 2 Evaluation Survey", "15"),
        ("Table 4 Discussion Report", "35"),
    ])
    assert not _p062_findings(pdf_path)


def test_p062_sparse_combined_skipped(tmp_path: Path) -> None:
    """Fewer than 3 combined comparable entries → skipped."""
    pdf_path = tmp_path / "p062_sparse.pdf"
    _make_cross_page_toc_pdf(pdf_path, [
        [("5 Overview Survey", "45")],
        [("2 Analysis Report", "15")],
    ])
    assert not _p062_findings(pdf_path)


def test_p062_word_prefix_entries_excluded(tmp_path: Path) -> None:
    """Word-prefix entries (CHAPTER, APPENDIX, ABSTRACT) not counted."""
    pdf_path = tmp_path / "p062_word_prefix.pdf"
    _make_cross_page_toc_pdf(pdf_path, [
        [
            ("ABSTRACT Survey", "iv"),
            ("1 Overview Survey", "5"),
            ("2 Analysis Report", "15"),
        ],
        [
            ("CHAPTER 3 Results Study", "25"),
            ("3 Evaluation Survey", "25"),
            ("4 Discussion Report", "35"),
            ("APPENDIX Notes", "98"),
        ],
    ])
    # Only numeric entries: (1,), (2,), (3,), (4,) → non-decreasing → no finding
    assert not _p062_findings(pdf_path)


def test_p062_finding_metadata_privacy_safe(tmp_path: Path) -> None:
    """Findings contain only allowed structural metadata keys; no entry text."""
    pdf_path = tmp_path / "p062_privacy.pdf"
    _make_cross_page_toc_pdf(pdf_path, [
        [
            ("1 Overview Survey", "5"),
            ("4 Analysis Report", "35"),
            ("7 Results Study", "65"),
        ],
        [
            ("2 Evaluation Survey", "15"),
            ("5 Discussion Report", "45"),
            ("8 Summary Report", "75"),
        ],
        [
            ("3 Summary Survey", "25"),
            ("6 Closing Report", "55"),
            ("9 Final Report", "85"),
        ],
    ])
    findings = _p062_findings(pdf_path)
    assert findings
    finding = findings[0]
    allowed_keys = {
        "issue_type",
        "page",
        "section_type",
        "page_count",
        "entry_count",
        "comparable_entry_number_count",
        "inversion_count",
        "first_inversion_index",
        "triage_tier",
        "source_q_rule_id",
    }
    for key in finding.details:
        assert key in allowed_keys, f"Unexpected metadata key: {key!r}"
    for key, val in finding.details.items():
        assert isinstance(val, str), f"Metadata value for {key!r} should be str"
    assert finding.details.get("triage_tier") == "medium"
    assert finding.details.get("source_q_rule_id") == "Q056"
    assert finding.details.get("section_type") == "table_of_contents"


def test_p062_import_and_wiring(tmp_path: Path) -> None:
    """Module importable; returns list; wired into audit_runner."""
    from njit_auditor.rules.pdf_toc_cross_page_entry_ordering import (
        check_pdf_toc_cross_page_entry_ordering as fn,
    )

    assert callable(fn)
    import inspect

    import njit_auditor.audit_runner as audit_runner

    source = inspect.getsource(audit_runner.collect_pdf_layout_findings)
    assert "check_pdf_toc_cross_page_entry_ordering" in source

    pdf_path = tmp_path / "p062_wire.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72.0, 200.0), "No TOC page here.", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = fn(model)
    assert isinstance(findings, list)


def test_p062_non_consecutive_toc_pages_not_combined(tmp_path: Path) -> None:
    """Non-consecutive TOC pages are not combined into one cross-page run."""
    pdf_path = tmp_path / "p062_nonconsecutive.pdf"
    doc = fitz.open()

    page1 = doc.new_page(width=612, height=792)
    page1.insert_text((190, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    y = 140.0
    for text, pg_num in [
        ("1 Overview Survey", "5"),
        ("4 Analysis Report", "35"),
        ("7 Results Study", "65"),
    ]:
        page1.insert_text((72.0, y), text, fontsize=12)
        page1.insert_text((500, y), pg_num, fontsize=12)
        y += 22.0

    page2 = doc.new_page(width=612, height=792)
    page2.insert_text((72.0, 200.0), "Body chapter text between TOC pages.", fontsize=12)

    page3 = doc.new_page(width=612, height=792)
    page3.insert_text((190, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    y = 140.0
    for text, pg_num in [
        ("2 Evaluation Survey", "15"),
        ("5 Discussion Report", "45"),
        ("8 Summary Report", "75"),
    ]:
        page3.insert_text((72.0, y), text, fontsize=12)
        page3.insert_text((500, y), pg_num, fontsize=12)
        y += 22.0

    doc.save(pdf_path)
    doc.close()
    # Non-consecutive pages → no combined run → no P062 finding
    assert not _p062_findings(pdf_path)


def test_p062_within_page_inversions_deferred_to_p060(tmp_path: Path) -> None:
    """Single-page inversions are P060 scope; P062 requires multi-page runs."""
    pdf_path = tmp_path / "p062_within_page_p060.pdf"
    _make_cross_page_toc_pdf(pdf_path, [[
        ("1 Overview Survey", "5"),
        ("5 Analysis Report", "45"),
        ("2 Results Study", "15"),
        ("4 Evaluation Survey", "35"),
        ("3 Discussion Report", "25"),
    ]])
    model = load_pdf_layout(str(pdf_path))
    p060 = [f for f in check_pdf_toc_entry_number_ordering(model) if f.rule_id == "P060"]
    p062 = [f for f in check_pdf_toc_cross_page_entry_ordering(model) if f.rule_id == "P062"]
    assert len(p060) == 1
    assert not p062


def test_p062_subsection_cross_page_inversions_warns(tmp_path: Path) -> None:
    """Subsection entries (X.Y) with cross-page inversions → finding."""
    pdf_path = tmp_path / "p062_subsect.pdf"
    _make_cross_page_toc_pdf(pdf_path, [
        [
            ("1.1 Overview Survey", "5"),
            ("1.4 Analysis Report", "35"),
            ("1.7 Results Study", "65"),
        ],
        [
            ("1.2 Evaluation Survey", "15"),
            ("1.5 Discussion Report", "45"),
            ("1.8 Summary Report", "75"),
        ],
        [
            ("1.3 Summary Survey", "25"),
            ("1.6 Closing Report", "55"),
            ("1.9 Final Report", "85"),
        ],
    ])
    findings = _p062_findings(pdf_path)
    assert len(findings) == 1
    assert findings[0].details.get("issue_type") == "toc_cross_page_entry_numbers_not_nondecreasing"
    assert int(findings[0].details.get("inversion_count", "0")) >= 2
