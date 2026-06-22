# Student-Facing Warning Clarity / Actionability Audit — 2026-06-22

**Type:** Read-only audit / gap analysis. No product code, detector logic, tests,
rule IDs, issue types, canonical data, stashes, branches, worktrees, or open PRs
(#311, #349) were modified while producing this report.

**Baseline:** `main` @ `fd508cdacadff5bd1032f0a1a7d7d25c113a8431` (includes merged
PR #348 and PR #350; PR #350 commit `62dde9225bbb6b43b664c7cf41f558e77913b73c`).

**Branch:** `audit/warning-actionability-20260622`
**Worktree:** `../njit-thesis-auditor-warning-actionability-audit`

---

## 1. Executive Summary

This audit inspected all five available sample outputs (built-in Samples A–D plus
the homepage Digital Commons article-4387 URL) on current `main`, covering the
main results page, grouped cards, expanded occurrence rows, rule/category/issue-type
drilldown pages, Markdown export, and desktop vs mobile HTML rendering via
`TestClient`.

**Headline:** Warning clarity is materially better than the live/mobile issue
reported by the user. On current `main`, **confidence is not buried inside warning
paragraphs on the web UI**, and the per-card string
`Automated finding — please verify against NJIT guidelines manually.` **does not
appear on grouped result cards** for any sample tested. If that wording still
appears on a live/mobile page, the most likely cause is **stale deployed code or a
stale cached audit job**, not current `main` wording.

The largest remaining student-facing gaps are:

1. **Missing separate “Suggested fix” lines** on many grouped cards even when the
   polished comment body already contains remediation prose (88 card instances
   across samples for priority rules).
2. **High-volume grouped cards** (especially P036 TOC/List spacing, P020 title-case,
   P026 font-family, P011 margins, P012 annotations) where expanded occurrence
   tables repeat identical text dozens of times without per-row differentiation.
3. **P020 still splits into multiple cards by confidence band** (medium vs high),
   which is not a bug but can look like duplicate warnings to students.
4. **Markdown export** still carries generic manual-check fallback wording for a
   small number of non-specific rule fallbacks (5 lines on Digital Commons, 3 on
   Sample D).
5. **“Review needed:”** prefixes on low-confidence or advisory findings blur the
   distinction between confident problems and items the auditor is only asking the
   student to verify.

**Issue count (documented unclear/actionability gaps):** **42** distinct findings
below (P1: 18, P2: 17, P3: 7). These are structural/pattern issues, not a raw count
of every repeated occurrence row.

---

## 2. Audit Method and Samples Tested

### Repository / environment

| Item | Value |
|---|---|
| Commit tested | `fd508cdacadff5bd1032f0a1a7d7d25c113a8431` |
| Branch | `audit/warning-actionability-20260622` |
| Validation for this PR | `git diff --check` (clean), `git status --short --branch` |
| Full pytest | Not required for doc-only PR; audit generation used live `run_audit_for_uploaded_file` + `build_report_view` + `TestClient` HTML rendering |

### Samples exercised

| Sample ID | Source | Grouped cards | Raw findings |
|---|---|---:|---:|
| `ester_sample_a` | Built-in Sample A | 36 | 325 |
| `ester_sample_b` | Built-in Sample B | 47 | — |
| `ester_sample_c` | Built-in Sample C | 45 | — |
| `ester_sample_d` | Built-in Sample D | 74 | — |
| `digitalcommons_4387` | Homepage example URL (article 4387) | 39 | — |

### Surfaces inspected

- Main job results page (`job.html`): grouped cards, filters, confidence chips/badges, global caveat, triage panels, occurrence tables
- Drilldown pages: rule-level, issue-type-level, category-level (`problem_group.html`)
- Markdown download (`write_markdown_report`)
- JSON/report view fields that feed student display (`report_view.py`, `polished_comments.py`)
- Desktop vs mobile HTML (`User-Agent` iPhone emulation) for Digital Commons and Sample A

### Safety

No dissertation body text, headings, captions, TOC/List entry text, annotation
contents, raw LaTeX, coordinates, or internal paths are quoted below. Examples use
structural references only.

---

## 3. Highest-Priority Unclear Warnings

| Priority | Sample | Rule | Issue type | Problem # | Page(s) | What student sees (paraphrased) | Why unclear | Recommended fix | Layer |
|---|---|---|---|---|---|---|---|---|---|
| P1 | all live/mobile reports | *varies* | *varies* | *varies* | *varies* | Warning paragraph still embeds `Confidence: medium.` plus per-card `Automated finding — please verify…` | **Not reproduced on current `main`.** Matches pre–PR #350 behavior | Deploy current `main`; invalidate stale jobs/cache | deployment |
| P1 | `digitalcommons_4387` | P036 | `toc_inter_entry_spacing_too_tight` | Problems 51–73 | 12 | One card with 23 occurrences; every expanded row shows the same spacing warning with no entry index or gap detail | Student cannot tell which TOC rows differ; looks like 23 duplicate warnings | Add safe per-row structural detail (entry index / gap measurement) or collapse to summary + page-level instruction | UI wording / location enrichment |
| P1 | `digitalcommons_4387` | P020 | `possible_title_capitalization_issue` | Problems 90–91… and 92–93… | 1–3, 7, 62 | Two large cards (15 + 16 occurrences) with identical comment text; split only by confidence band | Looks like duplicate title-case warnings; expanded rows do not identify which heading | Differentiate rows by heading level/role already in metadata; explain why confidence split exists | UI wording / grouping policy |
| P1 | `ester_sample_d` | P036 | `toc_inter_entry_spacing_too_tight` | Problems 311–352 | 12 | 42-occurrence card with identical row text | Same as Digital Commons P036 pattern at larger scale | Same as above | UI wording |
| P1 | `ester_sample_a` | P012 | `pdf_annotation_detected` | high-numbered group | multiple | 78-occurrence annotation card | Overwhelming volume; hard to see which pages matter first | Triage summary is present but card expansion still noisy; consider stronger rollup default | UI grouping (separate in-progress task) |
| P1 | `ester_sample_a`/`b` | P026 | `possible_body_font_family_issue` | multiple groups | body pages | Several font-family cards with 9–44 occurrences each | Same underlying font suspicion repeated across cards/pages | Merge/limit font-family cards per document section; keep one actionable summary | UI grouping + wording |
| P1 | `ester_sample_a` | P011 | `margin_boundary_violation` | Problems 19–25… and 29–30… | 92, 98 | Two margin cards cover the same pages | Same page appears under multiple margin cards (side/context split) | Cross-link cards or merge by page with side listed in row details | UI grouping |
| P1 | `digitalcommons_4387` | P018 | `missing_page_number` | Problems 44, 46–47 | 12, 14–15 | TOC/List entries missing page numbers; only page-level location | Student must scan entire TOC/List page | Add entry-kind label (TOC vs LoT vs LoF) and entry index already captured by detector | UI location enrichment |
| P1 | `digitalcommons_4387` | P035 | `figure_caption_not_below_body` | Problems 36, 38–40 | 52–54 | Caption placement issue with original-page action only | No highlight; coarse location | Prefer highlight when bbox exists; otherwise name figure/table ordinal | UI action + location |
| P1 | `ester_sample_a`–`c` | P051 | `copyright_year_not_found` | Problem 44/60 | copyright page | Copyright-year advisory with comment body but **no separate Suggested fix line** | Fix instructions buried in paragraph | Surface `suggested_fix` on grouped card (year placement guidance) | UI wording |
| P1 | all samples | P019 | `wrong_page_numbering_style` | Problem 3/9/21/33 | document-level | “Review needed” document-level page-number style warning, explanation-only action | No page to open; student may not read explanation accordion | Keep global doc note, but add prominent doc-level callout near top | UI wording |
| P1 | `digitalcommons_4387` | P033 | `frontmatter_title_mismatch` | Problem 19 | front matter | Title mismatch across front-matter roles; no separate Suggested fix line | Good comment body, but fix not scannable | Mirror remediation into `suggested_fix` | UI wording |
| P1 | `ester_sample_d` | P017 | `missing_terminal_punctuation` | Problems 260–261… | 52–54 | 12-occurrence caption punctuation card, no Suggested fix line | Student sees problem statement but not a crisp edit instruction | Populate suggested fix from rule remediation | UI wording |
| P1 | `ester_sample_d` | P024 | `list_of_tables_title_case` | Problems 296–299… | 14–15 | Multiple capitalization cards on same List pages | Fragmented capitalization feedback | Roll up by list page + capitalization rule | UI grouping |
| P1 | `digitalcommons_4387` | P040 | `lof_entry_missing_terminal_punctuation` | Problems 81–85 | 15 | 5-occurrence List-of-Figures punctuation card | Rows differ only by problem number | Add entry index / punctuation expectation per row | UI location enrichment |
| P1 | `ester_sample_d` | P011 | `margin_boundary_violation` | two large groups | 11, 15, 17… | 43- and 21-occurrence margin cards; busy pages up to 13 cards on one page | Page 12/14/15 overwhelming | Page-level problem budget / stronger triage default | UI grouping |
| P1 | `digitalcommons_4387` | P016 | `suspicious_heading_blank_gap` | Problem 30 | heading page | Heading gap warning without Suggested fix line | Missing scannable correction | Surface spacing remediation on card | UI wording |
| P1 | `ester_sample_b`/`c` | P017 | `possible_title_case_issue` | Problem 184 | caption page | Low-confidence title-case on caption; no Suggested fix line | Unclear what word/format to change | Add safe “check terminal words / proper nouns” fix line | UI wording |
| P1 | `ester_sample_d` | P030 | `missing_continued_heading` | Problems 306–308 | multi-page table | Missing “continued” heading warnings, no Suggested fix line | Student knows something is missing, not exact heading format | Add continued-heading template to suggested fix | UI wording |

---

## 4. Rule-by-Rule Clarity Table

Legend: **Clear** = student gets location + problem + fix on card; **Partial** = some elements missing or only in body prose; **Weak** = generic/volumetric/fragmented.

| Rule | Issue types seen | Samples | Location | Problem statement | Fix / next step | Confidence visible | Overall |
|---|---|---|---|---|---|---|---|
| P011 | margin_boundary_violation | A–D, DC | Partial (quadrant label; side in details) | Clear | Clear on most cards | Badge yes | Partial |
| P012 | pdf_annotation_detected | A, B | Page list | Clear after PR #348 | Clear | Badge yes | Partial (volume) |
| P013 | duplicate/ambiguous page number | A–D, DC | Page | Clear | Clear | Badge yes | Clear |
| P015 | missing_later_indent | A–D, DC | Enriched on body pages | Clear | Clear | Badge yes | Clear |
| P016 | excessive gaps / heading gap | A–D, DC | Page | Clear | **Weak** — often no Suggested fix line | Badge mixed | Partial |
| P017 | caption punctuation / title case | B–D, DC | Highlight when available | Clear | **Weak** — fix line often missing | Badge yes | Partial |
| P018 | missing page number / indent | D, DC | Page only for list entries | Clear | **Weak** — fix line missing | Badge yes | Partial |
| P019 | numbering style/sequence/location | A–D, DC | Doc/page mix | Clear | Style cards explanation-only | Badge yes | Partial |
| P020 | title capitalization | A–D, DC | Highlight | Clear | Fix only inside comment; **no Suggested fix line** | Badge yes; splits medium/high | Weak |
| P023 | body spacing | A, B, DC | Body region | Clear | Clear | Badge yes | Clear |
| P024 | list capitalization/punctuation | D, DC | Page | Clear | **Weak** — fix line missing | Badge yes | Partial |
| P026 | font family/size | A–D, DC | Body region | Clear | Clear on card | Badge yes | Partial (volume) |
| P028 | page-number style overlap | A, D | Page/footer context | Clear | Clear | Badge yes | Clear |
| P030 | missing continued heading | D | Page | Clear | **Weak** | Badge yes | Partial |
| P033 | frontmatter title mismatch | DC | Role-based pages | Clear in comment | **Weak** — no fix line | Badge yes | Partial |
| P035 | caption placement / centering | D, DC | Page / highlight mixed | Clear | **Weak** | Badge mixed | Partial |
| P036 | TOC/LoT/LoF spacing | D, DC | Page only | Clear | **Weak** — no fix line; rows identical | Often blank badge on card | Weak |
| P040 | LoF terminal punctuation | DC | Page only | Clear | **Weak** | Badge mixed | Partial |
| P046 | list number column alignment | D | Page | Clear | **Weak** | Badge blank | Partial |
| P051 | copyright year | A–C, DC | Copyright page | Clear in comment | **Weak** — no fix line | Badge blank | Partial |
| P052 | copyright author | — | — | Not seen in these samples | — | — | n/a |
| P053 | list terminal period | D | Page | Clear | **Weak** | Badge blank | Partial |

---

## 5. Confidence-Display Audit

### Current `main` web UI (tested)

| Check | Result |
|---|---|
| Separate confidence badge/line on grouped cards | **Yes** — `confidence-badge` with High/Medium/Low/Needs review/Mixed labels |
| Badge has visible text | **Yes** |
| Color/styling noticeable and distinct from severity | **Yes** — blue/purple/gray palette in `job.html` (PR #350) |
| Color is not the only signal | **Yes** — text label always present |
| Confidence buried in polished_comment paragraph | **No** — 0 instances across all five samples |
| `Needs review` for missing confidence | **Yes** — observed on cards with empty confidence (e.g., some P036/P051 cards) |
| Per-card `Automated finding — please verify…` on web cards | **No** — 0 instances in grouped-card HTML for Sample A and Digital Commons |
| Global caveat near report top/bottom | **Yes** — `job.html` global note present |
| Occurrence table `Confidence` column | **Yes** — separate from comment text |
| Legacy `conf:` muted text | **No** — 0 instances (removed in PR #350) |

### User-reported live/mobile issue — root cause assessment

| Hypothesis | Verdict |
|---|---|
| Stale deployed code (pre–PR #350) | **Most likely** if live site still shows `Confidence: medium.` inside paragraph text |
| Stale audit job / cached HTML | **Possible** — old job artifacts would keep old comment rendering |
| Remaining current-code wording on web UI | **Ruled out** for grouped cards on `fd508cd` |

**Note:** Automated analysis initially flagged “confidence in prose” in HTML because badge text includes strings like `Mixed confidence: Medium, Low`. That is badge text, not paragraph burial.

### Remaining confidence UX gaps

| Priority | Issue | Layer |
|---|---|---|
| P2 | `Review needed:` prefix still appears on many advisory cards and reads like a third confidence system | UI wording |
| P2 | Some high-volume rules (P036) show blank confidence on the grouped card even though row-level confidence exists | UI wiring |
| P3 | Markdown export does not mirror web confidence badges (uses metadata lines only when present) | export formatting |

---

## 6. Repeated Manual-Caveat Audit

| Surface | Per-card `Automated finding — please verify…` | Global caveat | Assessment |
|---|---|---|---|
| Web grouped cards (all samples) | **0** | **Present once** near report footer | **Meets desired standard** |
| `polished_comments.py` non-specific path | Still appended in `_finish_comment()` when `specific=False` | n/a | Fallback path mostly bypassed by specific builders |
| Markdown Sample A/B/C | 0 | n/a | Good |
| Markdown Sample D | 3 generic fallback lines | n/a | Residual |
| Markdown Digital Commons | 5 generic fallback lines | n/a | Residual |

**Finding:** Web UI is in good shape after PR #350. Markdown still repeats manual-check phrasing for a handful of generic fallback findings (rules without specific comment builders). A single global Markdown preamble would be better than repeating fallback caveats.

---

## 7. Duplicate / Redundant-Warning Audit

| Priority | Sample | Rules | Pages | Why duplicate/redundant | Recommendation |
|---|---|---|---|---|---|
| P1 | DC | P020 | 1–3, 7, 62 | Two large title-case cards (15 + 16 occurrences) with same comment | Keep confidence split but add banner “same issue type, different confidence band”; enrich rows |
| P1 | DC/D | P036 | 12–15 | 23–42 identical spacing rows | Per-entry differentiation or summary-only expansion |
| P1 | A/B | P026 | body | Multiple font-family mega-cards | Section-level rollup |
| P1 | A | P011 | 92, 98 | Same page in two margin cards | Merge or cross-link |
| P2 | A | P044 | 1 | Two abstract-indent cards on same page | Merge by page + issue |
| P2 | D | P020 | multiple | Four title-case cards by confidence | Explain relation in card header |
| P2 | D | page 12 | many rules | 13 grouped cards on one page | Triage-first UI for busy pages |
| P3 | A/B | P012 | many | Annotation volume | Already triaged; consider default-collapsed expansion |

**Note:** A separate duplicate-warning implementation task may address some P011/P026/P036 patterns. This audit does not prescribe overlapping implementation details beyond flagging student impact.

---

## 8. Location / Highlight / Action-Button Audit

| Rule / issue | Highlight available? | Button honesty | Location precision | Gap |
|---|---|---|---|---|
| P011 margin | Usually highlight | Honest | Quadrant + side in details | Busy pages |
| P012 annotation | Original page | Honest | Page list only | Volume |
| P015 indent | Highlight | Honest | Enriched body location | Clear |
| P017 caption | Often highlight | Honest | Caption region | Fix line missing |
| P018 TOC/List | Original page | Honest | **Page only** | Needs entry index/kind |
| P019 style | Explanation only | Honest | Document-level | Acceptable with better doc callout |
| P020 title-case | Highlight | Honest | Heading region | Rows need heading role |
| P023 spacing | Highlight | Honest | Body region | Clear |
| P026 font | Highlight | Honest | Body region | Volume |
| P035 caption placement | Often original page only | Honest | Page only | Highlight when possible |
| P036 spacing | Original page | Honest | **Page only** | Needs list entry pointer |
| P038 missing heading | Explanation only | Honest | Document-level | Expected |

**Open original PDF page** buttons are labeled honestly. The main gap is not dishonest buttons but **page-only location when list/caption/heading index already exists in metadata**.

---

## 9. Desktop / Mobile Audit

Tested via `TestClient` with desktop browser UA vs iPhone UA on Sample A and Digital Commons.

| Check | Result |
|---|---|
| Same grouped-card count | Yes |
| Same confidence badge labels/counts | Yes |
| Same problem numbering present | Yes |
| Same action buttons | Yes |
| Same global caveat | Yes |
| Table scroll wrappers present | Yes (`table-scroll` wrappers observed) |
| Content mismatches | **None** |
| Hidden important details on mobile | No evidence — tables scroll instead of crushing |

**Verdict:** Desktop/mobile parity is good for the surfaces tested. If the user still sees old confidence-in-paragraph layout on mobile, suspect deployment/cache rather than responsive template divergence.

---

## 10. Exact-Problem / Category Navigation Audit

Current `main` navigation wording (PR #350) is **mostly honest**:

| Page kind | Kicker / heading | Honest about scope? |
|---|---|---|
| Issue-type page | “Examples of this exact problem” | **Yes** |
| Rule page | “Examples for this rule” / “All examples for this rule” | **Yes** |
| Category page | “Problems in this category” / “All examples in this category” | **Yes** |
| Card button | “Examples of this exact problem” when issue type known | **Yes** |

### Remaining navigation confusion

| Priority | Issue | Recommendation |
|---|---|---|
| P2 | Category page for `list_of_tables_figures_toc` can contain many unrelated issue types | Keep current kicker; add note “multiple issue types on this page” (partially present via `group_explanation`) |
| P3 | Triage panel links to rule page labeled “Examples for this rule” while card uses exact-problem button | Acceptable but students may not understand difference — add one-line scope hint on triage panel |

No evidence that category pages are mislabeled as exact-problem pages on current `main`.

---

## 11. Possible False Positives

| Priority | Sample | Rule | Issue type | Why suspicious | Action |
|---|---|---|---|---|---|
| P2 | DC | P020 | title capitalization | Very high occurrence counts on front-matter headings; APA title-case is inherently fuzzy | Ester/editor policy on threshold vs educational wording |
| P2 | DC/D | P036 | list spacing tight | 23–42 occurrences on one TOC/List page | Confirm detector threshold; improve “which entry” guidance before suppressing |
| P2 | A/B | P012 | pdf_annotation_detected | Annotations may be reviewer comments rather than student errors | Policy: informational vs problem severity |
| P3 | A–C | P051 | copyright_year_not_found | Advisory by design; year may be present but OCR-hard | Keep advisory tone; improve fix scannability |
| P3 | B/C | P017 | possible_title_case_issue | Low confidence on caption | Ensure “Needs review” character is obvious |

---

## 12. Items Needing Ester / Editor Policy Decision

1. Should P020 title-case findings remain **Problems** at medium confidence, or shift more to **Likely problem / Needs review** wording?
2. Should P012 reviewer annotations be **problems** or a separate informational class for student uploads?
3. Should P036 tight-spacing findings be capped per page in the student UI even if detector emits many rows?
4. Should P019 document-level numbering-style warnings appear in the main problem list or only in a dedicated document summary section?
5. Should confidence-based splits (P020 medium vs high) remain separate cards or roll up with confidence shown per row only?

---

## 13. Recommended Implementation Tasks (Ordered by Priority)

1. **Deploy current `main`** (includes PR #350 confidence badges + PR #348 P012 clarity) to resolve live/mobile stale wording reports.
2. **Surface `suggested_fix` on grouped cards** for rules where remediation already exists only inside `polished_comment` (P016, P017, P018, P020, P024, P030, P033, P035, P036, P040, P046, P051, P053).
3. **Enrich occurrence-row location for list/caption rules** using safe structural metadata (entry kind, index, side) without quoting entry text.
4. **Collapse or summarize high-volume occurrence tables** (P036, P020, P026, P012) so expansion adds information density, not repetition.
5. **Markdown export parity** — remove residual per-finding manual-verify fallback repetition; add one global automated-check note.
6. **Busy-page triage** — when a page has 8+ cards (Sample D page 12), default to triage/summary-first presentation.
7. **P019 document-level callout** — elevate numbering-style warnings near the top with explanation-only action.
8. **Cross-link related cards** on the same page (P011 margins, P024 capitalization fragments).

---

## 14. Safe Quick Wins

1. Populate grouped-card `suggested_fix` from existing remediation strings for P051/P033/P016 (data already in comment builders).
2. Add one sentence to P036 grouped card: “Each row is a different list entry on this page; open the original PDF page and inspect list lines top-to-bottom.”
3. Add scope hint on P020 split cards: “This card groups findings with the same confidence level.”
4. Ensure blank-confidence cards (some P036) display **Needs review** badge consistently.
5. Deploy + smoke-test homepage Digital Commons sample on mobile after release.

---

## 15. Larger Follow-Up Tasks

1. Per-entry spacing/indent indices for P036/P018/P040 without exposing entry text.
2. Document-level results panel for P019/P038-style findings.
3. Font-family rollup policy across P026 mega-groups.
4. Annotation handling policy for P012 volume control.
5. Markdown report redesign to mirror web badge semantics.

---

## 16. Final Repository Status

| Item | Value |
|---|---|
| Branch | `audit/warning-actionability-20260622` |
| Based on | `origin/main` @ `fd508cd` |
| Files changed for this PR | `docs/status/warning_actionability_audit_20260622.md` only |
| `git diff --check` | Clean (no conflict markers / whitespace errors) |
| Working tree | Only the audit report staged/committed; LFS pointer noise in worktree left untouched |
| Open PRs left alone | #311, #349 |
| Stash | Not touched |

### Validation run for this audit PR

```
git diff --check          → clean
git status --short --branch → report file only on audit branch
```

### Audit generation commands (local)

- `python /tmp/warning_actionability_audit_runner.py` (structural JSON analysis)
- Supplemental `run_audit_for_uploaded_file` / `build_report_view` probes on all five samples
- `TestClient` HTML desktop/mobile checks for Sample A and Digital Commons

---

## Appendix — Issue Index by Classification

| Classification | Count (distinct findings) |
|---|---:|
| missing expected correction / no Suggested fix line | 16 |
| duplicate/redundant high-volume grouping | 8 |
| only page-level location when more precision is needed | 6 |
| stale deployment / cached results (confidence in prose) | 1 |
| generic boilerplate / Review needed prefix | 4 |
| explanation-only document findings | 3 |
| possible false positive / policy | 4 |
| **Total documented** | **42** |
