# Numbered body heading wrap spacing

## Authority and scope

P023 / R023 states that body prose is double-spaced with an exception for
multi-line titles. The NJIT *Titles Examples Level 1 to 5* guideline explicitly
requires single spacing in wrapped chapter and level-2 titles. An original
reviewer annotation applies the same requirement to a numbered, bold level-3
body heading. This supports a positive check for **internal spacing of numbered
level-2 and level-3 body headings**.
It does not establish a new rule for heading-to-paragraph gaps or subtitles.

In the reviewed PDF, the heading's internal pitch matches nearby double-spaced
prose. The baseline auditor produced no finding on that heading. Exact source
geometry and reviewer evidence are retained only in the private validation
report.

## Implementation and confidence

P023 now has a separate issue type,
`multiline_body_heading_not_single_spaced`. It reconstructs visual rows across
PDF text blocks, including same-row number/title fragments. It requires a bold
level-2 or level-3 heading; an immediately following unnumbered line with the same bold
font, size, and title indent; a first title line reaching the page's prose
right edge; and an internal pitch close to the page's own double-spaced prose
pitch after normalizing each by its font size. Both pitches must be double-like relative to the
measured font size. These independent geometry signals support a high
confidence warning. The highlighted box covers the affected title lines.

The student card explains that the heading's internal pitch appears to match
double-spaced prose. Its suggested fix is to single-space the wrapped heading
lines while preserving the normal gap from heading to paragraph.

## Boundaries and remaining manual review

The check abstains without a clear body start, usable prose pitch, exact font
match, right-edge evidence, or title-indent alignment. It skips named front
matter, TOC, LoT, LoF, references, and caption continuations. Unnumbered
headings, centered chapter titles, run-in level-4 and italic level-5 titles,
unusual hanging indents, image-only text,
and ambiguous same-style subtitles remain manual checks. P023's existing body
prose detector and P032/P036's list-entry detectors are unchanged.
