"""Synthetic tests for P061 — LoT/LoF cross-page entry-number ordering."""

from __future__ import annotations

from pathlib import Path

import fitz

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.rules.pdf_lot_lof_cross_page_entry_ordering import (
    check_pdf_lot_lof_cross_page_entry_ordering,
)
from njit_auditor.rules.pdf_lot_lof_entry_number_ordering import (
    check_pdf_lot_lof_entry_number_ordering,
)


def _make_cross_page_lot_lof_pdf(
    path: Path,
    pages: list[list[tuple[str, str | None]]],
    heading: str = "LIST OF TABLES",
) -> None:
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


def _make_toc_page_pdf(path: Path, entries: list[tuple[str, str | None]]) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    y = 140.0
    for text, pg_num in entries:
        page.insert_text((72.0, y), text, fontsize=12)
        if pg_num is not None:
            page.insert_text((500, y), pg_num, fontsize=12)
        y += 22.0
    doc.save(path)
    doc.close()


def _p061_findings(pdf_path: Path) -> list:
    model = load_pdf_layout(str(pdf_path))
    return [f for f in check_pdf_lot_lof_cross_page_entry_ordering(model) if f.rule_id == "P061"]


def test_p061_single_page_lot_no_finding(tmp_path: Path) -> None:
    """Single LoT page → no P061 finding (P059 scope)."""
    pdf_path = tmp_path / "p061_single_lot.pdf"
    _make_cross_page_lot_lof_pdf(pdf_path, [[
        ("Table 1 Overview Survey", "10"),
        ("Table 5 Analysis Report", "45"),
        ("Table 2 Results Study", "20"),
        ("Table 4 Evaluation Survey", "35"),
        ("Table 3 Discussion Report", "30"),
    ]])
    assert not _p061_findings(pdf_path)


def test_p061_two_page_lot_ascending_no_finding(tmp_path: Path) -> None:
    """Two LoT pages, combined sequence non-decreasing → no finding."""
    pdf_path = tmp_path / "p061_lot_asc.pdf"
    _make_cross_page_lot_lof_pdf(pdf_path, [
        [
            ("Table 1 Overview Survey", "10"),
            ("Table 2 Analysis Report", "20"),
            ("Table 3 Results Study", "30"),
        ],
        [
            ("Table 4 Evaluation Survey", "40"),
            ("Table 5 Discussion Report", "50"),
            ("Table 6 Summary Report", "60"),
        ],
    ])
    assert not _p061_findings(pdf_path)


def test_p061_two_page_lot_one_inversion_no_finding(tmp_path: Path) -> None:
    """Two LoT pages, 1 cross-page inversion → no finding."""
    pdf_path = tmp_path / "p061_lot_one_inv.pdf"
    _make_cross_page_lot_lof_pdf(pdf_path, [
        [
            ("Table 1 Overview Survey", "10"),
            ("Table 2 Analysis Report", "20"),
            ("Table 5 Results Study", "50"),
        ],
        [
            ("Table 3 Evaluation Survey", "30"),
            ("Table 4 Discussion Report", "40"),
            ("Table 6 Summary Report", "60"),
        ],
    ])
    assert not _p061_findings(pdf_path)


def test_p061_two_page_lot_two_inversions_warns(tmp_path: Path) -> None:
    """Multi-page LoT with >=2 combined cross-page inversions → finding."""
    pdf_path = tmp_path / "p061_lot_two_inv.pdf"
    _make_cross_page_lot_lof_pdf(pdf_path, [
        [
            ("Table 1 Overview Survey", "10"),
            ("Table 4 Analysis Report", "40"),
            ("Table 7 Results Study", "70"),
        ],
        [
            ("Table 2 Evaluation Survey", "20"),
            ("Table 5 Discussion Report", "50"),
            ("Table 8 Summary Report", "80"),
        ],
        [
            ("Table 3 Summary Survey", "30"),
            ("Table 6 Closing Report", "60"),
            ("Table 9 Final Report", "90"),
        ],
    ])
    findings = _p061_findings(pdf_path)
    assert len(findings) == 1
    assert findings[0].details.get("issue_type") == "lot_cross_page_entry_numbers_not_nondecreasing"
    assert findings[0].details.get("section_type") == "list_of_tables"
    assert int(findings[0].details.get("page_count", "0")) == 3
    assert int(findings[0].details.get("inversion_count", "0")) >= 2


def test_p061_two_page_lof_two_inversions_warns(tmp_path: Path) -> None:
    """Multi-page LoF with >=2 combined cross-page inversions → lof finding."""
    pdf_path = tmp_path / "p061_lof_two_inv.pdf"
    _make_cross_page_lot_lof_pdf(
        pdf_path,
        [
            [
                ("Figure 1 Overview Survey", "10"),
                ("Figure 4 Analysis Report", "40"),
                ("Figure 7 Results Study", "70"),
            ],
            [
                ("Figure 2 Evaluation Survey", "20"),
                ("Figure 5 Discussion Report", "50"),
                ("Figure 8 Summary Report", "80"),
            ],
            [
                ("Figure 3 Summary Survey", "30"),
                ("Figure 6 Closing Report", "60"),
                ("Figure 9 Final Report", "90"),
            ],
        ],
        heading="LIST OF FIGURES",
    )
    findings = _p061_findings(pdf_path)
    assert len(findings) == 1
    assert findings[0].details.get("issue_type") == "lof_cross_page_entry_numbers_not_nondecreasing"
    assert findings[0].details.get("section_type") == "list_of_figures"
    assert int(findings[0].details.get("inversion_count", "0")) >= 2


def test_p061_toc_unaffected(tmp_path: Path) -> None:
    """TOC page → P061 does not fire."""
    pdf_path = tmp_path / "p061_toc.pdf"
    _make_toc_page_pdf(pdf_path, [
        ("5 Overview Survey", "10"),
        ("1 Analysis Report", "45"),
        ("3 Results Study", "20"),
        ("2 Evaluation Survey", "35"),
        ("4 Discussion Report", "30"),
    ])
    assert not _p061_findings(pdf_path)


def test_p061_sparse_combined_skipped(tmp_path: Path) -> None:
    """Fewer than 3 combined comparable entries → skipped."""
    pdf_path = tmp_path / "p061_sparse.pdf"
    _make_cross_page_lot_lof_pdf(pdf_path, [
        [("Table 5 Overview Survey", "45")],
        [("Table 2 Analysis Report", "10")],
    ])
    assert not _p061_findings(pdf_path)


def test_p061_mixed_format_skipped(tmp_path: Path) -> None:
    """Mixed sequential + chapter-based across pages → skipped."""
    pdf_path = tmp_path / "p061_mixed.pdf"
    _make_cross_page_lot_lof_pdf(pdf_path, [
        [
            ("Table 1 Overview Survey", "10"),
            ("Table 2 Analysis Report", "20"),
        ],
        [
            ("Table 2.1 Results Study", "30"),
            ("Table 2.2 Evaluation Survey", "35"),
            ("Table 3 Discussion Report", "40"),
        ],
    ])
    assert not _p061_findings(pdf_path)


def test_p061_finding_metadata_privacy_safe(tmp_path: Path) -> None:
    """Findings contain only allowed keys; no entry text."""
    pdf_path = tmp_path / "p061_privacy.pdf"
    _make_cross_page_lot_lof_pdf(pdf_path, [
        [
            ("Table 1 Overview Survey", "10"),
            ("Table 4 Analysis Report", "40"),
            ("Table 7 Results Study", "70"),
        ],
        [
            ("Table 2 Evaluation Survey", "20"),
            ("Table 5 Discussion Report", "50"),
            ("Table 8 Summary Report", "80"),
        ],
        [
            ("Table 3 Summary Survey", "30"),
            ("Table 6 Closing Report", "60"),
            ("Table 9 Final Report", "90"),
        ],
    ])
    findings = _p061_findings(pdf_path)
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
    assert finding.details.get("source_q_rule_id") in {"Q063", "Q072"}


def test_p061_import_and_wiring(tmp_path: Path) -> None:
    """Module importable; returns list; wired into cli.py."""
    from njit_auditor.rules.pdf_lot_lof_cross_page_entry_ordering import (
        check_pdf_lot_lof_cross_page_entry_ordering as fn,
    )

    assert callable(fn)
    import inspect

    import njit_auditor.cli as cli_module

    source = inspect.getsource(cli_module)
    assert "check_pdf_lot_lof_cross_page_entry_ordering" in source

    pdf_path = tmp_path / "p061_wire.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72.0, 200.0), "No LoT/LoF page here.", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = fn(model)
    assert isinstance(findings, list)


def test_p061_word_only_entries_skipped(tmp_path: Path) -> None:
    """Non-Table/Figure entries skipped."""
    pdf_path = tmp_path / "p061_word_only.pdf"
    _make_cross_page_lot_lof_pdf(pdf_path, [
        [
            ("Table 1 Overview Survey", "10"),
            ("Diagram 2 Random Analysis", "20"),
            ("Table 4 Results Study", "40"),
        ],
        [
            ("Random Entry Content Here", "30"),
            ("Table 5 Discussion Report", "50"),
            ("Table 3 Summary Report", "35"),
        ],
    ])
    assert not _p061_findings(pdf_path)


def test_p061_chapter_based_cross_page_warns(tmp_path: Path) -> None:
    """Chapter-based numbers crossing page boundary with inversions → finding."""
    pdf_path = tmp_path / "p061_chapter.pdf"
    _make_cross_page_lot_lof_pdf(pdf_path, [
        [
            ("Table 1.1 Overview Survey", "10"),
            ("Table 1.4 Analysis Report", "40"),
            ("Table 1.7 Results Study", "70"),
        ],
        [
            ("Table 1.2 Evaluation Survey", "20"),
            ("Table 1.5 Discussion Report", "50"),
            ("Table 1.8 Summary Report", "80"),
        ],
        [
            ("Table 1.3 Summary Survey", "30"),
            ("Table 1.6 Closing Report", "60"),
            ("Table 1.9 Final Report", "90"),
        ],
    ])
    findings = _p061_findings(pdf_path)
    assert len(findings) == 1
    assert findings[0].details.get("issue_type") == "lot_cross_page_entry_numbers_not_nondecreasing"
    assert int(findings[0].details.get("inversion_count", "0")) >= 2


def test_p061_non_consecutive_pages_no_cross_page_run(tmp_path: Path) -> None:
    """Non-consecutive LoT pages are not combined into one cross-page run."""
    pdf_path = tmp_path / "p061_nonconsecutive.pdf"
    doc = fitz.open()
    page1 = doc.new_page(width=612, height=792)
    page1.insert_text((190, 90), "LIST OF TABLES", fontsize=16, fontname="Times-Bold")
    y = 140.0
    for text, pg_num in [
        ("Table 1 Overview Survey", "10"),
        ("Table 4 Analysis Report", "40"),
        ("Table 7 Results Study", "70"),
    ]:
        page1.insert_text((72.0, y), text, fontsize=12)
        page1.insert_text((500, y), pg_num, fontsize=12)
        y += 22.0

    page2 = doc.new_page(width=612, height=792)
    page2.insert_text((72.0, 200.0), "Body chapter content between LoT pages.", fontsize=12)

    page3 = doc.new_page(width=612, height=792)
    page3.insert_text((190, 90), "LIST OF TABLES", fontsize=16, fontname="Times-Bold")
    y = 140.0
    for text, pg_num in [
        ("Table 2 Evaluation Survey", "20"),
        ("Table 5 Discussion Report", "50"),
        ("Table 8 Summary Report", "80"),
    ]:
        page3.insert_text((72.0, y), text, fontsize=12)
        page3.insert_text((500, y), pg_num, fontsize=12)
        y += 22.0
    doc.save(pdf_path)
    doc.close()
    assert not _p061_findings(pdf_path)


def test_p061_lot_and_lof_runs_not_combined(tmp_path: Path) -> None:
    """Consecutive LoT and LoF pages are evaluated separately, not combined."""
    pdf_path = tmp_path / "p061_mixed_sections.pdf"
    doc = fitz.open()

    lot_page = doc.new_page(width=612, height=792)
    lot_page.insert_text((190, 90), "LIST OF TABLES", fontsize=16, fontname="Times-Bold")
    y = 140.0
    for text, pg_num in [
        ("Table 1 Overview Survey", "10"),
        ("Table 4 Analysis Report", "40"),
        ("Table 7 Results Study", "70"),
    ]:
        lot_page.insert_text((72.0, y), text, fontsize=12)
        lot_page.insert_text((500, y), pg_num, fontsize=12)
        y += 22.0

    lof_page = doc.new_page(width=612, height=792)
    lof_page.insert_text((190, 90), "LIST OF FIGURES", fontsize=16, fontname="Times-Bold")
    y = 140.0
    for text, pg_num in [
        ("Figure 1 Overview Survey", "10"),
        ("Figure 4 Analysis Report", "40"),
        ("Figure 7 Results Study", "70"),
    ]:
        lof_page.insert_text((72.0, y), text, fontsize=12)
        lof_page.insert_text((500, y), pg_num, fontsize=12)
        y += 22.0

    doc.save(pdf_path)
    doc.close()
    assert not _p061_findings(pdf_path)


def test_p061_within_page_inversions_deferred_to_p059(tmp_path: Path) -> None:
    """Single-page inversions are P059 scope; P061 requires multi-page runs."""
    pdf_path = tmp_path / "p061_within_page_p059.pdf"
    _make_cross_page_lot_lof_pdf(pdf_path, [[
        ("Table 1 Overview Survey", "10"),
        ("Table 5 Analysis Report", "45"),
        ("Table 2 Results Study", "20"),
        ("Table 4 Evaluation Survey", "35"),
        ("Table 3 Discussion Report", "30"),
    ]])
    model = load_pdf_layout(str(pdf_path))
    p059 = [f for f in check_pdf_lot_lof_entry_number_ordering(model) if f.rule_id == "P059"]
    p061 = [f for f in check_pdf_lot_lof_cross_page_entry_ordering(model) if f.rule_id == "P061"]
    assert len(p059) == 1
    assert not p061
