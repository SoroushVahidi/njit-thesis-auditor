"""What the PDF audit checks, and what students must still verify themselves.

One shared description of check coverage, organized by the sections of the
Graduate Studies self-assessment sheet. The web results page, the plain-text
and Markdown downloads, and the combined student PDF all render from this
data so the disclosure cannot drift between surfaces.

Coverage was classified from the rule modules and their tests, not from the
rule registry. ``rule_ids`` lists the internal rules behind each "checked" or
"partly checked" claim; they are for maintainers and are not shown to
students. Wording is deliberately conservative: it never claims compliance
and never presents the report as a replacement for the self-assessment sheet
or for Graduate Studies review.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CoverageStatus = Literal["checked", "partial", "manual", "guidance_differs"]

STATUS_LABELS: dict[CoverageStatus, str] = {
    "checked": "Checked",
    "partial": "Partly checked",
    "manual": "Not checked",
    "guidance_differs": "Checked; guidance differs",
}

COVERAGE_HEADING = "What this report checked and what you must check yourself"

COVERAGE_INTRO: tuple[str, ...] = (
    "This report checks many, but not all, of the items on the Graduate Studies "
    "self-assessment sheet. It does not replace that sheet or Graduate Studies review.",
    "Each finding is a possible problem detected automatically. Some findings may be "
    "wrong, and some real problems may be missed, so review every finding before you "
    "change your document.",
    "Having few or no findings does not mean your document meets NJIT requirements. Check "
    "the items listed under \"Check yourself\" by hand.",
    "The checks read the text stored in your PDF. Pages without selectable text, such as "
    "scanned or image-only pages, cannot be checked.",
)


@dataclass(frozen=True)
class CoverageArea:
    key: str
    title: str
    status: CoverageStatus
    checked: str
    manual: str
    rule_ids: tuple[str, ...] = ()

    @property
    def status_label(self) -> str:
        return STATUS_LABELS[self.status]


COVERAGE_AREAS: tuple[CoverageArea, ...] = (
    CoverageArea(
        key="margins",
        title="Margins",
        status="partial",
        checked=(
            "Text that crosses the 1.5-inch left margin or the 1-inch top, right, or "
            "bottom margin."
        ),
        manual="Images, drawings, and table rules that extend into a margin.",
        rule_ids=("P011",),
    ),
    CoverageArea(
        key="font",
        title="Font",
        status="partial",
        checked=(
            "Body text font family and size on main-text pages. A page is flagged only "
            "when most of its body text differs, and sizes from 11 to 13 pt are accepted."
        ),
        manual=(
            "That all body text is exactly 12 pt; fonts on the front-matter and "
            "References pages; fonts inside tables and figures."
        ),
        rule_ids=("P026",),
    ),
    CoverageArea(
        key="pagination",
        title="Page numbers",
        status="partial",
        checked=(
            "Roman numerals in the front matter and Arabic numerals in the main text; "
            "no number on the Title, Copyright, Approval, and Abstract pages; the "
            "Biographical Sketch on page iv; gaps, repeats, and position."
        ),
        manual=(
            "That Arabic numbering starts on the first page of Chapter 1 and continues "
            "through the last page of the References."
        ),
        rule_ids=("P013", "P019", "P022", "P028", "P029", "P037", "P085"),
    ),
    CoverageArea(
        key="title_page",
        title="Title page",
        status="partial",
        checked=(
            "Clear differences between the title on the Title, Abstract, and Approval "
            "pages, when the title can be read on at least two of them; that the degree "
            "and institution lines are present; graduation month (May, August, or December)."
        ),
        manual=(
            "That the title is identical, word for word, on all three pages (small "
            "differences may not be flagged); that the page follows your program's template."
        ),
        rule_ids=("P025", "P033", "P074"),
    ),
    CoverageArea(
        key="approval_page",
        title="Approval page",
        status="partial",
        checked="That an advisor label appears among the committee entries.",
        manual=(
            "Signature and date lines for each member; honorifics (Dr., Mr., Ms.); advisor "
            "listed first; committee order by department and rank; external members' "
            "institution, city, and state."
        ),
        rule_ids=("P068",),
    ),
    CoverageArea(
        key="biographical_sketch",
        title="Biographical Sketch",
        status="partial",
        checked=(
            "Publications are not numbered, single-spaced within an entry, separated "
            "by a blank line, and in reverse chronological order."
        ),
        manual=(
            "Alignment of the Author, Degree, Date, and Major fields; publications use "
            "the same citation style as your References."
        ),
        rule_ids=("P045", "P067"),
    ),
    CoverageArea(
        key="acknowledgements",
        title="Acknowledgements",
        status="partial",
        checked="Heading spelling and paragraph indentation.",
        manual=(
            "Paragraph order (advisor, committee, technical support, funding with "
            "grant numbers, colleagues, family); full names; \"Advisor\" and "
            "\"Committee Members\" capitalized."
        ),
        rule_ids=("P038", "P043"),
    ),
    CoverageArea(
        key="table_of_contents",
        title="Table of Contents",
        status="partial",
        checked=(
            "Heading and \"(Continued)\" headings; chapter titles in all caps; level-2 "
            "titles in title case; clear level-3 Title Case violations; wrapped titles "
            "with a large gap between their lines; "
            "indentation; leaders; right-aligned page numbers in order."
        ),
        manual=(
            "Double spacing between entries, with wrapped titles fully single-spaced; "
            "ambiguous level-3 sentence case; level-4 and level-5 titles not listed; "
            "each page number matches the page where the section begins."
        ),
        rule_ids=("P014", "P018", "P024", "P030", "P032", "P038", "P039", "P058", "P075"),
    ),
    CoverageArea(
        key="list_of_tables",
        title="List of Tables",
        status="partial",
        checked=(
            "Title case; the word \"Table\" before each number; wrapped titles with a "
            "large gap between their lines; leaders and page-number alignment."
        ),
        manual=(
            "Double spacing between entries, with wrapped titles fully single-spaced; "
            "each page number matches the page where the table begins."
        ),
        rule_ids=("P018", "P024", "P032", "P055"),
    ),
    CoverageArea(
        key="list_of_figures",
        title="List of Figures",
        status="guidance_differs",
        checked=(
            "The word \"Figure\" before each number; ending punctuation; title case, "
            "following current Graduate Studies reviewer guidance."
        ),
        manual=(
            "The self-assessment sheet describes sentence case for figure descriptions; "
            "if unsure, confirm the expected style with Graduate Studies. Also check "
            "that figure part letters are consistently upper- or lowercase, and that "
            "entries are double-spaced with wrapped titles single-spaced."
        ),
        rule_ids=("P024", "P040", "P055"),
    ),
    CoverageArea(
        key="spacing_paragraphs",
        title="Text spacing and paragraphs",
        status="partial",
        checked=(
            "Double spacing of body text; first paragraph of a section not indented and "
            "later paragraphs indented; unusually large blank gaps; clearly double-spaced "
            "wraps within numbered body headings."
        ),
        manual=(
            "Bullet lists single-spaced within a bullet and double-spaced between "
            "bullets; multi-line titles without clear numbered-heading geometry "
            "single-spaced."
        ),
        rule_ids=("P015", "P016", "P023"),
    ),
    CoverageArea(
        key="headings",
        title="Headings (levels 1 to 5)",
        status="partial",
        checked=(
            "Chapter titles in all caps; level-2 titles in title case; numbered level-3 "
            "and level-4 titles in sentence case; level-4 titles ending with a period."
        ),
        manual=(
            "Capitalization of unnumbered level-3 to level-5 headings; centering, "
            "alignment, and bold; two blank lines after a chapter title; level-5 italics; "
            "where the text begins after each heading."
        ),
        rule_ids=("P020", "P027"),
    ),
    CoverageArea(
        key="tables_figures",
        title="Tables and figures",
        status="partial",
        checked=(
            "Tables and figures centered; table titles above the table and figure "
            "descriptions below the figure; title and description capitalization and "
            "punctuation."
        ),
        manual=(
            "Only \"Table X.x\" or \"Figure X.x\" in bold; two blank lines between a "
            "figure and its description; sources in 10 pt; \"(Continued)\" on "
            "multi-page tables."
        ),
        rule_ids=("P017", "P035"),
    ),
    CoverageArea(
        key="equations",
        title="Equations",
        status="manual",
        checked="",
        manual=(
            "Chapter-form numbers (X.x) in parentheses, right-aligned; equations "
            "centered; \"Equation\" capitalized in the text."
        ),
    ),
    CoverageArea(
        key="appendices",
        title="Appendices",
        status="partial",
        checked="APPENDIX or APPENDIX A, B, C labels in the Table of Contents and the text.",
        manual="Titles in all caps; each appendix introduced by a short paragraph.",
        rule_ids=("P042", "P063"),
    ),
    CoverageArea(
        key="references",
        title="References",
        status="partial",
        checked="Consistent entry indentation and spacing.",
        manual="One citation style, agreed with your advisor, used consistently.",
        rule_ids=("P064",),
    ),
)


def coverage_text_lines() -> list[str]:
    """Plain-text rendering shared by the text download."""
    lines = [COVERAGE_HEADING.upper(), ""]
    for paragraph in COVERAGE_INTRO:
        lines.append(paragraph)
        lines.append("")
    for area in COVERAGE_AREAS:
        lines.append(f"{area.title}: {area.status_label}")
        if area.checked:
            lines.append(f"  Checked: {area.checked}")
        lines.append(f"  Check yourself: {area.manual}")
    return lines


def coverage_markdown_lines() -> list[str]:
    """Markdown rendering for the Markdown download."""
    lines = [f"## {COVERAGE_HEADING}", ""]
    for paragraph in COVERAGE_INTRO:
        lines.append(paragraph)
        lines.append("")
    for area in COVERAGE_AREAS:
        parts = [f"- **{area.title}** ({area.status_label})."]
        if area.checked:
            parts.append(f"Checked: {area.checked}")
        parts.append(f"Check yourself: {area.manual}")
        lines.append(" ".join(parts))
    lines.append("")
    return lines
