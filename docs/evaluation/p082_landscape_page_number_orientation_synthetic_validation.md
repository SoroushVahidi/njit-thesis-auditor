# P082 Synthetic Validation — Landscape Page-Number Orientation Advisory

- **Auditor scope:** P001–P082 implemented (P082 experimental, disabled by default)
- **Baseline commit:** `31e3236` (main before P082)
- **Privacy:** Aggregate test counts only; no dissertation body text quoted

---

## 1. Purpose

P082 is an **experimental opt-in advisory** that inspects visually landscape pages with exactly
one accepted medium-confidence page-number candidate from existing P013 detection. It uses
PyMuPDF `line_dir`, `wmode`, and `page_rotation` metadata to emit **warning / manual-review**
advisories for clear orientation or margin-position outliers.

**P082 is disabled by default.** Default audit output and the canonical five-PDF aggregate
(**1,543**) are unchanged unless `--enable-experimental P082` (or `AuditOptions`) is set.

---

## 2. Enablement

| Mechanism | Example |
|---|---|
| CLI | `njit-audit pdf path/to/file.pdf --enable-experimental P082` |
| API | `run_pdf_audit_full(path, options=AuditOptions(experimental_rules=frozenset({"P082"})))` |
| Web UI | Not wired in v1 — CLI/API only |

---

## 3. Issue Types

| Issue type | When emitted |
|---|---|
| `landscape_page_number_orientation_advisory` | Visual angle is 90° or 270° (vertical text on landscape page) |
| `landscape_page_number_position_advisory` | Clear margin-position outlier (side edge or top margin on landscape) |

Both are `warning` severity with `triage_tier: manual_review`. **No error-level findings.**

---

## 4. Relationship to P013 and Related Rules

| Rule | Role |
|---|---|
| **P013** | Supplies page-number candidates; logic unchanged |
| **P019** | Page-numbering consistency; unchanged |
| **P028/P029/P037** | Numbering regime / roman sequence; unchanged |
| **P082** | Observational advisory over accepted P013 candidates on landscape pages only |

---

## 5. Synthetic Test Coverage

18 tests in `tests/test_p082_landscape_page_number_orientation.py`:

| # | Test | Behavior verified |
|---|---|---|
| 1 | `test_quantize_dir_cardinals` | Cardinal direction mapping (0/90/180/270) |
| 2 | `test_quantize_dir_noisy_near_cardinal` | Near-cardinal tolerance |
| 3 | `test_quantize_dir_non_cardinal_returns_none` | 15° direction → skip |
| 4 | `test_visual_angle_composition` | `(line_angle + page_rotation) % 360` |
| 5 | `test_is_visually_landscape_page_from_model` | Landscape aspect detection |
| 6 | `test_p082_disabled_by_default` | No findings when disabled |
| 7 | `test_p082_portrait_page_out_of_scope_when_enabled` | Portrait pages skipped |
| 8 | `test_p082_landscape_acceptable_bottom_center_horizontal` | Acceptable placement silent |
| 9 | `test_p082_landscape_vertical_orientation_advisory` | Vertical text → orientation advisory |
| 10 | `test_p082_landscape_top_margin_position_advisory` | Top margin → position advisory |
| 11 | `test_p082_rotate_90_visually_acceptable_no_false_positive` | Page rotation composition |
| 12 | `test_p082_non_cardinal_direction_skipped` | Non-cardinal morph → skip |
| 13 | `test_p082_image_only_landscape_page_skipped` | Image-only page → skip |
| 14 | `test_p082_does_not_flag_figure_label_without_page_number_candidate` | Figure label → skip |
| 15 | `test_p082_default_mode_invariant_against_enabled_mode` | Non-P082 findings unchanged |
| 16 | `test_p082_finding_details_are_privacy_safe` | No raw text in details |
| 17 | `test_pdf_layout_preserves_line_dir_and_wmode` | Parser metadata preserved |
| 18 | `test_cli_enable_experimental_p082_flag` | CLI `--enable-experimental P082` works |

**All 18 tests pass.**

---

## 6. Privacy Model

P082 finding `details` may include:

- `page_number`, `candidate_bbox`, `page_width_pt`, `page_height_pt`
- `page_rotation`, `line_dir`, `line_angle_deg`, `visual_angle_deg`
- `wmode`, `location_bucket`, `position_type`, `confidence`, `advisory_reason`

P082 finding `details` must **not** include raw page text, nearby text, captions, or author names.

---

## 7. Default-Mode Five-PDF Evaluation

Default-mode audit on the canonical five-PDF set (no `--enable-experimental`):

| Result | Value |
|---|---|
| Total findings | **1,543** (unchanged vs pre-P082 baseline) |
| P082 findings | **0** |

P082 emits findings only when explicitly enabled. The canonical aggregate document
`docs/evaluation/current_auditor_after_p070_evaluation.md` remains the reference snapshot;
no new aggregate doc is required because totals are unchanged in default mode.

---

## 8. Targeted P082-Enabled Synthetic Result

Synthetic landscape PDF with vertical page-number text (`rotate=90` at long edge):

- **P082 enabled:** emits `landscape_page_number_orientation_advisory` (warning)
- **P082 disabled:** silent (no P082 findings)
- Acceptable bottom-center horizontal page numbers: silent even when enabled
- Ambiguous/non-cardinal/image-only cases: silent when enabled

---

## 9. Explicit Non-Goals Confirmed

- No OCR implementation
- No GUI/HITL changes
- No appendix rule work
- No raw data file changes
- No LFS migration or history rewrite
- No changes to P013/P019/P028/P029/P037 candidate logic
