"""P026 font-policy tests: CMR/LaTeX false-positive fix (Ester feedback).

Covers:
1. classify_font() still correct for CMR, Times, math, other
2. _infer_pdf_origin() for latex / word / unknown creator strings
3. Issue-type routing: CMR+LaTeX → latex_cm; CMR+Word → standard; non-CMR+LaTeX → standard
4. Student-facing text guardrails for the latex_cm path
5. Times New Roman PDF gets no family warning (no regression)
"""

from __future__ import annotations

from njit_auditor.pdf_models import (
    BBox,
    PdfDocument,
    PdfPage,
    PdfTextBlock,
    PdfTextLine,
    PdfTextSpan,
)
from njit_auditor.rules.pdf_font_compliance import (
    _infer_pdf_origin,
    check_pdf_font_compliance,
    classify_font,
)

# ---------------------------------------------------------------------------
# Synthetic document builder helpers
# ---------------------------------------------------------------------------

_PAGE_HEIGHT = 792.0
_PAGE_WIDTH = 612.0

_BODY_TEXT = (
    "The quick brown fox jumps over the lazy dog and writes a dissertation."
)


def _body_span(font: str, size: float = 12.0, y0: float = 300.0) -> PdfTextSpan:
    return PdfTextSpan(
        text=_BODY_TEXT,
        font=font,
        size=size,
        bold=False,
        italic=False,
        bbox=BBox(x0=72.0, y0=y0, x1=540.0, y1=y0 + 14.0),
    )


def _body_line(font: str, size: float = 12.0, y0: float = 300.0) -> PdfTextLine:
    sp = _body_span(font, size=size, y0=y0)
    return PdfTextLine(text=sp.text, bbox=sp.bbox, spans=[sp])


def _body_block(
    font: str, n: int = 8, size: float = 12.0, y0_start: float = 200.0
) -> PdfTextBlock:
    lines = [_body_line(font, size=size, y0=y0_start + i * 16.0) for i in range(n)]
    all_y0 = min(ln.bbox.y0 for ln in lines)
    all_y1 = max(ln.bbox.y1 for ln in lines)
    return PdfTextBlock(
        bbox=BBox(x0=72.0, y0=all_y0, x1=540.0, y1=all_y1),
        lines=lines,
        text=" ".join(ln.text for ln in lines),
    )


def _page_with_block(block: PdfTextBlock, page_number: int = 5) -> PdfPage:
    return PdfPage(
        page_number=page_number,
        width=_PAGE_WIDTH,
        height=_PAGE_HEIGHT,
        text_blocks=[block],
    )


def _doc(font: str, *, creator: str | None = None, size: float = 12.0) -> PdfDocument:
    block = _body_block(font, size=size)
    page = _page_with_block(block)
    return PdfDocument(path="synthetic", pages=[page], creator=creator)


def _family_findings(doc: PdfDocument) -> list:
    return [
        f
        for f in check_pdf_font_compliance(doc)
        if f.details.get("issue_type", "").startswith("possible_body_font_family")
    ]


# ---------------------------------------------------------------------------
# Group 1: classify_font()
# ---------------------------------------------------------------------------


class TestClassifyFont:
    def test_times_new_roman_psmt(self):
        assert classify_font("TimesNewRomanPSMT") == "times"

    def test_times_roman(self):
        assert classify_font("Times-Roman") == "times"

    def test_times_new_roman_bold(self):
        assert classify_font("TimesNewRomanPS-BoldMT") == "times"

    def test_nimbus_rom(self):
        assert classify_font("NimbusRomNo9L-Regu") == "times"

    def test_cmr_is_computer_modern(self):
        assert classify_font("CMR12") == "computer_modern"

    def test_cmbx_is_computer_modern(self):
        assert classify_font("CMBX12") == "computer_modern"

    def test_cmti_is_computer_modern(self):
        assert classify_font("CMTI10") == "computer_modern"

    def test_lmroman_is_computer_modern(self):
        assert classify_font("LMRoman10-Regular") == "computer_modern"

    def test_lmbx_is_computer_modern(self):
        assert classify_font("LMBx10") == "computer_modern"

    def test_cmmi_is_math(self):
        assert classify_font("CMMI10") == "math"

    def test_cmsy_is_math(self):
        assert classify_font("CMSY10") == "math"

    def test_symbol_is_math(self):
        assert classify_font("Symbol") == "math"

    def test_unknown_none(self):
        assert classify_font(None) == "unknown"

    def test_unknown_empty(self):
        assert classify_font("") == "unknown"

    def test_embedded_subset_stripped(self):
        assert classify_font("ABCDEF+TimesNewRomanPSMT") == "times"

    def test_embedded_subset_cmr(self):
        assert classify_font("ABCDEF+CMR12") == "computer_modern"

    def test_georgia_is_other(self):
        assert classify_font("Georgia") == "other"

    def test_arial_is_other(self):
        assert classify_font("ArialMT") == "other"


# ---------------------------------------------------------------------------
# Group 2: _infer_pdf_origin()
# ---------------------------------------------------------------------------


class TestInferPdfOrigin:
    def test_pdflatex_creator(self):
        assert _infer_pdf_origin("pdfTeX-1.40.21") == "latex"

    def test_latex_creator(self):
        assert _infer_pdf_origin("LaTeX with hyperref") == "latex"

    def test_xetex_creator(self):
        assert _infer_pdf_origin("XeTeX output 2024.05.01") == "latex"

    def test_lualatex_creator(self):
        assert _infer_pdf_origin("LuaLaTeX") == "latex"

    def test_word_creator(self):
        assert _infer_pdf_origin("Microsoft Word") == "word"

    def test_libreoffice_creator(self):
        assert _infer_pdf_origin("LibreOffice 7.6") == "word"

    def test_openoffice_creator(self):
        assert _infer_pdf_origin("OpenOffice.org Writer") == "word"

    def test_acrobat_creator(self):
        assert _infer_pdf_origin("Adobe Acrobat 23.0") == "word"

    def test_none_creator(self):
        assert _infer_pdf_origin(None) == "unknown"

    def test_empty_creator(self):
        assert _infer_pdf_origin("") == "unknown"

    def test_unknown_creator(self):
        assert _infer_pdf_origin("Quark XPress") == "unknown"


# ---------------------------------------------------------------------------
# Group 3: Issue-type routing via check_pdf_font_compliance()
# ---------------------------------------------------------------------------


class TestIssueTypeRouting:
    def test_cmr_latex_emits_latex_cm_issue_type(self):
        doc = _doc("CMR12", creator="pdfTeX-1.40.21")
        findings = _family_findings(doc)
        assert len(findings) >= 1
        assert all(
            f.details["issue_type"] == "possible_body_font_family_issue_latex_cm"
            for f in findings
        )

    def test_cmr_latex_pdf_origin_recorded(self):
        doc = _doc("CMR12", creator="LaTeX with hyperref")
        findings = _family_findings(doc)
        assert all(f.details.get("pdf_origin") == "latex" for f in findings)

    def test_cmr_word_emits_standard_issue_type(self):
        doc = _doc("CMR12", creator="Microsoft Word")
        findings = _family_findings(doc)
        assert len(findings) >= 1
        assert all(
            f.details["issue_type"] == "possible_body_font_family_issue"
            for f in findings
        )

    def test_cmr_unknown_origin_emits_standard_issue_type(self):
        doc = _doc("CMR12", creator=None)
        findings = _family_findings(doc)
        assert len(findings) >= 1
        assert all(
            f.details["issue_type"] == "possible_body_font_family_issue"
            for f in findings
        )

    def test_georgia_latex_emits_standard_issue_type(self):
        doc = _doc("Georgia", creator="pdfTeX-1.40.21")
        findings = _family_findings(doc)
        assert len(findings) >= 1
        assert all(
            f.details["issue_type"] == "possible_body_font_family_issue"
            for f in findings
        )

    def test_georgia_word_emits_standard_issue_type(self):
        doc = _doc("Georgia", creator="Microsoft Word")
        findings = _family_findings(doc)
        assert len(findings) >= 1
        assert all(
            f.details["issue_type"] == "possible_body_font_family_issue"
            for f in findings
        )

    def test_pdf_origin_always_in_family_finding_details(self):
        cases = [
            ("pdfTeX-1.40.21", "latex"),
            ("Microsoft Word", "word"),
            (None, "unknown"),
        ]
        for creator, expected_origin in cases:
            doc = _doc("CMR12", creator=creator)
            for f in check_pdf_font_compliance(doc):
                if f.details.get("issue_type", "").startswith("possible_body_font_family"):
                    got = f.details.get("pdf_origin")
                    assert got == expected_origin, (
                        f"creator={creator!r}: expected pdf_origin={expected_origin!r}, got {got!r}"
                    )

    def test_size_issue_pdf_origin_in_details(self):
        doc = _doc("CMR12", creator="pdfTeX-1.40.21", size=10.0)
        size_findings = [
            f for f in check_pdf_font_compliance(doc)
            if f.details.get("issue_type") == "possible_body_font_size_issue"
        ]
        assert all(f.details.get("pdf_origin") == "latex" for f in size_findings)


# ---------------------------------------------------------------------------
# Group 4: Student-facing text guardrails for latex_cm path
# ---------------------------------------------------------------------------


class TestStudentFacingText:
    def test_latex_cm_message_mentions_advisor(self):
        doc = _doc("CMR12", creator="pdfTeX-1.40.21")
        latex_cm = [
            f for f in check_pdf_font_compliance(doc)
            if f.details.get("issue_type") == "possible_body_font_family_issue_latex_cm"
        ]
        assert latex_cm, "Expected latex_cm finding to exist"
        for f in latex_cm:
            fix = f.details.get("suggested_fix", "")
            assert "advisor" in f.message.lower() or "advisor" in fix.lower()

    def test_latex_cm_suggested_fix_does_not_say_word(self):
        doc = _doc("CMR12", creator="pdfTeX-1.40.21")
        for f in check_pdf_font_compliance(doc):
            if f.details.get("issue_type") == "possible_body_font_family_issue_latex_cm":
                fix = f.details.get("suggested_fix", "")
                assert "word:" not in fix.lower(), (
                    f"latex_cm fix should not mention Word: {fix!r}"
                )

    def test_latex_cm_suggested_fix_mentions_mathptmx(self):
        doc = _doc("CMR12", creator="pdfTeX-1.40.21")
        for f in check_pdf_font_compliance(doc):
            if f.details.get("issue_type") == "possible_body_font_family_issue_latex_cm":
                fix = f.details.get("suggested_fix", "")
                assert "mathptmx" in fix, (
                    f"latex_cm fix should mention mathptmx: {fix!r}"
                )

    def test_word_path_fix_mentions_times_new_roman(self):
        doc = _doc("Georgia", creator="Microsoft Word")
        for f in check_pdf_font_compliance(doc):
            if f.details.get("issue_type") == "possible_body_font_family_issue":
                fix = f.details.get("suggested_fix", "")
                assert "times new roman" in fix.lower(), (
                    f"Word fix should mention Times New Roman: {fix!r}"
                )


# ---------------------------------------------------------------------------
# Group 5: Times New Roman gets no family warning (no regression)
# ---------------------------------------------------------------------------


class TestTimesNoWarning:
    def test_times_new_roman_no_family_finding(self):
        doc = _doc("TimesNewRomanPSMT", creator="Microsoft Word")
        findings = _family_findings(doc)
        assert findings == [], (
            f"Times New Roman should produce no family findings, got: {findings}"
        )

    def test_times_new_roman_latex_no_family_finding(self):
        doc = _doc("TimesNewRomanPSMT", creator="pdfTeX-1.40.21")
        assert _family_findings(doc) == []

    def test_nimbus_rom_no_family_finding(self):
        doc = _doc("NimbusRomNo9L-Regu", creator=None)
        assert _family_findings(doc) == []
