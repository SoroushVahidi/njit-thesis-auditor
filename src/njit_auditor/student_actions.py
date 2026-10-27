"""Conservative, web-only edits to existing correction text.

Never truncate an instruction or discard an unrecognised clause. The original
correction remains available in the card's optional explanation and exports.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

# Exact replacements keep unknown/dynamic detector advice intact. Each pair
# preserves the original action and its constraints, rather than guessing policy.
# fmt: off
_SHORT_ACTIONS = {
    (
        "Single-space the wrapped lines within this heading. Keep the normal spacing "
        "between the heading and the body paragraph."
    ): (
        "Single-space this heading's wrapped lines, keeping normal spacing before "
        "the body."
    ),
    (
        "Center this heading within the text area. Keep it bold and in all capital "
        "letters."
    ): (
        "Center this heading within the text area, in bold capital letters."
    ),
    (
        "Start the second line directly under the first word of the title text, not "
        "under the section number and not indented past it."
    ): (
        "Start the second line directly under the title's first word, not its "
        "section number."
    ),
    (
        "Start the second line of this wrapped title directly under the first word "
        "of the title, not under the section number and not indented past the title "
        "text."
    ): (
        "Start the second line directly under the title's first word, not its "
        "section number."
    ),
    (
        "Begin this List of Tables entry with the word 'Table' before its number "
        "(for example, Table 1.1)."
    ): (
        "Add 'Table' before this entry's number (for example, Table 1.1)."
    ),
    (
        "Begin this List of Figures entry with the word 'Figure' before its number "
        "(for example, Figure 1.1)."
    ): (
        "Add 'Figure' before this entry's number (for example, Figure 1.1)."
    ),
    (
        "Remove the number or label (such as [1] or 1.) in front of each publication "
        "or presentation entry. Keep the same citation format as the References "
        "section, just without the number."
    ): (
        "Remove each publication or presentation entry's number, keeping the "
        "References citation format."
    ),
    (
        "Remove any visible page number from the Abstract, Title, Approval, or "
        "Copyright page. These pages must not display a page number per NJIT "
        "formatting guidelines."
    ): (
        "Hide page numbers on the Abstract, Title, Approval, and Copyright pages."
    ),
    (
        "Shorten the abstract to within the applicable limit. PhD: ≤400 words. MS: "
        "≤200 words."
    ): (
        "Shorten the abstract to 400 words or fewer (PhD) or 200 words or fewer (MS)."
    ),
    (
        "Add the required column headers directly below the list heading: \"Table\" or "
        "\"Figure\" on the left and \"Page\" on the right."
    ): (
        "Add 'Table' or 'Figure' on the left and 'Page' on the right, below the list "
        "heading."
    ),
    (
        "Single-space wrapped TOC, List of Tables, and List of Figures entries so "
        "continuation lines stay within the same entry without extra blank space."
    ): (
        "Single-space each wrapped TOC or list entry without blank lines inside it."
    ),
}
# fmt: on


# Match both rule and subtype: neighbouring findings must keep their own advice.
_SUBTYPE_ACTIONS = {
    ("P027", "level2_title_case_issue"): (
        "Check whether this level-2 heading needs title case: "
        "capitalize the first word and major words."
    ),
    ("P027", "level4_sentence_case_or_punctuation_issue"): (
        "Check whether this level-4 heading needs a final period."
    ),
    ("P063", "single_appendix_uses_letter_label"): (
        "If this is the only appendix, remove its letter and use APPENDIX followed by the title."
    ),
    ("P064", "references_entry_indentation_inconsistent"): (
        "If these reference entries mix indentation styles, use one style consistently, "
        "following the style agreed with your advisor."
    ),
    ("P065", "dedication_text_not_centered"): (
        "Check whether the dedication text is centered within the text area."
    ),
    ("P065", "dedication_text_not_italic"): (
        "Check whether the dedication text uses an italic or oblique font."
    ),
    ("P067", "biosketch_publication_order_suspicious"): (
        "Check the publication years, then order entries from newest to oldest if needed."
    ),
}


def short_student_action(
    finding: Mapping[str, Any], original: str, *, details: Mapping[str, Any] | None = None
) -> str:
    """Shorten reviewed phrases, preserve evidence, and qualify uncertain advice."""
    text = " ".join(original.split())
    key = (str(finding.get("rule_id", "")), str(finding.get("issue_type", "")))
    if key == ("P027", "level1_not_all_caps"):
        preview = str((details or {}).get("line_preview", "")).lstrip()
        role = "level-1"
        if re.match(r"APPENDIX\b", preview, re.I):
            role = "appendix"
        elif re.match(r"CHAPTER\b", preview, re.I):
            role = "chapter"
        text = f"Check whether this {role} heading should be in ALL CAPITALS."
    else:
        text = _SUBTYPE_ACTIONS.get(key, text)
    # This reference is background, not part of the punctuation correction.
    text = re.sub(
        r"; their capitalization is checked under R024E\.{1,4}",
        ".",
        text,
    )
    text = _SHORT_ACTIONS.get(text, text)
    # The generic caption advice is longer than the issue-specific alternatives.
    if text == (
        "For figure captions: use sentence case (only first word and proper nouns "
        "capitalized) and end with a period. List of Figures entries end with a period."
    ):
        text = (
            "Use sentence case for figure captions (first word and proper nouns capitalized), "
            "ending captions and List of Figures entries with a period."
        )
    # Combine the existing caption-placement constraints without losing either.
    text = re.sub(r"\. Keep the (figure image|caption and table rows)", r", keeping the \1", text)
    uncertain = str(
        finding.get("confidence_level") or finding.get("confidence") or "low"
    ).lower() in {
        "low",
        "medium",
    } or "possible" in str(finding.get("issue_type", ""))
    # Qualification must govern the opening action. A later "may" in
    # unrelated background cannot qualify an imperative such as "Reorder".
    qualified = re.match(r"^(check|review|verify|confirm|if)\b", text, re.I)
    if text and uncertain and not qualified:
        if re.match(
            r"^(Add|Align|Apply|Begin|Center|Change|Correct|Delete|Edit|Format|Hide|Indent|"
            r"Keep|Make|Move|Number|Order|Place|Remove|Rename|Renumber|Reorder|Replace|"
            r"Resolve|Rewrite|Set|Shorten|Single-space|Start|Use)\b",
            text,
        ):
            text = "Check whether to " + text[0].lower() + text[1:]
        else:
            text = "Review this suggestion: " + text
    return text
