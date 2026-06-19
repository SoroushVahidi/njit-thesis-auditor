"""Synthetic tests for P063 — body-page appendix heading label checks."""

from __future__ import annotations

from pathlib import Path

import fitz

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.rules.pdf_appendix_body_headings import (
    check_pdf_appendix_body_headings,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pdf_with_appendix_headings(
    path: Path,
    appendix_headings: list[tuple[str, int]],
    *,
    include_chapter: bool = True,
) -> None:
    """Create a synthetic PDF with optional chapter and given appendix headings.

    appendix_headings: list of (heading_text, page_number_in_doc) tuples.
      page_number_in_doc is 1-based page index in the PDF.
    include_chapter: if True, insert a CHAPTER 1 heading on page 1 to trigger
      body region detection.
    """
    # Determine number of pages needed.
    max_page = max((pn for _, pn in appendix_headings), default=1)
    if include_chapter:
        max_page = max(max_page, 1)

    doc = fitz.open()
    for _ in range(max_page):
        doc.new_page(width=612, height=792)

    # Insert chapter heading on page 1 if requested (body start trigger).
    if include_chapter:
        page_obj = doc[0]
        page_obj.insert_text((72.0, 200.0), "CHAPTER 1 Introduction", fontsize=14)

    # Insert appendix headings.
    for heading_text, pg_1based in appendix_headings:
        page_obj = doc[pg_1based - 1]
        page_obj.insert_text((72.0, 100.0), heading_text, fontsize=14)

    doc.save(path)
    doc.close()


def _p063_findings(pdf_path: Path) -> list:
    model = load_pdf_layout(str(pdf_path))
    return [f for f in check_pdf_appendix_body_headings(model) if f.rule_id == "P063"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_p063_no_appendix_no_finding(tmp_path: Path) -> None:
    """No body appendix headings → no P063 finding."""
    pdf_path = tmp_path / "p063_no_appendix.pdf"
    _make_pdf_with_appendix_headings(pdf_path, [], include_chapter=True)
    assert not _p063_findings(pdf_path)


def test_p063_single_appendix_no_letter_no_finding(tmp_path: Path) -> None:
    """Single appendix, bare APPENDIX heading (no letter) → no finding (correct per Q058)."""
    pdf_path = tmp_path / "p063_single_bare.pdf"
    _make_pdf_with_appendix_headings(
        pdf_path,
        [("APPENDIX Supporting Material", 2)],
        include_chapter=True,
    )
    assert not _p063_findings(pdf_path)


def test_p063_single_appendix_with_letter_warns(tmp_path: Path) -> None:
    """Single appendix uses APPENDIX A heading → warning (Q058 violation)."""
    pdf_path = tmp_path / "p063_single_with_letter.pdf"
    _make_pdf_with_appendix_headings(
        pdf_path,
        [("APPENDIX A Supporting Material", 2)],
        include_chapter=True,
    )
    findings = _p063_findings(pdf_path)
    assert len(findings) == 1
    f = findings[0]
    assert f.details.get("issue_type") == "single_appendix_uses_letter_label"
    assert f.details.get("letter_found") == "A"
    assert f.details.get("appendix_count") == "1"
    assert f.details.get("source_q_rule_id") == "Q058"
    assert f.details.get("triage_tier") == "medium"


def test_p063_multiple_appendix_with_letters_no_finding(tmp_path: Path) -> None:
    """Multiple appendices each with consecutive letter labels → no finding."""
    pdf_path = tmp_path / "p063_multi_letters_ok.pdf"
    _make_pdf_with_appendix_headings(
        pdf_path,
        [
            ("APPENDIX A First Appendix", 2),
            ("APPENDIX B Second Appendix", 3),
            ("APPENDIX C Third Appendix", 4),
        ],
        include_chapter=True,
    )
    assert not _p063_findings(pdf_path)


def test_p063_multiple_appendix_missing_letter_warns(tmp_path: Path) -> None:
    """Multiple appendices, one heading without letter → warning (Q059 violation)."""
    pdf_path = tmp_path / "p063_multi_missing_letter.pdf"
    _make_pdf_with_appendix_headings(
        pdf_path,
        [
            ("APPENDIX A First Appendix", 2),
            ("APPENDIX Second Appendix Without Letter", 3),
        ],
        include_chapter=True,
    )
    findings = _p063_findings(pdf_path)
    # Page 3 heading is missing the letter suffix.
    issue_types = [f.details.get("issue_type") for f in findings]
    assert "multiple_appendix_missing_letter" in issue_types
    for f in findings:
        if f.details.get("issue_type") == "multiple_appendix_missing_letter":
            assert f.details.get("appendix_count") == "2"
            assert f.details.get("source_q_rule_id") == "Q059"


def test_p063_multiple_appendix_letter_gap_warns(tmp_path: Path) -> None:
    """Multiple appendices with gap in letter sequence (A, C, no B) → warning."""
    pdf_path = tmp_path / "p063_multi_gap.pdf"
    _make_pdf_with_appendix_headings(
        pdf_path,
        [
            ("APPENDIX A First Appendix", 2),
            ("APPENDIX C Third Appendix", 3),
        ],
        include_chapter=True,
    )
    findings = _p063_findings(pdf_path)
    assert len(findings) == 1
    f = findings[0]
    assert f.details.get("issue_type") == "appendix_letter_sequence_gap"
    assert f.details.get("expected_letter") == "B"
    assert f.details.get("found_letter") == "C"
    assert f.details.get("source_q_rule_id") == "Q059"


def test_p063_multiple_appendix_letter_repeat_warns(tmp_path: Path) -> None:
    """Multiple appendices with repeated letter (A, A) → warning."""
    pdf_path = tmp_path / "p063_multi_repeat.pdf"
    _make_pdf_with_appendix_headings(
        pdf_path,
        [
            ("APPENDIX A First Appendix", 2),
            ("APPENDIX A Repeated Appendix", 3),
        ],
        include_chapter=True,
    )
    findings = _p063_findings(pdf_path)
    assert any(
        f.details.get("issue_type") == "appendix_letter_sequence_repeat" for f in findings
    )
    for f in findings:
        if f.details.get("issue_type") == "appendix_letter_sequence_repeat":
            assert f.details.get("letter_repeated") == "A"


def test_p063_no_body_start_skipped(tmp_path: Path) -> None:
    """No CHAPTER or APPENDIX body heading → body region not detected → no finding."""
    pdf_path = tmp_path / "p063_no_body.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    # Use plain paragraph text with no CHAPTER/APPENDIX marker — body start not triggered.
    page.insert_text((72.0, 200.0), "This document has only body text and no chapter.", fontsize=12)
    page.insert_text((72.0, 220.0), "No appendix section headings here.", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    # No body-start heading detected → rule skips entirely → no finding.
    assert not _p063_findings(pdf_path)


def test_p063_finding_privacy_safe(tmp_path: Path) -> None:
    """Findings contain only structural metadata; no body text or dissertation content."""
    pdf_path = tmp_path / "p063_privacy.pdf"
    _make_pdf_with_appendix_headings(
        pdf_path,
        [("APPENDIX A First Appendix", 2)],
        include_chapter=True,
    )
    findings = _p063_findings(pdf_path)
    assert len(findings) == 1
    f = findings[0]
    allowed_keys = {
        "issue_type",
        "page",
        "appendix_count",
        "letter_found",
        "triage_tier",
        "source_q_rule_id",
        "bbox",
    }
    for key in f.details:
        assert key in allowed_keys, f"Unexpected metadata key: {key!r}"
    for val in f.details.values():
        assert isinstance(val, str), "All detail values must be str"
    bbox_parts = f.details["bbox"].split(",")
    assert len(bbox_parts) == 4
    for part in bbox_parts:
        float(part)  # must be numeric, not heading text


def test_p063_import_and_wiring(tmp_path: Path) -> None:
    """Module importable; function callable; wired into audit_runner."""
    from njit_auditor.rules.pdf_appendix_body_headings import (
        check_pdf_appendix_body_headings as fn,
    )

    assert callable(fn)

    import inspect

    import njit_auditor.audit_runner as audit_runner

    source = inspect.getsource(audit_runner.collect_pdf_layout_findings)
    assert "check_pdf_appendix_body_headings" in source

    pdf_path = tmp_path / "p063_wire.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72.0, 200.0), "No appendix here.", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    result = fn(model)
    assert isinstance(result, list)


def test_p063_single_page_no_heading_no_crash(tmp_path: Path) -> None:
    """Single-page PDF with no headings → no finding, no crash."""
    pdf_path = tmp_path / "p063_no_heading.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72.0, 200.0), "Just some body text, no appendix.", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_appendix_body_headings(model)
    assert isinstance(findings, list)
    assert not findings


def test_p063_two_appendix_correct_ab(tmp_path: Path) -> None:
    """Two appendices labeled A and B in order → no finding."""
    pdf_path = tmp_path / "p063_two_ab.pdf"
    _make_pdf_with_appendix_headings(
        pdf_path,
        [
            ("APPENDIX A Data Tables", 2),
            ("APPENDIX B Supplementary Figures", 3),
        ],
        include_chapter=True,
    )
    assert not _p063_findings(pdf_path)


def test_p063_finding_rule_id_and_severity(tmp_path: Path) -> None:
    """P063 findings have correct rule_id and WARNING severity."""
    pdf_path = tmp_path / "p063_rule_id.pdf"
    _make_pdf_with_appendix_headings(
        pdf_path,
        [("APPENDIX A With Letter", 2)],
        include_chapter=True,
    )
    findings = _p063_findings(pdf_path)
    assert findings
    from njit_auditor.models import Severity
    for f in findings:
        assert f.rule_id == "P063"
        assert f.severity == Severity.WARNING
