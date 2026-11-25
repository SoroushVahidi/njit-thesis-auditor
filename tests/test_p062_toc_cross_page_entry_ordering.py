"""Synthetic tests for P062 — TOC cross-page section-number ordering."""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.pdf_models import BBox, format_bbox_detail
from njit_auditor.rules import pdf_toc_cross_page_entry_ordering as p062
from njit_auditor.rules.pdf_toc_alignment import (
    TocEntryLine,
    TocPageContext,
    detect_toc_like_pages,
    extract_toc_entry_lines,
)
from njit_auditor.rules.pdf_toc_cross_page_entry_ordering import (
    check_pdf_toc_cross_page_entry_ordering,
)
from njit_auditor.rules.pdf_toc_entry_number_ordering import (
    check_pdf_toc_entry_number_ordering,
)
from njit_auditor.toc_order_evidence import P062_ISSUE


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
    assert findings[0].details.get("issue_type") == P062_ISSUE
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
        "representative_inversion_index",
        "suggested_fix",
        "highlight_bboxes",
        *(
            f"{role}_entry_{field}"
            for role in ("preceding", "following")
            for field in ("number", "page", "index", "toc_folio", "destination_folio", "bbox")
        ),
    }
    for key in finding.details:
        assert key in allowed_keys, f"Unexpected metadata key: {key!r}"
    for key, val in finding.details.items():
        assert isinstance(val, str), f"Metadata value for {key!r} should be str"
    assert finding.details.get("triage_tier") == "medium"
    assert finding.details.get("source_q_rule_id") == "Q056"
    assert finding.details.get("section_type") == "table_of_contents"
    assert not any("Results Study" in value for value in finding.details.values())


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


def _reproduction(
    path: Path, *, wrapper: bool = False, wrapped: bool = False, ambiguous_footer: bool = False
) -> None:
    """Reuse W73's synthetic section sequence, with independently placed folios."""
    with fitz.open() as doc:
        if wrapper:
            page = doc.new_page(width=612, height=792)
            page.insert_text((72, 72), "Digital Commons @ NJIT", fontsize=14)
            page.insert_text((72, 102), "Theses and Dissertations", fontsize=12)
            page.insert_text((72, 130), "Recommended Citation", fontsize=11)
        for i, (numbers, folio) in enumerate(
            zip(((1, 2, 3), (4, 7, 6), (5, 8, 9)), ("vi", "vii", "viii"), strict=True)
        ):
            page = doc.new_page(width=612, height=792)
            page.insert_text((190, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
            if i:
                page.insert_text((240, 113), "(Continued)", fontsize=12)
            page.insert_text((300, 753), folio, fontsize=12)
            if ambiguous_footer and i == 2:
                page.insert_text((298, 725), "ix", fontsize=12)
            for j, number in enumerate(numbers):
                x = 72 if number != 6 else 94
                y = 152 + i * 8 + j * 25
                text = f"{number}.1 Synthetic sequence entry for local verification"
                page.insert_text((x, y), text, fontsize=12)
                if wrapped and number == 6:
                    y += 14
                    page.insert_text((x + 18, y), "with wrapped title words", fontsize=12)
                page.insert_text((500, y), str(33 + j), fontsize=12)
        doc.save(path)


def _source_box(path: Path, page: int, prefix: str) -> str:
    page_model = load_pdf_layout(str(path)).pages[page - 1]
    span, = [
        span for block in page_model.text_blocks for line in block.lines for span in line.spans
        if span.text.startswith(prefix + " ")
    ]
    return format_bbox_detail(span.bbox)


@pytest.mark.parametrize("wrapped", [False, True])
def test_p062_reproduction_selects_cross_page_pair_on_later_pages(
    tmp_path: Path, wrapped: bool
) -> None:
    path = tmp_path / "p062_later_pair.pdf"
    _reproduction(path, wrapped=wrapped)
    finding, = _p062_findings(path)
    details = finding.details
    assert finding.page == 3
    assert details["first_inversion_index"] == "4"
    assert details["representative_inversion_index"] == "5"
    assert details["inversion_count"] == "2"
    assert details["preceding_entry_number"] == "6.1"
    assert details["following_entry_number"] == "5.1"
    contexts = {c.page.page_number: c for c in detect_toc_like_pages(load_pdf_layout(str(path)))}
    for role, page, section in (("preceding", 2, "6.1"), ("following", 3, "5.1")):
        entries = extract_toc_entry_lines(contexts[page])
        assert entries[int(details[f"{role}_entry_index"])].cleaned_text.startswith(section + " ")
    assert details["preceding_entry_page"] == "2" and details["following_entry_page"] == "3"
    assert details["preceding_entry_toc_folio"] == "vii"
    assert details["following_entry_toc_folio"] == "viii"
    assert details["preceding_entry_destination_folio"] == "35"
    assert details["following_entry_destination_folio"] == "33"
    assert details["preceding_entry_bbox"] == _source_box(path, 2, "6.1")
    assert details["following_entry_bbox"] == _source_box(path, 3, "5.1")
    assert details["highlight_bboxes"] == details["following_entry_bbox"]
    assert "Check sections 6.1 and 5.1 against manuscript headings" in details["suggested_fix"]


def test_p062_same_page_pair_remains_in_scope_with_a_multi_page_run(tmp_path: Path) -> None:
    path = tmp_path / "p062_local_pair.pdf"
    _make_cross_page_toc_pdf(path, [
        [(f"{n}.1 Owned numbered section", "15") for n in group]
        for group in ((1, 2, 3), (5, 4, 7, 6), (8, 9, 10))
    ])
    finding, = _p062_findings(path)
    details = finding.details
    assert finding.page == 2
    assert details["first_inversion_index"] == details["representative_inversion_index"] == "3"
    assert (details["preceding_entry_number"], details["following_entry_number"]) == ("5.1", "4.1")
    assert details["preceding_entry_page"] == details["following_entry_page"] == "2"
    assert details["highlight_bboxes"].split(" | ") == [
        _source_box(path, 2, "5.1"), _source_box(path, 2, "4.1")
    ]
    assert details["inversion_count"] == "2"


def test_p062_numbers_only_with_equal_destination_folios_and_nested_appendix(
    tmp_path: Path
) -> None:
    path = tmp_path / "p062_number_kinds.pdf"
    _make_cross_page_toc_pdf(path, [
        [("Acknowledgments", "xii"), ("1 Chapter Introduction", "1"),
         ("1.1 Section Overview", "1"), ("1.1.1 Subsection Details", "1")],
        [("1.2 Second Section", "1"), ("1.10 Later Section", "1"), ("2 Next Chapter", "10"),
         ("APPENDIX A Study Materials", "20"), ("A.1 Appendix Subsection", "20")],
    ])
    assert _p062_findings(path) == []


def test_p062_ambiguous_footer_is_not_replaced_by_the_entry_destination(tmp_path: Path) -> None:
    path = tmp_path / "p062_folios.pdf"
    _reproduction(path, ambiguous_footer=True)
    finding, = _p062_findings(path)
    assert finding.details["following_entry_destination_folio"] == "33"
    assert "following_entry_toc_folio" not in finding.details
    assert "physical PDF page 3" in finding.message


@pytest.mark.parametrize("ambiguous_span", [False, True])
def test_p062_conservatively_omits_unreliable_geometry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ambiguous_span: bool
) -> None:
    path = tmp_path / "p062_unreliable.pdf"
    _reproduction(path)
    implementation = p062.extract_toc_entry_lines

    def extract(context: TocPageContext) -> list[TocEntryLine]:
        entries = implementation(context)
        if context.page.page_number == 3:
            target, = [entry for entry in entries if entry.cleaned_text.startswith("5.1 ")]
            if ambiguous_span:
                # The modified span is not on any source row.
                target.line.spans[0] = target.line.spans[0].model_copy(
                    update={"bbox": BBox(x0=72, y0=110, x1=100, y1=120)}
                )
            else:
                target.line.spans = []
        return entries

    monkeypatch.setattr(p062, "extract_toc_entry_lines", extract)
    finding, = _p062_findings(path)
    assert finding.page == 3
    assert finding.details["preceding_entry_bbox"] == _source_box(path, 2, "6.1")
    assert "following_entry_bbox" not in finding.details
    assert "highlight_bboxes" not in finding.details


@pytest.mark.parametrize("wrapper", [False, True])
def test_p062_report_routes_preserve_cross_page_geometry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, wrapper: bool
) -> None:
    from fastapi.testclient import TestClient

    from njit_auditor import web_app

    path = tmp_path / "p062_report.pdf"
    _reproduction(path, wrapper=wrapper, wrapped=True)
    earlier = 3 if wrapper else 2
    later = earlier + 1
    monkeypatch.setattr(web_app, "RUNTIME_DIR", tmp_path / "audits")
    with TestClient(web_app.app) as client:
        submission = client.post(
            "/audits", files={"file": (path.name, path.read_bytes(), "application/pdf")},
            follow_redirects=False,
        )
        assert submission.status_code == 303
        url = submission.headers["location"]
        assert client.get(url + "/status").json()["state"] == "complete"
        rows = client.get(url + "/download/json").json()["findings"]
        row, = [f for f in rows if f["rule_id"] == "P062"]
        assert row["page"] == later
        detail = row["details"]
        assert detail["preceding_entry_page"] == str(earlier)
        assert detail["following_entry_page"] == str(later)
        assert detail["manuscript_page_number"] == "3"
        assert detail["following_entry_toc_folio"] == "viii"
        advice = "Check sections 6.1 and 5.1 against manuscript headings"
        pair = f"Section 6.1 on physical PDF page {earlier} (printed TOC folio vii)"
        for route in ("", "/download/markdown", "/download/text"):
            response = client.get(url + route)
            assert response.status_code == 200
            assert pair in response.text and advice in response.text
        job = web_app._get_job(url.rsplit("/", 1)[-1])
        assert job is not None
        card, = [c for c in job.findings if c["rule_id"] == "P062"]
        assert card["page"] == later and card["has_highlight"]
        finder = {"rule_id": "P062", "finding_id": card["finding_id"]}
        marks: dict[int, tuple[float, ...]] = {}
        for kind, number in (("preceding", earlier), ("following", later)):
            response = client.get(url + "/highlighted-page.pdf", params={**finder, "page": number})
            assert response.status_code == 200
            with fitz.open(stream=response.content) as focused:
                mark, = [tuple(a.rect) for a in focused[0].annots()]
            expected = detail[f"{kind}_entry_bbox"].split(",")
            assert all(abs(actual - float(ref)) < 2 for actual, ref in zip(
                mark, expected, strict=True
            ))
            marks[number] = mark
        isolated = client.get(url + "/pdf/highlighted", params=finder)
        complete = client.get(url + "/download/student-report.pdf")
        assert isolated.status_code == complete.status_code == 200
        with fitz.open(stream=isolated.content) as annotated:
            for page in annotated:
                expected_marks = [marks[page.number + 1]] if page.number + 1 in marks else []
                assert [tuple(a.rect) for a in page.annots()] == expected_marks
        with fitz.open(stream=complete.content) as combined:
            for page, mark in marks.items():
                assert mark in [tuple(a.rect) for a in combined[page - 1].annots()]
                assert f"#{card['problem_number']}" in combined[page - 1].get_text()
            comments = " ".join(
                " ".join(page.get_text().split()) for page in combined if page.number >= later
            )
            assert pair in comments and advice in comments
