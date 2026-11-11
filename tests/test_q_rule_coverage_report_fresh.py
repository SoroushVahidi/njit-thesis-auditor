"""The checked-in Q-rule coverage report must match its generator."""

from __future__ import annotations

import json
from pathlib import Path

from njit_auditor.specs.q_rule_coverage import (
    REPORT_PATH,
    build_coverage_report,
    coverage_report_payload,
    main,
    render_coverage_report,
)

_REGENERATE = "python -m njit_auditor.specs.q_rule_coverage --generated <YYYY-MM-DD>"


def _checked_in() -> dict[str, object]:
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


def test_checked_in_coverage_report_is_fresh() -> None:
    checked_in = _checked_in()
    expected = coverage_report_payload(build_coverage_report(), str(checked_in["generated"]))
    if checked_in != expected:
        stale = [
            new["q_id"]
            for old, new in zip(checked_in["q_rules"], expected["q_rules"])  # type: ignore[call-overload]
            if old != new
        ]
        raise AssertionError(
            f"data/specs/q_rule_coverage_report.json is stale (rows: {stale or 'summary/order'}). "
            f"Regenerate with: {_REGENERATE}"
        )


def test_checked_in_file_uses_generator_format() -> None:
    checked_in = _checked_in()
    assert REPORT_PATH.read_text(encoding="utf-8") == render_coverage_report(
        str(checked_in["generated"])
    )


def test_generator_is_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    assert main(["--generated", "2026-01-01", "--output", str(first)]) == 0
    assert main(["--generated", "2026-01-01", "--output", str(second)]) == 0
    assert first.read_bytes() == second.read_bytes()


def test_q052_coverage_reflects_toc_owner_p075() -> None:
    rows = {row["q_id"]: row for row in _checked_in()["q_rules"]}  # type: ignore[attr-defined]
    q052 = rows["Q052"]
    assert q052["implementation_status"] == "implemented"
    assert "P075" in q052["implementing_p_rules"]
    # P018 keeps its List of Tables/List of Figures leader findings (R018D).
    assert "P018" in q052["implementing_p_rules"]
    for q_id in ("Q069", "Q079"):
        assert {"P018", "P048"} <= set(rows[q_id]["implementing_p_rules"])


def test_q029_q074_preserve_history_and_show_current_authority() -> None:
    rows = {row["q_id"]: row for row in _checked_in()["q_rules"]}  # type: ignore[attr-defined]
    q029 = rows["Q029"]
    q074 = rows["Q074"]
    assert "hanging indent" in q029["question"]
    assert q029["implementation_status"] == "unimplemented"
    assert q029["current_authority_overlay"]["effective_implementation_status"] == (
        "optional_not_enforced"
    )
    assert "optional" in q029["current_authority_overlay"]["effective_requirement"]
    assert "sentence case" in q074["question"]
    assert q074["implementation_status"] == "implemented"
    assert q074["current_authority_overlay"]["effective_implementation_status"] == (
        "partially_implemented"
    )
    assert "sentence case" in q074["current_authority_overlay"]["effective_requirement"]
    assert "current_authority_overlay" not in rows["Q030"]
