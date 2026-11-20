"""Synthetic tests for P078 — PDF abstract forbidden-term and pronoun check."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import fitz
import pytest

from njit_auditor.audit_runner import collect_pdf_layout_findings
from njit_auditor.pdf_highlight import build_highlighted_pdf
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.pdf_models import BBox, PdfDocument, PdfPage, PdfTextBlock, PdfTextLine
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view
from njit_auditor.rules.pdf_abstract import check_pdf_abstract_keywords

_FT = "abstract_pdf_forbidden_term"
_FP = "abstract_pdf_first_person_pronoun"


def _make_abstract_pdf(path: Path, body: str, include_heading: bool = True) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    if include_heading:
        page.insert_text((250, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    page.insert_text((108, 130), body, fontsize=12)
    doc.save(path)
    doc.close()


def _forbidden_terms(findings: list[Any]) -> list[str]:
    return [f.details["term"] for f in findings if f.details.get("issue_type") == _FT]


def _pronouns(findings: list[Any]) -> list[str]:
    return [
        f.details["pronoun"]
        for f in findings
        if f.details.get("issue_type") == _FP
    ]


def test_p078_no_findings_when_abstract_heading_absent(tmp_path: Path) -> None:
    _make_abstract_pdf(tmp_path / "no_heading.pdf", "This is a study.", include_heading=False)
    model = load_pdf_layout(str(tmp_path / "no_heading.pdf"))
    assert check_pdf_abstract_keywords(model) == []


def test_p078_no_findings_when_abstract_body_is_clean(tmp_path: Path) -> None:
    _make_abstract_pdf(tmp_path / "clean.pdf", "This study examines the problem.")
    model = load_pdf_layout(str(tmp_path / "clean.pdf"))
    assert check_pdf_abstract_keywords(model) == []


def test_p078_forbidden_term_paper(tmp_path: Path) -> None:
    _make_abstract_pdf(tmp_path / "paper.pdf", "In this paper the problem is examined.")
    model = load_pdf_layout(str(tmp_path / "paper.pdf"))
    assert "paper" in _forbidden_terms(check_pdf_abstract_keywords(model))


def test_p078_forbidden_term_article(tmp_path: Path) -> None:
    _make_abstract_pdf(tmp_path / "article.pdf", "This article proposes a framework.")
    model = load_pdf_layout(str(tmp_path / "article.pdf"))
    assert "article" in _forbidden_terms(check_pdf_abstract_keywords(model))


def test_p078_plural_forbidden_terms(tmp_path: Path) -> None:
    _make_abstract_pdf(tmp_path / "plural.pdf", "Prior papers and articles are reviewed.")
    model = load_pdf_layout(str(tmp_path / "plural.pdf"))
    terms = set(_forbidden_terms(check_pdf_abstract_keywords(model)))
    assert "papers" in terms
    assert "articles" in terms


def test_p078_word_boundary_no_false_positive_newspaper(tmp_path: Path) -> None:
    _make_abstract_pdf(tmp_path / "newspaper.pdf", "The newspaper coverage was analyzed.")
    model = load_pdf_layout(str(tmp_path / "newspaper.pdf"))
    terms = _forbidden_terms(check_pdf_abstract_keywords(model))
    assert "newspaper" not in terms
    assert not any("paper" in t for t in terms)


def test_p078_first_person_pronoun_i(tmp_path: Path) -> None:
    _make_abstract_pdf(tmp_path / "pronoun_i.pdf", "I propose a new method for the study.")
    model = load_pdf_layout(str(tmp_path / "pronoun_i.pdf"))
    assert "i" in _pronouns(check_pdf_abstract_keywords(model))


def test_p078_first_person_pronoun_we(tmp_path: Path) -> None:
    _make_abstract_pdf(tmp_path / "pronoun_we.pdf", "We present a framework for analysis.")
    model = load_pdf_layout(str(tmp_path / "pronoun_we.pdf"))
    assert "we" in _pronouns(check_pdf_abstract_keywords(model))


def test_p078_country_abbreviation_us_is_not_a_pronoun(tmp_path: Path) -> None:
    _make_abstract_pdf(tmp_path / "country.pdf", "The US cohort was measured.")
    model = load_pdf_layout(str(tmp_path / "country.pdf"))
    assert _pronouns(check_pdf_abstract_keywords(model)) == []


def test_p078_genuine_us_and_we_still_match(tmp_path: Path) -> None:
    _make_abstract_pdf(tmp_path / "pronouns.pdf", "We compared samples; the result helps us.")
    model = load_pdf_layout(str(tmp_path / "pronouns.pdf"))
    assert set(_pronouns(check_pdf_abstract_keywords(model))) == {"us", "we"}


def test_p078_source_line_has_highlight_geometry(tmp_path: Path) -> None:
    _make_abstract_pdf(tmp_path / "located.pdf", "We evaluated the synthetic result.")
    model = load_pdf_layout(str(tmp_path / "located.pdf"))
    finding = next(
        f for f in check_pdf_abstract_keywords(model) if f.details.get("pronoun") == "we"
    )
    assert finding.details["highlight_scope"] == "line"
    x0, y0, x1, y1 = map(float, finding.details["bbox"].split(","))
    assert x0 < x1 and 100 < y0 < y1 < 150

    report = audit_findings_to_json_dict([finding], {"audit_type": "pdf"})
    assert report["findings"][0]["details"]["bbox"] == finding.details["bbox"]
    view = build_report_view(report, pdf_page_sizes=[(612, 792)])
    assert view.findings[0].has_highlight
    highlighted = tmp_path / "highlighted.pdf"
    result = build_highlighted_pdf(
        tmp_path / "located.pdf", highlighted, {1: [(x0, y0, x1, y1)]}
    )
    assert result.has_highlight and highlighted.exists()


def test_p078_next_section_stops_scan_across_blocks() -> None:
    def line(text: str, y: float) -> PdfTextLine:
        return PdfTextLine(text=text, bbox=BBox(x0=108, y0=y, x1=500, y1=y + 12))

    blocks = [
        PdfTextBlock(lines=[line("ABSTRACT", 80), line("A neutral result.", 120),
                            line("TABLE OF CONTENTS", 180)],
                     bbox=BBox(x0=108, y0=80, x1=500, y1=192), text=""),
        PdfTextBlock(lines=[line("We describe a later section.", 210)],
                     bbox=BBox(x0=108, y0=210, x1=500, y1=222), text=""),
    ]
    model = PdfDocument(path="synthetic.pdf", pages=[
        PdfPage(page_number=1, width=612, height=792, text_blocks=blocks)
    ])
    assert _pronouns(check_pdf_abstract_keywords(model)) == []


@pytest.mark.parametrize("pronoun", ["me", "my", "mine", "we", "us", "our", "ours"])
def test_p078_documented_non_i_pronouns(tmp_path: Path, pronoun: str) -> None:
    _make_abstract_pdf(
        tmp_path / f"pronoun_{pronoun}.pdf",
        f"This abstract includes {pronoun} as a documented first-person form.",
    )
    model = load_pdf_layout(str(tmp_path / f"pronoun_{pronoun}.pdf"))
    assert pronoun in _pronouns(check_pdf_abstract_keywords(model))


def test_p078_lowercase_ie_abbreviation_not_first_person(tmp_path: Path) -> None:
    _make_abstract_pdf(tmp_path / "ie.pdf", "This result is useful, i.e. broadly applicable.")
    model = load_pdf_layout(str(tmp_path / "ie.pdf"))
    assert "i" not in _pronouns(check_pdf_abstract_keywords(model))


def test_p078_standalone_lowercase_i_not_first_person(tmp_path: Path) -> None:
    _make_abstract_pdf(tmp_path / "lower_i.pdf", "The notation i is defined for this study.")
    model = load_pdf_layout(str(tmp_path / "lower_i.pdf"))
    assert "i" not in _pronouns(check_pdf_abstract_keywords(model))


def test_p078_capital_i_punctuation_is_first_person(tmp_path: Path) -> None:
    _make_abstract_pdf(tmp_path / "capital_i_punctuation.pdf", "(I), however, report a result.")
    model = load_pdf_layout(str(tmp_path / "capital_i_punctuation.pdf"))
    assert "i" in _pronouns(check_pdf_abstract_keywords(model))


def test_p078_abbreviation_does_not_suppress_nearby_pronoun(tmp_path: Path) -> None:
    _make_abstract_pdf(tmp_path / "ie_and_we.pdf", "We report this result, i.e. the main finding.")
    model = load_pdf_layout(str(tmp_path / "ie_and_we.pdf"))
    pronouns = _pronouns(check_pdf_abstract_keywords(model))
    assert "i" not in pronouns
    assert "we" in pronouns


def test_p078_case_distinguishes_i_from_I(tmp_path: Path) -> None:
    _make_abstract_pdf(tmp_path / "case_distinction.pdf", "The symbol i differs from (I).")
    model = load_pdf_layout(str(tmp_path / "case_distinction.pdf"))
    pronouns = _pronouns(check_pdf_abstract_keywords(model))
    assert pronouns == ["i"]


def test_p078_pronoun_word_boundary_guard(tmp_path: Path) -> None:
    # "mine" inside "undermined" must not match
    _make_abstract_pdf(tmp_path / "mine_compound.pdf", "The undermined structure was analyzed.")
    model2 = load_pdf_layout(str(tmp_path / "mine_compound.pdf"))
    pronouns2 = {
        f.details.get("pronoun")
        for f in check_pdf_abstract_keywords(model2)
        if f.details.get("issue_type") == _FP
    }
    assert "mine" not in pronouns2


def test_p078_deduplication_repeated_term(tmp_path: Path) -> None:
    _make_abstract_pdf(tmp_path / "dup.pdf", "In this paper this paper is about paper.")
    model = load_pdf_layout(str(tmp_path / "dup.pdf"))
    terms = _forbidden_terms(check_pdf_abstract_keywords(model))
    assert terms.count("paper") == 1


def test_p078_q004_and_q005_coexist(tmp_path: Path) -> None:
    _make_abstract_pdf(tmp_path / "both.pdf", "In this paper we propose a new method.")
    model = load_pdf_layout(str(tmp_path / "both.pdf"))
    findings = check_pdf_abstract_keywords(model)
    issue_types = {f.details.get("issue_type") for f in findings}
    assert _FT in issue_types
    assert _FP in issue_types


def test_p078_does_not_affect_p021(tmp_path: Path) -> None:
    from njit_auditor.rules.pdf_abstract import check_pdf_abstract_word_count

    _make_abstract_pdf(tmp_path / "p021_coexist.pdf", "This study examines the problem.")
    model = load_pdf_layout(str(tmp_path / "p021_coexist.pdf"))
    p021_findings = check_pdf_abstract_word_count(model)
    p078_findings = check_pdf_abstract_keywords(model)
    assert not any(f.rule_id == "P021" for f in p021_findings)
    assert p078_findings == []


def test_p078_wired_in_audit_runner(tmp_path: Path) -> None:
    pdf_path = tmp_path / "runner.pdf"
    _make_abstract_pdf(pdf_path, "In this paper we study the problem.")
    doc = load_pdf_layout(str(pdf_path))
    findings = collect_pdf_layout_findings(doc, pdf_path)
    p078 = [f for f in findings if f.rule_id == "P078"]
    assert len(p078) >= 2  # at least one forbidden term + one pronoun


def test_p078_finding_details_fields(tmp_path: Path) -> None:
    _make_abstract_pdf(tmp_path / "fields.pdf", "In this paper we present findings.")
    model = load_pdf_layout(str(tmp_path / "fields.pdf"))
    findings = check_pdf_abstract_keywords(model)
    for f in findings:
        assert f.rule_id == "P078"
        assert f.details.get("triage_tier") == "check"
        assert f.details.get("confidence") == "medium"
        assert "source_q_rule_ids" in f.details
        if f.details.get("issue_type") == _FT:
            assert "term" in f.details
            assert f.details["source_q_rule_ids"] == "Q004"
        elif f.details.get("issue_type") == _FP:
            assert "pronoun" in f.details
            assert f.details["source_q_rule_ids"] == "Q005"
