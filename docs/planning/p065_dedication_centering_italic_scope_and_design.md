# P065 — Dedication Page Centering/Italic Formatting Check: Scope and Design

## 1. Metadata

- **Rule ID:** P065
- **Rule name:** Dedication Page Centering/Italic Formatting Check
- **Date scoped:** 2026-06-08
- **Baseline commit:** `01aebfb` (post PR #230)
- **Status:** Scoped only — not yet implemented
- **Validation baseline:** 910 pytest, ruff clean, mypy 82 source files
- **Source Q-rules:** Q033, Q034
- **Module (planned):** `src/njit_auditor/rules/pdf_dedication_centering_italic.py`
- **Companion rule:** P041 (`pdf_dedication_page.py`) — covers Q032 (no header in top margin)

---

## 2. Motivation

Q033 and Q034 are classified as `not_implemented` in `data/processed/rules/njit_rule_inventory.json`
and `docs/status/source_to_implementation_coverage_after_p029.md`. They are the only remaining
Dedication section Q-rules not yet addressed by a P-rule.

P041 already covers Q032 (no header text in the top margin of the Dedication page) via
`pdf_dedication_page.py`. That module explicitly states it "does not check dedication text
centering (Q033) or italicization (Q034)."

Q033 and Q034 are good P065 candidates because:

1. **Deterministic geometry:** Centering is a bounding-box metric derivable from the PDF
   text layer without OCR or content reading.
2. **Deterministic font metadata:** Italic/oblique style is extractable from PDF span font
   names (`PdfSpan.italic`, populated by `_style_flags_from_font_name` in `pdf_layout.py`).
3. **Shared detection utility:** `_find_dedication_page` in `pdf_dedication_page.py` already
   locates the Dedication page and can be reused or imported.
4. **Existing centering precedent:** `_line_centered` in `pdf_headings.py` and
   `_centering_issue` in `pdf_figure_table_layout.py` show a tested centering pattern.
5. **Conservative skip conditions:** Both checks have natural gates (no Dedication page,
   no usable text, ambiguous layout) that keep false-positive rates low.

After P064 (references/citations structural check), the highest-priority remaining gap
identified in PR #224 was dedication centering/italic (Q033/Q034), making P065 the
natural next rule.

---

## 3. Guideline/Q-rule basis

| Q-rule | Source | Description (paraphrase) | Classification |
|---|---|---|---|
| Q033 | `260330_YESNO_audit_logic_matrix.xlsx` | Dedication text block must be centered on the page | Automatable in v1 via bbox centering metric |
| Q034 | `260330_YESNO_audit_logic_matrix.xlsx` | Latin-alphabet dedication text must be italicized | Automatable in v1 via font name metadata |
| Q032 | `260330_YESNO_audit_logic_matrix.xlsx` | No header text in top margin of Dedication page | Already covered by P041 — do not duplicate |

**Q033 details:** "Is the full dedication text block visually centered on the page?"
The rule definition requires the dedication text block to be centered. This is detectable
as a horizontal bounding-box center alignment check relative to the text area center.

**Q034 details:** "If the dedication text uses the Latin alphabet, is the entire text
italicized?" The rule definition requires italicization when the text uses the Latin alphabet.
This is detectable via `PdfSpan.italic` (set by `_style_flags_from_font_name` in
`pdf_layout.py`), which checks for "italic" or "oblique" in the PDF font name.

**Not automatable in v1:**
- Whether the dedication is appropriate or professional in content (manual-only, privacy-sensitive).
- Whether the dedication page is present vs. absent — it is optional per NJIT formatting.
- Whether dedication text in non-Latin scripts satisfies Q034 (skip for non-Latin alphabet spans).

**Already covered:**
- Page numbering on the Dedication page (P022, P037, P029).
- Page order relative to other front matter (P029).
- Top-margin header text (P041 / Q032).

---

## 4. P065 v1 scope

### What P065 checks

1. **`dedication_text_not_centered` (Check A — Q033)**
   - Detect the Dedication page using the existing DEDICATION heading pattern.
   - Identify the main dedication text block: the largest contiguous block(s) of non-heading,
     non-page-number text below the DEDICATION heading, ignoring the top and bottom margin zones.
   - Compute the horizontal center of the bounding box of the dedication text block.
   - Compare to the horizontal center of the text area (`(LEFT_MARGIN_PT + page.width - RIGHT_MARGIN_PT) / 2`).
   - Emit a finding if the offset exceeds a conservative threshold (e.g., 20 pt or ~0.10 of
     text-area width, whichever is larger).
   - Gate: skip if fewer than 2 usable non-heading text lines detected.

2. **`dedication_text_not_italic` (Check B — Q034)**
   - On the same dedication text block, collect all `PdfSpan` objects that are not part of the
     heading line.
   - Compute the italic span ratio: italic_span_count / total_span_count.
   - Emit a finding if the italic ratio is below a conservative threshold (e.g., < 0.5 of spans).
   - Gate: skip if fewer than 3 usable text spans are available.
   - Gate: skip if no spans have font metadata (all fonts are None) — indicates missing font
     metadata in the PDF.
   - Note: Q034 qualifies the italic requirement with "if the dedication text uses the Latin
     alphabet." Skip if all detected spans have font names suggesting non-Latin encoding
     (heuristic: no ASCII-visible characters in span text).

### What P065 does not check

- Dedication text content, wording, or subject matter.
- Whether the dedication is required (it is optional — absence is not a finding).
- Page number presence, Roman numeral value, or order (P022, P029, P037).
- Top-margin header text (P041 / Q032).
- Dedication heading formatting — only the text below the heading is evaluated.
- Font size or font family of dedication text (no NJIT Q-rule for this).
- Non-Latin script italic requirements — deferred (Q034 qualifies with "Latin alphabet").
- TeX source: deferred to a future extension.

---

## 5. Detection algorithm

### Step 1 — Dedication page detection

Reuse the `_find_dedication_page` pattern from `pdf_dedication_page.py`:
- Scan the first 15 pages of the PDF.
- Find the first page with a line whose normalized text equals `"DEDICATION"`.
- If not found, return immediately with no findings (dedication page is optional).
- If multiple candidate pages are found within the first 15 pages, skip (ambiguous; emit
  no findings rather than risking false positives).

### Step 2 — Identify dedication text lines

On the located page:
- Collect all text lines below the DEDICATION heading line (by y-coordinate).
- Exclude: the DEDICATION heading line itself, page-number candidates (match
  `^\s*[\[(]?(?:\d+|[ivxlcdm]+)[\])]?\s*$`), lines in the bottom margin zone
  (below `page.height - 0.10 * page.height`), and lines with fewer than 2 non-space characters.
- Result: the "dedication text lines" list.

### Step 3 — Centering check (Check A, Q033)

- Compute the unified bounding box of all dedication text lines:
  `x0 = min(line.bbox.x0 for lines)`, `x1 = max(line.bbox.x1 for lines)`.
- Compute the block center: `block_center_x = (x0 + x1) / 2.0`.
- Compute the text area center: `text_area_center_x = (LEFT_MARGIN_PT + page.width - RIGHT_MARGIN_PT) / 2.0`.
- Compute offset: `center_offset_pt = abs(block_center_x - text_area_center_x)`.
- Compute ratio: `center_offset_ratio = center_offset_pt / (page.width - LEFT_MARGIN_PT - RIGHT_MARGIN_PT)`.
- Threshold: `CENTER_OFFSET_THRESHOLD_PT = 20.0` (approximately 0.28 inches).
- Emit `dedication_text_not_centered` if `center_offset_pt > CENTER_OFFSET_THRESHOLD_PT`.
- Gate: require at least `_MIN_TEXT_LINES = 2` dedication text lines; skip silently if fewer.

### Step 4 — Italic check (Check B, Q034)

- Collect all `PdfSpan` objects from the dedication text lines.
- Filter to spans with non-empty text (at least one printable character).
- If no spans have font metadata (all `span.font is None`): skip silently (no font metadata).
- Compute: `italic_count = sum(1 for s in spans if s.italic)`.
- Compute: `italic_ratio = italic_count / len(spans)`.
- Threshold: `ITALIC_RATIO_THRESHOLD = 0.5` (majority must be italic).
- Emit `dedication_text_not_italic` if `italic_ratio < ITALIC_RATIO_THRESHOLD`.
- Gate: require at least `_MIN_SPANS = 3` usable spans; skip if fewer.

### Step 5 — Skip conditions (full list)

See §8 for the complete conservative skip conditions.

### Privacy note

No dedication text, span text, font name strings, or any content from the PDF is
included in finding details. All finding fields are geometric/numeric metadata only.

---

## 6. Issue types

| Issue type | Q-rule | Condition |
|---|---|---|
| `dedication_text_not_centered` | Q033 | Block center deviates from text-area center by more than `CENTER_OFFSET_THRESHOLD_PT` (20 pt) |
| `dedication_text_not_italic` | Q034 | Italic span ratio below `ITALIC_RATIO_THRESHOLD` (0.5) among usable spans |

No ambiguity-signal issue type is used (ambiguous cases are skipped silently).

---

## 7. Finding fields

Finding details must be privacy-safe — no dedication text, names, or content.

**For `dedication_text_not_centered`:**

```python
{
    "issue_type": "dedication_text_not_centered",
    "page_number": str(page_number),
    "text_area_center_x": f"{text_area_center_x:.1f}",
    "observed_block_center_x": f"{block_center_x:.1f}",
    "center_offset_pt": f"{center_offset_pt:.1f}",
    "center_offset_ratio": f"{center_offset_ratio:.3f}",
    "text_line_count": str(text_line_count),
    "triage_tier": "medium",
    "source_q_rule_ids": "Q033",
}
```

**For `dedication_text_not_italic`:**

```python
{
    "issue_type": "dedication_text_not_italic",
    "page_number": str(page_number),
    "span_count": str(span_count),
    "italic_span_count": str(italic_count),
    "italic_span_ratio": f"{italic_ratio:.3f}",
    "triage_tier": "medium",
    "source_q_rule_ids": "Q034",
}
```

**Explicitly excluded from all fields:**
- Dedication text content
- Author/dedicatee names
- Font name strings (may leak text or encoding info)
- Source file paths
- Title text
- EF annotation text

---

## 8. Conservative skip conditions

| Condition | Reason |
|---|---|
| No DEDICATION heading found in first 15 pages | Dedication page is optional; absence is not a finding |
| Multiple DEDICATION headings detected in first 15 pages | Ambiguous layout; skip to avoid false positives |
| Fewer than `_MIN_TEXT_LINES = 2` usable dedication text lines | Too sparse to evaluate centering reliably |
| Fewer than `_MIN_SPANS = 3` usable text spans | Too sparse to evaluate italic ratio reliably |
| All spans have `font is None` | No font metadata available; italic check unreliable |
| Page has no text blocks at all | Image-only or fully flattened page |
| Dedication page is the only page in the document | Degenerate document; skip |
| Dedication text lines span more than 60% of page width | Very wide blocks may indicate complex or multi-column layout; skip centering check |

---

## 9. False-positive and false-negative risks

**Centering (Check A):**
- Very short single-word dedications may have a narrow bounding box that appears off-center
  even when visually acceptable. The `_MIN_TEXT_LINES = 2` gate reduces this risk.
- Multi-line dedications where lines have varying widths may produce a composite bounding box
  that misrepresents visual centering. Using the union bbox is conservative for this reason.
- Some PDFs encode text with x-coordinates relative to the text area, not the page; margin
  constants (`LEFT_MARGIN_PT = 108 pt`, `RIGHT_MARGIN_PT = 72 pt`) assume standard NJIT margins.
- Decorative or graphical elements on the dedication page may contribute bounding boxes
  that distort the text area center calculation if they appear as text blocks.

**Italic (Check B):**
- PDF font names may not expose italic style reliably. Many TeX-generated PDFs use Computer
  Modern font variants (`cmti10`, `cmsl10`) that are covered by `_style_flags_from_font_name`
  (which checks for "italic" and "oblique"), but other encodings may not.
- Some italic fonts may not include "italic" or "oblique" in the font name string, leading
  to false negatives (failing to detect non-italic text that should be italic). The skip
  condition "all fonts are None" handles entirely missing metadata, but partial metadata
  may produce incorrect italic ratios.
- A dedication with a mix of italic (primary text) and non-italic (e.g., quoted name)
  could fall below the 0.5 ratio threshold even when largely compliant. The 0.5 threshold
  is deliberately lenient.
- Flattened or image-rendered dedications yield no span metadata; the all-None skip
  condition handles this.

**Detection:**
- Dedications without a "DEDICATION" heading (e.g., styled as a subtitle or positioned
  differently) will not be detected. The heading-based detection gate is conservative
  and intentional.
- In EF-annotated PDFs, EF annotation text blocks may appear on the dedication page and
  influence block detection. The skip condition (too many wide blocks) partially mitigates
  this, but noisy geometry may still affect the centering metric.

---

## 10. Synthetic test plan

Minimum 12 tests in `tests/test_p065_dedication_centering_italic.py`:

| # | Test description | Expected outcome |
|---|---|---|
| 1 | No dedication page in document | No findings |
| 2 | Dedication page with centered, italic text | No findings |
| 3 | Dedication page with off-center text block (offset > 20 pt) | `dedication_text_not_centered` |
| 4 | Dedication page with centered but non-italic text | `dedication_text_not_italic` |
| 5 | Dedication page with both off-center and non-italic text | Two findings |
| 6 | Dedication page with only 1 text line (below `_MIN_TEXT_LINES`) | No findings (centering skipped) |
| 7 | Dedication page with fewer than 3 spans (below `_MIN_SPANS`) | No findings (italic skipped) |
| 8 | Dedication page where all spans have `font = None` | No findings (italic skipped; no font metadata) |
| 9 | Image-only page (no text blocks at all) | No findings |
| 10 | Multiple DEDICATION headings in first 15 pages | No findings (ambiguous; skip) |
| 11 | Dedicated page with DEDICATION heading excluded from metric (heading is top line) | No findings contamination from heading line |
| 12 | Privacy test: no dedication text content in finding details | All finding detail values are numeric/geometric only |

Optional additional tests:
- Page-number footer excluded from text block metric.
- Exactly at threshold boundary (offset = 20 pt) — no finding.
- Exactly above threshold (offset = 21 pt) — finding.
- Mixed italic/non-italic spans just above 0.5 ratio — no finding.
- Mixed italic/non-italic spans just below 0.5 ratio — finding.

---

## 11. Current-dataset evaluation plan

After implementation, run P065 on the five documented evaluation PDFs:

- Cibaku Elson 1st Review
- Yin H 2nd Review (flattened)
- Yin Haotian 2nd Review
- Yin H 4th Review (compressed)
- Sebastian Fine clean baseline (extracted from tracked ZIP)

Report per-file:
- Whether a DEDICATION page was detected (boolean/page number only).
- P065 finding count.
- Issue-type counts: `dedication_text_not_centered`, `dedication_text_not_italic`.
- Skip condition triggered if applicable.
- No dedication text, dedicatee names, or content quoted.

Expected limitation: if these dissertations have image-only, flattened, or non-standard
dedication pages, P065 may skip for most or all files. Zero findings do not prove compliance.

Generated outputs must go under `data/evaluation/generated/p065_evaluation/` (gitignored).

---

## 12. Implementation checklist

| Step | Description |
|---|---|
| 1 | Create `src/njit_auditor/rules/pdf_dedication_centering_italic.py` with `check_pdf_dedication_centering_italic()` function |
| 2 | Wire into `audit_runner.py`: add import and call in `_run_pdf_rules()` (alongside `check_pdf_dedication_page`) |
| 3 | Add P065 to rule ID and callable name lists in `audit_runner.py` (parity test arrays) |
| 4 | Add P065 entry to `data/processed/rules/project_added_rules.json` |
| 5 | Add `dedication_text_not_centered` and `dedication_text_not_italic` to evaluation category mapping |
| 6 | Write tests in `tests/test_p065_dedication_centering_italic.py` (12+ tests) |
| 7 | Create `docs/evaluation/p065_dedication_centering_italic_synthetic_validation.md` |
| 8 | Run `ruff check .`, `mypy src`, `python -m pytest` to confirm all pass |
| 9 | Update `docs/status/current_project_state_and_next_steps.md` with P065 implemented note |
| 10 | Update `data/processed/evaluation_data_manifest.json` with p065 note and new rule scope |
| 11 | Create current-dataset evaluation doc after run |
| 12 | Open PR targeting main |

Import pattern to reuse from P041:
```python
from njit_auditor.rules.pdf_dedication_page import _find_dedication_page
```
(or copy the function to avoid cross-rule imports if policy requires it)

Reuse centering pattern from `pdf_headings.py`:
```python
from njit_auditor.rules.pdf_margins import LEFT_MARGIN_PT, RIGHT_MARGIN_PT
```

Reuse italic detection from existing `PdfSpan.italic` field (already set during PDF layout loading).

---

## 13. Recommendation

**P065 is ready for implementation** following this scoping document.

The guideline basis is confirmed (Q033, Q034 in the rule inventory, both `not_implemented`).
Both detection algorithms rely on existing infrastructure:
- `_find_dedication_page` from P041 companion module
- `PdfSpan.italic` already populated by `pdf_layout.py`'s `_style_flags_from_font_name`
- Centering metric pattern from `pdf_headings.py` and `pdf_figure_table_layout.py`
- Margin constants from `pdf_margins.py`

No new infrastructure is required. Conservative skip conditions are well-defined. Privacy
model follows established P041/P064 patterns. Synthetic tests are fully specified above.

**Next PR:** Implement P065 (`pdf_dedication_centering_italic.py`), wire into `audit_runner.py`,
add 12+ synthetic tests, create synthetic validation doc, update manifest and status docs.
