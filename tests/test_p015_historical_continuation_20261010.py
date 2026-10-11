"""Real-page P015 regressions from historical Ester review documents.

The assertions use page and rectangle metadata only; dissertation prose stays
in the private PDFs. Yin is a positive control: Ester marked that exact indent
for removal in both the second and third review versions.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from njit_auditor.highlight_targeting import parse_highlight_bboxes_from_details
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.pdf_models import PdfDocument
from njit_auditor.rules.pdf_indentation import check_pdf_indentation

_ESTER_DIR = Path(__file__).resolve().parents[1] / "data/raw/ester"
_PENNOCK = _ESTER_DIR / "250213 Pennock Andrew Revised 1st Dissertation Draft with EF comments.pdf"
_TERMINI = _ESTER_DIR / "250415 Termini_DoloresThirdReview with EF comments.pdf"
_YIN = _ESTER_DIR / "Yin_Haotian_Second_R_with_EF_Feedback.pdf"
_YIN_THIRD = _ESTER_DIR / "260428 Yin H 3rd review with EF Comments.pdf"


def _load(path: Path) -> PdfDocument:
    if not path.exists() or path.stat().st_size < 1000:
        pytest.skip("historical Ester PDF is unavailable")
    return load_pdf_layout(str(path))


@pytest.fixture(scope="module")
def pennock() -> PdfDocument:
    return _load(_PENNOCK)


@pytest.fixture(scope="module")
def termini() -> PdfDocument:
    return _load(_TERMINI)


def _page_findings(document: PdfDocument, physical_page: int) -> list:
    page_only = PdfDocument(path=document.path, pages=[document.pages[physical_page - 1]])
    return check_pdf_indentation(page_only)


@pytest.mark.parametrize("physical_page", [40, 121, 134])
def test_pennock_split_equation_row_is_not_an_indented_continuation(
    pennock: PdfDocument, physical_page: int
) -> None:
    # Each printed row starts flush left; PDF extraction drops a short math
    # prefix and makes its usable second fragment look indented.
    assert _page_findings(pennock, physical_page) == []


def test_pennock_completed_adjacent_paragraph_is_not_a_continuation(
    pennock: PdfDocument,
) -> None:
    # The page-58 line is a correctly indented new paragraph after a period.
    assert _page_findings(pennock, 58) == []


def test_termini_wrapped_code_comment_is_not_a_body_paragraph(
    termini: PdfDocument,
) -> None:
    assert _page_findings(termini, 116) == []


@pytest.mark.parametrize("path, physical_page", [(_YIN, 22), (_YIN_THIRD, 26)])
def test_yin_ester_marked_real_continuation_indent_remains_highlighted(
    path: Path, physical_page: int
) -> None:
    findings = _page_findings(_load(path), physical_page)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.details["issue_type"] == "unexpected_indent_on_continuation_line"
    assert parse_highlight_bboxes_from_details(finding.details) == [
        (136.8, 321.7, 540.0, 333.6)
    ]
