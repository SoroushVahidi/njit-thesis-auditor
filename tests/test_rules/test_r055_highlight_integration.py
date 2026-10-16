"""Synthetic R055 targets through the student and full-PDF highlight routes."""

from pathlib import Path

import fitz
from fastapi.testclient import TestClient

from njit_auditor import web_app


def _synthetic_rotated_list(path: Path) -> None:
    doc = fitz.open()
    doc.new_page(width=612, height=792).insert_text((108, 100), "SYNTHETIC TITLE")
    page = doc.new_page(width=612, height=792)
    page.insert_text((210, 100), "LIST OF FIGURES", fontsize=14)
    for y, text, number in (
        (180, "2.1 Synthetic repeated entry", "8"),
        (220, "2.1 Synthetic repeated entry", "9"),
        (260, "2.2 Synthetic wrapped entry starts here", None),
        (340, "Figure 2.3 Correctly prefixed entry", "11"),
    ):
        page.insert_text((108, y), text, fontsize=12)
        if number is not None:
            page.insert_text((530, y), number, fontsize=12)
    page.insert_text((150, 276), "and continues with synthetic words", fontsize=12)
    page.insert_text((530, 276), "10", fontsize=12)
    page.set_rotation(90)
    doc.save(path)
    doc.close()


def test_r055_rotated_repeated_wrapped_rows_render_at_distinct_targets(
    tmp_path: Path, monkeypatch,
) -> None:
    source = tmp_path / "synthetic.pdf"
    _synthetic_rotated_list(source)
    monkeypatch.setattr(web_app, "RUNTIME_DIR", tmp_path / "runtime")
    with TestClient(web_app.app) as client:
        upload = client.post(
            "/audits",
            files={"file": ("synthetic.pdf", source.read_bytes(), "application/pdf")},
            follow_redirects=False,
        )
        assert upload.status_code == 303
        url = upload.headers["location"]
        job = web_app._get_job(url.rsplit("/", 1)[-1])
        assert job is not None and job.state == "complete"
        raw = client.get(url + "/download/json").json()
        raw_r055 = [
            finding for finding in raw["findings"]
            if finding["rule_id"] == "P055"
        ]
        cards = [finding for finding in job.findings if finding["rule_id"] == "P055"]
        assert len(raw_r055) == len(cards) == 3
        assert [finding["details"]["entry_index"] for finding in raw_r055] == [
            "0", "1", "2"
        ]
        assert all(card["has_highlight"] for card in cards)
        boxes = [card["bbox"] for card in cards]
        assert all(box is not None for box in boxes)
        assert [round(box[1]) for box in boxes] == [167, 207, 247]
        assert boxes[2][3] > 278  # The wrapped continuation is inside its parent box.

        for card in cards:
            for route, expected_pages, annotated_page in (
                ("/highlighted-page.pdf", 1, 0),
                ("/pdf/highlighted", 2, 1),
            ):
                response = client.get(
                    url + route,
                    params={"page": 2, "finding_id": card["finding_id"]},
                )
                assert response.status_code == 200
                assert response.headers["content-type"] == "application/pdf"
                with fitz.open(stream=response.content, filetype="pdf") as highlighted:
                    assert highlighted.page_count == expected_pages
                    target_page = highlighted[annotated_page]
                    assert target_page.rotation == 90
                    annotations = list(target_page.annots() or [])
                    assert len(annotations) == 1
                    rect = annotations[0].rect
                    assert abs(rect.y0 - card["bbox"][1]) < 2
                    assert abs(rect.y1 - card["bbox"][3]) < 2
                    if expected_pages == 2:
                        title_page = highlighted[0]
                        assert not list(title_page.annots() or [])
