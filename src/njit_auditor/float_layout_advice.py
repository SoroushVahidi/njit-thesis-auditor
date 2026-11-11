"""Shared R035 actions using only the affected object's recorded identity."""

from __future__ import annotations


def float_layout_suggested_fix(issue_type: str, float_number: str = "") -> str:
    """Keep subtype, terminology and any supplied number together across outputs.

    Never infer identity from another object or from prose. An absent number
    retains the object-specific generic action.
    """
    number = float_number.strip()
    table = f"Table {number}" if number else "the table"
    figure = f"Figure {number}" if number else "the figure"
    table_title = f"the table title for Table {number}" if number else "the table title"
    description = (
        f"the figure description for Figure {number}" if number else "the figure description"
    )
    return {
        "table_body_not_centered": f"Center {table} within the page margins.",
        "figure_body_not_centered": f"Center {figure} within the page margins.",
        "table_caption_not_above_body": f"Place {table_title} above the table body.",
        "figure_caption_not_below_body": f"Place {description} below the figure body.",
    }.get(issue_type, "")
