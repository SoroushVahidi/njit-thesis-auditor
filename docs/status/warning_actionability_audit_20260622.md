# Student-Facing Warning Clarity / Actionability Audit — 2026-06-22

**Type:** Read-only audit / gap analysis. No product code, detector logic, tests,
rule IDs, issue types, canonical data, stashes, branches, worktrees, or open PRs
(#311, #349) were modified while producing this report.

**Baseline:** `main` @ `fd508cdacadff5bd1032f0a1a7d7d25c113a8431` (includes merged
PR #348 and PR #350; PR #350 commit `62dde9225bbb6b43b664c7cf41f558e77913b73c`).

**Branch:** `audit/warning-actionability-20260622`
**Worktree:** `../njit-thesis-auditor-warning-actionability-audit`

---

## 0. Refresh Status — 2026-06-24

This audit document was refreshed against current `main` after PR #358 (status/doc
cleanup, P020 pattern-note addition) and PR #351 (page-number duplicate-card
dedup) merged. The refresh is presentation-only: no detector logic, thresholds,
rule IDs, issue types, canonical rule data, or private fixture content changed.
Re-verification used the real `run_audit_for_uploaded_file` → `build_audit_report`
→ `sanitize_report_for_web_export` → `build_report_view` pipeline against all
four built-in samples (A–D), plus `write_markdown_report`.

**Resolved since the original 2026-06-22 audit:**

- **Missing "Suggested fix" lines** (Executive Summary #1; Section 4 "Weak —
  fix line missing" rows for P016, P017, P018, P024, P030, P033, P035, P036,
  P040, P046, P051, P053). Verified **0 missing `suggested_fix`** across all of
  these rule IDs in all four built-in samples. `finalize_student_facing_comment_and_fix()`
  / `resolve_suggested_fix_for_display()` in `polished_comments.py` now
  guarantee a non-empty suggested-fix line, falling back to canonical rule
  remediation text when a detector doesn't supply one directly.
- **High-volume grouped cards with no repetition explanation** (Executive
  Summary #2; Section 3 P1 rows for P036, P020, P026, P012). All four now
  produce a `pattern_note` explaining why the card repeats
  (`_high_volume_pattern_note()` in `report_outputs.py`).
- **P011 (margin) high-volume cards had no repetition explanation** — this was
  the one high-volume rule from Section 3/8 still missing a `pattern_note` as
  of this refresh. Added a P011 branch to `_high_volume_pattern_note()`
  (mirrors the existing P026/P036/P012 wording pattern; presentation only).
  Verified via the four built-in samples: P011 groups now carry a pattern note
  in every sample that has one.
- **P020 confidence-band split looking like duplicate warnings** (Executive
  Summary #3) — the P020 `pattern_note` branch now explicitly states that a
  separate card for a different capitalization reason or confidence band "is
  not a duplicate" (landed on `main` ahead of this refresh).
- **Markdown export generic manual-check fallback repetition** (Executive
  Summary #4; Section 6; Section 13 item 5) — verified **0** occurrences of
  the per-finding fallback phrase across all four samples' Markdown exports;
  exactly **one** global preamble line (`> Automated findings require manual
  verification against NJIT guidelines.`) now appears at the top of every
  report instead.
- **P018 / P046 / P024 page-only location** (Section 3 P1 rows for P018 and
  P024; Section 4 rows for P018/P024/P046) — addressed by two already-merged
  commits (`Clarify P018 and P046 list entry locations`,
  `Clarify P024 list-format locations`), which add entry-index / line / section
  location detail using only safe structural metadata.

**Still genuinely open (kept below, not removed):**

- **"Review needed:" prefix vs. confidence badges** (Executive Summary #5;
  Section 5 P2; Section 12 item) — `_finish_comment()` in `polished_comments.py`
  still unconditionally prepends `Review needed:` to every polished comment
  regardless of confidence level. This is a global wording/policy choice
  affecting every comment in the system, not a small presentation fix, and the
  original audit already correctly scoped it as an Ester/editor policy
  decision (Section 12 item 1/5). Not changed in this refresh.
- **Same page covered by multiple P011/P044 cards** (Section 3 P1; Section 7) —
  re-verified as still real: `ester_sample_a` still shows two P011 cards both
  covering pages 92 and 98, and a P044 abstract-indent pair still shares page 1.
  This needs card-level cross-linking or merge-by-page UI grouping work, which
  is beyond a small presentation fix.
- **Busy-page triage / page-level problem budget** (Section 3 P1; Section 13
  item 6) — `ester_sample_d` still produces dense pages (e.g. up to 13 cards on
  one page); no page-level triage budget exists yet.
- **P024 "roll up by list page" grouping** — the 2026-06-22→23 P024 commit
  fixed location clarity (entry index/line) but did not implement the
  separate "merge fragmented capitalization cards per list page" grouping
  recommendation from Section 3/13; that remains open.
- **P019 document-level callout placement**, **P035 highlight-when-possible**,
  and the **Section 11 false-positive / policy items** were not independently
  re-verified in this refresh and should be treated as still open until
  checked.

Section 2's grouped/raw finding counts below are from the original
`fd508cd` baseline and were **not** re-verified in this refresh (the live
pipeline's finding/grouping counts have shifted since, partly because the
original "raw findings" column included non-problem rows that the report view
filters out). Rely on the status notes above and the per-row annotations in
Section 3/4 for current resolution state, not the raw counts in Section 2.

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

The largest remaining student-facing gaps were (see Section 0 for 2026-06-24
refresh status — items 1–4 below are now **RESOLVED**):

1. **[RESOLVED 2026-06-24]** ~~Missing separate "Suggested fix" lines on many
   grouped cards~~ — `polished_comments.py` now guarantees a non-empty
   suggested-fix line on every card for the affected rules.
2. **[RESOLVED 2026-06-24]** ~~High-volume grouped cards (P036 TOC/List
   spacing, P020 title-case, P026 font-family, P011 margins, P012 annotations)
   with no repetition explanation~~ — all five now produce a `pattern_note`.
3. **[RESOLVED 2026-06-24]** ~~P020 splitting into multiple cards by
   confidence band looks like duplicate warnings~~ — the P020 `pattern_note`
   now explicitly explains the split is not a duplicate.
4. **[RESOLVED 2026-06-24]** ~~Markdown export generic manual-check fallback
   wording repeated per finding~~ — now a single global preamble line.
5. **[STILL OPEN — policy decision]** **"Review needed:"** prefixes on
   low-confidence or advisory findings blur the distinction between confident
   problems and items the auditor is only asking the student to verify. See
   Section 12.

**Issue count (documented unclear/actionability gaps):** **42** distinct findings
below as originally documented (P1: 18, P2: 17, P3: 7). Per Section 0, a
majority of these are now resolved; see per-row status notes in Sections 3–4
and the updated Appendix count for the current open total.

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

| Priority | Sample | Rule | Issue type | Problem # | Page(s) | What student sees (paraphrased) | Why unclear | Recommended fix | Layer | Status (2026-06-24 refresh) |
|---|---|---|---|---|---|---|---|---|---|---|
| P1 | all live/mobile reports | *varies* | *varies* | *varies* | *varies* | Warning paragraph still embeds `Confidence: medium.` plus per-card `Automated finding — please verify…` | **Not reproduced on current `main`.** Matches pre–PR #350 behavior | Deploy current `main`; invalidate stale jobs/cache | deployment | Unchanged — deployment/cache issue, not a `main` code gap |
| P1 | `digitalcommons_4387` | P036 | `toc_inter_entry_spacing_too_tight` | Problems 51–73 | 12 | One card with 23 occurrences; every expanded row shows the same spacing warning with no entry index or gap detail | Student cannot tell which TOC rows differ; looks like 23 duplicate warnings | Add safe per-row structural detail (entry index / gap measurement) or collapse to summary + page-level instruction | UI wording / location enrichment | **Partially resolved** — `pattern_note` now explains the repetition; per-row entry-index detail still not added |
| P1 | `digitalcommons_4387` | P020 | `possible_title_capitalization_issue` | Problems 90–91… and 92–93… | 1–3, 7, 62 | Two large cards (15 + 16 occurrences) with identical comment text; split only by confidence band | Looks like duplicate title-case warnings; expanded rows do not identify which heading | Differentiate rows by heading level/role already in metadata; explain why confidence split exists | UI wording / grouping policy | **RESOLVED** — `pattern_note` explains the confidence-band split is not a duplicate |
| P1 | `ester_sample_d` | P036 | `toc_inter_entry_spacing_too_tight` | Problems 311–352 | 12 | 42-occurrence card with identical row text | Same as Digital Commons P036 pattern at larger scale | Same as above | UI wording | **Partially resolved** — same as the Digital Commons P036 row above |
| P1 | `ester_sample_a` | P012 | `pdf_annotation_detected` | high-numbered group | multiple | 78-occurrence annotation card | Overwhelming volume; hard to see which pages matter first | Triage summary is present but card expansion still noisy; consider stronger rollup default | UI grouping (separate in-progress task) | **Partially resolved** — `pattern_note` now explains the repetition; stronger rollup default still not implemented |
| P1 | `ester_sample_a`/`b` | P026 | `possible_body_font_family_issue` | multiple groups | body pages | Several font-family cards with 9–44 occurrences each | Same underlying font suspicion repeated across cards/pages | Merge/limit font-family cards per document section; keep one actionable summary | UI grouping + wording | **Partially resolved** — `pattern_note` now explains the repetition; per-section merge/limit still not implemented |
| P1 | `ester_sample_a` | P011 | `margin_boundary_violation` | Problems 19–25… and 29–30… | 92, 98 | Two margin cards cover the same pages | Same page appears under multiple margin cards (side/context split) | Cross-link cards or merge by page with side listed in row details | UI grouping | **STILL OPEN** — re-verified 2026-06-24: `ester_sample_a` still shows two P011 cards both covering pages 92 and 98. Needs cross-link/merge-by-page UI work, beyond a small presentation fix |
| P1 | `digitalcommons_4387` | P018 | `missing_page_number` | Problems 44, 46–47 | 12, 14–15 | TOC/List entries missing page numbers; only page-level location | Student must scan entire TOC/List page | Add entry-kind label (TOC vs LoT vs LoF) and entry index already captured by detector | UI location enrichment | **RESOLVED** — landed via `Clarify P018 and P046 list entry locations` |
| P1 | `digitalcommons_4387` | P035 | `figure_caption_not_below_body` | Problems 36, 38–40 | 52–54 | Caption placement issue with original-page action only | No highlight; coarse location | Prefer highlight when bbox exists; otherwise name figure/table ordinal | UI action + location | **STILL OPEN** — not re-verified/addressed in this refresh |
| P1 | `ester_sample_a`–`c` | P051 | `copyright_year_not_found` | Problem 44/60 | copyright page | Copyright-year advisory with comment body but **no separate Suggested fix line** | Fix instructions buried in paragraph | Surface `suggested_fix` on grouped card (year placement guidance) | UI wording | **RESOLVED** — verified 0 missing `suggested_fix` for P051 |
| P1 | all samples | P019 | `wrong_page_numbering_style` | Problem 3/9/21/33 | document-level | “Review needed” document-level page-number style warning, explanation-only action | No page to open; student may not read explanation accordion | Keep global doc note, but add prominent doc-level callout near top | UI wording | **STILL OPEN** — not re-verified/addressed in this refresh |
| P1 | `digitalcommons_4387` | P033 | `frontmatter_title_mismatch` | Problem 19 | front matter | Title mismatch across front-matter roles; no separate Suggested fix line | Good comment body, but fix not scannable | Mirror remediation into `suggested_fix` | UI wording | **RESOLVED** — verified 0 missing `suggested_fix` for P033 |
| P1 | `ester_sample_d` | P017 | `missing_terminal_punctuation` | Problems 260–261… | 52–54 | 12-occurrence caption punctuation card, no Suggested fix line | Student sees problem statement but not a crisp edit instruction | Populate suggested fix from rule remediation | UI wording | **RESOLVED** — verified 0 missing `suggested_fix` for P017 |
| P1 | `ester_sample_d` | P024 | `list_of_tables_title_case` | Problems 296–299… | 14–15 | Multiple capitalization cards on same List pages | Fragmented capitalization feedback | Roll up by list page + capitalization rule | UI grouping | **Partially resolved** — `Clarify P024 list-format locations` added location detail; the "roll up by list page" card-merge ask is **still open** |
| P1 | `digitalcommons_4387` | P040 | `lof_entry_missing_terminal_punctuation` | Problems 81–85 | 15 | 5-occurrence List-of-Figures punctuation card | Rows differ only by problem number | Add entry index / punctuation expectation per row | UI location enrichment | **Partially resolved** — verified 0 missing `suggested_fix` for P040; per-row entry-index enrichment not re-verified |
| P1 | `ester_sample_d` | P011 | `margin_boundary_violation` | two large groups | 11, 15, 17… | 43- and 21-occurrence margin cards; busy pages up to 13 cards on one page | Page 12/14/15 overwhelming | Page-level problem budget / stronger triage default | UI grouping | **Partially resolved** — `pattern_note` now explains why each margin card repeats; busy-page triage budget still open |
| P1 | `digitalcommons_4387` | P016 | `suspicious_heading_blank_gap` | Problem 30 | heading page | Heading gap warning without Suggested fix line | Missing scannable correction | Surface spacing remediation on card | UI wording | **RESOLVED** — verified 0 missing `suggested_fix` for P016 |
| P1 | `ester_sample_b`/`c` | P017 | `possible_title_case_issue` | Problem 184 | caption page | Low-confidence title-case on caption; no Suggested fix line | Unclear what word/format to change | Add safe “check terminal words / proper nouns” fix line | UI wording | **RESOLVED** — verified 0 missing `suggested_fix` for P017 |
| P1 | `ester_sample_d` | P030 | `missing_continued_heading` | Problems 306–308 | multi-page table | Missing “continued” heading warnings, no Suggested fix line | Student knows something is missing, not exact heading format | Add continued-heading template to suggested fix | UI wording | **RESOLVED** — verified 0 missing `suggested_fix` for P030 |

---

## 4. Rule-by-Rule Clarity Table

Legend: **Clear** = student gets location + problem + fix on card; **Partial** = some elements missing or only in body prose; **Weak** = generic/volumetric/fragmented.

Status column added 2026-06-24; original `Fix / next step` / `Overall` ratings
left as written, with a refresh note appended where verified resolved.

| Rule | Issue types seen | Samples | Location | Problem statement | Fix / next step | Confidence visible | Overall | Refresh note (2026-06-24) |
|---|---|---|---|---|---|---|---|---|
| P011 | margin_boundary_violation | A–D, DC | Partial (quadrant label; side in details) | Clear | Clear on most cards | Badge yes | Partial | `pattern_note` added for high-volume groups; cross-link/merge-by-page still open |
| P012 | pdf_annotation_detected | A, B | Page list | Clear after PR #348 | Clear | Badge yes | Partial (volume) | `pattern_note` added; rollup default still open |
| P013 | duplicate/ambiguous page number | A–D, DC | Page | Clear | Clear | Badge yes | Clear | Unchanged |
| P015 | missing_later_indent | A–D, DC | Enriched on body pages | Clear | Clear | Badge yes | Clear | Unchanged |
| P016 | excessive gaps / heading gap | A–D, DC | Page | Clear | **Weak** — often no Suggested fix line | Badge mixed | Partial | **RESOLVED** — `suggested_fix` now always populated |
| P017 | caption punctuation / title case | B–D, DC | Highlight when available | Clear | **Weak** — fix line often missing | Badge yes | Partial | **RESOLVED** — `suggested_fix` now always populated |
| P018 | missing page number / indent | D, DC | Page only for list entries | Clear | **Weak** — fix line missing | Badge yes | Partial | **RESOLVED** — fix line populated; location enriched via `Clarify P018 and P046 list entry locations` |
| P019 | numbering style/sequence/location | A–D, DC | Doc/page mix | Clear | Style cards explanation-only | Badge yes | Partial | Not re-verified this refresh |
| P020 | title capitalization | A–D, DC | Highlight | Clear | Fix only inside comment; **no Suggested fix line** | Badge yes; splits medium/high | Weak | **RESOLVED** — fix line populated; `pattern_note` explains confidence-band split |
| P023 | body spacing | A, B, DC | Body region | Clear | Clear | Badge yes | Clear | Unchanged |
| P024 | list capitalization/punctuation | D, DC | Page | Clear | **Weak** — fix line missing | Badge yes | Partial | **Partially resolved** — fix line populated; location enriched via `Clarify P024 list-format locations`; per-page rollup still open |
| P026 | font family/size | A–D, DC | Body region | Clear | Clear on card | Badge yes | Partial (volume) | `pattern_note` added; per-section merge/limit still open |
| P028 | page-number style overlap | A, D | Page/footer context | Clear | Clear | Badge yes | Clear | Unchanged |
| P030 | missing continued heading | D | Page | Clear | **Weak** | Badge yes | Partial | **RESOLVED** — `suggested_fix` now always populated |
| P033 | frontmatter title mismatch | DC | Role-based pages | Clear in comment | **Weak** — no fix line | Badge yes | Partial | **RESOLVED** — `suggested_fix` now always populated |
| P035 | caption placement / centering | D, DC | Page / highlight mixed | Clear | **Weak** | Badge mixed | Partial | **RESOLVED** (fix line) — `suggested_fix` now always populated; highlight-when-possible not re-verified |
| P036 | TOC/LoT/LoF spacing | D, DC | Page only | Clear | **Weak** — no fix line; rows identical | Often blank badge on card | Weak | **Partially resolved** — fix line populated; `pattern_note` explains repetition; per-row differentiation still open |
| P040 | LoF terminal punctuation | DC | Page only | Clear | **Weak** | Badge mixed | Partial | **RESOLVED** (fix line) — `suggested_fix` now always populated |
| P046 | list number column alignment | D | Page | Clear | **Weak** | Badge blank | Partial | **RESOLVED** — fix line populated; location enriched via `Clarify P018 and P046 list entry locations` |
| P051 | copyright year | A–C, DC | Copyright page | Clear in comment | **Weak** — no fix line | Badge blank | Partial | **RESOLVED** — `suggested_fix` now always populated |
| P052 | copyright author | — | — | Not seen in these samples | — | — | n/a | Not seen in this refresh either |
| P053 | list terminal period | D | Page | Clear | **Weak** | Badge blank | Partial | **RESOLVED** (fix line) — `suggested_fix` now always populated |

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

| Priority | Sample | Rules | Pages | Why duplicate/redundant | Recommendation | Status (2026-06-24) |
|---|---|---|---|---|---|---|
| P1 | DC | P020 | 1–3, 7, 62 | Two large title-case cards (15 + 16 occurrences) with same comment | Keep confidence split but add banner “same issue type, different confidence band”; enrich rows | **RESOLVED** — `pattern_note` now states this explicitly |
| P1 | DC/D | P036 | 12–15 | 23–42 identical spacing rows | Per-entry differentiation or summary-only expansion | **Partially resolved** — `pattern_note` explains repetition; per-entry differentiation still open |
| P1 | A/B | P026 | body | Multiple font-family mega-cards | Section-level rollup | **Partially resolved** — `pattern_note` explains repetition; section-level rollup still open |
| P1 | A | P011 | 92, 98 | Same page in two margin cards | Merge or cross-link | **STILL OPEN** — re-verified 2026-06-24, same pages still split across two cards |
| P2 | A | P044 | 1 | Two abstract-indent cards on same page | Merge by page + issue | **STILL OPEN** — re-verified 2026-06-24, still two cards on page 1 |
| P2 | D | P020 | multiple | Four title-case cards by confidence | Explain relation in card header | **RESOLVED** — same `pattern_note` change as the DC P020 row above |
| P2 | D | page 12 | many rules | 13 grouped cards on one page | Triage-first UI for busy pages | **STILL OPEN** — no page-level triage budget implemented |
| P3 | A/B | P012 | many | Annotation volume | Already triaged; consider default-collapsed expansion | **Partially resolved** — `pattern_note` explains repetition; default-collapsed expansion still open |

**Note:** A separate duplicate-warning implementation task may address some P011/P026/P036 patterns. This audit does not prescribe overlapping implementation details beyond flagging student impact.

---

## 8. Location / Highlight / Action-Button Audit

| Rule / issue | Highlight available? | Button honesty | Location precision | Gap |
|---|---|---|---|---|
| P011 margin | Usually highlight | Honest | Quadrant + side in details | Busy pages |
| P012 annotation | Original page | Honest | Page list only | Volume |
| P015 indent | Highlight | Honest | Enriched body location | Clear |
| P017 caption | Often highlight | Honest | Caption region | **RESOLVED 2026-06-24** — fix line now populated |
| P018 TOC/List | Original page | Honest | **Page only** | **RESOLVED 2026-06-24** — entry index/kind added via `Clarify P018 and P046 list entry locations` |
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

1. **Deploy current `main`** (includes PR #350 confidence badges + PR #348 P012 clarity) to resolve live/mobile stale wording reports. — *[OPEN — deployment action, outside this repo's PRs]*
2. **[DONE 2026-06-24]** ~~Surface `suggested_fix` on grouped cards~~ for rules where remediation already exists only inside `polished_comment` (P016, P017, P018, P020, P024, P030, P033, P035, P036, P040, P046, P051, P053). Verified 0 missing across all listed rules.
3. **Enrich occurrence-row location for list/caption rules** using safe structural metadata (entry kind, index, side) without quoting entry text. — *[PARTIALLY DONE — P018/P046/P024 landed; P036/P040/P011 side-detail still open]*
4. **[DONE 2026-06-24]** ~~Collapse or summarize high-volume occurrence tables~~ (P036, P020, P026, P012, **and P011**) — all now carry a `pattern_note` explaining the repetition. (Per-row differentiation / section-level rollup beyond the explanatory note remains a larger follow-up, see Section 15.)
5. **[DONE 2026-06-24]** ~~Markdown export parity~~ — verified 0 residual per-finding manual-verify fallback lines; one global automated-check note now present.
6. **Busy-page triage** — when a page has 8+ cards (Sample D page 12), default to triage/summary-first presentation. — *[STILL OPEN]*
7. **P019 document-level callout** — elevate numbering-style warnings near the top with explanation-only action. — *[STILL OPEN — not re-verified]*
8. **Cross-link related cards** on the same page (P011 margins, P024 capitalization fragments). — *[STILL OPEN — re-verified 2026-06-24, P011/P044 page overlap still reproduces]*

---

## 14. Safe Quick Wins

1. **[DONE 2026-06-24]** ~~Populate grouped-card `suggested_fix` from existing remediation strings for P051/P033/P016~~ — done for these and all other rules flagged in Section 4.
2. **[SUPERSEDED 2026-06-24]** ~~Add one sentence to P036 grouped card...~~ — superseded by the more general `pattern_note` mechanism, which now covers P036 (and P020/P026/P012/P011).
3. **[SUPERSEDED 2026-06-24]** ~~Add scope hint on P020 split cards...~~ — superseded by the P020 `pattern_note` branch, which states the same thing in more detail.
4. Ensure blank-confidence cards (some P036) display **Needs review** badge consistently. — *[STILL OPEN — not re-verified]*
5. Deploy + smoke-test homepage Digital Commons sample on mobile after release. — *[OPEN — deployment action, outside this repo's PRs]*

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
| Based on | `origin/main` @ `fd508cd` (original); refreshed 2026-06-24 against `main` @ `6f1fe259` (post PR #358, PR #351) |
| Files changed for this PR | `docs/status/warning_actionability_audit_20260622.md`; refresh also adds a small P011 `pattern_note` fix in `src/njit_auditor/report_outputs.py` and `tests/test_high_volume_warning_clarity.py` |
| `git diff --check` | Clean (no conflict markers / whitespace errors) |
| Working tree | Only the audit report staged/committed; LFS pointer noise in worktree left untouched |
| Open PRs left alone | #311, #349 |
| Stash | Not touched |

### 2026-06-24 refresh notes

This branch was refreshed from current `main` after PR #358 and PR #351 merged.
See Section 0 for the full resolved/open breakdown. No detector logic,
thresholds, rule IDs, issue types, canonical rule data, or binary/private
fixture files were touched. Stashes, PR #349, and PR #311 were left untouched.

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

| Classification | Count (distinct findings) | Status (2026-06-24 refresh) |
|---|---:|---|
| missing expected correction / no Suggested fix line | 16 | **RESOLVED** — verified 0 missing `suggested_fix` across every affected rule |
| duplicate/redundant high-volume grouping | 8 | **Partially resolved** — `pattern_note` now explains the repetition on every high-volume rule named in this audit (P036, P020, P026, P012, plus P011 added in this refresh); the structural asks (cross-link P011/P044 same-page cards, busy-page triage budget, per-section rollup) are still open — see Sections 3/7/13 |
| only page-level location when more precision is needed | 6 | **Partially resolved** — P018/P046/P024 entry-index/location landed; P036/P040/P011 side-detail not re-verified |
| stale deployment / cached results (confidence in prose) | 1 | Unchanged — deployment/cache issue, not a `main` code gap |
| generic boilerplate / Review needed prefix | 4 | **Partially resolved** — Markdown per-finding fallback repetition is gone (0 occurrences); the `Review needed:` prefix itself is unchanged and remains an open policy item (Section 12) |
| explanation-only document findings | 3 | Not re-verified this refresh |
| possible false positive / policy | 4 | Not re-verified this refresh |
| **Total documented** | **42** | One row fully resolved (16), the rest partially resolved or not re-verified — see Section 0 |
