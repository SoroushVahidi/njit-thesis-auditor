from pathlib import Path

from typer.testing import CliRunner

from njit_auditor.cli import app, collect_tex_findings
from njit_auditor.models import Severity

runner = CliRunner()


def test_good_demo_has_no_fail_findings() -> None:
    _, _, findings = collect_tex_findings("examples/latex/good_minimal_thesis/main.tex")
    assert not any(f.severity == Severity.FAIL for f in findings)
    assert not any(f.rule_id == "Q006" and f.severity == Severity.WARNING for f in findings)


def test_bad_demo_reports_expected_rules() -> None:
    _, _, findings = collect_tex_findings("examples/latex/bad_minimal_thesis/main.tex")
    rule_ids = {f.rule_id for f in findings}
    assert "Q004" in rule_ids
    assert "Q005" in rule_ids
    assert "Q006" in rule_ids
    assert any(f.rule_id == "Q006" and f.severity == Severity.WARNING for f in findings)
    assert "P001" in rule_ids
    assert "P002" in rule_ids
    assert any(rule_id in {"P005", "P006", "P007"} for rule_id in rule_ids)


def test_cli_tex_command_runs_for_demo_examples() -> None:
    good_path = Path("examples/latex/good_minimal_thesis/main.tex")
    bad_path = Path("examples/latex/bad_minimal_thesis/main.tex")

    good_result = runner.invoke(app, ["tex", str(good_path)])
    assert good_result.exit_code == 0
    assert good_result.output  # CLI produces some output

    bad_result = runner.invoke(app, ["tex", str(bad_path)])
    assert bad_result.exit_code == 0
    assert bad_result.output  # CLI produces some output
    # Verify FAIL findings via the stable direct API rather than Rich-rendered output.
    # Rich adds ANSI escape codes and truncates table cells in narrow terminals (e.g., tmux),
    # making substring checks on rendered output terminal-width-dependent and fragile.
    # Functional correctness is covered by test_bad_demo_reports_expected_rules.
    _, _, bad_findings = collect_tex_findings(str(bad_path))
    assert any(f.severity == Severity.FAIL for f in bad_findings)


def test_cli_tex_linters_flag_does_not_crash_when_tools_missing() -> None:
    good_path = Path("examples/latex/good_minimal_thesis/main.tex")
    result = runner.invoke(app, ["tex", str(good_path), "--linters"])
    assert result.exit_code == 0
    assert "P009" in result.output or "P010" in result.output
