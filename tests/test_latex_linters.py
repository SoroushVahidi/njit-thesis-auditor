from pathlib import Path

from njit_auditor.latex_linters import (
    _parse_chktex_line,
    _parse_lacheck_line,
    is_tool_available,
    run_chktex,
    run_lacheck,
)


def test_is_tool_available_uses_path_lookup() -> None:
    assert isinstance(is_tool_available("definitely_missing_tool_name"), bool)


def test_missing_chktex_returns_skipped_finding(monkeypatch: object, tmp_path: Path) -> None:
    monkeypatch.setattr("njit_auditor.latex_linters.is_tool_available", lambda _: False)
    findings = run_chktex(tmp_path / "main.tex")
    assert findings
    assert findings[0].rule_id == "P009"
    assert "skipped" in findings[0].message.lower()


def test_missing_lacheck_returns_skipped_finding(monkeypatch: object, tmp_path: Path) -> None:
    monkeypatch.setattr("njit_auditor.latex_linters.is_tool_available", lambda _: False)
    findings = run_lacheck(tmp_path / "main.tex")
    assert findings
    assert findings[0].rule_id == "P010"
    assert "skipped" in findings[0].message.lower()


def test_parse_sample_chktex_output_line() -> None:
    finding = _parse_chktex_line("main.tex:12:4:Warning 24:Command terminated with space.")
    assert finding is not None
    assert finding.rule_id == "P009"
    assert finding.details["line"] == "12"
    assert "terminated with space" in finding.message


def test_parse_sample_lacheck_output_line() -> None:
    finding = _parse_lacheck_line("main.tex, line 8: possible unwanted space at \"~\"")
    assert finding is not None
    assert finding.rule_id == "P010"
    assert finding.details["line"] == "8"
    assert "possible unwanted space" in finding.message
