"""Synthetic counterexamples and true-positive controls for assessment Stage 2."""

import fitz
import pytest

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.pdf_models import (
    BBox,
    PdfDocument,
    PdfGraphicBlock,
    PdfPage,
    PdfTextBlock,
    PdfTextLine,
    PdfTextSpan,
)
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view
from njit_auditor.rules.pdf_biosketch_bullet_spacing import check_pdf_biosketch_bullet_spacing
from njit_auditor.rules.pdf_figure_table_layout import check_pdf_figure_table_layout
from njit_auditor.rules.pdf_font_compliance import check_pdf_font_compliance


def line(text, y, *, x=108, right=500, size=12, baseline=None, direction=(1.0, 0.0)):
    box = BBox(x0=x, y0=y, x1=right, y1=y + 12)
    span = PdfTextSpan(text=text, bbox=box, size=size, font="Times-Roman", baseline_y=baseline)
    return PdfTextLine(text=text, bbox=box, spans=[span], line_dir=direction, baseline_y=baseline)


def block(lines, *, bottom=None):
    return PdfTextBlock(
        lines=lines,
        text="\n".join(ln.text for ln in lines),
        bbox=BBox(
            x0=min(ln.bbox.x0 for ln in lines),
            x1=max(ln.bbox.x1 for ln in lines),
            y0=min(ln.bbox.y0 for ln in lines),
            y1=bottom or max(ln.bbox.y1 for ln in lines),
        ),
    )


def document(blocks, graphics=()):
    return PdfDocument(
        path="synthetic.pdf",
        pages=[
            PdfPage(
                page_number=1,
                width=612,
                height=792,
                text_blocks=blocks,
                graphic_blocks=list(graphics),
            )
        ],
    )


@pytest.mark.parametrize("bad_bullets", [False, True])
@pytest.mark.parametrize(
    "boundary", ["Presentations and Publications:", "Major:", "Selected Publications:"]
)
def test_education_scope_excludes_later_sections_but_keeps_bad_bullets(bad_bullets, boundary):
    lines = [line("BIOGRAPHICAL SKETCH", 60), line("Undergraduate and Graduate Education:", 100)]
    for y in (140, 270):
        lines += [
            line("•Synthetic degree entry with wrapped text", y, x=126),
            line(
                "Continuation of this education entry only.", y + (30 if bad_bullets else 14), x=144
            ),
            line(
                "Final continuation of this education entry.",
                y + (60 if bad_bullets else 28),
                x=144,
            ),
        ]
    lines += [line(boundary, 390)]
    for y in (420, 550):
        lines += [
            line("Unrelated section prose with sufficient content.", y),
            line("Following unrelated prose with a large line gap.", y + 30),
            line("Final unrelated prose with another large gap.", y + 60),
        ]
    findings = check_pdf_biosketch_bullet_spacing(document([block(lines)]))
    assert len(findings) == (2 if bad_bullets else 0)


def test_separate_bullets_do_not_turn_inter_entry_spacing_into_internal_spacing():
    lines = [line("BIOGRAPHICAL SKETCH", 60), line("Education:", 100)]
    for y in (140, 185, 230):
        lines += [
            line("•A sufficiently long synthetic education item.", y, x=126),
            line("A single-spaced continuation of the same item.", y + 14, x=144),
        ]
    assert check_pdf_biosketch_bullet_spacing(document([block(lines)])) == []


@pytest.mark.parametrize("drift", [-0.5, -0.1, 0, 0.1, 0.5])
@pytest.mark.parametrize("pitch", [16, 32])
def test_real_pdf_bullet_membership_survives_coordinate_jitter(tmp_path, drift, pitch):
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 70), "BIOGRAPHICAL SKETCH", fontsize=14, fontname="Times-Bold")
    page.insert_text((108, 110), "Education:", fontsize=12, fontname="Times-Bold")
    for y in (160, 330):
        for index, text in enumerate(
            (
                "- Generic educational qualification and supporting details.",
                "First ordinary continuation of the same education bullet.",
                "Second ordinary continuation of the same education bullet.",
            )
        ):
            page.insert_text(
                (108 + (drift if index else 0), y + index * pitch),
                text,
                fontsize=12,
                fontname="Times-Roman",
            )
    # Badly spaced publication entries must not be owned by education.
    page.insert_text((108, 420), "Selected Publications:", fontsize=12, fontname="Times-Bold")
    for y in (450, 570):
        for index in range(3):
            text = ("- " if index == 0 else "") + "Synthetic publication entry continuation."
            page.insert_text((108, y + index * 32), text, fontsize=12, fontname="Times-Roman")
    path = tmp_path / "education.pdf"
    doc.save(path)
    doc.close()
    findings = check_pdf_biosketch_bullet_spacing(load_pdf_layout(str(path)))
    assert len(findings) == (2 if pitch == 32 else 0)
    for finding in findings:
        assert finding.details["observed_gap_points"] == "16.0"
        assert finding.details["required_max_gap_points"] == "12.0"
        assert float(finding.details["bbox"].split(",")[3]) < 410


def test_neighboring_markers_keep_bad_entry_distinct_from_good_entries():
    lines = [line("BIOGRAPHICAL SKETCH", 60), line("Education:", 100)]
    for start, pitch in ((150, 14), (210, 30), (300, 14)):
        lines += [
            line("- Generic degree with sufficient educational detail", start),
            line("First continuation of this same educational entry", start + pitch, x=107.9),
            line("Final continuation of this same educational entry", start + 2 * pitch, x=108.1),
        ]
    findings = check_pdf_biosketch_bullet_spacing(document([block(lines)]))
    assert len(findings) == 1
    assert findings[0].details["block_index"] == "1"
    assert float(findings[0].details["bbox"].split(",")[1]) == 210


@pytest.mark.parametrize("x", [72, 510])
def test_outdented_or_separate_column_text_is_not_a_bullet_continuation(x):
    lines = [line("BIOGRAPHICAL SKETCH", 60), line("Education:", 100)]
    for y in (150, 300):
        lines += [
            line("- A single educational entry with supporting detail", y),
            line("Unrelated adjacent text in a distinct column", y + 30, x=x, right=x + 80),
            line("Additional adjacent text in a distinct column", y + 60, x=x, right=x + 80),
        ]
    assert check_pdf_biosketch_bullet_spacing(document([block(lines)])) == []


@pytest.mark.parametrize("shift,expected", [(0, False), (-40, True)])
@pytest.mark.parametrize("ruled", [True, False])
def test_table_border_uses_ink_extent_without_losing_off_center_tables(shift, expected, ruled):
    title = line("Table 1.1 Synthetic Measured Results", 140, right=540)
    rows = [
        line("Material alpha and measured result", 170, x=108 + shift, right=500 + shift),
        line("Material beta and measured result", 195, x=108 + shift, right=490 + shift),
        line("Material gamma and measured result", 220, x=108 + shift, right=480 + shift),
    ]
    # Empty extracted line and block padding extend past the visible bottom rule.
    rows += [line(" ", 242, x=108 + shift, right=500 + shift)]
    doc = document([block([title]), block(rows, bottom=260)])
    if ruled:
        doc.pages[0].horizontal_rules = [
            BBox(x0=108 + shift, x1=540 + shift, y0=y, y1=y + 1) for y in (165, 237)
        ]
    findings = check_pdf_figure_table_layout(doc)
    centered = [f for f in findings if f.details["issue_type"] == "table_body_not_centered"]
    assert bool(centered) == (expected if ruled else True)
    if centered and ruled:
        assert centered[0].details["bbox"] == "68.0,165.0,500.0,238.0"
        assert centered[0].details["center_delta_points"] == "40.0"


def test_empty_block_padding_does_not_let_incomplete_rules_hide_last_real_row():
    title = line("Table 1.1 Synthetic Measured Results", 140)
    rows = [
        line("First row of actual table content", 170),
        line("Last row below an incomplete rule", 240),
    ]
    doc = document([block([title]), block(rows, bottom=280)])
    doc.pages[0].horizontal_rules = [BBox(x0=108, x1=540, y0=y, y1=y + 1) for y in (165, 200)]
    assert any(
        f.details["issue_type"] == "table_body_not_centered"
        for f in check_pdf_figure_table_layout(doc)
    )


@pytest.mark.parametrize("shift", [0, -40])
def test_unruled_table_centering_still_uses_text_geometry(shift):
    title = line("Table 1.1 Synthetic Measured Results", 140)
    rows = [
        line("Ordinary experimental table row content", y, x=108 + shift, right=540 + shift)
        for y in (170, 195, 220)
    ]
    findings = check_pdf_figure_table_layout(document([block([title]), block(rows)]))
    assert [f.details["issue_type"] for f in findings] == (
        ["table_body_not_centered"] if shift else []
    )


@pytest.mark.parametrize("first_rule", [151.5, 149.0])
def test_rule_below_title_baseline_but_inside_font_descent_padding(first_rule):
    title = line("Table 1.1 Synthetic Measured Results", 140, baseline=150)
    rows = [
        line("First actual row of experimental data", 154),
        line("Final actual row of experimental data", 180),
    ]
    doc = document([block([title]), block(rows, bottom=215)])
    doc.pages[0].horizontal_rules = [
        BBox(x0=108, x1=540, y0=y, y1=y + 0.4) for y in (first_rule, 198)
    ]
    findings = check_pdf_figure_table_layout(doc)
    assert bool(findings) == (first_rule < 150)


@pytest.mark.parametrize("body_size", [12, 9, 10])
@pytest.mark.parametrize("kind", ["description", "rotated_label", "graphic"])
def test_nonbody_font_regions_leave_ordinary_body_enforcement_live(body_size, kind):
    prose = [
        line("Ordinary body prose remains independently measurable.", 450 + i * 24, size=body_size)
        for i in range(6)
    ]
    extra = [
        line("Scientific figure content with a different font size.", 180 + i * 14, size=9)
        for i in range(8)
    ]
    graphics = []
    if kind == "description":
        extra.insert(0, line("Figure 1.1 Synthetic scientific figure description", 166, size=9))
    elif kind == "rotated_label":
        for ln in extra:
            ln.line_dir = (0.0, -1.0)
    else:
        graphics = [PdfGraphicBlock(bbox=BBox(x0=100, y0=170, x1=510, y1=310), kind="image")]
        extra.append(line("Figure 1.1 Synthetic scientific figure description", 325, size=9))
    findings = check_pdf_font_compliance(document([block(extra), block(prose)], graphics))
    assert [f.details["issue_type"] for f in findings] == (
        [] if body_size == 12 else ["possible_body_font_size_issue"]
    )
    if findings:
        assert float(findings[0].details["bbox"].split(",")[1]) >= 450


@pytest.mark.parametrize("background", [True, False])
def test_background_or_unowned_graphic_does_not_hide_small_body_text(background):
    prose = [
        line("Ordinary small body prose must remain measurable.", 180 + i * 24, size=9)
        for i in range(6)
    ]
    box = BBox(x0=0, y0=0, x1=612, y1=792) if background else BBox(x0=100, y0=170, x1=510, y1=320)
    blocks = [block(prose)]
    if background:
        blocks.append(block([line("Figure 1.1 Synthetic scientific figure description", 340)]))
    findings = check_pdf_font_compliance(
        document(blocks, [PdfGraphicBlock(bbox=box, kind="image")])
    )
    assert [f.details["issue_type"] for f in findings] == ["possible_body_font_size_issue"]


def test_caption_continuation_stops_at_body_spacing_in_same_block():
    lines = [
        line("Figure 1.1 Synthetic scientific figure description", 160, size=9),
        line("Continuation with legitimate figure description text.", 174, size=9),
    ]
    lines += [
        line("Ordinary small body prose must remain measurable.", 220 + i * 24, size=9)
        for i in range(6)
    ]
    findings = check_pdf_font_compliance(document([block(lines)]))
    assert len(findings) == 1
    assert float(findings[0].details["bbox"].split(",")[1]) == 220


@pytest.mark.parametrize("shift", [-4.0, 4.0, 0.0, None])
def test_script_exclusion_requires_local_size_and_baseline_evidence(shift):
    lines = []
    for i in range(6):
        y = 160 + i * 30
        ln = line("Body prose with a local exponent and further words.", y, baseline=y + 10)
        ln.spans[0].bbox.x1 = 250
        small = PdfTextSpan(
            text="2",
            size=8,
            font="Times-Roman",
            bbox=BBox(x0=250, y0=y + (shift or 0), x1=255, y1=y + 8 + (shift or 0)),
            baseline_y=None if shift is None else y + 10 + shift,
        )
        ln.spans.append(small)
        lines.append(ln)
    findings = check_pdf_font_compliance(document([block(lines)]))
    assert bool(findings) == (shift in (0.0, None))


@pytest.mark.parametrize(
    "issue,noun,other,action",
    [
        ("table_body_not_centered", "table", "figure", "Center the table"),
        ("figure_body_not_centered", "figure", "table", "Center the figure"),
        ("table_caption_not_above_body", "table title", "figure", "above"),
        ("figure_caption_not_below_body", "figure description", "table", "below"),
    ],
)
@pytest.mark.parametrize("number", ["", "1.1", " B.2 "])
def test_r035_actions_only_address_the_affected_object(issue, noun, other, action, number):
    finding = AuditFinding(
        rule_id="P035",
        severity=Severity.WARNING,
        page=1,
        message="Layout review",
        details={
            "issue_type": issue,
            "float_number": number,
            "float_type": issue.split("_")[0],
            "nearby_float_number": "9.9",
        },
    )
    view = build_report_view(
        audit_findings_to_json_dict([finding], {"audit_type": "pdf"})
    ).findings[0]
    for text in (view.polished_comment, view.suggested_fix):
        assert other not in text.lower()
        assert "caption" not in text.lower()
    assert noun in view.polished_comment.lower()
    assert action.lower().replace("the ", "") in view.suggested_fix.lower().replace("the ", "")
    assert "9.9" not in view.suggested_fix
    if number.strip():
        assert f"{issue.split('_')[0].title()} {number.strip()}" in view.suggested_fix
    else:
        assert not any(char.isdigit() for char in view.suggested_fix)
    # Pin complete instructions, including generic fallback when identity is absent.
    expected = {
        "table_body_not_centered": "Center the table within the page margins.",
        "figure_body_not_centered": "Center the figure within the page margins.",
        "table_caption_not_above_body": "Place the table title above the table body.",
        "figure_caption_not_below_body": "Place the figure description below the figure body.",
    }[issue]
    if number.strip():
        target = f"{issue.split('_')[0].title()} {number.strip()}"
        if "not_centered" in issue:
            expected = f"Center {target} within the page margins."
        elif issue.startswith("table"):
            expected = f"Place the table title for {target} above the table body."
        else:
            expected = f"Place the figure description for {target} below the figure body."
    assert view.suggested_fix == expected
