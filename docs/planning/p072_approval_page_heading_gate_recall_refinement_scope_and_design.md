# P072 — Approval Page Heading-Gate Recall Refinement: Scope and Design

## 1. Metadata

| Field | Value |
|---|---|
| **P-rule** | P072 |
| **Rule name** | Approval Page Heading-Gate Recall Refinement |
| **Date** | 2026-06-08 |
| **Baseline commit** | `0762cd6` (PR #260 — repository polish after P071) |
| **Status** | **Scoped only** — not implemented |
| **Validation baseline** | 1000 pytest (`ruff check .`, `mypy src`, 87 source files) |
| **Type** | **Shared infrastructure / localization recall refinement** (companion to P068) |
| **Companion module** | `src/njit_auditor/rules/pdf_approval_page_committee_blocks.py` (P068) |
| **Expected issue types in v1** | **None new** — P068 issue types only when structural checks reach the page |

### State at time of scoping

| Field | Value |
|---|---|
| Highest implemented P-rule | **P071** |
| Implemented P-rule count | **71** (`P001`–`P071`) |
| Canonical aggregate | **1,543** (post-P070; P071 infrastructure-only; unchanged) |
| Current EF overlap | `docs/evaluation/ef_overlap_after_p071_evaluation.md` |
| `committee_approval_page` EF gap | **5 EF comments, 0 tool findings** on comparison PDFs |
| APPROVAL PAGE gate reach | 2/5 PDFs (3/5 skipped at heading gate) |
| Comparison PDF gate reach | 0/2 (Cibaku and Yin Haotian 2nd Review both skip) |
| pytest count | **1000** |

---

## 2. Motivation

P068 (`pdf_approval_page_committee_blocks.py`) checks structural quality of the Approval Page
committee block. It exists and fires correctly on 2 of 5 evaluation PDFs. However:

- The comparison PDFs used for EF overlap (Cibaku Elson 1st Review, Yin Haotian 2nd Review)
  still have **0 tool findings** on `committee_approval_page`, because P068 skips when
  `find_gate_matches_for_heading(doc, "APPROVAL PAGE")` returns 0 matches.
- The EF reviewer flagged **5 `committee_approval_page` annotations** on those files.
- **P069** improved general front-matter heading gate recall (adding the `ACKNOWLEDGMENTS`
  variant), but did NOT add new APPROVAL PAGE matches on the comparison PDFs. P069 evaluation
  confirmed: "remaining skips are not variant-map recoverable in v1" and "image-only or
  non-variant heading text layers remain the limiting factor."
- **P071** resolved the references localization gap but left the approval-page gap unchanged.

The `committee_approval_page` gap (5 EF, 0 tool) is now the **largest remaining EF gap**
addressable by localization/structural recall — if the page is machine-readable.

### Why P072 now?

P072 mirrors the successful pattern of P069 (heading variant recall) and P071 (structural
fallback when forward localization fails). It is the natural next infrastructure companion
to P068, and the strongest EF-backed automatable gap after the post-P071 polish.

---

## 3. Guideline and Q-Rule Basis

Source materials inspected from the repository only
(`data/processed/rules/njit_rule_inventory.json`, `data/raw/guidelines/`):

| Q-rule | Paraphrased requirement | Classification for P072 |
|---|---|---|
| Q013 | Approval Page displays the exact phrase "APPROVAL PAGE" in all caps, bold, centered, near top | **Recall refinement** — heading detection is partially covered (P014, P038, P068 gate); P072 adds structural fallback when heading text is absent from the text layer |
| Q014 | Approval Page has no visible page number | **Already covered** — P022 handles no-number pages |
| Q015 | Every committee entry begins with an honorific (Dr., Mr., Ms.) | **Manual-only** — requires human name/honorific knowledge; not in P072 scope |
| Q016 | Dissertation Advisor entries appear before non-advisor entries | **Manual-only** — requires semantic role ordering; not in P072 scope |
| Q017 | Committee members listed in descending rank order | **Manual-only** — requires external rank knowledge; not in P072 scope |
| Q018 | Same-rank members alphabetized by surname | **Manual-only** — requires external rank and name knowledge; not in P072 scope |
| Q019 | External/non-NJIT entries appear after all NJIT entries | **Manual-only** — requires affiliation knowledge; not in P072 scope |
| Q020 | Every external entry includes institution name, city, and state | **Manual-only** — requires content reading; not in P072 scope |

**P072 v1 basis:** Q013 structural reach only. Q015–Q020 remain manual-only as documented in P068.

---

## 4. Candidate Analysis

### Option 1 — Approval-page heading-gate variant expansion

**Approach:** Add curated approval-page heading variants to
`FRONTMATTER_HEADING_VARIANTS` in `pdf_frontmatter_heading_gate.py`, analogous to
`"ACKNOWLEDGMENTS"` → `"ACKNOWLEDGEMENTS"` added by P069.

**Potential variants:**
- `"APPROVAL PAGE"` (exact) — already in `GATE_CANONICAL_HEADINGS`; already handled
- `"APPROVAL PAGE:"` (with colon) — already handled by `TRAILING_PUNCT_RE` stripping
- `"Approval Page"` (mixed case) — already handled by `.upper()` normalization in resolver
- `"APPROVALPAGE"` (run-together, text-extraction artifact) → could add if confirmed
- `"COMMITTEE APPROVAL PAGE"` → not standard NJIT format; high FP risk; defer

**Assessment:** Most safe typographic variants are already handled by the existing resolver
(case normalization, trailing-punctuation stripping). The only realistic benefit is run-together
text artifacts. Adding those requires confirmation from real data (not available without
inspecting private PDFs). Low expected gain; do not pursue as primary v1 approach.

| Metric | Assessment |
|---|---|
| Guideline basis | Q013 (partial) |
| EF motivation | Could help if heading text exists but is malformed |
| Automatable | Yes |
| Privacy risk | Low |
| False-positive risk | Low |
| Implementation complexity | Low |
| P072 v1 recommendation | Include as minor addition if safe variants are confirmed; not primary |

---

### Option 2 — Structural approval-page localization fallback (selected)

**Approach:** If no `"APPROVAL PAGE"` gate match is found in the document, scan
front-matter/ambiguous pages for the distinctive combination of role-label phrases and
structural indicators that uniquely identify an approval page. If exactly one such page is
found with sufficient confidence, pass it to the P068 structural checker.

This mirrors the P071 tail-fallback pattern: P071 adds a tail-scan for references when the
forward scan fails. P072 adds a structural-pattern scan for the approval page when the heading
gate fails.

**Detection signal:** The combination of role-label phrases (e.g., "Dissertation Advisor",
"Committee Member") and structural indicators (date labels, signature blanks, underscore lines)
is highly specific to the NJIT approval page format. Body prose mentioning "committee" is
rejected by the existing `_mostly_single_token_noise` and multi-word role-label gates.

**Fallback conditions (all must hold):**
1. `find_gate_matches_for_heading(doc, "APPROVAL PAGE")` returns 0 matches
2. The candidate page is in a front-matter or ambiguous region
3. The candidate page has ≥`_MIN_BODY_LINES` usable lines (not image-only/sparse)
4. The candidate page has ≥`_MIN_ROLE_LABELS` role-label phrase matches
5. Exactly 1 page passes all conditions (skip if 0 or ≥2 candidates — ambiguous)

**Skip conditions:**
- Explicit heading already found → use existing P068 path unchanged
- Image-only page (empty `text_blocks`) → skip
- Sparse text layer (< `_MIN_BODY_LINES` usable lines) → skip
- Zero or below-gate role-label phrases → skip
- Multiple candidate pages → skip (too ambiguous without heading to disambiguate)
- Page is classified as "body" by `_classify_pages()` → skip

| Metric | Assessment |
|---|---|
| Guideline basis | Q013 (structural reach) |
| EF motivation | Direct: 5 EF `committee_approval_page`, 0 tool on comparison PDFs |
| Automatable | Yes (when text is machine-readable) |
| Privacy risk | Low — role-label phrases and structural counts only; no names, signatures, or content |
| False-positive risk | Low-medium — role labels + indicators are distinctive; skip gates reduce FP |
| Implementation complexity | Low-medium — new fallback function; wires into existing P068 logic |
| P072 v1 recommendation | **Selected** |

**Honest limitation:** If the comparison PDFs' approval pages are truly image-only (no text
layer at all), the structural fallback will also find nothing — the fallback requires at least
enough text to match role-label phrases. No approach without OCR can recover fully image-only
pages.

---

### Option 3 — Approval-page v2 new issue types

**Assessment:** Not justified in P072 v1. The existing P068 issue types
(`approval_page_advisor_role_label_missing`, `approval_page_signature_blocks_sparse`) are
appropriate for any structurally detected approval page. New issue types addressing Q015–Q020
(honorific, rank ordering, NJIT/external ordering) are manual-only and not in scope.
Defer indefinitely.

---

### Option 4 — Data/evaluation expansion instead of P072

**Assessment:** Valuable parallel track, not a substitute. Expanding the comparison PDF set
(e.g., acquiring Sebastian Fine EF archive PDF) would improve metric stability and reveal
whether the approval-page gap is universal. However, data acquisition is not a P-rule
implementation. P072 should proceed regardless; data expansion is recommended after P072.

---

## 5. P072 v1 Scope

**P072 is infrastructure-only.** It improves P068's approval-page localization reach without
adding new issue types or changing existing P068 structural-check behavior.

### What P072 does

1. Adds a **structural approval-page localization fallback** in
   `pdf_approval_page_committee_blocks.py` (or extracted to a shared helper in
   `pdf_frontmatter_heading_gate.py`).
2. The fallback activates **only** when the heading gate returns 0 matches.
3. When the fallback finds exactly 1 candidate page, it is treated as the inferred approval
   page and passed to the existing P068 structural-check logic (`_usable_body_lines`,
   `_is_role_label_line`, `_advisor_role_present`, date/signature indicators, finding emission).
4. Optionally adds `"detected_via": "structural_fallback"` to finding `details` for
   diagnostics (aggregate-only, no private text).
5. Minor: adds any safe run-together heading variants to `FRONTMATTER_HEADING_VARIANTS` if
   confirmed on real data.

### What P072 does NOT do

- No new standalone issue types
- No OCR or image-based detection
- No fuzzy typo matching beyond curated variants
- No reading, quoting, or emitting committee-member names, honorifics, affiliations,
  signatures, dates, title text, or approval-page prose
- No semantic Q015–Q020 ordering/completeness checks
- No change to any rule other than P068's page-localization step

### Affected module(s)

Primary: `src/njit_auditor/rules/pdf_approval_page_committee_blocks.py`

Optional helper extraction: `src/njit_auditor/rules/pdf_frontmatter_heading_gate.py`
(if the structural fallback is general enough to reuse for other front-matter sections)

---

## 6. Issue Types

**None new.** P072 is infrastructure-only. All findings emitted after a successful fallback
detection use existing P068 issue types:
- `approval_page_advisor_role_label_missing`
- `approval_page_signature_blocks_sparse`

If `"detected_via": "structural_fallback"` is added to finding `details`, it is a
boolean/keyword field — no private text.

---

## 7. Finding and Output Fields

No change to existing P068 finding fields. All fields are numeric, boolean, or enumerated:

| Field | Type | Notes |
|---|---|---|
| `page_number` | str (int) | Page number of detected approval-page region |
| `issue_type` | str | Existing P068 issue types only |
| `role_label_count` | str (int) | Count of role-label phrases detected |
| `advisor_label_present` | str (bool) | Whether advisor role phrase found |
| `date_label_count` | str (int) | Count of date-label indicators |
| `signature_label_count` | str (int) | Count of signature-label indicators |
| `signature_blank_count` | str (int) | Count of underscore-blank structural lines |
| `signature_date_indicator_count` | str (int) | Sum of structural indicators |
| `confidence` | str | "high" / "medium" / "low" |
| `triage_tier` | str | "medium" |
| `source_q_rule_ids` | str | "Q013" |
| `detected_via` | str (optional) | "heading_gate" or "structural_fallback" |

**No names, signatures, dates, honorifics, affiliations, committee text, or private content
appear in any field.**

---

## 8. Conservative Skip Conditions

| Condition | Behavior |
|---|---|
| Explicit "APPROVAL PAGE" heading found (≥1 gate match) | Use existing heading-gate path; fallback does not activate |
| Image-only page (empty `text_blocks`) | Skip silently |
| Sparse text layer (< `_MIN_BODY_LINES = 4` usable lines) | Skip silently |
| No role-label phrases detected (< `_MIN_ROLE_LABELS = 2`) | Skip silently |
| Multiple structural candidate pages (≥2 pass conditions) | Skip silently — too ambiguous |
| Page classified as "body" region | Skip silently |
| `_mostly_single_token_noise()` returns True | Skip silently |
| No safe approval-page signal at all | No findings emitted |

---

## 9. False-Positive and False-Negative Risks

### False-positive risks

| Risk | Mitigation |
|---|---|
| Acknowledgements page misidentified (mentions "committee") | Acknowledgements has its own heading and is in a different region; role-label phrase gate is specific to approval-page phrasing |
| Biographical sketch (mentions "committee member" in prose) | `_mostly_single_token_noise()` and min role-label gates reject noisy prose pages |
| Front-matter page with committee names in TOC-style entries | TOC-like entries lack role-label phrase + date/signature indicator pattern |
| Multiple approval-page-like pages (e.g., continuation page) | Multi-candidate skip gate rejects ≥2 candidates |

### False-negative risks

| Risk | Mitigation |
|---|---|
| Truly image-only approval page — no text layer at all | Cannot recover without OCR; documented as known limitation |
| Approval page text layer too sparse to match role labels | Existing P068 skip gates already handle this conservatively |
| Non-standard role labels not in `_ROLE_LABEL_PHRASES` | `_ROLE_LABEL_PHRASES` can be extended conservatively; v1 uses existing P068 set |
| Approval page in unusual document position | `_eligible_page_numbers` already accepts all front-matter/ambiguous pages without page-limit |

---

## 10. Synthetic Test Plan

At least 12 tests in `tests/test_p072_approval_page_heading_gate_recall.py`:

| # | Test description | Expected result |
|---|---|---|
| 1 | Canonical "APPROVAL PAGE" heading present with complete body | No findings — heading path unchanged (P068 regression) |
| 2 | Structural fallback: no heading, role labels + date/signature indicators present, unique page | P068 structural issues emitted if thresholds not met |
| 3 | Structural fallback: "Major Professor" variant accepted as advisor-role label | Advisor label recognized |
| 4 | No heading, role labels present but no structural indicators (below signature gate) | No findings — skip condition |
| 5 | No heading, role labels present on 2 candidate pages (ambiguous) | No findings — multi-candidate skip |
| 6 | Image-only page (empty text_blocks), no heading | No findings — image-only skip |
| 7 | No heading, sparse text layer (< MIN_BODY_LINES) | No findings — sparse skip |
| 8 | No heading, body prose mentioning "committee" but no role-label phrases | No findings — gate not met |
| 9 | TOC-like entry with "Approval Page" text | No findings — standalone-line gate rejects TOC entry |
| 10 | Heading present on page 1, fallback not activated even if structural patterns exist on page 2 | Only heading-path page used (fallback inactive when heading found) |
| 11 | Structural fallback finds page; `detected_via` field is "structural_fallback" | Optional diagnostics field contains no private text |
| 12 | Privacy: finding details contain no names, signatures, dates, or private text from fallback path | No private content in finding.details |
| 13 | P069 heading-gate regression: "ACKNOWLEDGMENTS" variant still resolves (unaffected by P072 changes) | Existing gate unaffected |
| 14 | Single role label (below `_MIN_ROLE_LABELS = 2`) on otherwise structural-looking page | No findings |

**All test PDFs use clearly fake placeholder text only. No real committee names, advisor names,
or dissertation content appear in any test fixture or finding.**

Test fixture path convention: `/tmp/p072_test_{id(doc)}.pdf` (in-memory, deleted after test).

---

## 11. Current-Dataset and EF-Overlap Evaluation Plan

After P072 is implemented, run in order:

### A. Five-PDF gate-reach evaluation

Before/after comparison of P068 reach on the five evaluation PDFs:

| File label | P071-era P068 reach | Expected after P072 | Notes |
|---|---|---|---|
| Cibaku Elson 1st Review | 0 | 0 or 1 | Depends on whether approval page has machine-readable role labels |
| Yin Haotian 2nd Review | 0 | 0 or 1 | Same |
| Yin H 2nd Review (flattened) | 0 | 0 | Likely image-only; structural fallback unlikely to help |
| Yin H 4th Review (compressed) | 1 (via heading) | 1 | Heading already detected; no change |
| Sebastian Fine clean baseline | 1 (via heading) | 1 | Heading already detected; no change |

Report: per-file P068 finding counts (aggregate only); gate-reach before/after; no private text.

Document in: `docs/evaluation/p072_approval_page_heading_gate_recall_current_dataset_evaluation.md`

### B. EF-overlap refresh

If gate reach improves on Cibaku or Yin Haotian, refresh:
`docs/evaluation/ef_overlap_after_p072_evaluation.md`

Metrics to report (aggregate-only):
- EF `committee_approval_page` count: 5 (unchanged — EF annotations are fixed)
- Tool `committee_approval_page` count: before (0) vs after (0 or increased)
- Page overlap count for `committee_approval_page`

If gate reach does NOT improve (approval pages are image-only), the existing
`ef_overlap_after_p071_evaluation.md` remains canonical and no refresh is needed.

### C. Full aggregate re-run

P072 is infrastructure-only. If P068 fires on new pages, the aggregate count will increase.
Confirm against current canonical: 1,543. Document the delta.

If aggregate is unchanged (most likely outcome): no separate
`current_auditor_after_p072_evaluation.md` is needed; note in the current dataset doc.

---

## 12. Implementation Checklist

| Step | Item |
|---|---|
| Code | Add `_find_approval_page_structural_candidate()` to `pdf_approval_page_committee_blocks.py` (or as a helper in `pdf_frontmatter_heading_gate.py`) |
| Code | Update `check_pdf_approval_page_committee_blocks()` to call structural fallback when heading gate returns 0 matches |
| Code | Add optional `detected_via` field to finding details |
| Code | Add any confirmed safe run-together heading variants to `FRONTMATTER_HEADING_VARIANTS` |
| Rules | Add P072 entry to `data/processed/rules/project_added_rules.json` |
| Tests | `tests/test_p072_approval_page_heading_gate_recall.py` (14 tests) |
| Eval doc | `docs/evaluation/p072_approval_page_heading_gate_recall_synthetic_validation.md` |
| Eval doc | `docs/evaluation/p072_approval_page_heading_gate_recall_current_dataset_evaluation.md` |
| Eval doc | `docs/evaluation/ef_overlap_after_p072_evaluation.md` (only if gate reach improves) |
| Status | Update `docs/status/current_project_state_and_next_steps.md` |
| Status | Update `docs/status/full_repository_audit_after_p071.md` (add P072 link/note) |
| Status | Update `README.md` planning index and status tables |
| Status | Update `data/processed/evaluation_data_manifest.json` |
| Validation | `ruff check .`, `mypy src`, `python -m pytest` (expect 1012 passed: 1000 + ~12 P072) |

---

## 13. Recommendation

**P072 is ready for implementation** subject to the limitations documented above.

**What it will improve:** P068 structural checks will now fire on approval pages that have
machine-readable role-label text even when the "APPROVAL PAGE" heading text is absent from the
text layer.

**What it will not fix:** Truly image-only approval pages (no text layer) cannot be detected
without OCR. The comparison PDFs (Cibaku, Yin Haotian 2nd Review) may fall into this category.
If so, the five-PDF aggregate and EF-overlap metrics may remain unchanged, and
`ef_overlap_after_p071_evaluation.md` will remain the canonical EF overlap doc.

**This is still worth doing** because:
- Mirrors the successful P069/P071 pattern of conservative infrastructure recall improvements
- Is the strongest remaining automatable EF-backed gap
- Infrastructure work is low-risk (skip gates prevent false positives)
- Creates a documented, tested fallback path for future data sets where approval pages may be
  more extractable

**Implementation branch:** `rules/p072-approval-page-heading-gate-recall`

**P072 is infrastructure-only in v1.** If structural reach improves and new structural
issues are found on previously unreachable approval pages, the existing P068 issue types
handle them correctly. No new issue types are needed unless Q015–Q020 are later determined
to be partially automatable (currently manual-only).

---

## 14. Cross-References

- P068 scope: `docs/planning/p068_approval_page_committee_block_structural_scope_and_design.md`
- P069 scope: `docs/planning/p069_frontmatter_heading_gate_recall_refinement_scope_and_design.md`
- P071 scope: `docs/planning/p071_references_section_localization_recall_refinement_scope_and_design.md`
- Current EF overlap: `docs/evaluation/ef_overlap_after_p071_evaluation.md`
- P068 implementation: `src/njit_auditor/rules/pdf_approval_page_committee_blocks.py`
- Gate infrastructure: `src/njit_auditor/rules/pdf_frontmatter_heading_gate.py`
- Q-rule inventory: `data/processed/rules/njit_rule_inventory.json` (Q013–Q020)
