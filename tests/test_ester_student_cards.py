"""Student card regressions using only committed synthetic PDFs."""

from __future__ import annotations

import io
import os
import re
from html import unescape
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from njit_auditor.student_cards import student_card_fields

FIXTURES = Path(__file__).parent / "fixtures" / "web_demo"


@pytest.fixture()
def web(tmp_path: Path) -> tuple[TestClient, Any]:
    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "jobs")
    import importlib

    import njit_auditor.web_app as wa

    importlib.reload(wa)
    return TestClient(wa.app, raise_server_exceptions=False), wa


def _job(web: tuple[TestClient, Any], name: str = "issues_pdf.pdf") -> tuple[TestClient, Any, str]:
    client, wa = web
    result = client.post(
        "/audits",
        files={"file": (name, io.BytesIO((FIXTURES / name).read_bytes()), "application/pdf")},
        follow_redirects=False,
    )
    assert result.status_code == 303
    job_id = result.headers["location"].rsplit("/", 1)[-1]
    job = wa._get_job(job_id)
    assert job is not None and job.state == "complete"
    return client, job, job_id


def _primary_cards(body: str) -> list[str]:
    return re.findall(
        r'<article\b[^>]*class="finding-row finding-card"[^>]*>(.*?)</article>',
        body,
        re.DOTALL,
    )


def test_margin_wording_uses_only_detector_evidence() -> None:
    finding = {
        "rule_id": "P011",
        "category": "margin_or_overflow",
        "page": 4,
        "location_label": "Page 4 — bottom margin",
        "issue_type_label": "Margin boundary violation",
    }
    measured = student_card_fields(finding, {"side": "bottom_margin", "worst_overflow_pt": "22.0"})
    assert measured["student_topic"] == "MARGINS"
    assert measured["student_summary"] == (
        "Text appears to extend about 0.31 inch past the bottom margin boundary."
    )
    assert measured["student_location"] == ""
    assert measured["margin_questions"] == [
        ("Did the check detect text crossing the bottom margin?", "Yes")
    ]
    assert len(measured["check_yourself"]) == 2
    assert measured["technical_details"] == [("Detected bottom overflow", "22.0 pt")]
    unknown = student_card_fields(finding, {})
    assert unknown["margin_questions"] == []
    assert len(unknown["check_yourself"]) == 3
    assert "Needs review" not in str(unknown)
    assert "Yes" not in str(unknown)
    assert "No" not in str(unknown)
    assert "pt" not in unknown["student_summary"]
    assert not student_card_fields(
        finding, {"side": "bottom_margin", "worst_overflow_pt": "nan"}
    )["margin_questions"]

    other = student_card_fields(
        {"rule_id": "P026", "category": "font_format", "issue_type_label": "Body font issue"}, {}
    )
    assert other["student_topic"] == "FONT FORMATTING"
    assert other["margin_questions"] == []


def test_synthetic_results_cards_and_drilldown_agree(web: tuple[TestClient, Any]) -> None:
    client, job, job_id = _job(web)
    response = client.get(f"/audits/{job_id}")
    assert response.status_code == 200
    body = unescape(response.text)
    cards = _primary_cards(body)
    assert len(cards) == len(job.findings) > 0
    assert [f"Finding {index} of {len(cards)}" in card for index, card in enumerate(cards, 1)] == [
        True
    ] * len(cards)
    assert 'id="filter-rule"' in body and 'id="sort-problems"' in body
    assert 'position.textContent = "Finding " + visible' in body
    assert "Open highlighted PDF" in body or "Open PDF" in body
    for card in cards:
        assert "Problem " not in card.split("<details", 1)[0]
        assert "What to check:" in card or "Review this finding" in card
        assert re.search(r'<span class="finding-card__page">\s*Page \d+', card)
        assert "All findings on this page" in card
        assert "Technical details" in card
        assert re.search(r"confidence-badge--(?:high|medium|low)", card)
        if "Open highlighted PDF" in card or ">Open PDF</a>" in card:
            action = re.search(r'<div class="finding-card__action">\s*<a href="([^"]+)"', card)
            assert action is not None
            pdf = client.get(action.group(1))
            assert pdf.status_code == 200
            assert pdf.headers["content-type"].startswith("application/pdf")
    margin = next(card for card in cards if ">MARGINS</a>" in card)
    assert ">R011</a>" not in margin.split("<details", 1)[0]
    assert "Check yourself" in margin and ">Yes</strong>" in margin
    assert "Needs review" not in margin
    assert "past the" in margin and "inch" in margin
    assert "margin-answer--no" not in margin
    assert "Page " not in re.search(
        r'<div class="finding-card__action">(.*?)</div>', margin, re.DOTALL
    ).group(1)

    detail = unescape(client.get(f"/audits/{job_id}/problems/rule/P011").text)
    assert "MARGINS" in detail and "Finding 1 of" in detail
    assert "Check yourself" in detail and "Open" in detail
    assert "Needs review" not in detail
    assert "highlighted-page.pdf" in detail or "/pdf" in detail
    assert "Check yourself" in detail and "Technical details" in detail
    assert client.get(f"/audits/{job_id}/download/json").status_code == 200
    assert client.get(f"/audits/{job_id}/download/markdown").status_code == 200


def test_sort_and_viewport_keep_real_totals(web: tuple[TestClient, Any]) -> None:
    client, job, job_id = _job(web)
    count = len(job.findings)
    for sort in ("default", "confidence_desc", "confidence_asc"):
        for width in ("390", "1440"):
            response = client.get(
                f"/audits/{job_id}?sort={sort}", headers={"Viewport-Width": width}
            )
            assert response.status_code == 200
            cards = _primary_cards(response.text)
            assert len(cards) == count
            assert all(f"Finding {i} of {count}" in card for i, card in enumerate(cards, 1))
            assert 'aria-pressed="true"' in response.text
            assert 'target="_blank" rel="noopener noreferrer"' in response.text


def test_other_topics_render_as_names_on_both_views(web: tuple[TestClient, Any]) -> None:
    from njit_auditor.audit_runner import UploadedAuditResult
    from njit_auditor.models import AuditFinding, Severity
    from njit_auditor.upload_handling import UploadKind

    client, wa = web
    findings = [
        AuditFinding(
            rule_id="P026",
            severity=Severity.WARNING,
            page=1,
            message="Possible body font issue.",
            details={"issue_type": "possible_body_font_family_issue"},
        ),
        AuditFinding(
            rule_id="P037",
            severity=Severity.WARNING,
            page=2,
            message="Page number sequence issue.",
            details={"issue_type": "wrong_page_number_sequence"},
        ),
    ]

    def fake_audit(_path: Path, **_kwargs: Any) -> UploadedAuditResult:
        return UploadedAuditResult(upload_kind=UploadKind.PDF, audit_type="pdf", findings=findings)

    with patch.object(wa, "run_audit_for_uploaded_file", fake_audit):
        client, job, job_id = _job(web)
    body = client.get(f"/audits/{job_id}").text
    cards = _primary_cards(body)
    assert len(cards) == len(job.findings) == 2
    assert ">FONT FORMATTING</a>" in cards[0]
    assert ">PAGE NUMBERING</a>" in cards[1]
    assert "Finding 1 of 2" in cards[0] and "Finding 2 of 2" in cards[1]
    detail = client.get(f"/audits/{job_id}/problems/rule/P026").text
    assert "FONT FORMATTING" in detail and "Finding 1 of 1" in detail
    assert "About this issue" in detail
    assert "Finding type: Possible body font family issue" not in detail
