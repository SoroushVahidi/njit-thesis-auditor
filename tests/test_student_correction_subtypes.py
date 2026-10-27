"""Semantic checks using the eight independently reproduced synthetic cases."""

from __future__ import annotations

import importlib
import re
from html import unescape
from pathlib import Path
from typing import Any

import fitz
import pytest
from fastapi.testclient import TestClient
from test_p063_appendix_body_headings import _make_pdf_with_appendix_headings
from test_p064_references_citations_structural import (
    _ENTRY_GAP,
    _insert_flush_entry,
    _insert_hanging_entry,
    _insert_heading,
    _new_doc_with_chapter,
)
from test_p065_dedication_centering_italic import (
    _PLACEHOLDER_1,
    _PLACEHOLDER_2,
    _PLACEHOLDER_3,
    _make_dedication_page,
)
from test_p067_biosketch_publication_ordering import (
    _make_biosketch_publication_doc,
    _make_entry,
)

from njit_auditor.student_actions import short_student_action

EXPECTED_ACTIONS = {
    (
        "P027",
        "level1_not_all_caps",
    ): "Check whether this chapter heading should be in ALL CAPITALS.",
    ("P027", "level2_title_case_issue"): (
        "Check whether this level-2 heading needs title case: "
        "capitalize the first word and major words."
    ),
    (
        "P027",
        "level4_sentence_case_or_punctuation_issue",
    ): "Check whether this level-4 heading needs a final period.",
    (
        "P063",
        "single_appendix_uses_letter_label",
    ): "If this is the only appendix, remove its letter and use APPENDIX followed by the title.",
    ("P064", "references_entry_indentation_inconsistent"): (
        "If these reference entries mix indentation styles, use one style consistently, "
        "following the style agreed with your advisor."
    ),
    (
        "P065",
        "dedication_text_not_centered",
    ): "Check whether the dedication text is centered within the text area.",
    (
        "P065",
        "dedication_text_not_italic",
    ): "Check whether the dedication text uses an italic or oblique font.",
    (
        "P067",
        "biosketch_publication_order_suspicious",
    ): "Check the publication years, then order entries from newest to oldest if needed.",
}


def correction_pdfs(directory: Path) -> list[Path]:
    """Generate review reproductions; all content is synthetic."""
    directory.mkdir(parents=True, exist_ok=True)
    paths = [
        directory / f"{kind}.pdf"
        for kind in ("appendix", "references", "dedication", "publications", "headings")
    ]
    _make_pdf_with_appendix_headings(
        paths[0], [("APPENDIX A Supporting Material", 2)], include_chapter=True
    )
    doc = _new_doc_with_chapter(num_body_pages=8)
    _insert_heading(doc, 6, "REFERENCES")
    y = 130.0
    for _ in range(3):
        y = _insert_hanging_entry(doc, 6, y, first_x=72, cont_x=102) + _ENTRY_GAP
    for _ in range(3):
        y = _insert_flush_entry(doc, 6, y, x=72) + _ENTRY_GAP
    doc.save(paths[1])
    doc.close()
    doc = _make_dedication_page(
        dedic_text_lines=[
            (108, text, "helv") for text in (_PLACEHOLDER_1, _PLACEHOLDER_2, _PLACEHOLDER_3)
        ]
    )
    doc.save(paths[2])
    doc.close()
    doc = _make_biosketch_publication_doc(
        publication_entries=[
            _make_entry(f"Placeholder Author {label} Placeholder Title", year)
            for label, year in (("Alpha", 2015), ("Beta", 2019), ("Gamma", 2023))
        ]
    )
    doc.save(paths[3])
    doc.close()
    doc = fitz.open()
    page = doc.new_page()
    for y, text, size in (
        (100, "CHAPTER 1 Introduction", 14),
        (170, "1.1 a synthetic heading", 12),
        (270, "1.1.1.1 A synthetic heading", 12),
    ):
        page.insert_text((108, y), text, fontname="hebo", fontsize=size)
    for y in (200, 300):
        page.insert_text((108, y), "Synthetic body paragraph for heading review.", fontsize=12)
    doc.save(paths[4])
    doc.close()
    return paths


def test_reproduced_actions_and_complete_exports(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setenv("NJIT_AUDITOR_WEB_RUNTIME_DIR", str(tmp_path / "jobs"))
    import njit_auditor.web_app as wa

    importlib.reload(wa)
    monkeypatch.setattr(wa, "list_builtin_samples", lambda: [])
    client = TestClient(wa.app)
    seen = set()
    for path in correction_pdfs(tmp_path / "pdfs"):
        response = client.post(
            "/audits",
            files={"file": (path.name, path.read_bytes(), "application/pdf")},
            follow_redirects=False,
        )
        assert response.status_code == 303
        url = response.headers["location"]
        job = wa._get_job(url.rsplit("/", 1)[-1])
        assert job.state == "complete"
        html = unescape(client.get(url).text)
        text = " ".join(client.get(url + "/download/text").text.split())
        markdown = client.get(url + "/download/markdown").text
        exported = client.get(url + "/download/json").json()
        pdf = client.get(url + "/download/student-report.pdf")
        assert pdf.status_code == 200
        with fitz.open(stream=pdf.content, filetype="pdf") as report:
            pdf_text = " ".join(" ".join(p.get_text() for p in report).split())
            pdf_text = re.sub(r"Formatting Problems \| Report page \d+ ?", "", pdf_text)
        assert "student_web_action" not in str(exported)
        for finding in job.findings:
            key = finding["rule_id"], finding["issue_type"]
            if key not in EXPECTED_ACTIONS:
                continue
            seen.add(key)
            assert finding["student_web_action"] == EXPECTED_ACTIONS[key]
            assert EXPECTED_ACTIONS[key] in html
            original = finding["suggested_fix"]
            assert not original.endswith(("...", "…"))
            assert original in html and original in text
            # These downloads retain the complete source correction, rather
            # than replacing it with a web action or a 200-character excerpt.
            assert original in markdown
            assert original in pdf_text
            assert finding["page"] is not None and finding["location_label"]
    assert seen == set(EXPECTED_ACTIONS)


def test_appendix_heading_role_and_unrelated_subtypes() -> None:
    finding = {"rule_id": "P027", "issue_type": "level1_not_all_caps"}
    assert "appendix heading" in short_student_action(
        finding, "Background", details={"line_preview": "APPENDIX A Supporting Material"}
    )
    for rule, issue in EXPECTED_ACTIONS:
        action = "Verify this separate concern."
        assert (
            short_student_action({"rule_id": rule, "issue_type": issue + "_other"}, action)
            == action
        )
    # Capitalization and period checks are separate detector findings.
    assert "final period" not in short_student_action(
        {"rule_id": "P027", "issue_type": "level4_sentence_case_issue"},
        'Check whether to change "1.1.1.1 A Synthetic Heading" to "1.1.1.1 A synthetic heading".',
    )


@pytest.mark.parametrize("later", ["may", "might", "check", "if", "whether", "review"])
def test_later_qualifier_cannot_excuse_confident_opening(later: str) -> None:
    action = f"Reorder these entries. Background {later} need separate review."
    result = short_student_action({"confidence_level": "medium"}, action)
    assert result.startswith("Check whether to reorder these entries.")


def test_incomplete_source_is_not_labelled_full_correction() -> None:
    from jinja2 import Environment, FileSystemLoader

    env = Environment(
        loader=FileSystemLoader(Path(__file__).parents[1] / "src/njit_auditor/templates")
    )
    env.filters["display_rule_id"] = str
    macro = env.get_template("_macros.html").module.finding_explanation
    rendered = macro(
        {"suggested_fix": "Original excerpt...", "student_web_action": "Check it."}, "id"
    )
    assert "source text is incomplete" in rendered
    assert "Full correction:" not in rendered
