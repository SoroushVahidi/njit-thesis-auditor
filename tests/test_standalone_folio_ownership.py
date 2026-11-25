"""Geometry controls for destination folios in logical list entries."""

import pytest

from njit_auditor.p018_guidance import P018_MISSING_PAGE_NUMBER_FIX
from njit_auditor.pdf_models import (
    BBox,
    PdfDocument,
    PdfPage,
    PdfTextBlock,
    PdfTextLine,
    PdfTextSpan,
    format_bbox_detail,
)
from njit_auditor.rules.pdf_toc_alignment import (
    check_pdf_toc_alignment,
    detect_toc_like_pages,
    extract_toc_logical_entry_lines,
)
from njit_auditor.toc_list_student_preview import p018_short_suggested_fix


def _line(y: float, *pieces: tuple[str, float, float]) -> PdfTextLine:
    spans = [
        PdfTextSpan(text=text, bbox=BBox(x0=x0, y0=y, x1=x1, y1=y + 12), size=12)
        for text, x0, x1 in pieces
    ]
    return PdfTextLine(
        text=" ".join(span.text for span in spans),
        spans=spans,
        bbox=BBox(x0=spans[0].bbox.x0, y0=y, x1=spans[-1].bbox.x1, y1=y + 12),
    )


def _doc(rows: list[PdfTextLine], heading: str = "LIST OF FIGURES") -> PdfDocument:
    header = _line(80, (heading, 190, 350))
    return PdfDocument(
        path="synthetic.pdf",
        pages=[
            PdfPage(
                page_number=12,
                width=612,
                height=792,
                text_blocks=[
                    PdfTextBlock(lines=[row], bbox=row.bbox, text=row.text)
                    for row in [header, *rows]
                ],
            )
        ],
    )


@pytest.mark.parametrize(
    ("heading", "second_prefix", "third_prefix"),
    [
        ("LIST OF FIGURES", "2.2", "Figure"),
        ("LIST OF FIGURES", "II.2", "Figure"),
        ("LIST OF FIGURES", "Figure 2.2", "Figure"),
        ("LIST OF FIGURES", "Table 2.2", "Figure"),
        ("LIST OF TABLES", "2.2", "Table"),
        ("LIST OF TABLES", "Figure 2.2", "Table"),
        ("TABLE OF CONTENTS", "A.2", "Appendix"),
    ],
)
def test_indented_new_entry_owns_its_folio(heading, second_prefix, third_prefix):
    document = _doc(
        [
            _line(140, ("2.1 First synthetic item with no folio", 108, 510)),
            _line(156, (f"{second_prefix} Second synthetic item with folio 9", 149, 540)),
            _line(185, (f"{third_prefix} 2.3 Third synthetic item 10", 108, 540)),
        ],
        heading,
    )
    (context,) = detect_toc_like_pages(document)
    for options in ({}, {"require_right_edge": True}, {"recover_displaced_leader_folio": True}):
        entries = extract_toc_logical_entry_lines(context, **options)
        assert [(entry.page_number_token, entry.line.bbox.y0) for entry in entries] == [
            (None, 140),
            ("9", 156),
            ("10", 185),
        ]
        assert entries[1].page_number_line is not None
        assert entries[1].page_number_line.bbox.y0 == 156


def test_tied_folio_cannot_be_claimed_by_either_entry():
    doc = _doc(
        [
            _line(140, ("Figure 2.1 First entry", 108, 340)),
            _line(148, ("9", 530, 540)),
            _line(156, ("Figure 2.2 Second entry", 140, 350)),
            _line(180, ("Figure 2.3 Third entry ....", 108, 510), ("10", 528, 540)),
        ]
    )
    (context,) = detect_toc_like_pages(doc)
    assert [e.page_number_token for e in extract_toc_logical_entry_lines(context)] == [
        None,
        None,
        "10",
    ]


def _peer(y: float, index: int, edge: float = 540) -> PdfTextLine:
    return _line(y, (f"2.{index} Reference entry ....", 108, 450), ("19", edge - 12, edge))


def _wrapped_rows(token: str = "30") -> list[PdfTextLine]:
    return [
        _peer(115, 1),
        _peer(139, 2),
        _peer(163, 3),
        _line(195, ("3.1 A wrapped synthetic description", 108, 510)),
        _line(209, ("final description.", 149, 500)),
        _line(223, (token, 149, 164)),
        _peer(249, 4),
    ]


@pytest.mark.parametrize("offset", [0, 2, 5])
def test_aligned_standalone_block_keeps_ordinary_ownership(offset):
    doc = _doc(
        [
            _peer(115, 1),
            _peer(139, 2),
            _peer(163, 3),
            _line(195, ("Figure 3.1 Independent title", 108, 450)),
            _line(195 + offset, ("xii", 528, 540)),
            _peer(229, 4),
        ]
    )
    (context,) = detect_toc_like_pages(doc)
    assert [entry.page_number_token for entry in extract_toc_logical_entry_lines(context)] == [
        "19",
        "19",
        "19",
        "xii",
        "19",
    ]
    assert not _p018(doc, "missing_page_number")
    assert not _p018(doc, "misaligned_page_number_column")


def _p018(doc: PdfDocument, issue: str):
    return [f for f in check_pdf_toc_alignment(doc) if f.details["issue_type"] == issue]


@pytest.mark.parametrize("token", ["30", "31", "xiv"])
def test_displaced_terminal_folio_gets_alignment_advice_and_exact_geometry(token):
    rows = _wrapped_rows(token)
    doc = _doc(rows)
    assert not _p018(doc, "missing_page_number")
    (warning,) = _p018(doc, "misaligned_page_number_column")
    assert warning.page == 12
    assert warning.details["destination_folio"] == token
    assert warning.details["affected_entry_count"] == "1"
    assert warning.details["bbox"] == format_bbox_detail(rows[-2].bbox)
    assert p018_short_suggested_fix(warning.details["issue_type"]).startswith("Align")


@pytest.mark.parametrize(
    "scenario",
    [
        "footer",
        "roman_letter",
        "invalid_roman",
        "notes_column",
        "two_numbers",
        "unfinished",
        "later_entry_baseline",
        "intervening_note",
        "weak_peers",
    ],
)
def test_ambiguous_displaced_numerals_leave_missing_finding(scenario):
    rows = _wrapped_rows()
    if scenario == "footer":
        rows[-2] = _line(740, ("30", 149, 164))
    elif scenario == "roman_letter":
        rows[-2] = _line(223, ("I", 149, 164))
    elif scenario == "invalid_roman":
        rows[-2] = _line(223, ("VX", 149, 164))
    elif scenario == "notes_column":
        rows[-2] = _line(223, ("30", 170, 185))
    elif scenario == "two_numbers":
        rows.insert(-1, _line(237, ("31", 149, 164)))
    elif scenario == "unfinished":
        rows[-3] = _line(209, ("final description continues", 149, 500))
    elif scenario == "later_entry_baseline":
        rows[-2] = _line(244, ("30", 149, 164))
    elif scenario == "intervening_note":
        rows.insert(-1, _line(237, ("Unidentified text", 149, 230)))
    else:
        rows = rows[2:]
        rows[-1] = _line(249, ("Figure 3.2 Next title", 108, 450))
    doc = _doc(rows)
    (warning,) = _p018(doc, "missing_page_number")
    assert warning.details["affected_entry_preview"].startswith("3.1")
    assert (
        p018_short_suggested_fix(warning.details["issue_type"]) == P018_MISSING_PAGE_NUMBER_FIX
    )
    assert not _p018(doc, "misaligned_page_number_column")


def test_multiple_displaced_folios_do_not_redefine_peer_column():
    rows = [_peer(115, 1), _peer(139, 2), _peer(163, 3)]
    digits = []
    for i in range(5):
        y = 194 + i * 56
        digits.append(_line(y + 28, (str(i + 26), 149, 164)))
        rows.extend(
            [
                _line(y, (f"3.{i + 1} Synthetic wrapped description", 108, 510)),
                _line(y + 14, ("final text.", 149, 500)),
                digits[-1],
            ]
        )
    rows.append(_peer(470, 4))
    for ordered in (rows, list(reversed(rows))):
        doc = _doc(ordered)
        assert not _p018(doc, "missing_page_number")
        (warning,) = _p018(doc, "misaligned_page_number_column")
        assert warning.details["worst_delta_pt"] == "376.0"
        assert warning.details["highlight_bboxes"].split(" | ") == [
            format_bbox_detail(digit.bbox) for digit in digits
        ]


def test_aligned_final_row_folio_keeps_same_line_provenance():
    doc = _doc(
        [
            *_wrapped_rows()[:4],
            _line(209, ("final description.", 149, 500), ("30", 528, 540)),
            _peer(249, 4),
        ]
    )
    (context,) = detect_toc_like_pages(doc)
    entry = extract_toc_logical_entry_lines(context)[3]
    assert entry.is_wrapped
    assert entry.page_number_token == "30"
    assert entry.page_number_line is not None
    assert entry.page_number_line.bbox.y0 == 209
    assert not _p018(doc, "missing_page_number")
    assert not _p018(doc, "misaligned_page_number_column")


@pytest.mark.parametrize("case", ["confirmed", "absent", "unowned_numeral"])
def test_folio_geometry_in_rotated_pdf_with_wrapper_and_reviewer(tmp_path, monkeypatch, case):
    import secrets

    import pymupdf
    from fastapi.testclient import TestClient

    from njit_auditor import admin_accounts, admin_feedback, web_app

    with pymupdf.open() as pdf:
        wrapper = pdf.new_page(width=612, height=792)
        wrapper.insert_text((108, 100), "Digital Commons @ NJIT")
        wrapper.insert_text((108, 130), "Recommended Citation")
        page = pdf.new_page(width=612, height=792)
        page.insert_text((190, 88), "LIST OF FIGURES")
        rows = _wrapped_rows()
        if case != "confirmed":
            rows = rows[:-2]
            if case == "unowned_numeral":
                rows.append(_line(223, ("30", 249, 264)))
        for row in rows:
            for span in row.spans:
                page.insert_text((span.bbox.x0, span.bbox.y0 + 12), span.text, fontsize=12)
        target_token = "30" if case == "confirmed" else "3.1"
        (unrotated_target,) = [
            pymupdf.Rect(w[:4]) for w in page.get_text("words") if w[4] == target_token
        ]
        page.set_rotation(90)
        source = pdf.tobytes()

    runtime = tmp_path / "runtime"
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    monkeypatch.setenv("NJIT_AUDITOR_ADMIN_DB_PATH", str(private / "reviewer.sqlite3"))
    monkeypatch.setenv("NJIT_AUDITOR_ADMIN_SESSION_KEY", secrets.token_urlsafe(32))
    monkeypatch.setenv("NJIT_AUDITOR_REVIEWER_HTTP_BETA_ENABLED", "1")
    monkeypatch.setattr(web_app, "RUNTIME_DIR", runtime)
    password = secrets.token_urlsafe(24)
    admin_accounts.create_account("ester", password, role="reviewer")

    with TestClient(web_app.app, base_url="http://testserver") as client:
        response = client.post(
            "/audits",
            files={"file": ("synthetic.pdf", source, "application/pdf")},
            follow_redirects=False,
        )
        assert response.status_code == 303
        url = response.headers["location"]
        assert client.get(url + "/status").json()["state"] == "complete"
        job = web_app._get_job(url.rsplit("/", 1)[-1])
        assert job is not None
        raw = client.get(url + "/download/json").json()["findings"]
        (finding,) = [f for f in raw if f["rule_id"] == "P018"]
        assert finding["page"] == 2
        issue = (
            "misaligned_page_number_column" if case == "confirmed" else "missing_page_number"
        )
        expected_folio = "30" if case == "confirmed" else None
        assert finding["details"].get("destination_folio") == expected_folio
        assert finding["details"]["issue_type"] == issue
        (card,) = [c for c in job.findings if c["rule_id"] == "P018"]
        assert card["page"] == 2
        assert card["has_highlight"]
        student = client.get(url)
        assert student.status_code == 200
        if case == "confirmed":
            assert "align" in card["suggested_fix"].lower()
            assert "missing" not in card["suggested_fix"].lower()
        else:
            assert card["suggested_fix"] == P018_MISSING_PAGE_NUMBER_FIX
            assert P018_MISSING_PAGE_NUMBER_FIX in student.text
        for format_name in ("markdown", "text"):
            export = client.get(url + "/download/" + format_name)
            assert export.status_code == 200
            if case == "confirmed":
                assert "page-number column" in export.text
            else:
                assert P018_MISSING_PAGE_NUMBER_FIX in export.text
            assert "3.1 A wrapped synthetic description" in export.text

        params = {"page": 2, "rule_id": "P018", "finding_id": card["finding_id"]}
        focused = client.get(url + "/highlighted-page.pdf", params=params)
        full = client.get(url + "/pdf/highlighted", params=params)
        assert client.get("/reviewer/login", params={"next": url}).status_code == 200
        login = client.post(
            "/reviewer/login",
            data={
                "username": "ester",
                "password": password,
                "csrf_token": client.cookies.get(admin_feedback._REVIEWER_LOGIN_CSRF),
                "next": url,
            },
            headers={"Origin": "http://testserver"},
            follow_redirects=False,
        )
        assert login.status_code == 303
        reviewer = client.get(url + "/pdf/highlighted", params=params)
        complete = client.get(url + "/download/student-report.pdf")
        if case != "confirmed":
            assert P018_MISSING_PAGE_NUMBER_FIX in client.get(url).text
            comments = client.get(url + "/download/comments.pdf")
            for response in (comments, complete):
                assert response.status_code == 200
                with pymupdf.open(stream=response.content) as exported:
                    content = " ".join(" ".join(sheet.get_text().split()) for sheet in exported)
                    assert P018_MISSING_PAGE_NUMBER_FIX in content

        for response, index in ((focused, 0), (full, 1), (reviewer, 1), (complete, 1)):
            assert response.status_code == 200
            with pymupdf.open(stream=response.content) as pdf:
                assert pdf[index].rotation == 90
                matched = [
                    mark.rect
                    for mark in pdf[index].annots()
                    if mark.rect.intersects(unrotated_target)
                ]
                (rect,) = matched
                assert rect.y0 == pytest.approx(unrotated_target.y0, abs=2)
                if case == "confirmed":
                    assert rect.x1 < 180
                    assert rect.y1 == pytest.approx(unrotated_target.y1, abs=2)
                else:
                    assert rect.y1 > unrotated_target.y1
                if response is not complete:
                    assert sum(len(list(page.annots() or [])) for page in pdf) == 1
                if index == 1:
                    assert not list(pdf[0].annots() or [])


def test_holdout_inverted_reading_order_cannot_bridge_a_typed_entry():
    rows = [
        _peer(105, 1),
        _peer(129, 2),
        _line(161, ("Figure 4.1 Earlier title", 100, 435)),
        _line(171, ("Table 4.2 Later typed title", 137, 450)),
        _line(176, ("xiv", 523, 540)),
        _peer(216, 3),
    ]
    (context,) = detect_toc_like_pages(_doc(list(reversed(rows))))
    entries = extract_toc_logical_entry_lines(context, require_right_edge=True)
    assert [entry.page_number_token for entry in entries] == ["19", "19", None, "xiv", "19"]
    assert entries[3].line.bbox.y0 == 171


def test_holdout_two_equal_peer_columns_cannot_authorize_recovery():
    rows = [
        _peer(101, 1, edge=470),
        _peer(125, 2, edge=470),
        _peer(149, 3, edge=470),
        *_wrapped_rows()[3:-1],
        _peer(250, 4),
        _peer(275, 5),
        _peer(300, 6),
    ]
    # The ordinary column rule might compare the two groups. The left-hand
    # numeral still cannot enter that comparison or suppress a missing warning.
    doc = _doc(rows)
    (missing,) = _p018(doc, "missing_page_number")
    assert missing.details["affected_entry_preview"].startswith("3.1")
    for finding in _p018(doc, "misaligned_page_number_column"):
        assert "destination_folio" not in finding.details
        assert "149.0,223.0" not in finding.details.get("highlight_bboxes", "")


def test_holdout_detached_leaders_still_belong_to_their_own_final_row():
    rows = [
        _peer(115, 1),
        _peer(140, 2),
        _peer(165, 3),
        _line(193, ("Figure 4.1 An item with a broken extraction row", 108, 440)),
        _line(207, ("final title line.", 149, 330)),
        _line(209, ("...........................", 341, 503)),
        _line(211, ("31", 528, 540)),
        _peer(242, 4),
    ]
    doc = _doc(rows)
    (context,) = detect_toc_like_pages(doc)
    entries = extract_toc_logical_entry_lines(context)
    assert entries[3].page_number_token == "31"
    assert entries[3].is_wrapped
    assert not _p018(doc, "missing_page_number")
    assert not _p018(doc, "misaligned_page_number_column")


def test_holdout_integer_after_a_long_hanging_row_keeps_its_parent_folio():
    rows = [
        _peer(115, 1),
        _peer(139, 2),
        _peer(163, 3),
        _line(195, ("8.24 Long synthetic title with", 108, 510)),
        _line(212, ("a continuation extending to the title edge", 149, 509)),
        _line(223, ("90 Example units observed in the final wrap", 149, 511), ("30", 528, 540)),
        _peer(250, 4),
    ]
    (context,) = detect_toc_like_pages(_doc(rows))
    entries = extract_toc_logical_entry_lines(context)
    assert len(entries) == 5
    assert entries[3].page_number_token == "30"
    assert entries[3].is_wrapped
    assert entries[3].page_number_line is not None
    assert entries[3].page_number_line.bbox.y0 == 223


@pytest.mark.parametrize("displaced_x", [149, 180], ids=["verified-owner", "lost-owner"])
def test_wrapped_alignment_peers_keep_recovered_folio_visible(displaced_x):
    """The column is trustworthy even when wrapped title boxes are wider."""
    rows = []
    for index, y in enumerate((115, 150, 185), 1):
        rows.extend(
            [
                _line(y, (f"2.{index} Reference entry long first synthetic title", 108, 560)),
                _line(y + 14, ("continued description ...", 149, 350), ("19", 528, 540)),
            ]
        )
    number = _line(248, ("30", displaced_x, displaced_x + 15))
    rows.extend(
        [
            _line(220, ("3.1 A wrapped synthetic description", 108, 510)),
            _line(234, ("final description.", 149, 500)),
            number,
            _line(274, ("3.2 A new reference entry", 108, 560)),
            _line(288, ("continued reference ....", 149, 320), ("32", 528, 540)),
        ]
    )
    doc = _doc(rows)
    if displaced_x == 149:
        (warning,) = _p018(doc, "misaligned_page_number_column")
        assert warning.page == 12
        assert warning.details["affected_entry_count"] == "1"
        assert warning.details["destination_folio"] == "30"
        assert warning.details["bbox"] == format_bbox_detail(number.bbox)
        assert warning.details["highlight_bboxes"] == format_bbox_detail(number.bbox)
        assert not _p018(doc, "missing_page_number")
    else:
        (warning,) = _p018(doc, "missing_page_number")
        assert warning.details["affected_entry_preview"].startswith("3.1 ")
        assert not _p018(doc, "misaligned_page_number_column")
