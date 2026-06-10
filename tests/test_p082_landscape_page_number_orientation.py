"""Tests for experimental P082 landscape page-number orientation advisory."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import fitz

from njit_auditor.audit_options import AuditOptions
from njit_auditor.audit_runner import collect_pdf_layout_findings
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.rules.pdf_landscape_page_number_orientation import (
    ISSUE_ORIENTATION,
    ISSUE_POSITION,
    check_pdf_landscape_page_number_orientation,
    is_visually_landscape_page,
    quantize_dir,
    visual_angle,
)

_ORIENTATION = ISSUE_ORIENTATION
_POSITION = ISSUE_POSITION


def _make_landscape_pdf(
    path: Path,
    *,
    text: str = "42",
    x: float = 386.0,
    y: float = 580.0,
    rotate: int = 0,
    width: float = 792.0,
    height: float = 612.0,
    page_rotation: int = 0,
) -> None:
    doc = fitz.open()
    page = doc.new_page(width=width, height=height)
    if page_rotation:
        page.set_rotation(page_rotation)
    page.insert_text((x, y), text, fontsize=12, rotate=rotate)
    doc.save(path)
    doc.close()


def _issue_types(findings: list[Any]) -> list[str]:
    return [f.details["issue_type"] for f in findings if f.rule_id == "P082"]


def test_quantize_dir_cardinals() -> None:
    assert quantize_dir((1.0, 0.0)) == 0
    assert quantize_dir((0.0, -1.0)) == 90
    assert quantize_dir((-1.0, 0.0)) == 180
    assert quantize_dir((0.0, 1.0)) == 270


def test_quantize_dir_noisy_near_cardinal() -> None:
    assert quantize_dir((0.98, 0.05)) == 0
    assert quantize_dir((0.05, -0.99)) == 90


def test_quantize_dir_non_cardinal_returns_none() -> None:
    angle = math.radians(15)
    assert quantize_dir((math.cos(angle), math.sin(angle))) is None


def test_visual_angle_composition() -> None:
    assert visual_angle(90, 90) == 180
    assert visual_angle(0, 90) == 90
    assert visual_angle(270, 90) == 0


def test_is_visually_landscape_page_from_model(tmp_path: Path) -> None:
    path = tmp_path / "landscape.pdf"
    _make_landscape_pdf(path)
    page = load_pdf_layout(str(path)).pages[0]
    assert is_visually_landscape_page(page)


def test_p082_disabled_by_default(tmp_path: Path) -> None:
    path = tmp_path / "bad.pdf"
    _make_landscape_pdf(path, x=720, y=580, rotate=90)
    model = load_pdf_layout(str(path))
    assert check_pdf_landscape_page_number_orientation(model) == []
    default_findings = collect_pdf_layout_findings(model, path)
    assert not any(f.rule_id == "P082" for f in default_findings)


def test_p082_portrait_page_out_of_scope_when_enabled(tmp_path: Path) -> None:
    path = tmp_path / "portrait.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((300, 760), "42", fontsize=12)
    doc.save(path)
    doc.close()
    model = load_pdf_layout(str(path))
    assert check_pdf_landscape_page_number_orientation(model, enabled=True) == []


def test_p082_landscape_acceptable_bottom_center_horizontal(tmp_path: Path) -> None:
    path = tmp_path / "ok.pdf"
    _make_landscape_pdf(path)
    model = load_pdf_layout(str(path))
    assert check_pdf_landscape_page_number_orientation(model, enabled=True) == []


def test_p082_landscape_vertical_orientation_advisory(tmp_path: Path) -> None:
    path = tmp_path / "vertical.pdf"
    _make_landscape_pdf(path, x=720, y=580, rotate=90)
    model = load_pdf_layout(str(path))
    findings = check_pdf_landscape_page_number_orientation(model, enabled=True)
    assert _ORIENTATION in _issue_types(findings)


def test_p082_landscape_top_margin_position_advisory(tmp_path: Path) -> None:
    path = tmp_path / "top.pdf"
    _make_landscape_pdf(path, x=386, y=50, rotate=0)
    model = load_pdf_layout(str(path))
    findings = check_pdf_landscape_page_number_orientation(model, enabled=True)
    assert _POSITION in _issue_types(findings)


def test_p082_rotate_90_visually_acceptable_no_false_positive(tmp_path: Path) -> None:
    path = tmp_path / "rotated_page.pdf"
    _make_landscape_pdf(path, x=386, y=580, rotate=0, page_rotation=90)
    model = load_pdf_layout(str(path))
    assert check_pdf_landscape_page_number_orientation(model, enabled=True) == []


def test_p082_non_cardinal_direction_skipped(tmp_path: Path) -> None:
    path = tmp_path / "non_cardinal.pdf"
    doc = fitz.open()
    page = doc.new_page(width=792, height=612)
    page.insert_text(
        (386, 580),
        "42",
        fontsize=12,
        morph=(
            fitz.Point(386, 580),
            fitz.Matrix(
                math.cos(math.radians(15)),
                math.sin(math.radians(15)),
                -math.sin(math.radians(15)),
                math.cos(math.radians(15)),
                0,
                0,
            ),
        ),
    )
    doc.save(path)
    doc.close()
    model = load_pdf_layout(str(path))
    assert check_pdf_landscape_page_number_orientation(model, enabled=True) == []


def test_p082_image_only_landscape_page_skipped(tmp_path: Path) -> None:
    path = tmp_path / "image_only.pdf"
    doc = fitz.open()
    page = doc.new_page(width=792, height=612)
    page.draw_rect(
        fitz.Rect(72, 72, 720, 540),
        color=(0.8, 0.8, 0.8),
        fill=(0.8, 0.8, 0.8),
    )
    doc.save(path)
    doc.close()
    model = load_pdf_layout(str(path))
    assert check_pdf_landscape_page_number_orientation(model, enabled=True) == []


def test_p082_does_not_flag_figure_label_without_page_number_candidate(tmp_path: Path) -> None:
    path = tmp_path / "figure_label.pdf"
    doc = fitz.open()
    page = doc.new_page(width=792, height=612)
    page.insert_text((386, 580), "Figure 3.1", fontsize=12)
    doc.save(path)
    doc.close()
    model = load_pdf_layout(str(path))
    assert check_pdf_landscape_page_number_orientation(model, enabled=True) == []


def test_p082_default_mode_invariant_against_enabled_mode(tmp_path: Path) -> None:
    path = tmp_path / "invariant.pdf"
    _make_landscape_pdf(path, x=720, y=580, rotate=90)
    model = load_pdf_layout(str(path))
    default_findings = collect_pdf_layout_findings(model, path)
    enabled_findings = collect_pdf_layout_findings(
        model,
        path,
        options=AuditOptions(experimental_rules=frozenset({"P082"})),
    )
    assert not any(f.rule_id == "P082" for f in default_findings)
    assert {f.rule_id for f in default_findings}.issubset(
        {f.rule_id for f in enabled_findings}
    )
    non_p082_default = [f for f in default_findings if f.rule_id != "P082"]
    non_p082_enabled = [f for f in enabled_findings if f.rule_id != "P082"]
    assert len(non_p082_default) == len(non_p082_enabled)


def test_p082_finding_details_are_privacy_safe(tmp_path: Path) -> None:
    path = tmp_path / "privacy.pdf"
    _make_landscape_pdf(path, x=720, y=580, rotate=90)
    model = load_pdf_layout(str(path))
    findings = check_pdf_landscape_page_number_orientation(model, enabled=True)
    assert findings
    payload = json.dumps([f.model_dump() for f in findings])
    assert "42" not in payload
    for finding in findings:
        assert "candidate_sample" not in finding.details
        assert "text" not in finding.details


def test_pdf_layout_preserves_line_dir_and_wmode(tmp_path: Path) -> None:
    path = tmp_path / "meta.pdf"
    _make_landscape_pdf(path, x=720, y=580, rotate=90)
    line = load_pdf_layout(str(path)).pages[0].text_blocks[0].lines[0]
    assert line.line_dir == (0.0, -1.0)
    assert line.wmode == 0


def test_cli_enable_experimental_p082_flag(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from njit_auditor.cli import app

    path = tmp_path / "cli.pdf"
    _make_landscape_pdf(path, x=720, y=580, rotate=90)
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "pdf",
            str(path),
            "--enable-experimental",
            "P082",
            "--json-out",
            str(tmp_path / "out.json"),
        ],
    )
    assert result.exit_code == 0
    payload = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert any(item["rule_id"] == "P082" for item in payload["findings"])
