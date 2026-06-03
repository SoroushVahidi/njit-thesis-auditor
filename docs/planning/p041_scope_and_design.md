# P041 Scope and Design

- **Date:** 2026-06-03
- **Status:** **Scoped — not yet implemented**
- **Baseline main:** `4f9642c` (PR #106 — post-P040 consistency audit; P001–P040 implemented)

---

## Current state

| Area | State |
|------|--------|
| P-rules | **40/40** implemented (`P001`–`P040`) |
| Q-rules (raw inventory) | **79** total — **2** implemented, **11** partially_implemented, **66** not_implemented |
| Copyright page no-header | **P034** — Q009 top-margin header check for Copyright page; Q010/Q011 year/author consistency |
| Dedication page checks | **Not implemented** — Q032/Q033/Q034 completely unaddressed |
| TOC continued headings | **P030** — Q048/Q062/Q071 partially covered (presence check; style/format not checked) |
| Abstract indentation | **P015** — paragraph indentation covers all pages including Abstract (Q002/Q003 partial) |
| LoT/LoF entry alignment | **P018** — page-number column and indent-outlier checks (Q068/Q069/Q078/Q079 partially) |
| LoT/LoF column labels bold | **P031** — presence check for Table/Figure/Page labels (Q063/Q064/Q072/Q073 partial; bold styling not checked) |
| LoF terminal punctuation | **P040** — Q075 complete entries checked; implemented |

**P034 vs remaining Dedication gap:** P034 uses `_check_top_margin_header` on the Copyright page (Q009). The same approach can be applied to the Dedication page for Q032. DEDICATION page detection already exists in P037 via `_find_heading_first_page("DEDICATION", ...)`.

---

## Candidate comparison

### Candidate 1 — Dedication page no-top-margin-header (Q032) ← RECOMMENDED

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q032: "Is there no header text in the top margin area of the Dedication page?" |
| **Proposed rule** | **P041** — Dedication page top-margin header check |
| **Module** | `src/njit_auditor/rules/pdf_dedication_page.py` |
| **Issue types** | `dedication_top_margin_header_text` |
| **Implementation risk** | **Low** — exact same approach as P034's Q009 copyright-page header check; DEDICATION page detection via `_find_heading_first_page("DEDICATION", front_matter_pages, pdf_doc)` already used in P037; `_in_top_zone` and top-margin scan pattern proven in P034 |
| **Noise risk** | **Low-medium** — conservative gate: skip if no DEDICATION page detected; DEDICATION detection may miss pages without verbatim heading text (compressed/flattened PDFs, stylized dedication) |
| **Privacy** | **Low** — only inspects top-margin geometry (line.bbox.y0/y1); never reads dedication content; `observed_text_kind` in findings is a classification label, not dedication prose |
| **Likely tests** | (1) Dedication page with no top-margin text → no finding; (2) Dedication page with stray header text in top margin → `dedication_top_margin_header_text`; (3) No DEDICATION heading detected → no finding; (4) Page number in top margin → no finding (page numbers excluded); (5) CLI integration |
| **Finding count impact** | Low: most well-formatted Dedication pages should show 0; theses with running headers will show findings |
| **Why selected** | Q032 is completely unimplemented; proven P034 pattern directly applicable; uses existing P037 infrastructure; optional-page gate keeps noise low; clear privacy boundary (top margin only) |

### Candidate 2 — Abstract indentation (Q002, Q003)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q002: Abstract first paragraph flush-left; Q003: subsequent paragraphs indented |
| **Implementation risk** | **Low** — P015 already processes all pages including Abstract; detection of Abstract page via `EXPECTED_HEADINGS` already exists |
| **Noise risk** | **Low** — P015 already checks paragraph indentation broadly; Q002/Q003 would be a scoped version restricted to the Abstract page |
| **Privacy** | **Low** — paragraph geometry only; no text content in findings |
| **Why not recommended** | P015 already functionally covers Q002/Q003 (checks first-paragraph flush and subsequent-paragraph indentation on all pages including Abstract); a standalone P041 for Abstract-specific indentation would largely duplicate P015 behavior; incremental value too low relative to Q032 |

### Candidate 3 — TOC/List continued-heading refinement (Q048, Q062, Q071)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q048/Q062/Q071: subsequent TOC/LoT/LoF pages display correct "(Continued)" heading |
| **Implementation risk** | **Medium** — P030 already covers presence of continued headings; remaining gap is format checking (bold, centered) which requires heading-style detection from P014 |
| **Noise risk** | **Medium** — overlap with P014/P030; bold metadata may be absent in compressed PDFs |
| **Why not recommended** | P030 already covers the core requirement (presence); the remaining gap (bold/centered format) requires additional heading-style infrastructure with limited added value; P014 already checks heading style for named headings generally |

### Candidate 4 — LoT/LoF number-column left-alignment (Q068, Q078)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q068: table numbers in one left column; Q078: figure numbers in one left column |
| **Implementation risk** | **Low-medium** — P018 already checks right-column alignment; extending to check left-column consistency (all entry `indent_x` values within tolerance) is straightforward |
| **Noise risk** | **Medium** — indent-outlier detection may already partially cover this via P018's `inconsistent_hierarchy_indent` check; adding an explicit left-column check risks emitting P041 + P018 findings for the same page |
| **Why not recommended** | Overlap with P018's existing indent-outlier check; implementing a standalone P041 for Q068/Q078 left-column alignment would likely duplicate P018 behavior for many cases |

### Candidate 5 — P031 column label bold/alignment refinement (Q063, Q064, Q072, Q073)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q063/Q072: "Table"/"Figure" label bold and left-aligned; Q064/Q073: "Page" label bold and right-aligned |
| **Implementation risk** | **Medium** — P031 already checks presence of the labels; adding bold check requires span-level bold metadata which may be unreliable |
| **Noise risk** | **Medium** — bold metadata absent in many PDFs; high false-negative rate undermines value |
| **Why not recommended** | P031 already covers label presence; the remaining bold/alignment detail requires unreliable italic/bold metadata; better deferred until a more robust approach is available |

### Candidate 6 — Dedication text centering (Q033)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q033: "Is the full dedication text block visually centered on the page?" |
| **Implementation risk** | **High** — detecting the dedication text block (not the heading) and computing its horizontal centroid relative to page center requires text-block grouping not currently in any module |
| **Noise risk** | **High** — multi-paragraph dedications, single-line dedications, and stylized text all complicate block detection |
| **Privacy** | **Medium** — must never read/quote dedication content; centroid check is geometry-only |
| **Why not recommended** | High false-positive risk from block detection ambiguity; confirmed high-risk in P038/P039/P040 scoping |

### Lower-priority candidates

| Candidate | Why deferred |
|-----------|-------------|
| Q034 (dedication italic) | Very high FP; italic metadata unreliable |
| Q023–Q030 (bio-sketch content) | Semantic parsing; high privacy risk; manual-only |
| Full canonical P001–P040 rerun | Evaluation-only; PDFs unavailable |
| YAML spec abstraction | Infrastructure; premature |

---

## Ranking

| Rank | Candidate | Q-rule | Risk | Value |
|------|-----------|--------|------|-------|
| **1** | **Dedication page no-top-margin-header** | **Q032** | **Low-med** | **Medium** |
| 2 | LoT/LoF number-column left-alignment | Q068, Q078 | Low-med | Medium (overlaps P018) |
| 3 | Abstract indentation | Q002, Q003 | Low | Low (overlaps P015) |
| 4 | TOC continued-heading refinement | Q048, Q062, Q071 | Medium | Low (overlaps P030) |
| 5 | P031 label bold/alignment refinement | Q063–Q064, Q072–Q073 | Medium | Low (bold metadata unreliable) |
| 6 | Dedication centering | Q033 | High | Low |

---

## Selected P041 scope

### Rule title

**P041 — PDF Dedication page top-margin header check**

### Source basis

- **Q032**: "Is there no header text in the top margin area of the Dedication page?"
- Analogy to **P034** Q009 (Copyright page top-margin header check) — same detection approach

### Scope included

1. **DEDICATION page detection** — use `_find_heading_first_page("DEDICATION", front_matter_pages, pdf_doc)` from `pdf_roman_section_anchors.py` (P037) infrastructure. If no DEDICATION page is detected, emit nothing (optional page gate).
2. **Top-margin scan** — scan all lines on the Dedication page where `line.bbox.y1 <= page.height * _TOP_ZONE_RATIO` (same 0.15 ratio as P034).
3. **Header-text classification** — classify scanned text using the same logic as P034's `_classify_top_margin_text`: skip page-number candidates, skip the "DEDICATION" heading itself (when present in the top zone), skip copyright-like fragments; flag other text as `dedication_top_margin_header_text`.
4. **One finding per page** — emit at most one finding per detected Dedication page.
5. **Privacy-safe findings** — include `page_number`, `issue_type`, `observed_text_kind` (classification label), `approx_y0_pt`, `flagged_line_count`, `source_q_rule_id` (Q032). No dedication text, author name, or private content.

### Scope excluded

- Dedication text content (centering, italicization) — Q033/Q034 high FP risk; deferred.
- Dedication page numbering — owned by P037 (section-anchored Roman numerals) and P022 (no page number on no-number pages).
- Copyright page header — owned by P034 (Q009).
- Body pages and other front-matter pages.

### Expected module path

`src/njit_auditor/rules/pdf_dedication_page.py`

Imports from:
- `pdf_roman_section_anchors.py` — `_find_heading_first_page`, `_classify_pages`
- `pdf_copyright_page.py` — top-zone classification pattern (re-implemented locally for clarity)

### Expected CLI / report / evaluation wiring

| Surface | Change |
|---------|--------|
| `src/njit_auditor/cli.py` | Import and call `check_pdf_dedication_page()` after `check_pdf_copyright_page` (P034) |
| `data/processed/rules/project_added_rules.json` | Add **P041** entry (`implementation_status: implemented` after code lands) |
| `src/njit_auditor/evaluation.py` | Map P041 → `title_page_metadata` category (same as P033/P034) |
| Reports | Standard `AuditFinding` details; no new triage rollup in v1 |

### Expected tests

| Test | Expectation |
|------|-------------|
| Dedication page with no top-margin text | No P041 finding |
| Dedication page with stray header text (e.g., chapter title) in top margin | `dedication_top_margin_header_text` |
| No DEDICATION heading detected (gate) | No P041 finding |
| Page-number-only text in top margin | No finding (page-number candidates excluded) |
| "DEDICATION" heading text appears in top zone (skip heading itself) | No finding |
| CLI integration | P041 in JSON output when triggered |

Update `tests/test_rule_inventory.py` count to **41** when implemented.

### Privacy constraints

- Findings include only: `page_number`, `issue_type`, `observed_text_kind` (label like `"short_running_header"`), `approx_y0_pt`, `flagged_line_count`, `source_q_rule_id` (`Q032`).
- **Never** quote dedication text, author name, or any dedication prose in findings.
- Test fixtures use synthetic placeholder text, not real dissertation content.

### Acceptance criteria

1. P041 emits `dedication_top_margin_header_text` when non-page-number text is found in the top 15% of a detected Dedication page.
2. P041 emits nothing when no DEDICATION page is detected (conservative gate).
3. P041 emits nothing when the only top-margin text is the DEDICATION heading itself or a page number.
4. P041 does not duplicate P034 (copyright page) checks.
5. CLI runs P041 without changing P001–P040 behavior.
6. All existing 474 tests pass; new P041 synthetic tests added.
7. `project_added_rules.json` lists P041 (implementation PR only).

### Known false-positive risks

- DEDICATION page with very short running header: the `observed_text_kind` classification may misidentify short dedication text near the top of the page as a header. Mitigation: use the same conservative `_classify_top_margin_text` logic as P034, which only flags non-heading, non-page-number text.
- DEDICATION pages where the heading appears in the top zone AND another text is also present: skip the heading itself but flag only genuinely unexpected text.
- Compressed/flattened PDFs: DEDICATION heading may not be detectable → gate silently skips → false negative, not false positive.

### Local evaluation rerun (not committed)

After implementation, rerun five-PDF audit locally into gitignored
`data/evaluation/generated/current_auditor_after_p041/` and add
`docs/evaluation/p041_current_dataset_evaluation.md` with aggregate P041 counts only.

Do **not** commit generated JSON/MD. Do **not** update `generated_for_commit` or the
pre-P035/P036/P037/P038/P039/P040 canonical **1,446** aggregate.

---

## Implementation plan (next task)

1. Create `src/njit_auditor/rules/pdf_dedication_page.py`:
   - Import `_classify_pages`, `_find_heading_first_page` from `pdf_roman_section_anchors.py`
   - Define `_TOP_ZONE_RATIO = 0.15` and classification logic (page-number skip, heading-text skip)
   - Implement `check_pdf_dedication_page(pdf_document) -> list[AuditFinding]`
2. Wire CLI in `src/njit_auditor/cli.py` after P034 call.
3. Add P041 entry to `data/processed/rules/project_added_rules.json`.
4. Map P041 → `title_page_metadata` in `src/njit_auditor/evaluation.py`.
5. Add synthetic tests in `tests/test_pdf_rules.py`; update `tests/test_rule_inventory.py` to 41 rules.
6. Run full validation (`ruff check .`, `mypy src`, `python -m pytest`).
7. Optional: local evaluation doc (aggregate only, gitignored outputs).

No changes to P001–P040 detector behavior in the scoping PR.

---

## Validation plan

| Step | Command |
|------|---------|
| Inventory (post-impl) | `python -m pytest tests/test_rule_inventory.py -q` |
| P041 synthetics | `python -m pytest tests/test_pdf_rules.py -k p041 -q` |
| Full suite | `ruff check .`, `mypy src`, `python -m pytest` |

Scoping PR (this document): `python -m pytest tests/test_rule_inventory.py -q` minimum.

---

## Privacy notes

- Design and evaluation docs must remain aggregate and metadata-only.
- Test fixtures use synthetic placeholder text for the Dedication page heading and header text — no real dissertation content.
- P041 findings report only top-margin geometry metadata and a classification label — no dedication prose, no author name, no title text.

## Generated-output safety

- Outputs under `data/evaluation/generated/` stay gitignored.
- Do not commit audit JSON, per-PDF reports, or regenerated full-audit bundles from local runs.
