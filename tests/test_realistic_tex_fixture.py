from pathlib import Path

from typer.testing import CliRunner

from njit_auditor.cli import app, collect_tex_findings
from njit_auditor.latex_loader import load_tex_project
from njit_auditor.models import Severity

runner = CliRunner()


def test_realistic_loader_loads_multifile_fixture() -> None:
    project = load_tex_project("examples/latex/njit_style_synthetic_thesis/main.tex")
    loaded_paths = {file.path for file in project.files}
    assert len(loaded_paths) >= 5
    assert any(path.name == "abstract.tex" for path in loaded_paths)
    assert any(path.name == "chapter1.tex" for path in loaded_paths)
    assert any(path.name == "chapter2.tex" for path in loaded_paths)


def test_realistic_good_fixture_has_no_fail_findings() -> None:
    _, _, findings = collect_tex_findings("examples/latex/njit_style_synthetic_thesis/main.tex")
    assert not any(f.severity == Severity.FAIL for f in findings)
    assert not any(f.rule_id == "Q006" and f.severity == Severity.WARNING for f in findings)


def test_realistic_bad_fixture_reports_expected_rules() -> None:
    _, _, findings = collect_tex_findings("examples/latex/njit_style_synthetic_thesis_bad/main.tex")
    rule_ids = {f.rule_id for f in findings}
    assert "Q004" in rule_ids
    assert "Q005" in rule_ids
    assert "Q006" in rule_ids
    assert any(f.rule_id == "Q006" and f.severity == Severity.WARNING for f in findings)
    project_rule_ids = {"P001", "P002", "P003", "P004", "P005", "P006", "P007", "P008"}
    assert any(rule_id in project_rule_ids for rule_id in rule_ids)


def test_realistic_fixture_cli_runs() -> None:
    good = Path("examples/latex/njit_style_synthetic_thesis/main.tex")
    bad = Path("examples/latex/njit_style_synthetic_thesis_bad/main.tex")

    good_result = runner.invoke(app, ["tex", str(good)])
    assert good_result.exit_code == 0
    assert "TeX Audit Findings" in good_result.output

    bad_result = runner.invoke(app, ["tex", str(bad)])
    assert bad_result.exit_code == 0
    assert "FAIL" in bad_result.output
