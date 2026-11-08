"""Synthetic controls for periods on geometrically spaced run-in headings."""

from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.pdf_models import (
    BBox,
    PdfDocument,
    PdfPage,
    PdfTextBlock,
    PdfTextLine,
    PdfTextSpan,
)
from njit_auditor.rules.pdf_heading_levels import check_pdf_heading_level_styles


def _document(
    number: str,
    title: str,
    *,
    split_number: bool = True,
    tail: str = "ordinary text continues on this row",
    tail_italic: bool = False,
) -> PdfDocument:
    x = 108.0
    spans: list[PdfTextSpan] = []
    for word in [number, *title.split()]:
        width = 4.0 * len(word)
        spans.append(
            PdfTextSpan(
                text=word,
                font="Times-Bold",
                size=12,
                bold=True,
                bbox=BBox(x0=x, y0=300, x1=x + width, y1=312),
            )
        )
        x += width + 5.0
    if tail:
        spans.append(
            PdfTextSpan(
                text=tail,
                font="Times-Italic" if tail_italic else "Times-Roman",
                size=12,
                bold=False,
                italic=tail_italic,
                bbox=BBox(x0=x, y0=300, x1=x + 4.0 * len(tail), y1=312),
            )
        )

    def line(parts: list[PdfTextSpan], text: str) -> PdfTextLine:
        return PdfTextLine(
            text=text,
            spans=parts,
            bbox=BBox(x0=parts[0].bbox.x0, y0=300, x1=parts[-1].bbox.x1, y1=312),
        )

    if split_number:
        lines = [line(spans[:1], number), line(spans[1:], "".join(s.text for s in spans[1:]))]
    else:
        lines = [line(spans, f"{number} {title} {tail}".strip())]
    blocks = [PdfTextBlock(text=ln.text, bbox=ln.bbox, lines=[ln]) for ln in lines]
    return PdfDocument(
        path="synthetic-run-in.pdf",
        pages=[PdfPage(page_number=5, width=612, height=792, text_blocks=blocks)],
    )


def _issues(doc: PdfDocument) -> list[str]:
    return [f.details["issue_type"] for f in check_pdf_heading_level_styles(doc)]


def _continued_title(
    number: str,
    continuation: str,
    *,
    split_number: bool,
    packed_prefix: bool = False,
    body: str = "",
    whitespace: str = " ",
) -> PdfDocument:
    doc = _document(number, "Synthetic heading e.g.", tail=continuation, split_number=split_number)
    line = doc.pages[0].text_blocks[-1].lines[0]
    if packed_prefix:
        prefix = line.spans[:-1]
        line.spans[:-1] = [
            PdfTextSpan(
                text=("" if split_number else number + " ") + "Synthetic heading e.g.",
                font="Times-Bold",
                size=12,
                bold=True,
                bbox=BBox(x0=prefix[0].bbox.x0, y0=300, x1=prefix[-1].bbox.x1, y1=312),
            )
        ]
    tail = line.spans[-1]
    tail.bold = True
    tail.font = "Times-Bold"
    line.spans.insert(
        -1,
        PdfTextSpan(
            text=whitespace,
            font="Times-Roman",
            size=12,
            bbox=BBox(x0=line.spans[-2].bbox.x1, y0=300, x1=tail.bbox.x0, y1=312),
        ),
    )
    if body:
        line.spans.append(
            PdfTextSpan(
                text=body,
                font="Times-Roman",
                size=12,
                bbox=BBox(x0=tail.bbox.x1 + 5, y0=300, x1=tail.bbox.x1 + 5 + 4 * len(body), y1=312),
            )
        )
        line.text += " " + body
        line.bbox.x1 = line.spans[-1].bbox.x1
    return doc


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
@pytest.mark.parametrize("split_number", [False, True])
@pytest.mark.parametrize("packed_prefix", [False, True])
def test_regular_whitespace_does_not_end_a_bold_heading(
    number: str,
    split_number: bool,
    packed_prefix: bool,
) -> None:
    issues = _issues(
        _continued_title(
            number,
            "continued heading",
            split_number=split_number,
            packed_prefix=packed_prefix,
        )
    )
    assert any("punctuation" in issue for issue in issues)


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
@pytest.mark.parametrize("split_number", [False, True])
@pytest.mark.parametrize("packed_prefix", [False, True])
@pytest.mark.parametrize("terminal_period", [False, True])
@pytest.mark.parametrize("whitespace", [" ", "\u00a0", "\t"])
def test_only_the_complete_bold_title_controls_the_period_before_body(
    number: str,
    split_number: bool,
    packed_prefix: bool,
    terminal_period: bool,
    whitespace: str,
) -> None:
    continuation = "continued heading" + ("." if terminal_period else "")
    issues = _issues(
        _continued_title(
            number,
            continuation,
            split_number=split_number,
            whitespace=whitespace,
            packed_prefix=packed_prefix,
            body="ordinary paragraph body continues here",
        )
    )
    assert any("punctuation" in issue for issue in issues) is not terminal_period


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
def test_body_emphasis_does_not_extend_the_completed_heading(number: str) -> None:
    doc = _continued_title(
        number,
        "continued heading.",
        split_number=True,
        body="ordinary paragraph body continues here",
    )
    line = doc.pages[0].text_blocks[-1].lines[0]
    line.spans.append(
        PdfTextSpan(
            text="emphasized body words",
            font="Times-Bold",
            size=12,
            bold=True,
            bbox=BBox(x0=line.bbox.x1 + 5, y0=300, x1=line.bbox.x1 + 100, y1=312),
        )
    )
    line.text += " emphasized body words"
    line.bbox.x1 = line.spans[-1].bbox.x1
    assert not any("punctuation" in issue for issue in _issues(doc))


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
@pytest.mark.parametrize("split_number", [False, True])
def test_existing_heading_period_before_regular_body_is_not_missing(
    number: str,
    split_number: bool,
) -> None:
    assert not any(
        "punctuation" in issue
        for issue in _issues(
            _document(number, "Synthetic heading boundary.", split_number=split_number)
        )
    )


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
@pytest.mark.parametrize("split_number", [False, True])
def test_genuine_missing_heading_period_still_warns(number: str, split_number: bool) -> None:
    assert any(
        "punctuation" in issue
        for issue in _issues(
            _document(number, "Synthetic heading boundary", split_number=split_number)
        )
    )


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
def test_colon_ended_heading_still_requires_period(number: str) -> None:
    assert any(
        "punctuation" in issue
        for issue in _issues(_document(number, "Synthetic heading boundary:"))
    )


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
def test_heading_case_warning_is_preserved_independently(number: str) -> None:
    issues = _issues(_document(number, "Synthetic Heading Boundary."))
    assert any(issue.endswith("_sentence_case_issue") for issue in issues)
    assert not any("punctuation" in issue for issue in issues)


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
def test_period_before_italic_heading_continuation_is_not_a_run_in_boundary(number: str) -> None:
    assert any(
        "punctuation" in issue
        for issue in _issues(
            _document(number, "Synthetic heading e.g.", tail="variable", tail_italic=True)
        )
    )


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
def test_period_before_single_math_symbol_is_not_a_run_in_boundary(number: str) -> None:
    assert any(
        "punctuation" in issue
        for issue in _issues(_document(number, "Synthetic heading e.g.", tail="x"))
    )


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
def test_fully_bold_heading_with_period_remains_valid(number: str) -> None:
    assert not any(
        "punctuation" in issue
        for issue in _issues(_document(number, "Synthetic heading boundary.", tail=""))
    )


@pytest.mark.parametrize("numbered", [False, True])
def test_run_in_heading_keeps_numbered_and_unnumbered_rule_ownership(numbered: bool) -> None:
    from test_p086_unnumbered_bold_heading import (
        _block,
        _doc,
        _following_body,
        _page,
        _run_in_row,
    )

    from njit_auditor.rules.pdf_unnumbered_bold_heading import check_pdf_unnumbered_bold_heading

    title = "Synthetic Comparison Discussion Heading"
    if numbered:
        title = "2.3.4.5 " + title
    lead, tail = _run_in_row(
        title, "continues in regular style on the same row", y0=220.0, y1=232.0
    )
    doc = _doc(_page(12, _block(lead, tail, *_following_body(244.0))))
    issues = _issues(doc)
    assert any("punctuation" in issue for issue in issues) is numbered
    if not numbered:
        assert issues == []  # R027 must not infer a level for an unnumbered phrase.
    assert bool(check_pdf_unnumbered_bold_heading(doc)) is not numbered


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6", ""])
@pytest.mark.parametrize(
    ("abbreviation", "expression"),
    [
        ("e.g.", "sin x + cos y"),
        ("e.g.", "log x + exp y"),
        ("i.e.", "f(x, y) + g(z)"),
        ("e.g.", "alpha = 1.5 + beta"),
    ],
)
@pytest.mark.parametrize("terminal_period", [False, True])
@pytest.mark.parametrize("italic", [False, True])
@pytest.mark.parametrize("capitalization_error", [False, True])
def test_generated_mathematical_heading_continuation(
    number: str,
    abbreviation: str,
    expression: str,
    terminal_period: bool,
    italic: bool,
    capitalization_error: bool,
    tmp_path: Path,
) -> None:
    # These include all 16 reviewer controls. The whole row is a heading;
    # an upright formula is not a paragraph merely because it contains letters.
    path = tmp_path / "math-heading.pdf"
    words = ("Synthetic Heading Boundary" if capitalization_error else "Synthetic heading").split()
    words.append(abbreviation)
    if number:
        words.insert(0, number)
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=612, height=792)
        x = 108.0
        for index, word in enumerate(words):
            page.insert_text((x, 300), word, fontname="tibo", fontsize=12)
            x += pymupdf.get_text_length(word, fontname="tibo", fontsize=12)
            x += 15 if number and index == 0 else 5
        page.insert_text(
            (x, 300),
            expression + ("." if terminal_period else ""),
            fontname="tiit" if italic else "tiro",
            fontsize=12,
        )
        pdf.save(path)
    issues = _issues(load_pdf_layout(str(path)))
    if not number:
        assert issues == []  # R027 must not take ownership of unnumbered headings.
        return
    level = len(number.split("."))
    expected = []
    if capitalization_error:
        expected.append(f"level{level}_sentence_case_issue")
    if not terminal_period:
        expected.append(f"level{level}_sentence_case_or_punctuation_issue")
    assert issues == expected


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
@pytest.mark.parametrize("split_number", [False, True])
@pytest.mark.parametrize("packed_prefix", [False, True])
@pytest.mark.parametrize("terminal_period", [False, True])
@pytest.mark.parametrize("expression", [
    "alpha + beta", "alpha + (beta * gamma)", "alpha = -1", "sin(x)",
])
def test_math_boundary_does_not_depend_on_literal_prefix_spaces(
    number: str, split_number: bool, packed_prefix: bool, terminal_period: bool, expression: str,
) -> None:
    doc = _document(
        number,
        "Synthetic heading e.g.",
        split_number=split_number,
        tail=expression + ("." if terminal_period else ""),
    )
    line = doc.pages[0].text_blocks[-1].lines[0]
    if packed_prefix:
        prefix = line.spans[:-1]
        line.spans[:-1] = [
            PdfTextSpan(
                text=("" if split_number else number + " ") + "Synthetic heading e.g.",
                font="Times-Bold",
                size=12,
                bold=True,
                bbox=BBox(x0=prefix[0].bbox.x0, y0=300, x1=prefix[-1].bbox.x1, y1=312),
            )
        ]
    level = len(number.split("."))
    assert _issues(doc) == (
        [] if terminal_period else [f"level{level}_sentence_case_or_punctuation_issue"]
    )


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
@pytest.mark.parametrize("terminal_period", [False, True])
@pytest.mark.parametrize(
    "body",
    [
        "Ordinary paragraph text follows here",
        "We compare alpha + beta in this paragraph",
        "The state-of-the-art method follows here",
        "The measured value is 1.5 in this paragraph",
        "For x > 0, the result increases",
        "Values alpha + beta are compared here",
    ],
)
def test_genuine_body_text_keeps_heading_punctuation_and_capitalization(
    number: str, terminal_period: bool, body: str
) -> None:
    # Operators, hyphens and decimal punctuation later in prose are not evidence
    # that the regular-font suffix starts with a mathematical heading continuation.
    doc = _document(
        number, "Synthetic Heading Boundary" + ("." if terminal_period else ""), tail=body
    )
    level = len(number.split("."))
    expected = [f"level{level}_sentence_case_issue"]
    if not terminal_period:
        expected.append(f"level{level}_sentence_case_or_punctuation_issue")
    assert _issues(doc) == expected


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
@pytest.mark.parametrize("split_number", [False, True])
def test_complete_heading_can_be_followed_by_expression_only_body(
    number: str, split_number: bool
) -> None:
    # Mathematical syntax alone cannot turn an ordinary terminal period into
    # an abbreviation's internal period. Keep this established body boundary.
    assert _issues(
        _document(
            number, "Synthetic heading boundary.", split_number=split_number, tail="alpha + beta"
        )
    ) == []


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
@pytest.mark.parametrize("terminal_period", [False, True])
@pytest.mark.parametrize("expression", [
    "alpha + (beta * gamma)",
    "alpha = -1",
    "sin(x)",
    "alpha = +1.5",
    "alpha = -.5",
    "-sin(x)",
    "f(x, g(y + 1))",
    "f(g(x)) + h(y)",
    "alpha * -(beta + gamma)",
    "alpha / (beta - gamma)",
    "(alpha + beta)^2",
    "alpha = (-1 + beta)",
    "alpha + [beta * {gamma + delta}]",
    "(+alpha)",
    "alpha >= -1",
    "f(x)**2 + g(y)",
])
def test_generated_grouped_unary_and_function_heading_continuations(
    tmp_path: Path, number: str, terminal_period: bool, expression: str,
) -> None:
    # Exercise real PDF extraction, including all six independently reproduced
    # false negatives and their genuinely period-terminated counterparts.
    test_generated_mathematical_heading_continuation(
        number, "e.g.", expression, terminal_period, False, False, tmp_path
    )


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
@pytest.mark.parametrize("split_number", [False, True])
@pytest.mark.parametrize("abbreviation", ["e.g.", "i.e."])
@pytest.mark.parametrize("body", [
    "Ordinary paragraph text follows here",
    "We compare alpha + beta in this paragraph",
    "The state-of-the-art method follows here",
    "The measured value is -1.5 in this paragraph",
    "For x > 0, the result increases",
    "Values alpha + beta are compared here",
    "The method (with grouping) follows here",
    "sin(x) is used in this paragraph",
    "alpha = -1 is the initial value",
    "ordinary paragraph",
    "(ordinary paragraph)",
])
def test_abbreviation_ending_before_prose_remains_a_valid_boundary(
    number: str, split_number: bool, abbreviation: str, body: str,
) -> None:
    assert _issues(_document(
        number, "Synthetic heading " + abbreviation, split_number=split_number, tail=body,
    )) == []


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
@pytest.mark.parametrize("expression", ["sin(x)", "alpha = -1", "alpha + (beta * gamma)"])
def test_grouped_formula_body_does_not_extend_a_completed_nonabbreviated_heading(
    number: str, expression: str,
) -> None:
    assert _issues(_document(number, "Synthetic heading boundary.", tail=expression)) == []


@pytest.mark.parametrize("text", [
    "alpha + (beta * gamma", "alpha + [beta)", "sin()", "sin(x,)",
    "alpha + beta prose continues", "alpha + .", "alpha =", "alpha beta gamma + delta",
    "state-of-the-art", "ordinary paragraph", "sin(x); prose", "sin(x)..",
    "(ordinary paragraph)", "method(ordinary paragraph)",
])
def test_incomplete_or_prose_suffix_is_not_certified_as_mathematics(text: str) -> None:
    from njit_auditor.rules.pdf_heading_levels import _period_precedes_math_continuation

    # Malformed syntax must not cause arbitrary prose to be absorbed as a title.
    assert not _period_precedes_math_continuation("Synthetic heading e.g.", text)


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
def test_abbreviation_at_end_of_heading_without_continuation_is_valid(number: str) -> None:
    assert _issues(_document(number, "Synthetic heading e.g.", tail="")) == []


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
@pytest.mark.parametrize("terminal_period", [False, True])
@pytest.mark.parametrize("expression", ["log 2 + alpha", "2 alpha + beta"])
def test_numeric_implicit_operand_regressions_through_pdf(
    tmp_path: Path, number: str, terminal_period: bool, expression: str,
) -> None:
    test_generated_mathematical_heading_continuation(
        number, "e.g.", expression, terminal_period, False, False, tmp_path,
    )


def _render_math_tree(tree):
    """Test-only notation grammar; no production tokenizer or matcher is used."""
    kind, *parts = tree
    if kind in {"identifier", "number"}:
        return parts[0]
    if kind == "unary":
        return parts[0] + _render_math_tree(parts[1])
    if kind == "binary":
        operator, left, right = parts
        return f"{_render_math_tree(left)} {operator} {_render_math_tree(right)}"
    if kind == "group":
        return "(" + _render_math_tree(parts[0]) + ")"
    if kind == "call":
        return parts[0] + "(" + ", ".join(map(_render_math_tree, parts[1])) + ")"
    if kind == "implicit":
        left, separator, right = parts
        return _render_math_tree(left) + separator + _render_math_tree(right)
    raise AssertionError(f"Unknown test grammar production: {kind}")


def _numeric_math_grammar_cases():
    """Bounded two-level derivations with independently known mathematical roles.

    Space-only atom pairs get a binary context: an isolated pair could be prose.
    Calls and coefficient/group juxtaposition also exercise standalone forms.
    Every generated row is a heading, so the period flag alone defines its
    expected punctuation result, independently of implementation recognition.
    """
    cases = set()
    omega = ("identifier", "omega")
    for name in ("alpha", "beta"):
        for literal in ("2", "1.5"):
            identifier = ("identifier", name)
            number = ("number", literal)
            addition = ("binary", "+", identifier, number)
            group = ("group", addition)
            call = ("call", "f", (identifier,))
            kernels = (
                addition,
                ("unary", "+", group),
                ("unary", "-", group),
                ("implicit", identifier, " ", number),
                ("implicit", number, " ", identifier),
                ("implicit", number, "", identifier),
                ("implicit", number, "", group),
                ("implicit", number, " ", call),
                ("call", "h", (group, ("call", "g", (number,)))),
                ("implicit", group, "", ("group", ("binary", "*", identifier, omega))),
            )
            for index, kernel in enumerate(kernels):
                operator = ("+", "-", "*", "/", "^", "=")[index % 6]
                root = ("binary", operator, kernel, omega)
                cases.add(_render_math_tree(root))
                cases.add(_render_math_tree(("call", "g", (("group", root),))))
            for sign in ("+", "-"):
                signed = ("unary", sign, number)
                cases.add(_render_math_tree(("binary", "+",
                    ("implicit", ("identifier", "log"), " ", signed), omega)))
                cases.add(_render_math_tree(("binary", "*",
                    ("implicit", signed, " ", identifier), omega)))
            cases.add(_render_math_tree(("implicit", number, "", group)))
            cases.add(_render_math_tree(("implicit", number, "", identifier)))
            cases.add(_render_math_tree(call))
    # The earlier two-atom notation admitted identifiers, numbers, and calls
    # in either position. Cover the whole small cross-product independently.
    atoms = (("identifier", "alpha"), ("number", "2"),
             ("call", "f", (("identifier", "beta"),)))
    for left in atoms:
        for right in atoms:
            cases.add(_render_math_tree(("binary", "+",
                ("implicit", left, " ", right), omega)))
    assert len(cases) <= 128
    assert all(len(case) < 95 for case in cases)
    return tuple(sorted(cases))


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
@pytest.mark.parametrize("terminal_period", [False, True])
@pytest.mark.parametrize("expression", _numeric_math_grammar_cases())
def test_bounded_math_grammar_through_pdf(
    tmp_path: Path, number: str, terminal_period: bool, expression: str,
) -> None:
    # Reuse only the PDF writer and public detector assertion, never the parser
    # helper as an oracle. Both levels and both terminal states use extraction.
    test_generated_mathematical_heading_continuation(
        number, "e.g.", expression, terminal_period, False, False, tmp_path,
    )


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
@pytest.mark.parametrize("abbreviation", ["e.g.", "i.e."])
@pytest.mark.parametrize("body", [
    "(continued)", "(optional)", "((continued))", "ordinary prose",
    "There are 2 groups in this paragraph", "Results 2 are discussed here",
    "2 results", "Chapter 2", "The method (with options) follows here",
    "alpha + (beta", "alpha +", "method(alpha,)", "alpha + [beta)",
    "alpha + beta are discussed here", "method(alpha); ordinary prose follows",
])
def test_numeric_grammar_does_not_absorb_prose_or_ambiguous_suffixes_through_pdf(
    tmp_path: Path, number: str, abbreviation: str, body: str,
) -> None:
    # In these independently specified controls the bold abbreviation ends the
    # heading; the regular suffix is body text or insufficient evidence to
    # override that boundary. A terminal heading period must not be requested.
    path = tmp_path / "body-boundary.pdf"
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=612, height=792)
        x = 108.0
        for index, word in enumerate([number, "Synthetic", "heading", abbreviation]):
            page.insert_text((x, 300), word, fontname="tibo", fontsize=12)
            x += pymupdf.get_text_length(word, fontname="tibo", fontsize=12)
            x += 15 if index == 0 else 5
        page.insert_text((x, 300), body, fontname="tiro", fontsize=12)
        pdf.save(path)
    assert _issues(load_pdf_layout(str(path))) == []


@pytest.mark.parametrize("text,expected", [
    ("(" * 70 + "alpha + 1" + ")" * 70, True),
    ("(" * 149 + "x", False),
    ("f(" * 49 + "x" + ")" * 49, True),
    ("(" * 1000 + "alpha" + ")" * 1000, False),
    ("alpha + " + "beta" * 1000, False),
])
def test_numeric_grammar_depth_and_length_are_bounded(text: str, expected: bool) -> None:
    from njit_auditor.rules.pdf_heading_levels import _period_precedes_math_continuation

    assert _period_precedes_math_continuation("Synthetic heading e.g.", text) is expected
