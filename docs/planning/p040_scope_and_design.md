# P040 Scope and Design

- **Date:** 2026-06-03
- **Status:** **Scoped — not yet implemented**
- **Baseline main:** `5389686` (PR #102 — post-P039 consistency audit; P001–P039 implemented)

---

## Current state

| Area | State |
|------|--------|
| P-rules | **39/39** implemented (`P001`–`P039`) |
| Q-rules (raw inventory) | **79** total — **2** implemented, **11** partially_implemented, **66** not_implemented |
| LoF sentence case | **P024** — `_sentence_case_violation` in `_check_lof_page`; Q074 partially covered |
| LoF terminal punctuation | **Not implemented** — Q075 completely unaddressed |
| LoT title case / no-period | **P024** — both checks present |
| Dedication page top-margin | **Not implemented** — Q032 completely unaddressed |
| TOC level indentation | **P039** — L2 relative to L1, L3 relative to L2; Q056 |
| TOC/LoF/LoT formatting cluster | P018 (alignment), P024 (case/punct), P030 (continued headings), P031 (column headers), P032 (wrap spacing), P036 (inter-entry spacing), P039 (TOC indentation hierarchy) |

**P024 vs remaining LoF gap:** P024 detects LoF pages and processes entries via `_check_lof_page`. It checks sentence case (Q074 partial) but does **not** check whether entries end with terminal punctuation. Q075 asks exactly that.

---

## Candidate comparison

### Candidate 1 — LoF terminal punctuation (Q075) ← RECOMMENDED

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q075: "Does every figure description end with a terminal punctuation mark?" |
| **Proposed rule** | **P040** — LoF entry terminal punctuation check |
| **Module** | `src/njit_auditor/rules/pdf_lof_terminal_punctuation.py` |
| **Issue types** | `lof_entry_missing_terminal_punctuation` |
| **Implementation risk** | **Low** — P024 already detects LoF pages via `detect_toc_like_pages` and extracts entries via `extract_toc_entry_lines`; `_clean_entry_text` and `_strip_list_prefix` provide the needed text; checking terminal `.`/`?`/`!` is deterministic |
| **Noise risk** | **Low-medium** — restrict to entries with `page_number_token is not None` (complete entries / last line of wrapped entries) to avoid false positives on wrap-continuation lines |
| **Privacy** | **Low** — findings contain only `page_number`, `issue_type`, and per-page count metadata; no entry text quoted |
| **Likely tests** | (1) LoF entry ending with `.` → no finding; (2) LoF entry ending with no punctuation → `lof_entry_missing_terminal_punctuation`; (3) Wrapped entry: only last line checked; (4) Entry without page number token skipped; (5) Non-LoF page (TOC, LoT) → no finding; (6) CLI JSON includes P040 when triggered |
| **Finding count impact** | Low–moderate: depends on theses; well-formatted LoFs should show 0; theses without terminal punctuation on figure captions/descriptions will show findings |
| **Why selected** | Q075 is completely unimplemented; the exact infrastructure needed (LoF page detection, entry parsing, `_clean_entry_text`, `_strip_list_prefix`) already exists in P024; filtering to `page_number_token is not None` elegantly handles wrapped entries; low privacy risk; clear acceptance criteria; natural complement to P024's LoT no-period and LoF sentence-case checks |

### Candidate 2 — Dedication page no-top-margin-header (Q032)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q032: "Is there no header text in the top margin area of the Dedication page?" |
| **Proposed rule** | P040 — Dedication page top-margin header check |
| **Module** | `src/njit_auditor/rules/pdf_dedication_page.py` (new) |
| **Issue types** | `dedication_top_margin_header_text` |
| **Implementation risk** | **Medium** — DEDICATION not in `EXPECTED_HEADINGS`; must use `_find_heading_first_page("DEDICATION", ...)` from P037; top-margin check is analogous to P034 Q009 (already proven); gate: skip if no DEDICATION page detected |
| **Noise risk** | **Medium** — DEDICATION heading may be absent or undetectable on flattened/compressed PDFs; gate silently skips when not found, limiting recall |
| **Privacy** | **Low** — checks only top-margin geometry; never reads dedication content |
| **Why not recommended** | (1) Detection reliability lower than Q075: DEDICATION not in EXPECTED_HEADINGS requires a separate detection path; (2) optional page means check fires infrequently; (3) Q075 has broader applicability (any thesis with figures has a LoF) |

### Candidate 3 — Dedication text centering (Q033)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q033: "Is the full dedication text block visually centered on the page?" |
| **Implementation risk** | **High** — requires detecting the dedication text block (not the heading), computing block centroid relative to page horizontal midpoint; multi-paragraph dedications complicate block detection |
| **Noise risk** | **High** — dedication content can be a single line, multiple paragraphs, or indented blocks; centroid detection is unreliable without clear block boundaries |
| **Privacy** | **Medium** — must not read or quote dedication prose; centroid check is geometry-only but page structure detection is harder than heading-level checks |
| **Why not recommended** | High false-positive risk from block detection ambiguity; optional section; confirmed high-risk in P038 scoping (same conclusion holds for P040) |

### Candidate 4 — Dedication text italicization (Q034)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q034: "If the dedication text uses the Latin alphabet, is the entire text italicized?" |
| **Implementation risk** | **High** — italic metadata is frequently absent in PDFs; many theses produce no italic flags even on visually italic text |
| **Noise risk** | **Very high** — false negatives extremely likely; cannot reliably distinguish styled-italic from non-italic at PDF text-layer level |
| **Privacy** | **Medium** — must not quote dedication text; italic flag is metadata but requires scanning text content |
| **Why not recommended** | Italic metadata unreliable in rendered PDFs; high false-negative rate makes this check misleading; identified as highest-risk candidate in P038 scoping; unsuitable for heuristic v1 |

### Candidate 5 — P035 image-block body layout refinement

| Field | Detail |
|-------|--------|
| **Source basis** | P035 v1 skips image-only floats; improvement uses PyMuPDF image/vector bbox extraction |
| **Implementation risk** | **High** — requires changes to `pdf_layout.py`; not a new Q-rule; adds PyMuPDF image-extraction dependency |
| **Noise risk** | **Medium** — image bboxes may not reliably distinguish figure body from decorative images |
| **Why not recommended** | Refinement of existing P035, not a new Q-rule; infrastructure-heavy; reusable-tooling audit identified deepdoctection as future P035 v2 path, not a v1 extension |

### Lower-priority candidates (not ranked above 5)

| Candidate | Why deferred |
|-----------|-------------|
| Q044–Q045 (Acknowledgements indentation) | Q015–Q020 paragraph intent is manual-only; Q044–Q045 (flush/indent) would heavily overlap P015 (paragraph indentation) |
| Q023–Q030 (Bio-sketch content) | Semantic parsing; high privacy risk; manual-only per coverage audit |
| Full canonical P001–P039 evaluation rerun | Evaluation-only; no implementation; PDFs unavailable |
| YAML/spec abstraction | Infrastructure; premature; no urgent Q-rule motivation |

---

## Ranking

| Rank | Candidate | Q-rule | Risk | Value |
|------|-----------|--------|------|-------|
| **1** | **LoF terminal punctuation** | **Q075** | **Low** | **High** |
| 2 | Dedication no-top-margin-header | Q032 | Medium | Low (optional page) |
| 3 | Dedication centering | Q033 | High | Low |
| 4 | Dedication italicization | Q034 | Very High | Low |
| 5 | P035 image-block refinement | — (P035 v2) | High | Medium |

---

## Selected P040 scope

### Rule title

**P040 — PDF List of Figures entry terminal punctuation check**

### Source basis

- **Q075**: "Does every figure description end with a terminal punctuation mark?"
- Complements **P024** (Q074 sentence case, Q065 LoT title case/no-period); does **not** replace it

### Scope included

1. **LoF pages only** — apply only to pages classified as `list_of_figures` by `detect_toc_like_pages`.
2. **Complete entries only** — restrict to `TocEntryLine` instances where `page_number_token is not None`. These are complete single-line entries or the final (last) line of wrapped multi-line entries. Lines without a page number token are wrap continuations; skip them to avoid false positives.
3. **Entry text extraction** — use `_clean_entry_text(entry)` to strip page number token and leader dots, then `_strip_list_prefix` to remove "Figure N." prefix. The result is the figure description text.
4. **Terminal punctuation check** — the description text must end with `.`, `?`, or `!`. If not, emit `lof_entry_missing_terminal_punctuation`.
5. **Minimum length gate** — skip entries with fewer than 10 characters after stripping (avoids false positives on very short entries or orphaned fragments).
6. **One finding per page** — aggregate all missing-punctuation entries per page into a single finding with an entry count, rather than one finding per entry.
7. **Privacy-safe findings** — include only `page_number`, `issue_type`, `entry_count`, `source_q_rule_id` in finding details. No figure description text.

### Scope excluded

- TOC and LoT pages — only LoF is covered (Q075 is LoF-specific).
- LoF sentence case — owned by **P024** (Q074 partial).
- LoT title case / no-period — owned by **P024** (Q065 area).
- Continuation lines (wrap fragments) without page number tokens.
- Entries shorter than 10 characters.
- Figure caption punctuation in the document body — owned by **P017**.

### Expected module path

`src/njit_auditor/rules/pdf_lof_terminal_punctuation.py`

Imports from:
- `pdf_toc_alignment.py` — `detect_toc_like_pages`, `extract_toc_entry_lines`, `TocEntryLine`, `TocPageContext`
- `pdf_toc_list_formatting.py` — `_clean_entry_text`, `_strip_list_prefix`

### Expected CLI / report / evaluation wiring

| Surface | Change |
|---------|--------|
| `src/njit_auditor/cli.py` | Import and call `check_pdf_lof_terminal_punctuation()` after `check_pdf_toc_list_entry_spacing` and `check_pdf_toc_entry_hierarchy` |
| `data/processed/rules/project_added_rules.json` | Add **P040** entry (`implementation_status: implemented` after code lands) |
| `src/njit_auditor/evaluation.py` | Map P040 → `list_of_tables_figures_toc` category (same as P024/P036/P039) |
| Reports | Standard `AuditFinding` details; no new triage rollup in v1 |

### Expected tests

| Test | Expectation |
|------|-------------|
| LoF entry ending with `.` | No P040 finding |
| LoF entry ending with `?` | No P040 finding |
| LoF entry ending with `!` | No P040 finding |
| LoF entry ending with no punctuation | `lof_entry_missing_terminal_punctuation` |
| LoF entry ending with a word (no punct) | `lof_entry_missing_terminal_punctuation` |
| Wrapped entry: continuation line (no page num token) | Not checked; no finding |
| Wrapped entry: final line with page num token + no terminal punct | Finding |
| TOC page | No P040 finding |
| LoT page | No P040 finding |
| Short entry (< 10 chars) | Skipped; no finding |
| Finding metadata privacy check | No figure description text in details |
| CLI integration | P040 in JSON output when triggered |

Update `tests/test_rule_inventory.py` count to **40** when implemented.

### Privacy constraints

- `lof_entry_missing_terminal_punctuation` findings include only: `page_number`, `issue_type`, `entry_count`, `source_q_rule_id` (`Q075`). No figure description text, caption prose, or private content.
- Test fixtures use synthetic placeholder figure descriptions, not real dissertation content.

### Acceptance criteria

1. P040 emits `lof_entry_missing_terminal_punctuation` when complete LoF entries lack terminal `.`/`?`/`!`.
2. P040 does not flag continuation lines (entries without `page_number_token`).
3. P040 does not fire on TOC or LoT pages.
4. P040 does not duplicate P024, P017, or P035 issue types.
5. CLI runs P040 on `njit-audit pdf` without changing P001–P039 behavior.
6. All existing 465 tests pass; new P040 synthetic tests added.
7. `project_added_rules.json` lists P040 with correct module path (implementation PR).

### Known false-positive risks

- **Wrapped entries where pdfplumber splits lines**: if pdfplumber does not assign a page number token to the last line of a wrapped entry, that line is skipped. This causes false negatives, not false positives.
- **Very short entries**: the `< 10` character minimum avoids most fragments, but short valid entries (e.g., "Fig. 1.") may still be checked.
- **Entries ending in closing parentheses or brackets**: some figure descriptions end with a parenthetical without terminal punctuation. These are legitimate NJIT violations per Q075.

### Local evaluation rerun (not committed)

After implementation, rerun five-PDF audit locally into gitignored
`data/evaluation/generated/current_auditor_after_p040/` and add
`docs/evaluation/p040_current_dataset_evaluation.md` with aggregate P040 counts only.

Do **not** commit generated JSON/MD. Do **not** update `generated_for_commit` or the
pre-P035/P036/P037/P038/P039 canonical **1,446** aggregate.

---

## Implementation plan (next task)

1. Create `src/njit_auditor/rules/pdf_lof_terminal_punctuation.py`:
   - Import helpers from `pdf_toc_alignment.py` and `pdf_toc_list_formatting.py`
   - Define `MIN_ENTRY_TEXT_LEN = 10` and `_TERMINAL_PUNCT_RE = re.compile(r'[.?!]\s*$')`
   - Implement `_check_lof_terminal_punctuation_page(context, entries) -> list[AuditFinding]`
   - Implement `check_pdf_lof_terminal_punctuation(pdf_document) -> list[AuditFinding]`
2. Wire CLI in `src/njit_auditor/cli.py` after P039 call.
3. Add P040 entry to `data/processed/rules/project_added_rules.json`.
4. Map P040 → `list_of_tables_figures_toc` in `src/njit_auditor/evaluation.py`.
5. Add synthetic tests in `tests/test_pdf_rules.py`; update `tests/test_rule_inventory.py` to 40 rules.
6. Run full validation (`ruff check .`, `mypy src`, `python -m pytest`).
7. Optional: local evaluation doc (aggregate only, gitignored outputs).

No changes to P001–P039 detector behavior in the scoping PR.

---

## Validation plan

| Step | Command |
|------|---------|
| Inventory (post-impl) | `python -m pytest tests/test_rule_inventory.py -q` |
| P040 synthetics | `python -m pytest tests/test_pdf_rules.py -k p040 -q` |
| Full suite | `ruff check .`, `mypy src`, `python -m pytest` |

Scoping PR (this document): `python -m pytest tests/test_rule_inventory.py -q` minimum.

---

## Privacy notes

- Design and evaluation docs must remain aggregate and metadata-only.
- Test fixtures use synthetic placeholder figure descriptions, not real dissertation content.
- P040 findings report only per-page counts and issue type — no figure description text.
- `lof_entry_missing_terminal_punctuation` findings never contain dissertation prose.

## Generated-output safety

- Outputs under `data/evaluation/generated/` stay gitignored.
- Do not commit audit JSON, per-PDF reports, or regenerated full-audit bundles from local runs.
