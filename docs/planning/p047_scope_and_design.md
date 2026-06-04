# P047 Scope and Design

- **Date:** 2026-06-03
- **Status:** **Implemented**
- **Baseline main:** `0331c35` (PR #132 — post-P046 consistency audit; P001–P046 implemented)

---

## Current state

| Area | State |
|------|-------|
| P-rules | **47/47** implemented (`P001`–`P047`) |
| Q-rules (updated inventory, post-P047) | **79** total — **2** implemented, **55** partially_implemented, **22** not_implemented (9 manual-only, 13 automatable gaps) |
| Bio Sketch hanging indent / inter-entry spacing | **P045** — Q028/Q029; implemented |
| LoT/LoF entry number left-column alignment | **P046** — Q068/Q078; implemented |
| LoT/LoF page number right-column alignment | **P018** — Q069/Q079; partially covered via `misaligned_page_number_column` |
| Bio Sketch bullet single-spacing | **P047** — Q026; implemented |

**Gap:** Q026 ("Are the bullet items in the education section single-spaced within each bullet?") was deferred from P045 because the single-gap-threshold approach used in P043/P044/P045 cannot reliably distinguish within-bullet gaps from between-bullet gaps. A v2 approach using section-detection (finding the education/publications sub-sections by looking for characteristic patterns) would allow more targeted single-spacing checks.

---

## Candidate comparison

### Candidate 1 — Bio Sketch bullet single-spacing (Q026) ← RECOMMENDED

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q026: bullet items in the education section are single-spaced within each bullet |
| **Proposed rule** | **P047** — Bio Sketch bullet section single-spacing check |
| **Module** | `src/njit_auditor/rules/pdf_biosketch_bullet_spacing.py` |
| **Issue types** | `biosketch_bullet_item_spacing_not_single` |
| **Implementation risk** | **Medium** — requires identifying likely "bullet" blocks on the Bio Sketch page; approach: look for multi-line blocks that are NOT hanging-indent (flush or indented-first pattern) and check their internal line spacing; gate: require ≥2 such blocks |
| **Noise risk** | **Medium** — bullet blocks in the bio sketch may look similar to other content; conservative threshold needed |
| **Privacy** | **Low** — findings contain only geometry (page number, block index, line gap); no bio sketch text content |
| **Likely tests** | (1) No Bio Sketch heading → no finding; (2) Bullet blocks with tight single-spacing → no finding; (3) Bullet block with too-large internal gap → biosketch_bullet_item_spacing_not_single; (4) Too few blocks (gate) → no finding; (5) Privacy metadata check |
| **Why selected** | Q026 is the highest-remaining-value automatable gap after P046; builds on P045 infrastructure (BIOGRAPHICAL SKETCH heading detection, block grouping); geometry-only; privacy-safe |

### Candidate 2 — Dedication text centering (Q033)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q033: dedication text block visually centered on the page |
| **Why not selected** | High FP risk — no reliable centering signal in PDF text layer; consistently deferred |

### Candidate 3 — Dedication text italic (Q034)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q034: dedication text italicized if Latin alphabet |
| **Why not selected** | High FP risk — italic metadata unreliable in many PDFs; consistently deferred |

### Candidate 4 — Bio Sketch semantic content (Q023–Q025, Q027, Q030)

| Field | Detail |
|-------|--------|
| **Why not selected** | Content/semantic checks with high privacy risk; require reading bio sketch text |

### Candidate 5 — Acknowledgements semantic content (Q039–Q043)

| Field | Detail |
|-------|--------|
| **Why not selected** | Content/semantic checks with very high privacy risk; require reading private acknowledgements content |

---

## Ranking

| Rank | Candidate | Q-rule | Risk | Value | Decision |
|------|-----------|--------|------|-------|----------|
| **1** | **Bio Sketch bullet single-spacing** | **Q026** | **Medium** | **Medium** | **SELECTED** |
| 2 | Dedication centering | Q033 | High | Low | High FP; defer |
| 3 | Dedication italic | Q034 | High | Low | Metadata unreliable; defer |
| 4 | Bio Sketch semantic content | Q023–Q027/Q030 | High | Low | Privacy risk; defer |
| 5 | Acknowledgements semantic content | Q039–Q043 | Very high | Low | Privacy risk; defer |

---

## Selected P047 scope

### Rule title

**P047 — PDF Biographical Sketch bullet section single-spacing check**

### Source basis

- **Q026**: "Are the bullet items in the education section single-spaced within each bullet?"

### Scope included

1. **Bio Sketch page detection** — use `find_named_frontmatter_headings` to locate pages with a "BIOGRAPHICAL SKETCH" heading. If not detected, emit nothing.
2. **Multi-line block extraction** — collect text line groups below the heading using `MAX_PARA_GAP_PT = 20.0`. This is wider than P043/P044/P045 so wrapped or double-spaced bullet/list lines stay in one candidate block. Filter short lines and page-number candidates.
3. **Bullet-block identification** — identify blocks that do NOT have hanging indent (i.e., `rest_x0 - first_x0 < HANGING_THRESHOLD_PT = 12pt`). These are likely bullet or body blocks.
4. **Q026 check** — for each non-hanging-indent block with ≥ 3 lines: check that all internal line gaps are ≤ `BULLET_MAX_GAP_PT = 12.0`. This tighter split/check threshold keeps distinct bullet/list entries separate while still flagging non-single-spaced internal gaps. If any internal gap exceeds the threshold, emit `biosketch_bullet_section_not_single_spaced`.
5. **Gates** — skip if BIOGRAPHICAL SKETCH heading absent; skip Q026 check if fewer than `MIN_BULLET_BLOCKS = 2` non-hanging-indent multi-line blocks are found.
6. **Privacy-safe findings** — include only: `page_number`, `issue_type`, `block_index`, `line_pair_index`, `observed_gap_points`, `required_max_gap_points`, `triage_tier`, `source_q_rule_id`.

### Scope excluded

- Bio Sketch publication entries (Q028/Q029) — covered by P045
- Bio Sketch heading presence (Q021) — covered by P038
- Bio Sketch text content (Q023–Q030) — manual/privacy
- Acknowledgements content — manual/privacy
- General body spacing — covered by P016/P023

### Expected module path

`src/njit_auditor/rules/pdf_biosketch_bullet_spacing.py`

### Expected issue types

- `biosketch_bullet_section_not_single_spaced` (Q026)

### Expected evaluation category

`indentation` (same as P043/P044/P045)

### Known false-positive risks

| Risk | Mitigation |
|------|-----------|
| Bio Sketch blocks without publications may all be hanging-indent | Gate: require ≥2 non-hanging-indent blocks |
| Very short blocks (2-line) | Require ≥3 lines per block for internal spacing check |
| Compressed/flattened PDFs | Gate silently skips |

### Privacy constraints

- Findings: page number, block index, line pair index, gap measurements only.
- No bio sketch text, degree information, institution names, or author names.

### Acceptance criteria

1. P047 emits `biosketch_bullet_section_not_single_spaced` when a non-hanging-indent block on the Bio Sketch page has excessive internal line gaps.
2. P047 emits nothing when no BIOGRAPHICAL SKETCH page is detected.
3. P047 emits nothing when fewer than MIN_BULLET_BLOCKS non-hanging-indent multi-line blocks are found.
4. P047 does not duplicate P045, P043/P044, or P015/P016 issue types.
5. All existing 524 tests pass; 6 new P047 synthetic tests added; post-merge suite has 530 tests.

---

## Data/evaluation blocker note

Only 4 of 5 evaluation PDFs are directly accessible. Sebastian Fine Revised is ZIP-only.
A canonical five-PDF run is not possible until all five PDFs are mounted or extracted.

---

## Privacy notes

- Findings report only geometry — no Bio Sketch text content.
- Test fixtures use synthetic placeholder content.
- P047 findings never contain names, degrees, institutions, or bio prose.

## Generated-output safety

- Outputs under `data/evaluation/generated/` stay gitignored.
- Do not commit audit JSON or per-PDF reports.
