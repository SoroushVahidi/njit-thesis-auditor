# Highlight Quality & Correctness Audit

**Date:** 2026-07-06
**Baseline:** `origin/main` @ `e6973cb0326e5a3c47ef5a91e4aaeaaf87659a98` (PR #473), 0 open PRs.
**Scope:** PDF highlight correctness/quality only — not detector policy, not branch cleanup.
**Environment:** scratch worktree `wt-highlight-audit` (not the live deployment), scratch
uvicorn on port 8020 (live service on 8000 and vllm on 8010 untouched throughout).

---

## Executive summary

The highlight pipeline (`highlight_targeting.py` → `pdf_highlight.py` → `web_app.py`
routes → `job.html`/`problem_group.html`) is, at the geometry level, in good shape: the
last few weeks of work (PRs #327–#437) propagated real per-line/per-region bboxes to
almost every rule that has one available, and P011 (margins) and P035 (figure/table
placement) are genuinely good reference implementations — tight, accurate regions, not
guesses.

However, this audit found **one significant, currently-live correctness bug** that
undermines a large fraction of those otherwise-good highlights, plus a smaller set of
real "too broad" / "missing" / "inconsistent" issues worth narrow follow-up work.

**Headline finding (fixed in this PR):** on the main results page's individual-findings
list — the default, page-ordered view students see first — every "Open highlighted PDF
page" / "Open original PDF page" link was built from the *displayed* (page-sorted) list
position, but the server resolved that position against the finding list's *storage*
order, which is not page-sorted. The two orders differ for effectively every audit, so
clicking a card's highlight link would silently open a **plain, non-highlighted page**
(the common case) or, in principle, a **different finding's box** on a page that
happens to be shared (the more concerning case) — a direct instance of "the card says
one thing, the highlight shows another." This was introduced by PR #459 (2026-07-05,
two commits before the audited baseline) and was live on production. See [Finding
1](#finding-1-finding_index-displaystorage-order-mismatch-fixed) for the full
root-cause trace and the fix applied in this PR.

Everything else found is scoped, narrow, and left as a documented follow-up per the
task's guardrails (no detector/threshold/confidence changes in this PR):

- P019's `sequence_gap` issue type highlights the Arabic-numeral case but not the
  structurally identical Roman-numeral case (a two-line asymmetry, not a design
  decision).
- P023 (double-spacing) highlights the *entire* measured body-text block on the page
  for what is a page-wide statistical finding — technically not "wrong" but broad
  enough to read as "the whole page is the problem," which isn't quite what the finding
  means.
- P064 (References hanging-indent) has no highlight at all, and — more importantly —
  always reports the References heading's own page, not necessarily the page the
  inconsistent entries are actually on.
- P011's margin-boundary "guide" line (marking the required margin) and its
  "violation" box (marking the actual overflowing text) are drawn in the exact same
  color/style with no legend anywhere explaining the difference.

Full detail, per-rule matrix, and prioritization below.

---

## Samples tested

| Sample | Source | Notable rule coverage |
|---|---|---|
| `ester_sample_a` | built-in, "First Review (EF-annotated)" | P011, P012, P013, P015, P016, P019, P020, P027, P028, P038, P044, P051 |
| `ester_sample_b` | built-in, "Second review with EF feedback" | + P017, P023, P026 |
| `ester_sample_c` | built-in, "Second review with EF comments" | same family as sample_b |
| `ester_sample_d` | built-in, "Fourth review compressed (EF-annotated)" | **P011, P013, P017, P018, P019, P020, P024, P026, P027, P028, P029, P030, P035, P036, P037, P038, P044, P046, P053, P054, P068** — the single richest sample, covering nearly every rule in the task's required list |

All four are the app's own curated built-in samples (`web_samples.py`); no private
documents were uploaded, no dissertation body text or screenshots were committed to the
repo. One diagnostic PNG render of a highlighted page was viewed locally to confirm box
placement and was kept in the session scratch directory only (never written to the
repo).

**P014** (front-matter heading centering) and **P040** (List of Figures terminal
punctuation) do not occur in any of the four samples. Both were verified by direct
source inspection (`pdf_headings.py`, `pdf_lof_terminal_punctuation.py`) to already
carry a correct `bbox` in `details`, matching the pattern used by their sibling rules
(P053/P054 for P040; P027/P038 for P014) — confirmed by reading the code, not by a live
render.

---

## Rule-by-rule highlight matrix

| Rule | Issue type(s) | Highlight exists? | What's highlighted | Matches message? | No-highlight OK? | Risk classification |
|---|---|---|---|---|---|---|
| P011 | margin_boundary_violation | Yes | Tight per-group union of contiguous violating lines + a thin boundary-guide rectangle at the required margin | Yes | n/a | **Good** (see caveat: guide vs. violation box are visually identical — minor polish) |
| P012 | pdf_annotation_detected | Yes | The exact PDF annotation rect | Yes | n/a | Good (reference implementation, oldest) |
| P013 | page_number_candidate | Yes | The candidate token's own line | Yes | n/a | Good |
| P013 | p013_document_overview | No | — (doc-level aggregate) | n/a | Yes | Should not highlight — correct as-is |
| P014 | frontmatter_heading_layout_issue / _not_centered | Yes | The heading line's visible-text bbox | Yes | n/a | Good (code-verified, no live sample) |
| P015 | missing_later_indent | Yes | First line of the flagged paragraph | Yes | n/a | Good |
| P016 | excessive_line_gap / excessive_paragraph_gap / suspicious_heading_blank_gap | **No** | — | n/a | Debatable | **Missing but useful** — message names an exact `largest_gap_pt`; no bbox exists anywhere in `pdf_spacing.py` |
| P017 | all 4 issue types | Yes | Exact caption line | Yes | n/a | Good |
| P018 | inconsistent_hierarchy_indent, missing_page_number | Yes | Entry line (worst-entry when grouped) | Yes | n/a | Good; wrapped continuation lines not unioned (minor) |
| P019 | multiple_page_numbers, inconsistent_position, sequence_gap (**arabic only**) | Yes (partial) | Candidate's line | Yes when present | Partial | **Inconsistent** — see [Finding 2](#finding-2-p019-roman-sequence_gap-missing-bbox) |
| P019 | missing_page_number, mixed_numbering_style, sequence_gap (**roman**) | No | — | n/a | Yes for missing/mixed (no single token exists); **no** for roman sequence_gap (arabic sibling has one) | Missing but useful (roman gap only) |
| P020 | possible_title_capitalization_issue | Yes | Shrunk to the flagged word (`_TOKEN_HIGHLIGHT_RULES`) | Yes | n/a | Good |
| P023 | possible_body_text_not_double_spaced | Yes | Union of **every** measured body line on the page | Technically yes, but very broad | n/a | **Present but broad** — see [Finding 3](#finding-3-p023-over-broad-highlight-region) |
| P024 | list_of_figures_sentence_case, list_of_tables_title_case, unexpected_terminal_punctuation | Yes | Entry line (word-shrunk for the sentence-case variant) | Yes | n/a | Good |
| P026 | possible_body_font_family/size_issue | Yes | First violating span | Yes | n/a | Good |
| P027 | level1–5 variants | Yes | Line (word-shrunk for level 3–5 sentence/punctuation) | Yes | n/a | Good |
| P028 | frontmatter/body page-number style issues | Yes | Candidate's line | Yes | n/a | Good |
| P029 | roman_sequence_repeat/gap | Yes | Candidate's line | Yes | n/a | Good |
| P030 | missing_continued_heading | No | — (heading absent by definition) | n/a | Yes | Should not highlight — correct |
| P035 | figure/table caption placement, body-not-centered | Yes | `body_bbox` ∪ `caption_bbox` (placement) or body block (centering) | Yes | n/a | **Good — reference implementation** |
| P036 | LoF/LoT/TOC inter-entry spacing | Yes | The specific gap region between the two entries | Yes | n/a | Good |
| P037 | roman_bio_sketch_not_iv, roman_section_wrong_value | Yes | Candidate's line | Yes | n/a | Good |
| P038 | heading_phrase_not_exact | Yes | Heading line | Yes | n/a | Good |
| P038 | required_heading_missing | No | — (heading absent) | n/a | Yes | Should not highlight — correct |
| P040 | missing_terminal_punctuation (LoF) | Yes | Full entry line | Yes | n/a | Good (code-verified, no live sample) |
| P044 | abstract indent issues | Yes | Paragraph's first line | Yes | n/a | Good |
| P046 | LoF/LoT entry-number column misaligned | Yes | Worst-offending entry's line (not the full column) | Mostly | n/a | Acceptable; full-column union is a documented future enhancement, not a defect |
| P051 | copyright_year_not_found | No | — (value absent) | n/a | Yes | Should not highlight — correct |
| P053 | lot_entry_has_terminal_period | Yes | Full entry line | Yes | n/a | Good |
| P054 | toc_entry_has_terminal_period | Yes | Full entry line | Yes | n/a | Good |
| P064 | references_structural_issue (hanging indent) | No | — | n/a | Debatable | **Present but misleading location** — see [Finding 4](#finding-4-p064-references-no-geometry-and-page-may-be-wrong) |
| P068 | approval_page_advisor_role_label_missing, _signature_blocks_sparse | No | — (page-wide count-based finding) | n/a | Yes, currently | Acceptable as explanation-only; a full committee-block region highlight is a plausible future enhancement, following the P035 pattern |

---

## Finding 1: `finding_index` display/storage-order mismatch (FIXED)

### Root cause

- `web_app.py`'s `_run_audit_task` stores `job.findings` in whatever order
  `build_report_view()` produced (`view_dict["findings"]`), **not** page order.
- `job_page()` (the `/audits/{job_id}` route) calls
  `sort_findings(job.findings, sort_mode)` and passes the **result** to the template as
  `findings`. `SORT_MODE_DEFAULT` (used on every first page load, with no `?sort=` in
  the URL) sorts by page — a real reorder relative to storage order, confirmed
  empirically (`job.findings[76]` in storage order landed on a page-117 finding; the
  same position after the default page-order sort landed on a page-13 finding, for the
  same job).
- `job.html`'s individual-findings loop (`{% for f in findings %}`, the section
  matching the task's "Findings in page order with compact cards") builds each
  highlight/page-action link with `finding_index=loop.index0` — the position in the
  **displayed** (sorted) list.
- Server-side, `_matching_findings_for_highlight()` in `web_app.py`, when given a
  `finding_index`, looks up `job.findings[finding_index]` — the **storage**-order list —
  and derives the page/rule_id/issue_type to search for from *that* (generally
  unrelated) finding, ignoring the correct `page`/`rule_id`/`issue_type` query
  parameters that were also present in the same URL (built correctly, from the actually
  -displayed finding).
- Net effect: the finding used to select which boxes to draw is essentially random
  relative to the card the student is looking at. In practice this almost always
  produces a page mismatch, which the existing `boxes_by_page.get(page)` fallback
  quietly serves as a plain, non-highlighted single page — but if the wrongly-resolved
  finding happens to land on the same page as the displayed one, the wrong rule's box
  would be drawn under the right rule's card, with no error or signal to the student.

### Reproduction

Confirmed live, end to end, on `ester_sample_d`: the rendered card for a P054 finding
(page 13) linked to
`/audits/{job}/highlighted-page.pdf?page=13&rule_id=P054&issue_type=toc_entry_has_terminal_period&finding_index=76`.
Fetching that exact URL returned **200 OK with zero annotations** (silent plain-page
fallback), while the same page/rule/issue_type **without** `finding_index` correctly
drew the highlight box. Tracing `job.findings[76]` in storage order showed it was
actually a **P011** finding on **page 117** — nothing to do with the displayed P054
card.

### Scope

- Only affects `action_kind in ("highlight", "original_page")` links rendered in
  **job.html's flat individual-findings list** (lines ~615/630) — the main, default,
  page-ordered results view.
- **Not affected:** `problem_group.html` (category/rule/issue-type drill-down pages)
  and job.html's grouped "individual occurrences" table (line ~809) — both already
  build highlight links from `page`/`rule_id`/`issue_type` alone, with no
  `finding_index`, which is the correct pattern.
- `action_kind == "original_page"` links resolve via `_pdf_original_page_url(page=...)`
  alone (no finding_index involved at all in the URL target), so those were never
  actually broken in terms of *where* they navigate — only the `highlight`-kind links
  were functionally broken.

### Fix applied

Removed `finding_index=loop.index0` from both link-building call sites in
`templates/job.html`'s individual-findings loop, matching the already-correct pattern
used everywhere else in the codebase (drill-down pages, grouped occurrences table).
`_pdf_action_url`'s `finding_index` parameter already defaults to `None`, so this is a
pure subtraction — no `web_app.py` or `report_view.py` change needed. The trade-off
(multiple same-page/same-rule/same-issue-type findings on the main list now aggregate
all their boxes together, rather than isolating one) is the same trade-off the
already-tested, already-correct drill-down pages make, and is far preferable to the
previous silently-wrong/silently-empty behavior.

New regression test:
`tests/test_finding_index_page_order_consistency.py` — constructs two findings whose
page order is the reverse of their storage order, confirms the rendered page contains
no `finding_index=` fragment, and confirms each card's actual highlight link opens a
highlight on the page that card claims (not the other finding's page). Verified to
**fail** against the pre-fix template (reproduced the exact bug) and **pass** after the
fix.

---

## Finding 2: P019 Roman `sequence_gap` missing bbox

In `rules/pdf_page_numbers.py`, the Arabic-numeral `sequence_gap` branch (~line 585)
looks up `_primary_plausible_candidate(by_page.get(page, []))` and attaches its `bbox`
to `details` when available. The Roman-numeral `sequence_gap` branch immediately below
it (~line 618) does not — it never attempts the same lookup, despite `by_page` and
`_primary_plausible_candidate` both being equally available at that call site. Same
rule, same issue type, same underlying data structure — one path highlights, the other
silently doesn't. This reads as an oversight, not an intentional roman/arabic
distinction (nothing about the Roman-numeral case makes the candidate less locatable
than the Arabic one).

**Recommended fix (not applied in this PR — touches a rule/detector file):** mirror the
three lines from the Arabic branch (`primary = _primary_plausible_candidate(...)`;
`if primary is not None and primary.bbox is not None: details["bbox"] = ...`) in the
Roman branch. No threshold, confidence, or detection-logic change — purely exposing
already-computed geometry, following the exact precedent already used one code block
above it.

---

## Finding 3: P023 over-broad highlight region

`rules/pdf_body_spacing.py` computes `bbox` for `possible_body_text_not_double_spaced`
as the union of **every** measured body line on the page (`_union_bbox`, matching every
line contributing to the page's median-gap statistic). The finding's message reports a
specific `median_body_gap_pt`/ratio — a page-wide *pattern*, which is a defensible
reason to highlight broadly — but the resulting box can cover nearly the entire visible
text area of the page, which risks reading to a student as "this whole page is wrong"
rather than "the spacing between lines here doesn't reach double-spacing."

This is not a bug (nothing is mis-measured or mis-placed), but it sits at the boundary
the task asks about explicitly: "are highlights too broad… misleading?" Unlike P011/P035
(where the union is scoped to a specific, bounded violation), P023's union is scoped to
"every line the statistic drew from," which is inherently page-wide by construction.

**Recommendation (not applied — would touch detector output / bbox scope, out of
this PR's safe-fix budget):** either (a) leave as page-level explanation-only (drop the
whole-page bbox, matching P016's current treatment of the same class of statistical
finding), or (b) if a highlight is kept, scope it to a representative sample of the
specific line-pairs whose gap ratio falls short, rather than the full body-block union.
Needs an Ester/policy call on which reads better to a student, not a unilateral
implementation choice.

---

## Finding 4: P064 References — no geometry, and page may be wrong

`rules/pdf_references_citations_structural.py`'s hanging-indent check (`_check_indentation`)
reports only aggregate statistics (`median_indent_px`, `first_line_x`,
`continuation_line_x`, `affected_entry_count`) — no line/entry bbox is ever computed or
stored, so there is no highlight possible today. Separately and more importantly, the
finding's `page` is always the References **heading's** page — for a multi-page
References section, the actual inconsistently-indented entries may be on a *later*
continuation page that the finding never names. A student opening "the" page referenced
by this finding may find nothing wrong there at all if the real offending entries are a
page or two later.

**Recommendation (not applied — requires detector-level changes: computing per-entry
geometry and, ideally, the page(s) the flagged entries actually live on):** track and
expose the specific entry line(s)/page(s) driving `affected_entry_count`, not just the
heading's page. This is a larger lift than the other findings here (new geometry, not
just exposing existing geometry) and should be scoped as its own follow-up.

---

## Good highlight examples

- **P011** (`ester_sample_d`, page 1, right-margin overflow): four separate tight boxes,
  one per contiguous violating text block, each bounded to the actual overflowing
  paragraph — not the whole page, not one arbitrary line — plus a correctly-scoped thin
  boundary-guide line at the exact required margin. Confirmed visually by rendering the
  highlighted PDF page. This directly addresses the original user complaint that
  motivated the whole highlight-quality investigation (a multi-row table/paragraph
  overflow previously only got one row highlighted; it now gets the whole affected
  region).
- **P035** (`ester_sample_d`, pages 62/117/121, caption placement): separate `body_bbox`
  and `caption_bbox` boxes, both real unions of the actual content clusters — the
  reference implementation the other rules' fixes were modeled on.
- **P020/P027 word-level shrinking**: highlights shrink to the exact flagged word
  rather than the whole line, when the finding is genuinely about one word.

## Bad / missing / misleading examples

- **Any P011/P012/etc. card on the main results page, before this PR's fix**: link
  labeled "Open highlighted PDF page" that actually opened a plain page (or, in the
  worst case, a different rule's box) — see Finding 1.
- **P019 roman `sequence_gap`**: message describes an exact page-number token; no way
  to see it, while the identical arabic case can.
- **P023**: highlight technically present but covers most of the page for what reads as
  a narrower complaint.
- **P064**: no highlight, and the page shown may not even be where the problem is.

## Rules where no highlight is acceptable (confirmed correct as-is)

P013 `p013_document_overview`, P016 (all 3 issue types, pending the P023-style policy
call), P019 `missing_page_number`/`mixed_numbering_style`, P030
`missing_continued_heading`, P038 `required_heading_missing`, P051
`copyright_year_not_found`, P068 (both issue types, currently) — every one of these is
either a document-level aggregate or a "the thing is *absent*" finding with no location
to point to. None of these fabricate a highlight; all correctly fall back to
`action_kind="explanation"` or `"original_page"` with an honest reason.

## Rules where highlight should be added (follow-up, not this PR)

P019 roman `sequence_gap` (Finding 2), P064 References (Finding 4, larger lift). P068
could plausibly gain a whole-committee-block region highlight following the P035
pattern, but its current explanation-only behavior is honest and not broken — lower
priority than the two above.

## Rules where highlight should be removed or restricted (needs policy input)

P023 (Finding 3) — candidate for either dropping the highlight (matching P016) or
narrowing its scope; genuinely a judgment call on what reads best to a student, not a
correctness bug.

## Mobile/desktop observations

- Action-button text, link targets, and rendered content are byte-identical between a
  simulated mobile UA/viewport (390px) and desktop (1440px) for `ester_sample_d`'s full
  results page — verified directly in this audit and consistent with the existing
  `test_mobile_desktop_consistency.py`/`test_finding_actionability.py` mobile-parity
  suites.
- No highlight-specific mobile breakpoint exists in `job.html`; the action button
  simply inherits the finding card's existing responsive grid layout
  (`@media (min-width: 720px)`), which is the same layout every other card element
  uses — no separate risk found here beyond what the existing mobile-overflow tests
  already cover.
- The highlighted PDF itself (the rendered box/guide) is identical regardless of the
  viewport that requested it — it's server-rendered into the PDF, not client-side.

## Prioritized follow-up fixes

**Fix now (this PR):**
- `finding_index` display/storage-order mismatch (Finding 1) — implemented, tested,
  validated.

**Minor polish (safe, narrow, recommended next):**
- P011: add one clarifying sentence (or a distinguishing stroke color/style in
  `pdf_highlight.py`, gated to the guide box only) so students can tell the
  boundary-guide line apart from the actual violation box. Not implemented here because
  the existing P011 explanation strings are pinned by exact-text assertions across
  several test files; changing them safely needs its own small, focused PR.
- P019 roman `sequence_gap` bbox (Finding 2) — three-line mirror of the existing Arabic
  branch in `pdf_page_numbers.py`.

**Defer (real lift, own PR):**
- P064 References geometry + correct-page tracking (Finding 4).
- P046/P048 column-region highlighting (currently worst-entry-only; documented as
  acceptable, not broken, in the prior `highlight_quality_improvement_plan.md`).
- P068 whole-committee-block region highlight, following the P035 pattern.

**Needs Ester/policy decision:**
- P023 (Finding 3): keep a broad highlight, narrow it, or drop it — a communication
  judgment call, not a correctness question.
- P016: whether its 3 issue types should ever get a highlight, or should permanently
  stay explanation-only like P023's eventual policy resolution.

---

## Validation

```
ruff check .    → All checks passed!
mypy src        → Success: no issues found in 106 source files
python -m pytest → 2610 passed, 3 warnings (all pre-existing/unrelated)
```

Live deployment (port 8000) was not touched, restarted, or otherwise affected by this
audit. All testing used a scratch worktree (`wt-highlight-audit`) and a scratch uvicorn
instance on port 8020.

---

## Follow-up (2026-07-06): "Open highlighted/original PDF page" button honesty

**Baseline:** `origin/main` @ `affae79` (PR #474 merged and deployed).

A live mobile report showed a "Open highlighted PDF page"-family button that, for a
no-highlight finding, opened what looked like the full multi-page PDF rather than an
isolated page. Investigation found:

- `action_kind == "highlight"` findings already resolved through
  `/audits/{job_id}/highlighted-page.pdf` — a route that always extracts a genuine
  single page (drawing a highlight box when available, or a plain single-page copy
  otherwise via `build_single_page_pdf`). This tier was already correct.
- `action_kind == "original_page"` findings (page known, no bbox) instead resolved
  through `/audits/{job_id}/pdf#page=N` — the **full original PDF** with a `#page=N`
  fragment anchor. `build_highlighted_single_page_pdf`'s own docstring already notes
  browsers should avoid such fragments, since mobile PDF viewers do not reliably honor
  them — exactly matching the reported symptom.

**Fix:** `_pdf_action_url` (`web_app.py`) now routes both action kinds through the same
true single-page endpoint; the now-unused `_pdf_original_page_url` helper was removed.
The visible button text (job.html ×3, problem_group.html ×1, plus the hero action in
`_problem_group_context`) now includes the finding's page number (e.g. "Open
highlighted PDF page 4" / "Open original PDF page 4") — previously the page number
only appeared in the (mobile-invisible) `title` tooltip attribute, so the button text
alone did not make clear that only one specific page would open.

No detector, threshold, confidence, rule ID, or JSON-export change. `finding_index` is
still never used in any rendered link (unaffected by this change, verified again in the
new test file). New tests: `tests/test_pdf_action_button_wording.py` (7 tests) —
button text includes the page number, both action kinds resolve to a true single-page
PDF, explanation-only findings render no PDF action, mobile/desktop parity, no
`finding_index` leakage. 10 pre-existing tests updated to assert the new (intentional)
URL pattern instead of the old `#page=N` fragment for `original_page` findings.

Validation: `ruff check .` clean, `mypy src` clean, `python -m pytest` → 2617 passed.
Live deployment untouched (investigation and fix done in a scratch worktree).
