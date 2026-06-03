# P038 Scope and Design

- **Date:** 2026-06-02
- **Status:** **Implemented** — `src/njit_auditor/rules/pdf_frontmatter_headings.py`
- **Baseline main:** `d0f6175` (P001–P037 implemented; P038 scoped PR #95)
- **Implementation PR:** rules/p038-frontmatter-heading-phrases

## Current state

| Area | State |
|------|--------|
| P-rules | **37/37** implemented (`P001`–`P037`) |
| Q-rules (raw inventory) | **79** total — **2** implemented, **11** partially_implemented, **66** not_implemented |
| Front-matter heading cluster | **P014** — style checks (bold/centered/all-caps/near-top) when heading text matches exactly; **no** missing-section or phrase-mismatch detection |
| Front-matter structure cluster | **P025** — abstract body, title-page elements, approval-page content; does not check heading phrases |
| Page-numbering cluster | **P013**, **P019**, **P022**, **P028**, **P029**, **P037** — complete for v1 |
| Reusable helpers | `find_named_frontmatter_headings`, `normalize_heading_text`, `_NAMED_HEADINGS` |

**P014 vs remaining heading gap:** P014 detects headings whose normalized text exactly matches an expected phrase and checks their layout/style. It does **not** flag headings that are missing entirely or present with a variant spelling (e.g., "ACKNOWLEDGMENTS" instead of "ACKNOWLEDGEMENTS"). Q013, Q021, Q036, Q047, Q061, Q070 ask about exact phrase presence, which P014 only partially covers.

---

## Candidate comparison

### Candidate A — Front-matter exact heading phrase / missing-section detection (recommended)

| Field | Detail |
|-------|--------|
| **Source basis** | Q013 (APPROVAL PAGE exact phrase), Q021 (BIOGRAPHICAL SKETCH exact phrase), Q036 (ACKNOWLEDGEMENTS exact phrase), Q047 (TABLE OF CONTENTS heading), Q061 (LIST OF TABLES heading), Q070 (LIST OF FIGURES heading) |
| **Proposed rule** | **P038** — PDF front-matter exact heading phrase and missing-section checks |
| **Module** | `src/njit_auditor/rules/pdf_frontmatter_headings.py` |
| **Issue types** | `required_heading_missing`, `heading_phrase_not_exact` |
| **Risk / noise** | **Medium** — optional sections (DEDICATION, LIST OF FIGURES without figures) must not be flagged as missing; flattened/image-only PDFs may miss detections; spelling variants must be handled carefully |
| **Privacy** | **Low** — heading text is metadata; no body prose, author names, or private content in findings |
| **Tests** | Synthetic front matter with: (a) all correct headings; (b) missing BIOGRAPHICAL SKETCH; (c) "ACKNOWLEDGMENTS" instead of "ACKNOWLEDGEMENTS"; (d) "LIST OF FIGURE" (typo); (e) optional DEDICATION absent → no finding; (f) optional LIST OF FIGURES absent → no finding |
| **Five-PDF impact** | **Low–moderate** — depends on PDFs; most well-formed theses should show 0 findings; theses with variant spellings will show findings |
| **Why P038?** | Direct coverage of 6 Q-rules; builds on P014 infrastructure; low privacy risk; clear incremental value; recommended in post-P037 next-steps |

### Candidate B — Dedication page centering and italic (Q033–Q034)

| Field | Detail |
|-------|--------|
| **Source basis** | Q033 (dedication text centered), Q034 (dedication text italic if Latin alphabet) |
| **Risk / noise** | **High** — italic metadata often absent in PDFs; DEDICATION heading detection unreliable; section is optional |
| **Privacy** | **Medium** — dedication prose must not appear in findings |
| **Why not P038?** | Narrow optional section; weak PDF text-layer italic signals; high FP/FN rate; low incremental value relative to risk |

### Candidate C — P035 image-block body layout refinement

| Field | Detail |
|-------|--------|
| **Source basis** | P035 v1 skips image-only floats; improvement would use PyMuPDF image bbox extraction |
| **Risk / noise** | **Medium** — infrastructure change to `pdf_layout.py`; not a new Q-rule cluster |
| **Privacy** | **Low** |
| **Why not P038?** | Refinement of existing P035; no new Q-rule coverage; requires non-trivial infra changes; better addressed in a P035 v2 refinement pass |

### Candidate D — Biographical Sketch content/layout subset (Q023–Q030)

| Field | Detail |
|-------|--------|
| **Source basis** | Q023–Q030 (birth info excluded, degree ordering, publication formatting, hanging indents) |
| **Risk / noise** | **Very high** — semantic content parsing; degree ordering requires understanding of degree types; publication formatting highly variable |
| **Privacy** | **High** — biographical content is private; findings must never quote bio prose |
| **Why not P038?** | Unsuitable for heuristic v1; remains in manual-only category until semantic AI is used |

### Candidate E — Bibliography / reference formatting

| Field | Detail |
|-------|--------|
| **Source basis** | No specific Q-rule in current `njit_rule_inventory.json` for bibliography format; `thesis-compliance` reference has hanging-indent checks |
| **Risk / noise** | **High** — bibliography detection is heuristic; NJIT guidelines specifics unclear from current inventory |
| **Privacy** | **Medium** — reference text is generally academic metadata but can include author names |
| **Why not P038?** | No documented NJIT Q-rule basis in current inventory; reference formatting requires scoping a new Q-rule cluster before implementing |

### Candidate F — Canonical P001–P037 evaluation rerun

| Field | Detail |
|-------|--------|
| **Source basis** | Evaluation/manifest maintenance |
| **Why not P038?** | Evaluation PDFs unavailable in workspace; not an implementation rule; defer until PDFs available locally |

### Ranking

1. **A — Front-matter exact heading phrase / missing-section** (recommended P038)
2. **C — P035 image-block refinement** (incremental; better deferred)
3. **B — Dedication centering/italic** (optional section; high FP rate)
4. **E — Bibliography formatting** (no Q-rule basis yet)
5. **D — Bio-sketch content** (unsuitable for automation v1)
6. **F — Canonical rerun** (evaluation-only; defer)

---

## Selected P038 scope

### Rule title

**P038 — PDF front-matter exact heading phrase and missing-section checks**

### Source basis

- Q013 — "APPROVAL PAGE" exact phrase (all caps, matches exactly)
- Q021 — "BIOGRAPHICAL SKETCH" exact phrase
- Q036 — "ACKNOWLEDGEMENTS" exact phrase (common variant: "ACKNOWLEDGMENTS")
- Q047 — "TABLE OF CONTENTS" heading correct
- Q061 — "LIST OF TABLES" heading correct
- Q070 — "LIST OF FIGURES" heading correct
- Complements **P014** (which checks style of correctly-matched headings); does **not** replace it

### Scope included

1. **Required heading presence:** For each required heading in the NJIT template, confirm at least one front-matter page contains it. Required: APPROVAL PAGE, BIOGRAPHICAL SKETCH, ACKNOWLEDGEMENTS, TABLE OF CONTENTS. Emit `required_heading_missing` if not detected anywhere in the front-matter region.
2. **Heading phrase exact match:** Scan front-matter top-zone lines for lines that normalize to a near-match of an expected heading but do not exactly match the canonical phrase. Known variants to detect:
   - "ACKNOWLEDGMENTS" (American spelling) when canonical is "ACKNOWLEDGEMENTS"
   - Case-fold variants: "Biographical Sketch" when canonical is "BIOGRAPHICAL SKETCH"
   - Truncations or typos within reasonable edit distance (heuristic, conservative)
   - Emit `heading_phrase_not_exact` with `canonical_phrase` and `observed_phrase` in details (no body text).
3. **Optional section handling:** DEDICATION, LIST OF TABLES, LIST OF FIGURES — emit `required_heading_missing` only if these are in the document's structure context (e.g., LIST OF TABLES is required when there are numbered tables; conservative: skip if no LOT/LOF candidate pages detected). Do not flag DEDICATION as missing.
4. Restrict checks to pages classified as `front_matter` via `_classify_pages()`.
5. Privacy-safe findings: heading canonical text and observed text only; no section body content, author names, or private prose.

### Scope excluded

- Heading style checks (bold/centered/all-caps/near-top) — owned by **P014**.
- Front-matter structural order (Abstract before TOC) — owned by **P025**.
- Abstract body presence, title-page degree/institution — owned by **P025**.
- Body chapter headings (CHAPTER N, APPENDIX) — out of scope.
- Dedication centering/italic — high FP risk; deferred (Candidate B).
- Bio-sketch content rules Q023–Q030 — manual-only.
- Bibliography format — no Q-rule basis yet.
- Image-only/flattened PDFs: skip conservatively when heading text layer is absent.

### Expected module path

`src/njit_auditor/rules/pdf_frontmatter_headings.py`

Shared imports from:

- `pdf_page_numbering_regime.py` — `_classify_pages`
- `pdf_headings.py` — `find_named_frontmatter_headings`, `normalize_heading_text`, `EXPECTED_HEADINGS`

### Expected CLI / report / evaluation wiring

| Surface | Change |
|---------|--------|
| `src/njit_auditor/cli.py` | Call `check_pdf_frontmatter_headings()` after P014 in the front-matter block |
| `data/processed/rules/project_added_rules.json` | Add **P038** entry (`implementation_status: implemented` only after code lands) |
| `src/njit_auditor/evaluation.py` | Map P038 → `heading_title` category (same as P014) |
| Reports | Standard `AuditFinding` details; no new triage rollup in v1 |

### Expected tests

| Test | Expectation |
|------|-------------|
| All canonical headings present and correct | No P038 finding |
| BIOGRAPHICAL SKETCH missing | `required_heading_missing` with `section_key=biographical_sketch` |
| "ACKNOWLEDGMENTS" (American) instead of "ACKNOWLEDGEMENTS" | `heading_phrase_not_exact` |
| "Biographical Sketch" (title case, not all caps) | `heading_phrase_not_exact` (distinct from P014 which checks style of detected matches) |
| DEDICATION absent | No P038 finding (optional) |
| LIST OF FIGURES absent (no LOF candidate pages) | No P038 finding (optional) |
| Finding details privacy-safe | No body text, author names, or private prose in details |
| CLI integration | P038 present in JSON output when triggered |

Update `tests/test_rule_inventory.py` count to **38** when implemented.

### Privacy constraints

- `heading_phrase_not_exact` findings include `canonical_phrase` (expected heading text) and `observed_phrase` (detected near-match) — neither contains body content.
- `required_heading_missing` findings include `section_key` and `page_region` only — no body text.
- Do not quote dissertation body text, biographical prose, dedication text, acknowledgements prose, or any section body content in findings or evaluation docs.

### Acceptance criteria

1. P038 flags `required_heading_missing` for required headings absent in synthetic front matter.
2. P038 flags `heading_phrase_not_exact` for "ACKNOWLEDGMENTS" when "ACKNOWLEDGEMENTS" is canonical.
3. P038 does not flag missing DEDICATION (optional section).
4. P038 does not flag missing LIST OF FIGURES when no LOF-candidate pages are detected.
5. P038 does not duplicate P014 issue types.
6. CLI runs P038 on `njit-audit pdf` without changing P001–P037 behavior.
7. All existing tests pass; new P038 tests added.
8. `project_added_rules.json` lists P038 with correct module path (implementation PR).

### Known false-positive risks

- Flattened/image-only front-matter pages: heading text not in text layer → `required_heading_missing` fires on every required section even when headings are visually present.
  - Mitigation: check that at least one heading from `EXPECTED_HEADINGS` is detected before running required-heading checks; if no headings at all are detected, emit nothing (conservative gate).
- Near-match scan may flag legitimate alternate phrases used by NJIT variants.
  - Mitigation: use a small hand-curated variant list rather than edit-distance search; err on the side of not flagging.
- Optional sections (LIST OF TABLES/FIGURES): not all theses have tables or figures.
  - Mitigation: require LOT/LOF candidate page detection before flagging as missing.

### Local evaluation rerun (not committed)

After implementation, rerun five-PDF audit locally into gitignored
`data/evaluation/generated/current_auditor_after_p038/` and add
`docs/evaluation/p038_current_dataset_evaluation.md` with aggregate P038 counts only.

Do **not** commit generated JSON/MD. Do **not** update `generated_for_commit` or the pre-P037 canonical **1,446** aggregate until a documented full P001–P038 rerun.

---

## Implementation plan (next task)

1. Add `pdf_frontmatter_headings.py` with:
   - Required-heading gate (skip if no headings detected at all)
   - `required_heading_missing` check for required headings
   - `heading_phrase_not_exact` check using curated variant list
   - Optional-section skip logic for DEDICATION, LIST OF TABLES, LIST OF FIGURES
2. Wire CLI + `project_added_rules.json` + `evaluation.py` category map.
3. Add synthetic tests; update `tests/test_rule_inventory.py` to 38 rules.
4. Run full validation (`ruff`, `mypy`, `pytest`).
5. Optional: local evaluation doc (aggregate only, gitignored outputs).

No changes to P001–P037 detector behavior in the scoping PR.

---

## Validation plan

| Step | Command |
|------|---------|
| Inventory (post-impl) | `python -m pytest tests/test_rule_inventory.py -q` |
| P038 synthetics | `python -m pytest tests/test_pdf_rules.py -k p038 -q` |
| Full suite | `ruff check .`, `mypy src`, `python -m pytest` |

Scoping PR (this document): `python -m pytest tests/test_rule_inventory.py -q` minimum.

---

## Privacy notes

- Design and evaluation docs must remain aggregate and metadata-only.
- Test fixtures use synthetic placeholder heading text, not real dissertation content.
- `heading_phrase_not_exact` findings report canonical and observed heading phrases only — heading text is public metadata, not private content.
- `required_heading_missing` findings report `section_key` only — no body text.

## Generated-output safety

- Outputs under `data/evaluation/generated/` stay gitignored.
- Do not commit audit JSON, per-PDF reports, or regenerated full-triage bundles from local runs.
