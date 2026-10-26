"""Evidence-limited wording for the web UI's student finding cards."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from typing import Any

from njit_auditor.report_outputs import category_display_label
from njit_auditor.rules.pdf_margins import (
    BOTTOM_MARGIN_PT,
    INCH_TO_PT,
    LEFT_MARGIN_PT,
    RIGHT_MARGIN_PT,
    TOP_MARGIN_PT,
)
from njit_auditor.student_actions import short_student_action


def topic_label(finding: Mapping[str, Any]) -> str:
    if str(finding.get("rule_id", "")) == "P011":
        return "MARGINS"
    return category_display_label(str(finding.get("category", ""))).upper()


def _margin_side(details: Mapping[str, Any]) -> str:
    side = str(details.get("side", ""))
    return (
        side.removesuffix("_margin")
        if side in {"left_margin", "right_margin", "top_margin", "bottom_margin"}
        else ""
    )


def issue_summary(finding: Mapping[str, Any], details: Mapping[str, Any]) -> str:
    """Use a measurement only when the detector supplied a valid one."""
    if str(finding.get("rule_id", "")) == "P011":
        side = _margin_side(details)
        try:
            overflow = float(details.get("worst_overflow_pt", ""))
        except (TypeError, ValueError):
            overflow = 0.0
        if side and math.isfinite(overflow) and overflow > 0:
            return f"{side.capitalize()} margin — approximately {overflow:.1f} pt over"
    label = str(finding.get("issue_type_label") or "").strip()
    if label:
        return label
    # Older in-memory jobs may have only the detector's issue type. Keep that
    # short, factual description instead of replacing it with a generic prompt.
    issue_type = str(finding.get("issue_type") or "").strip()
    return issue_type.replace("_", " ") if issue_type else "Review this finding"


def margin_questions(
    finding: Mapping[str, Any], details: Mapping[str, Any]
) -> list[tuple[str, str]]:
    """A warning proves its own crossing; other margins remain unverified."""
    if str(finding.get("rule_id", "")) != "P011":
        return []
    side = _margin_side(details)
    landscape = details.get("page_orientation") == "landscape"
    if landscape:
        binding = str(details.get("binding_edge", ""))
        first = (
            f"Is the {binding} binding margin {LEFT_MARGIN_PT / INCH_TO_PT:g} inches?"
            if binding in {"top", "bottom", "left", "right"}
            else "Is the binding margin correct?"
        )
        # The rotated binding edge may be known, but this finding never measures
        # the document's margin setting. Only a detected crossing can be "No".
        questions = [
            (first, "Needs review"),
            (
                f"Are the other three margins {RIGHT_MARGIN_PT / INCH_TO_PT:g} inch?",
                "Needs review",
            ),
        ]
    else:
        questions = [
            (f"Is the left margin {LEFT_MARGIN_PT / INCH_TO_PT:g} inches?", "Needs review"),
            (
                f"Are the top, bottom, and right margins {TOP_MARGIN_PT / INCH_TO_PT:g} inch?",
                "Needs review",
            ),
        ]
        # These constants are expected to match; do not silently show a wrong
        # combined requirement if the canonical detector values ever diverge.
        if not (TOP_MARGIN_PT == BOTTOM_MARGIN_PT == RIGHT_MARGIN_PT):
            questions[1] = ("Are the top, bottom, and right margins set correctly?", "Needs review")
    questions.append(
        ("Is all text within the required margins on this page?", "No" if side else "Needs review")
    )
    return questions


def student_card_fields(finding: Mapping[str, Any], details: Mapping[str, Any]) -> dict[str, Any]:
    location = str(finding.get("location_label", "")).strip()
    page = finding.get("page")
    if page is not None:
        location = re.sub(
            rf"^Page {re.escape(str(page))}(?:\s*[—–-]\s*|\s*$)",
            "",
            location,
            count=1,
            flags=re.IGNORECASE,
        )
    if str(finding.get("rule_id", "")) == "P011" and re.fullmatch(
        r"(?:left|right|top|bottom) margin(?: \(~[\d.]+ pt over\))?",
        location,
        flags=re.IGNORECASE,
    ):
        location = ""
    original_action = str(finding.get("suggested_fix") or "").strip()
    report_action = ""
    if str(finding.get("rule_id", "")) == "P011" and (side := _margin_side(details)):
        report_action = f"Move the flagged text inside the {side} margin."
    return {
        "student_topic": topic_label(finding),
        "student_summary": issue_summary(finding, details),
        # Reports already consume student_action; preserve its baseline value.
        "student_action": report_action,
        "student_web_action": short_student_action(finding, report_action or original_action),
        "margin_questions": margin_questions(finding, details),
        "student_location": location,
    }
