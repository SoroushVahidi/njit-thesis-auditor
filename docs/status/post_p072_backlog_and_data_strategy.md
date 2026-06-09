# Post-P072 Backlog and Data Strategy

- **Date:** 2026-06-09
- **Baseline commit:** `b889e5f` (PR #263 — P072 post-implementation evaluation and EF-overlap refresh)
- **Validation:** P001–P072 implemented; **1014 pytest**; ruff clean; mypy 87 source files, no issues
- **Canonical aggregate:** **1,543** (unchanged post-P072; `docs/evaluation/current_auditor_after_p070_evaluation.md`)
- **Privacy:** Aggregate-only. No dissertation body text, EF comment text, author names, reference entries, or approval-page text quoted.

---

## 1. Repository State Verification

| Check | Result |
|---|---|
| Latest main | `b889e5f` (PR #263) |
| Branch | `main` |
| Working tree | Clean, in sync with `origin/main` |
| Highest implemented P-rule | **P072** |
| P-rules in `project_added_rules.json` | **72** |
| Infrastructure-only P-rules | P069, P070, P071, P072 (no standalone issue types) |
| Standalone finding rules | **68** (P001–P068) |
| pytest count | **1014** |
| Generated outputs tracked | None — `data/evaluation/generated/` is gitignored |
| Accidentally tracked dissertation PDFs | None |

### Stale references found (addressed in this PR)

| Location | Stale content | Correction |
|---|---|---|
| `README.md` line 181 | "P001–P071 implemented; **1000 pytest**" | P001–P072; 1014 pytest |
| `data/processed/evaluation_data_manifest.json` `generated_for_commit` | `bbb65cc` | `b889e5f` |
| `data/processed/evaluation_data_manifest.json` `latest_main_at_last_doc_refresh` | `97f2b30` | `b889e5f` |
| `docs/status/data_inventory_and_evaluation_sources.md` processed-data section | "P001-P071" | P001-P072 |

---

## 2. Evaluation and Status Documentation Consistency

| Check | Status |
|---|---|
| Docs reflect P001–P072 and 1014 tests | Mostly — minor stale fields corrected in this PR |
| Canonical aggregate 1,543 clearly stated | Yes — `current_auditor_after_p070_evaluation.md` (unchanged) |
| No separate post-P072 aggregate needed | Confirmed — P072 infrastructure-only, aggregate unchanged |
| EF overlap after P072 indexed | Yes — `ef_overlap_after_p072_evaluation.md`; manifest updated |
| P072 evaluation docs linked | Yes — manifest, `current_project_state_and_next_steps.md`, README |
| Stale P071/P072 "not yet implemented" references | Resolved in prior PRs #258–#263 |

`docs/status/full_repository_audit_after_p071.md` already carries a P072 note (added after PR #262). No separate `full_repository_audit_after_p072.md` is needed because the aggregate, test count, and rule inventory are unchanged except for the infrastructure-only P072 addition.

---

## 3. Remaining EF Gaps and Root Causes

### 3.1 `committee_approval_page` (5 EF comments, 0 tool findings)

| Item | Status |
|---|---|
| Implemented rules | P068 (structural check), P072 (heading-gate recall / structural fallback) |
| P068 reach on comparison PDFs | 0/2 |
| P072 structural fallback outcome | 0 role-label candidates on all 3 non-detecting files |
| Root cause | Approval pages on both comparison PDFs are image-embedded; text layer yields noise-only fragments, not word-level role-label phrases |
| Remaining blocker | No machine-readable approval-page text; OCR out of scope |
| Further rule work justified? | **No** — not until comparison PDFs have text-layer approval pages or OCR is added |
| More data needed? | Yes — PDFs with text-layer approval pages would activate P072 structural fallback |
| Manual-only? | For this dataset: effectively manual-only on comparison PDFs |

### 3.2 `references_citations` (9 EF comments, 0 tool findings)

| Item | Status |
|---|---|
| Implemented rules | P064 (structural check), P071 (localization recall) |
| P064 reach on comparison PDFs | 2/2 after P071 (localization fixed) |
| P064 findings on comparison PDFs | 0 structural findings |
| Root cause | EF comments target citation style, missing entries, or semantic/content issues not modeled by P064 v1 structural checks |
| Remaining blocker | Semantic/style gap; Q030 is manual-only (citation style enforcement) |
| Further rule work justified? | **No** — localization is fixed; remaining gap requires semantic content analysis |
| More data needed? | Not for this gap specifically; rule logic is sound |
| Manual-only? | Remaining gap is manual/process-only per Q030 classification |

### 3.3 `list_of_tables_figures_toc` (4 EF comments, 0 tool findings)

| Item | Status |
|---|---|
| Implemented rules | P030–P053, P054, P057–P062 (formatting rules); P070 (parser recall refinement) |
| P070 outcome | Improved parser recall (185→167 entries deduplicated); but comparison PDFs still have 0 detected list pages |
| Root cause | Comparison PDFs (Cibaku, Yin Haotian 2nd) do not have machine-readable LoT/LoF list pages detectable by current parser — or their list pages do not match detection patterns |
| Remaining blocker | Data limitation: 4 EF comments on this category come entirely from Yin Haotian 2nd review; the parser finds 0 list pages on this file |
| Further rule work justified? | **Not yet** — would need evidence from a file where list pages are detected to validate improvement |
| More data needed? | Yes — a third comparison PDF where LoT/LoF is detected would clarify whether parser changes help |
| Manual-only? | Not manual-only by design; data-limited in practice for current comparison set |

### 3.4 `unclear_or_other` (88 EF comments)

| Item | Status |
|---|---|
| Coverage | Out-of-scope / manual-only / heuristic classification gap |
| Remaining blocker | EF categorization is keyword-based; 88 comments span diverse formatting issues not captured by category mapping |
| Further rule work? | Not applicable — this is a categorization gap, not a rule gap |
| Notes | Persistent structural limitation of the 2-file comparison set |

---

## 4. Q-Rule Backlog Summary

From `data/processed/rules/njit_rule_inventory.json` (79 Q-rules):

| Status | Count |
|---|---:|
| `implemented` | 2 (Q004, Q005 — abstract forbidden words, abstract first-person) |
| `partially_implemented` | 60 |
| `not_implemented` | 17 |
| Manual-only (`checkability: manual`) | 9 (Q007, Q015–Q020, Q037, Q038) |

### Not-implemented automatable/heuristic gaps

| Rule | Section | Checkability | Remaining blocker |
|---|---|---|---|
| Q023 | Biographical Sketch | heuristic | Requires content reading (exclude birth-place/date text) — high false-positive risk |
| Q024 | Biographical Sketch | heuristic | Requires content reading (exclude employment history) — high false-positive risk |
| Q030 | Biographical Sketch / References | heuristic | Citation style consistency — manual-only; no reliable structural proxy |
| Q039 | Acknowledgements | heuristic | Semantic paragraph intent; very limited structural proxy possible |
| Q040 | Acknowledgements | heuristic | Grant attribution presence — semantic; false-positive risk |
| Q041 | Acknowledgements | heuristic | Peer/colleague thanks — semantic |
| Q042 | Acknowledgements | heuristic | Family thanks — semantic |
| Q043 | Acknowledgements | heuristic | Full-name usage — requires named-entity recognition |

### Not-implemented manual-only (deferred by design)

Q007 (Title Page institutional block exact match), Q015–Q020 (committee rank/order/affiliation), Q037–Q038 (Acknowledgements intent) — manual review required; automation would require AI/NLP.

### Contradictions and stale statuses

- Q025–Q029 inventory entries still say `not_implemented` or `partially_implemented` though P066/P067 partially address Q025 (degree ordering) and Q027/Q028/Q029 (publication layout/ordering). Inventory metadata lags P066/P067; considered low-priority to backfill given rules are in production.

### Partially-implemented Q-rules — major clusters

| Section | Partial count | Notes |
|---|---:|---|
| Table of Contents | 14 | Most structural sub-checks covered by P030–P042, P054, P058–P062 |
| List of Tables | 10 | Most covered by P031–P059; column/header/formatting aspects addressed |
| List of Figures | 10 | Symmetric to LoT; mostly covered |
| Biographical Sketch | 7 | Structural (ordering, layout) covered by P045–P047, P066–P067; content not covered |
| Copyright Page | 4 | P034, P051, P052 cover structural presence + year/author |
| Dedication Page | 4 | P041, P065 cover header/centering/italic |
| Acknowledgements | 4 | P043 covers indentation; paragraph content deferred |
| Abstract | 3 | P044, P021 cover indentation and word count |

---

## 5. Data Limitations

### Current comparison set

| File | EF comment status | Used in EF overlap |
|---|---|---|
| Cibaku Elson 1st Review | 78 extractable | Yes |
| Yin Haotian 2nd Review | 65 extractable | Yes |
| Yin H 2nd Review (flattened) | 0 extractable | No |
| Yin H 4th Review (compressed) | 0 extractable | No |
| Sebastian Fine clean baseline | No EF comments | No (clean baseline only) |

**Only 2 files usable for EF overlap.** This is the single most important data limitation. All three
remaining EF category gaps (approval page, references, list pages) are now confirmed data-limited
rather than algorithm-limited after P071/P072.

### Sebastian Fine EF-annotated PDF

`250128 Sebastian.Fine Revised 1st Dissertation Draft EF.pdf` is documented in the manifest as
`referenced_not_standalone_tracked` — it exists in the original archive but is not a standalone
tracked path in the working tree. Recovering it would expand the comparison set from 2 to 3 files,
improving metric stability and potentially providing new data points for `list_of_tables_figures_toc`
(if the fine PDF has detected list pages).

### Unevaluated rules (current-dataset audit not run)

Many P-rules have never been run against the full five-PDF set because only 4/5 PDFs were directly
accessible when those rules were implemented. Now that all 5 PDFs are accessible (Sebastian Fine
via ZIP), a comprehensive current-dataset evaluation gap-fill is possible:

| Rules | Reason not evaluated |
|---|---|
| P036–P039, P041–P043 | Evaluation PDFs unavailable at implementation time |
| P040, P044–P048, P051–P063 | Only 4/5 PDFs directly accessible at implementation time |

---

## 6. Candidate Next-Step Comparison

### Candidate A: Data acquisition — Sebastian Fine EF archive recovery

| Dimension | Assessment |
|---|---|
| Type | Data acquisition |
| Evidence | Manifest documents the file as `referenced_not_standalone_tracked`; archive zip is committed |
| Expected value | **High** — expands comparison set to 3 files; may provide new list-page data points; improves metric stability across all EF categories |
| Implementation risk | Medium — file may not be recoverable from current archive without original bundle |
| Privacy risk | High (local only; file must never be committed as standalone PDF) |
| Ready to scope? | **Yes** — search archive, extract locally if found, run overlap eval, update docs |

### Candidate B: Evaluation gap-fill — current-dataset evals for P036–P063

| Dimension | Assessment |
|---|---|
| Type | Evaluation / documentation |
| Evidence | ~20 rules have "current-dataset audit not run" status; all 5 PDFs now accessible |
| Expected value | **Medium-High** — provides comprehensive performance picture; may reveal zero-or-low-signal rules for future triage; no code changes |
| Implementation risk | Low — no audit code changes |
| Privacy risk | Low (aggregate counts only; generated outputs gitignored) |
| Ready to scope? | Yes, but large scope — best done as a separate dedicated PR |

### Candidate C: P073 — P019 reporting triage refinement

| Dimension | Assessment |
|---|---|
| Type | Rule refinement / reporting |
| Evidence | P019 has 67 five-PDF findings; page-numbering category; no triage rollup (unlike P011/P013/P026) |
| Expected value | Low-medium — improves reporting actionability for page-numbering sequence findings |
| Implementation risk | Low — precedent from P011/P013/P026 triage rollups |
| Privacy risk | Low (aggregate page-numbering metadata) |
| Ready to scope? | Yes — straightforward addition to existing P019 logic |

### Candidate D: P073 — LoT/LoF/list-page detection recall refinement

| Dimension | Assessment |
|---|---|
| Type | Infrastructure refinement (P070 companion) |
| Evidence | 4 EF comments, 0 tool on comparison PDFs; but P070 already improved recall; comparison PDFs have no detected list pages |
| Expected value | Low — data-limited; no evidence that additional parser paths would fire on current comparison PDFs |
| Implementation risk | Medium — risk of introducing false positives without evaluation data to validate |
| Privacy risk | Low |
| Ready to scope? | **Not yet** — data acquisition first; new comparison PDF needed to evaluate impact |

### Candidate E: P073 — approval-page image/text-layer limitation documentation

| Dimension | Assessment |
|---|---|
| Type | Documentation/evaluation |
| Evidence | P072 fully confirmed the limitation; already documented in P072 eval |
| Expected value | Low — already well-documented in `p072_approval_page_heading_gate_recall_current_dataset_evaluation.md` |
| Implementation risk | None |
| Ready to scope? | Not needed — existing docs are sufficient |

### Candidate F: P073 — Bio Sketch content checks (Q023/Q024)

| Dimension | Assessment |
|---|---|
| Type | New rule — heuristic content |
| Evidence | Q023/Q024 not implemented; heuristic checkability |
| Expected value | Low-medium — privacy-safe keyword detection possible |
| Implementation risk | High — content-reading rules with high false-positive risk; no EF comment evidence in current set |
| Privacy risk | Medium — bio sketch text reading |
| Ready to scope? | **No** — insufficient EF evidence; high risk |

### Candidate G: P073 — Acknowledgements structural subset (Q039–Q043)

| Dimension | Assessment |
|---|---|
| Type | New rule — semantic/heuristic |
| Evidence | Q039–Q043 not implemented; Q044/Q045 (indentation) already covered by P043 |
| Expected value | Very low — remaining checks are semantic paragraph-intent checks; no reliable structural proxy |
| Implementation risk | Very high — semantic; would require NLP/AI patterns for any real coverage |
| Privacy risk | Medium |
| Ready to scope? | **No** — defer; manual-only by available technique |

### Candidate H: P073 — Equation numbering/layout

| Dimension | Assessment |
|---|---|
| Type | New rule |
| Evidence | No confirmed Q-rule basis; not in inventory |
| Expected value | Unknown |
| Implementation risk | High — requires math-layer parsing or OCR |
| Ready to scope? | **Reject** — no guideline basis in current inventory |

---

## 7. Ranked Next-Step Recommendations

### Recommendation 1 (Primary): Data acquisition — Sebastian Fine EF archive recovery

**The strongest next step is data acquisition, not another P-rule.**

After P072, all three EF category gaps are confirmed data-limited:
- `committee_approval_page`: algorithm confirmed correct; data has no text-layer
- `references_citations`: localization confirmed correct (P071); remaining gap is semantic
- `list_of_tables_figures_toc`: parser confirmed operational (P070); data has no detected list pages

Adding another infrastructure rule to a dataset where the algorithm is already correct and the
data is the bottleneck will not close any EF gap. Recovering the Sebastian Fine EF-annotated PDF
expands the comparison set from 2 to 3 files, which would:
- Improve metric stability on all EF categories
- Potentially provide a file with detected list pages (unblocking `list_of_tables_figures_toc` analysis)
- Allow false-positive delta analysis on a third distinct dissertation

**Target:** `250128 Sebastian.Fine Revised 1st Dissertation Draft EF.pdf`

**Search procedure (privacy-safe):**
1. Check if the file exists in the original Google Drive RAR archive locally.
2. If found, extract locally to `data/evaluation/private/` (gitignored).
3. Run comment extraction to verify EF annotations are machine-readable.
4. If extractable: run full five-file audit comparison; update EF overlap docs with aggregate counts only.
5. Do not commit the extracted PDF or any raw comment text.
6. Commit only curated aggregate overlap docs to `docs/evaluation/`.

**Expected outputs:**
- Updated `docs/evaluation/ef_overlap_after_p073_evaluation.md` (if annotations found)
- Clarification of `list_of_tables_figures_toc` gap on Sebastian Fine (does list-page detection fire?)
- Improved metric confidence for all three remaining EF category gaps

**Recovery attempts:**
- **PR #265 (2026-06-09, commit e3ca516):** BLOCKED — original Google Drive RAR not present locally.
- **Retry 2 (2026-06-09, commit 42e10fb):** BLOCKED — `data/evaluation/private/` absent; no new archives found in workspace or home directory to depth 6. File must be manually placed at `data/evaluation/private/` (gitignored) before next attempt can proceed.

**Branch name:** `data/sebastian-ef-archive-recovery`

### Recommendation 2 (Secondary): Evaluation gap-fill for P036–P063 ✅ COMPLETE

Run current-dataset evaluations for all rules that have never been evaluated on the full five-PDF
set (unevaluated because only 4/5 PDFs were accessible at implementation time). No code changes.
Documents actual performance of ~20 rules on real data.

**Status:** Complete (2026-06-09, commit `85a1326`, PR #266). 27 rules evaluated; 8 with findings
(P036: 55, P038: 16, P044: 7, P051: 3, P037: 3, P046: 2, P040: 1, P053: 1; total 88);
all consistent with canonical 1,543. See `docs/evaluation/p036_p063_current_dataset_gap_fill_evaluation.md`.

**Branch name:** `docs/p036-p063-current-dataset-gap-fill`

### Recommendation 3 (Engineering fallback): P073 — P019 reporting triage ✅ COMPLETE

If data acquisition is blocked (file not in current archive or not recoverable), the best
engineering task is adding a triage rollup to P019 (page-numbering sequence/style/position
inconsistencies, 67 five-PDF findings). This follows the established pattern of P011/P013/P026
triage rollups and improves actionability without narrowing coverage.

**Status:** Complete (2026-06-09, baseline commit `eb66d4a`). P073 v1 docs-only triage rollup
created: 67 P019 findings classified; `sequence_gap` (6) highest-actionability; `multiple_page_numbers`
and `inconsistent_position` on EF PDFs artifact-likely; v2 code rollup (`build_p019_page_numbering_triage_summary()`)
deferred. See `docs/evaluation/p073_p019_page_numbering_triage_rollup.md` and
`docs/planning/p073_p019_page_numbering_triage_rollup_scope_and_design.md`.

**Branch name:** `docs/p073-p019-page-numbering-triage-rollup`

### Deferred / rejected

| Candidate | Decision |
|---|---|
| D: LoT/LoF/list-page recall (P070 companion) | Defer — data-limited; need new comparison PDF first |
| E: Approval-page limitation doc | Not needed — already documented |
| F: Bio Sketch content (Q023/Q024) | Defer — high false-positive risk; no EF evidence |
| G: Acknowledgements structural (Q039–Q043) | Defer — semantic/manual-only |
| H: Equation numbering | Reject — no guideline basis in inventory |

---

## 8. Decision: Should P073 Be Scoped Next, or Data/Evaluation First?

**Decision: Data/evaluation task first. P073 should not be forced.**

Rationale:
- All three EF gaps are confirmed data-limited after P071/P072.
- The algorithm paths (localization, structural fallback, parser recall) are correct and tested.
- Adding another infrastructure rule to an unchanged dataset will not improve EF overlap.
- The comparison set (2 extractable files) is too small to validate new infrastructure rules
  reliably — a rule that fires on a new PDF cannot be distinguished from a rule that fires on noise.
- The P069→P070→P071→P072 infrastructure track has reached its natural limit on the current dataset.

**If data acquisition succeeds:** scope the next EF-overlap evaluation and decide whether a P073
rule is motivated by the new data. If the Sebastian Fine EF PDF shows detected list pages,
`list_of_tables_figures_toc` becomes a candidate for targeted P073 work.

**If data acquisition fails:** the best P073 is Recommendation 3 (P019 triage), which is a
low-risk reporting improvement with established precedent, not a new structural rule.

---

## 9. Privacy and Caveats

- All reporting in this document is aggregate-only.
- No dissertation body text, EF comment text, approval-page text, reference entries, names,
  signatures, captions, or TOC/LoT/LoF entry text is quoted.
- Real dissertation files (`data/raw/ester/`) are tracked but must be handled as
  privacy-sensitive materials.
- Data acquisition (Recommendation 1) must follow privacy-safe extraction: files stay in
  `data/evaluation/private/` (gitignored); only aggregate counts committed.
- Generated outputs remain under `data/evaluation/generated/` (gitignored).
- OCR is out of scope for this project.
- No external network calls are used in auditing.

---

## Cross-References

- Canonical aggregate: `docs/evaluation/current_auditor_after_p070_evaluation.md` (**1,543**)
- EF overlap after P072: `docs/evaluation/ef_overlap_after_p072_evaluation.md`
- P072 current-dataset eval: `docs/evaluation/p072_approval_page_heading_gate_recall_current_dataset_evaluation.md`
- Full repository audit (P071 era, P072 note): `docs/status/full_repository_audit_after_p071.md`
- Rolling status: `docs/status/current_project_state_and_next_steps.md`
- Q-rule inventory: `data/processed/rules/njit_rule_inventory.json`
- P-rule inventory: `data/processed/rules/project_added_rules.json`
- Evaluation data manifest: `docs/status/evaluation_data_manifest.md`
- Real thesis pairing readiness: `docs/evaluation/real_thesis_pairing_and_ef_overlap_readiness.md`
