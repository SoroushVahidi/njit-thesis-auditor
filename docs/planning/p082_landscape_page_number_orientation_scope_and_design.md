# P082 — Landscape Page-Number Orientation Advisory: Scope and Design

## 1. Metadata

| Field | Value |
|---|---|
| **P-rule** | P082 |
| **Rule name** | Landscape Page-Number Orientation Advisory |
| **Date** | 2026-06-09 |
| **Baseline commit** | `31e3236` (main before P082 work) |
| **Status** | **Implemented** — experimental, opt-in, disabled by default |
| **Type** | **Experimental advisory** (observational over existing P013 page-number candidates) |
| **Module** | `src/njit_auditor/rules/pdf_landscape_page_number_orientation.py` |
| **Issue types** | `landscape_page_number_orientation_advisory`, `landscape_page_number_position_advisory` |
| **Severity** | `warning` only — manual review / triage tier `manual_review` |

### State at time of implementation

| Field | Value |
|---|---|
| Highest implemented P-rule | **P082** |
| Implemented P-rule count | **81** (`P001`–`P082`, with `P075` non-inventory) |
| Next project-added rule ID | **P083** |
| Canonical aggregate (default mode) | **1,543** (unchanged) |
| pytest count | **1124** (18 new P082 tests) |

---

## 2. Motivation

Post-P080 DOCX+PDF overlap evaluation identified landscape page-number orientation as a
reviewer-comment theme (Aguado Alvaro DOCX: 3 comments) with no PDF-side coverage. University
guidance on landscape page-number placement and orientation is inconsistent across sources, and
NJIT-specific hard orientation language was **not verified** in this repository.

P082 is therefore **experimental and observational**:

- It reuses existing P013 page-number candidate detection without changing P013/P019/P028/P029/P037.
- It adds orientation/position advisories only when explicitly enabled.
- It does not affect default audit output or the canonical five-PDF aggregate.

---

## 3. Guideline and Q-Rule Basis

| Source | Relevance for P082 |
|---|---|
| Q001 / page-numbering family | **Indirect** — P082 observes accepted page-number candidates only |
| NJIT landscape footer guidance | **Not verified** — no hard pass/fail threshold adopted |
| EF overlap (post-P080) | **Motivation only** — landscape orientation comments exist in DOCX feedback |

P082 does **not** claim compliance with a specific NJIT landscape orientation rule.

---

## 4. Design Decisions

### 4.1 Experimental opt-in

- Disabled by default via `AuditOptions` / `DEFAULT_AUDIT_OPTIONS`.
- Enabled with CLI: `njit-audit pdf <file> --enable-experimental P082`.
- Enabled in API: `AuditOptions(experimental_rules=frozenset({"P082"}))`.

### 4.2 Parser/model metadata (backward compatible)

Added optional fields without breaking existing constructors:

| Field | Source | Purpose |
|---|---|---|
| `PdfTextLine.line_dir` | PyMuPDF `line["dir"]` | Cardinal direction quantization |
| `PdfTextLine.wmode` | PyMuPDF `line["wmode"]` | Writing-mode gate (supported: `0` only) |
| `PdfPage.page_rotation` | `page.rotation` | Visual angle composition |
| `PdfPage.is_visually_landscape` | width/height aspect ratio | Landscape page filter |

### 4.3 Candidate reuse (no P013 changes)

- Uses `detect_page_number_candidates()` and `_candidate_confidence()`.
- Accepts only **one medium-confidence** candidate per page.
- Skips low-confidence, multiple-candidate, unmatched-line, and ambiguous cases.

### 4.4 Orientation and position logic

- `line_angle` from quantized cardinal `line_dir`.
- `visual_angle = (line_angle + page_rotation) % 360`.
- Orientation advisory when `visual_angle in {90, 270}` → `vertical_text_on_landscape_page`.
- Position advisory for clear margin outliers (side edge, top margin on landscape).

### 4.5 Strict skip conditions

P082 skips when:

- not explicitly enabled;
- page is not visually landscape;
- no text layer / image-only page;
- no accepted page-number candidate;
- more than one accepted candidate;
- matched text line not found;
- missing `line_dir`;
- unsupported `wmode`;
- non-cardinal / noisy direction;
- uncertain position bucket;
- figure labels and other non-page-number text.

### 4.6 Privacy

Findings include structural metadata only: page index, normalized bbox, page dimensions,
rotation, direction vector, quantized angles, location bucket, confidence, advisory reason.
**No raw page text, captions, section titles, author names, or dissertation content.**

---

## 5. Out of Scope

- OCR / image-only page-number recovery
- GUI / HITL workflow changes
- Appendix rule work
- Changes to P013/P019/P028/P029/P037 candidate logic
- Raw guideline/data file edits
- LFS migration or git history rewrite
- Error-level findings or automatic remediation

---

## 6. Validation Plan

1. `ruff check .`, `mypy src`, `python -m pytest`
2. Default-mode five-PDF audit: aggregate **1,543**, **0 P082** findings
3. Synthetic fixtures with P082 enabled: bad landscape pages emit advisories; acceptable/ambiguous cases silent
4. Default-mode invariant test: non-P082 findings identical with and without P082 flag

See `docs/evaluation/p082_landscape_page_number_orientation_synthetic_validation.md`.
