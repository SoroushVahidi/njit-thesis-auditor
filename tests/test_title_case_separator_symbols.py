"""A subtitle separator capitalizes the first *word* of the subtitle.

Ester's capitalization rule: the first word after a period, colon, question
mark, or exclamation mark is capitalized; articles, prepositions, and
conjunctions otherwise stay lowercase. When a symbol or number opens the
subtitle (": # of", ": % of", ": 3 of"), that token is the first word, so a
following preposition must not be forced to a capital.
"""

from __future__ import annotations

from njit_auditor.rules.pdf_title_capitalization import check_apa_title_case_phrase


def _flagged(text: str) -> set[str]:
    return {issue["word"] for issue in check_apa_title_case_phrase(text)}


def test_preposition_after_separator_and_symbol_is_not_flagged() -> None:
    assert "of" not in _flagged("Model Parameters: # of Trees and Depth Limits")
    assert "of" not in _flagged("Detection Results: % of Samples Flagged by Method")
    assert "of" not in _flagged("Benchmark Summary: 3 of the Datasets Used")


def test_word_directly_after_separator_is_still_capitalized() -> None:
    issues = check_apa_title_case_phrase("Network Design: of Models and Methods")
    assert any(
        i["word"] == "of" and i["reason"] == "word_after_separator_requires_capital"
        for i in issues
    )


def test_opening_quote_or_bracket_does_not_consume_the_first_word() -> None:
    assert "the" in _flagged("Case Study: (the Northern Region) Results")
    assert "the" in _flagged('Case Study: "the Northern Region" Results')


def test_major_words_after_symbol_are_still_checked() -> None:
    assert "trees" in _flagged("Model Parameters: # of trees and Depth Limits")
