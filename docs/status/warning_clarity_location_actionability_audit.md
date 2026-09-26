# Warning Clarity, Location & Student-Actionability Audit

**Date:** 2026-07-06
**Baseline:** `origin/main` @ `d465c52c43f06161c837926c2032b0556771963b` (PR #476), 0 open PRs.
**Scope:** wording/actionability clarity only — no detector logic, thresholds, warning
counts, confidence logic, JSON export schema, rule IDs, or P021/P026 policy changes.
**Environment:** scratch worktree `warning-clarity-audit` (branch
`docs/warning-clarity-actionability-audit`), scratch uvicorn on port 8020. Live
deployment (port 8000) and vllm (port 8010) were not touched at any point.

---

## Executive summary

For each warning, the audit asked four questions a student needs answered: where is
the problem, what is it, why does it matter, and what should I do next. The wording
layer is built from three independent, parallel per-rule/issue-type dictionaries
(`finding_explanations.py` for the long-form explanation, `issue_type_explanations.py`
for the short "Issue type:" blurb and title, `polished_comments.py` for the "Review
note" and suggested fix), each falling through Python builder function → specific
template → per-rule fallback → fully generic text. For the ~50 rules sampled, that
fallback chain almost always bottoms out at a specific, rule-aware template — the
"Review this finding" literal string does not appear anywhere in current source and is
effectively unreachable for any rule with real data.

**The one rule where it wasn't unreachable: P021 (abstract word count).** Its detector
(`rules/pdf_abstract.py`) never sets `details["issue_type"]`, and none of the three
presentation modules ever derived one from the `word_count`/`limit` keys that *are*
present — except `finding_explanations.py`, which already had a private
`_resolve_issue_type()` helper doing exactly that for its own explanation text. Because
the other two modules didn't have the equivalent, P021's actual student-facing title
rendered as the literal fallback **"Review this finding"**, and its "Review note"
rendered as **"Review needed: This check (P021) found a possible formatting issue on
page N"** — despite the exact word count, limit, and degree type sitting unused one
line away in `details`, and despite a fully-written, correctly-templated string for
this exact case already existing (and already tested with an explicit `issue_type=`
override) in `polished_comments.py`. This was the clearest, most mechanical "fix now"
case in the whole audit and is fixed in this PR (see [Finding 1](#finding-1-p021-abstract-word-count-title-and-review-note-degrade-to-the-generic-fallback-fixed)).

**Second fix:** the "Findings by topic" drill-down page (`problem_group.html`, driven
by `web_app._student_location_text`) recomputes its own location string instead of
reusing the main list's `location_label` verbatim, and only recognized labels starting
with the singular `"page "` as already containing a page number. P025's Digital Commons
wrapper-page notice uses the plural `"Pages starting at N ..."` form for multi-page
wrapper detections, so that drill-down view rendered a doubled, garbled location like
`"Page 3 - Pages starting at 3 — Digital Commons wrapper pages (5 total)"` while the
main results page showed the clean version of the same finding. Fixed by recognizing
the plural prefix too (see [Finding 2](#finding-2-p025-multi-page-wrapper-location-text-doubled-on-the-findings-by-topic-drill-down-fixed)).

Everything else surveyed — P011 margins, P013/P019/P037 page numbering, P014/P038
headings, P016/P023 spacing, P026 fonts, P035 table/figure centering, P040/P053/P054
list entries, P064 references, P068 approval page, P025 wrapper notice — already has
working, rule-specific, student-legible wording with no internal jargon leaking through
(the one exception, P013's "candidate" language, is a deliberate, already-reviewed
manual-verification framing, not a defect). The main quality gaps that remain are
**structural, not wording bugs**, and are deferred per the guardrails in this task —
see [Deferred issues](#deferred-issues).

---

## Samples tested

| Sample | Findings | Notable rule coverage |
|---|---|---|
| `ester_sample_a` (Cibaku, First Review) | 39 | P011, P013, P015, P016, P020, P027, P028, P044, P051 |
| `ester_sample_b` (Yin, 2nd Review, EF Feedback) | 67 | P011, P013, P015, P016, P017, P019, P020, P023, P026, P028, P038, P051 |
| `ester_sample_c` (Yin, 2nd Review, EF Comments) | 66 | Same family as sample B |
| `ester_sample_d` (Yin, 4th Review, compressed) | 240 | P011, P013, P015–P020, P024, P026–P030, P035–P038, P044, P046, P053, P054, P068 |

Combined, the four built-in samples cover margins, page numbering, headings, spacing,
captions/TOC/list entries, fonts, roman-numeral sequencing, table/figure centering, and
approval-page structure. None of the four samples happen to trigger **P021** (abstract
within limits in all four) or **P025** (none contain Digital Commons wrapper pages), so
both audit findings below were additionally verified with small synthetic single-page
PDF fixtures (matching this project's synthetic-tests-only convention) run through the
real detector → `report_view.build_report_view` pipeline, and via the scratch HTTP
server for the sample-based checks.

---

## Rule-by-rule warning-quality matrix

| Rule | Example title | Location text | Suggested fix | Review note | Highlight/excerpt | Rating | Action |
|---|---|---|---|---|---|---|---|
| P011 margins | "Margin boundary violation" | `Page 12 — left margin` | Content-kind-specific (paragraph/approval-date/references/float/generic) | "Likely problem: Some body text on page 12 appears too close to or beyond a required page margin... NJIT margin rules are strict: no text, table, or figure may cross a required boundary, even by a small amount." | True highlight box when bbox known | **Clear and actionable** | None |
| P011 borderline (1–4pt) | same as above | same | same | Identical wording to large overflows; only the numeric `overflow_pt` value differs | same | **No distinct wording for borderline cases** — not misleading, but a 3.2pt and a 30pt overflow read identically | Defer (would need a wording *and* possibly confidence-tier decision — out of scope this pass) |
| P013 page-number candidate | "Page number candidate" | `Page 42` | "Verify placement/format against NJIT page-number requirements." | "A page-number candidate was detected in the bottom area of this page. This finding is a manual-verification signal... It does not by itself confirm a formatting defect." | Highlight when bbox known | **Clear and actionable** — deliberately framed as informational, never renders as a standalone problem card (folds into P019 when it's a real defect) | None |
| P019 wrong/missing page number | "Wrong page-number location" / missing | `Page 5 — no printed page number detected` | Rule-specific | "Problem: The auditor did not find a clear page number on page 5. NJIT requires page numbers on this type of page unless numbering is intentionally suppressed for that page type." | Highlight when bbox known | **Clear and actionable** | None |
| P037 roman section anchor | Section-specific | `Page N — {Section} numbered 'x' (expected 'y')` | "change this page's Roman numeral to '{expected}'" | Names the exact front-matter section and explains the fixed-template reasoning | Highlight when bbox known | **Clear and actionable** | None |
| P014 named heading | Heading-specific | Heading-specific, quotes the heading text | "correct any attributes that do not match" | Quotes the exact heading (e.g. `'ABSTRACT'`) and lists which attributes failed (centered/near top/bold/all caps) | Highlight when bbox known | **Clear and actionable** | None |
| P038 missing/variant heading | Heading-specific | Names the required heading | Rule-specific | Names the exact expected heading and, for variants, the exact observed vs. canonical text | Highlight when bbox known | **Clear and actionable** | None |
| P016 spacing (line/paragraph gap) | "Detected excessive vertical spacing..." | `Page N` (no sub-area) | Generic per-issue-type | Page-level, no pointer to which paragraph/line pair | No bbox in `details` at all — original-page action only | **Location vague** — confirmed generic "this page" wording with no finer pointer | Defer (needs new highlight geometry — out of scope) |
| P023 body under-spacing | "Body text on page N appears to be under-spaced..." | `Page N` (measured-region bbox covers whole block) | "Increase paragraph/line spacing to double-spaced" | Page-level median statistic, not a per-paragraph pointer | Highlight covers the whole measured region, not the specific under-spaced paragraph | **Problem vague at the paragraph level** (page-level metric, correctly disclosed as such) | Defer (documented in the prior highlight-quality audit; would need new geometry) |
| P021 abstract length | **"Review this finding"** (before fix) → **"Abstract word count exceeded"** (after fix) | `Page N` | Current remediation: "Shorten the abstract to within the applicable limit. PhD: ≤400 words. MS: ≤200 words." | Current review note substitutes the observed count and current detected-degree limit, for example a PhD abstract over the 400-word limit. | Original-page action (no bbox) | **Fixed this PR** — was the one true generic-fallback rule in the audited set | **Fixed** ([Finding 1](#finding-1-p021-abstract-word-count-title-and-review-note-degrade-to-the-generic-fallback-fixed)) |
| P026 fonts | "Possible body font family/size issue" | Font-location-specific | "correct the source document's body-text font settings if needed" | Consistently hedged: "may not use... Review the card's observed font value, confirm whether the flagged text is body text rather than a caption, heading, table entry, or footnote..." | Highlight when bbox known | **Clear, and correctly framed as a judgment call**, not a hard defect | None (per guardrail, P026 policy untouched) |
| P035 table/figure centering | "Table caption not above body" / "Figure body not centered" | `Page N — Table 3.2` (names the float number when extracted) | "Place the Table 3.2 caption above the table body. Keep the caption and table rows together within the text area." | Names the specific object | Highlight when bbox known | **Clear and actionable** | None |
| P040 LoF terminal punctuation | "List of Figures entry missing terminal punctuation" | Entry-specific | "Add terminal punctuation... to every figure description" | Cites the specific NJIT guideline reference (Q075) | Highlight when bbox known | **Clear and actionable** | None |
| P053 LoT terminal period | "List of Tables entry has a terminal period" | Entry-specific | "Remove the final period... Table titles should use title case without terminal punctuation." | Correctly the *opposite* rule of P040 (no cross-contamination) | Highlight when bbox known | **Clear and actionable** | None |
| P054 TOC terminal period | Same pattern as P053, for TOC entries | Entry-specific | Rule-specific | Rule-specific | Highlight when bbox known | **Clear and actionable** | None |
| P064 references | "No references section heading detected" / indentation / spacing inconsistency | Names the References section's page | Rule-specific per issue type | Specific, non-generic per issue type | **No highlight at all** (documented, pre-existing gap; always reports the References heading's page, not necessarily where inconsistent entries are) | **Clear wording; location precision is a known, deferred highlight-geometry gap** (see prior highlight-quality audit) | Defer (highlight geometry, out of scope) |
| P068 approval page | "Missing advisor role label" / "signature blocks sparse" | Approval Page, quantified counts | "Add the required advisor or committee role label for each committee entry..." | Quantified (counts), by design never names a specific committee member (privacy) | Highlight when bbox known | **Clear and actionable within its stated privacy constraint** | None |
| P025 Digital Commons wrapper | "Digital Commons wrapper pages detected" | `Page 1 — Digital Commons wrapper page` (single) / `Pages starting at 3 — Digital Commons wrapper pages (5 total)` (multi) | "Upload the thesis manuscript PDF without Digital Commons cover, copyright, or metadata pages, then re-run the auditor." | Unambiguous: explains what the pages are and why they cause downstream noise | Document/page-level, no bbox (structural notice) | **Clear on the main results page; was garbled on the "Findings by topic" drill-down for multi-page cases** | **Fixed this PR** ([Finding 2](#finding-2-p025-multi-page-wrapper-location-text-doubled-on-the-findings-by-topic-drill-down-fixed)) |

---

## Best examples

1. **P037 (roman-numeral front-matter anchors)** — names the exact section
   (Dedication, Biographical Sketch, etc.), explains *why* it's independent of the
   page-to-page sequence check (a fixed template position, not a relative count), and
   states the exact fix ("change this page's Roman numeral to 'v'"). This is the
   clearest four-question answer (where/what/why/how) in the codebase.
2. **P035 (table/figure centering)** — correctly identifies the specific object (e.g.
   "Table 3.2") rather than a generic "a table," in both the location label and the
   suggested fix, whenever the float number was successfully extracted.
3. **P025 (Digital Commons wrapper)** — the suggested fix is a complete, literal
   instruction ("upload the thesis manuscript PDF without Digital Commons cover,
   copyright, or metadata pages, then re-run the auditor"), not a vague pointer.
4. **P013 (page-number candidates)** — a good example of *deliberately* not
   over-claiming: it explicitly tells the student this is a manual-verification signal,
   not a confirmed defect, and (per the PR #476 fix already live) no longer confuses
   long body-text IDs with real page numbers.

## Weakest examples (pre-fix)

1. **P021 (abstract length)** — title literally read **"Review this finding"** and the
   review note was the fully generic "This check (P021) found a possible formatting
   issue on page N," despite exact word count/limit/degree data sitting unused in
   `details`. **Fixed this PR.**
2. **P025 multi-page wrapper, "Findings by topic" view** — doubled/garbled location
   text ("Page 3 - Pages starting at 3 — ..."). **Fixed this PR.**
3. **P016 (line/paragraph spacing)** — generic "this page" location with no bbox at
   all; a student sees "excessive vertical spacing" and has to scan the whole page.
   Deferred (needs new highlight geometry, out of scope for a wording-only pass).
4. **P011 borderline overflows (1–4pt)** — technically correct but reads identically to
   a 30pt overflow; a student with a 1.2pt overflow gets the same "NJIT margin rules are
   strict" language as someone with a genuinely broken layout. Deferred (a distinct
   borderline sentence is a wording change that borders on a confidence/threshold
   framing decision — flagged for Esther/policy input, not attempted here).

---

## Safe fixes made

### Finding 1: P021 abstract-word-count title and review note degrade to the generic fallback (fixed)

- **Root cause:** `rules/pdf_abstract.py`'s `check_pdf_abstract_word_count()` never sets
  `details["issue_type"]`. `finding_explanations.py` already had a private
  `_resolve_issue_type()` that synthesizes `"abstract_word_count_exceeded"` from the
  presence of `word_count`/`limit` keys, used only for its own long-form explanation
  text. `polished_comments.build_polished_comment()` and
  `report_view._finding_view_from_item()` (which computes the card title via
  `humanize_issue_type()`) had no equivalent, so both read `issue_type` as `""`,
  producing the literal template fallback `"Review this finding"` for the title
  (`job.html`'s `{% else %}Review this finding{% endif %}` branch) and the fully
  generic `"This check (P021) found a possible formatting issue on page N"` for the
  review note — even though the specific template for
  `("P021", "abstract_word_count_exceeded")` already existed in
  `polished_comments.py` and was already covered by
  `tests/test_bespoke_long_tail_remediations.py` (which only ever calls it with an
  explicit `issue_type=` override, so it never exercised the real bug).
- **Fix:** added the same 6-line resolution (`if rule_id == "P021" and not issue and
  details.get("word_count") and details.get("limit"): issue =
  "abstract_word_count_exceeded"`) in both `polished_comments.build_polished_comment()`
  and `report_view._finding_view_from_item()`, mirroring the existing pattern already
  used in `finding_explanations._resolve_issue_type()`. `build_polished_comment()` is
  the single function called by both the web (`report_view.py`) and Markdown/JSON
  (`report_outputs.py`, via `_individual_finding_comment()` and
  `build_grouped_findings()`) pipelines, so the review-note fix applies consistently to
  both without touching either export path directly.
- **Files:** `src/njit_auditor/polished_comments.py`, `src/njit_auditor/report_view.py`.
- **Not touched:** detector logic (`rules/pdf_abstract.py` untouched — `details` dict
  contents and JSON export are unchanged; the resolution is a local presentation-layer
  variable, never written back into `details`), thresholds, confidence, warning counts,
  P021 policy (word limits), rule IDs.
- **Verified:** direct script through `load_pdf_layout` → `check_pdf_abstract_word_count`
  → `build_report_view` on a synthetic 400-word abstract PDF; before the fix,
  `issue_type_label == ""` and `polished_comment == "Review needed: This check (P021)
  found a possible formatting issue on page 1"`; after the fix, `issue_type_label ==
  "Abstract word count exceeded"` and `polished_comment` names the word count, limit,
  and degree. Also confirmed live on the scratch server (port 8020).
- **Tests:** strengthened `tests/test_finding_actionability.py::test_abstract_no_fake_highlight`'s
  weak `or`-assertion and added
  `test_abstract_word_count_title_and_comment_are_specific_without_issue_type_key` and
  `test_abstract_word_count_card_does_not_show_generic_review_title` (both use the
  exact real-world `details` dict shape — no `issue_type` key — and assert
  `"Review this finding"` and `"This check ("` never appear).

### Finding 2: P025 multi-page-wrapper location text doubled on the "Findings by topic" drill-down (fixed)

- **Root cause:** `web_app._student_location_text()` recomputes a location string for
  the category/rule/issue-type drill-down page (`problem_group.html`) instead of
  reusing `location_label` verbatim (which is what the main "Findings in page order"
  list does). It treats any `location_label` not starting with the singular `"page "`
  as not yet containing a page reference, and prepends `f"Page {page} - {location_label}"`.
  `digital_commons_student_preview.py`'s multi-page wrapper label uses the plural
  `"Pages starting at {first_page} — Digital Commons wrapper pages ({page_count}
  total)"`, which doesn't match that check, producing `"Page 3 - Pages starting at 3
  — Digital Commons wrapper pages (5 total)"` on the drill-down page for the exact same
  finding that renders cleanly on the main list.
- **Fix:** extended the prefix check to `("page ", "pages ")` — a one-line, purely
  mechanical fix using the same metadata that was already being read.
- **File:** `src/njit_auditor/web_app.py`.
- **Not touched:** the underlying `location_label` values, the digital-commons
  detection/wrapper-page logic, warning counts, thresholds, rule IDs.
- **Verified:** direct call to `_student_location_text()` with the real production
  label shape; confirmed the fix does not alter the singular-page case, the
  no-page-reference case, the blank-label case, or the document-wide case.
- **Tests:** new `tests/test_student_location_text_no_duplication.py` (6 cases:
  plural-prefix dedup, singular-prefix passthrough, typical rule passthrough,
  non-page-prefixed label still gets prepended, blank label, no-page/no-label).

---

## Deferred issues

These are real quality gaps found during the audit but are explicitly out of scope for
a wording-only pass per the task's guardrails (each would require a detector change,
new highlight geometry, a threshold/confidence decision, or a policy call):

1. **P011 borderline (1–4pt) overflows** read identically to large overflows. A
   distinct, softer sentence for near-threshold cases is a reasonable future
   improvement, but risks reading as a de facto confidence-tier change — **flagged for
   Esther/policy input**, not attempted here.
2. **P016/P023 spacing** findings are page-level statistics with no highlight geometry
   pointing at the specific offending paragraph/line pair. This is a known, previously
   documented gap (see the highlight-quality audit) that needs new bbox extraction
   work in the detector, not a wording change.
3. **P064 references** location always reports the References heading's page, not
   necessarily the page containing the inconsistent entries. Same category as above —
   needs new highlight/location geometry in the detector.
4. **P021's `original_page` (no-highlight) card** shows no `no_highlight_reason` text
   at all on the primary findings list — the only signal that no highlight box will
   appear is the one-word difference between "Open highlighted PDF page" and "Open
   original PDF page" button labels. This is a structural template gap shared by *all*
   `original_page`-action findings (not P021-specific), already documented as a known
   risk in this audit's research phase. A fix would mean deciding whether to surface
   `no_highlight_reason` on the primary card template (a modest UI change, arguably
   beyond "narrow wording fix") — **flagged as a candidate for the next UI-focused
   slice**, not attempted here.
5. **Duplicated `"flagged issue type"` / privacy-leak-probe constants** across ~6 test
   files (`_GENERIC_MARKERS`, `_GENERIC_COMMENT_MARKERS`, `_BANNED_FALLBACK_PHRASE`,
   etc., all independently equal to the same string) — a test-maintenance
   simplification opportunity, not a product wording bug. Left as-is; consolidating
   into a shared test helper is a good candidate for a future test-cleanup slice but
   was out of scope for a findings-focused audit.

## Questions for Esther / policy later

- Should P011 margin-boundary wording distinguish "just over the line" (1–4pt) from
  clearly-broken layouts, or is uniform strict wording intentional (matching NJIT's
  stated zero-tolerance boundary policy)?
- Is it acceptable for `original_page` (no-exact-highlight) findings to show *no*
  explanatory text on the primary card, relying solely on the "highlighted" vs.
  "original" word in the button label? Or should `no_highlight_reason` be promoted to
  the primary card template?

## Prioritized follow-up slices

1. Highest value, lowest risk: surface `no_highlight_reason` on the primary
   "Findings in page order" card for `original_page`-action findings (currently only
   shown in grouped/advanced views) — addresses the most concrete "looks broken"
   confusion risk found in this audit.
2. P011 borderline-overflow wording — pending Esther/policy input from the question
   above.
3. New highlight geometry for P016/P023 (paragraph/line-level spacing) and P064
   (references entry-level location) — larger, detector-touching work; separate slice.
4. Test-suite consolidation of the duplicated generic-fallback/privacy-leak constants
   — housekeeping, no product impact.
5. Confidence calibration audit (per the user's stated next major task).
