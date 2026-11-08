"""Synthetic controls for periods on geometrically spaced run-in headings."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

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
                # Nest the raw kernel, independently of binary context. This
                # catches premature recursive rejection of implicit operands.
                cases.add(_render_math_tree(("call", "f", (kernel,))))
                root = ("binary", operator, kernel, omega)
                cases.add(_render_math_tree(root))
                cases.add(_render_math_tree(("call", "g", (("group", root),))))
            for sign in ("+", "-"):
                signed = ("unary", sign, number)
                cases.add(_render_math_tree(("binary", "+",
                    ("implicit", ("identifier", "log"), " ", signed), omega)))
                cases.add(_render_math_tree(("binary", "*",
                    ("implicit", signed, " ", identifier), omega)))
                cases.add(_render_math_tree(("implicit", signed, " ", call)))
            cases.add(_render_math_tree(("implicit", number, "", group)))
            cases.add(_render_math_tree(("implicit", number, "", identifier)))
            cases.add(_render_math_tree(("implicit", number, " ", call)))
            cases.add(_render_math_tree(call))
    # The earlier two-atom notation admitted identifiers, numbers, and calls
    # in either position. Cover the whole small cross-product independently.
    atoms = (("identifier", "alpha"), ("number", "2"),
             ("call", "f", (("identifier", "beta"),)))
    for left in atoms:
        for right in atoms:
            cases.add(_render_math_tree(("binary", "+",
                ("implicit", left, " ", right), omega)))
    assert len(cases) <= 180
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
    "sin(x) increases", "Evaluate f(x)",
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


def _in_memory_expression_pdf(
    number: str, suffix: str, *, prefix: str = "Synthetic heading e.g.",
) -> PdfDocument:
    """Real PDF bytes and extraction; substitute only the file opener."""
    with pymupdf.open() as pdf:
        # Wide enough to avoid clipping adversarial 150-character expressions.
        page = pdf.new_page(width=1200, height=1600)
        x = 108.0
        for index, word in enumerate([number, *prefix.split()]):
            page.insert_text((x, 300), word, fontname="tibo", fontsize=12)
            x += pymupdf.get_text_length(word, fontname="tibo", fontsize=12)
            x += 15 if index == 0 else 5
        page.insert_text((x, 300), suffix, fontname="tiro", fontsize=12)
        extracted = pymupdf.open(stream=pdf.tobytes(), filetype="pdf")
    with patch("njit_auditor.pdf_layout.fitz.open", return_value=extracted):
        doc = load_pdf_layout("synthetic-expression.pdf")
    assert suffix in " ".join(
        line.text for block in doc.pages[0].text_blocks for line in block.lines
    )
    return doc


def _nested_math_grammar_cases():
    """Valid symbolic derivations selected without consulting production code.

    Implicit products are nested BEFORE introducing any binary expression.
    Calls, groups and signs are independent constructors. Unknown function and
    argument names check that context is not limited to a list of call names.
    """
    alpha, beta = ("identifier", "alpha"), ("identifier", "beta")
    gamma, two = ("identifier", "gamma"), ("number", "2")
    kernels = (
        ("implicit", alpha, " ", beta),
        ("implicit", two, " ", alpha),
        ("implicit", ("unary", "-", two), " ", alpha),
        ("implicit", ("identifier", "log"), " ", two),
        ("implicit", two, "", ("group", ("binary", "+", alpha, beta))),
        ("implicit", two, "", ("group", ("implicit", alpha, " ", beta))),
        ("implicit", ("identifier", "x_1"), " ", ("identifier", "theta2")),
        ("implicit", two, "", ("identifier", "velocity")),
        ("implicit", ("number", "3.5"), "", ("identifier", "capacity")),
    )
    cases = set()
    for kernel in kernels:
        for argument in (kernel, ("group", kernel), ("unary", "-", ("group", kernel))):
            call = ("call", "f", (argument,))
            forms = (
                ("unary", "-", argument),
                ("unary", "+", ("group", argument)),
                call,
                ("call", "transform", (argument,)),
                ("call", "f", (("call", "g", (argument,)),)),
                ("call", "f", (argument, ("identifier", "velocity"))),
                ("call", "f", (("identifier", "velocity"), argument)),
                ("binary", "+", call, gamma),
                ("binary", "+", ("group", argument), gamma),
                ("binary", "*", gamma, ("group", argument)),
                ("implicit", two, "", call),
                ("unary", "-", call),
            )
            cases.update(map(_render_math_tree, forms))
    assert {
        "f(alpha beta)", "f(2 alpha)", "f(-2 alpha)", "f(log 2)",
        "f((2 alpha))", "f(g(2 alpha))", "f(2(alpha + beta))", "f(alpha beta) + gamma",
    } <= cases
    assert all(len(case) < 100 for case in cases)
    return tuple(sorted(cases))


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
@pytest.mark.parametrize("terminal_period", [False, True])
@pytest.mark.parametrize("expression", _nested_math_grammar_cases())
def test_nested_implicit_context_through_in_memory_pdf(
    number: str, terminal_period: bool, expression: str,
) -> None:
    doc = _in_memory_expression_pdf(number, expression + ("." if terminal_period else ""))
    level = len(number.split("."))
    assert _issues(doc) == (
        [] if terminal_period else [f"level{level}_sentence_case_or_punctuation_issue"]
    )


_AMBIGUOUS_NESTED_SUFFIXES = (
    "(continued)", "2 (continued)", "2(continued)", "-2 (continued)",
    "(ordinary prose)", "f(ordinary prose)", "method(ordinary paragraph)",
    "-(ordinary prose)", "-ordinary prose", "-2 results", "-(2 results)",
    "(alpha beta)", "2 alpha", "log 2",
    "f((ordinary prose))", "f(g(ordinary prose))", "f(2 results)",
    "f(ordinary prose, alpha beta)", "f(alpha beta, ordinary prose)",
    "(ordinary prose) + notes", "f(ordinary prose) + notes",
    "f((ordinary prose)) + alpha", "f(2 results) + alpha",
    "f(alpha beta) increases", "f(alpha + beta) increases",
    "2 (optional)", "2 ((continued))", "2 f(ordinary prose)",
    "f(alpha) (continued)", "f(alpha) ordinary prose", "f(alpha) continues here",
    "f(alpha beta) is useful", "Evaluate f(alpha beta)",
    "alpha + (beta", "f(2 alpha", "f(2 alpha,)", "f(,2 alpha)",
    "f((2 alpha])", "f(alpha beta gamma)", "function()", "function(())",
    "f(alpha beta); prose", "f(alpha beta)..", "f(alpha beta) +", "f(alpha beta) **",
)


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
@pytest.mark.parametrize("abbreviation", ["e.g.", "i.e."])
@pytest.mark.parametrize("suffix", _AMBIGUOUS_NESTED_SUFFIXES)
def test_nested_prose_and_malformed_controls_through_pdf(
    number: str, abbreviation: str, suffix: str,
) -> None:
    # Independently labelled body/ambiguous suffixes must not undo the bold
    # heading's terminal period, including word pairs enclosed by a call.
    assert _issues(_in_memory_expression_pdf(
        number, suffix, prefix="Synthetic heading " + abbreviation,
    )) == []


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
@pytest.mark.parametrize("terminal_period", [False, True])
@pytest.mark.parametrize("expression", [
    "f(2 alpha) + beta", "f(-2 alpha) + beta", "f(log 2) + alpha",
    "f(alpha beta) + gamma", "f((2 alpha))", "f(g(2 alpha))",
])
@pytest.mark.parametrize("split_number", [False, True])
@pytest.mark.parametrize("packed_prefix", [False, True])
def test_nested_context_on_both_heading_boundary_paths(
    number: str, terminal_period: bool, expression: str,
    split_number: bool, packed_prefix: bool,
) -> None:
    # Existing geometric model helper exercises the two bold-prefix paths in
    # addition to the independently extracted PDF cases above.
    test_math_boundary_does_not_depend_on_literal_prefix_spaces(
        number, split_number, packed_prefix, terminal_period, expression,
    )


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
@pytest.mark.parametrize("terminal_period", [False, True])
@pytest.mark.parametrize("extra", [-1, 0, 1])
def test_nested_pdf_heading_length_boundary(
    number: str, terminal_period: bool, extra: int,
) -> None:
    # The complete physical heading has its own 150-character gate. Construct
    # exact lengths independently and keep enough letters for its alpha ratio.
    prefix = "Synthetic heading e.g."
    target = 150 + extra
    size = target - len(number + " " + prefix + " ") - len("f(x +  alpha)")
    size -= int(terminal_period)
    expression = "f(x + " + "x" * size + " alpha)" + ("." if terminal_period else "")
    doc = _in_memory_expression_pdf(number, expression)
    assert len(number + " " + prefix + " " + expression) == target
    issues = _issues(doc)
    assert any("punctuation" in issue for issue in issues) is (
        extra <= 0 and not terminal_period
    )


@pytest.mark.parametrize("text,expected", [
    ("f(" + "(" * 66 + "2 alpha" + ")" * 66 + ")", True),
    ("f(" * 47 + "2 alpha" + ")" * 47, True),
    ("f(" * 48 + "2 alpha" + ")" * 48, False),
    ("(" * 74 + "x" + ")" * 74, False),
    ("(" * 150, False),
    ("f()", False),
    ("velocity speed + alpha", True),
    ("f(velocity speed + alpha)", True),
    ("f(ordinary prose) + notes", False),
    ("f(())", False),
    ("+" * 149 + "x", True),
    ("+" * 150 + "x", False),
    ("f(" * 45 + "2 alpha" + ")" * 44 + "]", False),
])
def test_nested_parser_resource_boundary(text: str, expected: bool) -> None:
    from njit_auditor.rules.pdf_heading_levels import _period_precedes_math_continuation

    assert _period_precedes_math_continuation("Synthetic heading e.g.", text) is expected


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
@pytest.mark.parametrize("terminal_period", [False, True])
@pytest.mark.parametrize("depth", [1, 7, 15])
def test_deep_nested_implicit_pdf(number: str, terminal_period: bool, depth: int) -> None:
    expression = "f(" * depth + "alpha beta" + ")" * depth
    doc = _in_memory_expression_pdf(number, expression + ("." if terminal_period else ""))
    assert any("punctuation" in issue for issue in _issues(doc)) is not terminal_period


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
def test_deep_mismatched_group_pdf(number: str) -> None:
    # Enough alphabetic content to exercise syntax rather than the independent
    # minimum-alpha body-boundary gate; mismatch occurs at the outermost group.
    suffix = "f(" * 20 + "alpha" * 10 + " beta" + ")" * 19 + "]"
    assert _issues(_in_memory_expression_pdf(number, suffix)) == []



@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
@pytest.mark.parametrize("terminal_period", [False, True])
@pytest.mark.parametrize("expression", [
    "2velocity", "3.5capacity", "f(2velocity)", "-2velocity", "f(-3.5capacity)",
    "velocity speed + alpha", "f(velocity speed + alpha)",
    "-(2 alpha)", "+(alpha beta)", "-2 alpha", "f(alpha) beta",
])
def test_named_coefficient_and_existing_binary_operands_through_pdf(
    number: str, terminal_period: bool, expression: str,
) -> None:
    doc = _in_memory_expression_pdf(number, expression + ("." if terminal_period else ""))
    assert any("punctuation" in issue for issue in _issues(doc)) is not terminal_period


_INDEXED_CALL_REGRESSIONS = (
    "f(2 theta_i) + beta", "f(alpha_i beta_j) + gamma", "f(-3 sigma_k) + tau",
    "f((2 theta_i)) + beta", "f(g(velocity) alpha) + beta", "f(alpha g(velocity)) + beta",
    # These previously passed at the detector level despite parser rejection.
    "f(2 x_i) + beta", "f(g(2 x_i)) + beta",
)


def _indexed_operand_grammar_cases():
    """Independent symbolic AST derivations, including opaque argument names.

    Symbol spelling is a base/index cross-product. Calls and binary expressions
    are operands in their own right, so their parameter vocabulary must not
    exclude them from multiplication. Expectations follow these declared roles.
    """
    cases = set(_INDEXED_CALL_REGRESSIONS)
    named = ("identifier", "velocity")
    another = ("identifier", "acceleration")
    two = ("number", "2")
    beta = ("identifier", "beta_j")
    call = ("call", "g", (named,))
    group = ("group", ("binary", "+", named, another))
    for base in ("alpha", "theta", "x"):
        for index in ("i", "12", "k2", "j_3"):
            symbol = ("identifier", base + "_" + index)
            kernels = (
                ("implicit", two, " ", symbol),
                ("implicit", ("unary", "-", two), " ", symbol),
                ("implicit", symbol, " ", beta),
                ("implicit", call, " ", symbol),
                ("implicit", symbol, " ", call),
                ("implicit", group, " ", symbol),
                ("implicit", symbol, " ", group),
            )
            for kernel in kernels:
                for tree in (
                    ("call", "f", (kernel,)),
                    ("call", "f", (("group", kernel),)),
                    ("call", "f", (("call", "h", (kernel,)),)),
                    ("binary", "+", ("group", kernel), beta),
                    ("unary", "-", ("group", kernel)),
                ):
                    cases.add(_render_math_tree(tree))
            # Mix explicit and implicit products and nest multiple named calls.
            product = ("implicit", call, " ", ("call", "h", (another,)))
            cases.add(_render_math_tree(("call", "f", (
                ("binary", "*", symbol, product),))))
            cases.add(_render_math_tree(("implicit", two, "", ("call", "f", (symbol, named)))))
    cases.update((
        "f(alpha_i)", "f(theta_2)", "f(sigma_k)", "f(x_12)", "f(beta_j)",
        "f(g(velocity) alpha)", "f(alpha g(velocity))", "g(velocity) alpha",
        "alpha g(velocity)", "f(g(alpha) beta)", "f(beta g(alpha))",
        "f((velocity + acceleration) alpha)", "f(alpha (velocity + acceleration))",
        "f(g(velocity) h(acceleration))", "f(-velocity alpha)",
    ))
    assert len(cases) < 480
    assert all(len(case) < 100 for case in cases)
    return tuple(sorted(cases))


# Direct tests and PDF tests intentionally have separate parametrizations. A
# parser failure must not prevent execution of the independently expected PDF
# outcome, and a PDF warning must not count as proof of parser recognition.
@pytest.mark.parametrize("terminal_period", [False, True])
@pytest.mark.parametrize("expression", sorted(
    set(_numeric_math_grammar_cases()) | set(_nested_math_grammar_cases())
    | set(_indexed_operand_grammar_cases())
))
def test_generated_mathematical_syntax_directly(expression: str, terminal_period: bool) -> None:
    from njit_auditor.rules.pdf_heading_levels import _period_precedes_math_continuation

    assert _period_precedes_math_continuation(
        "Synthetic heading e.g.", expression + ("." if terminal_period else ""),
    )


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
@pytest.mark.parametrize("terminal_period", [False, True])
@pytest.mark.parametrize("expression", _indexed_operand_grammar_cases())
def test_indexed_and_named_operand_grammar_pdf(
    number: str, terminal_period: bool, expression: str,
) -> None:
    doc = _in_memory_expression_pdf(number, expression + ("." if terminal_period else ""))
    level = len(number.split("."))
    assert _issues(doc) == (
        [] if terminal_period else [f"level{level}_sentence_case_or_punctuation_issue"]
    )


_SYMBOLIC_PROSE_CONTROLS = (
    "ordinary_text", "ordinary_text follows", "(ordinary_text)", "2 (ordinary_text)",
    "function (ordinary discussion)", "function(ordinary discussion)",
    "f(ordinary_text follows)", "f(alpha_i ordinary_text)",
    "g(velocity) increases", "g(velocity) increases steadily", "Evaluate g(velocity)",
    "f(g(ordinary prose) alpha_i)", "f(alpha_i g(ordinary prose))",
    "f(g(ordinary prose) alpha_i) + beta", "f(2 (continued)) + beta",
    "f(g(velocity) ordinary_text)", "f(ordinary_text g(velocity))",
    "(ordinary_text follows) + alpha", "f(ordinary prose, alpha_i)",
    "f(alpha_i, ordinary prose)", "f(g(velocity), ordinary prose) + beta",
    "f(2 theta_)", "f(2 theta__i)", "f(alpha_i beta_)", "f(_alpha)",
    "f(theta_-1)", "f(theta_i,)", "f(,theta_i)", "f(theta_i beta_j gamma_k)",
    "f((theta_i beta_j])", "f(theta_i) trailing words", "f(theta_i); text",
    "g(velocity)..", "f(g(velocity) alpha_i) +", "function_name()",
)


@pytest.mark.parametrize("terminal_period", [False, True])
@pytest.mark.parametrize("suffix", (*_AMBIGUOUS_NESTED_SUFFIXES, *_SYMBOLIC_PROSE_CONTROLS))
def test_symbolic_ambiguity_and_invalid_syntax_directly(suffix: str, terminal_period: bool) -> None:
    from njit_auditor.rules.pdf_heading_levels import _period_precedes_math_continuation

    assert not _period_precedes_math_continuation(
        "Synthetic heading e.g.", suffix + ("." if terminal_period else ""),
    )


@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
@pytest.mark.parametrize("terminal_period", [False, True])
@pytest.mark.parametrize("suffix", _SYMBOLIC_PROSE_CONTROLS)
def test_symbolic_ambiguity_and_invalid_syntax_pdf(
    number: str, terminal_period: bool, suffix: str,
) -> None:
    assert _issues(_in_memory_expression_pdf(
        number, suffix + ("." if terminal_period else ""),
    )) == []


@pytest.mark.parametrize("expression,parser_expected,pdf_missing", [
    ("f(x_)", False, True),  # Short malformed suffix cannot establish a body boundary.
    ("f(2 x_i) + beta", True, True),  # A PDF fallback previously hid parser rejection.
    ("f(" * 45 + "alpha_i" + ")" * 45, True, False),  # Complete heading exceeds 150.
    ("f(" * 48 + "alpha_i" + ")" * 48, False, False),  # Expression itself exceeds 150.
    ("(" * 74 + "x" + ")" * 74, False, False),  # Grouping alone supplies no math evidence.
])
@pytest.mark.parametrize("number", ["2.3.4.5", "2.3.4.5.6"])
@pytest.mark.parametrize("terminal_period", [False, True])
def test_parser_and_detector_have_distinct_boundary_expectations(
    expression: str, parser_expected: bool, pdf_missing: bool,
    number: str, terminal_period: bool,
) -> None:
    from njit_auditor.rules.pdf_heading_levels import _period_precedes_math_continuation

    suffix = expression + ("." if terminal_period else "")
    # Compute both before asserting either: parser success never defines the
    # detector oracle. The eligibility/short-body gates have separate labels.
    parser_result = _period_precedes_math_continuation("Synthetic heading e.g.", suffix)
    detector_result = any("punctuation" in i for i in _issues(
        _in_memory_expression_pdf(number, suffix),
    ))
    assert (parser_result, detector_result) == (
        parser_expected, pdf_missing and not terminal_period,
    )


def test_balanced_expression_parser_stack_budget() -> None:
    import sys

    from njit_auditor.rules import pdf_heading_levels as rule

    depth = peak = 0

    def observe(frame, event, _value):
        nonlocal depth, peak
        if frame.f_code.co_filename == rule.__file__:
            if event == "call":
                depth += 1
                peak = max(peak, depth)
            elif event == "return":
                depth -= 1

    previous = sys.getprofile()
    sys.setprofile(observe)
    try:
        assert rule._period_precedes_math_continuation(
            "Synthetic heading e.g.", "(" * 74 + "+x" + ")" * 74,
        )
        assert not rule._period_precedes_math_continuation(
            "Synthetic heading e.g.", "(" * 75 + ")" * 75,
        )
        assert not rule._period_precedes_math_continuation(
            "Synthetic heading e.g.", "(" * 149 + "x",
        )
        assert not rule._period_precedes_math_continuation(
            "Synthetic heading e.g.", "(" * 10000 + "x",
        )
    finally:
        sys.setprofile(previous)
    assert peak < 310  # Previously unbalanced input reached about 601 frames.
