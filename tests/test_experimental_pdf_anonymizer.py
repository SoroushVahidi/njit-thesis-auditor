"""Technical gates for the isolated, synthetic-only CLI prototype."""

from __future__ import annotations

import socket
import sys
from pathlib import Path
from unittest.mock import patch

import fitz
import pytest

from scripts.experimental_pdf_anonymizer import _block_network, main, run
from scripts.experimental_pdf_engine_adapter import UnsupportedEditorPDF
from scripts.generate_anonymizer_adversarial_fixtures import make_adversarial_fixtures
from scripts.generate_synthetic_obfuscation_fixtures import generate_fixtures
from scripts.probe_pdf_editor_privacy import PLANTED, generate_planted_fixture


@pytest.mark.parametrize(
    ("kind", "severity"),
    [
        ("kerning_widened", "info"),
        ("overflow_shift_suppressed", "warning"),
        ("font_extension_failed", "error"),
    ],
)
def test_any_upstream_degradation_refuses_output(
    tmp_path: Path, kind: str, severity: str
) -> None:
    """Even an informational upstream event must be reviewed before publication."""
    pytest.importorskip("pdf_edit_engine")
    from pdf_edit_engine import replace
    from pdf_edit_engine.models import Degradation

    source = generate_fixtures(tmp_path)[0]
    output = tmp_path / "degraded-output.pdf"

    def degraded(*args: object, **kwargs: object) -> object:
        result = replace(*args, **kwargs)
        result.fidelity_report.degradations.append(
            Degradation(kind=kind, detail="synthetic trigger", severity=severity)
        )
        return result

    with patch("pdf_edit_engine.replace", side_effect=degraded):
        with pytest.raises(UnsupportedEditorPDF, match="degradation"):
            run(source, output, seed=42)
    assert not output.exists()


def test_boundary_policy_changes_word_pattern_with_strict_gates(tmp_path: Path) -> None:
    pytest.importorskip("pdf_edit_engine")
    source = generate_fixtures(tmp_path)[0]
    output = tmp_path / "boundary-output.pdf"
    report = run(source, output, seed=17, strategy="boundary")
    assert output.is_file()
    assert report["privacy"]["word_length_pattern_equal"] is False
    assert report["auditor"]["lost"] == report["auditor"]["introduced"] == 0
    assert report["geometry"]["max_line_end_x_delta_pt"] <= 0.25


def test_pinned_upstream_reports_real_oversize_degradation(tmp_path: Path) -> None:
    pytest.importorskip("pdf_edit_engine")
    from pdf_edit_engine import find, replace

    source = generate_fixtures(tmp_path)[0]
    with fitz.open(source) as doc:
        body_line = next(
            line.strip() for line in doc[2].get_text().splitlines() if len(line.strip()) > 45
        )
    matches = find(str(source), body_line, page=2)
    assert len(matches) == 1
    result = replace(
        str(source), matches[0], body_line * 2, str(tmp_path / "oversize.pdf"), reflow=False
    )
    kinds = {event.kind for event in result.fidelity_report.degradations}
    assert {"kerning_compressed", "overflow_shift_clamped"} <= kinds


def test_balanced_cli_preserves_synthetic_auditor_and_is_deterministic(tmp_path: Path) -> None:
    pytest.importorskip("pdf_edit_engine")
    sources = generate_fixtures(tmp_path)
    original_socket_connect = socket.socket.connect
    total = 0
    for source in sources:
        first = source.with_name(source.stem + "-first.pdf")
        second = source.with_name(source.stem + "-second.pdf")
        report = run(source, first, seed=42)
        run(source, second, seed=42)
        with fitz.open(first) as a, fitz.open(second) as b:
            assert [page.get_text() for page in a] == [page.get_text() for page in b]
        assert report["auditor"]["lost"] == 0
        assert report["auditor"]["introduced"] == 0
        assert report["geometry"]["max_line_end_x_delta_pt"] <= 0.25
        assert report["privacy"]["recovered_nonstructural_source_words"] == 0
        total += report["auditor"]["full_box_matched"]
    assert total == 38
    assert socket.socket.connect is original_socket_connect


def test_planted_secrets_are_not_recovered_by_independent_tools(tmp_path: Path) -> None:
    pytest.importorskip("pdf_edit_engine")
    source, output = tmp_path / "planted.pdf", tmp_path / "output.pdf"
    generate_planted_fixture(source)
    report = run(source, output, seed=7, planted_tokens=PLANTED)
    assert all(
        count == 0 for count in report["privacy"]["recovered_token_counts_by_surface"].values()
    )
    assert not report["output_safe_to_share"]


def test_network_connections_and_datagrams_are_blocked_and_restored() -> None:
    original_connect = socket.socket.connect
    original_sendto = socket.socket.sendto
    with _block_network(), socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
        with pytest.raises(RuntimeError, match="Network access is disabled"):
            client.connect(("127.0.0.1", 9))
        with pytest.raises(RuntimeError, match="Network access is disabled"):
            client.sendto(b"synthetic", ("127.0.0.1", 9))
    assert socket.socket.connect is original_connect
    assert socket.socket.sendto is original_sendto


def test_residual_object_and_unsupported_image_leave_no_output(tmp_path: Path) -> None:
    pytest.importorskip("pdf_edit_engine")
    source = tmp_path / "source.pdf"
    generate_planted_fixture(source)
    residual = tmp_path / "residual.pdf"
    residual.write_bytes(source.read_bytes() + b"\n999 0 obj\n(SECRET_TRAILING_OBJECT)\nendobj\n")
    destination = tmp_path / "residual-output.pdf"
    with pytest.raises(UnsupportedEditorPDF):
        run(residual, destination, seed=1)
    assert not destination.exists()

    image_source = tmp_path / "image.pdf"
    with fitz.open(source) as doc:
        pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 2, 2), False)
        pix.clear_with(255)
        doc[0].insert_image(fitz.Rect(20, 20, 40, 40), pixmap=pix)
        doc.save(image_source, garbage=4, deflate=True)
    image_output = tmp_path / "image-output.pdf"
    with pytest.raises(UnsupportedEditorPDF):
        run(image_source, image_output, seed=1)
    assert not image_output.exists()


def test_hostile_pdf_surfaces_refuse_without_output(tmp_path: Path) -> None:
    pytest.importorskip("pdf_edit_engine")
    fixtures = make_adversarial_fixtures(tmp_path / "fixtures")
    accepted = {"visible_metadata", "multi_column"}
    assert len(fixtures) == 23
    for surface, source in fixtures.items():
        output = tmp_path / f"{surface}-output.pdf"
        if surface in accepted:
            report = run(source, output, seed=42)
            assert report["auditor"]["lost"] == 0
            assert output.is_file()
        else:
            with pytest.raises(UnsupportedEditorPDF):
                run(source, output, seed=42)
            assert not output.exists()

    with fitz.open(fixtures["vector"]) as doc:
        positions = {round(drawing["rect"].x0) for drawing in doc[0].get_drawings()}
    bits = "".join(
        "1" if 50 + 3 * index in positions else "0"
        for index in range(8 * len(b"VECTOR_SECRET_CEDAR_521"))
    )
    recovered = bytes(int(bits[i : i + 8], 2) for i in range(0, len(bits), 8))
    assert recovered == b"VECTOR_SECRET_CEDAR_521"


def test_privacy_and_auditor_gate_failures_do_not_publish(tmp_path: Path) -> None:
    pytest.importorskip("pdf_edit_engine")
    source = make_adversarial_fixtures(tmp_path / "fixtures")["visible_metadata"]
    leaked = tmp_path / "leaked.pdf"
    # ABSTRACT is intentionally retained as a structural marker. Declaring
    # it planted secret must still cause the privacy gate to refuse output.
    with pytest.raises(UnsupportedEditorPDF, match="Privacy"):
        run(source, leaked, seed=7, planted_tokens=("ABSTRACT",))
    assert not leaked.exists()

    drifted = tmp_path / "drifted.pdf"
    with patch(
        "scripts.experimental_pdf_anonymizer._strict_comparison",
        return_value={"original": 1, "matched": 0, "lost": 1, "introduced": 0},
    ):
        with pytest.raises(UnsupportedEditorPDF, match="auditor-equivalence"):
            run(source, drifted, seed=7)
    assert not drifted.exists()


def test_report_path_cannot_overwrite_pdf(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "source.pdf"
    generate_planted_fixture(source)
    before = source.read_bytes()
    output = tmp_path / "output.pdf"
    monkeypatch.setattr(
        sys, "argv", ["experimental_pdf_anonymizer", str(source), str(output),
                     "--seed", "1", "--report", str(output)],
    )
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
    assert source.read_bytes() == before
    assert not output.exists()
