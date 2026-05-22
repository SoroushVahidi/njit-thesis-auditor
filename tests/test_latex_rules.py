from pathlib import Path

from njit_auditor.latex_loader import LoadedTexProject, load_tex_project
from njit_auditor.models import Severity
from njit_auditor.rules.latex_abstract import run_latex_abstract_checks
from njit_auditor.rules.latex_figures_tables import run_latex_figure_table_checks
from njit_auditor.rules.latex_labels import run_latex_label_checks
from njit_auditor.rules.latex_metadata import run_latex_graduation_month_check
from njit_auditor.rules.latex_risky_commands import run_latex_risky_command_checks
from njit_auditor.rules.latex_structure import run_latex_structure_checks


def _load_single(tmp_path: Path, text: str) -> LoadedTexProject:
    main = tmp_path / "main.tex"
    main.write_text(text, encoding="utf-8")
    return load_tex_project(main)


def test_abstract_forbidden_and_first_person(tmp_path: Path) -> None:
    project = _load_single(
        tmp_path,
        r"\begin{abstract}This paper shows our result.\end{abstract}",
    )
    findings = run_latex_abstract_checks(project)
    rule_ids = {f.rule_id for f in findings}
    assert "Q004" in rule_ids
    assert "Q005" in rule_ids


def test_invalid_graduation_month(tmp_path: Path) -> None:
    project = _load_single(tmp_path, "Submitted for degree in January 2026.")
    findings = run_latex_graduation_month_check(project)
    assert any(f.severity == Severity.WARNING for f in findings)
    assert any("January" in f.message for f in findings)
    assert any(f.rule_id == "Q006" for f in findings)


def test_missing_structure_warnings(tmp_path: Path) -> None:
    project = _load_single(tmp_path, "Hello world.")
    findings = run_latex_structure_checks(project)
    assert any(f.rule_id == "P008" for f in findings)


def test_risky_command_line_numbers(tmp_path: Path) -> None:
    project = _load_single(tmp_path, "Line1\n\\vspace{1em}\nLine3")
    findings = run_latex_risky_command_checks(project)
    hit = next(f for f in findings if f.rule_id == "P001")
    assert hit.details["line"] == "2"
    assert hit.details["command"] == "vspace"


def test_duplicate_labels_and_missing_ref(tmp_path: Path) -> None:
    project = _load_single(
        tmp_path,
        "\\label{dup}\n\\label{dup}\n\\label{bad label}\n\\ref{missing}",
    )
    findings = run_latex_label_checks(project)
    assert any(
        f.rule_id == "P002" and f.severity == Severity.FAIL for f in findings
    )
    assert any(f.rule_id == "P003" for f in findings)
    assert any(f.rule_id == "P004" for f in findings)


def test_figure_table_caption_and_punctuation(tmp_path: Path) -> None:
    project = _load_single(
        tmp_path,
        "\n".join(
            [
                r"\begin{figure}",
                r"\caption{Caption without ending}",
                r"\end{figure}",
                r"\begin{table}",
                r"\label{tab:x}",
                r"\end{table}",
            ]
        ),
    )
    findings = run_latex_figure_table_checks(project)
    assert any(f.rule_id == "P006" for f in findings)
    assert any(f.rule_id == "P007" for f in findings)
    assert any(f.rule_id == "P005" for f in findings)
