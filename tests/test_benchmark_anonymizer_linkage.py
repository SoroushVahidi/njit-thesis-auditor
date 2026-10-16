"""Checks for the synthetic candidate-original attack scoring contract."""

from scripts.benchmark_anonymizer_linkage import _distance, _topk_expected


def test_geometry_attack_never_requires_replacement_text() -> None:
    geometry = {
        "dimensions": [(612, 792)],
        "layout": [(0, 108, 165, 12, "Helvetica")],
        "right": [202.0],
        "heading": [(0, 108, 105)],
    }
    candidate = {**geometry, "word_lengths": [(5, 8, 6)]}
    assert _distance(geometry, candidate, "line_geometry") == 0
    assert _distance(geometry, candidate, "page") == 0


def test_candidate_ties_get_fractional_credit() -> None:
    distances = [(7, 0.0), (3, 0.0), (9, 0.0), (1, 0.0)]
    assert _topk_expected(distances, truth=7, k=1) == 0.25
    assert _topk_expected(distances, truth=7, k=3) == 0.75
