"""PDF typographic ligatures must not invent title-case word tokens.

Privacy-safe synthetic phrases only — no dissertation prose.
"""

from __future__ import annotations

import unicodedata

from njit_auditor.highlight_targeting import estimate_word_bbox_in_line_bbox
from njit_auditor.rules.pdf_title_capitalization import (
    check_apa_title_case_phrase,
    tokenize_title_words,
)
from njit_auditor.title_case_student_preview import p020_short_suggested_fix


def _flagged(text: str) -> set[str]:
    return {issue["word"] for issue in check_apa_title_case_phrase(text)}


def test_ligature_inside_capitalized_word_is_one_token() -> None:
    # ﬁ (U+FB01), ﬃ (U+FB03), ﬄ (U+FB04), ﬂ (U+FB02), ﬀ (U+FB00)
    text = "Clariﬁcation and Coeﬃcient of Baﬄe Flow and Eﬀects"
    assert tokenize_title_words(text) == [
        "Clariﬁcation",
        "and",
        "Coeﬃcient",
        "of",
        "Baﬄe",
        "Flow",
        "and",
        "Eﬀects",
    ]
    assert _flagged(text) == set()


def test_ligature_split_fragments_are_not_flagged_as_major_words() -> None:
    # Without ligature-aware tokenization these become phantom majors:
    # cation / cients / e / clari / occulator / lter / uence.
    text = (
        "Clariﬁcation Methods and Minor Loss Coeﬃcients for Baﬄe Design "
        "and Floc ﬁltration Inﬂuence Studies"
    )
    flagged = _flagged(text)
    assert "cation" not in flagged
    assert "cients" not in flagged
    assert "e" not in flagged
    assert "clari" not in flagged
    assert "occulator" not in flagged
    assert "lter" not in flagged
    assert "uence" not in flagged


def test_lowercase_ligature_major_word_still_flagged() -> None:
    text = "Results for ﬂocculator design and Mixing Methods"
    issues = check_apa_title_case_phrase(text)
    by_word = {issue["word"]: issue for issue in issues}
    assert "ﬂocculator" in by_word
    assert by_word["ﬂocculator"]["expected"] == "Flocculator"
    assert "design" in by_word


def test_fragmented_extraction_around_ligature_does_not_invent_cation() -> None:
    # Some extractors emit the ligature as its own run; the surrounding ASCII
    # letters must not become independent capitalization targets.
    glued = "Surface Clariﬁcation Results Overview Title"
    spaced = "Surface Clari ﬁcation Results Overview Title"
    assert "cation" not in _flagged(glued)
    assert "cation" not in _flagged(spaced)
    # The spaced form still has a lowercase major after the break; that real
    # token remains detectable.
    assert "ﬁcation" in _flagged(spaced) or "fication" in {
        unicodedata.normalize("NFKC", w) for w in _flagged(spaced)
    }


def test_genuine_lowercase_major_and_legitimate_minor_words() -> None:
    assert "learning" in _flagged("Machine learning Approaches for Signal Processing")
    assert "with" not in _flagged("Comparison with Prior Studies and Methods")
    assert _flagged("Performance of the Baseline Model on Benchmark Data") == set()


def test_mixed_punctuation_and_unicode_title_still_checks_majors() -> None:
    text = "Results: Clariﬁcation—and Coeﬃcient Effects on Flow"
    flagged = _flagged(text)
    assert "cation" not in flagged
    assert "cients" not in flagged
    # Em-dash is a subtitle separator, so the following word is capitalized
    # even when it is ordinarily a minor word.
    assert any(
        i["word"] == "and" and i["reason"] == "word_after_separator_requires_capital"
        for i in check_apa_title_case_phrase(text)
    )
    assert "Clariﬁcation" not in flagged
    assert "Coeﬃcient" not in flagged


def test_highlight_and_suggested_fix_use_full_ligature_token() -> None:
    word = "ﬂocculator"
    line = "Results for ﬂocculator design and Mixing Methods"
    box = estimate_word_bbox_in_line_bbox((100.0, 200.0, 500.0, 212.0), line, word)
    assert box is not None
    # The estimated box must cover the ligature token, not a later ASCII fragment.
    assert box[0] < 100.0 + (line.index(word) + len(word)) * (
        400.0 / max(len(line), 1)
    )
    fix = p020_short_suggested_fix(
        word,
        "Flocculator",
        line,
        source="heading",
    )
    assert "ﬂocculator" in fix or "Flocculator" in fix
    assert "cation" not in fix
