"""Evidence-limited student wording; never changes detector findings or raw details."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

from njit_auditor.report_outputs import category_display_label
from njit_auditor.rules.pdf_margins import INCH_TO_PT, LEFT_MARGIN_PT, RIGHT_MARGIN_PT

CONFIDENCE_NOTE = "Confidence describes how sure the tool is about its detection, not severity."
MARGIN_SETTINGS_NOTE = (
    "PDF text positions do not establish the margin settings in your source document."
)
STUDENT_FIELDS = (
    "student_topic",
    "student_summary",
    "student_fix",
    "student_note",
    "margin_questions",
    "check_yourself",
    "technical_details",
    "student_location",
)


def topic_label(finding: Mapping[str, Any]) -> str:
    if str(finding.get("rule_id", "")) == "P011":
        return "MARGINS"
    return category_display_label(str(finding.get("category", ""))).upper()


def plain_student_text(text: str) -> str:
    """Remove repeated labels, retaining the evidence and its uncertainty words."""
    return re.sub(r"^(?:(?:Review needed|Likely problem|Problem):\s*)+", "", text).strip()


def _margin_side(details: Mapping[str, Any]) -> str:
    side = str(details.get("side", "")).strip()
    return (
        side.removesuffix("_margin")
        if side
        in {
            "left_margin",
            "right_margin",
            "top_margin",
            "bottom_margin",
        }
        else ""
    )


def _measured_overflow(details: Mapping[str, Any]) -> float | None:
    try:
        value = float(details.get("worst_overflow_pt", ""))
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) and value > 0 else None


def margin_self_checks(details: Mapping[str, Any]) -> list[tuple[str, str]]:
    if details.get("page_orientation") == "landscape":
        edge = str(details.get("binding_edge", ""))
        binding = f"{edge} binding edge" if edge in {"top", "bottom"} else "binding edge"
        checks = [
            (
                "Are the landscape-page margins set correctly?",
                f"In the source document, check the {LEFT_MARGIN_PT / INCH_TO_PT:g}-inch "
                f"margin at the {binding} and {RIGHT_MARGIN_PT / INCH_TO_PT:g} inch "
                "at the other edges. Confirm which edge is bound.",
            ),
        ]
    else:
        checks = [
            (
                f"Is the left margin set to {LEFT_MARGIN_PT / INCH_TO_PT:g} inches?",
                "Open page setup in your source document and check the left margin.",
            ),
            (
                f"Are the top, bottom, and right margins set to {RIGHT_MARGIN_PT / INCH_TO_PT:g} "
                "inch?",
                "Check those three settings in your source document.",
            ),
        ]
    return checks


def margin_presentation(
    details: Mapping[str, Any],
    observations: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    observations = observations if observations is not None else [details]
    measured = [(item, _margin_side(item), _measured_overflow(item)) for item in observations]
    known = [(item, side, value) for item, side, value in measured if side and value is not None]
    summary = []
    answers = []
    technical = []
    for item, side, value in known:
        assert value is not None
        inches = value / INCH_TO_PT
        distance = f"about {inches:.2f} inch" if inches >= 0.01 else "less than 0.01 inch"
        summary.append(f"Text appears to extend {distance} past the {side} margin boundary.")
        answers.append((f"Did the check detect text crossing the {side} margin?", "Yes"))
        technical.append((f"Detected {side} overflow", f"{item['worst_overflow_pt']} pt"))
    checks = margin_self_checks(details)
    if len(known) != len(measured) or not known:
        checks.append(
            (
                "Does any marked text cross a required margin?",
                "Open the marked page and compare the text with the required margin "
                "boundary. The stored evidence does not establish the edge or distance.",
            )
        )
    sides = list(dict.fromkeys(side for _, side, _ in known))
    target = " and ".join(sides) + (" margin boundaries" if len(sides) > 1 else " margin boundary")
    if not sides:
        target = "required margin boundary"
    kind = str(details.get("margin_content_kind", ""))
    action = {
        "table_layout": "wrap the marked table text or adjust its column width",
        "figure_layout": "adjust the marked caption text or its position",
        "code_listing": "wrap the long line or reduce the listing width",
        "references_hanging_indent": "check the reference indentation and wrap long URLs",
        "toc_entry": "check the entry's tab stops, leaders, and indentation",
        "approval_date_layout": "move or shorten the date/signature line",
    }.get(kind, "adjust that text's wrapping, indentation, or position")
    fix = f"Compare the marked text with the {target}. If it crosses the boundary, {action}."
    return {
        "student_summary": " ".join(dict.fromkeys(summary))
        or "The check flagged a possible text crossing near a margin.",
        "student_fix": fix,
        "margin_questions": list(dict.fromkeys(answers)),
        "check_yourself": checks,
        "technical_details": list(dict.fromkeys(technical)),
        "student_note": MARGIN_SETTINGS_NOTE,
    }


def student_fix(finding: Mapping[str, Any]) -> str:
    if "student_fix" in finding:
        return str(finding["student_fix"])
    if str(finding.get("rule_id", "")) == "P011":
        details = finding.get("details", {})
        return str(
            margin_presentation(details if isinstance(details, Mapping) else {})["student_fix"]
        )
    fix = plain_student_text(str(finding.get("suggested_fix", "")))
    raw = finding.get("details", {})
    confidence = finding.get("confidence_level") or finding.get("confidence")
    if not confidence and isinstance(raw, Mapping):
        confidence = raw.get("confidence")
    if confidence in {"low", "medium"} and re.match(
        r"^(?:Add|Remove|Set|Use|Replace|Move|Change|Format|Convert|Apply|Correct|Include)\b", fix
    ):
        return "If confirmed, " + fix[0].lower() + fix[1:]
    return fix


def student_card_fields(
    finding: Mapping[str, Any],
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if details is None and all(key in finding for key in STUDENT_FIELDS):
        return {key: finding[key] for key in STUDENT_FIELDS if key in finding}
    raw = details if details is not None else finding.get("details", {})
    raw = raw if isinstance(raw, Mapping) else {}
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
    label = str(
        finding.get("issue_type_label")
        or finding.get("issue_type")
        or raw.get("issue_type")
        or "Review this finding"
    ).replace("_", " ")
    confidence = (
        finding.get("confidence_level") or finding.get("confidence") or raw.get("confidence")
    )
    if confidence in {"low", "medium"} and not label.endswith("?") and not re.match(
        r"^(?:Possible|Check|Review|May)\b", label, re.IGNORECASE
    ):
        label = "Possible issue: " + label
    fields = {
        "student_topic": topic_label(finding),
        "student_summary": label,
        "student_fix": student_fix({**finding, "details": raw}),
        "student_note": plain_student_text(str(finding.get("polished_comment", ""))),
        "margin_questions": [],
        "check_yourself": [],
        "technical_details": [],
        "student_location": location,
    }
    if str(finding.get("rule_id", "")) == "P011":
        observations = raw.get("_margin_observations")
        fields.update(margin_presentation(raw, observations))
        if re.fullmatch(
            r"(?:left|right|top|bottom) margin(?: \(~[\d.]+ pt over\))?",
            location,
            flags=re.IGNORECASE,
        ):
            fields["student_location"] = ""
    return fields


def finding_check_lines(fields: Mapping[str, Any]) -> list[str]:
    """Shared text/Markdown/PDF checklist wording; unknowns have no answer field."""
    lines = [f"{question} {answer}" for question, answer in fields.get("margin_questions", [])]
    if fields.get("check_yourself"):
        lines.append("Check yourself (not answered by the tool):")
        lines.append(str(fields["student_note"]))
        lines.extend(
            f"{question} {instruction}" for question, instruction in fields["check_yourself"]
        )
    return lines
