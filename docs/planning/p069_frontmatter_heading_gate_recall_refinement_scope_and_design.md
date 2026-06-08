# P069 — Front-Matter Heading Gate Recall Refinement: Scope and Design

## 1. Metadata

| Field | Value |
|---|---|
| **P-rule** | P069 |
| **Rule name** | Front-Matter Heading Gate Recall Refinement |
| **Date** | 2026-06-08 |
| **Baseline commit** | `8766359` (PR #245 — post-P068 aggregate evaluation snapshot) |
| **Status** | **Implemented (v1)** — see `docs/evaluation/p069_frontmatter_heading_gate_recall_synthetic_validation.md` |
| **Validation baseline** | 963 pytest (`ruff check .`, `mypy src`) |
| **Type** | **Shared infrastructure / gate refinement** (not a standalone semantic checker) |
| **Companion rules** | P038 (`pdf_frontmatter_headings.py` — variant reporting), P014 (`pdf_headings.py` — strict style checks), P065–P068 and other front-matter consumers |

---

## 2. Post-P068 Backlog Audit Summary

### Repository state (audit date 2026-06-08)

| Item | Value |
|---|---|
| Branch | `main` (clean working tree at `8766359`) |
| Highest implemented P-rule | **P068** |
| Implemented P-rule count | **68** (`P001`–`P068`) |
| Q-rules in inventory | **79** total |
| Q-rule `implemented` | **2** (Q004, Q005) |
| Q-rule `partially_implemented` | **60** |
| Q-rule `not_implemented` | **17** (manual-only + automatable gaps) |
| Pytest count | **963** |
| Full aggregate snapshot | `docs/evaluation/current_auditor_after_p068_evaluation.md` — **1,590** findings; P068 adds **3** |

### Repeated skip pattern motivating P069

Recent front-matter rules frequently skip on the five-PDF evaluation set because
`find_named_frontmatter_headings()` requires an **exact normalized line match** to
`EXPECTED_HEADINGS`. P038 can report some variant spellings, but downstream structural
rules do not reuse that relaxed resolution.

| Rule / eval | Skip pattern on five-PDF set |
|---|---|
| P065 (DEDICATION) | 5/5 skipped — no standalone `DEDICATION` heading detected |
| P066 (Bio Sketch degrees) | 3/5 skipped — `BIOGRAPHICAL SKETCH` not detected |
| P067 (Bio Sketch publications) | 3/5 skipped at heading gate; 0/5 reached Publications boundary |
| P068 (Approval Page blocks) | 3/5 skipped — `APPROVAL PAGE` not detected |
| P061 (LoT/LoF cross-page) | 3/5 — no LoT/LoF pages detected (separate parser track) |

P068 fired on 2/5 files; the other 3/5 failures align with the shared strict heading gate,
not with missing approval-page content in every case.

### EF-overlap context after P068

| EF category | EF comments (2-file set) | Tool coverage after P068 | Notes |
|---|---:|---|---|
| `committee_approval_page` | 5 | **Partial** — P068 adds structural checks | Residual gaps are semantic (Q015–Q020) |
| `references_citations` | 9 | **Partial** — P064 structural checks | Style semantics remain manual |
| `list_of_tables_figures_toc` | 4 | Sparse on comparison PDFs | Parser recall, not a clean new rule |
| `unclear_or_other` | 88 | N/A | Permanent manual-only gap |

### No existing P069 planning docs

Confirmed before this document: no prior `p069_*` files under `docs/planning/`.

---

## 3. Motivation

After P064–P068, the highest-value **non-semantic** next step is not another narrow
front-matter content rule. It is improving the **shared heading gate** so existing and
future rules can run when front-matter sections are present but use tolerated variants,
continued-heading suffixes, or slightly nonstandard text-layer formatting.

Why P069 is the best next task:

1. **Cross-rule leverage:** P041, P044–P047, P065–P068, P037, and P038 all depend on
   reliable canonical heading resolution.
2. **Evaluation evidence:** 3/5 evaluation PDFs skipped multiple recent rules at the same
   heading-detection gate; post-P068 aggregate still shows `committee_approval_page` only
   on 2/5 files despite EF comments in that category.
3. **Non-duplication:** P038 reports missing headings and a small curated variant map for
   **findings**; P069 improves **gate resolution** used by other rules without replacing
   P038 or P014.
4. **Conservative automation:** No body-text reading, no committee semantics, no citation
   style enforcement.
5. **Privacy-safe:** Canonical heading labels and structural booleans only.

---

## 4. Candidate Comparison (post-P068)

| Candidate | Q/guideline basis | Current coverage | EF / eval motivation | Automatable? | Privacy / FP risk | Decision |
|---|---|---|---|---|---|---|
| **P069 Front-matter heading gate recall** | Q013, Q021, Q031–Q036, Q047, Q061, Q070 | P038/P014 partial; strict gate blocks P065–P068 | 3/5 skip pattern across recent evals | **Yes — infra** | Low privacy; **low–medium FP** if gates stay conservative | **Selected** |
| LoT/LoF/TOC entry extraction recall | Q052–Q079 partials | P018/P030–P062 implemented | 4 EF comments; 130 aggregate findings but sparse on comparison PDFs | Refinement only | Low privacy; parser complexity | Defer as P070+ infra unless recall stays blocked |
| Approval Page v2 (Q016 ordering, sparse blocks advisory) | Q016 partial | P068 v1 | P068 found 3 issues | Partial | Medium FP; ordering semantics risk | Deferred — P068 just landed |
| References/citations v2 (appendix vs references order) | P064 deferred note | P064 v1 | Residual EF style gaps | Weak Q-rule evidence | Medium FP | Deferred |
| Equation numbering/layout | Self-Assessment mention only | None | None | **No confirmed Q-rule** | Unknown | **Rejected** |
| Acknowledgements paragraph semantics (Q039–Q043) | Q039–Q043 | P043 indentation partial | Low EF volume | **No — semantic** | High privacy / FP | Deferred |
| Bio-sketch publication style (Q030) | Q030 | Manual | Low | Style semantic | High FP | Manual-only |
| Shared LoT/LoF page detection only | Q061, Q070 | `detect_toc_like_pages` stricter than heading gate on some PDFs | P061 3/5 no LoT/LoF | Infra | Low | Parallel follow-up after P069 |

---

## 5. Guideline / Q-Rule Basis

### Source files consulted

| File | Relevance |
|---|---|
| `data/processed/rules/njit_rule_inventory.json` | Q013, Q021, Q031–Q036, Q047, Q061, Q070 |
| `data/raw/guidelines/Front Matter Pages Lorem Ipsum.pdf` | Named front-matter section headings (paraphrased only) |
| `data/raw/guidelines/Self-Self Assessment Sheet.pdf` | Front-matter checklist expectations |
| `docs/evaluation/current_auditor_after_p068_evaluation.md` | Post-P068 skip patterns |
| `docs/evaluation/p065_current_dataset_evaluation.md` | DEDICATION gate failures |
| `docs/evaluation/p066_current_dataset_evaluation.md` | BIOGRAPHICAL SKETCH gate failures |
| `docs/evaluation/p068_current_dataset_evaluation.md` | APPROVAL PAGE gate failures |
| `src/njit_auditor/rules/pdf_frontmatter_headings.py` | Existing curated variant map |
| `src/njit_auditor/rules/pdf_toc_alignment.py` | Continued-heading normalization patterns |

### Q-rule classification for P069

| Q-rule | Paraphrased requirement | Classification for P069 |
|---|---|---|
| Q013 | Approval page uses exact `APPROVAL PAGE` heading phrase | **Partial — gate refinement** for canonical resolution |
| Q021 | Bio Sketch uses exact `BIOGRAPHICAL SKETCH` phrase | **Partial — gate refinement** |
| Q031–Q032 | Dedication heading / page cues | **Partial — gate refinement** for `DEDICATION` |
| Q035–Q036 | Acknowledgements heading phrase | **Partial — gate refinement** |
| Q047 | TOC heading phrase | **Already stronger** via `detect_toc_like_pages`; share continued-suffix logic only |
| Q061 | LoT heading phrase | **Indirect** — optional shared normalization helper |
| Q070 | LoF heading phrase | **Indirect** — optional shared normalization helper |
| Q015–Q020 | Committee semantics | **Out of scope** |
| Q039–Q043 | Acknowledgements paragraph intent | **Out of scope** |

---

## 6. P069 v1 Scope

### Included (shared PDF text-layer infrastructure)

1. Add a **canonical heading resolver** used by gate functions (either by extending
   `find_named_frontmatter_headings()` behind a flag or by introducing
   `find_frontmatter_headings_for_gates()` that returns the same `HeadingMatch` shape).
2. **Variant map expansion** (curated only — no arbitrary extracted text in findings):
   - Reuse and extend P038 `_KNOWN_VARIANTS` (e.g., `ACKNOWLEDGMENTS` → `ACKNOWLEDGEMENTS`).
   - Add only variants with confirmed guideline/matrix support or existing P038 precedent.
3. **Continued-heading normalization** for list headings:
   - Strip `(Continued)` / `Continued` suffixes before matching `LIST OF TABLES` /
     `LIST OF FIGURES` (reuse logic from `pdf_toc_alignment._normalize_toc_heading_variant`).
4. **Relaxed standalone-line gate** (detection only, not P014 style enforcement):
   - Candidate line length ≤ configurable max (e.g., 40 chars after normalization).
   - Line must appear in the front-matter page region (reuse `_classify_pages` /
     first-N-pages scan).
   - Reject lines with sentence-like punctuation density or word count above threshold.
5. **Wire gate resolver into consumers** that currently call strict
   `find_named_frontmatter_headings()` for section localization:
   - Minimum v1 consumers: P065, P066, P067, P068, P041, P044, P045, P046, P047.
   - P014 style checks remain on **strict** matches only (do not relax style heuristics).
6. **Regression guarantee:** Rules must preserve existing skip behavior when resolver returns
   the same result as strict matching.

### Excluded

- OCR or image-based heading detection
- Reading heading-adjacent body prose
- Emitting committee names, advisor names, dedication text, or bio-sketch content
- New semantic checks (committee order, acknowledgement paragraph intent, citation style)
- TeX-source heading checks in v1
- Fuzzy / Levenshtein matching on arbitrary headings
- Changing P014 layout/style thresholds
- LoT/LoF **entry** parser rewrite (deferred to a separate refinement track)

### Input type

**PDF text layer only** for v1.

### Standalone issue types

**None in v1.** P069 is infrastructure-first. Increased findings should appear through
dependent rules (for example P066/P067/P068) when gates previously skipped. P038 remains
the rule that emits `required_heading_missing` and `heading_phrase_not_exact`.

---

## 7. Detection / Refinement Algorithm

### Step 1 — Page region filter

```python
from njit_auditor.rules.pdf_page_numbering_regime import _classify_pages
```

- Restrict candidate scan to `front_matter` pages (and optionally the first body page only
  when a section is known to wrap — **out of scope for v1**).

### Step 2 — Line normalization

```python
from njit_auditor.rules.pdf_headings import normalize_heading_text
```

- Normalize whitespace and NBSP.
- Uppercase for comparison.
- Apply continued-suffix stripping for list headings.

### Step 3 — Canonical resolution order

For each candidate line:

1. **Exact match** to `EXPECTED_HEADINGS` → canonical heading.
2. **Curated variant map** hit → canonical heading.
3. Otherwise → not a gate match.

No fuzzy matching beyond the curated map in v1.

### Step 4 — Standalone-line gate

Accept a resolved canonical heading only when:

- normalized line length ≤ `_MAX_GATE_LINE_CHARS` (proposed 40),
- token count ≤ `_MAX_GATE_LINE_TOKENS` (proposed 6),
- line does not end with `.` or `?` (sentence-like prose filter),
- line is not a substring of a longer block line already rejected.

### Step 5 — Consumer integration

- Replace strict-only localization in targeted consumers with gate resolver.
- Keep P038 missing-heading logic unchanged initially; after P069, re-evaluate whether
  P038 should use the same resolver for consistency.

### Confidence scoring (metadata for dependent rules)

Resolver may attach `match_confidence` in internal structs:

| Match path | Confidence |
|---|---|
| Exact normalized match | `high` |
| Curated variant map | `medium` |
| Continued-suffix normalized list heading | `medium` |

Dependent rules may downgrade triage when confidence is `medium`.

---

## 8. Finding / Output Fields

### P069 standalone findings

**None expected in v1.**

### Internal resolver metadata (not exported to web sanitization-sensitive fields)

| Field | Type | Notes |
|---|---|---|
| `canonical_heading` | string | One of `EXPECTED_HEADINGS` |
| `page_number` | int | Page where gate matched |
| `match_path` | string | `exact`, `variant_map`, `continued_suffix` |
| `match_confidence` | string | `high` or `medium` |

### Explicitly excluded from all outputs

- Raw heading line text from real PDFs in findings
- Author names, committee names, department strings
- Dedication / acknowledgement / bio-sketch body text
- EF comment text

---

## 9. Conservative Skip Conditions

| Condition | Action |
|---|---|
| No front-matter region detected | Consumers keep current skip behavior |
| Zero gate matches after resolver | Skip silently (same as today) |
| Multiple matches for a required single-page section | Keep current ambiguous skip rules in consumers |
| Image-only / empty text layer on candidate page | Skip silently |
| Candidate line fails standalone-line gate | Do not promote to canonical match |
| Variant not in curated map | Do not guess; no match |
| Consumer-specific downstream gates fail (e.g., sparse body lines) | Unchanged |

---

## 10. False-Positive and False-Negative Risks

### False positives

- A body sentence that happens to equal a short heading phrase (e.g., a line containing only
  `DEDICATION` in prose context) → mitigated by standalone-line length/token gates and
  front-matter region filter.
- Variant map too broad → mitigated by curated map only; no automatic typo tolerance.
- Dependent rules fire on medium-confidence matches that are not true headings → mitigated by
  consumer-specific downstream gates unchanged.

### False negatives

- Image-rendered headings with no text layer remain undetectable.
- Headings split across lines or heavily styled in ways that break text extraction.
- Department-specific phrases outside the curated map (e.g., `Research Advisor`).

### Operational note

Improved recall may increase findings on the five-PDF set but does **not** prove full
guideline compliance. Evaluation must report before/after **gate pass rates**, not only
finding counts.

---

## 11. Synthetic Test Plan

Minimum **12** tests in `tests/test_p069_frontmatter_heading_gate_recall.py`:

| # | Scenario | Expected |
|---|---|---|
| 1 | Exact `BIOGRAPHICAL SKETCH` line | Resolver returns canonical match (`high`) |
| 2 | `ACKNOWLEDGMENTS` variant line | Maps to `ACKNOWLEDGEMENTS` (`medium`) |
| 3 | `LIST OF TABLES (Continued)` | Maps to `LIST OF TABLES` (`medium`) |
| 4 | Long prose line containing `BIOGRAPHICAL SKETCH` mid-sentence | No gate match |
| 5 | `DEDICATION` embedded in 80-character prose line | No gate match |
| 6 | Exact match on non-front-matter page | No gate match |
| 7 | Image-only page (no text blocks) | No gate match |
| 8 | P068 consumer uses resolver; variant `APPROVAL PAGE` exact still works | Same findings as strict baseline |
| 9 | P066 consumer reaches bio-sketch page via variant map in synthetic doc | Year-ordering check runs |
| 10 | Multiple `APPROVAL PAGE` gate matches | Consumer keeps ambiguous skip |
| 11 | Privacy: resolver returns no raw line text in exported details | Pass |
| 12 | Regression: synthetic doc with strict matches unchanged vs pre-P069 expectations | Dependent rule counts unchanged |

Additional regression tests:

- Run a subset of existing P065/P066/P067/P068 synthetic tests unchanged after wiring.

Synthetic fixtures use placeholder labels only.

---

## 12. Current-Dataset Evaluation Plan

After implementation:

1. **Before/after gate pass table** on five PDFs for headings:
   `APPROVAL PAGE`, `BIOGRAPHICAL SKETCH`, `DEDICATION`, `ACKNOWLEDGEMENTS`.
2. Record per file: strict match (Y/N), gate match (Y/N), match path, dependent rules
   newly reaching downstream checks.
3. Produce `docs/evaluation/p069_frontmatter_heading_gate_recall_evaluation.md` (aggregate only).
4. Optionally refresh full aggregate snapshot if dependent-rule counts change materially.

**Privacy:** No heading line text, names, or body prose in the evaluation doc.

---

## 13. Implementation Checklist

| Item | Path / action |
|---|---|
| Shared resolver | `src/njit_auditor/rules/pdf_headings.py` (extend) or `src/njit_auditor/rules/pdf_frontmatter_heading_gate.py` (new helper module) |
| Public entry | `find_frontmatter_headings_for_gates(pdf_document) -> list[HeadingMatch]` |
| Variant map | Shared constant imported by P038 and P069 resolver |
| Wire consumers | P041, P044, P045, P046, P047, P065, P066, P067, P068 (gate localization only) |
| P069 inventory stub | `data/processed/rules/project_added_rules.json` — `implementation_status: implemented`, type `infrastructure_refinement` |
| Evaluation mapping | `src/njit_auditor/evaluation.py` — optional `"P069": "frontmatter_structure"` or omit if zero standalone findings |
| Tests | `tests/test_p069_frontmatter_heading_gate_recall.py` (≥12) + targeted regressions |
| Synthetic validation doc | `docs/evaluation/p069_frontmatter_heading_gate_recall_synthetic_validation.md` |
| Current-dataset eval doc | `docs/evaluation/p069_frontmatter_heading_gate_recall_evaluation.md` |
| Status refresh | `docs/status/current_project_state_and_next_steps.md` |
| Validation | `ruff check .`, `mypy src`, `python -m pytest` |

---

## 14. Recommendation

**Implemented (2026-06-08):** `src/njit_auditor/rules/pdf_frontmatter_heading_gate.py`; wired into
P041, P044–P047, P065–P068, and TOC/list detection. Synthetic validation and five-PDF
current-dataset evaluation docs added. No standalone P069 findings in v1.

Suggested implementation PR:

- Branch: `rules/p069-frontmatter-heading-gate-recall`
- Title: `Implement P069 front-matter heading gate recall refinement`
- Scope guard: shared resolver + consumer gate wiring only; no new standalone issue types;
  no Q015–Q020 or Q039–Q043 semantics.

### Caveats

- Gate recall improvements will not fix image-only headings; OCR remains out of scope.
- LoT/LoF entry extraction and cross-page ordering rules may still skip when list **pages**
  are detected but entries are not parseable — that is a separate follow-up track.
- Medium-confidence variant matches must remain subject to each consumer's downstream gates to
  avoid noisy findings.
