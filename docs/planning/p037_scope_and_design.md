# P037 Scope and Design

- **Date:** 2026-06-02
- **Status:** **Implemented** — `src/njit_auditor/rules/pdf_roman_section_anchors.py`
- **Baseline main:** `f3768dc` (P001–P036 implemented; reusable-tooling audit PR #91)
- **Implementation PR:** rules/p037-roman-section-anchors

## Current state

| Area | State |
|------|--------|
| P-rules | **36/36** implemented (`P001`–`P036`) |
| Q-rules (raw inventory) | **79** total — **2** implemented, **11** partially_implemented, **66** not_implemented |
| Page-numbering cluster | **P013** candidates, **P019** consistency, **P022** no-number pages, **P028** Roman/Arabic regime, **P029** consecutive visible Roman ordering |
| Front-matter headings | **P014** — layout/style when heading text matches (7 headings); no missing-section detection |
| TOC/List cluster | **P018**, **P024**, **P030**, **P031**, **P032**, **P036** — spacing/alignment complete for v1 |
| Dedication / bio-sketch | Q023–Q030 (semantic), Q033–Q034 (layout) — manual/high-FP |
| Reusable helpers | `_classify_pages`, `_find_no_number_pages`, `detect_page_number_candidates`, `find_named_frontmatter_headings` |

**P029 vs remaining Roman gap:** P029 flags repeats, decreases, and non-consecutive **relative** steps between visible lowercase Roman candidates in front matter. It does **not** enforce **template-anchored** expectations (e.g. Biographical Sketch must show **iv** even when every visible step increments by one but the whole sequence is globally offset). Q022, Q031, Q035, Q046, and Q060 are marked `partially_implemented` via P028/P029 regime/sequence heuristics but lack section-specific absolute checks.

---

## Candidate comparison

### Candidate A — Section-anchored front-matter Roman numerals (recommended)

| Field | Detail |
|-------|--------|
| **Source basis** | Q022 (bio sketch = iv), Q031 (dedication next after bio), Q035 (acknowledgements next after dedication), Q046 (TOC continues), Q060 (LoT continues) |
| **Proposed rule** | **P037** — PDF front-matter section-anchored Roman numerals |
| **Module** | `src/njit_auditor/rules/pdf_roman_section_anchors.py` |
| **Issue types** | `roman_bio_sketch_not_iv`, `roman_section_wrong_value` (metadata includes `section_key`, expected/actual integer values — not prose) |
| **Risk / noise** | **Medium** — optional dedication shifts expected offsets; compressed PDFs may mis-locate candidates; must not duplicate P029 relative checks |
| **Privacy** | **Low** — page numbers, section keys, numeral tokens only |
| **Tests** | Synthetic front matter: bio=iv pass; bio=v fail; offset sequence (v,vi,vii) pass P029 but fail P037 bio anchor; optional dedication skipped |
| **Five-PDF impact** | **Low–moderate** — may surface globally offset sequences missed by P029; complements existing P028 findings |
| **Why P037?** | Clear incremental Q-rule coverage; builds directly on P028/P029/P014 stack; P036 planning ranked this #2 |

### Candidate B — Front-matter exact heading phrase / missing-section detection

| Field | Detail |
|-------|--------|
| **Source basis** | Q013, Q021, Q036, Q047, Q061, Q070 |
| **Proposed rule** | P037 or P014 refinement |
| **Module** | Extend `pdf_headings.py` or new `pdf_frontmatter_heading_phrases.py` |
| **Issue types** | `required_heading_missing`, `heading_phrase_not_exact` |
| **Risk / noise** | **Medium** — P014 already checks layout when heading text matches; spelling variants (`ACKNOWLEDGMENTS` vs `ACKNOWLEDGEMENTS`) |
| **Privacy** | **Low** |
| **Tests** | Missing APPROVAL PAGE; wrong phrase on detected page |
| **Five-PDF impact** | **Low** — P014 at 0 on current five-PDF snapshot after centering fix |
| **Why not P037?** | Mostly refinement of P014; incremental value vs new page-numbering cluster |

### Candidate C — Dedication page centering and italic (Q033–Q034)

| Field | Detail |
|-------|--------|
| **Source basis** | Q033, Q034 |
| **Proposed rule** | P037 — PDF dedication page layout |
| **Module** | `src/njit_auditor/rules/pdf_dedication_page.py` |
| **Issue types** | `dedication_text_not_centered`, `dedication_text_not_italic` |
| **Risk / noise** | **High** — dedication optional; italic metadata often absent |
| **Privacy** | **Medium** — dedication prose must not appear in findings |
| **Tests** | Synthetic centered/offset blocks |
| **Five-PDF impact** | **Unknown/low** — section often absent on evaluation PDFs |
| **Why not P037?** | Narrow optional section; weak PDF text-layer signals |

### Candidate D — Biographical Sketch content/layout subset (Q023–Q030)

| Field | Detail |
|-------|--------|
| **Source basis** | Q023–Q030 |
| **Proposed rule** | P037 — PDF biographical sketch layout |
| **Module** | `src/njit_auditor/rules/pdf_biographical_sketch.py` |
| **Issue types** | Multiple semantic content checks |
| **Risk / noise** | **Very high** — degree ordering, publication parsing, birth-place/date semantics |
| **Privacy** | **High** |
| **Tests** | Difficult without quoting private content |
| **Five-PDF impact** | **Unknown** |
| **Why not P037?** | Unsuitable for heuristic v1; remains manual-only |

### Candidate E — Full five-PDF P001–P036 canonical rerun (non-rule)

| Field | Detail |
|-------|--------|
| **Source basis** | Evaluation/manifest maintenance |
| **Proposed task** | Regenerate aggregate counts; update `generated_for_commit` |
| **Module** | N/A (evaluation workflow) |
| **Risk / noise** | **Low** if outputs stay gitignored |
| **Privacy** | **Medium** — aggregate-only docs required |
| **Why not P037?** | Evaluation PDFs unavailable in workspace; not an implementation rule |

### Candidate F — P035 image-block body layout refinement

| Field | Detail |
|-------|--------|
| **Source basis** | Status §4A figure/table partial coverage |
| **Proposed work** | Extend `pdf_layout.py` image bbox extraction; reduce P035 skips |
| **Risk / noise** | **Medium** — infrastructure change across loaders |
| **Why not P037?** | Refinement of P035, not a new Q-rule cluster |

### Ranking

1. **A — Section-anchored front-matter Roman numerals** (recommended P037)
2. **B — Front-matter exact heading / missing section** (P014 follow-on)
3. **F — P035 image-block refinement** (incremental)
4. **C — Dedication layout** (optional section, high skip rate)
5. **D — Bio-sketch content** (unsuitable for automation v1)
6. **E — Canonical rerun** (evaluation-only; defer until PDFs available)

---

## Selected P037 scope

### Rule title

**P037 — PDF front-matter section-anchored Roman numerals**

### Source basis

- Q022 — first Biographical Sketch page visible numeral must be lowercase Roman **iv**
- Q031 — Dedication page shows next sequential numeral after Biographical Sketch
- Q035 — Acknowledgements page shows next sequential numeral after Dedication
- Q046 — Table of Contents continues Roman sequence after Acknowledgements
- Q060 — List of Tables continues Roman sequence after TOC
- Status gap: `docs/status/current_project_state_and_next_steps.md` §4A (Roman numeral **value** beyond P028/P029 relative checks)
- Complements **P028** (regime/style), **P029** (relative ordering); does **not** replace them

### Scope included

1. Restrict to pages classified as `front_matter` via P028 `_classify_pages()`; skip body and ambiguous regions.
2. Reuse `detect_page_number_candidates()`; consider only `roman_lower` candidates within `_MAX_PLAUSIBLE_FRONTMATTER_ROMAN` (same cap as P029).
3. **Anchor:** On the first detected **BIOGRAPHICAL SKETCH** page (`find_named_frontmatter_headings`), require visible Roman value **4** (`iv`). Emit `roman_bio_sketch_not_iv` when a confident candidate exists and value ≠ 4.
4. **Sequential sections:** After anchor, validate expected values at first pages of detected sections in NJIT template order:
   - DEDICATION (optional — detect via normalized heading match `DEDICATION`; if absent, do not expect v)
   - ACKNOWLEDGEMENTS
   - TABLE OF CONTENTS (first TOC page only for anchor check; multi-page continuation stays with P029)
   - LIST OF TABLES (first LoT page)
5. Compute expected integer from: anchor iv at bio sketch + optional dedication offset + section order. Flag `roman_section_wrong_value` when candidate value ≠ expected (details: `section_key`, `expected_value`, `actual_value`, `page_number`).
6. Skip pages in `_find_no_number_pages()` (ABSTRACT, APPROVAL PAGE) and pages without a confident Roman candidate (no guess from missing numerals).
7. If Biographical Sketch heading is not detected, emit **no** P037 findings (conservative — do not infer anchor).
8. Privacy-safe findings only — no section body text, author names, or dedication prose.

### Scope excluded

- Relative repeat/decrease/gap checks already covered by **P029** (P037 must not re-emit the same conditions).
- Roman vs Arabic regime (**P028**), global candidate detection (**P013**), no-number pages (**P022**).
- Body Arabic numbering, appendix numbering, LoF continuation beyond first-page anchor (defer LoF anchor to v2 unless trivial reuse of LoT pattern).
- Biographical Sketch content rules Q023–Q030, dedication centering/italic Q033–Q034.
- Exact heading phrase layout Q013/Q021/Q036/Q047/Q061/Q070 (**P014** territory).
- Requiring visible numerals on pages that legitimately omit them.

### Expected module path

`src/njit_auditor/rules/pdf_roman_section_anchors.py`

Shared imports from:

- `pdf_page_numbering_regime.py` — `_classify_pages`, `_find_no_number_pages`
- `pdf_page_numbers.py` — `detect_page_number_candidates`
- `pdf_headings.py` — `find_named_frontmatter_headings`, `normalize_heading_text`
- `pdf_roman_sequence.py` — reuse `_MAX_PLAUSIBLE_FRONTMATTER_ROMAN` constant (import or duplicate with comment)

### Expected CLI / report / evaluation wiring

| Surface | Change |
|---------|--------|
| `src/njit_auditor/cli.py` | Call `check_pdf_roman_section_anchors()` after P029 in the page-numbering block |
| `data/processed/rules/project_added_rules.json` | Add **P037** entry (`implementation_status: implemented` only after code lands) |
| `src/njit_auditor/evaluation.py` | Map P037 → `page_numbering` category (same as P028/P029) |
| Reports | Standard `AuditFinding` details; no new triage rollup in v1 |

### Expected tests

| Test | Expectation |
|------|-------------|
| Bio sketch page with Roman iv | No P037 finding |
| Bio sketch page with Roman v (prev pages unnumbered) | `roman_bio_sketch_not_iv` |
| Globally offset sequence v,vi,vii with bio=v | P029 may pass; P037 fails bio anchor |
| Optional dedication absent; ack at vi after bio iv | Pass if ack shows vi (v skipped in template) |
| Dedication present; wrong numeral at dedication | `roman_section_wrong_value` with `section_key=dedication` |
| Bio sketch heading not detected | No P037 findings |
| Body chapter page with Roman candidate | No P037 finding (front matter only) |
| Finding details | No private prose; section_key + numeric metadata only |

Add `tests/test_rule_inventory.py` count bump to **37** when implemented.

### Privacy constraints

- Do not quote dissertation body text, dedication prose, biographical content, or heading-adjacent private text in findings or committed evaluation docs.
- Report only: page number, `section_key`, `issue_type`, Roman token text (numeral only), expected/actual integer values, confidence.
- Local evaluation docs: aggregate P037 counts only.

### Acceptance criteria

1. P037 flags bio sketch ≠ iv on synthetic fixture when heading and candidate are present.
2. P037 validates sequential section anchors with optional dedication skipped.
3. P037 does **not** duplicate P029 issue types on the same (page, condition).
4. P037 emits nothing when Biographical Sketch heading is absent.
5. CLI runs P037 on `njit-audit pdf` without changing P001–P036 behavior.
6. All existing tests pass; new P037 tests added.
7. `project_added_rules.json` lists P037 with correct module path (implementation PR).

### Known false-positive risks

- Wrong section page attributed when heading appears on a continued page (reuse near-top heuristic from P014).
- Optional dedication present but heading not detected → wrong expected offset for acknowledgements.
- Multiple Roman candidates on one page (footer vs header noise) — pick conservative bottom/footer candidate consistent with P013.
- Compressed PDFs with mis-extracted numerals.
- Templates with extra unnumbered interstitial pages not in `_find_no_number_pages` set.

Mitigation: require heading detection + single best candidate per page; skip when ambiguous; low confidence for optional-section paths.

### Local evaluation rerun (not committed)

After implementation, rerun five-PDF audit locally into gitignored
`data/evaluation/generated/current_auditor_after_p037/` and add
`docs/evaluation/p037_current_dataset_evaluation.md` with aggregate P037 counts only.

Do **not** commit generated JSON/MD. Do **not** update `generated_for_commit` or the pre-P037 canonical **1,446** aggregate until a documented full P001–P037 rerun.

---

## Implementation plan (next task)

1. Add `pdf_roman_section_anchors.py` with anchor map, optional dedication handling, and section-first-page candidate lookup.
2. Wire CLI + `project_added_rules.json` + `evaluation.py` category map.
3. Add synthetic tests in `tests/test_pdf_rules.py`; update `tests/test_rule_inventory.py` to 37 rules.
4. Run full validation (`ruff`, `mypy`, `pytest`).
5. Optional: local four/five-PDF evaluation doc (aggregate only, gitignored outputs).

No changes to P001–P036 detector behavior in the scoping PR.

---

## Validation plan

| Step | Command |
|------|---------|
| Inventory (post-impl) | `python -m pytest tests/test_rule_inventory.py -q` |
| P037 synthetics | `python -m pytest tests/test_pdf_rules.py -k p037 -q` |
| Full suite | `ruff check .`, `mypy src`, `python -m pytest` |

Scoping PR (this document): `python -m pytest tests/test_rule_inventory.py -q` minimum.

---

## Privacy notes

- Design and evaluation docs must remain aggregate and metadata-only.
- Test fixtures use synthetic placeholder headings and Roman tokens, not real dissertation content.

## Generated-output safety

- Outputs under `data/evaluation/generated/` stay gitignored.
- Do not commit audit JSON, per-PDF reports, or regenerated full-triage bundles from local runs.
