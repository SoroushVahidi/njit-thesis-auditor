# P044 Scope and Design

- **Date:** 2026-06-03
- **Status:** **Implemented** (implementation PR — P001–P044 implemented; see `docs/evaluation/p044_abstract_indentation_synthetic_validation.md`)
- **Baseline main:** `afc2f43` (PR #118 — post-P043 consistency audit; P001–P043 implemented)

---

## Current state

| Area | State |
|------|-------|
| P-rules | **43/43** implemented (`P001`–`P043`) |
| Q-rules (raw inventory) | **79** total — **2** implemented, **11** partially_implemented, **66** not_implemented (inventory JSON lags actual coverage — many Q-rules are heuristically covered by existing P-rules) |
| General paragraph indentation | **P015** — covers all pages; Q002/Q003 partially addressed for abstract opening only |
| Abstract-specific indentation | **Not yet implemented** — P015 checks the abstract opening paragraph (Q002 partial) but does not verify subsequent abstract paragraphs are indented (Q003 gap) |
| Acknowledgements indentation | **P043** — Q044/Q045; directly analogous page-scoped indentation check |
| Dedication top-margin header | **P041** — Q032 |
| TOC appendix format | **P042** — Q058/Q059 |

**Gap vs P015:** P015 flags the abstract *opening* paragraph if it appears indented (line 207 of `pdf_indentation.py`), but it does not check that *subsequent* abstract paragraphs begin with a visible indent. Q002 (first paragraph flush-left) is partially covered; Q003 (subsequent paragraphs indented) is not covered by any P-rule.

**Evaluation rerun status:** 4 of 5 evaluation PDFs are directly accessible in `data/raw/ester/`. The 5th (Sebastian Fine Revised) is ZIP-only. A canonical five-PDF run requires all five. The 4-PDF non-canonical subset situation mirrors P035. A new P-rule adds more value than a non-canonical rerun, so the evaluation rerun is deferred.

---

## Candidate comparison

### Candidate 1 — Abstract paragraph indentation (Q002, Q003) ← RECOMMENDED

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q002: first Abstract paragraph begins flush with the left margin; Q003: every Abstract paragraph after the first begins with a visible indent |
| **Proposed rule** | **P044** — Abstract page paragraph indentation check |
| **Module** | `src/njit_auditor/rules/pdf_abstract_indentation.py` |
| **Issue types** | `abstract_first_paragraph_indented`, `abstract_subsequent_paragraph_not_indented` |
| **Implementation risk** | **Low** — identical pattern to P043 (`pdf_acknowledgements_indentation.py`); change heading label to `ABSTRACT`, adjust gate conditions |
| **Noise risk** | **Low-medium** — ABSTRACT is in `EXPECTED_HEADINGS` (reliable detection); gate: skip if ABSTRACT heading absent; Q002 gate: ≥1 paragraph; Q003 gate: ≥2 paragraph blocks (many abstracts have only 1 paragraph — Q003 silently skips) |
| **Privacy** | **Low** — findings contain only geometry (x positions, page number, paragraph index); no Abstract text, author names, or body prose |
| **Likely tests** | (1) Abstract page with flush first para + indented later para → no finding; (2) Abstract page with indented first para → Q002 finding; (3) Abstract page with flush later para → Q003 finding; (4) No ABSTRACT heading detected → no finding; (5) Single paragraph → Q002 checked only, no Q003; (6) Finding metadata privacy check; (7) CLI integration |
| **Why selected** | Q002/Q003 are in `not_implemented` in the inventory; P015 partially covers Q002 (abstract opening) but not Q003; P043 establishes the direct reusable pattern; low FP risk with heading gate; privacy-safe (geometry only); natural successor to P043 |

### Candidate 2 — Evaluation rerun (4-PDF non-canonical)

| Field | Detail |
|-------|--------|
| **Basis** | Run P001–P043 on the 4 available PDFs to get current-dataset counts for P035–P043 |
| **Why not selected** | Only 4 of 5 PDFs directly available; Sebastian Fine Revised is ZIP-only → non-canonical; mirrors P035 local-subset precedent; adding a new P-rule provides more value than a non-canonical rerun; defer until full five-PDF set is available |

### Candidate 3 — LoT/LoF continued headings (Q062, Q071)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q062: LoT subsequent pages show "(Continued)"; Q071: LoF subsequent pages show "(Continued)" |
| **Why not selected** | **P030 already covers Q062 and Q071** — `pdf_toc_continued_headings.py` docstring declares "Partial heuristic coverage for Q048, Q062, and Q071"; confirmed in `source_q_rule_ids: Q048,Q062,Q071`; this is not a gap |

### Candidate 4 — TOC/List entry case (Q049, Q050)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q049: TOC L1 entries all-caps; Q050: TOC L2 entries title case |
| **Why not selected** | **P024 already covers Q049 and Q050** — `pdf_toc_list_formatting.py` docstring declares "TOC Level 1 chapter/front-matter entries: ALL CAPS (Q049)" and "TOC Level 2 entries: Title Case (Q050)"; emits P024 findings with `source_q_rule_id: Q049/Q050` |

### Candidate 5 — TOC leader style (Q052)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q052: consistent leader style from entry to page number |
| **Why not selected** | **P018 already covers Q052** via `inconsistent_leader_dots` finding; `pdf_toc_alignment.py` tracks `has_leader_dots` per entry and flags inconsistency (lines 274–322) |

### Candidate 6 — Copyright page header check (Q009)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q009: no header text in top margin of Copyright page |
| **Why not selected** | **P034 already covers Q009** — `pdf_copyright_page.py` docstring: "Q009: no header text in the Copyright page top margin"; `_check_top_margin_header` implements this check; marked `source_q_rule_id: Q009` |

### Candidate 7 — Dedication centering/italic (Q033, Q034)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q033: dedication text block centered; Q034: dedication text italicized |
| **Why not selected** | High FP risk — centering has no text-layer signal; italic metadata unreliable in many PDF renderings; deferred in every prior cycle; P041 already covers Q032 (top-margin header check) |

### Candidate 8 — Biographical Sketch content (Q023–Q030)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q023–Q030: semantic content checks (place of birth excluded, chronological order, citation style, etc.) |
| **Why not selected** | Semantic checks require reading paragraph content → high privacy risk; heuristic NLP fragile without proper NLP tools; deferred every prior cycle |

---

## Ranking

| Rank | Candidate | Q-rule | Risk | Value | Decision |
|------|-----------|--------|------|-------|----------|
| **1** | **Abstract paragraph indentation** | **Q002, Q003** | **Low** | **Medium** | **SELECTED** |
| 2 | Evaluation rerun (4-PDF subset) | — | Low | Medium | Deferred — non-canonical; 5th PDF ZIP-only |
| 3 | LoT/LoF continued headings | Q062, Q071 | Low | Low | Not applicable — P030 already covers |
| 4 | TOC entry case | Q049, Q050 | Low | Low | Not applicable — P024 already covers |
| 5 | Leader style | Q052 | Low | Low | Not applicable — P018 already covers |
| 6 | Copyright top-margin header | Q009 | Low | Low | Not applicable — P034 already covers |
| 7 | Dedication centering/italic | Q033, Q034 | High | Low | High FP risk; deferred |
| 8 | Biographical Sketch content | Q023–Q030 | High | Low | Semantic/privacy risk; deferred |

---

## Selected P044 scope

### Rule title

**P044 — PDF Abstract page paragraph indentation check**

### Source basis

- **Q002**: "Does the first Abstract paragraph begin flush with the left margin?"
- **Q003**: "Does every Abstract paragraph after the first begin with a visible indent?"
- Complements **P015** (general paragraph indentation, which partially flags abstract opening) and **P043** (Acknowledgements indentation); adds a dedicated, lower-threshold check for the Abstract page

### Scope included

1. **Abstract page detection** — use `find_named_frontmatter_headings` (from `pdf_headings.py`) to locate pages with an "ABSTRACT" heading. If not detected, emit nothing.
2. **Paragraph block extraction** — collect text line groups below the Abstract heading, grouped by vertical gap (same `MAX_PARA_GAP_PT = 14.0` as P043). Filter short lines, page-number candidates, and low-alpha content.
3. **Q002 check** — the first paragraph's first line x-position should be approximately equal to the body text left margin. If it exceeds `INDENT_THRESHOLD_PT = 18pt`, emit `abstract_first_paragraph_indented` (P044 / Q002).
4. **Q003 check** — each subsequent paragraph's first line should be meaningfully indented (> `INDENT_THRESHOLD_PT = 18pt`) relative to the body left margin. If any later paragraph begins flush (indent < threshold), emit `abstract_subsequent_paragraph_not_indented` (P044 / Q003). Gate: skip Q003 entirely if fewer than 2 paragraph blocks detected.
5. **Left margin derivation** — minimum x0 across all paragraph first-lines on the abstract section (same approach as P043).
6. **Privacy-safe findings** — include `page_number`, `issue_type`, `paragraph_index`, `observed_x0`, `expected_left_margin`, `indent_delta_points`, `required_indent_points`, `triage_tier`, `source_q_rule_id`. No Abstract text content.

### Scope excluded

- Abstract text content (thesis statement, methodology) — manual-only / semantic.
- Abstract word count — owned by **P021** (abstract length check).
- General body page indentation — owned by **P015**.
- Acknowledgements indentation — owned by **P043**.
- Abstract heading presence and style — owned by **P038**.

### Expected module path

`src/njit_auditor/rules/pdf_abstract_indentation.py`

Imports from:
- `pdf_headings.py` — `find_named_frontmatter_headings`, `normalize_heading_text`
- `pdf_models.py` — `PdfDocument`, `PdfPage`, `PdfTextLine`
- `njit_auditor.models` — `AuditFinding`, `Severity`

### Expected CLI / report / evaluation wiring

| Surface | Change |
|---------|--------|
| `src/njit_auditor/cli.py` | Import and call `check_pdf_abstract_indentation()` after `check_pdf_indentation` (P015) |
| `data/processed/rules/project_added_rules.json` | Add **P044** entry (`implementation_status: implemented` after code lands) |
| `src/njit_auditor/evaluation.py` | Map P044 → `indentation` category (same as P015 and P043) |
| Reports | Standard `AuditFinding` details; no new triage rollup in v1 |

### Expected tests

| Test | Expectation |
|------|-------------|
| Abstract page: flush first para + indented later para | No P044 finding |
| Abstract page: indented first para | `abstract_first_paragraph_indented` (Q002) |
| Abstract page: flush later para | `abstract_subsequent_paragraph_not_indented` (Q003) |
| No ABSTRACT heading detected | No P044 finding (gate) |
| Only one paragraph block | Q002 checked; no Q003 finding (gate) |
| Finding metadata privacy check | No Abstract text in finding details |
| CLI integration | P044 in JSON output when triggered |

Update `tests/test_rule_inventory.py` count from **43** to **44** when implemented.

### Privacy constraints

- Findings contain only: `page_number`, `issue_type`, `paragraph_index` (0-based), `observed_x0`, `expected_left_margin`, `indent_delta_points`, `required_indent_points`, `triage_tier`, `source_q_rule_id` (`Q002` or `Q003`).
- No Abstract text, thesis title, author names, or body prose in findings.
- Test fixtures use synthetic placeholder abstract text.

### Acceptance criteria

1. P044 emits `abstract_first_paragraph_indented` when the first Abstract paragraph is indented past threshold.
2. P044 emits `abstract_subsequent_paragraph_not_indented` when a subsequent paragraph is flush.
3. P044 emits nothing when no ABSTRACT page is detected.
4. P044 emits nothing on Q003 when only one paragraph block is found.
5. P044 does not duplicate P015 or P043 issue types.
6. CLI runs P044 without changing P001–P043 behavior.
7. All existing 498 tests pass; new P044 synthetic tests added.
8. `project_added_rules.json` lists P044 (implementation PR only).

### Known false-positive risks

| Risk | Mitigation |
|------|-----------|
| Some style guides use uniformly indented abstract paragraphs | `INDENT_THRESHOLD_PT = 18pt` reduces marginal-offset false positives |
| Very short or single-paragraph abstracts (Q003 scope is moot) | Q003 gate: require ≥2 paragraph blocks; silently skip otherwise |
| ABSTRACT heading not in text layer (compressed/flattened PDF) | Gate silently skips; no false positive |
| P015 and P044 may both flag the abstract opening paragraph | P044 uses distinct issue types; P015 issue type is `unexpected_opening_indent` — no confusion in reports |

### Local evaluation rerun (not committed)

After implementation, run five-PDF audit locally into gitignored
`data/evaluation/generated/current_auditor_after_p044/` when all five PDFs are accessible.
Add `docs/evaluation/p044_current_dataset_evaluation.md` with aggregate P044 counts only.

Do **not** commit generated JSON/MD. Do **not** update `generated_for_commit` or the
pre-P035/.../P043 canonical **1,446** aggregate.

---

## Implementation plan (next task)

1. Create `src/njit_auditor/rules/pdf_abstract_indentation.py`:
   - Import `find_named_frontmatter_headings`, `normalize_heading_text` from `pdf_headings.py`
   - Define `INDENT_THRESHOLD_PT = 18.0`, `MIN_TEXT_LEN = 20`, `MAX_PARA_GAP_PT = 14.0`, `MIN_PARA_BLOCKS = 2`, `_HEADING_LABEL = "ABSTRACT"`
   - Implement `_find_abstract_page_and_heading_y(pdf_document)` → `tuple[PdfPage, float] | None`
   - Implement `_lines_below_heading(page, heading_bottom_y)` → `list[PdfTextLine]`
   - Implement `_group_paragraphs(lines)` → `list[list[PdfTextLine]]`
   - Implement `check_pdf_abstract_indentation(pdf_document)` → `list[AuditFinding]`
2. Wire in `src/njit_auditor/cli.py` after the `check_pdf_indentation` call.
3. Add P044 entry to `data/processed/rules/project_added_rules.json`.
4. Map P044 → `indentation` in `src/njit_auditor/evaluation.py`.
5. Add synthetic tests covering all acceptance criteria; update `tests/test_rule_inventory.py` to **44** rules.
6. Run full validation: `ruff check .`, `mypy src`, `python -m pytest`.

No changes to P001–P043 detector behavior.

---

## Validation plan

| Step | Command |
|------|---------|
| Inventory | `python -m pytest tests/test_rule_inventory.py -q` |
| P044 synthetics | `python -m pytest tests/test_pdf_rules.py -k p044 -q` |
| Full suite | `ruff check .`, `mypy src`, `python -m pytest` |

---

## Privacy notes

- Findings report only geometry — no Abstract text content.
- Test fixtures use synthetic placeholder abstract text.
- P044 findings never contain thesis title, author names, or prose content.

## Generated-output safety

- Outputs under `data/evaluation/generated/` stay gitignored.
- Do not commit audit JSON or per-PDF reports.
