# P048 Scope and Design

- **Date:** 2026-06-03
- **Status:** **Implemented**
- **Baseline main:** `225e62c` (PR #136 — post-P047 documentation consistency; P001-P047 implemented)

---

## Baseline state at scoping

| Area | State |
|------|-------|
| P-rules at scoping | **47/47** implemented (`P001`-`P047`) |
| Q-rules (updated inventory, post-P047) | **79** total — **2** implemented, **55** partially_implemented, **22** not_implemented (9 manual-only, 13 automatable gaps) |
| LoT/LoF entry number left-column alignment | **P046** — Q068/Q078; implemented |
| LoT/LoF page-number right-column alignment | **P048** — Q069/Q079; implemented as a LoT/LoF-specific complement to generic P018 |
| Bio Sketch bullet single-spacing | **P047** — Q026; implemented |

**Implemented gap:** Q069 and Q079 ask whether List of Tables and List of Figures page numbers align vertically in one right column. P018 already detects generic TOC/list right-column outliers, but it reports under a broad P018 issue type and is not tailored to LoT/LoF-specific Q-rule attribution. P048 adds a narrow geometry-only complement, not a rewrite of P018.

---

## Candidate comparison

### Candidate 1 — LoT/LoF page-number right-column alignment (Q069/Q079) ← RECOMMENDED

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q069: LoT page numbers align vertically in one right column; Q079: LoF page numbers align vertically in one right column |
| **Proposed rule** | **P048** — LoT/LoF page-number right-column alignment check |
| **Module** | `src/njit_auditor/rules/pdf_lot_lof_page_number_alignment.py` |
| **Issue types** | `lot_page_number_column_misaligned`, `lof_page_number_column_misaligned` |
| **Implementation risk** | **Low-medium** — uses existing `detect_toc_like_pages` and `extract_toc_entry_lines`; must avoid duplicating P018 noise |
| **Noise risk** | **Low-medium** — gate on LoT/LoF pages, complete entries with detected page-number tokens, and minimum entry count |
| **Privacy** | **Low** — findings should contain only page/section, counts, right-edge geometry, thresholds, and Q-rule IDs |
| **Likely tests** | (1) no LoT/LoF pages -> no finding; (2) aligned LoT/LoF page numbers -> no finding; (3) misaligned LoT -> Q069 issue; (4) misaligned LoF -> Q079 issue; (5) sparse/ambiguous entries skip; (6) split numeric-only page-number lines still handled via existing extractor; (7) metadata privacy check |
| **Why selected** | It is the safest remaining geometry-only Q-rule pair after P047. It completes the P046 left-column work with a matching LoT/LoF right-column rule and keeps privacy risk low. |

### Candidate 2 — Copyright page recall refinement (Q010/Q011)

| Field | Detail |
|-------|--------|
| **Current coverage** | P034 already compares copyright year and author when both sides are confidently extracted |
| **Why not selected** | Remaining improvements would likely be recall refinements around names/title-page extraction. That carries higher privacy and false-positive risk than LoT/LoF geometry. |

### Candidate 3 — Dedication centering or italic checks (Q033/Q034)

| Field | Detail |
|-------|--------|
| **Why not selected** | Repeatedly deferred as high false-positive risk. Centering depends on visual block interpretation; italic metadata is unreliable in many PDFs. |

### Candidate 4 — Bio Sketch or Acknowledgements semantic content

| Field | Detail |
|-------|--------|
| **Why not selected** | Semantic/private content checks require reading sensitive text and remain manual-only. |

---

## Ranking

| Rank | Candidate | Q-rule | Risk | Value | Decision |
|------|-----------|--------|------|-------|----------|
| **1** | **LoT/LoF page-number right-column alignment** | **Q069/Q079** | **Low-med** | **Medium** | **SELECTED** |
| 2 | Copyright recall refinement | Q010/Q011 | Medium | Low | Defer |
| 3 | Dedication centering/italic | Q033/Q034 | High | Low | Defer |
| 4 | Semantic front-matter content checks | Various | High | Low | Manual-only |

---

## Selected P048 scope

### Rule title

**P048 — PDF List of Tables/Figures page-number right-column alignment check**

### Source basis

- **Q069**: "Are all table page numbers aligned vertically in one right column?"
- **Q079**: "Are all figure page numbers aligned vertically in one right column?"

### Scope included

1. **LoT/LoF page detection** — reuse `detect_toc_like_pages` and only process `list_of_tables` and `list_of_figures`.
2. **Complete entry extraction** — reuse `extract_toc_entry_lines`; prefer entries with a detected page-number token/right edge.
3. **Right-column geometry check** — for each LoT/LoF section, compute the page-number right-edge range or median deltas across complete entries.
4. **Conservative gates** — skip if fewer than `MIN_ENTRIES = 3` complete entries, no page-number tokens, image-only/flattened extraction, or ambiguous geometry.
5. **Privacy-safe findings** — include only `page_number`, `issue_type`, `section_type`, `entry_count`, observed/allowed right-edge geometry, `triage_tier`, and `source_q_rule_id`.

### Scope excluded

- TOC page-number column alignment outside LoT/LoF — remains under P018
- LoT/LoF entry number left-column alignment — covered by P046
- LoT/LoF heading/column labels — covered by P031/P038
- LoT/LoF entry text/caption/title semantics — manual/privacy
- Any P018 behavior changes except possible helper reuse if needed

### Expected module path

`src/njit_auditor/rules/pdf_lot_lof_page_number_alignment.py`

### Expected issue types

- `lot_page_number_column_misaligned` (Q069)
- `lof_page_number_column_misaligned` (Q079)

### Expected evaluation category

`list_of_tables_figures_toc` (same family as P018, P031, P036, P046)

### Known false-positive risks

| Risk | Mitigation |
|------|------------|
| Wrapped entries or split page-number tokens | Reuse `extract_toc_entry_lines`, which already pairs nearby numeric-only right-column lines |
| Multiple page ranges or appendix-style entries | Require consistent complete-entry geometry; skip ambiguous sparse pages |
| Duplicating P018 generic warning | Emit P048 only for LoT/LoF-specific Q069/Q079 with distinct issue types and Q-rule IDs |
| Flattened/image-only PDFs | Skip silently when text-layer entries are insufficient |

### Privacy constraints

- Findings must not include LoT/LoF entry text, table titles, figure captions, page labels as raw extracted text, author names, or dissertation body text.
- Test fixtures should use synthetic placeholder content only.
- Evaluation docs must remain aggregate-only.

### Acceptance criteria

1. P048 emits `lot_page_number_column_misaligned` when List of Tables page-number right edges vary beyond threshold.
2. P048 emits `lof_page_number_column_misaligned` when List of Figures page-number right edges vary beyond threshold.
3. P048 emits nothing for aligned LoT/LoF page-number columns.
4. P048 emits nothing when no LoT/LoF page is detected.
5. P048 emits nothing for sparse or ambiguous LoT/LoF pages.
6. P048 findings contain only privacy-safe geometry metadata.
7. P048 complements P018 and P046 without changing detector behavior outside P048.

---

## Implementation plan

1. Add `pdf_lot_lof_page_number_alignment.py`.
2. Reuse `detect_toc_like_pages` and `extract_toc_entry_lines`.
3. Add P048 inventory entry and CLI/evaluation wiring.
4. Add focused synthetic tests in `tests/test_pdf_rules.py`.
5. Add rule-inventory assertion for P048.
6. Add synthetic validation doc and update README/status docs.
7. Run full validation before PR.

---

## Validation plan

| Scope | Command |
|-------|---------|
| P048 focused tests | `python -m pytest tests/test_pdf_rules.py -q -k "p048 or lot_lof_page_number"` |
| Inventory | `python -m pytest tests/test_rule_inventory.py -q` |
| Lint | `ruff check .` |
| Types | `mypy src` |
| Full suite | `python -m pytest` |

---

## Generated-output safety

- Do not commit generated outputs under `data/evaluation/generated/`.
- Do not claim a canonical five-PDF current-dataset rerun unless all five PDFs are directly available and rerun.
- Keep `generated_for_commit` and canonical aggregate notes unchanged unless a full aggregate evaluation is intentionally performed.
