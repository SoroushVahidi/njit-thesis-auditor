"""Student disclosure, confidence contrast, and report presentation contracts."""

from __future__ import annotations

import html
import re
from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient
from test_web_app import _inject_complete_job_with_findings, _make_app

from njit_auditor.coverage_disclosure import (
    COVERAGE_AREAS,
    COVERAGE_INTRO,
    OFFICIAL_CHECKLIST_URL,
    STUDENT_LIMITATION_DISCLOSURE,
)
from njit_auditor.models import AuditFinding, Severity
from njit_auditor.student_confidence import CONFIDENCE_COLORS
from njit_auditor.student_pdf_report import build_combined_student_pdf_report


def sample_findings() -> list[AuditFinding]:
    # The same severity has two confidence levels; low confidence can be FAIL.
    return [
        AuditFinding(
            rule_id="P011",
            severity=severity,
            page=page,
            message="Left margin too narrow.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
                "confidence": level,
                "worst_overflow_pt": "12.0",
                "suggested_fix": "Move the flagged text inside the left margin.",
            },
        )
        for page, (level, severity) in enumerate(
            [("high", Severity.WARNING), ("medium", Severity.WARNING), ("low", Severity.FAIL)], 1
        )
    ]


def plain_html(text: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", text)).split())


def contrast(foreground: str, background: str) -> float:
    def luminance(color: str) -> float:
        rgb = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in rgb]
        return sum(v * weight for v, weight in zip(linear, [0.2126, 0.7152, 0.0722]))

    a, b = sorted([luminance(foreground), luminance(background)])
    return (b + 0.05) / (a + 0.05)


@pytest.mark.parametrize(
    "level,expected",
    [
        ("high", ("#9f1d16", "#fee4e2")),
        ("medium", ("#713f12", "#fef3c7")),
        ("low", ("#075985", "#e0f2fe")),
    ],
)
def test_confidence_palette_has_readable_text_and_distinct_boundary(level, expected):
    palette = CONFIDENCE_COLORS[level]
    assert (palette["foreground"], palette["background"]) == expected
    assert contrast(*expected) >= 4.5
    assert contrast(palette["border"], palette["background"]) >= 3


def test_results_one_disclosure_and_about_preserves_complete_coverage(tmp_path: Path):
    app, wa = _make_app(tmp_path)
    with TestClient(app) as client:
        job = _inject_complete_job_with_findings(
            wa, tmp_path, findings=sample_findings(), file_name="synthetic.pdf", audit_type="pdf"
        )
        response = client.get(f"/audits/{job}")
        assert response.status_code == 200
        text = plain_html(response.text)
        assert text.count(STUDENT_LIMITATION_DISCLOSURE) == 1
        assert OFFICIAL_CHECKLIST_URL in response.text
        for label in ["Partly checked", "Not checked", "Check yourself:"]:
            assert label not in text
        for paragraph in COVERAGE_INTRO:
            assert paragraph not in text
        assert 'href="/about#limitations"' in response.text
        about = client.get("/about")
        assert about.status_code == 200
        details = plain_html(about.text)
        for area in COVERAGE_AREAS:
            assert area.title in details and area.status_label in details
            assert area.manual in details
            if area.checked:
                assert area.checked in details
        assert "45 partially automated" in details and "32 requiring manual review" in details
        assert "5 not implemented" in details and "1 unresolved guidance conflict" in details
        assert "sentence case" in details and "title case" in details
        assert "PDFs and poor text extraction" in details
        explanation = (
            "Confidence indicates how certain the auditor is about a finding, "
            "not how serious the problem is."
        )
        assert details.count(explanation) == 1 and explanation not in text
        for level in CONFIDENCE_COLORS:
            assert f"confidence-badge--{level}" in response.text
            assert f"{level.title()} confidence" in text
        assert [f["severity"] for f in wa._get_job(job).findings] == ["WARNING", "WARNING", "FAIL"]
        for suffix in ["text", "markdown", "student-report.pdf"]:
            export = client.get(f"/audits/{job}/download/{suffix}")
            assert export.status_code == 200
            if suffix.endswith("pdf"):
                with fitz.open(stream=export.content, filetype="pdf") as doc:
                    content = " ".join(" ".join(page.get_text() for page in list(doc)[5:]).split())
            else:
                content = export.text
            assert content.count(STUDENT_LIMITATION_DISCLOSURE) == 1
            assert "Partly checked" not in content
            assert "Check yourself:" not in content
            assert "left margin" in content.lower()
            if suffix.endswith("pdf"):
                for finding in wa._get_job(job).findings:
                    assert finding["suggested_fix"] in content


def test_pdf_confidence_colors_do_not_follow_severity(tmp_path):
    source, output = tmp_path / "source.pdf", tmp_path / "report.pdf"
    with fitz.open() as doc:
        doc.new_page().insert_text((100, 100), "Synthetic source")
        doc.save(source)
    findings = [
        {
            "problem_number": number,
            "page": 1,
            "rule_id": "P011",
            "severity": "FAIL" if level == "low" else "WARNING",
            "polished_comment": "Margin issue.",
            "suggested_fix": "Move the flagged text.",
            "confidence_label": f"{level.title()} confidence",
        }
        for number, level in enumerate(CONFIDENCE_COLORS, 1)
    ]
    build_combined_student_pdf_report(
        source, output, findings, boxes_by_problem={}, file_name="synthetic.pdf"
    )
    with fitz.open(output) as doc:
        spans = [
            span
            for page in list(doc)[1:]
            for block in page.get_text("dict")["blocks"]
            for line in block.get("lines", [])
            for span in line["spans"]
        ]
        for level, palette in CONFIDENCE_COLORS.items():
            matches = [s for s in spans if s["text"] == f"{level.title()} confidence"]
            assert matches
            assert all(s["color"] == int(palette["foreground"][1:], 16) for s in matches)
