"""Helpers for converting LaTeX snippets into plain text safely."""

from __future__ import annotations

import re

try:
    from pylatexenc.latex2text import LatexNodes2Text
except Exception:  # pragma: no cover - fallback path if import fails
    LatexNodes2Text = None


def _fallback_strip_latex_to_text(latex: str) -> str:
    text = latex
    # Keep argument text for common single-argument macros.
    text = re.sub(r"\\[a-zA-Z]+\*?\s*\{([^{}]*)\}", r"\1", text)
    # Drop remaining simple macros.
    text = re.sub(r"\\[a-zA-Z@]+", " ", text)
    # Remove braces and leftover escape characters.
    text = text.replace("{", " ").replace("}", " ").replace("\\", " ")
    # Normalize whitespace.
    text = re.sub(r"\s+", " ", text).strip()
    return text


def strip_latex_to_text(latex: str) -> str:
    """Convert LaTeX text to readable plain text without raising parsing errors."""

    if LatexNodes2Text is None:
        return _fallback_strip_latex_to_text(latex)

    try:
        return LatexNodes2Text().latex_to_text(latex)
    except Exception:
        return _fallback_strip_latex_to_text(latex)
