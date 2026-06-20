# Ester Product-Feedback Implementation Audit — 2026-06-19

**Type:** Read-only audit / gap analysis. No code changes, no commits, no deployment,
no PR merges/closures, no stash actions were performed while producing this report.

**Baseline:** `main` @ `c73b697924e0911de59b57ef59991a5bb8b3a699` (merge of PR #326).

---

## 1. Executive Summary

Ester Farfan's product feedback maps to **14 distinct requirements**. Of these:

- **6 are Implemented**: NJIT-specificity (#1), visual/layout detection at the
  detector layer (#2), location-specific feedback (#8), exact warning/error wording
  (#10), the NJIT-relevant slice of APA title-case logic (#11), and PDF-only/
  privacy-first behavior (#13).
- **6 are Partially implemented**: the YES/NO matrix approach (#3), one-check/
  one-remediation discipline project-wide (#4 — fully done for the explicitly-named
  high-volume rules, not yet for ~70 long-tail issue types), using matrix question
  text verbatim as rule names (#5), using matrix column D verbatim as remediation
  (#7), imitating a human reviewer's PDF comment (#9), and reducing Graduate
  Studies' full-review workload (#12).
- **1 is Implemented at the UI layer specifically** ("what it checks" de-emphasis,
  #6) — counted with the implemented group.
- **1 is Unknown / needs human confirmation**: real-world accuracy before
  demo/official use (#14) — this is a judgment call about live performance against
  fresh dissertations that no amount of git/test inspection can settle.

The codebase is **far more mature on Ester's specific feedback than the stale
project-tracking artifacts suggest**. The matrix-tracking snapshot
(`data/processed/rules/njit_rule_inventory.json`) was last updated **2026-06-08**
and claims only 2 of 79 matrix questions are "implemented" with 60 "partially" and
17 "not implemented" — but cross-referencing its own `implementation_module` field
against the current rule catalog (`data/processed/rules/project_added_rules.json`,
82 entries) shows this snapshot **undercounts current coverage substantially**: for
example, it lists `implementation_module: None` for all 10 List of Tables and all
10 List of Figures questions, yet the current catalog has at least 10 dedicated
P-rules covering exactly that ground (P031, P040, P046, P048–P050, P053, P055,
P056, P059, P061). **Do not use that JSON's `implementation_status` field as a
status source — it is stale.** This report determines current status by reading
the actual detector source, presentation layer, and tests instead.

Validation is clean: `ruff check .`, `mypy src`, and `pytest -q` all pass —
**1580 passed, 1 warning** (the one warning is an intentional `UserWarning` from a
test constructing a malicious duplicate-member ZIP). `main` is up to date with
`origin/main`, working tree clean. Two PRs remain open (#311, #305); one stash is
untouched. See §2.

---

## 2. Phase 1–2: Repository and Validation State

| Item | Value |
|---|---|
| Current branch | `main` |
| Current HEAD | `c73b697924e0911de59b57ef59991a5bb8b3a699` |
| `origin/main` | identical — up to date, nothing to pull/push |
| Working tree | Clean, no untracked files |
| `ruff check .` | **All checks passed!** |
| `mypy src` | **Success: no issues found in 93 source files** |
| `python -m pytest -q` | **1580 passed, 1 warning** in 17.61s |
| Stash | 1 entry, untouched: `stash@{0}: On fix/student-facing-comment-wording: ...` |

**Open PRs:**

| PR | Title | Status | Notes |
|---|---|---|---|
| #311 | Add sub-page location labels for PDF findings | **OPEN on GitHub, but functionally superseded** | Its design (`_build_pdf_sublocation`, literal text-snippet extraction) was reviewed and **rejected on privacy and highlight-policy grounds** (`docs/planning/sub_page_location_labels_rebase_audit.md`), then the *concept* was reimplemented from scratch as a geometry-only `sub_page_location_label()` in PR #326 (now merged, on `main`). PR #311 itself was never merged and should be **closed without merging** as a follow-up action (not performed in this task — out of scope, see acceptance criteria). |
| #305 | Add example NJIT thesis URL to web upload page | OPEN | Conflicts confined to two doc files + one test file; the actual `index.html` feature diff merges cleanly. Low-risk rebase candidate, not yet rebased. |

**Recently merged, relevant to this audit:** #326 (sub-page location labels,
geometry-based reimplementation), #325 (`/healthz` + `/version`), #324
(page-number/margin/font actionability), #323 (P023/P016 issue_type fix), #322
(**Ester YES/NO matrix wording alignment**), #321 (strict PDF highlight policy),
#320 (finding actionability + drilldowns).

**Stash:** contains a since-superseded `bbox`/highlight-eligibility prototype and
`_REMEDIATION_OVERRIDES` for P023/P026/P028 that conflict with what actually
shipped in #320–#324, plus a detector-level wording edit that conflicts with the
established "sanitize at the presentation layer, never edit canonical detector
text" convention. One real, small, **not-yet-recovered** nugget: three test
assertions (`test_p023_suggested_fix_has_no_raw_latex_syntax`,
`test_p026_suggested_fix_has_no_raw_latex_syntax`,
`test_polished_comments_have_no_raw_latex_syntax`) with no current equivalent on
`main`. Not applied or popped in this task.

---

## 3. Requirement-by-Requirement Table

| # | Ester requirement | Status | Evidence in code | Evidence in tests | Evidence in docs | Current user-facing behavior | Gaps | Risk | Recommended next action |
|---|---|---|---|---|---|---|---|---|---|
| 1 | NJIT-specific rules, not generic APA/MLA/IEEE | **Implemented** | `data/processed/rules/project_added_rules.json` — every P-rule's `question`/`rule_definition` is NJIT-specific; `pdf_references_citations_structural.py:33` explicitly disclaims enforcing "Citation style compliance (APA, IEEE, ACM, MLA, Chicago) — advisor-dependent"; `pdf_title_capitalization.py:1-13` scopes itself to NJIT's own Level 1–5 heading convention | `tests/test_p064_references_citations_structural.py` (IEEE-style flush-left explicitly tolerated, not flagged) | `docs/sources/ester_materials.md` ties P020 directly to Ester's `Titles Examples Level 1 to 5.docx` | `/rules` page and `help.html` both state citation-style compliance is **out of scope**, manual-review only | None found | Low | None — re-verify if a new citation-related rule is ever proposed |
| 2 | Visual/layout analysis, not text-only | **Implemented** (detection layer); **Partial** (highlight/UI layer) | `pdf_models.py` `PdfTextSpan.bold/italic/bbox`; `pdf_margins.py` (P011, bbox vs allowed box); `pdf_page_numbers.py` (P013/P019, x/y position); `pdf_headings.py` (P014, bbox-centering + bold flag); `pdf_indentation.py` (P015, bbox.x0); `pdf_body_spacing.py` (P023, line bbox y-deltas); `pdf_font_compliance.py` (P026, span.size); `pdf_figure_table_layout.py` (P035, block clustering/centering, **confirmed wired into `audit_runner.py:266`**); `pdf_dedication_centering_italic.py` (P065, bbox + italic flag) | `tests/test_pdf_rules.py`, `tests/test_margin_font_actionability.py`, `tests/test_pdf_highlight.py` | `docs/planning/sub_page_location_labels_rebase_audit.md` | Findings show page + categorical sub-page label; only P012 gets a real drawn highlight box | Geometry is extracted and used for **detection** in ~10 rules, but `details["bbox"]`/`details["rect"]` is populated by **only P012** (`pdf_annotations.py:31`) — confirmed via `report_view.py:182` (`_BBOX_DETAIL_KEYS`) and a project-wide grep. So "the page as a visual unit" drives detection logic broadly, but a drawn visual highlight is available for one rule family only | Medium | Plumb `bbox` into `details` for P011/P014/P015/P026/P035/P065 (already computed internally, just not stored) — flagged as future work in `docs/planning/finding_actionability_matrix.md` |
| 3 | YES/NO matrix approach | **Partially implemented** | Every P-rule carries a YES/NO-phrased `question` field (`project_added_rules.json`); `/rules` page renders it as the card title (`web_app.py:736-739`, `rules.html:205`) | `tests/test_help_rules.py` | `docs/planning/ester_yesno_matrix_alignment_audit.md` (matrix scope = front-matter only, 79 Q-rows) | Each rule card on `/rules` is headed by a question | Titles are **project-authored paraphrases**, not verbatim matrix text, and often **consolidate several matrix rows into one P-rule question** (e.g. P022's question covers what the matrix splits into Q001/Q008/Q012/Q014 — one per page). Some matrix questions (committee ordering, paragraph-content semantics — see §6.3) have no P-rule at all, by deliberate design | Medium | Decide whether per-page-type Q-granularity is worth splitting P022/P025/P038 further, or whether the current per-page-type interpolation in `polished_comments.py` (e.g. `{page_type}`) is sufficient — likely sufficient, recommend no further splitting |
| 4 | One check, one problem, one remediation | **Implemented** for the named rule set; **Partial** project-wide | Independently re-verified P011,P012,P013,P019,P020,P022,P023,P025,P026,P027,P028,P038,P063 — all have one `_ISSUE_TEMPLATES`/bespoke-builder entry per distinct `issue_type`, no cross-level/cross-subject mixing (e.g. `polished_comments.py:193-224` P027, one template per heading level, level-agnostic fallback if a future level appears) | `tests/test_finding_actionability.py`, `tests/test_margin_font_actionability.py`, `tests/test_page_number_actionability.py`, `tests/test_p063_appendix_body_headings.py` all assert no cross-issue-type wording leakage | `docs/planning/ester_yesno_matrix_alignment_audit.md` §4-5 (root-cause is documented: P027 was the rule Ester's "P020" example actually meant) | Each finding card shows one problem statement + one remediation, scoped to its own issue type | ~70 long-tail `(rule_id, issue_type)` pairs (mostly LoT/LoF entry-numbering family: P041, P051–P058, etc.) still fall through to an **improved generic safety net** rather than a bespoke template — it no longer emits the banned "Formatting check P0XX flagged issue type..." phrase, but is not yet issue-specific prose | Low-Medium | Extend bespoke `_ISSUE_TEMPLATES` coverage to the long-tail rules, prioritized by finding volume in real EF-annotated evaluation data |
| 5 | Use matrix question text as visible names | **Partially implemented** | Same evidence as #3 — question-style naming exists and is real, but text is paraphrased/consolidated, not verbatim | — | — | Visible, but not literally Ester's matrix wording | Same as #3 | Low | Low priority — the question-style convention is the load-bearing part of this ask, not byte-for-byte text match |
| 6 | Remove/de-emphasize redundant "what it checks" | **Implemented** | `templates/rules.html:236-241` — wraps `what_it_checks` in `<details><summary>What it checks (details)</summary>`, collapsed by default; "How to correct it" (`rules.html:242-246`) is **always visible**, no toggle | `tests/test_help_rules.py` (2 tests added in PR #322 for the collapsible markup) | `docs/status/live_deployment_checklist.md` step 9 explicitly checks this | On `/rules`, students see the question + always-visible fix; details are opt-in | `templates/index.html:303-310` has an unrelated `<h2>What it checks</h2>` section — this is a landing-page scope summary ("PDF uploads are checked for..."), not a per-finding redundant block; coincidental heading text, not a violation, but worth renaming to avoid confusion | Low | Optional: rename the `index.html` heading (e.g. "What this tool checks") to avoid lexical overlap with the de-emphasized per-rule block |
| 7 | Use matrix remediation (column D) as "how to fix" | **Partially implemented** | Catalog-level remediation (`project_added_rules.json`) is a **paraphrase**, e.g. P022's catalog remediation reads "Remove any visible page number from the Abstract, Title, Approval, or Copyright page" versus matrix Q001's "Delete the visible page number from the Abstract page." (verified by direct comparison). The **per-finding** remediation actually shown to students (`polished_comments.py:83-87`, P022) interpolates `{page_type}` per actual page, which is much closer to the matrix's one-page-one-sentence style | `tests/test_finding_actionability.py` | `docs/planning/ester_yesno_matrix_alignment_audit.md` | Per-finding remediation is page/issue-specific; the `/rules` catalog page shows the broader paraphrase | The `/rules` reference page text and the live per-finding text are **two different remediation strings** for the same rule — not wrong, but worth being aware this is a two-layer system | Low | None required; optionally tighten the catalog-level text to read more like column D for rules with a single dominant page-type |
| 8 | Feedback identifies where edits are needed | **Implemented** | `pdf_highlight.py::sub_page_location_label()` (12-band categorical vocabulary, e.g. "Header area", "Upper-left area"); `report_view.py:235-248` computes it for every PDF finding; rendered in `job.html` and `problem_group.html` consistently via `_student_location_text()` (`web_app.py:824-836`) | `tests/test_sub_page_location_labels.py` (11 tests), `tests/test_pdf_highlight.py` | `docs/planning/sub_page_location_labels_rebase_audit.md` | Every PDF finding shows "Page N" plus, when geometry is known, a plain-language area label | None — confirmed no raw bbox/coordinates or raw document text rendered in any `.html` template (grepped) | Low | None |
| 9 | Imitate useful human PDF comments | **Partially implemented** | Location (page + area label) + specific problem + specific remediation exist for bespoke-covered rules; `pdf_annotations.py` (P012) only **detects** existing reviewer annotations, there is no feature to **write** findings back into the PDF as new sticky-note/comment annotations | `tests/test_pdf_highlight.py` | `docs/planning/finding_actionability_matrix.md` | Closest analog to a PDF comment today is the highlighted-PDF download for P012 only; everything else is "page + area label + text explanation" in the web UI, not inside the PDF itself | No "export as PDF annotation" feature exists at all (confirmed: no ADD-annotation code path anywhere in `src/`) | Medium | Candidate future feature: write findings into the downloadable PDF as real annotations using PyMuPDF's annotation API (already a dependency) — would directly mirror Ester's current workflow |
| 10 | Exact warning/error messages (what/why/fix) | **Implemented** | Dedicated phrase sweep across templates and presentation Python for "manual verification", "candidate", "possible issue", "verify against NJIT", "automated finding", "flagged issue type", "formatting check", "review needed", "check manually", "what it checks", "Open PDF"/"Open PDF page"/"Open first example page" found **zero bare/standalone occurrences** in student-facing text — every instance is part of a complete explanatory sentence (e.g. `job.html:320`: "All findings are automated signals and require manual verification. Cross-check every flagged item against the official NJIT thesis/dissertation formatting guidelines before submission to your committee reviewer.") | `tests/test_finding_actionability.py`, `tests/test_issue_type_explanations.py` | `docs/status/full_repository_audit_20260619.md` §8 reaches the same conclusion independently | Every "Review needed:" / "candidate" / "manual verification" instance is followed by specific context | "Open PDF page" / "Open first example page" exist **only** as a forbidden-pattern code comment in `web_app.py` and a stale label in the now-superseded `docs/planning/finding_actionability_matrix.md` (pre-#321) — never rendered | Low | Update or annotate `finding_actionability_matrix.md` as historical/superseded so a future reader doesn't mistake its "page-only" column for current behavior |
| 11 | Title/headline capitalization, APA-style logic | **Implemented**, correctly NJIT-scoped | `pdf_title_capitalization.py:28,107,143` — minor-word list explicitly commented "APA/NJIT title-case minor words"; scope is Level 2 headings + table titles only, grounded in Ester's own `Titles Examples Level 1 to 5.docx`; `pdf_references_citations_structural.py` explicitly does **not** extend this to citation-style enforcement | `tests/test_pdf_rules.py` (title-capitalization cases) | `docs/sources/ester_materials.md:27` | Findings state which violation category applies (first-word, after-separator, major-word) without ever quoting the flagged word (privacy-safe) | None — this is the one place "APA" terminology is used, and it is used only insofar as NJIT's own convention happens to match APA's minor-word convention, not as a blanket APA adoption | Low | None |
| 12 | Reduce Graduate Studies manual-review workload | **Partially implemented** | Strong self-check tooling exists: grouped findings, `/rules` reference, JSON/Markdown downloads, `/healthz`+`/version` (`web_app.py:1268-1286`), strict highlight policy. No reviewer-distinct UI, no false-positive dismissal, no PDF-annotation export, 24h job TTL with no persistence, no batch upload — confirmed absent via full-codebase search, not just absent from the UI | `tests/test_deployment_health.py`, `tests/test_web_app.py` | `docs/status/live_deployment_checklist.md`, `docs/planning/gui_scope_and_design.md` | Reduces obviously-wrong submissions reaching Ester by catching them before submission; does **not** yet give Ester a faster way to do her own review pass | No reviewer mode, no dismissal/override, no annotation export, no session persistence beyond 24h, no batch processing, no stable NJIT-branded hostname | Medium | See §8 prioritized list — these are the concrete features that would move this from "helps students avoid errors" to "helps Ester review faster" |
| 13 | PDF-only web UI, privacy/local-first | **Implemented** | `web_app.py:1307` (`if ext != ".pdf": return _index_error(...)`) — single-extension gate on the only public upload route; no `.zip`/`.tex` route exists anywhere in `web_app.py` (grepped); `pyproject.toml` dependencies are 100% local-execution libraries (pymupdf, pdfplumber, pypdf, fastapi, uvicorn, jinja2, python-docx) — no cloud/LLM SDK, no outbound-HTTP dependency in the runtime path | `tests/test_mobile_desktop_consistency.py` (asserts no "TeX"/".zip" string anywhere in rendered pages), `tests/test_upload_handling.py` | `help.html:147`: "The tool does not communicate with NJIT systems and cannot submit or approve your dissertation." | Upload page only accepts a single PDF; no source/TeX/ZIP option visible or reachable publicly | None found | Low | None |
| 14 | Accuracy before official/demo-level use | **Unknown — needs human confirmation** | 1580 synthetic tests pass, plus extensive `docs/evaluation/*.md` comparisons against real EF-annotated dissertations | Synthetic tests by design (`[[feedback_code_style]]` constraint: synthetic tests only, no cloud APIs) — they prove internal logical correctness, not real-world recall/precision against novel documents | `docs/evaluation/expanded_ester_dataset_evaluation.md`, `docs/evaluation/ef_overlap_after_p071_evaluation.md`, etc. document partial overlap with real EF annotations, with several explicit known false-negative classes (e.g. body-start detection failing on 2 of 5 evaluation PDFs due to collapsed text-layer spacing) | The tool states "Results are advisory" and frames itself as a self-check aid, not a certification | This audit cannot certify real-world accuracy — that requires Ester (or another reviewer) running the live tool against a fresh, not-previously-seen dissertation and comparing | Medium-High | Run the live tool against at least one fresh, unseen dissertation in front of Ester before any "official"/demo framing; do not claim production-readiness based on synthetic test counts alone |

---

## 4. Implemented Requirements (6 + 1 UI-layer item)

\#1 NJIT-specificity, \#2 visual/layout detection, \#6 "what it checks" de-emphasis,
\#8 location-specific feedback, \#10 exact warning wording, \#11 NJIT-scoped
title-case logic, \#13 PDF-only/privacy-first behavior.

## 5. Partially Implemented Requirements (6)

\#3 YES/NO matrix approach (real but paraphrased/consolidated), \#4 one-check/
one-remediation (done for the named high-volume rules, long tail remains generic),
\#5 matrix question text as names (question-style yes, verbatim no), \#7 matrix
remediation as "how to fix" (per-finding text is close, catalog-page text is a
paraphrase), \#9 imitate human PDF comments (text-based location/problem/fix yes,
no PDF-annotation export), \#12 reduce Graduate Studies workload (helps students,
not yet Ester's own review pass).

## 6. Not Implemented Requirements

None of the 14 top-level requirements are flatly "not implemented." The closest
sub-items to a hard "not implemented" are specific matrix questions, not
requirements as a whole:

### 6.1 Visual/layout property checklist (Phase 5 detail)

| Property | Status | Detector | Rule ID | Data basis | Highlight available |
|---|---|---|---|---|---|
| Indentation | Implemented | `pdf_indentation.py` | P015 | bbox.x0 | No (bbox not stored) |
| Boldness | Implemented | `pdf_headings.py`, `pdf_title_capitalization.py` | P014, P020 | font bold flag | No |
| Italics | Implemented | `pdf_dedication_centering_italic.py` | P065 | font italic flag | No |
| Page-number position | Implemented | `pdf_page_numbers.py` | P013, P019 | x/y vs page dims | No |
| Margin sizes | Implemented | `pdf_margins.py` | P011 | bbox vs allowed box | No |
| Title centering | Implemented | `pdf_headings.py`, `pdf_dedication_centering_italic.py` | P014, P065 | bbox center vs page center | No |
| Heading position/format | Implemented | `pdf_heading_levels.py` | P027 | font + text pattern | No |
| Figure/table layout | Implemented | `pdf_figure_table_layout.py` (wired in `audit_runner.py:266`) | P035 | block clustering/centering | No |
| Caption placement | Implemented | `pdf_captions.py`, `pdf_figure_table_layout.py` | P017, P035 | text pattern + position | No |
| Front-matter layout/order | Implemented | `pdf_frontmatter_structure.py` | P025 | structural/text order | No |
| Body text spacing | Implemented | `pdf_body_spacing.py` | P023 | line bbox y-deltas | No |
| Line spacing | Implemented | `pdf_body_spacing.py` | P023 | y-delta / font-size ratio | No |
| PDF annotations/comments (detect) | Implemented | `pdf_annotations.py` | P012 | direct PyMuPDF rect/info | **Yes — only this rule** |
| Highlighted PDF visual evidence | **Partial** | `pdf_highlight.py` | n/a (infra) | infrastructure ready, used by 1 rule | Infra-only |

Net: detection logic is genuinely visual/geometric for every property Ester named.
The gap is entirely at the "draw it on the PDF" layer, deliberately scoped to one
rule (P012) so far, by conservative engineering choice (avoid storing/validating
more bbox shapes than necessary), not because the underlying signal is unavailable.

### 6.2 Front-matter matrix coverage by section (Phase 6 detail)

The matrix (`260330_YESNO_audit_logic_matrix.xlsx`, transcribed into
`njit_rule_inventory.json`) covers **front-matter only** — 79 questions across
Abstract, Title Page, Copyright Page, Approval Page, Dedication Page,
Acknowledgements, Biographical Sketch, Table of Contents, List of Tables, List of
Figures. It has **no body-chapter rows** — body rules (margins, fonts, heading
levels, spacing) are P0xx-only, with no matrix counterpart, by the matrix's own
original scope.

Re-deriving coverage from the **current** rule catalog (not the stale tracking
JSON):

| Section | Matrix Qs | Current coverage (qualitative) | Confirmed real gaps |
|---|---|---|---|
| Abstract | 5 | Strong (page-number suppression, body-presence, length, forbidden terms, first-person) | None significant |
| Title Page | 3 | Strong (no-page-number, graduation month, title consistency) | Q007 institutional-identity-block exact match — not found |
| Copyright Page | 4 | Strong (no-page-number, year/author format, no header text, title-consistency cross-check) | None significant |
| Approval Page | 8 | Partial (presence/structure of committee block, advisor-role label) | Q015–Q020: honorific prefixes, advisor-before-non-advisor ordering, rank ordering, alphabetical-within-rank, NJIT-vs-external ordering — **none implemented**, by deliberate design (`pdf_approval_page_committee_blocks.py:12`: "Does not read or quote committee-member names, honorifics, affiliations") |
| Dedication Page | 4 | Strong (no header text, centering+italics, Roman-numeral sequencing) | None significant |
| Acknowledgements | 11 | Partial (Roman-numeral sequencing, paragraph indentation) | Q037–Q043: paragraph-content semantics (thanks-advisor-in-para-1, thanks-committee-in-para-2, grant agency/number, full-name usage) — **none implemented**, requires semantic content reading |
| Biographical Sketch | 10 | Partial (bullet/publication single-spacing, hanging indent) | Q023/Q024 (content exclusions: no birthplace/birthdate, no work history) and Q027–Q029 (publication ordering/format details beyond what P066/P067 cover) — largely not implemented, content-semantic |
| Table of Contents | 14 | Strong (Roman-numeral continuation, "(Continued)" heading, level indentation, inter/intra-entry spacing, appendix entry format, non-decreasing page/section numbers) | Q047 first-page exact heading text — uncertain, not independently confirmed |
| List of Tables | 10 | Strong (column headers + bold/alignment, terminal-period, title-case, spacing, number alignment) | None significant found |
| List of Figures | 10 | Strong (mirrors List of Tables) | Q074 sentence-case for figure descriptions — **explicitly excluded by design** (`pdf_title_capitalization.py:13`: "Figure descriptions: Sentence case — NOT checked by P020") |

**Pattern in the real remaining gaps:** every confirmed gap requires reading and
semantically interpreting actual document content (who is thanked, in what order,
committee honorifics/rank) rather than checking layout/geometry/exact-phrase
matching. This is consistent with the project's existing constraint of
conservative heuristics only, no cloud APIs/LLMs (`[[feedback_code_style]]`) — closing
these gaps would either require new heuristics of uncertain reliability or a
policy change on tooling.

### 6.3 Workflow features with no trace in the codebase (Phase 13 detail)

Confirmed **absent, no partial/experimental trace found**, after a full-codebase
search:

- Reviewer-mode UI distinct from student self-check
- Mark-as-false-positive / dismiss a finding
- Export findings as real PDF annotations (P012 only **detects** existing
  annotations; no add-annotation code path exists)
- Compare multiple review passes/versions over time
- Persist audit sessions beyond the 24h `JOB_TTL_SECONDS`
- Batch processing (multi-PDF submission)
- Stable NJIT-branded hostname (only local/dev `tmux`+`localhost:8000` setup
  documented)

---

## 7. Unknown / Needs-Human-Confirmation Items

1. **Requirement #14 (real-world accuracy)** — cannot be settled by code/test
   inspection; needs Ester (or another reviewer) to run the live tool against a
   fresh dissertation and judge precision/recall directly.
2. **Q047 (TOC first-page exact heading text)** and a handful of other individual
   matrix sub-questions where this audit found plausible but not 100%-confirmed
   coverage — would need a dedicated line-by-line re-pass of all 79 questions
   against detector source, which was judged disproportionate for this report
   (see §3 row #3/#5 methodology note).
3. **Whether PR #311 should simply be closed** — functionally yes (superseded by
   #326), but closing PRs was explicitly out of scope for this task.

---

## 8. Top 10 Gaps (relative to Ester's comments)

1. Only P012 (annotation detection) produces a real drawn PDF highlight; every
   other visual/layout rule computes real geometry internally but doesn't store
   it for highlighting (Req #2, #9).
2. No feature writes findings back into the PDF as actual reviewer-style
   annotations — the tool's output lives in the web UI/JSON/Markdown, not inside
   the PDF the way Ester's own PDF-comment workflow does (Req #9).
3. Matrix question text and column-D remediation are used as *paraphrases*, not
   verbatim, at the `/rules`-catalog level (though the live per-finding text is
   closer) (Req #5, #7).
4. ~70 long-tail `(rule_id, issue_type)` pairs (mostly List of Tables/Figures
   numbering-format family) still rely on a generic-but-safe fallback rather than
   bespoke per-issue wording (Req #4).
5. No reviewer-mode UI, false-positive dismissal, or session persistence — the
   tool reduces student errors, not yet Ester's own review-pass time (Req #12).
6. Approval-page committee ordering/honorifics and Acknowledgements
   paragraph-content checks (matrix Q015–Q020, Q037–Q043) are unimplemented by
   deliberate privacy-driven design, leaving a real, named-by-Ester category of
   front-matter checks uncovered (Req #3).
7. `docs/planning/finding_actionability_matrix.md` (pre-#321) is stale and still
   describes a "page-only" action pattern that no longer exists — risk of a future
   reader (human or agent) trusting it (Req #10, general hygiene).
8. The matrix-tracking snapshot `njit_rule_inventory.json`
   (`implementation_status`/`implementation_module` fields) is stale
   (2026-06-08) and significantly undercounts real coverage — risk of future
   planning decisions being made on bad data.
9. No batch-processing or multi-document comparison — relevant if Ester ever wants
   to audit a whole cohort of theses at once (Req #12).
10. Real-world accuracy against fresh, unseen dissertations has not been
    demonstrated in this audit — only synthetic tests and prior evaluation-dataset
    overlap analysis exist (Req #14).

---

## 9. Risks

1. **Stale planning docs being trusted as current** — both
   `finding_actionability_matrix.md` and `njit_rule_inventory.json` describe
   states that have since changed substantially; either should be re-labeled
   "historical" or refreshed to avoid misleading a future contributor.
2. **PR #311 remaining open** creates a risk that someone (human or agent) tries
   to merge/rebase it later, reintroducing the literal-text-extraction /
   page-only-link design that was deliberately rejected for privacy and
   highlight-policy reasons.
3. **Stash reuse risk** — popping the existing stash without diffing first would
   silently reintroduce superseded P023/P026/P028 wording and a detector-level
   edit that conflicts with the established sanitize-at-presentation-layer
   convention.
4. **Demo/accuracy risk** — presenting the tool as "done" based on the 1580-test
   green suite would overstate readiness; the tests are synthetic by design and
   do not substitute for a fresh real-document accuracy check with Ester.
5. **Long-tail generic remediation** — while no longer using a banned vague
   phrase, ~70 issue-type pairs still give less specific guidance than the
   bespoke rules; if those happen to be high-volume on a given real dissertation,
   the experience will be visibly less polished than the showcase rules.

---

## 10. Recommended Next Actions (priority order)

### Must fix before next Ester review
1. None of Ester's 14 requirements are broken or regressed — no "must fix"
   blocking item was found. The closest candidate is **re-confirming real-world
   accuracy on a fresh dissertation with Ester present** (Req #14), since this
   audit cannot substitute for that.

### Should fix soon
2. Plumb `bbox` into `details` for at least the highest-volume rules with
   internally-known geometry (P011 margins, P026 fonts) so highlighting extends
   beyond P012 — directly addresses Ester's "show me exactly where" ask (Req #2,
   #9).
3. Extend bespoke `_ISSUE_TEMPLATES` coverage to the highest-volume long-tail
   rules (prioritize by frequency in `docs/evaluation/*.md` overlap data), not
   all ~70 at once (Req #4).
4. Re-label or refresh `docs/planning/finding_actionability_matrix.md` and
   `data/processed/rules/njit_rule_inventory.json` as historical/stale, or
   regenerate the latter's `implementation_status` against current code, so
   future planning isn't based on outdated tracking data.
5. Close PR #311 (superseded, do not merge) and rebase the low-risk PR #305 —
   both already triaged in `docs/status/pr_and_stash_triage_20260619.md`; this
   report does not perform either action per its own scope constraints.

### Future enhancement
6. Design and build a PDF-annotation export (write findings into the PDF as real
   comment/sticky-note annotations via PyMuPDF) — the single feature that would
   most directly mirror Ester's current review workflow (Req #9).
7. Design a Graduate-Studies "reviewer mode": false-positive dismissal, session
   persistence beyond 24h, and eventually batch processing — these are the
   concrete features separating "helps students avoid errors" from "helps Ester
   review faster" (Req #12).
8. Consider whether to implement any of the semantic/content-level matrix
   questions (Approval Page committee ordering, Acknowledgements paragraph
   content, Biographical Sketch content exclusions) — and if so, decide the
   heuristic approach explicitly, since the current "no cloud APIs" constraint
   makes these meaningfully harder than the layout-based rules already shipped.

### Do not do now
9. Do not start P084 (confirmed absent from `src/`, correctly deferred).
10. Do not pop or apply the existing stash without a dedicated diff-review task.
11. Do not present the tool as "official"/demo-ready until action #1 (fresh
    accuracy check with Ester) has happened.

---

*Generated by a read-only audit pass on 2026-06-19. No files modified other than
this report itself; no commits created; no deployment, PR, or stash actions
taken.*
