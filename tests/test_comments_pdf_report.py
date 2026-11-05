"""Synthetic checks for comments-only content, Unicode, and pagination."""

from __future__ import annotations

import re
from copy import deepcopy

import fitz
import pytest
from comments_pdf_helpers import assert_comments_pdf_parity

from njit_auditor.comments_pdf_report import render_comments_pdf_report
from njit_auditor.incomplete_audit import incomplete_audit_notice
from njit_auditor.student_pdf_report import render_student_report_text


def _finding(number: int, page: int | None) -> dict:
    return {
        "problem_number": number,
        "page": page,
        "rule_id": "P012",
        "polished_comment": f"Synthetic annotation {number} — résumé, αβγ, ≤ ± × →, 中文, 😀.",
        "suggested_fix": "Remove the synthetic note; keep <literal> & quoted text.",
        "detailed_explanation": "Synthetic explanation with smart ‘quotes’ and an en–dash.",
        "location_label": f"PDF page {page}" if page else "Whole document",
        "confidence_label": "High confidence",
        "has_highlight": False,
        "no_highlight_reason": "No reliable coordinates for this synthetic finding.",
    }


def test_comments_pdf_preserves_every_text_field_and_unhighlighted_finding() -> None:
    findings = [_finding(3, None), _finding(2, 4), _finding(1, 1)]
    before = deepcopy(findings)
    canonical = render_student_report_text(
        findings,
        file_name="résumé_中文.pdf",
        manuscript_page_labels={4: "iv"},
        failed_check_count=2,
    )
    payload = render_comments_pdf_report(canonical)
    assert_comments_pdf_parity(payload, canonical)
    assert findings == before
    with fitz.open(stream=payload, filetype="pdf") as document:
        text = "\n".join(page.get_text() for page in document)
        assert text.index("Problem #1") < text.index("Problem #2") < text.index("Problem #3")
        assert "Manuscript page: iv" in text
        assert "DOCUMENT-LEVEL FINDINGS" in text
        assert text.count("Exact visual highlight unavailable.") == 2
        assert document.metadata["title"] == "NJIT Thesis/Dissertation Comments Report"
        assert "".join(incomplete_audit_notice(2).split()) in "".join(text.split())
        assert "Public rule reference: R012" in text


@pytest.mark.parametrize("failed_checks", [0, 3])
def test_empty_findings_still_include_scope_and_incomplete_notices(failed_checks: int) -> None:
    canonical = render_student_report_text(
        [],
        file_name="synthetic.pdf",
        failed_check_count=failed_checks,
    )
    payload = render_comments_pdf_report(canonical)
    assert_comments_pdf_parity(payload, canonical)
    with fitz.open(stream=payload, filetype="pdf") as document:
        assert 1 <= document.page_count <= 3
        text = " ".join(page.get_text() for page in document)
        assert "No formatting problems were detected" in text
        assert "Problem #" not in text


def test_long_findings_tokens_and_many_problems_flow_within_margins() -> None:
    findings = [_finding(number, number) for number in range(1, 36)]
    findings[0]["polished_comment"] += " Long explanation with Unicode résumé. " * 200
    findings[0]["suggested_fix"] += "X" * 1400 + " Final correction survives."
    canonical = render_student_report_text(findings, file_name="synthetic.pdf")
    payload = render_comments_pdf_report(canonical)
    assert_comments_pdf_parity(payload, canonical)
    with fitz.open(stream=payload, filetype="pdf") as document:
        assert document.page_count > 5
        for number, page in enumerate(document, 1):
            assert f"Report page {number}" in page.get_text()
            for source_page in re.findall(r"PDF PAGE (\d+)", page.get_text()):
                assert f"Problem #{source_page} —" in page.get_text()
            assert page.rect == fitz.Rect(0, 0, 612, 792)
            for word in page.get_text("words"):
                assert 53 <= word[0] <= word[2] <= 559
                assert 10 <= word[1] <= word[3] <= 772


def test_literal_markup_never_embeds_external_resources_or_links() -> None:
    finding = _finding(1, 1)
    finding["polished_comment"] = (
        '<img src="https://example.invalid/private.png"> '
        '<a href="file:///private/dissertation.pdf">literal text</a>'
    )
    canonical = render_student_report_text([finding], file_name="<synthetic>.pdf")
    assert_comments_pdf_parity(render_comments_pdf_report(canonical), canonical)


def test_renderer_works_with_all_socket_connections_and_dns_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import socket

    def deny(*args: object, **kwargs: object) -> None:
        raise AssertionError("Comments PDF attempted network access")

    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket.socket, "connect_ex", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)
    canonical = render_student_report_text([_finding(1, 1)], file_name="synthetic.pdf")
    assert_comments_pdf_parity(render_comments_pdf_report(canonical), canonical)
