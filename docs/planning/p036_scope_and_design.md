# P036 Scope and Design

- **Date:** 2026-06-01
- **Status:** Implemented
- **Baseline main:** `48b1e963` (P001–P036 implemented; status refresh PR #88; P036 implementation PR #87 `e4840aa`)
- **Author:** Design/scoping only; no detector code in this document

## Current state

| Area | State |
|------|--------|
| P-rules | **36/36** implemented (`P001`–`P036`) |
| Q-rules (raw inventory) | **79** total — **2** implemented, **11** partially_implemented, **66** not_implemented |
| TOC/List cluster | **P018**, **P024**, **P030**, **P031**, **P032** — alignment, capitalization, continued headings, column headers, **wrapped internal** spacing |
| TOC/List inter-entry spacing | **P036** — Q057, Q067, Q077 (distinct entry gaps; complements P032) |
| Front-matter named headings | **P014** — layout/style when heading text is found (7 headings); does not flag missing sections |
| Dedication / bio-sketch | Q033–Q034, Q023–Q030 — optional or semantic; high manual/FP risk |
| Figure/table body layout | **P035** — text-layer bodies (v1); image floats skipped |
| Reusable helpers | `detect_toc_like_pages()`, `extract_toc_entry_lines()`, entry line collection from `pdf_toc_list_wrapped_spacing.py` / `pdf_toc_alignment.py` |

Remaining high-value automatable clusters after P035 (from status/coverage docs): TOC/List **inter-entry** double spacing (Q057, Q067, Q077), front-matter exact heading/missing-section refinement (Q013, Q021, Q036, Q047, Q061, Q070 — largely overlaps P014/P030/P031), Roman numeral **value** sequence beyond P028/P029, dedication layout (Q033–Q034), P035 image-block refinement.

---

## Candidate comparison

### Candidate A — TOC/List inter-entry double spacing (recommended)

| Field | Detail |
|-------|--------|
| **Source basis** | Q057 (TOC), Q067 (LoT), Q077 (LoF); Self-Assessment Sheet / guideline matrix inter-entry spacing |
| **Proposed rule** | **P036** — PDF TOC/List inter-entry spacing |
| **Module** | `src/njit_auditor/rules/pdf_toc_list_entry_spacing.py` |
| **Issue types** | `toc_inter_entry_spacing_too_tight`, `lot_inter_entry_spacing_too_tight`, `lof_inter_entry_spacing_too_tight` |
| **Risk / noise** | **Medium–high** — entry boundary detection is ambiguous when entries wrap; must skip wrap pairs handled by P032 and conservative gap thresholds |
| **Privacy** | **Low** — geometry metadata only (`section_type`, `issue_type`, gap ratios, page numbers); no entry title text in findings |
| **Tests** | Synthetic `PdfDocument` fixtures in `tests/test_pdf_rules.py`: compliant double-spaced entries; single-spaced consecutive entries; wrapped continuation must not flag |
| **Five-PDF impact** | **Low–moderate** — may surface real spacing issues on dense LoT/LoF pages; 0 findings acceptable if evaluation PDFs are compliant |
| **Why P036?** | Clear **new** Q-rule cluster; complements P032 (intra-entry) without overlapping; reuses mature TOC/List detection stack; explicitly deferred from P035 planning |

### Candidate B — Front-matter exact heading phrase / missing-section detection

| Field | Detail |
|-------|--------|
| **Source basis** | Q013, Q021, Q036, Q047, Q061, Q070 exact heading requirements |
| **Proposed rule** | P036 or P014 refinement |
| **Module** | Extend `pdf_headings.py` or new `pdf_frontmatter_heading_phrases.py` |
| **Issue types** | `required_heading_missing`, `heading_phrase_not_exact` |
| **Risk / noise** | **Medium** — **P014** already checks layout when heading text matches; **P030**/**P031** cover continued/column headers; incremental value is missing-heading detection and spelling variants (`ACKNOWLEDGEMENTS` vs `ACKNOWLEDGMENTS`) |
| **Privacy** | **Low** |
| **Tests** | Extend P014 fixtures; missing APPROVAL PAGE on detected approval page |
| **Five-PDF impact** | **Low** — P014 already at 0 on current five-PDF snapshot after centering fix |
| **Why not P036?** | Mostly refinement of existing front-matter rules; better as targeted P014/P025 hardening unless bundled as missing-section rule |

### Candidate C — Dedication page centering and italic (Q033–Q034)

| Field | Detail |
|-------|--------|
| **Source basis** | Q033, Q034 |
| **Proposed rule** | P036 — PDF dedication page layout |
| **Module** | `src/njit_auditor/rules/pdf_dedication_page.py` |
| **Issue types** | `dedication_text_not_centered`, `dedication_text_not_italic` |
| **Risk / noise** | **High** — dedication is optional; page detection fragile; italic metadata often absent in PDF text layer |
| **Privacy** | **Medium** — dedication prose must not appear in findings |
| **Tests** | Synthetic dedication page with centered/offset blocks |
| **Five-PDF impact** | **Unknown/low** — section often absent on evaluation PDFs |
| **Why not P036?** | Narrow optional section; weak font-style signal; status doc marks as partial/manual |

### Candidate D — Biographical Sketch content/layout subset (Q023–Q030)

| Field | Detail |
|-------|--------|
| **Source basis** | Q023–Q030 bio-sketch ordering, spacing, citation style |
| **Proposed rule** | P036 — PDF biographical sketch layout |
| **Module** | `src/njit_auditor/rules/pdf_biographical_sketch.py` |
| **Issue types** | Multiple semantic content checks |
| **Risk / noise** | **Very high** — semantic NLP; degree ordering; publication parsing |
| **Privacy** | **High** — must not quote bio prose or names |
| **Tests** | Difficult without quoting private content in fixtures |
| **Five-PDF impact** | **Unknown** |
| **Why not P036?** | Unsuitable for heuristic v1; remains manual-only per coverage audit |

### Candidate E — Roman numeral value sequence (beyond P028/P029)

| Field | Detail |
|-------|--------|
| **Source basis** | Q022, Q031, Q035, Q046, Q060; status doc §4A Roman numeral **value** sequence gap |
| **Proposed rule** | P036 — PDF front-matter Roman numeral ordering |
| **Module** | `src/njit_auditor/rules/pdf_roman_value_sequence.py` |
| **Issue types** | `roman_sequence_gap`, `roman_sequence_out_of_order`, `roman_style_mismatch` |
| **Risk / noise** | **Medium** — overlaps P028/P029 regime/style checks; candidate extraction noise on compressed PDFs |
| **Privacy** | **Low** |
| **Tests** | Synthetic front-matter pages with i/ii/iii sequences |
| **Five-PDF impact** | **Low–moderate** — may add findings on mixed-regime PDFs already flagged by P028 |
| **Why not P036?** | Valid follow-on but less aligned with EF `list_of_tables_figures_toc` gap cluster; defer until TOC/List spacing closed |

### Ranking

1. **A — TOC/List inter-entry spacing** (recommended P036)
2. **E — Roman numeral value sequence** (page-numbering follow-on)
3. **B — Front-matter exact heading / missing section** (P014/P025 refinement)
4. **C — Dedication layout** (optional section, high skip rate)
5. **D — Bio-sketch content** (unsuitable for automation v1)

---

## Selected P036 scope

### Rule title

**P036 — PDF TOC/List inter-entry spacing**

### Source basis

- Q057 — visible double spacing between consecutive TOC section-title entries
- Q067 — visible double spacing between consecutive LoT table entries
- Q077 — visible double spacing between consecutive LoF figure entries
- Self-Assessment Sheet / guideline matrix inter-entry spacing expectations
- Status gap: `docs/status/current_project_state_and_next_steps.md` §2 (TOC/list internal formatting), §7 next steps (TOC/List robustness)
- Complements **P032** (wrapped **internal** spacing within one entry); does **not** duplicate P018/P024/P030/P031

### Scope included

1. Run on pages classified by `detect_toc_like_pages()` as `table_of_contents`, `list_of_tables`, or `list_of_figures`.
2. Collect entry-region lines (reuse/adapt `_collect_entry_region_lines` pattern from P032).
3. Identify **consecutive distinct entry boundaries** — pairs where the second line is a **new entry start** (has page-number column token, matches `Table N` / `Figure N` / chapter-section pattern, or indent cluster change), **not** a wrap continuation (inverse of P032 `_is_wrap_continuation_pair`).
4. Measure vertical gap between the **last line of entry N** and **first line of entry N+1**.
5. Flag when gap is **below** a conservative double-spacing threshold (e.g. gap ratio `< 1.4×` estimated line height, aligned with P023/P032 ratio conventions).
6. Skip ambiguous pairs: intervening page-number-only lines (reuse P032 guard), column-header rows, continued-heading rows, single-line pages, fewer than 2 entries.
7. Emit privacy-safe findings: `issue_type`, `section_type`, page number, gap metadata — **no entry title text**.

### Scope excluded

- Wrapped **internal** line spacing within one entry (**P032**).
- Entry alignment, leaders, capitalization (**P018**, **P024**).
- Continued headings (**P030**), column headers (**P031**).
- Inter-entry spacing on body chapters, references, or non-list pages.
- Full visual double-space proof on image-only or scanned lists.
- Appendix labeling rules (**Q058**, **Q059**).

### Expected module path

`src/njit_auditor/rules/pdf_toc_list_entry_spacing.py`

Shared imports from:

- `pdf_toc_alignment.py` — `detect_toc_like_pages`, `TocPageContext`, `_likely_entry_line`, `_extract_page_number_token`
- `pdf_toc_list_wrapped_spacing.py` — line collection helpers, wrap-pair exclusion logic (import private helpers or duplicate minimal inverse logic in-module to avoid circular imports)

### Expected CLI / report / evaluation wiring

| Surface | Change |
|---------|--------|
| `src/njit_auditor/cli.py` | Call `check_pdf_toc_list_entry_spacing()` after P032 (or adjacent TOC/List block) |
| `data/processed/rules/project_added_rules.json` | Add **P036** entry (`implementation_status: implemented` only after code lands) |
| `src/njit_auditor/evaluation.py` | Map P036 → `table_format` / `list_format` category (match P032) |
| Reports | Standard `AuditFinding` details; no new triage rollup in v1 |

### Expected tests

| Test | Expectation |
|------|-------------|
| TOC two entries with double spacing | No P036 finding |
| TOC two entries single-spaced | `toc_inter_entry_spacing_too_tight` |
| LoT / LoF compliant spacing | No finding |
| LoT / LoF tight spacing | `lot_*` / `lof_*` issue types |
| Wrapped entry (two lines, same entry) | No finding (P032 domain; P036 must skip) |
| Column header / continued heading page | No finding |
| Finding details | No entry title text; geometry metadata only |

Add `tests/test_rule_inventory.py` count bump to **36** when implemented.

### Privacy constraints

- Do not quote TOC/LoT/LoF entry titles, figure descriptions, or table captions in findings.
- Report only: page number, `section_type`, `issue_type`, gap points/ratios, confidence.
- Local evaluation docs: aggregate counts only; no dissertation body text.

### Acceptance criteria

1. P036 detects clearly single-spaced consecutive entries on synthetic TOC/LoT/LoF fixtures.
2. P036 does **not** flag wrapped continuations that P032 already covers.
3. P036 skips pages with fewer than two confident entry boundaries.
4. CLI runs P036 on `njit-audit pdf` without changing P001–P035 behavior.
5. All existing tests pass; new P036 tests added.
6. `project_added_rules.json` lists P036 with correct module path (implementation PR).

### Known false-positive risks

- Mis-segmented entries when page numbers are on separate lines from titles.
- Dense LoF pages where short descriptions look like new entries.
- PDFs with intentionally compact list formatting that still meet visual guidelines.
- Compression artifacts altering line bbox gaps on flattened PDFs.

Mitigation: conservative thresholds, high-confidence gate, skip when entry boundary confidence is low (same philosophy as P032 PR #59 split-page-number guard).

### Local evaluation rerun (not committed)

After implementation, rerun five-PDF audit locally into gitignored
`data/evaluation/generated/current_auditor_after_p036/` and add
`docs/evaluation/p036_current_dataset_evaluation.md` with aggregate P036 counts only.

Do **not** commit generated JSON/MD. Do **not** update `generated_for_commit` or the pre-P035 canonical **1,446** aggregate until a documented full P001–P036 rerun.

---

## Implementation plan (next task)

1. Add `pdf_toc_list_entry_spacing.py` with entry-boundary detection and inter-entry gap measurement.
2. Wire CLI + `project_added_rules.json` + `evaluation.py` category map.
3. Add synthetic tests in `tests/test_pdf_rules.py`; update `tests/test_rule_inventory.py` to 36 rules.
4. Run full validation (`ruff`, `mypy`, `pytest`).
5. Optional: local four/five-PDF evaluation doc (aggregate only, gitignored outputs).

No changes to P001–P035 detector behavior in the scoping PR.

---

## Validation plan

| Step | Command |
|------|---------|
| Inventory (post-impl) | `python -m pytest tests/test_rule_inventory.py -q` |
| P036 synthetics | `python -m pytest tests/test_pdf_rules.py -k p036 -q` |
| Full suite | `ruff check . && mypy src && python -m pytest` |

---

## Privacy notes

- Findings must remain metadata-only (page, section type, gap geometry).
- Evaluation write-ups: counts and issue-type mix only.
- Do not quote dissertation prose, headings beyond generic rule labels, or author-identifying content.

---

## Generated-output safety

- All audit JSON/MD under `data/evaluation/generated/` stays **gitignored**.
- Scoping and evaluation docs describe local rerun paths only; never commit generated artifacts.
