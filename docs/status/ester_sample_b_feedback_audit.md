# Ester Sample B Feedback Audit

**Recorded:** 2026-07-08  
**Branch:** `audit/ester-sample-b-feedback`  
**Baseline:** `origin/main` @ `32952f2` (PR #481 merged)  
**Worktree:** `/home/soroush/njit-thesis-auditor/njit-thesis-auditor-clean-worktrees/ester-sample-b-feedback`

## Purpose

Reassess Ester’s newest Sample B feedback as product requirements and map:

- what PR **#481** already fixed (presentation / wording),
- what draft PR **#482** is intended to fix (detector / highlight behavior), and
- what still needs a separate implementation pass.

This pass is **audit/planning only**. PR #482 was not modified here.

Ester's own language and files (email-stated concerns, the YESNO audit logic matrix, the wording map) are treated as the **product source of truth** for this audit — detector/report output is judged against what Ester said, not the reverse.

---

## PR status at audit time

| PR | Branch | State | Base | CI after latest work | Action taken in this pass |
|---|---|---|---|---|---|
| **#481** | `fix/ester-email-alignment-audit` | **Merged** into `main` (`32952f2`) | `main` | Green after `d723166` (and follow-up relax commits) | No further work — already merged before this audit |
| **#482** | `fix/ester-sample-a-correctness-pass1` | **Open draft** | `main` | Green (3.10 / 3.11 / 3.12) | **Not modified** — remains draft until reviewed/merged on its own |

PR #482 was originally stacked on #481. With #481 merged, #482 already targets `main` and does not require a rebase/retarget for this audit pass.

---

## Files reviewed

| Source | Path / location | Accessible? | Role in this audit |
|---|---|---|---|
| Sample B Feedback.docx | Not found in repo or local filesystem | **No** | Source doc unavailable in this environment — see note below |
| NJIT Thesis Auditor Formatting Rules | `data/specs/ester_warning_wording_map.json`, `data/processed/rules/project_added_rules.json` | Yes (repo mirror) | Column C/E wording baseline; live Google Sheet requires sign-in |
| 260330 YESNO audit logic matrix | `data/raw/ester/260330_YESNO_audit_logic_matrix.xlsx` | Yes | Atomic questions/remediations (Q036 Acknowledgements, Q065 table titles, body-spacing intent) |
| Sample A feedback.docx | Not in repo (Google Doc mirror only) | **No** | Prior alignment patterns via `docs/status/ester_sample_a_feedback_alignment.md` |
| Ester email alignment audit | `docs/status/ester_email_alignment_audit.md` | Yes | PR #481 scope and satisfied presentation items |
| Sample A correctness pass 1 | `docs/status/ester_sample_a_correctness_pass1.md` | Yes (PR #482 branch copy) | Detector fixes #482 carries for Sample A and overlapping Sample B families |
| Ester wording map | `data/specs/ester_warning_wording_map.json` | Yes | What #481 aligned; gaps for P020/P023/P051 |
| Built-in Sample B PDF | `data/raw/ester/Yin_Haotian_Second_R_with_EF_Feedback.pdf` (`ester_sample_b`) | Yes | Reproducible detector/report snapshot |

**Note:** `Sample B Feedback.docx` and `Sample A feedback.docx` were **not present in this repo or local filesystem** — this audit does not claim to have read the source docx directly. Page-level judgments below are built from three substitute sources instead:

1. **Ester's latest email-provided Sample B concerns** — the explicit per-page/per-rule concern list carried into the alignment task.
2. **Reproduced `ester_sample_b` outputs** — live detector/report runs against the built-in Sample B fixture on `main` (`32952f2`) and on the PR #482 branch.
3. **Available repo mirrors / status docs** — `ester_warning_wording_map.json`, `project_added_rules.json`, the YESNO audit logic matrix, and prior alignment docs (`ester_email_alignment_audit.md`, `ester_sample_a_feedback_alignment.md`, `ester_sample_a_correctness_pass1.md`).

Item numbers (`SB-01` …) are audit IDs assigned in this pass, not verbatim problem numbers from the missing docx.

---

## Reproduced Sample B snapshots

### `main` after PR #481 (`32952f2`)

Built-in `ester_sample_b` → **63** student-facing problems:

| Rule | Count | Sample B pages called out by Ester |
|---|---:|---|
| P011 | 33 | 1, 24, 39 (Ester: false positives); others may be correct |
| P015 | 13 | 23, 24, 26, 27, 38 (Ester: false positives) |
| P013 | 2 | 10, 11 |
| P028 | 2 | 10, 11 |
| P019 | 3 | document-wide + 57, 58 |
| P038 | 1 | 9 (`ACKNOWLEDGEMENTS`) |
| P020 | 2 | 71, 80 |
| P023 | 1 | 82 |
| P051 | 1 | 4 |
| P026 | 1 | 5 (font size; see SB-14) |
| P016 | 2 | 1 (duplicate spacing cards) |
| Other | 4 | P012×1, P017×1 |

**P011 low-overflow pattern (supports Ester’s margin concern):**

| Page | Ester judgment | Reproduced overflow | Notes |
|---|---|---:|---|
| 1 | false positive | ~4.9 pt right | Sub-5 pt — likely artifact / page-number / extraction noise |
| 24 | false positive | ~3.2 pt right | Sub-5 pt |
| 39 | false positive | ~4.7 pt right | Sub-5 pt |
| 78 | (not disputed) | ~34.5 pt right | Large overflow — consistent with a real violation |

Do **not** loosen P011 globally. Next work should distinguish true text/table/figure overflow from crop-box artifacts, page-number glyphs, and tiny extraction noise.

### Draft PR #482 (`fix/ester-sample-a-correctness-pass1`) — read-only comparison

Same fixture → **48** problems (−15). Material deltas:

| Rule | `main` | PR #482 | Ester-relevant change |
|---|---:|---:|---|
| P015 | 13 | 2 | Removes pages **24, 26, 27, 38**; **23** still fires; page **34** remains |
| P013 | 2 | 0 | TOC page-number false positives on 10–11 **resolved** |
| P028 | 2 | 0 | Front-matter Arabic-numeral false positives on 10–11 **resolved** |
| P011 | 33 | 33 | Unchanged |
| P038 / P020 / P023 / P051 / P019 | same family | same family | Unchanged |

---

## Sample B concern matrix

| Item | Rule ID | Page | Ester’s judgment | PR #481 resolves? | PR #482 resolves? | Still needs new work? | Recommended next fix |
|---|---|---:|---|---|---|---|---|
| SB-01 | P011 | 1 | false positive | no | no | **yes** | Filter sub-threshold / non-body margin noise; keep strict policy for real text-table-figure overflow (~5+ pt or content-kind-aware). |
| SB-02 | P011 | 24 | false positive | no | no | **yes** | Same as SB-01 — preserve detector strictness for large overflows. |
| SB-03 | P011 | 39 | false positive | no | no | **yes** | Same as SB-01. |
| SB-04 | P015 | 23 | false positive (mid-paragraph) | no | partial | **yes** | PR #482 still flags page 23 (`missing_later_indent`, body paragraph 6). Add regression for mid-paragraph / continuation-line suppression. **High priority — Ester explicit.** |
| SB-05 | P015 | 24, 26 | false positive (mid-paragraph) | no | **yes** | no | Covered by #482 continuation/split-heading guards; add Sample B regression tests before merge. |
| SB-06 | P015 | 27, 38 | false positive (section-opening sentences) | no | **yes** | no | Covered by #482 section-opening / code-block exclusions; verify highlights no longer target first sentences. |
| SB-07 | P013 | 10, 11 | incorrect highlight / false positive | no | **yes** | no | #482 front-matter page-number candidate selection; add Sample B regression on pages 10–11. |
| SB-08 | P028 | 10, 11 | incorrect highlight / false positive | no | **yes** | no | Same #482 candidate fix; numbering-style check should follow the real bottom-center Roman numeral. |
| SB-09 | P019 | 57, 58 | false positive / wrong element highlighted | no | partial | **yes** | Still fires on `main` and #482 (`duplicate_or_ambiguous_page_number` with top-center vs bottom-center candidates). Highlight must target the actual page-number glyph, not unrelated tokens. |
| SB-10 | P019 | document-wide | incorrect no-highlight / document-level handling | no | no | **yes** | Document-wide mixed-style card has no page anchor. Keep honest document-level wording but add front-matter vs body section breakdown per Ester. |
| SB-11 | P038 | 9 | false positive (`ACKNOWLEDGEMENTS`) | no | no | **yes** | `heading_phrase_not_exact` still fires. Align with Q036 (“Format the heading ACKNOWLEDGEMENTS correctly”) — do not treat present/variant headings as defects; analyze front-matter pages individually with page-specific remediation. |
| SB-12 | P023 | 82 | incorrect finding / exception gap | no | no | **yes** | Page 82 still flagged. Treat **figure descriptions** as allowed single-spaced exceptions. Question must match Ester: *“Is body text double-spaced, except for tables, figure descriptions, bullet points, and multi-line titles?”* (`project_added_rules.json` P023). |
| SB-13 | P020 | 71 | incorrect remediation (heading level) | no | no | **yes** | Heading-level capitalization still uses generic P020 remediation. Pull level-specific question/remediation from the Google Sheet / `Titles Examples Level 1 to 5.docx`; do not suggest capitalizing conjunctions like “and”. |
| SB-14 | P020 | 80 | table title vs figure caption mix-up | no | no | **yes** | Table-title finding on page 80 must use table-title wording (title case, no terminal period — cf. Q065), not figure-caption / sentence-case remediation. |
| SB-15 | UI | n/a | duplicate “Spacing / blank lines” section | no | no | **yes** | Sample B page 1 emits **two** P016 problems (`excessive_paragraph_gap` + `excessive_line_gap`) in the same `spacing_blank_lines` category — likely the duplicate Ester saw. Merge or rollup same-page P016 variants in the report. |
| SB-16 | P026 / font | 5 | incorrect highlight / feedback | no | no | **yes** | Ester feedback references font formatting on page 5. Tool reproduces **P026** `possible_body_font_size_issue` (10.9pt vs 12pt tolerance), category `font_format`. **P063** (appendix heading labels) does not fire on Sample B. Re-check extraction, tolerance, and highlight bbox on page 5 before tuning. |
| SB-17 | P051 | 4 | correct feedback, wrong category | no | no | **yes** | Finding is correct (`copyright_year_not_found`) but category is `title_page_metadata` → UI label **“Title page”**. Rename to **“Copyright page”** (`web_app._CATEGORY_LABELS`) — isolated, low-risk fix. |

---

## Explicit concern evaluation

### P011 margins (SB-01 – SB-03)

- Ester: some Sample B P011 findings are correct, but **pages 1, 24, and 39 are false positives**.
- Reproduction confirms all three are **low single-digit point overflows** (3–5 pt) vs much larger violations elsewhere (e.g. page 78 ~34.5 pt).
- **Do not loosen the margin rule globally.**
- Next branch: content-kind + overflow-magnitude gating, and exclusion of page-number / header-footer / crop-box artifacts before counting margin violations.

### P015 indentation (SB-04 – SB-06) — **high priority**

- Ester: pages **23, 24, 26** highlight middle-of-paragraph text; **27, 38** highlight first sentences of sections that should not be indented.
- PR #482 resolves 24, 26, 27, 38 on Sample B but **page 23 remains**.
- Merge #482 first, then open a focused follow-up for page 23 and any remaining mid-paragraph cases, with Sample B regression tests.

### P013 / P028 / P019 page numbering (SB-07 – SB-10)

- PR #482 clears P013/P028 on TOC pages 10–11 (same family fixed for Sample A).
- P019 pages 57–58 and document-wide mixed-style issues remain.
- Next work: highlight the **exact page-number element**; separate style/regime checks; improve document-level cards with honest no-highlight behavior and section-specific guidance.

### P038 front-matter headings (SB-11)

- `ACKNOWLEDGEMENTS` on page 9 is still flagged `heading_phrase_not_exact`.
- Ester also objects to document-level / no-page handling for front matter — each front-matter page should have specific remediation (Q036, Q044, Q045 in the YESNO matrix).
- Next branch: front-matter page-scoped cards + variant tolerance; avoid document-level rollup where a page anchor exists.

### P023 spacing (SB-12)

- Catalog already has Ester’s exception list in `project_added_rules.json` P023 question/remediation.
- Detector on page 82 does not yet exempt figure-description blocks.
- Next branch: figure-description / caption block detection inside P023 body-spacing measurement.

### P020 capitalization (SB-13 – SB-14)

- Page 71: concatenated heading token `Implementation,Experiments,andResults` — remediation must be heading-**level** specific, not generic title-case advice.
- Page 80: table title — use table-title rules (Q065 / title case, no final period), not figure-caption sentence-case wording.
- Add P020 entries to `ester_warning_wording_map.json` per issue subtype (heading level vs table title vs figure caption).

### Duplicate report sections (SB-15)

- On Sample B page 1, P016 emits two distinct issue types in one category — students may see redundant “Spacing / blank lines” information.
- Investigate rollup in `report_view` / `web_app` category presentation before adding new detectors.

### Font formatting page 5 (SB-16)

- Mapped to reproduced **P026** on page 5, not P063.
- Verify whether 10.9pt is real body text or front-matter / structural text misclassified before changing tolerance.

### P051 category (SB-17)

- Isolated presentation fix: map P051 to a **Copyright page** category label.

---

## Already resolved (by merged #481 or draft #482)

### PR #481 (merged) — presentation / wording

- Ester Column C questions on mapped rules (P011, P012, P013, P019, …).
- Column E fallback remediation via `ester_warning_wording_map.json` / `polished_comments.py`.
- Page-order-first findings layout.
- P011 student-facing question includes tables and figures.

### PR #482 (draft, not merged) — detector / highlight

- P013 / P028 TOC page-number false positives (pages 10–11) — **resolved on Sample B**.
- P015 false positives on pages 24, 26, 27, 38 — **resolved on Sample B**.
- Sample A correctness fixes (P044, P027, etc.) — documented in `ester_sample_a_correctness_pass1.md`.

---

## Still unresolved after #481 + #482

| Priority | Items | Rules |
|---|---|---|
| **P0** | P015 page 23; merge #482 + Sample B regressions | P015 |
| **P1** | P011 low-overflow false positives (pages 1, 24, 39) | P011 |
| **P1** | P019 highlight targeting + document-level numbering presentation | P019, P028 |
| **P1** | P038 Acknowledgements false positive + per-page front-matter handling | P038 |
| **P2** | P023 figure-description exception on page 82 | P023 |
| **P2** | P020 heading-level vs table-title specific wording | P020 |
| **P2** | Duplicate P016 spacing presentation on page 1 | P016 / UI |
| **P2** | P026 page 5 font highlight/feedback accuracy | P026 |
| **P3** | P051 category rename Title page → Copyright page | P051 / UI |

---

## Safest next implementation branch

Recommended sequence:

1. **Merge PR #482** (draft, green, already on `main`) after Sample B regression tests are added for P013/P028/P015 wins.
2. **`fix/ester-sample-b-p015-page23`** — narrow P015 follow-up for remaining page 23 mid-paragraph false positive.
3. **`fix/ester-p051-copyright-category`** — isolated category label (SB-17).
4. **`fix/ester-p016-spacing-rollup`** — duplicate spacing section on same page (SB-15), if reproducible in UI.
5. **`fix/ester-p011-margin-noise`** — artifact/low-overflow filter without global loosening (SB-01–03).
6. **`fix/ester-sample-b-frontmatter`** — P038 + document-level front-matter cards (SB-11).
7. **`fix/ester-p020-wording-split`** + **`fix/ester-p023-figure-description-exception`** — wording/detector slices with sheet-backed tests.

Avoid broad simultaneous rewrites of P011, P015, P019, P023, and P063/P026 in one pass.

---

## Validation run (this audit pass)

From clean worktree @ `32952f2` (docs-only change):

```bash
/home/soroush/njit-thesis-auditor/main/.venv/bin/python -m ruff check .
/home/soroush/njit-thesis-auditor/main/.venv/bin/python -m pytest -q
```

Sample B reproduction scripts (read-only, not committed):

```bash
PYTHONPATH=src python -m pytest tests/test_ester_sample_a_correctness.py -q  # Sample A baseline on main
# Manual Sample B counts via run_pdf_audit_full + build_report_view (see Reproduced snapshots above)
```

---

## Commit hygiene

- This pass adds **only** `docs/status/ester_sample_b_feedback_audit.md`.
- No `data/raw/...` or `tests/fixtures/web_demo/...` files were staged or committed.
- Worktree shows `M` on some LFS-tracked binaries (smudge/pointer mismatch without `git-lfs`) — left untouched and **not** part of this deliverable.
