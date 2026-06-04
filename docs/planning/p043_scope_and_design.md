# P043 Scope and Design

- **Date:** 2026-06-03
- **Status:** **Implemented** (PR #116 — P001–P043 implemented; see `docs/evaluation/p043_current_dataset_evaluation.md`)
- **Baseline main:** `70b37bc` (PR #116 — P043 Acknowledgements paragraph indentation; P001–P043 implemented)

---

## Current state

| Area | State |
|------|--------|
| P-rules | **43/43** implemented (`P001`–`P043`) |
| Q-rules (raw inventory) | **79** total — **2** implemented, **11** partially_implemented, **66** not_implemented |
| General paragraph indentation | **P015** — covers ALL pages including Acknowledgements; conservative thresholds (`MIN_LINES_FOR_MISSING_LATER_INDENT=4`, `MIN_LIKELY_INDENTED_PARAGRAPHS_FOR_PAGE_STYLE=2`, `MIN_INDENT_STYLE_CONFIDENCE_RATIO=0.6`); Q044/Q045 now partially_implemented via P043 |
| Acknowledgements-specific indentation | **Implemented as P043** — `src/njit_auditor/rules/pdf_acknowledgements_indentation.py`; Q044/Q045 addressed |
| Dedication page header | **P041** — Q032; top-margin check |
| TOC appendix format | **P042** — Q058/Q059; letter-identifier check |

**Gap vs P015:** P015 emits findings only when ≥4 lines per paragraph AND ≥2 indented paragraphs are found with ≥60% confidence. A short Acknowledgements page (2–3 brief paragraphs) falls below these thresholds entirely. Q044 (first paragraph flush-left) and Q045 (subsequent paragraphs indented) require a targeted, lower-threshold check on the specifically detected Acknowledgements page.

---

## Candidate comparison

### Candidate 1 — Acknowledgements paragraph indentation (Q044, Q045) ← RECOMMENDED

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q044: first Acknowledgements paragraph begins flush with left margin; Q045: subsequent paragraphs begin with visible indent |
| **Proposed rule** | **P043** — Acknowledgements page paragraph indentation check |
| **Module** | `src/njit_auditor/rules/pdf_acknowledgements_indentation.py` |
| **Issue types** | `acknowledgements_first_paragraph_not_flush`, `acknowledgements_later_paragraph_not_indented` |
| **Implementation risk** | **Low** — use `find_named_frontmatter_headings` (from `pdf_headings.py`) to find the Acknowledgements page; collect paragraph-leading lines below the heading; check first-paragraph x-position vs. body text baseline; check subsequent paragraph x-positions for visible indent |
| **Noise risk** | **Low-medium** — ACKNOWLEDGEMENTS is in EXPECTED_HEADINGS → reliable page detection; first-paragraph check requires finding a line that is NOT a heading and NOT a continuation of a previous block; gate: skip if fewer than 2 detected paragraph blocks |
| **Privacy** | **Low** — findings contain only geometry (x positions, page number, paragraph index); no Acknowledgements text content |
| **Likely tests** | (1) Acknowledgements page with flush first para + indented later paras → no finding; (2) Acknowledgements page where first para is indented → Q044 finding; (3) Acknowledgements page where later para is flush → Q045 finding; (4) No Acknowledgements page detected → no finding; (5) Single paragraph (no Q045 check) → no Q044 finding if flush; (6) Privacy check; (7) CLI integration |
| **Why selected** | Q044/Q045 are `not_implemented` and specifically call out the Acknowledgements page; P015's conservative thresholds miss short Acknowledgements pages; ACKNOWLEDGEMENTS is in EXPECTED_HEADINGS making detection reliable; low privacy risk (geometry only); clear Q-rule basis; analogous to how P041 added a Dedication-page-specific check after P034's copyright pattern |

### Candidate 2 — Abstract indentation (Q002, Q003)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q002: first Abstract paragraph flush-left; Q003: subsequent paragraphs indented |
| **Why not recommended** | Same P015 overlap as Q044/Q045; Abstract page is often very short (1 paragraph) making Q003 moot; ABSTRACT is in EXPECTED_HEADINGS but the paragraph count is typically too low to add value; Q044/Q045 (Acknowledgements) is more likely to have multiple paragraphs and genuinely benefit from a targeted check |

### Candidate 3 — TOC leader style (Q052)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q052: consistent leader style from entry to page number |
| **Why not recommended** | P018's `inconsistent_leader_dots` already covers the core Q052 requirement; incremental value too low |

### Candidate 4 — Copyright page year/author recall (Q010, Q011)

| Field | Detail |
|-------|--------|
| **Source basis** | P034 Q010/Q011 recall improvement (year 1/5, author 2/5) |
| **Why not recommended** | Not a new Q-rule; P034 refinement; Q044/Q045 add new Q-rule coverage vs. recall improvement of existing detection |

### Candidate 5 — LoT/LoF column alignment (Q068–Q069, Q078–Q079)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q068/Q078: number left column; Q069/Q079: page right column |
| **Why not recommended** | P018 already partially covers via `inconsistent_hierarchy_indent` and `misaligned_page_number_column`; overlap risk outweighs incremental value |

### Candidate 6 — LoT/LoF column label bold/alignment (Q063–Q064, Q072–Q073)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q063/Q072: label bold + left-aligned; Q064/Q073: Page label bold + right-aligned |
| **Why not recommended** | P031 covers presence; bold metadata unreliable; deferred every prior cycle for same reason |

### Candidate 7 — Dedication centering (Q033)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q033: dedication text block visually centered |
| **Why not recommended** | High FP from text block detection ambiguity; deferred every prior cycle |

---

## Ranking

| Rank | Candidate | Q-rule | Risk | Value |
|------|-----------|--------|------|-------|
| **1** | **Acknowledgements paragraph indentation** | **Q044, Q045** | **Low** | **Medium** |
| 2 | Abstract indentation | Q002, Q003 | Low | Low (short page, 1-para) |
| 3 | Copyright recall refinement | Q010, Q011 | Low | Low (P034 refinement) |
| 4 | TOC leader style | Q052 | Low | Low (overlaps P018) |
| 5 | LoT/LoF column alignment | Q068–Q069, Q078–Q079 | Low-med | Low (overlaps P018) |
| 6 | LoT/LoF column label bold | Q063–Q064, Q072–Q073 | Medium | Low (bold unreliable) |
| 7 | Dedication centering | Q033 | High | Low |

---

## Selected P043 scope

### Rule title

**P043 — PDF Acknowledgements page paragraph indentation check**

### Source basis

- **Q044**: "Does the first Acknowledgements paragraph begin flush with the left margin?"
- **Q045**: "Does every Acknowledgements paragraph after the first begin with a visible indent?"
- Complements **P015** (general paragraph indentation); adds page-targeted, lower-threshold check for the Acknowledgements section

### Scope included

1. **Acknowledgements page detection** — use `find_named_frontmatter_headings` (from `pdf_headings.py`) to locate pages with "ACKNOWLEDGEMENTS" heading. If not detected, emit nothing.
2. **Paragraph block extraction** — collect text line groups below the heading, grouping by vertical gap to identify paragraph breaks.
3. **Q044 check** — the first paragraph's first line should have an x-position approximately equal to the body text left baseline. If it is significantly indented (> INDENT_THRESHOLD_PT = 18pt), emit `acknowledgements_first_paragraph_not_flush`.
4. **Q045 check** — each subsequent paragraph's first line should be meaningfully indented (> INDENT_THRESHOLD_PT = 18pt) relative to the body left margin. If any later paragraph begins flush (indent < INDENT_THRESHOLD_PT), emit `acknowledgements_later_paragraph_not_indented`.
5. **Gate conditions**: skip if fewer than 2 paragraph blocks detected (can't check Q045 with only 1 block); skip if heading not detected.
6. **Privacy-safe findings** — include `page_number`, `issue_type`, `paragraph_index`, `observed_indent_pt`, `required_indent_pt`, `triage_tier`, `source_q_rule_id`. No Acknowledgements text content.

### Scope excluded

- Acknowledgements paragraph content (intent, advisor mention, etc.) — Q037–Q042 manual-only.
- General body page indentation — owned by **P015**.
- Abstract indentation (Q002/Q003) — partial P015 coverage; deferred.
- Acknowledgements heading style — owned by **P014** and **P038**.

### Expected module path

`src/njit_auditor/rules/pdf_acknowledgements_indentation.py`

Imports from:
- `pdf_headings.py` — `find_named_frontmatter_headings`, `HeadingMatch`
- `pdf_models.py` — `PdfDocument`, `PdfPage`, `PdfTextLine`

### Expected CLI / report / evaluation wiring

| Surface | Change |
|---------|--------|
| `src/njit_auditor/cli.py` | Import and call `check_pdf_acknowledgements_indentation()` after `check_pdf_indentation` (P015) |
| `data/processed/rules/project_added_rules.json` | Add **P043** entry (`implementation_status: implemented` after code lands) |
| `src/njit_auditor/evaluation.py` | Map P043 → `indentation` category (same as P015) |
| Reports | Standard `AuditFinding` details; no new triage rollup in v1 |

### Expected tests

| Test | Expectation |
|------|-------------|
| Acknowledgements page with flush first para + indented later para | No P043 finding |
| Acknowledgements page with indented first para | `acknowledgements_first_paragraph_not_flush` |
| Acknowledgements page with flush later para | `acknowledgements_later_paragraph_not_indented` |
| No ACKNOWLEDGEMENTS heading detected | No P043 finding (gate) |
| Only one paragraph block (can't check Q045) | No Q045 finding |
| Finding metadata privacy check | No Acknowledgements text in details |
| CLI integration | P043 in JSON output when triggered |

Update `tests/test_rule_inventory.py` count to **43** when implemented.

### Privacy constraints

- Findings contain only: `page_number`, `issue_type`, `paragraph_index` (0-based), `observed_indent_pt`, `required_indent_pt`, `triage_tier`, `source_q_rule_id` (`Q044` or `Q045`).
- No Acknowledgements text, advisor names, body prose, or private content in findings.
- Test fixtures use synthetic placeholder paragraph content.

### Acceptance criteria

1. P043 emits `acknowledgements_first_paragraph_not_flush` when the first Acknowledgements paragraph is indented.
2. P043 emits `acknowledgements_later_paragraph_not_indented` when a subsequent paragraph is flush.
3. P043 emits nothing when no ACKNOWLEDGEMENTS page is detected.
4. P043 emits nothing when only one paragraph block is found (gate for Q045).
5. P043 does not duplicate P015 issue types.
6. CLI runs P043 without changing P001–P042 behavior.
7. All existing 491 tests pass; new P043 synthetic tests added.
8. `project_added_rules.json` lists P043 (implementation PR only).

### Known false-positive risks

- **Indented acknowledgements styles**: Some disciplines use an indented-first-paragraph style for all acknowledgements. Mitigation: use INDENT_THRESHOLD_PT = 18pt to distinguish meaningful indentation from marginal offsets.
- **List or display content at page start**: If the Acknowledgements section begins with a list item or caption rather than a prose paragraph, the first "paragraph" may appear indented. Mitigation: require first block to contain at least MIN_TEXT_LEN = 20 chars; skip blocks that look like headings or captions.
- **ACKNOWLEDGEMENTS heading not in text layer**: Compressed/flattened PDFs may not have the heading detectable → gate silently skips.

### Local evaluation rerun (not committed)

After implementation, rerun five-PDF audit locally into gitignored
`data/evaluation/generated/current_auditor_after_p043/` and add
`docs/evaluation/p043_current_dataset_evaluation.md` with aggregate P043 counts only.

Do **not** commit generated JSON/MD. Do **not** update `generated_for_commit` or the
pre-P035/.../P042 canonical **1,446** aggregate.

---

## Implementation plan (next task)

1. Create `src/njit_auditor/rules/pdf_acknowledgements_indentation.py`:
   - Import `find_named_frontmatter_headings` from `pdf_headings.py`
   - Define `INDENT_THRESHOLD_PT = 18.0`, `MIN_TEXT_LEN = 20`, `MAX_PARA_GAP_PT = 14.0`
   - Implement `_find_acknowledgements_page(pdf_document)` → `PdfPage | None`
   - Implement `_extract_paragraphs(page, heading_bottom_y)` → `list[list[PdfTextLine]]`
   - Implement `_check_acknowledgements_indentation(page, paragraphs)` → `list[AuditFinding]`
   - Implement `check_pdf_acknowledgements_indentation(pdf_document)` → `list[AuditFinding]`
2. Wire CLI after `check_pdf_indentation` call.
3. Add P043 entry to `data/processed/rules/project_added_rules.json`.
4. Map P043 → `indentation` in `src/njit_auditor/evaluation.py`.
5. Add synthetic tests; update `tests/test_rule_inventory.py` to 43 rules.
6. Run full validation.

No changes to P001–P042 detector behavior.

---

## Validation plan

| Step | Command |
|------|---------|
| Inventory | `python -m pytest tests/test_rule_inventory.py -q` |
| P043 synthetics | `python -m pytest tests/test_pdf_rules.py -k p043 -q` |
| Full suite | `ruff check .`, `mypy src`, `python -m pytest` |

---

## Privacy notes

- Findings report only geometry — no Acknowledgements text content.
- Test fixtures use synthetic placeholder acknowledgements text.
- P043 findings never contain advisor names, institution names, or prose content.

## Generated-output safety

- Outputs under `data/evaluation/generated/` stay gitignored.
- Do not commit audit JSON or per-PDF reports.
