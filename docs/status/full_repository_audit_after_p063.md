# Full Repository Audit After P063

- **Date:** 2026-06-07
- **Branch:** main
- **Latest commit:** `71b3823` (PR #223 — Implement P063: body-page appendix heading label check)
- **Auditor scope:** P001–P063 implemented; 889 pytest; ruff clean; mypy 81 source files, no issues
- **Update (2026-06-08):** P064–P068 implemented; P068 adds approval page committee/signature-block structural checks (`pdf_approval_page_committee_blocks.py`); P068 current-dataset evaluation complete — **3** findings on 2/5 files; post-P068 full aggregate confirmed at **1,590** findings (+3 vs P067-era); **963+ pytest** after P068 implementation; **P069 scoped** — front-matter heading gate recall refinement (`docs/planning/p069_frontmatter_heading_gate_recall_refinement_scope_and_design.md`)

---

## 3.1 Git / Validation State

| Check | Result |
|---|---|
| Branch | main |
| Latest commit | `71b3823` |
| Working tree | clean (one untracked directory: `tests/fixtures/web_demo/demo_project_extracted/`; runtime artifact, safe to ignore) |
| `ruff check .` | All checks passed |
| `mypy src` | No issues in 81 source files |
| `python -m pytest` | 889 passed |

---

## 3.2 Rule Implementation Inventory

### Highest P-rule and count

- **Highest implemented:** P063
- **Total P-rules in `project_added_rules.json`:** 63 (P001–P063), all marked `"implementation_status": "implemented"`

### All P001–P063 present in project_added_rules.json?

Yes. Confirmed by `test_project_added_rules_implemented` (assert len == 63) and the P063 entry is present.

### All modules present in src/njit_auditor/rules/?

Confirmed. All 63 P-rules map to existing modules:

| Rule range | Module(s) |
|---|---|
| P001 | `latex_risky_commands.py` |
| P002–P004 | `latex_labels.py` |
| P005–P007 | `latex_figures_tables.py` |
| P008 | `latex_structure.py` |
| P009–P010 | `latex_linters.py` (via `latex_linters.py` in parent package) |
| P011 | `pdf_margins.py` |
| P012 | `pdf_annotations.py` |
| P013, P019 | `pdf_page_numbers.py` |
| P014 | `pdf_headings.py` |
| P015 | `pdf_indentation.py` |
| P016 | `pdf_spacing.py` |
| P017 | `pdf_captions.py` |
| P018 | `pdf_toc_alignment.py` |
| P020 | `pdf_title_capitalization.py` |
| P021 | `latex_abstract.py` (TeX) + `pdf_abstract.py` (PDF) |
| P022 | `pdf_frontmatter_no_page_number.py` |
| P023 | `pdf_body_spacing.py` |
| P024 | `pdf_toc_list_formatting.py` |
| P025 | `pdf_frontmatter_structure.py` |
| P026 | `pdf_font_compliance.py` |
| P027 | `pdf_heading_levels.py` |
| P028 | `pdf_page_numbering_regime.py` |
| P029 | `pdf_roman_sequence.py` |
| P030 | `pdf_toc_continued_headings.py` |
| P031 | `pdf_lot_lof_column_headers.py` |
| P032 | `pdf_toc_list_wrapped_spacing.py` |
| P033 | `pdf_title_consistency.py` |
| P034, P051, P052 | `pdf_copyright_page.py` |
| P035 | `pdf_figure_table_layout.py` |
| P036 | `pdf_toc_list_entry_spacing.py` |
| P037 | `pdf_roman_section_anchors.py` |
| P038 | `pdf_frontmatter_headings.py` |
| P039 | `pdf_toc_entry_hierarchy.py` |
| P040 | `pdf_lof_terminal_punctuation.py` |
| P041 | `pdf_dedication_page.py` |
| P042 | `pdf_toc_appendix_format.py` |
| P043 | `pdf_acknowledgements_indentation.py` |
| P044 | `pdf_abstract_indentation.py` |
| P045 | `pdf_biosketch_publication_layout.py` |
| P046 | `pdf_lot_lof_entry_number_alignment.py` |
| P047 | `pdf_biosketch_bullet_spacing.py` |
| P048 | `pdf_lot_lof_page_number_alignment.py` |
| P049, P050 | `pdf_lot_lof_column_header_style_alignment.py` |
| P053 | `pdf_lot_terminal_period.py` |
| P054 | `pdf_toc_terminal_period.py` |
| P055 | `pdf_lot_lof_entry_type.py` |
| P056 | `pdf_lot_lof_number_format.py` |
| P057 | `pdf_lot_lof_page_number_ordering.py` |
| P058 | `pdf_toc_page_number_ordering.py` |
| P059 | `pdf_lot_lof_entry_number_ordering.py` |
| P060 | `pdf_toc_entry_number_ordering.py` |
| P061 | `pdf_lot_lof_cross_page_entry_ordering.py` |
| P062 | `pdf_toc_cross_page_entry_ordering.py` |
| P063 | `pdf_appendix_body_headings.py` |

### Wiring verification (audit_runner.py)

`collect_pdf_layout_findings()` in `audit_runner.py` calls all P011–P063 checks in canonical order. P063 (`check_pdf_appendix_body_headings`) is imported and invoked. `PDF_AUDIT_POST_P054_RULE_IDS` and `PDF_AUDIT_POST_P054_CALLABLE_NAMES` tuples correctly include P063 as the last entry.

`collect_tex_findings()` covers P001–P010 (plus Q004/Q005/Q006) for TeX/ZIP uploads.

### Metadata vs code consistency

No mismatches detected. All 63 `project_added_rules.json` entries have `implementation_status: implemented`, each points to an existing module, and `test_project_added_rules_implemented` asserts all 63 are correct.

### Stale P-rule scope claims in docs

Several status docs still say "P001–P062" or "62/62 implemented" — these are stale. See section 3.9 for the complete list.

---

## 3.3 Q-Rule / Guideline Coverage

Source: `njit_rule_inventory.json` (79 entries, Q001–Q079), validated by `test_all_ester_rules_represented_in_inventory`.

| Status | Count | Notes |
|---|---:|---|
| `implemented` | 2 | Q004 (abstract forbidden words), Q005 (abstract first-person pronouns) |
| `partially_implemented` | 55 | Broad set covered by P-rule heuristics |
| `not_implemented` | 22 | 9 manual-only (`checkability=manual`); 13 automatable gaps |

**Note:** The test asserts `implemented=2`, `partially_implemented=55`, `not_implemented=22`. The `current_project_state_and_next_steps.md` document lists slightly different counts (51/26 from a prior snapshot) — the JSON and tests are authoritative.

### Top remaining automatable gaps (by Q-rule ID)

| Q-rule | Topic | Gap |
|---|---|---|
| Q023–Q025 | Bio Sketch degree chronology | Content-level ordering; partially addressed by P045/P047 for layout |
| Q027, Q030 | Bio Sketch publication ordering/citation style | Q027 now partially covered by P067; Q030 citation style remains manual/heuristic |
| Q033–Q034 | Dedication centering and italic | Visual layout requiring image analysis or font-style extraction |
| Q037–Q043 | Acknowledgements paragraph intent | Semantic; requires NLP-level interpretation |
| Q015–Q020 | Approval page committee order/rank | Semantic; requires knowledge of institutional roles |

### Top manual-only gaps (9 rules)

Q007 (title-page institutional template), Q015–Q020 (approval-page committee semantics), Q037–Q038 (acknowledgements advisor/committee intent): all require human review.

### Not fully implemented count

Approximately 22 Q-rules not implemented (13 automatable, 9 manual-only), and 55 Q-rules only partially covered. Approximately 0 Q-rules remain both automatable and completely unaddressed — the remaining automatable gaps are in content-semantic areas (degree chronology, citation style, dedication visual layout).

---

## 3.4 P063 State

| Item | Status |
|---|---|
| Module | `src/njit_auditor/rules/pdf_appendix_body_headings.py` — present and imported |
| Metadata in `project_added_rules.json` | Present; `implementation_status: implemented`; correct module path |
| Test file | `tests/test_p063_appendix_body_headings.py` — 13 synthetic tests, all passing |
| Wired in `audit_runner.py` | Yes — `check_pdf_appendix_body_headings` called in `collect_pdf_layout_findings()` |
| Wired in `PDF_AUDIT_POST_P054_CALLABLE_NAMES` | Yes — last entry |
| `docs/planning/p063_scope_and_design.md` | Present |
| Evaluation doc | No current-dataset audit run — only 4/5 evaluation PDFs directly accessible; no `p063_current_dataset_evaluation.md` |
| Current evaluation_data_manifest.json note | Missing — no `p063_current_dataset_note` in JSON |
| `current_project_state_and_next_steps.md` | P063 entry is present but the "Auditor scope" summary line still says "P001–P062" |
| `README.md` | Already updated to P001–P063 in rule table and usage sections |

**Issue types emitted:** `single_appendix_uses_letter_label`, `multiple_appendix_missing_letter`, `appendix_letter_sequence_gap`, `appendix_letter_sequence_repeat`.

**Gate:** Body region must be detected (CHAPTER or APPENDIX body heading required) before scanning. Skips documents with no body start detected.

---

## 3.5 Evaluation / Data Inventory

### Guideline / rule-source files

| Category | Count |
|---|---:|
| Guideline/rule-source files in `data/raw/guidelines/` | 8 |
| Processed rule inventory files in `data/processed/rules/` | 2 |

### Real dissertation sample counts

| Category | Count |
|---|---:|
| EF-commented dissertation PDFs (tracked) | 4 |
| EF-commented dissertation PDFs (referenced, not standalone tracked) | 1 |
| Clean/no-feedback baseline ZIP (tracked) | 1 |
| Clean/no-feedback baseline PDF (archive-contained) | 1 |
| Original-archive-only EF materials (not committed) | 12 |

### EF-commented extractable vs. flattened

| Label | Comment status | Extractable count |
|---|---|---:|
| Cibaku Elson 1st Review | extractable | 78 |
| Yin Haotian 2nd Review | extractable | 65 |
| Yin H 2nd Review (flattened) | flattened | 0 |
| Yin H 4th Review (compressed) | compressed/flattened | 0 |

Only 2 of 4 tracked EF PDFs yield extractable comments for auditor-vs-expert comparison.

### Raw/commented pair status

No committed raw/uncommented drafts are paired with committed EF-commented versions for the same document. The Sebastian Fine pair is the nearest candidate, but the EF-annotated version is not locally accessible as a standalone file.

### Synthetic web demo fixture count

5 committed synthetic fixtures in `tests/fixtures/web_demo/`:
- `clean_minimal.pdf`, `issues_pdf.pdf`, `clean_minimal.tex`, `issues_tex.tex`, `demo_project.zip`

Plus `demo_project_extracted/` as an untracked runtime directory (safe to gitignore).

### Generated / gitignored paths

`data/evaluation/generated/` is gitignored (confirmed in `.gitignore`). The directory exists locally with multiple evaluation subdirectories — none of these are tracked. Generated outputs are correctly kept out of the repository.

---

## 3.6 Real Thesis / EF Overlap Readiness

| Label | EF comments extractable? | Raw/clean version? | Comparison status |
|---|---|---|---|
| Cibaku Elson 1st Review | yes (78) | none tracked | ready for overlap; comparison already done |
| Yin Haotian 2nd Review | yes (65) | none tracked | ready for overlap; comparison already done |
| Yin H 2nd Review (flattened) | no | none tracked | aggregate counts only; no EF extraction |
| Yin H 4th Review (compressed) | no | none tracked | aggregate counts only; inflated P011 |
| Sebastian Fine (clean baseline) | n/a | archive-contained (via ZIP) | clean baseline only; no EF comments |
| Archive-only EF files (10) | not verified | none committed | needs extraction from Google Drive RAR |

### Comparisons already done

- EF comment-vs-tool page/category overlap: Cibaku and Yin Haotian (P001–P029 scope in `docs/evaluation/current_ef_comment_vs_tool_comparison.md`)
- EF overlap refinement round 1 (P013 noise reduction): `docs/evaluation/ef_overlap_driven_refinement_evaluation.md`
- EF overlap refinement round 2 (P018/P024 heading variants): `docs/evaluation/ef_overlap_refinement_round2_evaluation.md`
- Real-thesis pairing and overlap readiness doc: `docs/evaluation/real_thesis_pairing_and_ef_overlap_readiness.md`

### Key findings from overlap work

- All EF-commented pages have at least one tool finding (EF-only pages = 0 on both extractable-comment files).
- Category overlap is narrow: tool coverage concentrated in page_numbering/font_format/margin; EF comments concentrated in unclear_or_other/references_citations/committee_approval_page.
- Biggest unaddressed EF categories: `references_citations` (5+4 comments), `committee_approval_page` (3+2 comments).

### Real-data work remaining

1. No post-P063 current-dataset evaluation run performed.
2. No EF overlap refresh since P029 era; rules P030–P063 added significant new coverage that has not been compared against EF comments.
3. Sebastian Fine EF-annotated version not locally available; expanding extractable comparison set to 3 files requires archive extraction.

---

## 3.7 Current Evaluation Snapshots

| Era | Rules | Grand total | Key numbers | Commit |
|---|---|---:|---|---|
| P034-era (historical canonical) | P011–P034 | 1,446 | P013: 461, P026: ~388, P011: 169 | `00b9c2d` |
| P061-era | P011–P061 | 1,587 | P013: 461, P026: 415, P036: 77 | `ffea4e3` |
| P062-era (latest full five-PDF) | P011–P062 | 1,587 | P013: 461, P026: 415, P011: 169, P012: 143, P036: 77; P062: 0 | `36373c9` |
| P063-era (full five-PDF run, 2026-06-07) | P011–P063 | **1,587** | P013: 461, P026: 415, P011: 169, P012: 143, P036: 77; P063: 0 | `f170be5` |

### Top rules from P062-era snapshot (five PDFs)

| Rank | Rule | Total | Category |
|---:|---|---:|---|
| 1 | P013 | 461 | page_numbering |
| 2 | P026 | 415 | font_format |
| 3 | P011 | 169 | margin_or_overflow |
| 4 | P012 | 143 | annotations |
| 5 | P036 | 77 | list_of_tables_figures_toc |

### P062 / P063 behavior on five-file set

- **P062:** 0 findings (no qualifying cross-page TOC numeric sequence on this dataset).
- **P063:** 0 findings on five-PDF set (2026-06-07, commit `f170be5`). No qualifying body-region appendix heading sequence detected on this dataset; does not prove compliance if body heading gate not met. See `docs/evaluation/current_auditor_after_p063_evaluation.md`.

### Generated output folders

All in `data/evaluation/generated/` (gitignored). Key subdirectories present:
`current_auditor_after_p034_p011_triage/`, `current_auditor_after_p061/`, `current_auditor_after_p062/`, and many per-rule evaluation subdirectories. None are tracked.

---

## 3.8 Web / UI State

| Feature | Status |
|---|---|
| Upload types accepted | PDF, TeX (.tex), ZIP |
| PDF audit scope | P011–P063 |
| TeX/ZIP audit scope | P001–P010 (source; no compilation) |
| URL audit | Public HTTPS PDF URLs; SSRF-guarded |
| Built-in sample audit | Local evaluation PDFs via dropdown |
| JSON/Markdown downloads | Yes for all upload kinds |
| Privacy-reduced web exports | Yes — `sanitize_report_for_web_export()` for TeX/ZIP findings; basename-only paths for PDF |
| Job TTL cleanup | Yes — `cleanup_expired_jobs()` with `NJIT_AUDITOR_WEB_JOB_TTL_SECONDS` (default 24h) |
| Triage panels | P011, P012, P013, P026 |
| Synthetic fixtures | 5 committed in `tests/fixtures/web_demo/`; 21 smoke tests in `test_web_demo_fixtures.py` |
| Web demo smoke script | `scripts/web_demo_smoke.sh` |
| Web demo guide | `docs/web_ui_demo_guide.md` |
| Manual QA checklist | `docs/web_ui_manual_qa_checklist.md` |

### Known remaining caveats

| Caveat | Notes |
|---|---|
| No LaTeX compilation | TeX/ZIP audits run P001–P010 source checks only |
| No PDF annotation overlays | Finding markers on PDF pages not implemented (GUI Phase 4+) |
| No authentication or rate limiting by default | Public deployments need reverse proxy, TLS, auth, and rate limiting |
| In-memory job state lost on restart | On-disk files remain until TTL cleanup |
| Web exports privacy-reduced, not fully anonymized | `sanitize_report_for_web_export()` removes known private keys; does not guarantee perfect anonymization of all future field values |
| CLI export unchanged by web sanitizer | CLI `--json-out`/`--md-out` not sanitized |
| Sanitizer key list requires maintenance | If future source rules add private-content fields, update `_UNSAFE_SOURCE_DETAIL_KEYS` |
| URL audit only | ZIP not supported for URL audit mode |

---

## 3.9 Documentation Consistency

### Files with stale content

| File | Stale content | Correct value |
|---|---|---|
| `docs/status/current_project_state_and_next_steps.md` line 36 | "Auditor scope: P001–P062 implemented" | P001–P063 |
| `docs/status/current_project_state_and_next_steps.md` line 233 | "run_pdf_audit_full() / collect_pdf_layout_findings() — P011–P062" | P011–P063 |
| `docs/status/current_project_state_and_next_steps.md` line 255 | "P-rules (P001–P062) | 62 | 62" | P001–P063 | 63 | 63 |
| `docs/status/data_inventory_and_evaluation_sources.md` line 4 | "P001–P062 implemented … 876 pytest" | P001–P063; 889 pytest |
| `docs/status/data_inventory_and_evaluation_sources.md` line 12 | "defining … project P001-P062 implementation rules" | P001-P063 |
| `docs/status/data_inventory_and_evaluation_sources.md` line 54 | "P001-P062 all implemented" and "62/62 implemented" | P001-P063; 63/63 |
| `docs/status/evaluation_data_manifest.md` line 4 | "Latest main: 36373c9 … P001–P062 implemented" | `71b3823`; P001–P063 |
| `docs/status/evaluation_data_manifest.md` line 5 | "876 pytest" | 889 pytest |
| `docs/status/evaluation_data_manifest.md` line 57 | "P | 62 (P001–P062)" | 63 (P001–P063) |
| `docs/status/evaluation_data_manifest.md` line 59 | "P001–P062 are implemented" | P001–P063 |
| `data/processed/evaluation_data_manifest.json` | `p_rules_implemented: "P001-P062"`, `pytest_count_at_last_doc_refresh: 876`, `latest_main_at_last_doc_refresh: "36373c9"`, `rule_count: 62`, `rule_id_range: "P001-P062"`, no `p063_current_dataset_note` | P001-P063, 889, 71b3823, 63, P001-P063, plus P063 note |
| `docs/evaluation/real_thesis_pairing_and_ef_overlap_readiness.md` line 4 | "Auditor scope: P001–P062 implemented; 876 pytest" | P001–P063; 889 pytest |
| `docs/evaluation/real_thesis_pairing_and_ef_overlap_readiness.md` lines 96–123 | Table/text references to P011–P061 era; P062 still not run | Needs P063 addendum note |
| `docs/status/source_to_implementation_coverage_after_p029.md` line 11 | "P-rule implementation: 61/61 implemented (P001–P061)" | Historical baseline doc — acceptable as-is since it is a dated snapshot |

### README.md

`README.md` already correctly describes P011–P063 and is up to date. No changes needed.

### Evaluation data manifest doc vs JSON

`docs/status/evaluation_data_manifest.md` says "876 pytest" (stale) and references "P001–P062". The machine-readable `data/processed/evaluation_data_manifest.json` also has stale rule count (62) and pytest count (876). Both need updating.

### Files that do NOT need changes

- All per-rule evaluation docs (they are dated point-in-time snapshots).
- `docs/evaluation/current_auditor_after_p062_evaluation.md` (correct for its era).
- `docs/status/source_to_implementation_coverage_after_p029.md` (dated P029 baseline; acceptable as historical record).
- `README.md` (already up to date through P063).

---

## 3.10 Generated-Output and Privacy Hygiene

| Check | Status |
|---|---|
| `data/evaluation/generated/` gitignored? | Yes |
| Any generated reports or extracted PDFs tracked? | No — confirmed by directory presence but gitignore exclusion |
| Synthetic fixtures in `tests/fixtures/web_demo/`? | Yes — all 5 fixtures are committed; all contain synthetic placeholder text only |
| Private dissertation body text in docs? | No — all evaluation docs use aggregate counts and page numbers only |
| Private dissertation body text in tests? | No — confirmed by fixture privacy model (synthetic text) |

---

## 3.11 Issues / Risks

### Blocking

None at this time. All validation passes (ruff, mypy, pytest).

### High

| Issue | Notes |
|---|---|
| Stale P-rule scope in several status docs | `current_project_state_and_next_steps.md`, `data_inventory_and_evaluation_sources.md`, `evaluation_data_manifest.md`, `evaluation_data_manifest.json`, `real_thesis_pairing_and_ef_overlap_readiness.md` all say P001–P062 or 62/62 instead of P063 |
| No EF overlap refresh since P029 era | Rules P030–P063 added substantial new coverage; the EF overlap comparison has not been refreshed |

### Medium

| Issue | Notes |
|---|---|
| EF overlap comparison stale since P029 era | Rules P030–P063 added substantial new coverage; the EF overlap comparison in `current_ef_comment_vs_tool_comparison.md` is 30+ rules behind |
| No p063_current_dataset_note in manifest JSON | Machine-readable manifest does not record P063 evaluation status; adds inconsistency |
| 4/5 evaluation PDFs accessible for per-rule runs | Sebastian Fine Revision 3 requires ZIP extraction; prevents full five-PDF per-rule coverage for P044+ |
| P020 recall low due to font metadata quality | Fires only where bold font metadata is available; many PDFs lack reliable metadata |
| Ordering rules sparse on current dataset | P057–P062 consistently return 0 on evaluation PDFs due to sparse comparable entries |

### Low

| Issue | Notes |
|---|---|
| `demo_project_extracted/` untracked runtime dir | Not tracked, not gitignored explicitly, but not harmful |
| `source_to_implementation_coverage_after_p029.md` says 61/61 | Historical dated doc; not misleading if read in context |
| Sanitizer key list may drift | If future P001–P010 source rules add private detail fields, `_UNSAFE_SOURCE_DETAIL_KEYS` in `report_outputs.py` must be updated |

### Future enhancement

| Item | Notes |
|---|---|
| References/citations rule (P064 candidate) | Scope doc complete: `docs/planning/p064_references_citations_structural_check_scope_and_design.md`; ready for implementation in next PR |
| Committee/approval-page structural refinements | **P068 implemented** — role-label and signature/date block counts; Q015–Q020 remain manual |
| Image-heavy page detection for P035 | v1 skips image-only floats; extend to rasterized figure detection |
| No PDF page preview or annotation overlay | GUI Phase 4+; privacy-safe geometry markers only |
| No auth/rate limiting by default | Public deployments require reverse proxy, TLS, authentication, rate limiting |

---

## 3.12 Recommended Next Tasks

| Priority | Task | Rationale |
|---|---|---|
| 1 | Fix stale docs and manifest (done in this PR) | `evaluation_data_manifest.json` and several status docs still reference P001–P062; fixes are trivial and keep status accurate |
| 2 | Run post-P063 full five-PDF aggregate | 1,587 total is the last snapshot (P062-era); P063 adds appendix heading checks; run `njit-audit pdf` on all five evaluation PDFs and produce `docs/evaluation/current_auditor_after_p063_evaluation.md` |
| 3 | Refresh EF overlap comparison | Last run at P029 era; 30+ new rules not reflected; re-run on both extractable-comment PDFs (Cibaku, Yin Haotian) and produce updated aggregate doc |
| 4 | P064 — References/citations structural check | Biggest gap by EF comment volume with zero tool coverage; could check reference-section heading presence, hanging-indent consistency, or year-format patterns in reference list |
| 5 | P064 alt — Dedication page centering/italic check | Q033/Q034 completely unimplemented; detectable via PDF geometry (bounding box centering) and font-style metadata |
| 6 | Improve ordering rule entry-extraction recall | P059–P062 find 0 comparable entries on compressed/multi-column PDFs; shared extraction improvements before adding more ordering rules |
| 7 | Extract Sebastian Fine EF-annotated version from archive | Expands extractable comparison set from 2 to 3 files; already documented as the primary archive expansion step |
| 8 | Consider adding `p063_current_dataset_note` to manifest JSON | Keeps machine-readable manifest consistent with other per-rule notes |

---

## Cross-References

- Implementation status: `docs/status/current_project_state_and_next_steps.md`
- Rule inventory: `data/processed/rules/project_added_rules.json`, `data/processed/rules/njit_rule_inventory.json`
- Evaluation data manifest (human): `docs/status/evaluation_data_manifest.md`
- Evaluation data manifest (machine): `data/processed/evaluation_data_manifest.json`
- Data inventory: `docs/status/data_inventory_and_evaluation_sources.md`
- Latest full evaluation snapshot (P063-era): `docs/evaluation/current_auditor_after_p063_evaluation.md`
- **EF overlap after P063 (refreshed):** `docs/evaluation/ef_overlap_after_p063_evaluation.md`
- EF overlap readiness: `docs/evaluation/real_thesis_pairing_and_ef_overlap_readiness.md`
- Prior EF overlap (P001–P029 scope): `docs/evaluation/current_ef_comment_vs_tool_comparison.md`
- Web UI docs: `docs/web_gui_mvp.md`, `docs/web_ui_manual_qa_checklist.md`, `docs/web_ui_demo_guide.md`
- P063 design: `docs/planning/p063_scope_and_design.md`
