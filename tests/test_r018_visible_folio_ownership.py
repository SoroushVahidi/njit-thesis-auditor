"""Synthetic folio ownership boundaries; no manuscript passages or fixtures."""

import pytest

from njit_auditor.pdf_models import (
    BBox,
    PdfDocument,
    PdfPage,
    PdfTextBlock,
    PdfTextLine,
    PdfTextSpan,
    format_bbox_detail,
)
from njit_auditor.rules.pdf_lot_lof_entry_type import check_pdf_lot_lof_entry_type
from njit_auditor.rules.pdf_toc_alignment import (
    check_pdf_toc_alignment,
    detect_toc_like_pages,
    extract_toc_logical_entry_lines,
)
from njit_auditor.rules.pdf_toc_leader_consistency import check_pdf_toc_leader_consistency
from njit_auditor.toc_list_student_preview import p018_short_suggested_fix


def _line(y, *pieces):
    spans = [
        PdfTextSpan(text=text, bbox=BBox(x0=x0, y0=y, x1=x1, y1=y + 12), size=12)
        for text, x0, x1 in pieces
    ]
    return PdfTextLine(
        spans=spans,
        text=" ".join(s.text for s in spans),
        bbox=BBox(
            x0=min(s.bbox.x0 for s in spans), y0=y, x1=max(s.bbox.x1 for s in spans), y1=y + 12
        ),
    )


def _peer(y, label="2.1", edge=540):
    return _line(y, (f"{label} Synthetic reference ....", 108, 490), ("40", edge - 12, edge))


def _doc(rows, heading="LIST OF FIGURES", page=7):
    lines = [_line(80, (heading, 220, 390)), *rows]
    block = PdfTextBlock(lines=lines, text="", bbox=BBox(x0=100, y0=80, x1=570, y1=750))
    return PdfDocument(
        path="synthetic.pdf",
        pages=[
            PdfPage(
                page_number=page,
                width=612,
                height=792,
                text_blocks=[block],
            )
        ],
    )


def _findings(doc, subtype):
    return [f for f in check_pdf_toc_alignment(doc) if f.details.get("issue_type") == subtype]


def _standalone(rows_count=7, gap=14.3, number_x=149, heading="LIST OF FIGURES"):
    rows = [_peer(110), _peer(134, "2.2"), _peer(158, "2.3")]
    rows.append(_line(190, ("3.1 A synthetic wrapped description", 108, 510)))
    for i in range(1, rows_count):
        text = "additional synthetic description" if i < rows_count - 1 else "final description."
        rows.append(_line(190 + i * 14.3, (text, 149, 510)))
    number_y = rows[-1].bbox.y0 + gap
    number = _line(number_y, ("30", number_x, number_x + 12))
    rows.extend([number, _peer(number_y + 24, "3.2"), _peer(number_y + 48, "3.3")])
    return _doc(rows, heading), number


def test_interior_numerals_cannot_define_the_logical_folio_column():
    rows = [_line(140, ("2.6 A synthetic wrapped description", 108, 510))]
    rows.append(
        _line(
            154,
            ("(B) measured using", 149, 300),
            ("100", 340, 358),
            ("units over repeated trials.", 360, 510),
        )
    )
    for y in [168, 182, 196, 210]:
        rows.append(_line(y, ("additional synthetic continuation", 149, 510)))
    rows.append(_line(224, ("final description . . .", 149, 520), ("16", 528, 540)))
    for i in range(4):
        rows.append(
            _line(
                250 + 24 * i,
                (f"4.{i + 1} Synthetic measurement", 108, 300),
                ("100", 340, 358),
                ("units per interval", 365, 510),
            )
        )
    rows.extend([_peer(360), _peer(384, "2.2"), _peer(408, "2.3")])
    doc = _doc(rows)
    entry = extract_toc_logical_entry_lines(detect_toc_like_pages(doc)[0])[0]
    assert entry.page_number_token == "16"
    assert entry.page_number_right_x == 540
    assert entry.line.bbox.y1 == 236
    assert not any(
        f.details.get("affected_entry_preview", "").startswith("2.6 ")
        for f in _findings(doc, "missing_page_number")
    )


@pytest.mark.parametrize(
    ("rows_count", "gap", "number_x"),
    [
        (3, 24.1, 149),
        (7, 14.3, 149),
        (7, 14.3, 155.4),
        (7, 14.35, 155.5),
    ],
    ids=["short-wrap-blank-line", "long-wrap", "indented-folio", "indented-folio-jitter"],
)
def test_visible_standalone_folio_gets_alignment_advice_and_exact_box(
    rows_count,
    gap,
    number_x,
):
    doc, number = _standalone(rows_count, gap, number_x)
    assert not _findings(doc, "missing_page_number")
    (finding,) = _findings(doc, "misaligned_page_number_column")
    assert finding.page == 7
    assert finding.details["bbox"] == format_bbox_detail(number.bbox)
    assert float(finding.details["worst_delta_pt"]) == pytest.approx(540 - number.bbox.x1, abs=0.1)
    assert finding.details["affected_entry_count"] == "1"
    advice = p018_short_suggested_fix(finding.details["issue_type"])
    assert "Align" in advice and "Add" not in advice


@pytest.mark.parametrize(
    ("page", "y", "edge"),
    [
        (10, 686.5, 561.18),
        (10, 686.6, 561.19),
        (11, 710.1, 561.18),
        (12, 129.6, 561.18),
    ],
)
def test_leaderless_displaced_right_edge_remains_a_column_violation(page, y, edge):
    target = _line(y, ("1.3 Synthetic section title", 124.4, 360), ("20", edge - 12, edge))
    doc = _doc([_peer(180), _peer(204), _peer(228), target], "TABLE OF CONTENTS", page)
    (finding,) = _findings(doc, "misaligned_page_number_column")
    assert finding.page == page
    assert finding.details["bbox"] == format_bbox_detail(target.bbox)
    assert float(finding.details["worst_delta_pt"]) == pytest.approx(edge - 540, abs=0.1)
    assert not _findings(doc, "missing_page_number")


@pytest.mark.parametrize("heading", ["TABLE OF CONTENTS", "LIST OF TABLES", "LIST OF FIGURES"])
def test_wrapped_missing_and_present_adjacent_entries_keep_their_own_numbers(heading):
    doc, number = _standalone(3, heading=heading)
    rows = doc.pages[0].text_blocks[0].lines
    rows.remove(number)
    assert len(_findings(doc, "missing_page_number")) == 1
    assert not _findings(doc, "misaligned_page_number_column")
    rows.insert(-2, number)
    assert not _findings(doc, "missing_page_number")
    assert len(_findings(doc, "misaligned_page_number_column")) == 1


@pytest.mark.parametrize(
    "change",
    [
        "unfinished-title",
        "content-after-number",
        "footer",
        "next-row-number",
        "roman-content",
        "no-peers",
    ],
)
def test_ambiguous_standalone_numeral_is_not_claimed_as_a_folio(change):
    doc, number = _standalone(3)
    rows = doc.pages[0].text_blocks[0].lines
    idx = rows.index(number)
    if change == "unfinished-title":
        rows[idx - 1] = _line(rows[idx - 1].bbox.y0, ("measured over", 149, 350))
    elif change == "content-after-number":
        rows.insert(idx + 1, _line(number.bbox.y0 + 14, ("additional title content", 149, 450)))
    elif change == "footer":
        rows[idx] = _line(740, ("30", 300, 312))
    elif change == "next-row-number":
        rows[idx] = _line(rows[idx + 1].bbox.y0 - 4, ("30", 149, 161))
    elif change == "roman-content":
        rows[idx] = _line(number.bbox.y0, ("I", 149, 155))
    elif change == "no-peers":
        for i in [1, 2, 3, len(rows) - 2, len(rows) - 1]:
            rows[i] = _line(rows[i].bbox.y0, (f"5.{i} Missing peer title", 108, 450))
    assert _findings(doc, "missing_page_number")
    assert not _findings(doc, "misaligned_page_number_column")


def test_r018_standalone_recovery_does_not_change_r055_or_r075_ownership():
    doc, _ = _standalone(3)
    before = [f.model_dump() for f in check_pdf_lot_lof_entry_type(doc)]
    leaders = [f.model_dump() for f in check_pdf_toc_leader_consistency(doc)]
    check_pdf_toc_alignment(doc)
    assert [f.model_dump() for f in check_pdf_lot_lof_entry_type(doc)] == before
    assert [f.model_dump() for f in check_pdf_toc_leader_consistency(doc)] == leaders
    entries = extract_toc_logical_entry_lines(
        detect_toc_like_pages(doc)[0], require_right_edge=True
    )
    assert next(e for e in entries if e.cleaned_text.startswith("3.1")).page_number_token is None


def test_multiple_displaced_folios_keep_distinct_highlight_targets():
    from njit_auditor.highlight_targeting import parse_highlight_bboxes_from_details

    doc, number = _standalone(3)
    rows = doc.pages[0].text_blocks[0].lines
    other = _line(400, ("3.4 Another wrapped description", 108, 510))
    final = _line(414, ("ending with a sentence.", 149, 350))
    second_number = _line(428, ("31", 149, 159))
    rows.extend([other, final, second_number, _peer(452, "3.5")])
    (finding,) = _findings(doc, "misaligned_page_number_column")
    assert finding.details["affected_entry_count"] == "2"
    assert finding.details["bbox"] == format_bbox_detail(second_number.bbox)
    boxes = parse_highlight_bboxes_from_details(finding.details)
    assert len(boxes) == 2
    assert {
        tuple(round(v, 1) for v in row.bbox.model_dump().values())
        for row in [number, second_number]
    } == set(boxes)


def test_standalone_folio_targets_survive_student_pdf_routes(tmp_path, monkeypatch):
    import fitz
    from fastapi.testclient import TestClient

    from njit_auditor import web_app

    source = tmp_path / "synthetic.pdf"
    document, _ = _column_reference_case(5, number_gap=24)
    lines = document.pages[0].text_blocks[0].lines
    with fitz.open() as pdf:
        pdf.new_page(width=612, height=792).insert_text((108, 100), "SYNTHETIC TITLE")
        page = pdf.new_page(width=612, height=792)
        for line in lines:
            for span in line.spans:
                page.insert_text((span.bbox.x0, span.bbox.y0 + 12), span.text, fontsize=12)
        # Independently locate only the visible standalone digits in the PDF.
        expected = [
            fitz.Rect(word[:4])
            for word in page.get_text("words")
            if word[4] in {"30", "31", "32", "33", "34"} and word[0] < 200
        ]
        assert len(expected) == 5
        page.set_rotation(90)
        pdf.save(source)

    monkeypatch.setattr(web_app, "RUNTIME_DIR", tmp_path / "runtime")
    with TestClient(web_app.app) as client:
        response = client.post(
            "/audits",
            files={
                "file": ("synthetic.pdf", source.read_bytes(), "application/pdf"),
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        url = response.headers["location"]
        job = web_app._get_job(url.rsplit("/", 1)[-1])
        assert job is not None and job.state == "complete"
        raw = client.get(url + "/download/json").json()
        findings = [f for f in raw["findings"] if f["rule_id"] == "P018"]
        assert not any(f["details"]["issue_type"] == "missing_page_number" for f in findings)
        (finding,) = [
            f for f in findings if f["details"]["issue_type"] == "misaligned_page_number_column"
        ]
        assert finding["page"] == 2
        assert finding["details"]["affected_entry_count"] == "5"
        (card,) = [
            c
            for c in job.findings
            if c["rule_id"] == "P018" and c.get("issue_type") == "misaligned_page_number_column"
        ]
        assert card["has_highlight"]
        for route, count, target_index in [
            ("/highlighted-page.pdf", 1, 0),
            ("/pdf/highlighted", 2, 1),
        ]:
            highlighted = client.get(
                url + route, params={"page": 2, "finding_id": card["finding_id"]}
            )
            assert highlighted.status_code == 200
            with fitz.open(stream=highlighted.content, filetype="pdf") as result:
                assert len(result) == count
                target = result[target_index]
                assert target.rotation == 90
                annotations = list(target.annots() or [])
                assert len(annotations) == 5
                for box in expected:
                    (annotation,) = [a for a in annotations if a.rect.intersects(box)]
                    assert abs(annotation.rect.y0 - box.y0) < 2
                    assert abs(annotation.rect.y1 - box.y1) < 2
                    assert annotation.rect.x1 < 200
                if count == 2:
                    first_page = result[0]
                    assert not list(first_page.annots() or [])


@pytest.mark.parametrize("preceding_edge", [None, 540, 561.2])
def test_adjacent_missing_present_and_displaced_rows_keep_separate_ownership(preceding_edge):
    doc, number = _standalone(3, gap=24)
    pieces = [("2.4 Independent preceding entry", 108, 450)]
    if preceding_edge is not None:
        pieces.append(("29", preceding_edge - 12, preceding_edge))
    preceding = _line(176, *pieces)
    doc.pages[0].text_blocks[0].lines.insert(4, preceding)
    missing = _findings(doc, "missing_page_number")
    assert len(missing) == (1 if preceding_edge is None else 0)
    if missing:
        assert missing[0].details["bbox"] == format_bbox_detail(preceding.bbox)
    (finding,) = _findings(doc, "misaligned_page_number_column")
    assert finding.details["affected_entry_count"] == ("2" if preceding_edge == 561.2 else "1")
    assert finding.details["bbox"] == format_bbox_detail(number.bbox)


def _column_reference_case(displaced, edge=540, heading="LIST OF FIGURES", number_gap=14):
    rows = [_peer(110, edge=edge), _peer(134, "2.2", edge), _peer(158, "2.3", edge)]
    digits = []
    for i in range(displaced):
        y = 190 + (38 + number_gap) * i
        number = _line(y + 14 + number_gap, (str(30 + i), 149, 161))
        rows.extend(
            [
                _line(y, (f"3.{i + 1} Synthetic wrapped description", 108, 510)),
                _line(y + 14, ("final description.", 149, 350)),
                number,
            ]
        )
        digits.append(number)
    rows.append(_peer(190 + (38 + number_gap) * displaced, "3.9", edge))
    return _doc(rows, heading), digits


@pytest.mark.parametrize("displaced", [1, 2, 4, 5], ids=["single", "minority", "tie", "majority"])
@pytest.mark.parametrize("reverse", [False, True], ids=["forward", "reverse"])
@pytest.mark.parametrize(
    ("heading", "edge"),
    [
        ("LIST OF FIGURES", 540),
        ("LIST OF TABLES", 520),
        ("TABLE OF CONTENTS", 540),
    ],
)
def test_recovered_folios_cannot_redefine_a_reliable_column(displaced, reverse, heading, edge):
    from njit_auditor.highlight_targeting import parse_highlight_bboxes_from_details

    doc, digits = _column_reference_case(displaced, edge, heading)
    if reverse:
        doc.pages[0].text_blocks[0].lines.reverse()
    assert not _findings(doc, "missing_page_number")
    (finding,) = _findings(doc, "misaligned_page_number_column")
    assert finding.page == 7
    assert finding.details["affected_entry_count"] == str(displaced)
    assert finding.details["affected_entry_preview"].startswith("3.1 ")
    assert finding.details["bbox"] == format_bbox_detail(digits[0].bbox)
    assert float(finding.details["worst_delta_pt"]) == edge - 161
    assert set(parse_highlight_bboxes_from_details(finding.details)) == {
        tuple(number.bbox.model_dump().values()) for number in digits
    }
    assert p018_short_suggested_fix(finding.details["issue_type"]) == (
        "Align this entry's page number with the dominant right-hand column on this list page."
    )


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize(
    ("edges", "trusted"),
    [
        ([540, 540], None),  # Too few genuine peers, even with misleading title numerals.
        ([500, 500, 540, 540], None),  # Median lies between equally plausible columns.
        ([500, 500, 500, 540, 540, 540], None),
        ([500, 520, 540], None),  # No supported column at the median.
        ([532, 540, 548], None),  # A diffuse chain is not a compact peer group.
        ([500, 540, 540, 540], 540),  # A genuine majority survives an initial outlier.
        ([540, 539, 541, 561.2], 540),  # Existing tolerance admits small extraction jitter.
    ],
)
def test_recovery_requires_supported_initial_peers(edges, trusted, reverse):
    from njit_auditor.rules import pdf_toc_alignment as rule

    doc, _ = _column_reference_case(1)
    rows = doc.pages[0].text_blocks[0].lines
    rows[:] = [
        rows[0],
        *[
            _line(100 + 24 * i, (f"2.{i + 1} Reference ....", 108, 450), ("40", e - 12, e))
            for i, e in enumerate(edges)
        ],
        _line(300, ("3.1 Synthetic wrapped description", 108, 510)),
        _line(314, ("final description.", 149, 350)),
        _line(328, ("30", 149, 161)),
        _line(352, ("3.9 Actual missing folio", 108, 450)),
    ]
    # Neither internal quantities nor embedded terminal digits establish a measured column.
    for i in range(4):
        rows.append(
            _line(
                400 + 24 * i,
                (f"4.{i + 1} Measurement", 108, 300),
                ("100", 340, 358),
                ("units", 365, 510),
            )
        )
        rows.append(_line(510 + 24 * i, (f"5.{i + 1} Embedded title .... 40", 108, 500)))
    ctx = rule.detect_toc_like_pages(doc)[0]
    entries = rule.extract_toc_logical_entry_lines(ctx)
    if reverse:
        entries.reverse()
    reference = rule._attach_displaced_terminal_folios(entries, rule.collect_toc_visual_rows(ctx))
    assert reference == trusted
    entry = next(e for e in entries if e.cleaned_text.startswith("3.1 "))
    assert entry.page_number_token == ("30" if trusted is not None else None)
    missing = _findings(doc, "missing_page_number")
    assert len(missing) == 1
    assert missing[0].page == 7
    assert missing[0].details["affected_entry_count"] == ("1" if trusted is not None else "2")
    assert (
        missing[0]
        .details["affected_entry_preview"]
        .startswith("3.9 " if trusted is not None else "3.1 ")
    )
    assert "Add" in p018_short_suggested_fix("missing_page_number")
    if trusted is None and len(edges) >= 3 and max(edges) - min(edges) > 20:
        # Conservative recovery does not blanket-suppress ordinary column evidence.
        assert _findings(doc, "misaligned_page_number_column")
