"""R011 student wording on landscape sheets (presentation only, synthetic PDFs).

The detector records ``page_orientation``/``binding_edge`` for landscape
sheets (see ``rules.pdf_margins.MarginFrame``). Expected/fix wording must name
the page's binding edge instead of the portrait "left 1.5 inches" rule, and
portrait wording must stay byte-for-byte unchanged.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from njit_auditor.finding_explanations import _p011_margin_explanation
from njit_auditor.p011_margin_presentation import (
    margin_primary_remediation,
    margin_requirement_phrase,
    margin_suggested_fix,
)
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view
from njit_auditor.rules.pdf_margins import run_pdf_margin_rule

PORTRAIT_REQUIREMENT = "(left 1.5 inches; right, top, and bottom 1 inch)"
PORTRAIT_REMEDIATION = "Set left margin to 1.5 inches and top, bottom, and right margin to 1 inch."


def _landscape(side: str, binding_edge: str) -> dict[str, str]:
    return {"side": side, "page_orientation": "landscape", "binding_edge": binding_edge}


@pytest.mark.parametrize("side", ["left_margin", "right_margin", "top_margin", "bottom_margin"])
def test_portrait_wording_is_unchanged(side: str) -> None:
    details = {"side": side}
    assert margin_requirement_phrase(details) == PORTRAIT_REQUIREMENT
    assert margin_requirement_phrase() == PORTRAIT_REQUIREMENT
    assert margin_primary_remediation(details) == PORTRAIT_REMEDIATION
    kwargs = {"page_context": "body", "content_kind": "text_paragraph", "side_label": "left margin"}
    assert margin_suggested_fix(**kwargs, details=details) == margin_suggested_fix(**kwargs)


@pytest.mark.parametrize("edge", ["top", "bottom"])
def test_binding_edge_finding_names_that_edge(edge: str) -> None:
    details = _landscape(f"{edge}_margin", edge)
    phrase = margin_requirement_phrase(details)
    assert f"the document's 1.5-inch binding margin is the {edge} edge" in phrase
    assert "the other three edges need 1 inch" in phrase
    fix = margin_primary_remediation(details)
    assert f"on this page is the {edge} edge" in fix
    assert "inside the 1.5-inch binding-margin line" in fix
    assert "left margin to 1.5 inches" not in fix
    assert "left 1.5" not in phrase


def test_non_binding_edge_finding_keeps_the_one_inch_requirement() -> None:
    fix = margin_primary_remediation(_landscape("left_margin", "top"))
    assert "inside the 1-inch left margin line" in fix
    assert "on this page is the top edge" in fix
    fix = margin_primary_remediation(_landscape("top_margin", "bottom"))
    assert "inside the 1-inch top margin line" in fix


def test_undetermined_binding_edge_makes_no_edge_specific_claim() -> None:
    details = _landscape("top_margin", "undetermined")
    phrase = margin_requirement_phrase(details)
    fix = margin_primary_remediation(details)
    for text in (phrase, fix):
        assert "is the top edge" not in text and "is the bottom edge" not in text
        assert "at least 1 inch on every edge" in text
    assert "inside the 1-inch top margin line" in fix


def _landscape_pdf(tmp_path: Path) -> Path:
    import fitz

    doc = fitz.open()
    page = doc.new_page(width=792, height=612)
    body = "Synthetic landscape table row with enough words to be a real line"
    page.insert_text((120, 100), body, fontsize=11)  # inside the 1.5 in binding (top) edge
    page.insert_text((120, 300), body, fontsize=11)
    page.insert_text((50, 306), "81", fontsize=12, rotate=270)  # portrait page number
    path = tmp_path / "landscape.pdf"
    doc.save(path)
    doc.close()
    return path


def test_web_view_explanations_and_stored_fix_share_the_landscape_semantics(
    tmp_path: Path,
) -> None:
    (finding,) = [
        f
        for f in run_pdf_margin_rule(load_pdf_layout(str(_landscape_pdf(tmp_path))))
        if f.severity.value == "WARNING"
    ]
    details = finding.details
    assert details["binding_edge"] == "top" and details["side"] == "top_margin"
    expected = margin_requirement_phrase(details)

    view = build_report_view(audit_findings_to_json_dict([finding], {"audit_type": "pdf"}))
    rendered = next(f for f in view.findings if f.rule_id == "P011")
    assert expected in rendered.detailed_explanation
    assert "1.5-inch binding margin on this landscape page" in rendered.polished_comment
    assert rendered.suggested_fix.startswith(margin_primary_remediation(details))
    assert details["suggested_fix"].startswith(margin_primary_remediation(details)[:40])

    markdown_explanation = _p011_margin_explanation(dict(details), page=finding.page)
    assert expected in markdown_explanation
    for text in (rendered.detailed_explanation, rendered.suggested_fix, markdown_explanation):
        assert "left 1.5 inches" not in text and "Set left margin" not in text


def test_text_report_detruncation_keeps_landscape_wording() -> None:
    from njit_auditor.report_text import _detruncate_fix_text

    truncated = "Landscape pages keep the document's 1.5-inch binding margin, which..."
    landscape = _landscape("top_margin", "top")
    assert _detruncate_fix_text("P011", truncated, landscape) == margin_primary_remediation(
        landscape
    )
    portrait_truncated = "Set left margin to 1.5 inches and top, bottom, and right..."
    assert _detruncate_fix_text("P011", portrait_truncated, {"side": "right_margin"}) == (
        _detruncate_fix_text("P011", portrait_truncated)
    )
    assert _detruncate_fix_text("P011", "Full fix.", landscape) == "Full fix."


def test_multi_side_page_card_names_the_binding_edge_only_on_landscape() -> None:
    from njit_auditor.p011_student_preview import (
        P011PagePresentationStats,
        p011_combined_suggested_fix,
    )

    portrait = P011PagePresentationStats(
        page=5, sides=("left_margin", "right_margin"), raw_finding_count=2
    )
    assert p011_combined_suggested_fix(portrait).startswith(PORTRAIT_REMEDIATION)
    landscape = P011PagePresentationStats(
        page=5,
        sides=("left_margin", "top_margin"),
        raw_finding_count=2,
        page_orientation="landscape",
        binding_edge="bottom",
    )
    fix = p011_combined_suggested_fix(landscape)
    assert "on this page is the bottom edge" in fix
    assert PORTRAIT_REMEDIATION not in fix
