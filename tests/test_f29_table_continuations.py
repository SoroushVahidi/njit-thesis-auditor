"""Invented ruled tables exercise recognition without detector integration."""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.pdf_table_continuations import recognize_table_continuations
from njit_auditor.rules.pdf_captions import detect_caption_lines


def make_table_pdf(
    tmp_path: Path, *, marked: bool = False, notes_only: bool = True,
    change: str = "", paint: str = "stroke", source: bool = False,
) -> Path:
    path = tmp_path / "invented-table.pdf"
    with fitz.open() as pdf:
        for page_index in range(2):
            page = pdf.new_page(width=612, height=792)
            top = 120 if page_index == 0 else (100 if marked else 72)
            bottom = 720 if page_index == 0 else top + (82 if notes_only else 130)
            if page_index and change == "wrapped_notes":
                bottom += 18
            if page_index == 0:
                page.insert_text((108, 90), "Table 2.1 Invented Measurements.",
                                 fontsize=12, fontname="tiro")
            elif marked:
                label = "Table 2.1 (Continued)"
                if change in {
                    "wrong_number", "bare", "malformed", "new_table", "same_number", "prose_label",
                }:
                    label = {
                        "wrong_number": "Table 2.2 (Continued)",
                        "bare": "Table 2.1 continued",
                        "malformed": "Table 2.1 (continued",
                        "new_table": "Table 2.2 Independent Measurements",
                        "same_number": "Table 2.1 Independent Measurements",
                        "prose_label": "Table 2.1 continued to show an ordinary response.",
                    }[change]
                page.insert_text((108, 82), label, fontsize=12, fontname="tiro")
            offset = 20 if page_index and change == "shifted" else 0
            edges = [108 + offset, 252 + offset, 396 + offset, 540 + offset]
            separators = [top, top + 40, bottom]
            if page_index == 0:
                separators.insert(2, 675)
            if page_index and change == "single_rule":
                separators = [top]
            if page_index and change == "no_rules":
                separators = []
            color = (1, 1, 1) if page_index and change == "white" else (0, 0, 0)
            opacity = 0 if page_index and change == "invisible" else 1
            for y in separators:
                if paint == "filled":
                    for x0, x1 in zip(edges, edges[1:]):
                        page.draw_rect(fitz.Rect(x0, y, x1, y + 0.5), color=None,
                                       fill=color, fill_opacity=opacity)
                else:
                    page.draw_line((edges[0], y), (edges[-1], y), color=color,
                                   stroke_opacity=opacity)
            for x in edges:
                page.draw_line((x, top), (x, bottom), color=color, stroke_opacity=opacity)
            headings = ["Synthetic group", "Observed quantity", "Reference quantity"]
            if page_index and change == "schema":
                headings[1] = "Unrelated quantity"
            for x, text in zip(edges, headings):
                page.insert_text((x + 5, top + 20), text,
                                 fontname="tiro" if change == "chart" else "tibo", fontsize=10)
                if change == "wrapped_headers":
                    page.insert_text((x + 5, top + 32), "Synthetic units",
                                     fontname="tibo", fontsize=10)
            if page_index == 0 or not notes_only:
                for x, text in zip(edges, ["6 synthetic trials" if change == "numeric_cell"
                                          else "Trial alpha", "17", "23"]):
                    page.insert_text((x + 5, top + 65), text, fontsize=10, fontname="tiro")
            first_y = 695 if page_index == 0 else top + (55 if notes_only else 95)
            letters = ["a", "b"] if page_index == 0 else ["c", "d"]
            if page_index and change == "unrelated_notes":
                letters = ["a", "b"]
            if page_index and change == "nonconsecutive_notes":
                letters = ["c", "f"]
            for k, letter in enumerate(letters if change != "empty" else []):
                text = f"{letter}. Invented calibration note belonging to these synthetic readings."
                if page_index and change == "prose_in_grid":
                    text = "Ordinary prose with punctuation is not a table continuation."
                if page_index and change == "wrapped_notes" and k == 0:
                    text += "\nA wrapped invented sentence belongs to the same note."
                extra_y = 12 if page_index and change == "wrapped_notes" and k else 0
                page.insert_text((edges[0] + 5, first_y + k * 12 + extra_y), text,
                                 fontsize=9, fontname="tiro")
            if page_index and source:
                page.insert_text((edges[0] + 5, bottom - 4), "Source: Invented archive.",
                                 fontsize=8, fontname="tiro")
            if page_index:
                page.insert_text((108, bottom + 30), "2.2 Following section",
                                 fontsize=12, fontname="tibo")
                page.insert_text((144, bottom + 60), "Ordinary body prose resumes here.",
                                 fontsize=12, fontname="tiro")
            page.insert_text((300, 750), str(20 + page_index), fontsize=12, fontname="tiro")
        pdf.save(path)
    return path


@pytest.mark.parametrize("marked,notes_only", [(False, True), (True, True), (True, False)])
@pytest.mark.parametrize("paint", ["stroke", "filled"])
def test_recognizes_page_tagged_table_without_mutation(
    tmp_path: Path, marked: bool, notes_only: bool, paint: str,
) -> None:
    path = make_table_pdf(tmp_path, marked=marked, notes_only=notes_only, paint=paint)
    doc = load_pdf_layout(str(path))
    before = doc.model_dump()
    captions = [vars(c).copy() for c in detect_caption_lines(doc)]
    original = path.read_bytes()
    (table,) = recognize_table_continuations(doc)
    assert table.number == "2.1" and table.anchor_page == 1
    assert table.association == ("marked" if marked else "notes")
    first, last = table.fragments
    assert [(f.page_number, f.document_page_label) for f in table.fragments] == [
        (1, "20"), (2, "21"),
    ]
    assert len(last.horizontal_rules) == 3
    assert first.column_edges == last.column_edges
    assert {p.role for p in first.parts} == {"title", "header", "cell", "note"}
    assert ("continuation_identifier" in {p.role for p in last.parts}) == marked
    assert ("cell" in {p.role for p in last.parts}) != notes_only
    assert all(p.page_number == f.page_number for f in table.fragments for p in f.parts)
    assert not any("Following section" in p.text or "Ordinary body" in p.text for p in last.parts)
    assert first.bbox[3] >= 700 and last.bbox[3] < 300
    assert not any("(Continued)" in p.text for p in first.parts)
    assert doc.model_dump() == before
    assert [vars(c) for c in detect_caption_lines(doc)] == captions
    assert path.read_bytes() == original
    if not marked:
        assert doc.pages[1].horizontal_rules == []  # selective extraction is sidecar-only
    with pytest.raises(AttributeError):
        table.number = "9.9"  # type: ignore[misc]


@pytest.mark.parametrize("change", [
    "schema", "shifted", "single_rule", "no_rules", "white", "invisible",
    "unrelated_notes", "nonconsecutive_notes", "prose_in_grid", "chart", "empty",
])
def test_unlabelled_ambiguity_does_not_associate(tmp_path: Path, change: str) -> None:
    path = make_table_pdf(tmp_path, change=change)
    assert recognize_table_continuations(load_pdf_layout(str(path))) == ()


@pytest.mark.parametrize("change", [
    "wrong_number", "bare", "malformed", "new_table", "same_number", "prose_label",
])
def test_marker_cannot_override_identity_or_structure(tmp_path: Path, change: str) -> None:
    path = make_table_pdf(tmp_path, marked=True, change=change)
    assert recognize_table_continuations(load_pdf_layout(str(path))) == ()


def test_unlabelled_data_rows_with_same_schema_are_insufficient(tmp_path: Path) -> None:
    path = make_table_pdf(tmp_path, notes_only=False)
    assert recognize_table_continuations(load_pdf_layout(str(path))) == ()


def test_sources_are_separate_from_notes_and_title(tmp_path: Path) -> None:
    path = make_table_pdf(tmp_path, marked=True, source=True)
    (table,) = recognize_table_continuations(load_pdf_layout(str(path)))
    assert any(p.role == "source" and p.text.startswith("Source:")
               for p in table.fragments[1].parts)
    assert all("Source:" not in p.text for p in table.fragments[0].parts)


@pytest.mark.parametrize("change", [
    "nonadjacent", "original_gap", "rotation", "vertical", "content_rotation",
    "landscape", "font", "duplicate_page", "empty_page", "last_page", "three_pages",
])
def test_unsupported_page_or_text_geometry_abstains(tmp_path: Path, change: str) -> None:
    path = make_table_pdf(tmp_path)
    doc = load_pdf_layout(str(path))
    if change == "nonadjacent":
        doc.pages[1].page_number = 3
    elif change == "original_gap":
        doc.pages[1].original_page_number = 3
    elif change == "rotation":
        doc.pages[1].page_rotation = 90
    elif change == "landscape":
        doc.pages[1].is_visually_landscape = True
    elif change == "duplicate_page":
        doc.pages.append(doc.pages[1].model_copy(deep=True))
    elif change == "last_page":
        doc.pages.pop()
    elif change == "empty_page":
        doc.pages[1].text_blocks.clear()
    elif change == "three_pages":
        # A middle fragment reaches another boundary; no pretend logical end.
        for block in doc.pages[1].text_blocks:
            for line in block.lines:
                if line.text.startswith("c."):
                    line.bbox.y0 = 704
                    line.bbox.y1 = 716
    else:
        for block in doc.pages[1].text_blocks:
            for line in block.lines:
                if change == "vertical":
                    line.wmode = 1
                elif change == "content_rotation":
                    line.line_dir = (-1, 0)
                elif change == "font":
                    for span in line.spans:
                        span.font = "Courier-Bold"
    assert recognize_table_continuations(doc) == ()


def test_opt_in_recognition_preserves_detector_findings(tmp_path: Path) -> None:
    from njit_auditor.rules.pdf_body_spacing import check_pdf_body_spacing
    from njit_auditor.rules.pdf_captions import check_pdf_captions
    from njit_auditor.rules.pdf_figure_number_structure import check_pdf_figure_number_structure
    from njit_auditor.rules.pdf_figure_table_layout import check_pdf_figure_table_layout
    from njit_auditor.rules.pdf_font_compliance import check_pdf_font_compliance
    from njit_auditor.rules.pdf_title_capitalization import check_pdf_title_capitalization

    path = make_table_pdf(tmp_path)
    doc = load_pdf_layout(str(path))
    checks = [check_pdf_captions, check_pdf_body_spacing, check_pdf_figure_table_layout,
              check_pdf_font_compliance, check_pdf_title_capitalization,
              check_pdf_figure_number_structure]
    before = [[f.model_dump() for f in check(doc)] for check in checks]
    assert recognize_table_continuations(doc)
    assert [[f.model_dump() for f in check(doc)] for check in checks] == before


def test_below_border_source_stops_before_body_prose(tmp_path: Path) -> None:
    path = make_table_pdf(tmp_path, marked=True)
    changed = tmp_path / "with-source.pdf"
    with fitz.open(path) as pdf:
        # The final table rule is y182; heading/prose below are separate blocks.
        pdf[1].insert_text((113, 199), "Source: A fictional archive.",
                           fontsize=8, fontname="tiro")
        pdf.save(changed)
    (table,) = recognize_table_continuations(load_pdf_layout(str(changed)))
    sources = [part for part in table.fragments[1].parts if part.role == "source"]
    assert len(sources) == 1 and sources[0].bbox[1] > table.fragments[1].bbox[3]
    assert not any("Ordinary body" in part.text for part in table.fragments[1].parts)


@pytest.mark.parametrize("page_index,y", [(0, 737), (1, 65)])
def test_intervening_prose_breaks_ownership(tmp_path: Path, page_index: int, y: int) -> None:
    path = make_table_pdf(tmp_path)
    changed = tmp_path / "intervening.pdf"
    with fitz.open(path) as pdf:
        pdf[page_index].insert_text((108, y), "An unrelated body paragraph interrupts continuity.",
                                    fontsize=10, fontname="tiro")
        pdf.save(changed)
    assert recognize_table_continuations(load_pdf_layout(str(changed))) == ()


def test_next_page_vectors_are_not_read_without_a_bottom_table(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import njit_auditor.pdf_table_continuations as module

    path = make_table_pdf(tmp_path)
    seen = []
    extract = module._horizontal_rule_bboxes

    def record(page: fitz.Page) -> list:
        seen.append(page.number)
        return extract(page)

    # An anchor page whose table no longer reaches the bottom is ineligible.
    shortened = tmp_path / "short.pdf"
    with fitz.open(path) as source, fitz.open() as pdf:
        for index in range(2):
            page = pdf.new_page(width=612, height=792)
            page.show_pdf_page(fitz.Rect(0, 0, 612, 600), source, index, keep_proportion=False)
        pdf.save(shortened)
    doc = load_pdf_layout(str(shortened))
    monkeypatch.setattr(module, "_horizontal_rule_bboxes", record)
    assert recognize_table_continuations(doc) == ()
    assert seen == [0]


def test_finding_ids_and_highlight_pages_are_preserved(tmp_path: Path) -> None:
    from njit_auditor.highlight_targeting import parse_highlight_bboxes_from_details
    from njit_auditor.pdf_highlight import HighlightBox, build_highlighted_pdf
    from njit_auditor.report_outputs import audit_findings_to_json_dict
    from njit_auditor.report_view import build_report_view
    from njit_auditor.rules.pdf_captions import check_pdf_captions

    path = make_table_pdf(tmp_path)
    doc = load_pdf_layout(str(path))
    findings = check_pdf_captions(doc)
    before = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    before_view = build_report_view(before)
    assert any(f.rule_id == "P017" and f.page == 1 for f in findings)
    assert recognize_table_continuations(doc)
    after = audit_findings_to_json_dict(check_pdf_captions(doc), {"audit_type": "pdf"})
    assert before["findings"] == after["findings"]
    assert before_view.findings == build_report_view(after).findings
    rectangles = []
    for index, output in enumerate((before, after)):
        marked = tmp_path / f"highlighted-{index}.pdf"
        boxes = {f["page"]: [HighlightBox.from_tuple(box) for box in
                              parse_highlight_bboxes_from_details(f["details"])]
                 for f in output["findings"]}
        build_highlighted_pdf(path, marked, boxes)
        with fitz.open(marked) as pdf:
            assert list(pdf[0].annots() or [])
            assert not list(pdf[1].annots() or [])
            rectangles.append([tuple(a.rect) for a in pdf[0].annots() or []])
    assert rectangles[0] == rectangles[1]


def test_physical_page_numbers_are_not_subset_indices(tmp_path: Path) -> None:
    path = make_table_pdf(tmp_path)
    doc = load_pdf_layout(str(path))
    for page in doc.pages:
        page.page_number += 106
        page.original_page_number += 106
    (table,) = recognize_table_continuations(doc)
    assert table.anchor_page == 107
    assert [fragment.page_number for fragment in table.fragments] == [107, 108]
    assert all(part.page_number == fragment.page_number
               for fragment in table.fragments for part in fragment.parts)
    assert [fragment.document_page_label for fragment in table.fragments] == ["20", "21"]


@pytest.mark.parametrize("change", ["border", "edge_overlap", "disjoint", "missing_header"])
def test_non_table_vector_evidence_cannot_own_continuation(tmp_path: Path, change: str) -> None:
    path = make_table_pdf(tmp_path)
    changed = tmp_path / "non-table.pdf"
    with fitz.open(path) as original, fitz.open() as pdf:
        pdf.insert_pdf(original, from_page=0, to_page=0)
        page = pdf.new_page(width=612, height=792)
        if change == "border":
            page.draw_rect(fitz.Rect(20, 20, 592, 772))
        elif change == "edge_overlap":
            for y in (72, 112, 160):
                page.draw_line((0, y), (109, y))
        elif change == "disjoint":
            for y in (72, 112, 160):
                page.draw_line((108, y), (180, y))
                page.draw_line((470, y), (540, y))
        elif change == "missing_header":
            for y in (72, 112, 160):
                page.draw_line((108, y), (540, y))
            for x in (108, 252, 396, 540):
                page.draw_line((x, 72), (x, 160))
        page.insert_text((113, 130), "c. An invented note does not establish table ownership.",
                         fontsize=9, fontname="tiro")
        pdf.save(changed)
    assert recognize_table_continuations(load_pdf_layout(str(changed))) == ()


def test_source_ends_an_unlabelled_first_table(tmp_path: Path) -> None:
    path = make_table_pdf(tmp_path)
    changed = tmp_path / "finished-table.pdf"
    with fitz.open(path) as pdf:
        pdf[0].insert_text((113, 733), "Source: A completed fictional table.",
                           fontsize=8, fontname="tiro")
        pdf.save(changed)
    assert recognize_table_continuations(load_pdf_layout(str(changed))) == ()


def test_real_three_page_chain_is_outside_scope(tmp_path: Path) -> None:
    path = make_table_pdf(tmp_path, marked=True)
    changed = tmp_path / "chain.pdf"
    with fitz.open(path) as original, fitz.open() as pdf:
        pdf.insert_pdf(original, from_page=0, to_page=0)
        pdf.insert_pdf(original, from_page=0, to_page=0)
        pdf.insert_pdf(original, from_page=1, to_page=1)
        # Remove the second original title and replace it with a continued marker.
        page = pdf[1]
        page.add_redact_annot(fitz.Rect(100, 65, 540, 100))
        page.apply_redactions()
        page.insert_text((108, 90), "Table 2.1 (Continued)", fontsize=12, fontname="tiro")
        pdf.save(changed)
    assert recognize_table_continuations(load_pdf_layout(str(changed))) == ()


@pytest.mark.parametrize("change", ["wrapped_headers", "wrapped_notes", "numeric_cell"])
def test_wrapped_structure_and_numeric_cells_are_not_prose(tmp_path: Path, change: str) -> None:
    path = make_table_pdf(tmp_path, change=change)
    (table,) = recognize_table_continuations(load_pdf_layout(str(path)))
    if change == "wrapped_headers":
        assert all(sum(p.role == "header" for p in f.parts) == 6 for f in table.fragments)
    elif change == "wrapped_notes":
        assert sum(p.role == "note" for p in table.fragments[1].parts) == 3
    else:
        assert any(p.role == "cell" and p.text.startswith("6 synthetic")
                   for p in table.fragments[0].parts)


def test_source_block_font_change_stops_before_ordinary_prose(tmp_path: Path) -> None:
    path = make_table_pdf(tmp_path, marked=True)
    changed = tmp_path / "source-and-prose.pdf"
    with fitz.open(path) as pdf:
        page = pdf[1]
        page.add_redact_annot(fitz.Rect(100, 185, 545, 730))
        page.apply_redactions()
        page.insert_text((113, 199), "Source: A fictional archive.",
                         fontsize=8, fontname="tiro")
        page.insert_text((113, 211), "Ordinary body prose resumes with a different font size.",
                         fontsize=12, fontname="tiro")
        pdf.save(changed)
    (table,) = recognize_table_continuations(load_pdf_layout(str(changed)))
    assert any(part.role == "source" for part in table.fragments[1].parts)
    assert not any("Ordinary body" in part.text for part in table.fragments[1].parts)
