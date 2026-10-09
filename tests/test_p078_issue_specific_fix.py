"""Each P078 issue type gets only the remediation that applies to it.

Ester confirmed a first-person "we" in an abstract (R078, 2026-09-16); the
student-facing fix also told the student to replace "paper" or "article",
which was not the problem.
"""

from __future__ import annotations

from njit_auditor.polished_comments import resolve_suggested_fix_for_display


def test_pronoun_fix_does_not_mention_paper_or_article() -> None:
    fix = resolve_suggested_fix_for_display("P078", "abstract_pdf_first_person_pronoun")
    assert "first-person pronouns" in fix
    assert "paper" not in fix and "article" not in fix


def test_forbidden_term_fix_does_not_mention_pronouns() -> None:
    fix = resolve_suggested_fix_for_display("P078", "abstract_pdf_forbidden_term")
    assert '"paper" or "article"' in fix
    assert "pronoun" not in fix
