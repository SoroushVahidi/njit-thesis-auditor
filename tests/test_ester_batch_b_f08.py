"""Batch B Ester F08: malformed / non-sequential body figure numbering (P088)."""

from __future__ import annotations

import json

import fitz

from njit_auditor.finding_explanations import build_detailed_explanation
from njit_auditor.issue_type_explanations import (
    explain_issue_type,
    student_facing_issue_label,
)
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.polished_comments import build_polished_comment
from njit_auditor.report_outputs import (
    audit_findings_to_json_dict,
    write_json_report,
    write_markdown_report,
)
from njit_auditor.report_text import write_text_report
from njit_auditor.report_view import build_report_view
from njit_auditor.rules.pdf_captions import check_pdf_captions, detect_caption_lines
from njit_auditor.rules.pdf_figure_number_structure import (
    check_pdf_figure_number_structure,
)
from njit_auditor.rules.pdf_lot_lof_entry_number_ordering import (
    check_pdf_lot_lof_entry_number_ordering,
)
from njit_auditor.rules.pdf_lot_lof_entry_type import check_pdf_lot_lof_entry_type
from njit_auditor.rules.pdf_toc_entry_number_ordering import (
    check_pdf_toc_entry_number_ordering,
)
from njit_auditor.rules.pdf_toc_list_formatting import check_pdf_toc_list_formatting
from njit_auditor.rules.pdf_toc_title_structure import check_pdf_toc_title_structure


def _pdf(tmp_path, pages):
    path = tmp_path / "synthetic.pdf"
    doc = fitz.open()
    for heading, folio, lines in pages:
        page = doc.new_page(width=612, height=792)
        if heading:
            page.insert_text((210, 85), heading, fontsize=12, fontname="Times-Bold")
        if folio:
            page.insert_text((300, 770), folio, fontsize=12)
        for x, y, text, *rest in lines:
            font = rest[0] if rest else "Times-Roman"
            page.insert_text((x, y), text, fontsize=10, fontname=font)
    doc.save(path)
    doc.close()
    return load_pdf_layout(str(path))


def _synthetic_malformed_pages():
    """Generate seven malformed figure labels without document content."""
    return [
        (
            None,
            "59",
            [
                (
                    108,
                    140,
                    "Figure 4.204.1 Synthetic diagram of square boxes and round markers.",
                    "Times-Bold",
                ),
                (
                    108,
                    280,
                    "Figure 4.214.2 Synthetic diagram of square boxes and round markers.",
                    "Times-Bold",
                ),
            ],
        ),
        (
            None,
            "60",
            [
                (
                    108,
                    200,
                    "Figure 4.224.3 Synthetic diagram of square boxes and round markers.",
                    "Times-Bold",
                ),
            ],
        ),
        (
            None,
            "61",
            [
                (
                    108,
                    160,
                    "Figure 4.234.4 Synthetic diagram of square boxes and round markers.",
                    "Times-Bold",
                ),
                (
                    108,
                    320,
                    "Figure 4.244.5 Synthetic diagram of square boxes and round markers.",
                    "Times-Bold",
                ),
            ],
        ),
        (
            None,
            "62",
            [
                (
                    108,
                    160,
                    "Figure 4.254.6 Synthetic diagram of square boxes and round markers.",
                    "Times-Bold",
                ),
                (
                    108,
                    320,
                    "Figure 4.264.7 Synthetic diagram of square boxes and round markers.",
                    "Times-Bold",
                ),
            ],
        ),
    ]


def test_baseline_without_detector_misses_synthetic_malformed_numbers(tmp_path):
    """Original failure: caption parser sees the labels, but no numbering rule fires."""
    doc = _pdf(tmp_path, _synthetic_malformed_pages())
    captions = [
        c for c in detect_caption_lines(doc) if c.caption_type == "figure" and c.context == "body"
    ]
    assert len(captions) == 7
    legacy = check_pdf_captions(doc) + check_pdf_lot_lof_entry_number_ordering(doc)
    assert not any(
        (f.details or {}).get("issue_type")
        in {
            "figure_number_malformed",
            "figure_number_duplicate",
            "figure_number_out_of_order",
        }
        for f in legacy
    )


def test_f08_detects_synthetic_concatenated_figure_numbers(tmp_path):
    doc = _pdf(tmp_path, _synthetic_malformed_pages())
    findings = check_pdf_figure_number_structure(doc)
    malformed = [f for f in findings if f.details["issue_type"] == "figure_number_malformed"]
    assert len(malformed) == 7
    tokens = {f.details["number_token"] for f in malformed}
    assert tokens == {
        "4.204.1",
        "4.214.2",
        "4.224.3",
        "4.234.4",
        "4.244.5",
        "4.254.6",
        "4.264.7",
    }
    assert all(f.details.get("bbox") for f in malformed)
    assert all(f.details.get("triage_tier") == "high" for f in malformed)
    assert all(f.details.get("confidence") == "high" for f in malformed)
    assert all("chapter.sequence" in (f.details.get("suggested_fix") or "") for f in malformed)


def test_f08_well_formed_chapter_sequence_is_silent(tmp_path):
    doc = _pdf(
        tmp_path,
        [
            (
                None,
                "10",
                [
                    (
                        108,
                        140,
                        "Figure 4.1 Synthetic diagram of square boxes and round markers.",
                    ),
                    (
                        108,
                        260,
                        "Figure 4.2 Synthetic diagram of square boxes and round markers.",
                    ),
                    (
                        108,
                        380,
                        "Figure 4.20 Synthetic diagram of square boxes and round markers.",
                    ),
                ],
            )
        ],
    )
    assert check_pdf_figure_number_structure(doc) == []


def test_f08_missing_separator_space_is_not_malformed_number(tmp_path):
    """Glued title text is a spacing issue, not a 3-segment number."""
    doc = _pdf(
        tmp_path,
        [
            (
                None,
                "47",
                [
                    (
                        108,
                        200,
                        "Figure 4.2Synthetic diagram of square boxes and round markers.",
                    ),
                ],
            )
        ],
    )
    findings = check_pdf_figure_number_structure(doc)
    assert [f for f in findings if f.details["issue_type"] == "figure_number_malformed"] == []


def test_f08_adjacent_unrelated_numbers_in_caption_body_do_not_flag(tmp_path):
    doc = _pdf(
        tmp_path,
        [
            (
                None,
                "12",
                [
                    (
                        108,
                        180,
                        "Figure 3.4 Synthetic samples 12.5 and 18.0 in a comparison diagram.",
                    ),
                ],
            )
        ],
    )
    assert check_pdf_figure_number_structure(doc) == []


def test_f08_multiline_caption_preserves_well_formed_number(tmp_path):
    doc = _pdf(
        tmp_path,
        [
            (
                None,
                "15",
                [
                    (
                        108,
                        200,
                        "Figure 2.3 Synthetic diagram of square boxes and round markers.",
                    ),
                    (108, 214, "with a second line in this generated example."),
                ],
            )
        ],
    )
    assert check_pdf_figure_number_structure(doc) == []


def test_f08_list_of_figures_entries_are_not_flagged(tmp_path):
    doc = _pdf(
        tmp_path,
        [
            (
                "LIST OF FIGURES",
                "xvii",
                [
                    (108, 140, "Figure 4.204.1 Synthetic example diagram .... 59"),
                    (108, 165, "Figure 4.214.2 Synthetic example diagram .... 59"),
                ],
            )
        ],
    )
    assert check_pdf_figure_number_structure(doc) == []


def test_f08_in_text_cross_reference_is_not_a_caption(tmp_path):
    doc = _pdf(
        tmp_path,
        [
            (
                None,
                "20",
                [
                    (
                        108,
                        160,
                        "As shown in Figure 4.204.1 the synthetic example has two square boxes.",
                    ),
                    (
                        108,
                        180,
                        "The points cluster near the peak and remain stable afterward.",
                    ),
                ],
            )
        ],
    )
    assert check_pdf_figure_number_structure(doc) == []


def test_f08_panel_letters_are_not_treated_as_extra_segments(tmp_path):
    doc = _pdf(
        tmp_path,
        [
            (
                None,
                "22",
                [
                    (
                        108,
                        160,
                        "Figure 5.1 (a) Square, (b) circle, and (c) triangle panels.",
                    ),
                ],
            )
        ],
    )
    assert check_pdf_figure_number_structure(doc) == []


def test_f08_table_captions_are_out_of_scope(tmp_path):
    doc = _pdf(
        tmp_path,
        [
            (
                None,
                "30",
                [
                    (
                        108,
                        160,
                        "Table 4.204.1 Synthetic diagram of square boxes and round markers.",
                    ),
                ],
            )
        ],
    )
    assert check_pdf_figure_number_structure(doc) == []


def test_f08_duplicate_well_formed_numbers_flagged(tmp_path):
    doc = _pdf(
        tmp_path,
        [
            (
                None,
                "40",
                [
                    (
                        108,
                        140,
                        "Figure 2.1 Synthetic diagram of square boxes and round markers.",
                    ),
                    (
                        108,
                        260,
                        "Figure 2.1 Synthetic diagram of square boxes and round markers.",
                    ),
                ],
            )
        ],
    )
    findings = check_pdf_figure_number_structure(doc)
    dup = [f for f in findings if f.details["issue_type"] == "figure_number_duplicate"]
    assert len(dup) == 1
    assert dup[0].details["number_token"] == "2.1"


def test_f08_out_of_order_well_formed_numbers_flagged(tmp_path):
    doc = _pdf(
        tmp_path,
        [
            (
                None,
                "41",
                [
                    (
                        108,
                        140,
                        "Figure 3.2 Synthetic diagram of square boxes and round markers.",
                    ),
                    (
                        108,
                        260,
                        "Figure 3.1 Synthetic diagram of square boxes and round markers.",
                    ),
                ],
            )
        ],
    )
    findings = check_pdf_figure_number_structure(doc)
    oo = [f for f in findings if f.details["issue_type"] == "figure_number_out_of_order"]
    assert len(oo) == 1
    assert oo[0].details["number_token"] == "3.1"


def test_f08_chapter_reset_is_not_out_of_order(tmp_path):
    doc = _pdf(
        tmp_path,
        [
            (
                None,
                "50",
                [
                    (
                        108,
                        140,
                        "Figure 4.26 Synthetic diagram of square boxes and round markers.",
                    ),
                    (
                        108,
                        260,
                        "Figure 5.1 Synthetic diagram of square boxes and round markers.",
                    ),
                ],
            )
        ],
    )
    assert check_pdf_figure_number_structure(doc) == []


def test_f08_hyphen_separated_three_segment_number_flagged(tmp_path):
    doc = _pdf(
        tmp_path,
        [
            (
                None,
                "55",
                [
                    (
                        108,
                        180,
                        "Figure 4-20-1 Synthetic diagram of square boxes and round markers.",
                    ),
                ],
            )
        ],
    )
    findings = check_pdf_figure_number_structure(doc)
    malformed = [f for f in findings if f.details["issue_type"] == "figure_number_malformed"]
    assert len(malformed) == 1
    assert malformed[0].details["number_token"] == "4-20-1"


def test_f08_preserves_unrelated_r018_r024_r055_r060_and_batch_a(tmp_path):
    rows = [
        (138, 140, "5.4 Methods for the Study .... 10"),
        (170, 165, "5.4.1 Initial calibration procedure .... 11"),
        (170, 190, "5.42 Further calibration procedure .... 12"),
        (138, 215, "5.5 Results of the Study .... 13"),
    ]
    toc = _pdf(tmp_path, [("TABLE OF CONTENTS", "vii", rows)])
    structural = check_pdf_toc_entry_number_ordering(toc)
    case = check_pdf_toc_list_formatting(toc)
    assert structural and structural[0].details["issue_type"] == ("toc_subsection_number_ambiguous")
    assert not case
    assert check_pdf_figure_number_structure(toc) == []

    lot = _pdf(
        tmp_path,
        [
            (
                "LIST OF TABLES",
                "xii",
                [(108, 140, "1.1 Summary of measured results .... 12")],
            )
        ],
    )
    r055 = check_pdf_lot_lof_entry_type(lot)
    assert any(f.details.get("issue_type") == "lot_entry_missing_table_prefix" for f in r055)
    assert check_pdf_figure_number_structure(lot) == []

    # Batch A still silent on ordinary TOC without Abstract/repeats here.
    assert check_pdf_toc_title_structure(toc) == []


def test_student_facing_explanations_and_exports(tmp_path):
    doc = _pdf(tmp_path, _synthetic_malformed_pages())
    findings = check_pdf_figure_number_structure(doc)
    assert findings
    for finding in findings:
        issue = finding.details["issue_type"]
        assert student_facing_issue_label("P088", issue)
        explanation = build_detailed_explanation(
            rule_id="P088",
            issue_type=issue,
            details=finding.details,
            page=finding.page,
        )
        assert explanation
        assert "malformed" in explanation.lower() or "number" in explanation.lower()
        comment = build_polished_comment(
            rule_id="P088",
            issue_type=issue,
            page=finding.page,
            details=finding.details,
        )
        assert comment
        type_text = explain_issue_type(
            rule_id="P088",
            issue_type=issue,
            details=finding.details,
        )
        assert type_text

    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    assert any(f.rule_id == "P088" for f in view.findings)

    metadata = {"audit_type": "pdf"}
    json_path = tmp_path / "batch_b.json"
    text_path = tmp_path / "batch_b.txt"
    md_path = tmp_path / "batch_b.md"
    write_json_report(findings, metadata, json_path)
    write_text_report(findings, metadata, text_path)
    write_markdown_report(findings, metadata, md_path)
    exported = json.loads(json_path.read_text(encoding="utf-8"))
    assert any(item["rule_id"] == "P088" for item in exported["findings"])
    text = text_path.read_text(encoding="utf-8").lower()
    md = md_path.read_text(encoding="utf-8").lower()
    assert "4.204.1" in text or "malformed" in text
    assert "r088" in text and "r088" in md
