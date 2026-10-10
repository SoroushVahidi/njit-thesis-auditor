"""Synthetic coverage of Q051 without private dissertation text."""

from njit_auditor.pdf_models import (
    BBox,
    PdfDocument,
    PdfPage,
    PdfTextBlock,
    PdfTextLine,
    PdfTextSpan,
)
from njit_auditor.report_outputs import (
    audit_findings_to_json_dict,
    individual_finding_comment_and_fix,
    public_display_rule_id,
)
from njit_auditor.report_view import build_report_view
from njit_auditor.rules.pdf_toc_list_formatting import check_pdf_toc_list_formatting
from njit_auditor.web_app import _public_rule_reference_id


def _document(rows: list[str], prose: str = "") -> PdfDocument:
    lines = [PdfTextLine(text="TABLE OF CONTENTS", bbox=BBox(x0=220, y0=80, x1=390, y1=92))]
    lines += [
        PdfTextLine(
            text=row,
            bbox=BBox(
                x0=150
                if row.startswith("numerical ")
                else 110 + (25 if row.startswith("1.1") else 0),
                y0=131 + 23 * i if row.startswith("numerical ") else 140 + 23 * i,
                x1=540,
                y1=143 + 23 * i if row.startswith("numerical ") else 152 + 23 * i,
            ),
        )
        for i, row in enumerate(rows)
    ]
    toc = PdfPage(
        page_number=1,
        width=612,
        height=792,
        text_blocks=[
            PdfTextBlock(
                lines=lines,
                bbox=BBox(x0=110, y0=80, x1=540, y1=730),
                text="\n".join(line.text for line in lines),
            )
        ],
    )
    pages = [toc]
    if prose:
        body_box = BBox(x0=110, y0=140, x1=540, y1=152)
        body_line = PdfTextLine(
            text=prose, bbox=body_box, spans=[PdfTextSpan(text=prose, bbox=body_box)]
        )
        pages.append(
            PdfPage(
                page_number=2,
                width=612,
                height=792,
                text_blocks=[PdfTextBlock(lines=[body_line], bbox=body_line.bbox, text=prose)],
            )
        )
    return PdfDocument(path="synthetic.pdf", pages=pages)


def _level3(rows: list[str], prose: str = ""):
    return [
        f
        for f in check_pdf_toc_list_formatting(_document(rows, prose))
        if f.details.get("entry_level") == "3"
    ]


def test_clear_two_word_title_case_routes_to_r018c_with_entry_highlight() -> None:
    rows = [
        "1 INTRODUCTION .... 1",
        "1.1 Research Context .... 2",
        "1.1.1 Problem Formulation . . . . 3",
        "1.1.2 Problem formulation . . . . 4",
    ]
    findings = _level3(rows, "The formulation is explained in this section.")
    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule_id == "P024"
    assert finding.details["source_q_rule_id"] == "Q051"
    assert finding.details["issue_type"] == "toc_level_capitalization"
    assert finding.details["line_preview"].startswith("1.1.1 Problem Formulation")
    assert finding.details["bbox"] == "135.0,186.0,540.0,198.0"
    card = _public_rule_reference_id(
        finding.rule_id,
        issue_type=finding.details["issue_type"],
        source_q_rule_id=finding.details["source_q_rule_id"],
        details=finding.details,
    )
    assert public_display_rule_id(card) == "R018C"
    view = build_report_view(
        audit_findings_to_json_dict(findings, {"audit_type": "pdf"}),
        pdf_page_sizes=[(612, 792), (612, 792)],
    )
    assert view.findings[0].has_highlight
    assert "sentence case" in finding.message.lower()
    assert "proper names" in finding.message.lower()
    comment, fix = individual_finding_comment_and_fix(
        finding.rule_id,
        finding.details["issue_type"],
        severity="WARNING",
        page=finding.page,
        details=finding.details,
    )
    assert "Level 3" in comment and "sentence case" in comment
    assert "Level 2" not in comment
    assert "level-3" in fix and "sentence case" in fix


def test_other_levels_and_uncertain_titles_abstain() -> None:
    rows = [
        "1 INTRODUCTION .... 1",
        "1.1 Research Context .... 2",
        "1.1.1 Research context .... 3",
        "1.1.1.1 Problem Formulation .... 4",
        "1.1.2 Markov Chain .... 5",
        "1.1.3 MRI Analysis .... 6",
        "1.1.4 i.e. examples and e.g. notation .... 7",
        "1.1.5 ﬁnite element modeling .... 8",
        "1.1.6 Problem Formulation . . . .",  # detached page number
        "1.1.7 Methodology: Constraints .... 9",
        "1.1.8 Methodology: Constraints and Modeling .... 10",
    ]
    assert (
        _level3(
            rows,
            "The formulation and constraints are discussed; "
            "a Markov chain appears in Markov models.",
        )
        == []
    )


def test_wrapped_level3_title_is_checked_once() -> None:
    rows = [
        "1 INTRODUCTION .... 1",
        "1.1 Research Context .... 2",
        "1.1.1 Model Design and Validation for",
        "numerical analysis . . . . 3",
        "1.1.2 Model design for numerical analysis .... 4",
    ]
    findings = _level3(rows)
    assert len(findings) == 1
    assert "numerical analysis" in findings[0].details["line_preview"]
