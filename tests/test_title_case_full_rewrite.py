"""The P020 "Change X to Y" fix corrects every flagged word, not just the first.

Ester (Sample A, 2026-07-06) confirmed a level-2 title-case issue but rejected
the suggested fix. A rewrite that capitalizes one word and leaves the next
major word lowercase is still not title case.
"""

from __future__ import annotations

from njit_auditor.rules.pdf_title_capitalization import (
    _corrected_preview,
    check_apa_title_case_phrase,
)
from njit_auditor.title_case_student_preview import p020_short_suggested_fix

_TITLE = "Graph Attention Networks in power systems"


def test_corrected_preview_fixes_every_flagged_word() -> None:
    issues = check_apa_title_case_phrase(_TITLE)
    assert {i["word"] for i in issues} == {"power", "systems"}
    assert _corrected_preview(_TITLE, _TITLE, issues) == "Graph Attention Networks in Power Systems"


def test_corrected_preview_is_truncated_to_the_preview_prefix() -> None:
    issues = check_apa_title_case_phrase(_TITLE)
    assert _corrected_preview(_TITLE, _TITLE[:30], issues) == "Graph Attention Networks in Po"
    assert _corrected_preview(_TITLE, "Unrelated preview", issues) == ""


def test_suggested_fix_uses_the_fully_corrected_title() -> None:
    fix = p020_short_suggested_fix(
        "power", "Power", _TITLE, corrected_preview="Graph Attention Networks in Power Systems"
    )
    assert fix == f'Change "{_TITLE}" to "Graph Attention Networks in Power Systems".'


def test_suggested_fix_falls_back_without_a_corrected_preview() -> None:
    assert p020_short_suggested_fix("power", "Power", _TITLE) == (
        f'Change "{_TITLE}" to "Graph Attention Networks in Power systems".'
    )


def test_corrected_preview_that_changes_more_than_case_is_ignored() -> None:
    fix = p020_short_suggested_fix(
        "power", "Power", _TITLE, corrected_preview="Something else entirely"
    )
    assert "Something else" not in fix
