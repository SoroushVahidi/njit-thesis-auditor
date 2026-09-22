# P086/R086 Unnumbered Bold Heading Design Gate (2026-09-22)

## Reviewer Ground Truth

During the R015 (paragraph indentation) follow-up review, Ester separately
observed that the bold run-in phrase used as Youra's de facto section title
(physical page 101, already handled as an R015 case) carries no section
number, and stated that bold styling should be reserved for numbered
heading levels 1-4. She labelled the bold-without-number condition itself
as not allowed. This is recorded as a distinct, out-of-scope-for-R015
observation in
`docs/status/p015_r015_esther_feedback_run_in_heading_20260831.md`
("Separate Bold-Heading Observation"), which already ran a rule-ownership
audit and ruled out P020 (style of *recognized* headings only), P026 (font
family/size, no concept of "reserved for headings"), and P027
(numbered-heading level/style — cannot own an unnumbered phrase by
definition). No existing rule owns this condition.

## Design Gate (required before any implementation)

1. **What exact structural pattern is supported by Ester's existing
   judgment?** A bold phrase that reads as a de facto section title (the
   Youra page-101 case) with no section number in front of it. It is not a
   general statement that every bold span anywhere must carry a number.
2. **What legitimate bold structures can already be identified and
   excluded reliably?** Numbered headings (P027's own patterns), named
   front-matter/TOC/List/references headings (`group_lines_into_paragraphs`
   already excludes these from paragraph lines entirely), bullet/list items
   (same exclusion), figure/table captions (`CAPTION_PREFIX_RE`, same
   exclusion) — all already implemented and reused, not reinvented.
3. **Can the known violation be captured without broad body-wide false
   positives?** Yes, by requiring the *exact* structural shape Ester's own
   case has: a bold lead-in sharing a physical row with regular-styled
   continuation text (a "run-in heading"), which is the same shape
   `pdf_indentation.py` already detects and excludes from R015's own
   indentation comparison (`_is_run_in_heading_lead` /
   `_paragraph_starts_with_run_in_heading`). Reusing that detector verbatim
   means this rule inherits R015's own, already-validated precision for
   telling a genuine run-in heading apart from coincidental same-row bold
   text, rather than inventing a fresh "is this bold span heading-like"
   heuristic.
4. **Is there a general detector using structure rather than
   author/page/text hardcoding?** Yes — no author name, dissertation
   title, or physical-page special case appears anywhere in the detector;
   every exclusion is a structural/geometric property (row-sharing,
   style transition, section-number pattern, bullet marker, page-level
   named heading).
5. **Does the detector require inventing an unsupported font-weight
   threshold?** No — it reuses the existing `PdfTextSpan.bold` boolean
   already used by P027 and R015; no new threshold.
6. **Does it require guessing policy about ordinary inline emphasis Ester
   never adjudicated?** This is the real risk the gate exists to catch.
   Ordinary inline emphasis (a bold word or two inside an otherwise regular
   sentence) is *not* the run-in-heading shape: `_is_run_in_heading_lead`
   requires the bold text to be its own extracted line/fragment whose
   *trailing* span is bold and which shares a row with a *separately
   extracted*, differently-styled fragment — a text-extraction-level style
   transition, not merely "some bold characters somewhere in one merged
   line." A short bold call-out label (e.g. a one-word lead-in) is
   additionally excluded by reusing P027's own `_is_qualified_heading`
   text-quality filter (length, alpha ratio, not a citation-year pattern) —
   the same filter that already keeps P027 from treating noise as a
   heading, reused rather than reinvented. Between the exact-shape
   requirement and the qualifying-text filter, this stays within the shape
   Ester actually adjudicated without guessing about plain emphasis.
7. **Is an existing rule a clean owner, or is a new rule required?** No
   existing rule owns it (see the rule-ownership audit above, already done
   in the R015 follow-up doc); Ester's own words distinguish it from R015
   ("that is a separate formatting issue, not R015 paragraph indentation").
   A new rule is required. Per the rule inventory in
   `docs/status/CURRENT_STATUS.md` ("next new internal rule ID is P086"),
   this becomes P086 internally / **R086** in all student/reviewer-facing
   text (the existing `public_display_rule_id()` P→R mapping handles this
   automatically; no new registry entry needed).

**Gate outcome: PASS.** A general detector is achievable without inventing
new policy, by reusing three already-validated, already-conservative
structural signals (R015's run-in-heading-lead detection, P027's
qualifying-heading-text filter and numbered-pattern/named-heading
exclusions) rather than scanning for "any bold text."

## Real Corpus False Positives Found and Fixed During Validation

Manually inspecting every live finding across all seven private
dissertations (privacy-safe: structural shape and page only, no prose
quoted here or in tests/tracked files) surfaced three genuine false
positives, all traceable to known PDF text-extraction artifacts already
documented elsewhere in this repository (see
`docs/status/concatenated_heading_extraction_artifact.md`-style precedent):

1. **Anthony physical page 28, Praneeth physical page 84 (×2):** a real
   numbered heading whose number was extracted glued directly onto the
   first word with no space at all (e.g. a 4-level number immediately
   followed by a capital letter, no whitespace), or with a trailing period
   glued onto the last digit group before the space. `pdf_heading_levels.py`'s
   own per-level regexes require `\s+` immediately after the digits and
   correctly miss both shapes for their own (different) purpose; reusing
   them verbatim for this rule's *exclusion* check let three genuinely
   numbered headings slip through as "unnumbered." Fixed with a
   dedicated, more permissive leading-number pattern
   (`_LEADING_NUMBER_RE`) used only to exclude a candidate — over-matching
   here can only suppress a flag, never invent one, so the broader pattern
   is the safe direction to err in.
2. **Muyeed physical page 32:** a bulleted definition-list term
   (bullet character glued directly onto the bold term with no space).
   `pdf_indentation.py`'s own `BULLET_PREFIX_RE` requires `\s+` after the
   marker and misses this shape for the same extraction-artifact reason.
   Fixed with a whitespace-tolerant leading-bullet check
   (`_LEADING_BULLET_RE`), local to this rule only — `BULLET_PREFIX_RE`
   itself was not changed, since that is shared logic other rules
   (including R015) already rely on and retuning it is out of scope here.
3. **Muyeed physical page 34:** a real numbered heading whose section
   number extracted as a separate same-row fragment to the *left* of the
   bold title (rather than glued to it) — a split the candidate's own text
   cannot reveal by itself. Fixed by scanning the page's raw lines for a
   bare section-number-only fragment (reusing `pdf_indentation.py`'s own
   `_SECTION_NUMBER_ONLY_RE`) sharing the candidate's row before flagging.

All three fixes are structural pattern-matching corrections for known
extraction shapes, not policy inventions, and each has a dedicated
synthetic regression test (see below).

## Implementation

`src/njit_auditor/rules/pdf_unnumbered_bold_heading.py`
(`check_pdf_unnumbered_bold_heading`), wired into `audit_runner.py`
alongside the other PDF checks. Emits `rule_id="P086"`,
`issue_type="bold_heading_without_section_number"`. Student-facing wording
added to `issue_type_explanations.py` and `polished_comments.py`, matching
the existing P085 entries' pattern exactly (no `report_outputs.py` catalog
entry, matching P085's own precedent).

## Synthetic Regression Coverage

`tests/test_p086_unnumbered_bold_heading.py` (12 tests): numbered run-in
heading (no finding), the actual unnumbered run-in heading shape (finding),
front-matter named-heading page (no finding), List of Figures/Tables page
(no finding), bold figure-caption prefix (no finding), inline bold emphasis
not in run-in shape (no finding), plain body text (no finding), short bold
call-out label failing the qualifying-text filter (no finding), and the
three real extraction-artifact shapes found on the corpus above (each: no
finding). No dissertation prose, author name, or physical-page-specific
hardcoding anywhere in the fixtures.

## Seven-Document Corpus Audit

| Dissertation | P086 findings | Pages |
|---|---:|---|
| Youra | 5 | 89, 91, 94, 101, 105 |
| Anthony | 0 | — |
| Muyeed | 4 | 69, 79, 117, 188 |
| Philip | 0 | — |
| Praneeth | 0 | — |
| Sebastian | 0 | — |
| Patrick | 0 | — |
| **Total** | **9** | |

Youra physical page 101 is the exact Ester-adjudicated case; page 105 is
its clear structural sibling (a parallel "scenario" heading of the same
kind, same shape, different scenario number). None of the 9 findings are
themselves reviewer-confirmed beyond page 101 — they are new, structurally
consistent candidates for ordinary human/reviewer follow-up, not claimed
verdicts. All three false-positive shapes identified above are confirmed
absent from the final 9 (each was individually traced to a specific,
now-excluded extraction artifact and re-verified gone after the fix).

## Closed-Rule Regression Anchors (same seven-document corpus)

| Rule | Expected | Observed |
|---|---:|---:|
| R068 | 0 | 0 |
| R066 | 0 | 0 |
| R040 | 43 | 43 |
| R046 | 0 | 0 |
| R048 | 5 | 5 |
| R053 | 1 | 1 |
| R054 | 4 | 4 |
| R078 | 1 | 1 |

All eight anchors unchanged.

## Validation

`ruff check .` clean; `mypy src` clean (136 source files); targeted P086 +
shared R015 tests: 45 passed; full `python -m pytest -q`: 3612 passed, 5
skipped (was 3600/5; +12 new tests).

## Privacy

No private PDFs committed. No dissertation prose, author names, or
physical-page-specific hardcoding anywhere in this document, the detector,
or its tests — only structural shape descriptions (row-sharing, style
transition, extraction-artifact patterns) and page numbers.
