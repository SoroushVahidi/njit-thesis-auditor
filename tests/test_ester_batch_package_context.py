"""Tests for concise Ester-package context derived from live findings."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "ester_batch"))

from build_rule_package import _fallback_affected_lines  # noqa: E402


def test_r036_package_context_names_both_entries() -> None:
    details = {
        "issue_type": "toc_inter_entry_spacing_too_tight",
        "previous_entry_preview": "Previous title",
        "next_entry_preview": "Next title",
    }

    assert _fallback_affected_lines(details) == [
        "Previous entry: Previous title",
        "Next entry: Next title",
    ]


def test_other_rules_do_not_gain_synthetic_context() -> None:
    assert _fallback_affected_lines(
        {
            "issue_type": "some_other_issue",
            "previous_entry_preview": "Previous title",
            "next_entry_preview": "Next title",
        }
    ) == []
