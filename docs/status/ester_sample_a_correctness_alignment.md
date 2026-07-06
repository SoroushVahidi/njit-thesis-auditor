# Sample A Correctness Alignment Audit

**Recorded:** 2026-07-06  
**Baseline `main`:** `f323b57380865a94cb0e59de514335aa8a25eb5b` (live at audit start)  
**Branch:** `fix/ester-sample-a-correctness-alignment`  
**Ester claim:** only **1 of 39** tool comments on Sample A (Cibaku first review) was correct.

## Source document access

| Document | URL | Accessible? | Notes |
|---|---|---|---|
| NJIT Thesis Auditor Formatting Rules (Google Sheet) | [Sheet](https://docs.google.com/spreadsheets/d/1IohAmbslfX1orMDr7gx6oJyGGTqAV_AAtF31GP-57Gc/edit) | **No** (Google sign-in) | Column C/E per-item judgments **not** available for this pass |
| Sample A feedback (Google Doc) | [Doc](https://docs.google.com/document/d/1h-Jq_tAN4I3q-97qv5MKk9L1tff9Mmgq/edit) | **No** (sign-in / timeout) | Cannot map Ester's per-comment correct/incorrect flags |

**Repo mirrors used (dated, not live):** `data/specs/ester_warning_wording_map.json` (2026-07-06), `data/specs/ester_p_rule_feedback.json` (2026), `docs/status/warning_clarity_location_actionability_audit.md` (2026-07-06, 39-finding snapshot), `docs/status/warning_actionability_audit_20260622.md`.

Do **not** treat repo mirrors as live Ester judgments. Per-item "Ester correct?" cells below are **`unknown (doc inaccessible)`** unless backed by reproduced false-positive evidence in this pass.

## Sample A reproduction (`ester_sample_a`)

Built-in PDF: `data/raw/ester/250218 Cibaku Elson First Review.pdf` (EF-annotated).  
Auditor: `run_pdf_audit_full` + `build_report_view` @ `f323b57` detectors/presentation.

### Warning-count baseline

| Metric | Before this PR (`f323b57`) | After this PR |
|---|---:|---:|
| Raw detector findings | 211 | 211 |
| **Student problem findings** | **39** | **35** |
| Inventory-only candidates | 92 | 92 |
| P038 problem cards | 4 | **0** |
| P011 problem cards | 19 | 19 |

### Confidence distribution (problem findings)

| Tier | Before | After |
|---|---:|---:|
| high | 14 | 14 |
| medium | 18 | 14 |
| low | 3 | 3 |
| missing | 4 | 0 |

(P038 removals were all `medium` confidence document-level cards.)

### Rule counts (problem findings)

| Rule | Before | After | Notes |
|---|---:|---:|---|
| P011 | 19 | 19 | Largest share; margin strictness deferred |
| P038 | 4 | **0** | **Fixed** — concatenated heading false positives |
| P015 | 5 | 5 | Indentation |
| P013 | 2 | 2 | Page-number duplicates on TOC pages |
| P028 | 2 | 2 | Page-number style |
| P019 | 1 | 1 | Document-level numbering style |
| P051 | 1 | 1 | Copyright year advisory |
| P044 | 1 | 1 | Abstract indent |
| P016 | 1 | 1 | Spacing gap |
| P027 | 1 | 1 | Heading case |
| P020 | 1 | 1 | Title capitalization |
| P012 | 1 | 1 | Annotation rollup (78 annotations → 1 card) |

## Root cause: P038 false positives (fixed this PR)

`find_named_frontmatter_headings()` requires spaced canonical phrases. On Sample A, `pdf_layout` text lines are concatenated (`APPROVALPAGE`, `BIOGRAPHICALSKETCH`, `TABLEOFCONTENTS`, `ACKNOWLEDGMENT`) while raw `fitz` text shows correct spacing. P038 emitted `required_heading_missing` for four present sections.

**Fix:** P038-local `_P038_CONCATENATED_HEADING_VARIANTS` map for presence detection only. **Not** added to `FRONTMATTER_HEADING_VARIANTS` (shared gate/TOC map) — a global gate change was tested and **increased** problem findings to 101 by unlocking P036 TOC rules.

## Alignment matrix (39 prior tool comments)

Columns: **Ester judgment** = inaccessible unless noted. **Classification** from reproduced evidence + prior audits.

| # | Page | Rule | Issue type | Ester judgment | Classification | Fix this PR? |
|---:|---:|---|---|---|---|---|
| 1 | 10 | P013 | duplicate_or_ambiguous_page_number | unknown | needs Ester clarification / possible FP on TOC pages | deferred |
| 2 | 11 | P013 | duplicate_or_ambiguous_page_number | unknown | needs Ester clarification / possible FP on TOC pages | deferred |
| 3 | doc | P019 | wrong_page_numbering_style | unknown | detector false positive / policy borderline | deferred |
| 4 | 10 | P028 | wrong_page_numbering_style | unknown | detector false positive / policy borderline | deferred |
| 5 | 11 | P028 | wrong_page_numbering_style | unknown | detector false positive / policy borderline | deferred |
| 6–24 | various | P011 | margin_boundary_violation | unknown | over-strict/borderline (many 3–12pt bottom overflows) or true positive | deferred |
| 25 | doc | P038 | required_heading_missing (APPROVAL PAGE) | **incorrect (tool)** | **false positive** — heading present as `APPROVALPAGE` | **yes** |
| 26 | doc | P038 | required_heading_missing (BIOGRAPHICAL SKETCH) | **incorrect (tool)** | **false positive** — `BIOGRAPHICALSKETCH` | **yes** |
| 27 | doc | P038 | required_heading_missing (ACKNOWLEDGEMENTS) | **incorrect (tool)** | **false positive** — `ACKNOWLEDGMENT` | **yes** |
| 28 | doc | P038 | required_heading_missing (TABLE OF CONTENTS) | **incorrect (tool)** | **false positive** — `TABLEOFCONTENTS` | **yes** |
| 29 | 4 | P051 | copyright_year_not_found | unknown | detector false positive / advisory | deferred |
| 30–34 | various | P015 | missing_later_indent | unknown | detector false positive / geometry | deferred |
| 35 | 1 | P044 | abstract_first_paragraph_indented | unknown | policy mismatch / needs atomic split | deferred |
| 36 | 1 | P016 | excessive_paragraph_gap | unknown | detector false positive / geometry | deferred |
| 37 | 21 | P027 | level1_not_all_caps | unknown | detector false positive vs EF manual review | deferred |
| 38 | 61 | P020 | possible_title_capitalization_issue | unknown | detector false positive vs EF manual review | deferred |
| 39 | doc | P012 | pdf_annotation_detected | unknown | UI volume / student noise (78 EF annotations in PDF) | deferred |

After this PR the student-facing list has **35** numbered problems (P038 rows removed; downstream problem numbers shift in the UI).

## Deferred (not fixed this PR)

| Area | Why deferred |
|---|---|
| Per-item Ester correct/incorrect mapping | Live Google Doc inaccessible |
| P011 borderline margin strictness (19 cards) | Policy/threshold; not unambiguous from repo sources |
| P011 same-page grouped-card overlap (pages 92–98) | Partially improved; one card per page in individual list |
| P013/P019/P028 page-number FPs on TOC pages | Broad page-number detector change |
| P015/P016 geometry | Highlight/location project |
| P020/P027 heading case vs EF annotations | Needs EF comment ingestion |
| P044 atomic abstract questions | Atomic split project |
| P012 annotation volume | Detector correct; presentation rollup exists |
| P021/P026 policy | Out of scope |
| P084 | Out of scope |
| Global concatenated variants in gate/TOC map | Tested — caused +62 spurious TOC findings on Sample A |

## Tests

- `tests/test_ester_sample_a_correctness.py` — synthetic concatenated-heading P038 tests + Sample A 35-finding / zero-P038 regression + JSON schema guard

## Closer to Ester's benchmark?

- **Yes, narrowly:** removed 4 clear false-positive "missing section" warnings that contradicted visible PDF structure.
- **Still unknown:** which 1 of the original 39 Ester considered correct (requires Google Doc).
- **Still far from 1/39 accuracy** if most remaining 35 comments are also wrong per Ester — that requires her per-item feedback, not guessing.
