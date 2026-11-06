"""Original approved cases; opt in with an external private source manifest.

No manuscript text or binaries are checked in. Synthetic equivalents run in CI.
"""

from __future__ import annotations

import hashlib
import json
import os
from functools import cache
from pathlib import Path

import pytest

from njit_auditor.audit_runner import run_pdf_audit_full
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view


@cache
def _report(sample):
    manifest = os.environ.get("NJIT_ESTER_AUDIT_SOURCE_MANIFEST")
    if not manifest:
        pytest.skip("external approved audit source manifest not supplied")
    sources = json.loads(Path(manifest).read_text())["documents"]
    source = next(d for d in sources if d["sample_id"] == sample)
    path = Path(source["path"])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]
    errors = []
    findings = run_pdf_audit_full(path, check_failures=errors)
    assert not errors
    return audit_findings_to_json_dict(findings, {"audit_type": "pdf"})


CASES = [
    ("F-051e2561b5c1", "SAMPLE-02", "P019", 7, "missing_page_number", None, False),
    (
        "F-2a0c546f998d",
        "SAMPLE-02",
        "P029",
        8,
        "roman_sequence_gap",
        "317.1,753.2,331.7,765.2",
        False,
    ),
    (
        "F-ad0e0ddf527a",
        "SAMPLE-03",
        "P024",
        12,
        "toc_level_capitalization",
        "124.7,717.9,540.4,729.9",
        True,
    ),
    (
        "F-7e684a2a9404",
        "SAMPLE-06",
        "P024",
        10,
        "toc_level_capitalization",
        "151.3,474.0,540.0,485.9",
        True,
    ),
    (
        "F-603134269bd1",
        "SAMPLE-06",
        "P027",
        52,
        "level3_sentence_case_issue",
        "108.0,143.0,541.4,155.0",
        True,
    ),
    (
        "F-495c66199a9e",
        "SAMPLE-06",
        "P086",
        35,
        "bold_heading_without_section_number",
        "108.0,406.1,268.9,418.0",
        True,
    ),
    (
        "F-b2293de2972c",
        "SAMPLE-07",
        "P024",
        10,
        "toc_level_capitalization",
        "151.3,474.0,540.0,485.9",
        True,
    ),
    (
        "F-ba49e3345087",
        "SAMPLE-07",
        "P027",
        52,
        "level3_sentence_case_issue",
        "108.0,143.0,541.4,155.0",
        True,
    ),
    (
        "F-d4fd6820b0be",
        "SAMPLE-07",
        "P086",
        35,
        "bold_heading_without_section_number",
        "108.0,406.1,268.9,418.0",
        True,
    ),
    ("F-3d28339bf765", "SAMPLE-08", "P019", None, "mixed_numbering_style", None, False),
    (
        "F-e02cc74a3ee2",
        "SAMPLE-08",
        "P024",
        12,
        "toc_level_capitalization",
        "151.3,710.6,541.9,724.2",
        True,
    ),
    (
        "F-b42d1ce7583c",
        "SAMPLE-08",
        "P027",
        40,
        "level4_sentence_case_or_punctuation_issue",
        "108.0,211.4,543.2,225.1",
        False,
    ),
    (
        "F-509959e93190",
        "SAMPLE-08",
        "P029",
        7,
        "roman_sequence_repeat",
        "314.8,745.0,333.6,758.6",
        True,
    ),
    (
        "F-35f11d967136",
        "SAMPLE-08",
        "P037",
        6,
        "roman_bio_sketch_not_iv",
        "314.8,745.0,333.6,758.6",
        True,
    ),
    (
        "F-72c90ccf90e5",
        "SAMPLE-11",
        "P024",
        14,
        "list_of_tables_title_case",
        "108.0,431.8,540.0,443.8",
        True,
    ),
    (
        "F-031f4740928d",
        "SAMPLE-11",
        "P027",
        42,
        "level4_sentence_case_or_punctuation_issue",
        "108.0,604.4,309.3,616.4",
        True,
    ),
    (
        "F-b81c303c0a1d",
        "SAMPLE-12",
        "P024",
        11,
        "toc_level_capitalization",
        "151.3,639.3,540.0,651.2",
        True,
    ),
    (
        "F-c647088fa37c",
        "SAMPLE-12",
        "P027",
        46,
        "level3_sentence_case_issue",
        "108.0,501.7,489.1,513.6",
        True,
    ),
    (
        "F-c44f06ea476c",
        "SAMPLE-14",
        "P024",
        17,
        "list_of_tables_title_case",
        "108.4,145.1,540.4,159.7",
        False,
    ),
    (
        "F-9f0995a31197",
        "SAMPLE-17",
        "P018",
        12,
        "wrapped_title_continuation_misaligned",
        "126.0,652.2,551.4,679.3",
        True,
    ),
]


def _overlaps(raw, expected):
    if not expected:
        return True
    if not raw:
        return False
    a, b = [float(v) for v in raw.split(",")], [float(v) for v in expected.split(",")]
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


@pytest.mark.parametrize("case_id,sample,rule,page,issue,box,expected", CASES)
def test_original_feedback_target_and_retained_positive_controls(
    case_id,
    sample,
    rule,
    page,
    issue,
    box,
    expected,
):
    raw = _report(sample)
    matched = [
        (i, f)
        for i, f in enumerate(raw["findings"])
        if f["rule_id"] == rule
        and f["page"] == page
        and f["details"].get("issue_type") == issue
        and _overlaps(f["details"].get("bbox"), box)
    ]
    assert bool(matched) is expected, case_id
    if expected:
        ids = {f"f{i}" for i, _ in matched}
        assert any(f.finding_id in ids for f in build_report_view(raw).findings)


@pytest.mark.parametrize(
    "sample,rule,page,issue",
    [
        ("SAMPLE-17", "P039", 11, "toc_l3_not_indented_relative_to_l2"),
        ("SAMPLE-16", "P040", 15, "lof_entry_missing_terminal_punctuation"),
        ("SAMPLE-15", "P045", 5, "biosketch_publication_wrapped_line_spacing_not_single"),
    ],
)
def test_original_confirmed_violation_has_explicit_medium_confidence(sample, rule, page, issue):
    matched = [
        f
        for f in _report(sample)["findings"]
        if f["rule_id"] == rule and f["page"] == page and f["details"].get("issue_type") == issue
    ]
    assert matched
    assert all(f["details"]["confidence"] == "medium" for f in matched)
