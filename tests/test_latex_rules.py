from pathlib import Path

from njit_auditor.latex_loader import LoadedTexProject, load_tex_project
from njit_auditor.models import Severity
from njit_auditor.rules.latex_abstract import (
    count_abstract_words,
    infer_degree_type,
    run_latex_abstract_checks,
    run_latex_abstract_word_count_check,
)
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


def test_abstract_detection_through_latex_macros(tmp_path: Path) -> None:
    project = _load_single(
        tmp_path,
        r"\begin{abstract}\textit{paper} and \emph{We} present results.\end{abstract}",
    )
    findings = run_latex_abstract_checks(project)
    rule_ids = {f.rule_id for f in findings}
    assert "Q004" in rule_ids
    assert "Q005" in rule_ids


def test_latex_commands_do_not_create_abstract_false_positives(tmp_path: Path) -> None:
    project = _load_single(
        tmp_path,
        (
            r"\begin{abstract}"
            r"\newcommand{\papertrail}{x} The dissertation evaluates formatting."
            r"\end{abstract}"
        ),
    )
    findings = run_latex_abstract_checks(project)
    assert not any(f.rule_id in {"Q004", "Q005"} and f.severity == Severity.FAIL for f in findings)


def test_malformed_latex_in_abstract_does_not_crash(tmp_path: Path) -> None:
    project = _load_single(tmp_path, r"\begin{abstract}\textit{paper \emph{We}\end{abstract}")
    findings = run_latex_abstract_checks(project)
    assert findings


def test_invalid_graduation_month(tmp_path: Path) -> None:
    project = _load_single(tmp_path, r"\date{June 2026}")
    findings = run_latex_graduation_month_check(project)
    assert any(f.severity == Severity.WARNING for f in findings)
    assert any("June" in f.message for f in findings)
    assert any(f.rule_id == "Q006" for f in findings)


def test_valid_metadata_month_passes_q006(tmp_path: Path) -> None:
    project = _load_single(tmp_path, r"\date{May 2026}")
    findings = run_latex_graduation_month_check(project)
    q006_findings = [f for f in findings if f.rule_id == "Q006"]
    assert q006_findings
    assert all(f.severity != Severity.WARNING for f in q006_findings)


def test_body_month_does_not_override_valid_metadata_month(tmp_path: Path) -> None:
    project = _load_single(
        tmp_path,
        "\n".join(
            [
                r"\date{May 2026}",
                r"\begin{document}",
                "In January we reviewed prior unrelated results.",
                r"\end{document}",
            ]
        ),
    )
    findings = run_latex_graduation_month_check(project)
    q006_findings = [f for f in findings if f.rule_id == "Q006"]
    assert q006_findings
    assert all(f.severity != Severity.WARNING for f in q006_findings)


def test_missing_metadata_month_warns_q006(tmp_path: Path) -> None:
    project = _load_single(tmp_path, r"\title{Demo}\author{Student}")
    findings = run_latex_graduation_month_check(project)
    assert any(f.rule_id == "Q006" and f.severity == Severity.WARNING for f in findings)


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


# ---------------------------------------------------------------------------
# P021: Abstract word-count checks — unit helpers
# ---------------------------------------------------------------------------


def test_count_abstract_words_basic() -> None:
    assert count_abstract_words("This is a test sentence") == 5


def test_count_abstract_words_skips_pure_numbers() -> None:
    # Tokens with no letters (e.g. bare citation numbers) should not count
    assert count_abstract_words("Result: 42 items") == 2


def test_count_abstract_words_counts_mixed_tokens() -> None:
    # Words like CO2 contain letters, should count
    assert count_abstract_words("CO2 and H2O emissions") == 4


def test_infer_degree_type_phd(tmp_path: Path) -> None:
    project = _load_single(
        tmp_path,
        r"\documentclass{report}" + "\n" +
        r"\title{A Dissertation Submitted for the Degree of Doctor of Philosophy}" + "\n" +
        r"\begin{abstract}Text.\end{abstract}",
    )
    assert infer_degree_type(project) == "phd"


def test_infer_degree_type_ms(tmp_path: Path) -> None:
    project = _load_single(
        tmp_path,
        r"\documentclass{report}" + "\n" +
        r"\title{A Thesis Submitted for the Degree of Master of Science}" + "\n" +
        r"\begin{abstract}Text.\end{abstract}",
    )
    assert infer_degree_type(project) == "ms"


def test_infer_degree_type_unknown(tmp_path: Path) -> None:
    project = _load_single(tmp_path, r"\begin{abstract}Text.\end{abstract}")
    assert infer_degree_type(project) == "unknown"


# ---------------------------------------------------------------------------
# P021: Abstract word-count checks — integration tests
# ---------------------------------------------------------------------------


def _make_words(n: int) -> str:
    """Produce a synthetic plain-text phrase of exactly n words."""
    return " ".join(f"word{i}" for i in range(n))


def test_phd_abstract_under_limit_no_p021(tmp_path: Path) -> None:
    abstract_body = _make_words(300)  # 300 < 350
    project = _load_single(
        tmp_path,
        f"dissertation doctoral\\n\\\\begin{{abstract}}{abstract_body}\\\\end{{abstract}}",
    )
    project = _load_single(
        tmp_path,
        "dissertation\n" + f"\\begin{{abstract}}{abstract_body}\\end{{abstract}}",
    )
    findings = run_latex_abstract_word_count_check(project)
    assert not any(f.rule_id == "P021" for f in findings)


def test_phd_abstract_over_limit_warns_p021(tmp_path: Path) -> None:
    abstract_body = _make_words(360)  # 360 > 350
    project = _load_single(
        tmp_path,
        "dissertation\n" + f"\\begin{{abstract}}{abstract_body}\\end{{abstract}}",
    )
    findings = run_latex_abstract_word_count_check(project)
    warning = next(f for f in findings if f.rule_id == "P021")
    assert warning.severity.value == "WARNING"
    assert int(warning.details["word_count"]) > 350
    assert warning.details["inferred_degree_type"] == "phd"


def test_ms_abstract_under_limit_no_p021(tmp_path: Path) -> None:
    abstract_body = _make_words(120)  # 120 < 150
    project = _load_single(
        tmp_path,
        "thesis master\n" + f"\\begin{{abstract}}{abstract_body}\\end{{abstract}}",
    )
    findings = run_latex_abstract_word_count_check(project)
    assert not any(f.rule_id == "P021" for f in findings)


def test_ms_abstract_over_limit_warns_p021(tmp_path: Path) -> None:
    abstract_body = _make_words(160)  # 160 > 150
    project = _load_single(
        tmp_path,
        "thesis master\n" + f"\\begin{{abstract}}{abstract_body}\\end{{abstract}}",
    )
    findings = run_latex_abstract_word_count_check(project)
    warning = next(f for f in findings if f.rule_id == "P021")
    assert int(warning.details["word_count"]) > 150
    assert warning.details["inferred_degree_type"] == "ms"
    assert warning.details["limit"] == "150"


def test_latex_macros_do_not_badly_inflate_count(tmp_path: Path) -> None:
    # A short abstract with many LaTeX commands should not produce a false P021
    abstract_body = r"\textit{Short} \emph{clean} \cite{ref1} abstract text."
    project = _load_single(
        tmp_path,
        "dissertation\n" + f"\\begin{{abstract}}{abstract_body}\\end{{abstract}}",
    )
    findings = run_latex_abstract_word_count_check(project)
    assert not any(f.rule_id == "P021" for f in findings)


def test_unknown_degree_type_over_both_limits_warns_p021(tmp_path: Path) -> None:
    abstract_body = _make_words(400)  # > 350 = over both limits
    project = _load_single(
        tmp_path,
        f"\\begin{{abstract}}{abstract_body}\\end{{abstract}}",
    )
    findings = run_latex_abstract_word_count_check(project)
    warning = next(f for f in findings if f.rule_id == "P021")
    assert warning.details["inferred_degree_type"] == "unknown"


def test_unknown_degree_type_between_limits_warns_low_confidence(tmp_path: Path) -> None:
    abstract_body = _make_words(200)  # > 150 but < 350
    project = _load_single(
        tmp_path,
        f"\\begin{{abstract}}{abstract_body}\\end{{abstract}}",
    )
    findings = run_latex_abstract_word_count_check(project)
    warning = next(f for f in findings if f.rule_id == "P021")
    assert warning.details["confidence"] == "low"
    assert warning.details["inferred_degree_type"] == "unknown"


def test_no_abstract_block_produces_no_p021(tmp_path: Path) -> None:
    project = _load_single(tmp_path, r"\documentclass{report}")
    findings = run_latex_abstract_word_count_check(project)
    assert not any(f.rule_id == "P021" for f in findings)


def test_malformed_abstract_does_not_crash_p021(tmp_path: Path) -> None:
    project = _load_single(
        tmp_path,
        r"\begin{abstract}\textit{unclosed macro\end{abstract}",
    )
    findings = run_latex_abstract_word_count_check(project)
    assert isinstance(findings, list)
